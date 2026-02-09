from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta

BASE_URL = os.getenv("HOMEAI_API_BASE_URL", "http://localhost:8000")
USER_ID = os.getenv("HOMEAI_SMOKE_USER_ID", f"smoke_entitlement_{int(datetime.now(UTC).timestamp())}")


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


def fetch_entitlement(token: str) -> dict:
    return request_json("GET", f"/v1/subscriptions/entitlements/{USER_ID}", token=token)


def assert_equal(actual, expected, label: str) -> None:
    if actual != expected:
        raise RuntimeError(f"assert_failed:{label}: expected={expected!r} actual={actual!r}")


def main() -> None:
    login = request_json(
        "POST",
        "/v1/auth/login-dev",
        {"user_id": USER_ID, "platform": "script", "ttl_hours": 4},
    )
    token = login["access_token"]

    print("login:", json.dumps(login, indent=2))

    initial = fetch_entitlement(token)
    print("entitlement_initial:", json.dumps(initial, indent=2))

    web_payload = {
        "event_id": f"web_smoke_{int(datetime.now(UTC).timestamp())}",
        "user_id": USER_ID,
        "product_id": "pro_monthly_web",
        "status": "active",
        "metadata": {"origin": "web"},
    }
    request_json("POST", "/v1/webhooks/web-billing", web_payload)
    after_web = fetch_entitlement(token)
    print("entitlement_after_web_active:", json.dumps(after_web, indent=2))
    assert_equal(after_web.get("status"), "active", "status_after_web")
    assert_equal(after_web.get("source"), "web", "source_after_web")

    downgrade_payload = {
        "event_id": f"gplay_smoke_{int(datetime.now(UTC).timestamp())}",
        "user_id": USER_ID,
        "product_id": "pro_monthly_android",
        "status": "expired",
        "metadata": {"origin": "google_play", "attempt": "downgrade"},
    }
    request_json("POST", "/v1/webhooks/google-play", downgrade_payload)
    after_downgrade = fetch_entitlement(token)
    print("entitlement_after_google_play_expired:", json.dumps(after_downgrade, indent=2))
    assert_equal(after_downgrade.get("status"), "active", "status_after_expired_webhook")
    assert_equal(after_downgrade.get("source"), "web", "source_after_expired_webhook")

    renews_at = (datetime.now(UTC) + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ios_payload = {
        "event_id": f"storekit_smoke_{int(datetime.now(UTC).timestamp())}",
        "user_id": USER_ID,
        "product_id": "pro_monthly_ios",
        "status": "active",
        "renews_at": renews_at,
        "metadata": {"origin": "ios"},
    }
    request_json("POST", "/v1/webhooks/storekit", ios_payload)
    after_ios = fetch_entitlement(token)
    print("entitlement_after_ios_active:", json.dumps(after_ios, indent=2))
    assert_equal(after_ios.get("status"), "active", "status_after_ios")
    assert_equal(after_ios.get("source"), "ios", "source_after_ios")

    print("smoke_entitlement_reconciliation: PASS")


if __name__ == "__main__":
    main()
