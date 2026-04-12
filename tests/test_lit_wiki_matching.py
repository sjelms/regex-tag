import plistlib
import tempfile
import textwrap
import unittest
import zipfile
from pathlib import Path

from lit_wiki.bibliography import parse_bibliography
from lit_wiki.matching import match_source, parse_pdf_filename


class TestDeterministicMatching(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        bib_text = textwrap.dedent(
            """
            @ARTICLE{Fickett1996-aa,
              title = {Finding genes by computer - the state of the art},
              author = {Fickett, James W},
              date = {1996},
              abstract = {Abstract text.}
            }

            @BOOK{Daniels2013-pa,
              title = {Example EPUB Source},
              author = {Daniels, Harry and Edwards, Anne},
              date = {2013}
            }
            """
        )
        self.bib_path = self.root / "regex-tag.bib"
        self.bib_path.write_text(bib_text, encoding="utf-8")
        self.bibliography = parse_bibliography(self.bib_path)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_matches_markdown_citation_key(self):
        md_path = self.root / "source.md"
        md_path.write_text(
            textwrap.dedent(
                """
                ---
                citation-key: Fickett1996-aa
                ---
                Body text.
                """
            ).strip(),
            encoding="utf-8",
        )
        result = match_source(md_path, self.bibliography)
        self.assertEqual(result.citekey, "Fickett1996-aa")
        self.assertFalse(result.needs_review)

    def test_matches_pdf_filename(self):
        pdf_path = self.root / "Finding genes by computer - the state of the art_Fickett_1996.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")
        self.assertEqual(
            parse_pdf_filename(pdf_path),
            ("Finding genes by computer - the state of the art", ["Fickett"], "1996"),
        )
        result = match_source(pdf_path, self.bibliography)
        self.assertEqual(result.citekey, "Fickett1996-aa")

    def test_matches_epub_metadata_plist(self):
        epub_path = self.root / "source.epub"
        plist_bytes = plistlib.dumps(
            {"artistName": "Harry Daniels, Anne Edwards, Daniels2013-pa"}
        )
        with zipfile.ZipFile(epub_path, "w") as archive:
            archive.writestr("iTunesMetadata.plist", plist_bytes)
            archive.writestr("OPS/chapter1.xhtml", "<html><body><p>Hello</p></body></html>")

        result = match_source(epub_path, self.bibliography)
        self.assertEqual(result.citekey, "Daniels2013-pa")
        self.assertFalse(result.needs_review)

