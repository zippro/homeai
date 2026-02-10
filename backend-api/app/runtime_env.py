from __future__ import annotations

import os


def is_production_mode() -> bool:
    value = os.getenv("APP_ENV", "").strip().lower()
    return value in {"prod", "production"}


def read_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
