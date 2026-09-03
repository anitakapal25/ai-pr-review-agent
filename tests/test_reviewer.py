import unittest

from ai_pr_review_agent.config import ReviewConfig
from ai_pr_review_agent.models import ChangedFile, PullRequest
from ai_pr_review_agent.reviewer import (
    added_lines,
    analyze_pull_request,
    review_pull_request,
    validate_findings,
)


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
        self.assertEqual(finding.side, "RIGHT")
        self.assertEqual(finding.head_sha, "head")

    def test_multiple_hunks_and_deletions_track_new_lines(self):
        patch = "@@ -1,2 +1,2 @@\n-old\n+new\n context\n@@ -20 +20,2 @@\n keep\n+except:"
        self.assertEqual(list(added_lines(patch)), [(1, "new"), (21, "except:")])

    def test_missing_patch_is_reported_as_skipped(self):
        pr = PullRequest(
            "o/r",
            1,
            "",
            "",
            "base",
            "head",
            "",
            (ChangedFile("large.py", "modified", 100, 20, None),),
        )
        result = analyze_pull_request(pr)
        self.assertEqual(result.skipped_files, ("large.py",))
        self.assertEqual(result.reviewed_files, 0)

    def test_excluded_and_disabled_rules_are_not_reported(self):
        pr = PullRequest(
            "o/r",
            1,
            "",
            "",
            "base",
            "head",
            "",
            (
                ChangedFile("vendor/app.py", "modified", 1, 0, "@@ -0,0 +1 @@\n+except:"),
                ChangedFile("app.py", "modified", 1, 0, "@@ -0,0 +1 @@\n+except:"),
            ),
        )
        config = ReviewConfig(frozenset({"SEC001"}), ("vendor/**",), 20)
        self.assertEqual(analyze_pull_request(pr, config).findings, ())

    def test_finding_not_on_added_line_fails_closed(self):
        pr = PullRequest(
            "o/r",
            1,
            "",
            "",
            "base",
            "head",
            "",
            (ChangedFile("app.py", "modified", 1, 0, "@@ -0,0 +5 @@\n+except:"),),
        )
        invalid = review_pull_request(pr)[0]
        invalid = invalid.__class__(
            invalid.rule_id,
            invalid.title,
            invalid.severity,
            invalid.confidence,
            invalid.path,
            6,
            invalid.evidence,
            invalid.reviewer_notes,
            invalid.side,
            invalid.head_sha,
        )
        with self.assertRaisesRegex(ValueError, "invalid evidence"):
            validate_findings(pr, [invalid])
