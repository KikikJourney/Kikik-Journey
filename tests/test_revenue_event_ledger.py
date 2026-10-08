import json
import tempfile
import unittest
from pathlib import Path

from workers.revenue_event_ledger import append_events, load_events


class RevenueEventLedgerTests(unittest.TestCase):
    def test_append_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.json"
            event = {"event_id": "paid-abc", "event_type": "paid", "offer": "validation", "amount_idr": 19000}
            added, _ = append_events([event], path)
            added_again, events = append_events([event], path)
            self.assertEqual(added, 1)
            self.assertEqual(added_again, 0)
            self.assertEqual(len(events), 1)
            self.assertEqual(load_events(path)[0]["event_id"], "paid-abc")


if __name__ == "__main__":
    unittest.main()
