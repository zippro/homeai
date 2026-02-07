from __future__ import annotations

import json

from app.credit_reset_store import tick_daily_credit_reset


def main() -> None:
    result = tick_daily_credit_reset()
    print(json.dumps(result.model_dump(mode="json"), indent=2, default=str))


if __name__ == "__main__":
    main()
