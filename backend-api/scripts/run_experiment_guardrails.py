from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.bootstrap import init_database
from app.experiment_store import evaluate_experiment_guardrails
from app.schemas import AdminActionRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate and optionally enforce experiment guardrails.")
    parser.add_argument("--hours", type=int, default=24, help="Analytics lookback window in hours.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate only; do not pause experiments.",
    )
    parser.add_argument("--actor", default="scheduler", help="Audit actor name.")
    parser.add_argument("--reason", default="scheduled_guardrail_check", help="Audit reason.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    init_database()

    result = evaluate_experiment_guardrails(
        hours=max(1, int(args.hours)),
        dry_run=bool(args.dry_run),
        action=AdminActionRequest(actor=args.actor, reason=args.reason),
    )
    print(json.dumps(result.model_dump(mode="json"), indent=2, default=str))


if __name__ == "__main__":
    main()
