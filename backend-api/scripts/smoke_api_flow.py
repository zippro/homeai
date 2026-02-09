from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE_URL = os.getenv("HOMEAI_API_BASE_URL", "http://localhost:8000")


def request_json(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url=f"{BASE_URL}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"http_{exc.code}: {detail}") from exc


def main() -> None:
    login = request_json(
        "POST",
        "/v1/auth/login-dev",
        {"user_id": "smoke_user", "platform": "script", "ttl_hours": 4},
    )
    token = login["access_token"]

    me = request_json("GET", "/v1/auth/me", token=token)
    profile = request_json("GET", "/v1/profile/overview/me", token=token)
    board = request_json("GET", "/v1/projects/board/me?limit=5", token=token)

    print("login:", json.dumps(login, indent=2))
    print("me:", json.dumps(me, indent=2))
    print("profile_overview_me:", json.dumps(profile, indent=2))
    print("board_me:", json.dumps(board, indent=2))


if __name__ == "__main__":
    main()
