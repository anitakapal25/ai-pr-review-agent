import unittest

from ai_pr_review_agent.publisher import MARKER, publish_summary, render_summary


class FakeClient:
    def __init__(self, comments=None):
        self.comments = comments or []
        self.created = []
        self.updated = []

    def list_issue_comments(self, repository, number):
        return self.comments

    def create_issue_comment(self, repository, number, body):
        self.created.append(body)
        return {"id": 1}

    def update_issue_comment(self, repository, comment_id, body):
        self.updated.append((comment_id, body))
        return {"id": comment_id}


class PublisherTests(unittest.TestCase):
    def test_summary_is_comment_only(self):
        body = render_summary([], [])
        self.assertIn(MARKER, body)
        self.assertIn("No code was changed", body)

    def test_existing_summary_is_updated(self):
        client = FakeClient([{"id": 7, "body": MARKER}])
        self.assertEqual(publish_summary(client, "o/r", 1, [], []), "updated")
        self.assertEqual(client.updated[0][0], 7)
        self.assertEqual(client.created, [])
