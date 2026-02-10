from __future__ import annotations

import os
import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient

    from app.bootstrap import init_database
    from app.main import app

    _STYLE_ROUTE_TESTS_AVAILABLE = True
except ModuleNotFoundError:
    _STYLE_ROUTE_TESTS_AVAILABLE = False


@unittest.skipUnless(_STYLE_ROUTE_TESTS_AVAILABLE, "fastapi dependency is not installed in this environment")
class StyleCatalogRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_database()
        cls.client = TestClient(app)

    def test_public_styles_returns_seeded_active_styles(self) -> None:
        response = self.client.get("/v1/styles")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsInstance(payload, list)
        self.assertGreaterEqual(len(payload), 1)
        self.assertIn("style_id", payload[0])
        self.assertIn("prompt", payload[0])
        self.assertTrue(all(item.get("is_active", False) for item in payload))

    def test_admin_style_crud_flow(self) -> None:
        style_id = "qa_style_crud"
        body = {
            "display_name": "QA Style CRUD",
            "prompt": "Editorial interior with warm light and structured composition.",
            "thumbnail_url": "https://picsum.photos/id/1084/900/900",
            "is_active": True,
            "tags": ["qa", "editorial"],
            "room_types": ["living_room", "bedroom"],
            "sort_order": 404,
        }

        with patch.dict(
            os.environ,
            {"APP_ENV": "development", "ADMIN_API_TOKEN": "", "ADMIN_USER_IDS": ""},
            clear=False,
        ):
            put_response = self.client.put(f"/v1/admin/styles/{style_id}?actor=test_suite&reason=crud", json=body)
            self.assertEqual(put_response.status_code, 200)
            put_payload = put_response.json()
            self.assertEqual(put_payload["style_id"], style_id)
            self.assertEqual(put_payload["display_name"], body["display_name"])

            list_response = self.client.get("/v1/admin/styles?active_only=false")
            self.assertEqual(list_response.status_code, 200)
            styles = list_response.json()
            self.assertTrue(any(item["style_id"] == style_id for item in styles))

            delete_response = self.client.delete(f"/v1/admin/styles/{style_id}?actor=test_suite&reason=cleanup")
            self.assertEqual(delete_response.status_code, 200)
            self.assertEqual(delete_response.json(), {"deleted": True})

        missing_response = self.client.get(f"/v1/styles/{style_id}")
        self.assertEqual(missing_response.status_code, 404)
        self.assertEqual(missing_response.json()["detail"], "style_not_found")


if __name__ == "__main__":
    unittest.main()

