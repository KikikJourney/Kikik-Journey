import unittest
from workers import business_first_acquisition as a

class BusinessFirstAcquisitionTests(unittest.TestCase):
    def test_business_signal_is_qualified(self):
        item = {
            "title": "Need help automating WooCommerce orders into Google Sheets",
            "website": "https://example.com",
            "contact_email": "ops@example.com",
            "evidence": "Our ecommerce store manually copies WooCommerce orders into Google Sheets. We need help automating this.",
            "score": 60,
            "commercial_intent": 2,
            "reachability": "direct_email",
        }
        lead = a.make_lead(item, "public_business_web_signal")
        self.assertEqual(lead["status"], "QUALIFIED")
        self.assertTrue(lead["auto_contact_eligible"])

    def test_github_buyer_request_is_qualified_but_not_email_auto_contact(self):
        item = {
            "title": "Need help fixing CI automation",
            "url": "https://github.com/acme/project/issues/1",
            "evidence": "We need a developer to fix our failing automation workflow.",
            "score": 75,
        }
        lead = a.make_lead(item, "public_buyer_request")
        self.assertEqual(lead["status"], "QUALIFIED")
        self.assertFalse(lead["auto_contact_eligible"])

    def test_research_artifact_is_watch(self):
        item = {
            "title": "Automation research report",
            "website": "https://example.com",
            "contact_email": "ops@example.com",
            "evidence": "Our research report is a roadmap for automation. This is discussion only.",
            "score": 80,
        }
        lead = a.make_lead(item, "public_business_web_signal")
        self.assertEqual(lead["status"], "WATCH")
        self.assertFalse(lead["auto_contact_eligible"])

if __name__ == "__main__":
    unittest.main()
