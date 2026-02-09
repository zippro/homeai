from __future__ import annotations

import unittest

try:
    from fastapi.testclient import TestClient

    from app.main import app

    _ROUTE_TESTS_AVAILABLE = True
except ModuleNotFoundError:
    _ROUTE_TESTS_AVAILABLE = False


@unittest.skipUnless(_ROUTE_TESTS_AVAILABLE, "fastapi dependency is not installed in this environment")
class RouteResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def _login(self, user_id: str) -> str:
        response = self.client.post(
            "/v1/auth/login-dev",
            json={"user_id": user_id, "platform": "tests", "ttl_hours": 12},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        return payload["access_token"]

    def test_profile_overview_me_route_is_not_shadowed(self) -> None:
        token = self._login("route_user_profile")
        response = self.client.get(
            "/v1/profile/overview/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["user_id"], "route_user_profile")

    def test_projects_board_me_route_is_not_shadowed(self) -> None:
        token = self._login("route_user_board")
        response = self.client.get(
            "/v1/projects/board/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["user_id"], "route_user_board")


if __name__ == "__main__":
    unittest.main()
