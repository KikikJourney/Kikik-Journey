import unittest

import customer_acquisition as ca

class CustomerAcquisitionTests(unittest.TestCase):
    def test_woocommerce_offer_match(self):
        offer = ca.match_offer("Need WooCommerce orders sent to Google Sheets")
        self.assertEqual(offer["name"], "WooCommerce → Google Sheets Automation")

    def test_whatsapp_offer_match(self):
        offer = ca.match_offer("Looking for WhatsApp messages into Google Sheets")
        self.assertEqual(offer["name"], "WhatsApp → Google Sheets Mini Automation")

    def test_no_external_ai_dependency(self):
        source = open("customer_acquisition.py", encoding="utf-8").read()
        self.assertNotIn("openai", source.lower())
        self.assertNotIn("anthropic", source.lower())

if __name__ == "__main__":
    unittest.main()
