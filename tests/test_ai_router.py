import os
import unittest
from unittest.mock import patch

import ai_router


class RouterConfigTests(unittest.TestCase):
    def test_unconfigured_is_safe(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(ai_router.configured())
            self.assertIsNone(ai_router.base_url())

    def test_normalizes_v1_endpoint(self):
        with patch.dict(os.environ, {"AI_ROUTER_BASE_URL": "http://localhost:20128/v1/"}, clear=True):
            self.assertEqual(
                ai_router.base_url(),
                "http://localhost:20128/v1/chat/completions",
            )

    def test_legacy_env_name_is_supported(self):
        with patch.dict(os.environ, {"9ROUTER_BASE_URL": "https://router.example/v1"}, clear=True):
            self.assertTrue(ai_router.configured())


if __name__ == "__main__":
    unittest.main()
