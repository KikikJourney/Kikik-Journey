import unittest

from tools.api_agent import normalize_api_key, normalize_model


class ApiAgentConfigTests(unittest.TestCase):
    def test_api_key_trims_trailing_newlines_and_spaces(self):
        self.assertEqual(normalize_api_key("  test-key\n\r "), "test-key")

    def test_api_key_rejects_empty_value_after_trimming(self):
        with self.assertRaises(ValueError):
            normalize_api_key(" \n ")

    def test_model_defaults_when_variable_is_blank(self):
        self.assertEqual(normalize_model(" \n "), "gemini-2.5-flash-lite")

    def test_model_trims_whitespace(self):
        self.assertEqual(normalize_model("  gemini-test  "), "gemini-test")


if __name__ == "__main__":
    unittest.main()
