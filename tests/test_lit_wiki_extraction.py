import unittest

from lit_wiki.extraction import _clean_extracted_text


class TestExtractionCleanup(unittest.TestCase):
    def test_removes_jstor_boilerplate_and_nuls(self):
        raw = (
            "This content downloaded from \n"
            "\x00\x00\x0086.163.107.4 on Thu, 09 Apr 2026 13:55:37 UTC\x00\x00\n"
            "All use subject to https://about.jstor.org/terms\n"
            "\n"
            "On Two Metaphors for Learning\n"
            "The article text remains.\n"
        )
        cleaned = _clean_extracted_text(raw)
        self.assertNotIn("\x00", cleaned)
        self.assertNotIn("This content downloaded from", cleaned)
        self.assertNotIn("All use subject to https://about.jstor.org/terms", cleaned)
        self.assertIn("On Two Metaphors for Learning", cleaned)
        self.assertIn("The article text remains.", cleaned)
