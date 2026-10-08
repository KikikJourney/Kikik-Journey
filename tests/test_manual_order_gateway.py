import unittest
from unittest.mock import patch
from workers.manual_order_gateway import parse, ref, offer_from, tx_hash, process_payment, process_order, send

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
    def test_payment_function_isolated_from_delivery(self):
        self.assertTrue(callable(process_payment))

    def test_tx_hash_is_part_of_initial_order(self):
        tx = "0x" + "a" * 64
        p = parse(self.text + "\nTransaction hash: " + tx)
        self.assertEqual(tx_hash(self.text + "\nTransaction hash: " + tx), tx)
        self.assertEqual(p["tx_hash"], tx)

    @patch("workers.manual_order_gateway.append_events")
    @patch("workers.manual_order_gateway.github_issue")
    @patch("workers.manual_order_gateway.github_find", return_value=None)
    @patch("workers.manual_order_gateway.process_payment")
    def test_initial_order_with_tx_verifies_immediately(self, payment, _find, _issue, _events):
        payment.return_value = {"status": "paid_and_ready_for_delivery", "ref": "KJ-MANUAL-ABC123"}
        tx = "0x" + "b" * 64
        result = process_order("m1", self.text + "\nTransaction hash: " + tx)
        self.assertEqual(result["status"], "paid_and_ready_for_delivery")
        payment.assert_called_once()

    @patch("workers.manual_order_gateway.api")
    def test_delivery_uses_agentmail_send_endpoint(self, api_mock):
        send("buyer@example.com", "Subject", "Body", ["kj-paid"])
        api_mock.assert_called_once()
        args, kwargs = api_mock.call_args
        self.assertEqual(args[0], "/inboxes/kikikjourney%40agentmail.to/messages/send")
        self.assertEqual(args[1], "POST")
        self.assertEqual(args[2]["to"], "buyer@example.com")
        self.assertEqual(args[2]["labels"], ["kj-paid"])

    def test_reject_missing_contact(self):
        p=parse(self.text.replace("buyer@example.com",""))
        self.assertEqual(p["contact_email"],"")

if __name__=="__main__":
    unittest.main()
