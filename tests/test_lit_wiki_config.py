import tempfile
import textwrap
import unittest
from pathlib import Path

from lit_wiki.config import load_config


class TestConfigResolution(unittest.TestCase):
    def test_resolves_family_task_models_for_fallbacks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "config.yaml").write_text(
                textwrap.dedent(
                    """
                    provider:
                      families:
                        openai:
                          label: "OpenAI"
                          provider: "openai"
                          task_models:
                            default: "gpt-5-nano"
                            extraction: "gpt-5-mini"
                            summary: "gpt-5.4"
                          models:
                            gpt-5.4: "gpt-5.4"
                            gpt-5-mini: "gpt-5-mini"
                            gpt-5-nano: "gpt-5-nano"
                        gemini:
                          label: "Gemini"
                          provider: "google"
                          task_models:
                            default: "gemini-3.1-flash-lite-preview"
                            extraction: "gemini-3-flash-preview"
                            summary: "gemini-3.1-pro-preview"
                          models:
                            gemini-3.1-pro-preview: "gemini-3.1-pro-preview"
                            gemini-3-flash-preview: "gemini-3-flash-preview"
                            gemini-3.1-flash-lite-preview: "gemini-3.1-flash-lite-preview"
                      fallbacks:
                        - name: "openai_summary"
                          family: "openai"
                          task_model: "summary"
                        - name: "gemini_extraction"
                          family: "gemini"
                          task_model: "extraction"
                    """
                ),
                encoding="utf-8",
            )
            config = load_config(root)

        self.assertEqual(config.fallback_providers[0].backend, "openai")
        self.assertEqual(config.fallback_providers[0].model, "gpt-5.4")
        self.assertEqual(config.fallback_providers[1].backend, "gemini")
        self.assertEqual(config.fallback_providers[1].model, "gemini-3-flash-preview")
