import unittest
from workers import business_prospect_discovery_v3 as d


class BusinessProspectDiscoveryTests(unittest.TestCase):
    def test_explicit_buyer_request_is_classified(self):
        item = {"title": "Need help automating WooCommerce orders into Google Sheets"}
        result = d.classify(
            item,
            "Our ecommerce store manually copies orders into Google Sheets. "
            "We need help automating this workflow."
        )
        _, business, pain, intent, offer_hits, offer, request_context = result
        self.assertGreaterEqual(business, 1)
        self.assertGreaterEqual(pain, 1)
        self.assertGreaterEqual(intent, 1)
        self.assertGreaterEqual(offer_hits, 1)
        self.assertEqual(offer, "WooCommerce → Google Sheets Automation")
        self.assertTrue(request_context)

    def test_provider_without_buyer_intent_is_not_classified(self):
        item = {"title": "WooCommerce to Google Sheets automation service"}
        result = d.classify(
            item,
            "We build WooCommerce to Google Sheets automation for businesses."
        )
        _, _, _, intent, _, _, request_context = result
        self.assertEqual(intent, 0)
        self.assertFalse(request_context)

    def test_query_text_is_not_used_as_evidence(self):
        item = {"title": "Automation service"}
        result = d.classify(
            item,
            "Our company provides workflow automation services."
        )
        _, _, _, intent, _, _ = result
        self.assertEqual(intent, 0)


if __name__ == "__main__":
    unittest.main()
