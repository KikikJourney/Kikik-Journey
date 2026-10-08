import unittest
from workers import postiz_publisher as p

class PostizPublisherTests(unittest.TestCase):
    def test_fingerprint_is_stable(self):
        self.assertEqual(p.fingerprint("hello   world"),p.fingerprint("hello world"))
    def test_missing_configuration_is_disabled(self):
        self.assertFalse(p.KEY)
        self.assertEqual(len(p.CONTENT),6)
    def test_content_contains_central_checkout(self):
        for _,content in p.CONTENT:
            self.assertIn("kikikjourney.github.io/Kikik-Journey/sales/manual-order.html",content)

if __name__=="__main__":
    unittest.main()
