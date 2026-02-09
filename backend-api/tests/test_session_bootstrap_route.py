from __future__ import annotations

import unittest

try:
    from fastapi.testclient import TestClient

    from app.bootstrap import init_database
    from app.main import app

    _SESSION_ROUTE_TESTS_AVAILABLE = True
except ModuleNotFoundError:
    _SESSION_ROUTE_TESTS_AVAILABLE = False


@unittest.skipUnless(_SESSION_ROUTE_TESTS_AVAILABLE, "fastapi dependency is not installed in this environment")
class SessionBootstrapRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_database()
        cls.client = TestClient(app)

    def _login(self, user_id: str) -> str:
        response = self.client.post(
            "/v1/auth/login-dev",
            json={"user_id": user_id, "platform": "tests", "ttl_hours": 24},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["access_token"]

    def test_bootstrap_me_requires_authentication(self) -> None:
        response = self.client.get("/v1/session/bootstrap/me")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "missing_or_invalid_token")

    def test_bootstrap_me_returns_unified_payload(self) -> None:
        token = self._login("session_bootstrap_user")
        response = self.client.get(
            "/v1/session/bootstrap/me?board_limit=20&experiment_limit=10",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["me"]["user_id"], "session_bootstrap_user")
        self.assertEqual(payload["profile"]["user_id"], "session_bootstrap_user")
        self.assertEqual(payload["board"]["user_id"], "session_bootstrap_user")
        self.assertEqual(payload["experiments"]["user_id"], "session_bootstrap_user")
        self.assertIn("catalog", payload)
        self.assertIsInstance(payload["catalog"], list)
        self.assertGreaterEqual(len(payload["catalog"]), 1)
        self.assertIn("variables", payload)
        self.assertIn("provider_defaults", payload)
        self.assertIn("default_provider", payload["provider_defaults"])
        self.assertIn("fallback_chain", payload["provider_defaults"])


if __name__ == "__main__":
    unittest.main()

