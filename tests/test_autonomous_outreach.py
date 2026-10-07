import unittest
from unittest.mock import patch

import workers.autonomous_outreach as ao


class AutonomousOutreachTests(unittest.TestCase):
    def test_issue_ref_accepts_github_issue(self):
        self.assertEqual(
            ao.issue_ref("https://github.com/acme/project/issues/42"),
            ("acme/project", 42),
        )

    def test_issue_ref_rejects_non_issue_url(self):
        self.assertIsNone(ao.issue_ref("https://example.com/request/42"))

    def test_eligible_requires_qualified_buyer_request(self):
        base = {
            "status": "QUALIFIED",
            "source": "public_buyer_request",
            "url": "https://github.com/acme/project/issues/42",
            "matched_offer": "Workflow Rescue Pilot",
            "checkout_path": "sales/checkout.html?offer=workflow",
        }
        self.assertTrue(ao.eligible(base))
        base["status"] = "WATCH"
        self.assertFalse(ao.eligible(base))

    def test_comment_contains_marker_and_checkout(self):
        lead = {
            "title": "Need workflow automation",
            "matched_offer": "Workflow Rescue Pilot",
            "checkout_path": "sales/checkout.html?offer=workflow",
        }
        body = ao.comment_body(lead)
        self.assertIn(ao.MARKER, body)
        self.assertIn("offer=workflow", body)

    def test_send_one_is_deduplicated(self):
        lead = {
            "status": "QUALIFIED",
            "source": "public_buyer_request",
            "url": "https://github.com/KikikJourney/Kikik-Journey/issues/42",
            "matched_offer": "Workflow Rescue Pilot",
            "checkout_path": "sales/checkout.html?offer=workflow",
        }
        with patch.object(ao, "already_contacted", return_value=True), patch.object(ao, "api") as api:
            self.assertEqual(ao.send_one(lead), "already_contacted")
            api.assert_not_called()


if __name__ == "__main__":
    unittest.main()
