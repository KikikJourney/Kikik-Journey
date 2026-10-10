import json
import tempfile
import unittest
from pathlib import Path

from workers.gemini_business_intelligence import (
    build_prompt, compact_payload, normalize_key, run, validate_result,
)


class GeminiBusinessIntelligenceTests(unittest.TestCase):
    def test_missing_key_skips_without_failing_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input.json"
            output = Path(tmp) / "out.json"
            source.write_text('{"opportunities":[{"title":"Example"}]}', encoding="utf-8")
            result = run("opportunity", source, output, api_key="")
            self.assertEqual(result["status"], "skipped_no_key")
            self.assertTrue(output.exists())
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["recommendations"], [])

    def test_api_quota_failure_is_recorded_as_fallback_not_raised(self):
        def failing_request(*args):
            raise RuntimeError("429 quota exceeded")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input.json"
            output = Path(tmp) / "out.json"
            source.write_text('{"leads":[]}', encoding="utf-8")
            result = run("acquisition", source, output, api_key="test-key", request_fn=failing_request)
            self.assertEqual(result["status"], "fallback_error")
            self.assertIn("429", result["data_quality_notes"][0])

    def test_valid_gemini_result_is_saved_with_schema(self):
        response = {
            "summary": "Buyer intent evidence is limited.",
            "recommendations": [{
                "priority": "high", "action": "Validate the stated need",
                "evidence": "One public request mentions the workflow.",
                "metric": "Confirmed replies"
            }],
            "data_quality_notes": []
        }
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input.json"
            output = Path(tmp) / "out.json"
            source.write_text('{"leads":[{"title":"Need automation"}]}', encoding="utf-8")
            result = run("acquisition", source, output, api_key="test-key", request_fn=lambda *args: response)
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["recommendations"][0]["priority"], "high")
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["status"], "ok")

    def test_invalid_recommendations_are_filtered(self):
        result = validate_result({
            "summary": "Summary",
            "recommendations": [{"priority": "critical", "action": "Bypass gate", "evidence": "x", "metric": "y"}],
            "data_quality_notes": []
        })
        self.assertEqual(result["recommendations"], [])

    def test_prompt_keeps_deterministic_outreach_gate_authoritative(self):
        prompt = build_prompt("acquisition", '{"leads":[]}')
        self.assertIn("Do not authorize outreach", prompt)
        self.assertIn("deterministic repository gates remain authoritative", prompt)

    def test_payload_is_bounded_and_stage_specific(self):
        payload = {"leads": [{"title": "A"}], "private_unrelated": "x" * 1000}
        compact = compact_payload(payload, "acquisition", max_chars=100)
        self.assertLessEqual(len(compact), 120)
        self.assertIn("leads", compact)
        self.assertNotIn("private_unrelated", compact)

    def test_api_key_whitespace_is_normalized(self):
        self.assertEqual(normalize_key(" key\n"), "key")
        self.assertEqual(normalize_key("  "), "")


if __name__ == "__main__":
    unittest.main()
