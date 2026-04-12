import tempfile
import textwrap
import unittest
from pathlib import Path

from lit_wiki.config import load_config
from lit_wiki.registry import SourceRegistry
from lit_wiki.service import extract_source, ingest_source, process_watch_folder, register_source, sync_bibliography


class TestServiceWorkflow(unittest.TestCase):
    def _write_template(self, root: Path) -> None:
        (root / "specs").mkdir()
        (root / "specs" / "lit-note-template.md").write_text(
            Path("specs/lit-note-template.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    def _write_basic_bib(self, root: Path) -> None:
        (root / "regex-tag.bib").write_text(
            textwrap.dedent(
                """
                @ARTICLE{Fickett1996-aa,
                  title = {Finding genes by computer - the state of the art},
                  author = {Fickett, James W},
                  date = {1996},
                  abstract = {Gene finding is surveyed in this article.}
                }
                """
            ),
            encoding="utf-8",
        )

    def test_markdown_register_extract_and_ingest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_template(root)
            self._write_basic_bib(root)
            source_path = root / "input.md"
            source_path.write_text(
                textwrap.dedent(
                    """
                    ---
                    citation-key: Fickett1996-aa
                    ---
                    Finding genes by computer is discussed in detail.
                    """
                ).strip(),
                encoding="utf-8",
            )
            config = load_config(root)
            bibliography = sync_bibliography(config)
            self.assertEqual(len(bibliography.entries), 1)

            record, match = register_source(config, source_path)
            self.assertEqual(record.citekey, "Fickett1996-aa")
            self.assertEqual(match.reason, "markdown citation-key")

            extracted = extract_source(config, "Fickett1996-aa")
            self.assertTrue(Path(extracted.extracted_path).exists())

            note_path = ingest_source(config, "Fickett1996-aa")
            self.assertEqual(note_path.name, "Fickett1996-aa_wiki.md")
            note_text = note_path.read_text(encoding="utf-8")
            self.assertIn('key: "[[@Fickett1996-aa]]"', note_text)
            self.assertIn('type: "[[@article]]"', note_text)
            self.assertTrue((root / "wiki" / "index.md").exists())

    def test_watch_folder_archives_success_and_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_template(root)
            self._write_basic_bib(root)
            (root / "config.yaml").write_text(
                textwrap.dedent(
                    """
                    show_completion_dialog: false
                    watch_dir: "watch"
                    """
                ),
                encoding="utf-8",
            )
            watch_dir = root / "watch"
            watch_dir.mkdir()
            (watch_dir / "valid.md").write_text(
                textwrap.dedent(
                    """
                    ---
                    citation-key: Fickett1996-aa
                    ---
                    Finding genes by computer is discussed in detail.
                    """
                ).strip(),
                encoding="utf-8",
            )
            (watch_dir / "invalid.md").write_text(
                textwrap.dedent(
                    """
                    ---
                    citation-key: Missing1999-xx
                    ---
                    Unknown source.
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(root)
            summary = process_watch_folder(config)

            self.assertEqual(summary.success_count, 1)
            self.assertEqual(summary.fail_count, 1)
            self.assertTrue((root / "watch" / "processed" / "valid.md").exists())
            self.assertTrue((root / "watch" / "other" / "invalid.md").exists())
            self.assertTrue((root / "wiki" / "sources" / "Fickett1996-aa_wiki.md").exists())

            registry = SourceRegistry.load(config.registry_file)
            record = registry.get("Fickett1996-aa")
            self.assertIsNotNone(record)
            assert record is not None
            self.assertTrue(record.source_path.endswith("watch/processed/valid.md"))

    def test_watch_folder_requests_fallback_and_approves_one_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_template(root)
            self._write_basic_bib(root)
            (root / "config.yaml").write_text(
                textwrap.dedent(
                    """
                    show_completion_dialog: false
                    watch_dir: "watch"
                    provider:
                      primary:
                        backend: "openai_compatible"
                        model: "local-model"
                        api_base: ""
                      fallbacks:
                        - name: "fallback_api"
                          backend: "heuristic"
                          model: "fallback-model"
                      approval:
                        required: true
                        default_decision: "approve"
                      budget:
                        max_input_chars_per_request: 2000
                        max_output_tokens_per_request: 500
                        max_requests_per_file: 2
                        max_tokens_per_file: 4000
                        max_tokens_per_day: 10000
                    """
                ),
                encoding="utf-8",
            )
            watch_dir = root / "watch"
            watch_dir.mkdir()
            (watch_dir / "needs_fallback.md").write_text(
                textwrap.dedent(
                    """
                    ---
                    citation-key: Fickett1996-aa
                    ---
                    Finding genes by computer is discussed in detail.
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(root)
            summary = process_watch_folder(config)
            self.assertEqual(summary.success_count, 1)
            self.assertTrue((root / "watch" / "processed" / "needs_fallback.md").exists())
            record = SourceRegistry.load(config.registry_file).get("Fickett1996-aa")
            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(record.approval_decision, "approve")
            self.assertEqual(record.provider, "fallback_api")
            self.assertEqual(record.processing_state, "ingested")
            self.assertTrue(config.budget_ledger_file.exists())

    def test_watch_folder_skips_when_approval_denied(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_template(root)
            self._write_basic_bib(root)
            (root / "config.yaml").write_text(
                textwrap.dedent(
                    """
                    show_completion_dialog: false
                    watch_dir: "watch"
                    provider:
                      primary:
                        backend: "openai_compatible"
                        model: "local-model"
                        api_base: ""
                      fallbacks:
                        - name: "fallback_api"
                          backend: "heuristic"
                          model: "fallback-model"
                      approval:
                        required: true
                        default_decision: "skip"
                    """
                ),
                encoding="utf-8",
            )
            watch_dir = root / "watch"
            watch_dir.mkdir()
            (watch_dir / "needs_skip.md").write_text(
                textwrap.dedent(
                    """
                    ---
                    citation-key: Fickett1996-aa
                    ---
                    Finding genes by computer is discussed in detail.
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(root)
            summary = process_watch_folder(config)
            self.assertEqual(summary.issue_count, 1)
            self.assertTrue((root / "watch" / "other" / "needs_skip.md").exists())
            record = SourceRegistry.load(config.registry_file).get("Fickett1996-aa")
            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(record.processing_state, "needs_review")
            self.assertEqual(record.approval_decision, "skip")

    def test_daily_budget_blocks_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_template(root)
            self._write_basic_bib(root)
            (root / "config.yaml").write_text(
                textwrap.dedent(
                    """
                    show_completion_dialog: false
                    watch_dir: "watch"
                    provider:
                      primary:
                        backend: "openai_compatible"
                        model: "local-model"
                        api_base: ""
                      fallbacks:
                        - name: "fallback_api"
                          backend: "heuristic"
                          model: "fallback-model"
                      approval:
                        required: true
                        default_decision: "approve"
                      budget:
                        max_input_chars_per_request: 2000
                        max_output_tokens_per_request: 500
                        max_requests_per_file: 2
                        max_tokens_per_file: 4000
                        max_tokens_per_day: 10
                    """
                ),
                encoding="utf-8",
            )
            watch_dir = root / "watch"
            watch_dir.mkdir()
            (watch_dir / "blocked.md").write_text(
                textwrap.dedent(
                    """
                    ---
                    citation-key: Fickett1996-aa
                    ---
                    Finding genes by computer is discussed in detail.
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(root)
            summary = process_watch_folder(config)
            self.assertEqual(summary.issue_count, 1)
            self.assertTrue((root / "watch" / "other" / "blocked.md").exists())

    def test_keyword_catalogue_enriches_tags_and_see_also(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_template(root)
            self._write_basic_bib(root)
            (root / "unambiguous-keywords.csv").write_text(
                "Alias,LinkTarget,Clusters\nCLT,Cognitive Load Theory (CLT),education-learning\n",
                encoding="utf-8",
            )
            (root / "config.yaml").write_text(
                textwrap.dedent(
                    """
                    keywords:
                      enabled: true
                      unambiguous_csv: "unambiguous-keywords.csv"
                      mode: "guidance_enrichment"
                    """
                ),
                encoding="utf-8",
            )
            source_path = root / "input.md"
            source_path.write_text(
                textwrap.dedent(
                    """
                    ---
                    citation-key: Fickett1996-aa
                    ---
                    CLT is mentioned as an important idea in this source.
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(root)
            sync_bibliography(config)
            register_source(config, source_path)
            extract_source(config, "Fickett1996-aa")
            note_path = ingest_source(config, "Fickett1996-aa")
            note_text = note_path.read_text(encoding="utf-8")
            self.assertIn('"[[Cognitive Load Theory (CLT)]]"', note_text)
            self.assertIn('"education-learning"', note_text)
