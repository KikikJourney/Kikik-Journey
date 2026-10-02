import io
import json
import unittest
from unittest.mock import patch

import opportunity_radar


class RadarDeterminismTests(unittest.TestCase):
    def test_radar_module_has_no_external_ai_dependency(self):
        self.assertFalse(hasattr(opportunity_radar, "enrich_with_ai"))

    def test_candidate_scoring_is_deterministic(self):
        repo = {
            "full_name": "example/repo",
            "description": "automation workflow",
            "stargazers_count": 100,
            "forks_count": 10,
            "open_issues_count": 3,
            "language": "Python",
            "topics": ["automation"],
            "pushed_at": "2026-10-01T00:00:00Z",
            "homepage": None,
            "license": {"spdx": "MIT"},
            "html_url": "https://github.com/example/repo",
        }
        issues = [{"title": "deployment is difficult", "body": "manual setup", "html_url": "https://github.com/example/repo/issues/1"}]
        first = opportunity_radar.build_candidate(repo, "production integration setup", issues)
        second = opportunity_radar.build_candidate(repo, "production integration setup", issues)
        self.assertEqual(first, second)
        self.assertNotIn("ai_enrichment", first)

    def test_deterministic_helpers_remain_available(self):
        self.assertEqual(opportunity_radar.license_state({"license": {"spdx": "MIT"}}), "PERMISSIVE:MIT")

if __name__ == "__main__":
    unittest.main()
