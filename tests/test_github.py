import unittest

from ai_pr_review_agent.github import GitHubClient


class GitHubTests(unittest.TestCase):
    def test_repository_validation(self):
        self.assertEqual(GitHubClient.validate_repository("openai/example"), "openai/example")
        for value in ("owner", "../repo", "owner/repo/extra", "owner/repo?x=1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                GitHubClient.validate_repository(value)
