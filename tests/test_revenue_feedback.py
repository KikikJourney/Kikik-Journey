import json
import tempfile
import unittest
from pathlib import Path

from workers.revenue_feedback import build_feedback, ingest_event_file, ingest_outreach_reports


class RevenueFeedbackTests(unittest.TestCase):
    def test_build_feedback_aggregates_paid_conversion_and_profit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = [
                {"event_id": "out-1", "event_type": "contacted", "source": "public_business_web_signal", "offer": "WooCommerce → Google Sheets Automation", "amount_idr": 0, "cost_idr": 1000},
                {"event_id": "pay-1", "event_type": "paid", "source": "public_business_web_signal", "offer": "WooCommerce → Google Sheets Automation", "amount_idr": 399000, "cost_idr": 0},
                {"event_id": "out-2", "event_type": "contacted", "source": "public_business_web_signal", "offer": "WhatsApp → Google Sheets Mini Automation", "amount_idr": 0, "cost_idr": 1000},
            ]
            result = build_feedback(events)
            wc = result["offers"]["WooCommerce → Google Sheets Automation"]
            self.assertEqual(wc["contacted"], 1)
            self.assertEqual(wc["paid"], 1)
            self.assertEqual(wc["revenue_idr"], 399000)
            self.assertEqual(wc["profit_idr"], 398000)
            self.assertEqual(wc["conversion_rate"], 1.0)
            self.assertGreater(result["policy"]["offer_multipliers"]["WooCommerce → Google Sheets Automation"], 1.0)
            self.assertLess(result["policy"]["offer_multipliers"]["WhatsApp → Google Sheets Mini Automation"], 1.0)

    def test_m3_event_file_feeds_profit_feedback(self):
        events = [{"event_id": "contact-1", "event_type": "contacted", "source": "agentmail", "offer": "validation", "cost_idr": 0}]
        m3 = {"events": [{"event_id": "paid-1", "event_type": "paid", "source": "agentmail", "offer": "validation", "amount_idr": 19000, "cost_idr": 0}]}
        merged = ingest_event_file(m3, events)
        result = build_feedback(merged)
        self.assertEqual(result["totals"]["paid_orders"], 1)
        self.assertEqual(result["totals"]["revenue_idr"], 19000)

    def test_duplicate_event_ids_do_not_inflate_metrics(self):
        events = [
            {"event_id": "x", "event_type": "paid", "source": "s", "offer": "o", "amount_idr": 100, "cost_idr": 0},
            {"event_id": "x", "event_type": "paid", "source": "s", "offer": "o", "amount_idr": 100, "cost_idr": 0},
        ]
        result = build_feedback(events)
        self.assertEqual(result["totals"]["paid_orders"], 1)
        self.assertEqual(result["totals"]["revenue_idr"], 100)

    def test_multiple_outreach_channels_feed_profit_feedback_once(self):
        email_report = {"contacted_leads": [
            {"event_id": "email-1", "source": "public_business_web_signal", "offer": "Workflow Rescue Pilot", "cost_idr": 0}
        ]}
        github_report = {"contacted_leads": [
            {"event_id": "github-1", "source": "github_public_buyer_request", "offer": "Workflow Rescue Pilot", "cost_idr": 0},
            {"event_id": "github-1", "source": "github_public_buyer_request", "offer": "Workflow Rescue Pilot", "cost_idr": 0},
        ]}
        events = ingest_outreach_reports([email_report, github_report], [])
        result = build_feedback(events)
        self.assertEqual(result["totals"]["contacted"], 2)
        self.assertEqual(result["totals"]["events"], 2)
        self.assertEqual(result["sources"]["github_public_buyer_request"]["contacted"], 1)


if __name__ == "__main__":
    unittest.main()
