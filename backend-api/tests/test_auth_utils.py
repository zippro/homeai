from __future__ import annotations

import unittest

from app.auth_utils import parse_bearer_token


class AuthUtilsTests(unittest.TestCase):
    def test_parse_bearer_token_accepts_valid(self) -> None:
        token = parse_bearer_token("Bearer abc123")
        self.assertEqual(token, "abc123")

    def test_parse_bearer_token_is_case_insensitive(self) -> None:
        token = parse_bearer_token("bearer abc123")
        self.assertEqual(token, "abc123")

    def test_parse_bearer_token_rejects_other_scheme(self) -> None:
        self.assertIsNone(parse_bearer_token("Basic xyz"))

    def test_parse_bearer_token_rejects_missing_token(self) -> None:
        self.assertIsNone(parse_bearer_token("Bearer    "))

    def test_parse_bearer_token_rejects_none(self) -> None:
        self.assertIsNone(parse_bearer_token(None))


if __name__ == "__main__":
    unittest.main()
