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


if __name__ == "__main__":
    unittest.main()
