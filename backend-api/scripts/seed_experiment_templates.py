from __future__ import annotations

import argparse

from app.experiment_store import list_experiment_templates, upsert_experiment
from app.schemas import AdminActionRequest, ExperimentUpsertRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed admin experiments from built-in templates."
    )
    parser.add_argument(
        "--activate",
        action="store_true",
        help="Seed experiments in active state (default: inactive).",
    )
    parser.add_argument(
        "--actor",
        default="seed_script",
        help="Audit actor label.",
    )
    parser.add_argument(
        "--reason",
        default="seed_experiment_templates",
        help="Audit reason.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    templates = list_experiment_templates()
    action = AdminActionRequest(actor=args.actor, reason=args.reason)

    for template in templates:
        payload = ExperimentUpsertRequest(
            name=template.name,
            description=template.description,
            is_active=args.activate,
            assignment_unit=template.assignment_unit,
            primary_metric=template.primary_metric,
            guardrails=template.guardrails,
            variants=template.variants,
        )
        experiment = upsert_experiment(
            experiment_id=template.template_id,
            payload=payload,
            action=action,
        )
        print(
            f"seeded {experiment.experiment_id} "
            f"(active={experiment.is_active}, variants={len(experiment.variants)})"
        )


if __name__ == "__main__":
    main()
