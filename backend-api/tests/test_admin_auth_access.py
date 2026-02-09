from __future__ import annotations

import os
import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
    from sqlalchemy import delete

    from app.bootstrap import init_database
    from app.db import session_scope
    from app.main import app
    from app.models import AuthSessionModel

    _ADMIN_AUTH_TESTS_AVAILABLE = True
except ModuleNotFoundError:
    _ADMIN_AUTH_TESTS_AVAILABLE = False


@unittest.skipUnless(_ADMIN_AUTH_TESTS_AVAILABLE, "fastapi/sqlalchemy dependency is not installed")
class AdminAuthAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_database()
        cls.client = TestClient(app)

    def setUp(self) -> None:
        with session_scope() as session:
            session.execute(delete(AuthSessionModel))

    def _login(self, user_id: str) -> str:
        response = self.client.post(
            "/v1/auth/login-dev",
            json={"user_id": user_id, "platform": "tests", "ttl_hours": 24},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["access_token"]

    def test_admin_open_mode_allows_unauthenticated_requests(self) -> None:
        with patch.dict(os.environ, {"ADMIN_API_TOKEN": "", "ADMIN_USER_IDS": ""}, clear=False):
            response = self.client.get("/v1/admin/analytics/overview")
            self.assertEqual(response.status_code, 200)

    def test_admin_token_mode_requires_x_admin_token(self) -> None:
        with patch.dict(os.environ, {"ADMIN_API_TOKEN": "secret-admin-token", "ADMIN_USER_IDS": ""}, clear=False):
            missing_response = self.client.get("/v1/admin/analytics/overview")
            self.assertEqual(missing_response.status_code, 401)
            self.assertEqual(missing_response.json()["detail"], "missing_or_invalid_admin_token")

            wrong_response = self.client.get(
                "/v1/admin/analytics/overview",
                headers={"X-Admin-Token": "wrong-token"},
            )
            self.assertEqual(wrong_response.status_code, 401)

            success_response = self.client.get(
                "/v1/admin/analytics/overview",
                headers={"X-Admin-Token": "secret-admin-token"},
            )
            self.assertEqual(success_response.status_code, 200)

    def test_admin_user_mode_requires_admin_bearer_identity(self) -> None:
        admin_token = self._login("admin_user")
        member_token = self._login("member_user")
        with patch.dict(os.environ, {"ADMIN_API_TOKEN": "", "ADMIN_USER_IDS": "admin_user"}, clear=False):
            missing_response = self.client.get("/v1/admin/analytics/overview")
            self.assertEqual(missing_response.status_code, 401)

            member_response = self.client.get(
                "/v1/admin/analytics/overview",
                headers={"Authorization": f"Bearer {member_token}"},
            )
            self.assertEqual(member_response.status_code, 403)
            self.assertEqual(member_response.json()["detail"], "forbidden_admin_scope")

            admin_response = self.client.get(
                "/v1/admin/analytics/overview",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            self.assertEqual(admin_response.status_code, 200)

    def test_hybrid_mode_accepts_token_or_admin_user(self) -> None:
        admin_token = self._login("hybrid_admin")
        with patch.dict(
            os.environ,
            {"ADMIN_API_TOKEN": "hybrid-token", "ADMIN_USER_IDS": "hybrid_admin"},
            clear=False,
        ):
            token_header_response = self.client.get(
                "/v1/admin/analytics/overview",
                headers={"X-Admin-Token": "hybrid-token"},
            )
            self.assertEqual(token_header_response.status_code, 200)

            bearer_response = self.client.get(
                "/v1/admin/analytics/overview",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            self.assertEqual(bearer_response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
