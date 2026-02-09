from __future__ import annotations


def parse_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    value = authorization.strip()
    if not value:
        return None
    if not value.lower().startswith("bearer "):
        return None
    token = value[7:].strip()
    if not token:
        return None
    return token
