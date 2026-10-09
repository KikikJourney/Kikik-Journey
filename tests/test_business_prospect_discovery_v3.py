import unittest
from unittest.mock import patch

from workers import business_prospect_discovery_v3 as discovery


class BusinessProspectDiscoveryV3Tests(unittest.TestCase):
    def test_normalize_url_removes_quoted_markdown_title(self):
        raw = (
            "https://community.zapier.com/how-do-i-3/example-53828 "
            '"Mapping contact information between Fergus and Sender: Seeking a solution"'
        )
        self.assertEqual(
            discovery.normalize_url(raw),
            "https://community.zapier.com/how-do-i-3/example-53828",
        )

    def test_normalize_url_rejects_non_http_urls(self):
        self.assertEqual(discovery.normalize_url("not-a-url"), "")
        self.assertEqual(discovery.normalize_url("javascript:alert(1)"), "")

    def test_normalize_url_removes_fragment(self):
        self.assertEqual(
            discovery.normalize_url("https://example.com/path?x=1#frag"),
            "https://example.com/path?x=1",
        )

    def test_read_preserves_original_source_url(self):
        source = "https://community.zapier.com/how-do-i-3/example-53828"
        with patch.object(
            discovery,
            "get",
            return_value=("Title: Example", "https://r.jina.ai/" + source),
        ):
            body, final = discovery.read(source)
        self.assertEqual(body, "Title: Example")
        self.assertEqual(final, source)

    def test_search_strips_markdown_link_title_from_candidate_url(self):
        body = (
            '[Example request](https://example.com/request-1 "Example request")\n'
            'https://example.org/request-2'
        )
        with patch.object(discovery, "read", return_value=(body, "https://example.com")):
            results = discovery.search("test")
        urls = {item["url"] for item in results}
        self.assertIn("https://example.com/request-1", urls)
        self.assertIn("https://example.org/request-2", urls)


    def test_first_ten_queries_include_indonesian_small_business_pain(self):
        first_pass = " ".join(discovery.QUERIES[:10]).lower()
        self.assertIn("umkm", first_pass)
        self.assertIn("toko online", first_pass)
        self.assertIn("pencatatan stok", first_pass)
        self.assertIn("community.make.com", first_pass)

    def test_diagnostics_explain_zero_match_search_runs(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        import json
        import os

        with TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            old_diag = json.loads(json.dumps(discovery.DIAGNOSTICS))
            try:
                os.chdir(tmp)
                discovery.DIAGNOSTICS.update({
                    "queries_attempted": 0, "search_targets_attempted": 0,
                    "search_targets_with_content": 0, "search_targets_failed_or_empty": 0,
                    "links_seen": 0, "content_pages_read": 0, "content_pages_empty": 0,
                    "pages_rejected_no_buyer_evidence": 0, "reject_no_request_context": 0,
                    "reject_no_intent": 0, "reject_no_pain": 0, "reject_no_offer_fit": 0,
                    "reject_no_business_context": 0, "pages_with_buyer_evidence": 0,
                    "direct_business_emails_found": 0, "per_query": [],
                })
                with patch.object(discovery, "search", side_effect=[[{
                    "title": "Generic help", "url": "https://example.com/help"
                }]] + [[]] * (len(discovery.QUERIES) - 1)), patch.object(
                    discovery, "inspect", return_value=None
                ):
                    discovery.main()
                payload = json.loads(Path("business_prospects.json").read_text())
                self.assertEqual(payload["count"], 0)
                self.assertEqual(payload["diagnostics"]["queries_attempted"], 10)
                self.assertEqual(len(payload["diagnostics"]["per_query"]), 10)
            finally:
                discovery.DIAGNOSTICS.update(old_diag)
                os.chdir(old_cwd)

    def test_rejected_pages_do_not_consume_domain_prospect_quota(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        import json
        import os

        with TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            old_diag = json.loads(json.dumps(discovery.DIAGNOSTICS))
            candidates = [
                {"title": f"Request {i}", "url": f"https://example.com/request-{i}"}
                for i in range(5)
            ]
            valid_hit = {
                "title": "Request 4", "website": candidates[4]["url"],
                "contact_email": "sales@example.com", "actionable": True,
            }
            try:
                os.chdir(tmp)
                discovery.DIAGNOSTICS.update({
                    "queries_attempted": 0, "search_targets_attempted": 0,
                    "search_targets_with_content": 0, "search_targets_failed_or_empty": 0,
                    "links_seen": 0, "content_pages_read": 0, "content_pages_empty": 0,
                    "pages_rejected_no_buyer_evidence": 0, "reject_no_request_context": 0,
                    "reject_no_intent": 0, "reject_no_pain": 0, "reject_no_offer_fit": 0,
                    "reject_no_business_context": 0, "pages_with_buyer_evidence": 0,
                    "direct_business_emails_found": 0, "per_query": [],
                })
                with patch.object(
                    discovery, "search",
                    side_effect=[candidates] + [[]] * (len(discovery.QUERIES) - 1),
                ), patch.object(
                    discovery, "inspect",
                    side_effect=[None, None, None, None, valid_hit],
                ):
                    discovery.main()
                payload = json.loads(Path("business_prospects.json").read_text())
                self.assertEqual(payload["count"], 1)
                self.assertEqual(payload["prospects"][0]["contact_email"], "sales@example.com")
                self.assertEqual(payload["diagnostics"]["per_query"][0]["unique_pages_inspected"], 5)
            finally:
                discovery.DIAGNOSTICS.update(old_diag)
                os.chdir(old_cwd)

    def test_community_guideline_boilerplate_is_not_buyer_evidence(self):
        import json

        body = (
            "Title: Mastering the Make Community: Get Started. "
            "Our mission is to build a safe, productive, and welcoming space. "
            "Help others help you. Share knowledge, not sales pitches. "
            "Do not self-promote outside the designated Hire a Pro areas. "
            "This is a space for learning, not a marketplace."
        )
        old_diag = json.loads(json.dumps(discovery.DIAGNOSTICS))
        discovery.DIAGNOSTICS["reject_no_intent"] = 0
        try:
            with patch.object(
                discovery, "read",
                return_value=(body, "https://community.make.com/t/make-community-the-ultimate-guide/11682"),
            ):
                result = discovery.inspect({
                    "title": "Start here",
                    "url": "https://community.make.com/t/make-community-the-ultimate-guide/11682",
                }, "community guide query")
            self.assertIsNone(result)
            self.assertGreaterEqual(discovery.DIAGNOSTICS["reject_no_intent"], 1)
        finally:
            discovery.DIAGNOSTICS.update(old_diag)

    def test_rejects_generic_help_and_login_pages(self):
        self.assertFalse(discovery.is_candidate_page({
            "title": "How Do I...?",
            "url": "https://community.zapier.com/how-do-i-3",
        }))
        self.assertFalse(discovery.is_candidate_page({
            "title": "Log in",
            "url": "https://community.zapier.com/ssoproxy/login",
        }))

    def test_accepts_specific_public_discussion_topic(self):
        self.assertTrue(discovery.is_candidate_page({
            "title": "Mapping contact information between tools: seeking a solution",
            "url": "https://community.zapier.com/how-do-i-3/example-53828",
        }))

    def test_rejects_featured_article_even_if_url_looks_like_topic(self):
        self.assertFalse(discovery.is_candidate_page({
            "title": "How do you decide which apps to integrate with?",
            "url": "https://community.zapier.com/featured-articles-65/how-do-you-decide-which-app-s-to-integrate-with-9617",
        }))

    def test_rejects_generic_community_category_even_if_body_has_keywords(self):
        with patch.object(discovery, "read", return_value=(
            "Have a question? Get help. Automate your business with Google Sheets.",
            "https://community.zapier.com/how-do-i-3",
        )) as reader:
            result = discovery.inspect({
                "title": "How Do I...?",
                "url": "https://community.zapier.com/how-do-i-3",
            }, "test")
        self.assertIsNone(result)
        reader.assert_not_called()



if __name__ == "__main__":
    unittest.main()
