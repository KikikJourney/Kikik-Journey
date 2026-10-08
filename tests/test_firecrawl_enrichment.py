import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from workers import firecrawl_enrichment as f

class FirecrawlEnrichmentTests(unittest.TestCase):
    def test_public_url_rejects_local_destinations(self):
        self.assertFalse(f._public_url("http://localhost:8000/x"))
        self.assertFalse(f._public_url("http://127.0.0.1/x"))
        with patch.object(f.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
            self.assertTrue(f._public_url("https://example.com"))

    def test_missing_key_is_fail_open(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); inp=root/"business.json"; report=root/"report.json"
            inp.write_text(json.dumps({"prospects":[{"website":"https://example.com"}]}),encoding="utf-8")
            with patch.object(f,"INPUT",str(inp)),patch.object(f,"REPORT",str(report)),patch.object(f,"KEY",""):
                f.main()
            self.assertEqual(json.loads(report.read_text())["status"],"disabled_missing_secret")

    def test_scrape_contract_reads_markdown(self):
        response={"success":True,"data":{"markdown":"# Example","metadata":{"title":"Example","sourceURL":"https://example.com"}}}
        with patch.object(f,"urlopen") as opener:
            class Ctx:
                def __enter__(self): return self
                def __exit__(self,*args): pass
                def read(self): return json.dumps(response).encode()
            opener.return_value=Ctx()
            with patch.object(f,"_public_url",return_value=True),patch.object(f,"KEY","fc-test"):
                result=f.scrape("https://example.com")
        self.assertEqual(result["title"],"Example")
        self.assertEqual(result["markdown_excerpt"],"# Example")

if __name__=="__main__":
    unittest.main()
