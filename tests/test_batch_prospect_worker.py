import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workers.batch_prospect_worker import build_payload, main


class BatchProspectWorkerTests(unittest.TestCase):
    def test_payload_shape(self):
        payload = build_payload(
            {"title": "Need automation", "url": "https://example.com", "evidence": "manual reporting"},
            [{"name": "Workflow Rescue Pilot"}],
        )
        self.assertEqual(payload["buyer_request"]["title"], "Need automation")
        self.assertEqual(payload["offers"][0]["name"], "Workflow Rescue Pilot")

    def test_main_handles_worker_failure_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "report.json"
            output = root / "output.json"
            report.write_text(
                json.dumps({"buyer_requests": [{"title": "Need automation", "url": "https://example.com", "evidence": "manual"}]}),
                encoding="utf-8",
            )
            with patch("sys.argv", ["batch", "--input", str(report), "--output", str(output)]),                  patch("subprocess.run") as run:
                run.return_value.returncode = 1
                run.return_value.stdout = ""
                run.return_value.stderr = "worker failed"
                main()
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["reject"], 1)


if __name__ == "__main__":
    unittest.main()
