import unittest

from ai_pr_review_agent.models import ChangedFile, PullRequest
from ai_pr_review_agent.reviewer import added_lines, review_pull_request


class ReviewerTests(unittest.TestCase):
    def test_added_lines_track_new_file_numbers(self):
        patch = "@@ -4,2 +4,3 @@\n old\n-removed\n+except:\n+token = 'abcdefgh'"
        self.assertEqual(list(added_lines(patch)), [(5, "except:"), (6, "token = 'abcdefgh'")])

    def test_review_uses_added_lines_only(self):
        pr = PullRequest(
            "o/r",
            1,
            "t",
            "",
            "base",
            "head",
            "url",
            (ChangedFile("app.py", "modified", 1, 1, "@@ -1 +1 @@\n-except:\n+print('ok')"),),
        )
        self.assertEqual(review_pull_request(pr), [])

    def test_finding_has_exact_evidence(self):
        pr = PullRequest(
            "o/r",
            1,
            "t",
            "",
            "base",
            "head",
            "url",
            (ChangedFile("app.py", "modified", 1, 0, "@@ -0,0 +10 @@\n+except:"),),
        )
        finding = review_pull_request(pr)[0]
        self.assertEqual((finding.path, finding.line, finding.rule_id), ("app.py", 10, "PY001"))
