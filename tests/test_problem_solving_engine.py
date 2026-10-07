import unittest
from workers.problem_solving_engine import solve, build_customer_message

class ProblemSolvingEngineTests(unittest.TestCase):
    def test_automation_problem_gets_diagnosis(self):
        r = solve("Workflow broken", "My Zapier workflow is not firing and Google Sheets stays empty. Error: unauthorized.")
        self.assertEqual(r["category"], "automation")
        self.assertEqual(r["status"], "DIAGNOSIS_READY")
        self.assertTrue(r["hypotheses"])
        self.assertTrue(r["verification"])

    def test_secret_request_is_safety_escalation(self):
        r = solve("Login issue", "Please use my password and OTP to fix the account.")
        self.assertEqual(r["status"], "ESCALATE_SAFETY")
        self.assertTrue(r["safety_flags"])
        self.assertNotIn("password", r["customer_message"].lower())

    def test_vague_problem_requests_evidence(self):
        r = solve("Help", "It doesn't work.")
        self.assertEqual(r["status"], "NEEDS_EVIDENCE")
        self.assertTrue(r["missing_information"])

    def test_payment_is_not_claimed_paid_from_text(self):
        r = solve("Payment", "I paid the invoice with USDT on BEP-20.")
        self.assertEqual(r["category"], "payment")
        self.assertTrue(r["policy"]["no_unverified_completion_claims"])

if __name__ == "__main__":
    unittest.main()
