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


if __name__ == "__main__":
    unittest.main()
