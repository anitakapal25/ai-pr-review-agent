import unittest

from ai_pr_review_agent.router import classify_finding, route_finding


class RouterTests(unittest.TestCase):
    def test_low_confidence_requires_human(self):
        finding = {"title": "Suspicious pattern", "confidence": 0.1,
                   "reviewer_notes": "uncertain", "evidence_chain": ["app.py", 1, "x"]}
        self.assertEqual(classify_finding(finding)[0], "uncertain")
        self.assertTrue(route_finding(finding)["requires_human"])

    def test_confidence_never_grants_auto_apply(self):
        finding = {"title": "Clear style issue", "confidence": 0.99,
                   "reviewer_notes": "clear evidence", "evidence_chain": ["app.py", 1, "x"]}
        route = route_finding(finding)
        self.assertEqual(route["classification"], "certain")
        self.assertFalse(route["auto_apply"])
