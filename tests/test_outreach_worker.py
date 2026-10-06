import unittest
from outreach_worker import eligible, parse_issue

class OutreachWorkerTests(unittest.TestCase):
    def test_parse_issue(self):
        self.assertEqual(parse_issue("https://github.com/example/project/issues/42"), ("example/project", 42))

    def test_blocks_opt_out_language(self):
        lead = {
            "status":"QUALIFIED",
            "priority_score":90,
            "updated_at":"2099-01-01T00:00:00Z",
            "title":"No solicitation",
            "evidence":"please do not contact",
        }
        self.assertFalse(eligible(lead))

if __name__ == "__main__":
    unittest.main()
