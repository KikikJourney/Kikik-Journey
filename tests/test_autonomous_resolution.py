import unittest
from unittest.mock import patch
from workers.autonomous_resolution import (
    ActionRegistry, ActionResult, build_plan, resolve, public_url_probe
)


class AutonomousResolutionTests(unittest.TestCase):
    def test_public_url_probe_uses_correct_url_parser(self):
        self.assertEqual(build_plan({
            "category": "website",
            "evidence": ["public_url:https://example.com/path"],
        })["actions"][0]["id"], "public_url_probe")

    def test_private_address_is_blocked(self):
        with self.assertRaises(Exception):
            public_url_probe("http://127.0.0.1/")

    def test_unknown_write_adapter_fails_closed(self):
        result = resolve({"category": "automation", "evidence": ["error_signal:not working"]})
        self.assertEqual(result["status"], "ESCALATED")
        self.assertFalse(result["verification"]["verified"])
        self.assertTrue(result["policy"]["writes_require_registered_adapter"])

    def test_successful_read_only_action_is_verified(self):
        registry = ActionRegistry()
        registry.register(
            "public_url_probe",
            lambda **kwargs: ActionResult(
                "public_url_probe", "EXECUTED",
                {"url": kwargs["url"], "status_code": 200}
            ),
        )
        result = resolve({
            "category": "website",
            "evidence": ["public_url:https://example.com"],
        }, registry=registry)
        self.assertEqual(result["status"], "RESOLVED")
        self.assertTrue(result["verification"]["verified"])

    def test_retryable_failure_retries_once_then_recovers(self):
        calls = {"n": 0}
        registry = ActionRegistry()

        def flaky(**kwargs):
            calls["n"] += 1
            return ActionResult(
                "public_url_probe",
                "FAILED",
                {"url": kwargs["url"], "status_code": 503},
                retryable=True,
                message="temporary outage",
            )

        registry.register("public_url_probe", flaky)
        result = resolve({
            "category": "website",
            "evidence": ["public_url:https://example.com"],
        }, registry=registry, max_retries=1)
        self.assertEqual(calls["n"], 2)
        self.assertEqual(result["status"], "RECOVERY_REQUIRED")
        self.assertFalse(result["verification"]["verified"])


if __name__ == "__main__":
    unittest.main()
