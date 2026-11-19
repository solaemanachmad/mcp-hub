"""Tests for constant-time token verification."""

import unittest

from hub.auth import token_matches


class TestAuth(unittest.TestCase):
    def test_valid_token_matches(self):
        self.assertTrue(token_matches("secret-a", ("secret-a", "secret-b")))
        self.assertTrue(token_matches("secret-b", ("secret-a", "secret-b")))

    def test_invalid_or_empty_token_rejected(self):
        self.assertFalse(token_matches("", ("secret-a",)))
        self.assertFalse(token_matches("wrong", ("secret-a", "secret-b")))
        self.assertFalse(token_matches("secret-a", ("",)))


if __name__ == "__main__":
    unittest.main()
