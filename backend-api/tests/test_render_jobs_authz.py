from __future__ import annotations

import unittest

try:
    from fastapi.testclient import TestClient
    from sqlalchemy import delete

    from app.bootstrap import init_database
    from app.db import session_scope
    from app.main import app
    from app.models import AuthSessionModel, CreditBalanceModel, CreditLedgerEntryModel, RenderJobModel, UserProjectModel

    _RENDER_AUTH_TESTS_AVAILABLE = True
except ModuleNotFoundError:
    _RENDER_AUTH_TESTS_AVAILABLE = False


@unittest.skipUnless(_RENDER_AUTH_TESTS_AVAILABLE, "fastapi/sqlalchemy dependency is not installed")
class RenderJobsAuthzTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_database()
        cls.client = TestClient(app)

    def setUp(self) -> None:
        with session_scope() as session:
            session.execute(delete(UserProjectModel))
            session.execute(delete(RenderJobModel))
            session.execute(delete(CreditLedgerEntryModel))
            session.execute(delete(CreditBalanceModel))
            session.execute(delete(AuthSessionModel))

    def _login(self, user_id: str) -> str:
        response = self.client.post(
            "/v1/auth/login-dev",
            json={"user_id": user_id, "platform": "tests", "ttl_hours": 24},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["access_token"]

    def _grant_credits(self, user_id: str, token: str, amount: int = 20) -> None:
        response = self.client.post(
            "/v1/credits/grant",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": user_id, "amount": amount, "reason": "tests"},
        )
        self.assertEqual(response.status_code, 200)

    def _create_preview_job(self, user_id: str, token: str, project_id: str) -> str:
        response = self.client.post(
            "/v1/ai/render-jobs",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_id": user_id,
                "platform": "tests",
                "project_id": project_id,
                "image_url": "https://8.8.8.8/demo.jpg",
                "style_id": "modern",
                "operation": "restyle",
                "tier": "preview",
                "target_parts": ["full_room"],
                "prompt_overrides": {},
            },
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["id"]

    def test_render_job_create_requires_authentication(self) -> None:
        response = self.client.post(
            "/v1/ai/render-jobs",
            json={
                "user_id": "render_auth_user",
                "platform": "tests",
                "project_id": "render_auth_project",
                "image_url": "https://8.8.8.8/demo.jpg",
                "style_id": "modern",
                "operation": "restyle",
                "tier": "preview",
                "target_parts": ["full_room"],
                "prompt_overrides": {},
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_render_job_status_and_cancel_are_owner_scoped(self) -> None:
        owner_token = self._login("render_owner")
        other_token = self._login("render_other")
        self._grant_credits("render_owner", owner_token)

        job_id = self._create_preview_job("render_owner", owner_token, "render_owner_project")

        status_response = self.client.get(
            f"/v1/ai/render-jobs/{job_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        self.assertEqual(status_response.status_code, 404)

        cancel_response = self.client.post(
            f"/v1/ai/render-jobs/{job_id}/cancel",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        self.assertEqual(cancel_response.status_code, 404)

    def test_render_job_rejects_private_image_url(self) -> None:
        token = self._login("render_url_guard")
        self._grant_credits("render_url_guard", token)

        response = self.client.post(
            "/v1/ai/render-jobs",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_id": "render_url_guard",
                "platform": "tests",
                "project_id": "render_guard_project",
                "image_url": "http://127.0.0.1/private.jpg",
                "style_id": "modern",
                "operation": "restyle",
                "tier": "preview",
                "target_parts": ["full_room"],
                "prompt_overrides": {},
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "image_url_non_public_target")


if __name__ == "__main__":
    unittest.main()
