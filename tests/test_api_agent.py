import io
import unittest
import urllib.error
from unittest.mock import patch

from tools.api_agent import normalize_api_key, normalize_model, open_with_retry


class ApiAgentConfigTests(unittest.TestCase):
    def test_api_key_trims_trailing_newlines_and_spaces(self):
        self.assertEqual(normalize_api_key("  test-key\n\r "), "test-key")

    def test_api_key_rejects_empty_value_after_trimming(self):
        with self.assertRaises(ValueError):
            normalize_api_key(" \n ")

    def test_model_defaults_when_variable_is_blank(self):
        self.assertEqual(normalize_model(" \n "), "gemini-3.5-flash-lite")

    def test_model_trims_whitespace(self):
        self.assertEqual(normalize_model("  gemini-test  "), "gemini-test")

    def test_transient_503_is_retried(self):
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        unavailable = urllib.error.HTTPError(
            "https://example.invalid", 503, "unavailable", {}, io.BytesIO(b"")
        )
        with patch("tools.api_agent.time.sleep"), patch(
            "tools.api_agent.urllib.request.urlopen",
            side_effect=[unavailable, Response()],
        ) as mocked:
            result = open_with_retry(object(), attempts=3)
        self.assertIsInstance(result, Response)
        self.assertEqual(mocked.call_count, 2)


    def test_action_parser_accepts_only_allowlisted_json_action(self):
        from tools.api_agent import parse_decision

        decision = parse_decision(
            '{"action":"run_full_business_cycle","reason":"No recent full cycle","evidence":["M1 stale"]}'
        )
        self.assertEqual(decision["action"], "run_full_business_cycle")

    def test_action_parser_rejects_unknown_action(self):
        from tools.api_agent import parse_decision

        with self.assertRaises(ValueError):
            parse_decision('{"action":"run_shell_command","reason":"bad","evidence":[]}')

    def test_action_parser_rejects_non_json_model_output(self):
        from tools.api_agent import parse_decision

        with self.assertRaises(ValueError):
            parse_decision("I recommend running the workflow.")

    def test_workflow_dispatch_is_restricted_to_allowlist(self):
        from tools.api_agent import dispatch_workflow

        with self.assertRaises(ValueError):
            dispatch_workflow("run_arbitrary_code", "token", "owner/repo")

    def test_full_cycle_recency_guard_blocks_recent_success(self):
        from tools.api_agent import action_allowed

        self.assertFalse(action_allowed(
            "run_full_business_cycle",
            {"last_full_cycle_age_hours": 4},
            manual=False,
        ))

    def test_full_cycle_recency_guard_allows_stale_cycle(self):
        from tools.api_agent import action_allowed

        self.assertTrue(action_allowed(
            "run_full_business_cycle",
            {"last_full_cycle_age_hours": 30},
            manual=False,
        ))

    def test_manual_task_can_request_full_cycle(self):
        from tools.api_agent import action_allowed

        self.assertTrue(action_allowed(
            "run_full_business_cycle",
            {"last_full_cycle_age_hours": 4},
            manual=True,
        ))


if __name__ == "__main__":
    unittest.main()
