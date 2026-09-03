import unittest

from ai_pr_review_agent.genesis import load_state, validate_state


class GenesisTests(unittest.TestCase):
    def test_repository_state_is_valid(self):
        self.assertEqual(validate_state(load_state()), [])

    def test_complete_requires_evidence(self):
        state = load_state()
        state["milestones"][0] = {**state["milestones"][0], "status": "complete", "evidence": []}
        self.assertTrue(any("no evidence" in item for item in validate_state(state)))
