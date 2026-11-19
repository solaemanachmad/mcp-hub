"""Tests for hybrid local storage backend."""

import tempfile
import unittest

from hub.storage import LocalStorage


class TestStorage(unittest.TestCase):
    def test_save_load_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalStorage(tmp)
            key = "papers/general/sample.pdf"
            self.assertFalse(store.exists(key))
            store.save(key, b"%PDF-1.4 test")
            self.assertTrue(store.exists(key))
            self.assertEqual(store.load(key), b"%PDF-1.4 test")


if __name__ == "__main__":
    unittest.main()
