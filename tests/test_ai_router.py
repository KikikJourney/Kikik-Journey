import io
import json
import os
import unittest
from unittest.mock import patch

import ai_router
import opportunity_radar


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

    def test_normalizes_host_endpoint(self):
        with patch.dict(os.environ, {"NINEROUTER_URL": "http://localhost:20128"}, clear=True):
            self.assertEqual(
                ai_router.base_url(),
                "http://localhost:20128/v1/chat/completions",
            )


    def test_openrouter_free_mode_needs_only_api_key(self):
        with patch.dict(
            os.environ,
            {"OPENROUTER_API_KEY": "test-key"},
            clear=True,
        ):
            self.assertTrue(ai_router.configured())
            self.assertEqual(ai_router.base_url(), "https://openrouter.ai/api/v1/chat/completions")
            self.assertEqual(ai_router.model(), "openrouter/free")
            self.assertEqual(ai_router.api_key(), "test-key")

    def test_native_key_and_model_are_supported(self):
        with patch.dict(
            os.environ,
            {
                "NINEROUTER_URL": "https://router.example",
                "NINEROUTER_KEY": "secret",
                "NINEROUTER_MODEL": "test/model",
            },
            clear=True,
        ):
            self.assertEqual(ai_router.api_key(), "secret")
            self.assertEqual(ai_router.model(), "test/model")

    def test_legacy_env_name_is_supported(self):
        with patch.dict(os.environ, {"9ROUTER_BASE_URL": "https://router.example/v1"}, clear=True):
            self.assertTrue(ai_router.configured())


class RouterChatTests(unittest.TestCase):
    def test_chat_parses_openai_response(self):
        response = io.BytesIO(
            json.dumps({
                "choices": [{"message": {"content": "hello"}}]
            }).encode("utf-8")
        )
        with patch.dict(os.environ, {"NINEROUTER_URL": "http://localhost:20128"}, clear=True):
            with patch("ai_router.urlopen", return_value=response):
                self.assertEqual(
                    ai_router.chat([{"role": "user", "content": "hi"}]),
                    "hello",
                )


class EnrichmentTests(unittest.TestCase):
    def test_unconfigured_enrichment_does_not_call_network(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("ai_router.urlopen") as mocked:
                result = opportunity_radar.enrich_with_ai(
                    [{"full_name": "example/repo", "score": 80, "monetizable_offer": "audit",
                      "validation_action": "test", "evidence": {}}]
                )
                self.assertEqual(result["status"], "not_configured")
                self.assertEqual(result["enriched_count"], 0)
                mocked.assert_not_called()
