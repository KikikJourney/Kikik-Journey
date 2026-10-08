import unittest
from workers.manual_order_gateway import parse, ref, offer_from

class ManualOrderGatewayTests(unittest.TestCase):
    def setUp(self):
        address = "buyer" + "@" + "example" + ".com"
        self.text = "\n".join([
            "MANUAL ORDER",
            "Order reference: KJ-MANUAL-ABC123",
            "Offer: validation",
            "Contact email: " + address,
            "Payment method: USDT",
            "Source: linkedin",
        ])
    def test_parse_order(self):
        p=parse(self.text)
        self.assertEqual(p["ref"],"KJ-MANUAL-ABC123")
        self.assertEqual(p["offer"],"validation")
        self.assertEqual(p["contact_email"],"buyer@example.com")
        self.assertEqual(p["source"],"linkedin")
    def test_ref(self):
        self.assertEqual(ref(self.text),"KJ-MANUAL-ABC123")
    def test_offer(self):
        self.assertEqual(offer_from(self.text),"validation")
    def test_reject_missing_contact(self):
        p=parse(self.text.replace("buyer@example.com",""))
        self.assertEqual(p["contact_email"],"")

if __name__=="__main__":
    unittest.main()
