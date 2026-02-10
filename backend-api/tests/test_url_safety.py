from __future__ import annotations

import unittest

from app.url_safety import validate_external_http_url


class UrlSafetyTests(unittest.TestCase):
    def test_public_ip_url_is_allowed(self) -> None:
        validate_external_http_url("https://8.8.8.8/sample.jpg")

    def test_private_ip_url_is_rejected(self) -> None:
        with self.assertRaises(ValueError) as context:
            validate_external_http_url("http://127.0.0.1/sample.jpg")
        self.assertEqual(str(context.exception), "image_url_non_public_target")

    def test_non_http_scheme_is_rejected(self) -> None:
        with self.assertRaises(ValueError) as context:
            validate_external_http_url("file:///tmp/image.jpg")
        self.assertEqual(str(context.exception), "image_url_invalid_scheme")


if __name__ == "__main__":
    unittest.main()
