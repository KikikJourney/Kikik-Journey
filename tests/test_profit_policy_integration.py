import json
import tempfile
import unittest
from pathlib import Path

from workers import business_first_acquisition as acquisition


class ProfitPolicyIntegrationTests(unittest.TestCase):
    def test_policy_multiplier_changes_priority_without_bypassing_qualification(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = acquisition.POLICY
            acquisition.POLICY = Path(tmp) / "profit_policy.json"
            acquisition.POLICY.write_text(json.dumps({
                "offer_multipliers": {"WooCommerce → Google Sheets Automation": 1.4},
                "source_multipliers": {"public_business_web_signal": 1.0},
            }), encoding="utf-8")
            try:
                item = {
                    "title": "Need help automating WooCommerce orders into Google Sheets",
                    "website": "https://example.com",
                    "contact_email": "ops@example.com",
                    "evidence": "We need help automating WooCommerce orders into Google Sheets.",
                    "score": 50,
                }
                lead = acquisition.make_lead(item, "public_business_web_signal")
                self.assertEqual(lead["status"], "QUALIFIED")
                self.assertEqual(lead["feedback_multiplier"], 1.4)
                self.assertEqual(lead["priority_score"], 100)
            finally:
                acquisition.POLICY = old


if __name__ == "__main__":
    unittest.main()
