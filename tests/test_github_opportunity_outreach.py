import unittest
from unittest.mock import patch
import workers.github_opportunity_outreach as go


class GitHubOutreachTests(unittest.TestCase):
    def lead(self, **extra):
        base = {
            "status": "QUALIFIED",
            "source": "public_buyer_request",
            "url": "https://github.com/acme/shop/issues/7",
            "matched_offer": "Workflow Rescue Pilot",
            "checkout_path": "sales/manual_order.html?offer=workflow",
            "priority_score": 90,
            "title": "Need help fixing automation workflow",
            "evidence": "Our workflow is failing and we need a developer.",
        }
        base.update(extra)
        return base

    def test_default_outreach_cap_is_three(self):
        self.assertEqual(go.MAX_PER_RUN, 3)

    def test_ineligible_source_is_skipped(self):
        self.assertFalse(go.eligible(self.lead(source="public_business_web_signal")))

    @patch("workers.github_opportunity_outreach.api")
    def test_github_discovery_is_independent(self, api):
        api.return_value = {
            "items": [{
                "html_url": "https://github.com/acme/shop/issues/7",
                "title": "Need help fixing automation workflow",
                "body": "We are looking to hire a freelancer for a paid project to fix our failing automation workflow; please send a quote.",
                "updated_at": "2026-10-08T00:00:00Z",
            }]
        }
        leads = go.search_buyer_requests()
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["source"], "public_buyer_request")
        self.assertIn("github.com/acme/shop/issues/7", leads[0]["url"])

    @patch("workers.github_opportunity_outreach.api")
    def test_inactive_repo_is_skipped(self, api):
        api.return_value = {
            "archived": False, "disabled": False,
            "pushed_at": "2025-01-01T00:00:00Z"
        }
        active, age, status = go.activity("acme/shop")
        self.assertFalse(active)
        self.assertGreater(age, go.ACTIVE_DAYS)
        self.assertEqual(status, "inactive")

    def test_checkout_is_attributed(self):
        url = go.checkout_url(self.lead(), "acme/shop", 7)
        self.assertIn("source=github-outreach", url)
        self.assertIn("repo=acme/shop", url)
        self.assertIn("issue=7", url)

    def test_contacted_event_is_stable_and_attributed(self):
        first = go.contacted_event(self.lead(), "acme/shop", 7, "2026-10-09T00:00:00+00:00")
        replay = go.contacted_event(self.lead(), "acme/shop", 7, "2026-10-09T00:00:00+00:00")
        second = go.contacted_event(self.lead(), "acme/shop", 7, "2026-10-10T00:00:00+00:00")
        self.assertEqual(first["event_id"], replay["event_id"])
        self.assertNotEqual(first["event_id"], second["event_id"])
        self.assertEqual(first["source"], "github_public_buyer_request")
        self.assertEqual(first["offer"], "Workflow Rescue Pilot")
        self.assertEqual(first["occurred_at"], "2026-10-09T00:00:00+00:00")

    def test_generic_technical_issue_is_not_a_commercial_buyer(self):
        lead = self.lead()
        self.assertFalse(go.eligible(lead))
        lead["evidence"] = "We are looking to hire a freelancer for a paid project to fix our failing automation workflow."
        self.assertTrue(go.eligible(lead))

    @patch("workers.github_opportunity_outreach.api")
    def test_already_contacted_checks_later_comment_pages(self, api):
        api.side_effect = [
            [{"body": f"ordinary comment {i}"} for i in range(100)],
            [{"body": f"reply {i}"} for i in range(99)] + [{"body": go.MARKER}],
        ]
        self.assertTrue(go.already_contacted("acme/shop", 7))
        self.assertEqual(api.call_count, 2)
        self.assertIn("since=", api.call_args_list[0].args[0])
        self.assertIn("page=2", api.call_args_list[1].args[0])

    @patch("workers.github_opportunity_outreach.api")
    def test_buyer_discovery_rejects_noncommercial_technical_requests(self, api):
        api.return_value = {
            "items": [{
                "html_url": "https://github.com/acme/shop/issues/7",
                "title": "Need help fixing automation workflow",
                "body": "We need a developer because our workflow is failing.",
                "updated_at": "2026-10-08T00:00:00Z",
            }]
        }
        self.assertEqual(go.search_buyer_requests(), [])


if __name__ == "__main__":
    unittest.main()
