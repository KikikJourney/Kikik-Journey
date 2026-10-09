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
