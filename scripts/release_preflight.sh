#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SKIP_IOS="${SKIP_IOS:-0}"
SKIP_ANDROID="${SKIP_ANDROID:-0}"
SKIP_API_SMOKE="${SKIP_API_SMOKE:-0}"

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$1"
}

run_backend_checks() {
  log "Backend quality checks"
  cd "${ROOT_DIR}/backend-api"
  if [[ ! -f ".venv/bin/activate" ]]; then
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
  else
    source .venv/bin/activate
  fi

  make quality

  if [[ "${SKIP_API_SMOKE}" == "1" ]]; then
    log "Skipping backend smoke checks (SKIP_API_SMOKE=1)"
    return
  fi

  log "Backend smoke checks"
  uvicorn app.main:app --host 127.0.0.1 --port 8011 >/tmp/homeai-preflight-api.log 2>&1 &
  API_PID=$!
  trap 'kill "${API_PID}" >/dev/null 2>&1 || true' EXIT

  READY=0
  for _ in $(seq 1 45); do
    if curl -fsS http://127.0.0.1:8011/healthz >/dev/null; then
      READY=1
      break
    fi
    sleep 1
  done

  if [[ "${READY}" -ne 1 ]]; then
    echo "Backend API failed to become ready during preflight."
    cat /tmp/homeai-preflight-api.log
    exit 1
  fi

  HOMEAI_API_BASE_URL=http://127.0.0.1:8011 python scripts/smoke_api_flow.py
  HOMEAI_API_BASE_URL=http://127.0.0.1:8011 python scripts/smoke_entitlement_reconciliation.py
  python scripts/run_experiment_guardrails.py --dry-run --hours 24
  python scripts/run_experiment_automation.py --dry-run --hours 24 --rollout-limit 200
  kill "${API_PID}" >/dev/null 2>&1 || true
  trap - EXIT
}

run_web_checks() {
  log "Web app checks"
  cd "${ROOT_DIR}/web-app"
  npm run check
  npm run build

  log "Admin dashboard checks"
  cd "${ROOT_DIR}/admin-dashboard"
  npm ci
  npm run check
  npm run build
}

run_android_checks() {
  if [[ "${SKIP_ANDROID}" == "1" ]]; then
    log "Skipping Android checks (SKIP_ANDROID=1)"
    return
  fi

  log "Android assembleDebug"
  cd "${ROOT_DIR}/android-app"

  if [[ -z "${JAVA_HOME:-}" ]]; then
    if [[ -d "/opt/homebrew/opt/openjdk" ]]; then
      export JAVA_HOME="/opt/homebrew/opt/openjdk"
    fi
  fi
  export GRADLE_USER_HOME="${ROOT_DIR}/.gradle-home"

  ./gradlew :app:assembleDebug --no-daemon
}

run_ios_checks() {
  if [[ "${SKIP_IOS}" == "1" ]]; then
    log "Skipping iOS checks (SKIP_IOS=1)"
    return
  fi

  log "iOS build-for-testing"
  cd "${ROOT_DIR}/mobile-ios"

  if ! command -v xcodegen >/dev/null 2>&1; then
    echo "xcodegen is required for iOS preflight. Install with: brew install xcodegen"
    exit 1
  fi

  xcodegen generate
  DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
    xcodebuild -project HomeAI.xcodeproj \
      -scheme HomeAI \
      -configuration Debug \
      -destination 'generic/platform=iOS Simulator' \
      CODE_SIGNING_ALLOWED=NO \
      -derivedDataPath /tmp/HomeAIDerived \
      build-for-testing
}

main() {
  run_backend_checks
  run_web_checks
  run_android_checks
  run_ios_checks
  log "Release preflight finished successfully."
}

main "$@"
