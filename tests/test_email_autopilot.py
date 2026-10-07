import unittest
from workers.email_autopilot import classify
class EmailAutopilotTests(unittest.TestCase):
    def test_payment(self): self.assertEqual(classify("I sent USDT, transaction hash 0xabc"),"payment")
    def test_pricing(self): self.assertEqual(classify("How much does the automation cost?"),"pricing")
    def test_purchase_intent(self): self.assertEqual(classify("I am interested and want to start"),"purchase_intent")
    def test_offer_interest(self): self.assertEqual(classify("I need WooCommerce to Google Sheets"),"offer_interest")
    def test_general_is_not_auto_sold(self): self.assertEqual(classify("Hello, just saying hi"),"general")
if __name__=="__main__": unittest.main()
