import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from ai_pr_review_agent.github import GitHubClient, GitHubError


class GitHubTests(unittest.TestCase):
    def test_repository_validation(self):
        self.assertEqual(GitHubClient.validate_repository("openai/example"), "openai/example")
        for value in ("owner", "../repo", "owner/repo/extra", "owner/repo?x=1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                GitHubClient.validate_repository(value)

    def test_http_errors_are_not_silently_swallowed(self):
        client = GitHubClient("test-token", retries=0)
        error = HTTPError("https://api.github.com/test", 403, "Forbidden", {}, None)
        with (
            patch("ai_pr_review_agent.github.urlopen", side_effect=error),
            self.assertRaisesRegex(GitHubError, "HTTP 403"),
        ):
            client._request("GET", "/test")

    def test_network_error_is_reported(self):
        client = GitHubClient("test-token", retries=0)
        with (
            patch("ai_pr_review_agent.github.urlopen", side_effect=URLError("offline")),
            self.assertRaisesRegex(GitHubError, "failed or timed out"),
        ):
            client._request("GET", "/test")

    def test_malformed_pull_response_fails_closed(self):
        client = GitHubClient("test-token")
        with (
            patch.object(client, "_request", return_value={"title": "missing refs"}),
            self.assertRaisesRegex(GitHubError, "invalid pull request"),
        ):
            client.get_pull_request("owner/repo", 1)
