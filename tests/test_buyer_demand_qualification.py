import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from opportunity_radar import search_buyer_requests
from opportunity_packager import build_demand_item


class BuyerDemandQualificationTests(unittest.TestCase):
    @patch("opportunity_radar.api")
    def test_explicit_request_and_pain_rank_before_generic_issue(self, api):
        now = datetime.now(timezone.utc).isoformat()
        api.return_value = {
            "items": [
                {
                    "html_url": "https://github.com/acme/shop/issues/1",
                    "title": "Need help automating WooCommerce orders into Google Sheets",
                    "body": "Our team manually copies orders and this is error-prone.",
                    "repository_url": "https://api.github.com/repos/acme/shop",
                    "updated_at": now,
                },
                {
                    "html_url": "https://github.com/acme/tool/issues/2",
                    "title": "Automation workflow question",
                    "body": "What is the best workflow for this setup?",
                    "repository_url": "https://api.github.com/repos/acme/tool",
                    "updated_at": now,
                },
            ]
        }

        requests, failures = search_buyer_requests()

        self.assertEqual(failures, [])
        self.assertEqual(requests[0]["demand_status"], "QUALIFIED_REQUEST")
        self.assertIn("need help", requests[0]["intent_evidence"])
        self.assertIn("manual", requests[0]["pain_evidence"])
        self.assertEqual(requests[1]["demand_status"], "WATCH")

    def test_demand_item_maps_known_offer_and_preserves_validation_not_sale(self):
        item = build_demand_item(
            {
                "demand_status": "QUALIFIED_REQUEST",
                "title": "Need help automating WooCommerce orders into Google Sheets",
                "url": "https://github.com/acme/shop/issues/1",
                "evidence": "Our team manually copies orders.",
                "score": 80,
                "intent_evidence": ["need help"],
                "pain_evidence": ["manual"],
            },
            1,
        )
        self.assertEqual(item["matched_offer"], "WooCommerce → Google Sheets Automation")
        self.assertEqual(item["price_idr"], 399000)
        self.assertIn("consent", item["next_step"])
        self.assertIn("sale", item["next_step"])
        self.assertEqual(item["status"], "QUALIFIED_REQUEST")


if __name__ == "__main__":
    unittest.main()
