import unittest

from ai_pr_review_agent.models import Finding
from ai_pr_review_agent.publisher import (
    MARKER,
    publish_review,
    publish_summary,
    render_inline_comment,
    render_summary,
)


class FakeClient:
    def __init__(self, issue_comments=None, review_comments=None):
        self.issue_comments = issue_comments or []
        self.review_comments = review_comments or []
        self.created_summaries = []
        self.updated_summaries = []
        self.reviews = []
        self.updated_inline = []

    def list_issue_comments(self, repository, number):
        return self.issue_comments

    def create_issue_comment(self, repository, number, body):
        self.created_summaries.append(body)
        return {"id": 1}

    def update_issue_comment(self, repository, comment_id, body):
        self.updated_summaries.append((comment_id, body))
        return {"id": comment_id}

    def list_review_comments(self, repository, number):
        return self.review_comments

    def create_review(self, repository, number, head_sha, comments, body):
        self.reviews.append((head_sha, comments, body))
        return {"id": 2}

    def update_review_comment(self, repository, comment_id, body):
        self.updated_inline.append((comment_id, body))
        return {"id": comment_id}


def finding(line=7, severity="medium", confidence=0.9, sha="abc"):
    return Finding(
        "PY001",
        "Bare except",
        severity,
        confidence,
        "app.py",
        line,
        "except:",
        "Catch a specific exception.",
        "RIGHT",
        sha,
    )


def route(item):
    return {"fingerprint": item.fingerprint, "classification": "certain"}


class PublisherTests(unittest.TestCase):
    def test_summary_is_comment_only(self):
        body = render_summary([], [])
        self.assertIn(MARKER, body)
        self.assertIn("No code was changed", body)

    def test_existing_summary_is_updated(self):
        client = FakeClient(issue_comments=[{"id": 7, "body": MARKER}])
        self.assertEqual(publish_summary(client, "o/r", 1, [], []), "updated")
        self.assertEqual(client.updated_summaries[0][0], 7)
        self.assertEqual(client.created_summaries, [])

    def test_inline_payload_uses_right_side_line_and_head_sha(self):
        item = finding()
        client = FakeClient()
        result = publish_review(
            client,
            "o/r",
            1,
            "abc",
            [item],
            [route(item)],
            reviewed_files=1,
            skipped_files=(),
            max_comments=20,
        )
        self.assertEqual(result.posted, 1)
        head_sha, comments, _ = client.reviews[0]
        self.assertEqual(
            (head_sha, comments[0]["path"], comments[0]["line"], comments[0]["side"]),
            ("abc", "app.py", 7, "RIGHT"),
        )

    def test_same_sha_fingerprint_is_not_duplicated(self):
        item = finding()
        body = render_inline_comment(item, "certain")
        client = FakeClient(review_comments=[{"id": 8, "body": body}])
        result = publish_review(
            client,
            "o/r",
            1,
            "abc",
            [item],
            [route(item)],
            reviewed_files=1,
            skipped_files=(),
            max_comments=20,
        )
        self.assertEqual(result.duplicates, 1)
        self.assertEqual(client.reviews, [])

    def test_changed_body_is_updated(self):
        item = finding()
        old_body = render_inline_comment(item, "uncertain")
        client = FakeClient(review_comments=[{"id": 8, "body": old_body}])
        result = publish_review(
            client,
            "o/r",
            1,
            "abc",
            [item],
            [route(item)],
            reviewed_files=1,
            skipped_files=(),
            max_comments=20,
        )
        self.assertEqual(result.updated, 1)
        self.assertEqual(client.updated_inline[0][0], 8)

    def test_cap_prioritizes_high_severity_and_summarizes_overflow(self):
        medium = finding(line=7, severity="medium", confidence=0.99)
        high = finding(line=9, severity="high", confidence=0.8)
        client = FakeClient()
        result = publish_review(
            client,
            "o/r",
            1,
            "abc",
            [medium, high],
            [route(medium), route(high)],
            reviewed_files=1,
            skipped_files=("large.py",),
            max_comments=1,
        )
        self.assertEqual(result.overflow, 1)
        self.assertEqual(client.reviews[0][1][0]["line"], 9)
        self.assertIn("large.py", client.created_summaries[0])
