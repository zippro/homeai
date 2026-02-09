#!/usr/bin/env bash
set -euo pipefail

REPO="${1:-zippro/homeai}"
BRANCH="${2:-main}"

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI is required. Install from: https://cli.github.com/"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Run 'gh auth login' first."
  exit 1
fi

tmp_file="$(mktemp)"
cat >"${tmp_file}" <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Backend Quality / quality",
      "Web Admin Quality / syntax-check",
      "Android Quality / compile",
      "iOS Quality / build"
    ]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "required_approving_review_count": 1,
    "require_code_owner_reviews": false
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": true
}
EOF

gh api \
  --method PUT \
  "repos/${REPO}/branches/${BRANCH}/protection" \
  --input "${tmp_file}"

rm -f "${tmp_file}"

echo "Branch protection updated for ${REPO}:${BRANCH}"
