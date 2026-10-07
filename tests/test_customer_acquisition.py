import unittest

import customer_acquisition as ca

class CustomerAcquisitionTests(unittest.TestCase):
    def test_woocommerce_offer_match(self):
        offer = ca.match_offer("Need WooCommerce orders sent to Google Sheets")
        self.assertEqual(offer["name"], "WooCommerce → Google Sheets Automation")

    def test_whatsapp_offer_match(self):
        offer = ca.match_offer("Looking for WhatsApp messages into Google Sheets")
        self.assertEqual(offer["name"], "WhatsApp → Google Sheets Mini Automation")


    def test_research_artifact_is_not_a_buyer(self):
        item = {
            "title": "Market & Tech Review",
            "evidence": "Research report about workflow automation and integrations.",
            "score": 100,
        }
        score, status = ca.qualify(item)
        self.assertEqual(status, "WATCH")

    def test_explicit_workflow_request_is_a_buyer(self):
        item = {
            "title": "Need help fixing my n8n workflow",
            "evidence": "I need a developer to fix my automation and integrate it with Google Sheets.",
            "score": 50,
        }
        score, status = ca.qualify(item)
        self.assertEqual(status, "QUALIFIED")

    def test_roadmap_issue_is_not_a_buyer(self):
        item = {
            "title": "Automation Roadmap",
            "evidence": "Roadmap and backlog for future integrations; no contractor requested.",
            "score": 100,
        }
        score, status = ca.qualify(item)
        self.assertEqual(status, "WATCH")

    def test_no_external_ai_dependency(self):
        source = open("customer_acquisition.py", encoding="utf-8").read()
        self.assertNotIn("openai", source.lower())
        self.assertNotIn("anthropic", source.lower())

if __name__ == "__main__":
    unittest.main()
