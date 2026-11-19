"""Tests for built-in PDF text chunking."""

import unittest

from hub.services.pdf import chunk_text


class TestPdf(unittest.TestCase):
    def test_chunk_text_empty(self):
        self.assertEqual(chunk_text(""), [])
        self.assertEqual(chunk_text("   \n\t  "), [])

    def test_chunk_text_overlap_and_bounds(self):
        text = "Sentence one. " * 200
        chunks = chunk_text(text, chunk_size=300, overlap=50)
        self.assertGreater(len(chunks), 5)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 305)
            self.assertGreater(len(chunk), 0)

    def test_invalid_overlap_raises(self):
        with self.assertRaises(ValueError):
            chunk_text("hello world", chunk_size=100, overlap=100)


if __name__ == "__main__":
    unittest.main()
