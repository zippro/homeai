from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.bootstrap import init_database
from app.experiment_store import run_experiment_automation
from app.schemas import AdminActionRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run experiment automation pipeline (guardrails + rollout evaluation)."
    )
    parser.add_argument("--hours", type=int, default=24, help="Analytics lookback window in hours.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate only; do not mutate experiment state.",
    )
    parser.add_argument(
        "--rollout-limit",
        type=int,
        default=200,
        help="Maximum number of active experiments to evaluate for rollout.",
    )
    parser.add_argument(
        "--notify-webhook-url",
        default=os.getenv("EXPERIMENT_AUTOMATION_NOTIFY_WEBHOOK_URL", ""),
        help="Optional webhook URL for run summaries.",
    )
    parser.add_argument(
        "--notify-dry-run",
        action="store_true",
        help="Send webhook notifications even for dry-run executions.",
    )
    parser.add_argument(
        "--fail-on-breach",
        action="store_true",
        help="Exit non-zero when guardrail breaches are detected.",
    )
    parser.add_argument(
        "--fail-on-rollout-blocked",
        action="store_true",
        help="Exit non-zero when rollouts are blocked.",
    )
    parser.add_argument("--actor", default="scheduler", help="Audit actor name.")
    parser.add_argument("--reason", default="scheduled_experiment_automation", help="Audit reason.")
    return parser.parse_args()


def _build_notification_payload(result: dict) -> dict:
    guardrails = result.get("guardrails") or {}
    rollouts = result.get("rollouts") or {}
    return {
        "type": "homeai_experiment_automation",
        "checked_at": result.get("checked_at"),
        "dry_run": bool(result.get("dry_run")),
        "window_hours": int(result.get("window_hours") or 0),
        "rollout_limit": int(result.get("rollout_limit") or 0),
        "summary": {
            "guardrails": {
                "evaluated_count": int(guardrails.get("evaluated_count") or 0),
                "breached_count": int(guardrails.get("breached_count") or 0),
                "paused_count": int(guardrails.get("paused_count") or 0),
            },
            "rollouts": {
                "evaluated_count": int(rollouts.get("evaluated_count") or 0),
                "applied_count": int(rollouts.get("applied_count") or 0),
                "blocked_count": int(rollouts.get("blocked_count") or 0),
            },
        },
        "result": result,
    }


def _post_json(*, url: str, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url=url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            # Best effort read to complete the request lifecycle.
            response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"webhook_notify_failed:{exc}") from exc


def _determine_exit_code(*, result: dict, fail_on_breach: bool, fail_on_rollout_blocked: bool) -> int:
    guardrails = result.get("guardrails") or {}
    rollouts = result.get("rollouts") or {}
    breached_count = int(guardrails.get("breached_count") or 0)
    blocked_count = int(rollouts.get("blocked_count") or 0)

    if fail_on_breach and breached_count > 0:
        return 2
    if fail_on_rollout_blocked and blocked_count > 0:
        return 3
    return 0


def main() -> int:
    args = parse_args()
    init_database()

    result = run_experiment_automation(
        hours=max(1, int(args.hours)),
        dry_run=bool(args.dry_run),
        rollout_limit=max(1, int(args.rollout_limit)),
        action=AdminActionRequest(actor=args.actor, reason=args.reason),
    )
    result_payload = result.model_dump(mode="json")
    print(json.dumps(result_payload, indent=2, default=str))

    notify_webhook_url = str(args.notify_webhook_url or "").strip()
    should_notify = bool(notify_webhook_url) and (not bool(args.dry_run) or bool(args.notify_dry_run))
    if should_notify:
        notification_payload = _build_notification_payload(result_payload)
        _post_json(url=notify_webhook_url, payload=notification_payload)

    return _determine_exit_code(
        result=result_payload,
        fail_on_breach=bool(args.fail_on_breach),
        fail_on_rollout_blocked=bool(args.fail_on_rollout_blocked),
    )


if __name__ == "__main__":
    raise SystemExit(main())
