import unittest

from workers.prospect_worker import validate_result
from workers.batch_prospect_worker import DEFAULT_OFFERS, buyer_gate, guarded_result


class T(unittest.TestCase):
    def setUp(self):
        self.p = {"offers": [{"name": "A"}, {"name": "B"}]}

    def v(self):
        return {
            "decision": "QUALIFIED",
            "confidence": 90,
            "problem": "x",
            "buyer_type": "y",
            "matched_offer": "A",
            "priority": 80,
            "evidence": ["x"],
            "missing_information": ["z"],
            "reason": "x",
            "next_validation": "x",
        }

    def test_valid(self):
        validate_result(self.v(), self.p)

    def test_bad_offer(self):
        r = self.v()
        r["matched_offer"] = "C"
        with self.assertRaises(ValueError):
            validate_result(r, self.p)

    def test_missing_offer(self):
        r = self.v()
        r["matched_offer"] = None
        with self.assertRaises(ValueError):
            validate_result(r, self.p)

    def test_research_report_is_not_buyer(self):
        request = {
            "title": "Market & Tech Review - 2026-10-07",
            "evidence": "Research report on automation and integration trends.",
        }
        gate = buyer_gate(request, DEFAULT_OFFERS[2])
        self.assertFalse(gate["allowed"])

    def test_explicit_workflow_need_can_pass_gate(self):
        request = {
            "title": "Need help fixing my n8n workflow",
            "evidence": "I need help with a manual workflow and want an implementation.",
        }
        gate = buyer_gate(request, DEFAULT_OFFERS[2])
        self.assertTrue(gate["allowed"])

    def test_guard_downgrades_false_positive(self):
        request = {
            "title": "Roadmap",
            "evidence": "Research roadmap for an integration program.",
        }
        result = self.v()
        result["matched_offer"] = "Workflow Rescue Pilot"
        result["priority"] = 90
        guarded = guarded_result(result, request, DEFAULT_OFFERS)
        self.assertEqual(guarded["decision"], "WATCH")
        self.assertLessEqual(guarded["priority"], 59)


if __name__ == "__main__":
    unittest.main()
