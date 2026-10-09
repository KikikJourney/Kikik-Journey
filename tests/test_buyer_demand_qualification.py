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
                    "body": (
                        "We are looking to hire a freelancer for a paid project to automate this manual process. "
                        "Our team manually copies orders and this is error-prone."
                    ),
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

    @patch("opportunity_radar.api")
    def test_research_digest_and_generic_agent_issue_never_qualify(self, api):
        now = datetime.now(timezone.utc).isoformat()
        api.return_value = {
            "items": [
                {
                    "html_url": "https://github.com/acme/lens/issues/9700",
                    "title": "Scheduled Agent: lens",
                    "body": "Looking for a workflow to automate agent operations.",
                    "repository_url": "https://api.github.com/repos/acme/lens",
                    "updated_at": now,
                },
                {
                    "html_url": "https://github.com/acme/research/issues/26",
                    "title": "Market & Tech Review - 2026-09-28",
                    "body": (
                        "Looking to hire a freelancer for a paid project to automate a manual workflow."
                    ),
                    "repository_url": "https://api.github.com/repos/acme/research",
                    "updated_at": now,
                },
                {
                    "html_url": "https://github.com/acme/tool/issues/3",
                    "title": "Not looking to hire a developer",
                    "body": "We are not looking to hire a developer for our automation workflow.",
                    "repository_url": "https://api.github.com/repos/acme/tool",
                    "updated_at": now,
                },
            ]
        }
        requests, failures = search_buyer_requests()
        self.assertEqual(failures, [])
        by_url = {item["url"]: item for item in requests}
        self.assertEqual(by_url["https://github.com/acme/lens/issues/9700"]["demand_status"], "WATCH")
        self.assertEqual(by_url["https://github.com/acme/research/issues/26"]["demand_status"], "WATCH")
        self.assertNotEqual(by_url["https://github.com/acme/tool/issues/3"]["demand_status"], "QUALIFIED_REQUEST")

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
