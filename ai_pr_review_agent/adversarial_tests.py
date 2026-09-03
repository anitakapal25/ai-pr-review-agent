"""Backward-compatible adversarial suite; tests never mutate the repository."""

import unittest

from ai_pr_review_agent.models import ChangedFile, PullRequest
from ai_pr_review_agent.reviewer import review_pull_request
from ai_pr_review_agent.router import classify_finding, route_finding


class AdversarialTests(unittest.TestCase):
    def test_removed_vulnerability_is_not_reported(self):
        pr = PullRequest(
            "o/r",
            1,
            "",
            "",
            "b",
            "h",
            "",
            (
                ChangedFile(
                    "app.py",
                    "modified",
                    1,
                    1,
                    "@@ -1 +1 @@\n-token = 'abcdefgh'\n+token = os.environ['TOKEN']",
                ),
            ),
        )
        self.assertEqual(review_pull_request(pr), [])

    def test_untrusted_comment_does_not_create_secret_finding(self):
        pr = PullRequest(
            "o/r",
            1,
            "",
            "",
            "b",
            "h",
            "",
            (
                ChangedFile(
                    "app.py", "modified", 1, 0, "@@ -0,0 +1 @@\n+# password = 'not-a-secret'"
                ),
            ),
        )
        self.assertEqual(review_pull_request(pr), [])

    def test_low_confidence_escalates(self):
        finding = {
            "title": "Suspicious pattern",
            "severity": "low",
            "confidence": 0.1,
            "evidence_chain": ["app.py", 1, "x"],
            "reviewer_notes": "uncertain",
        }
        self.assertEqual(classify_finding(finding)[0], "uncertain")
        self.assertTrue(route_finding(finding)["requires_human"])

    def test_confidence_never_grants_auto_apply(self):
        finding = {
            "title": "Clear style issue",
            "severity": "low",
            "confidence": 0.99,
            "evidence_chain": ["app.py", 1, "x"],
            "reviewer_notes": "clear evidence",
        }
        self.assertFalse(route_finding(finding)["auto_apply"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
