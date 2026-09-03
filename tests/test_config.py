import tempfile
import unittest
from pathlib import Path

from ai_pr_review_agent.config import ReviewConfig, load_config


class ConfigTests(unittest.TestCase):
    def test_missing_config_uses_bounded_defaults(self):
        self.assertEqual(load_config(Path("missing.yaml"), workflow_max=7).max_inline_comments, 7)

    def test_repository_config_cannot_raise_workflow_cap(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.yaml"
            path.write_text("max_inline_comments: 40\nenabled_rules: [PY001]\n", encoding="utf-8")
            config = load_config(path, workflow_max=12)
        self.assertEqual(config.max_inline_comments, 12)
        self.assertEqual(config.enabled_rules, frozenset({"PY001"}))

    def test_invalid_config_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.yaml"
            path.write_text("unknown_option: true\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(path)

    def test_defaults_are_valid(self):
        self.assertEqual(ReviewConfig().max_inline_comments, 20)
