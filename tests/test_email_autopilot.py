import unittest
from workers.email_autopilot import classify, detect_offer, payment_amount, explicit_order_ref, tx_hash

class EmailAutopilotTests(unittest.TestCase):
    def test_payment(self): self.assertEqual(classify("I sent USDT, transaction hash 0xabc"), "payment")
    def test_pricing(self): self.assertEqual(classify("How much does the automation cost?"), "pricing")
    def test_purchase_intent(self): self.assertEqual(classify("I am interested and want to start"), "purchase_intent")
    def test_offer_interest(self): self.assertEqual(classify("I need WooCommerce to Google Sheets"), "offer_interest")
    def test_general_is_not_auto_sold(self): self.assertEqual(classify("Hello, just saying hi"), "general")
    def test_usdt_offer_amounts(self):
        self.assertEqual(str(payment_amount("I paid", "woocommerce")), "22.30")
        self.assertEqual(str(payment_amount("I paid", "validation")), "1.06")
    def test_order_reference(self):
        self.assertEqual(explicit_order_ref("Order KJ-ABC123 paid", "KJ-FALLBACK"), "KJ-ABC123")
    def test_tx_hash(self):
        h = "0x" + "a"*64
        self.assertEqual(tx_hash("tx " + h), h)
    def test_offer_detection(self):
        self.assertEqual(detect_offer("Need WooCommerce automation"), "woocommerce")

    def test_support_email_mentioning_automation_is_not_offer_interest(self):
        text = (
            "Subject: Re: [PINTU] USER'S FEEDBACK\n"
            "Regarding your report on potential vulnerabilities or bugs, submit it "
            "through our official Bug Bounty platform dashboard.\n"
            "Kikik Journey — Automation Sales\n"
            "Checkout: https://kikikjourney.github.io/Kikik-Journey/sales/checkout.html"
        )
        self.assertEqual(classify(text), "general")

    def test_generic_payment_word_is_not_payment_proof(self):
        self.assertEqual(classify("Your ticket is resolved. Please use the official platform for bug reports and payment status updates."), "general")

    def test_offer_keyword_without_customer_intent_is_not_order(self):
        self.assertEqual(classify("Our support team is checking your report about workflow automation."), "general")

if __name__ == "__main__": unittest.main()
