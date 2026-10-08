import json
import tempfile
import unittest
from pathlib import Path

from workers.revenue_feedback import build_feedback


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

    def test_duplicate_event_ids_do_not_inflate_metrics(self):
        events = [
            {"event_id": "x", "event_type": "paid", "source": "s", "offer": "o", "amount_idr": 100, "cost_idr": 0},
            {"event_id": "x", "event_type": "paid", "source": "s", "offer": "o", "amount_idr": 100, "cost_idr": 0},
        ]
        result = build_feedback(events)
        self.assertEqual(result["totals"]["paid_orders"], 1)
        self.assertEqual(result["totals"]["revenue_idr"], 100)


if __name__ == "__main__":
    unittest.main()
