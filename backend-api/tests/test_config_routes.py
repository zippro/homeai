from __future__ import annotations

import unittest

try:
    from fastapi.testclient import TestClient

    from app.bootstrap import init_database
    from app.main import app

    _CONFIG_ROUTE_TESTS_AVAILABLE = True
except ModuleNotFoundError:
    _CONFIG_ROUTE_TESTS_AVAILABLE = False


@unittest.skipUnless(_CONFIG_ROUTE_TESTS_AVAILABLE, "fastapi dependency is not installed in this environment")
class ConfigRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_database()
        cls.client = TestClient(app)

    def test_bootstrap_config_includes_provider_defaults(self) -> None:
        response = self.client.get("/v1/config/bootstrap")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("provider_defaults", payload)
        provider_defaults = payload["provider_defaults"]
        self.assertIn("default_provider", provider_defaults)
        self.assertIn("fallback_chain", provider_defaults)
        self.assertIn("version", provider_defaults)

    def test_provider_route_preview_returns_selected_provider_and_model(self) -> None:
        response = self.client.get(
            "/v1/config/provider-route-preview?operation=restyle&tier=preview&target_part=full_room"
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["operation"], "restyle")
        self.assertEqual(payload["tier"], "preview")
        self.assertEqual(payload["target_parts"], ["full_room"])
        self.assertIn("selected_provider", payload)
        self.assertIn("selected_model", payload)
        self.assertIsInstance(payload.get("candidate_chain"), list)
        self.assertGreaterEqual(len(payload["candidate_chain"]), 1)
        self.assertEqual(payload["selected_provider"], payload["candidate_chain"][0])


if __name__ == "__main__":
    unittest.main()
