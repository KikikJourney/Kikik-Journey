import unittest
from unittest.mock import patch
from workers.manual_order_gateway import parse, ref, offer_from, tx_hash, process_payment, process_order, send
from workers import verify_usdt_payment as verifier

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

    @patch("workers.manual_order_gateway.verify_payment")
    @patch("workers.manual_order_gateway.github_find_tx")
    @patch("workers.manual_order_gateway.github_find")
    def test_reused_transaction_for_different_order_is_rejected(self, find_order, find_tx, verify):
        tx = "0x" + "c" * 64
        find_order.return_value = {"ref": "KJ-MANUAL-ABC123", "offer": "validation", "contact_email": "buyer@example.com", "source": "direct"}
        find_tx.return_value = {
            "title": "[ORDER PAID] KJ-MANUAL-OLD123",
            "body": "Order reference: KJ-MANUAL-OLD123\\nStatus: PAID\\nTX hash: " + tx,
        }
        result = process_payment("m2", self.text + "\\nTransaction hash: " + tx)
        self.assertEqual(result["status"], "payment_rejected")
        self.assertEqual(result["verification"]["status"], "transaction_already_used")
        verify.assert_not_called()

    def test_reject_missing_contact(self):
        p=parse(self.text.replace("buyer@example.com",""))
        self.assertEqual(p["contact_email"],"")


class VerifyUsdtPaymentTests(unittest.TestCase):
    TOKEN = verifier.DEFAULT_USDT
    RECIPIENT = "0x" + "1" * 40
    SENDER = "0x" + "2" * 40
    TX_HASH = "0x" + "a" * 64
    AMOUNT = "1.06"

    @staticmethod
    def topic_address(address):
        return "0x" + ("0" * 24) + address[2:].lower()

    def rpc_fixture(self, *, chain_id=56, confirmations=20, amount=None, recipient=None):
        amount = amount or self.AMOUNT
        recipient = recipient or self.RECIPIENT
        transfer_amount = int(verifier.Decimal(amount) * (verifier.Decimal(10) ** 18))
        receipt = {
            "status": "0x1",
            "blockNumber": hex(100),
            "logs": [{
                "address": self.TOKEN,
                "topics": [
                    verifier.TRANSFER_TOPIC,
                    self.topic_address(self.SENDER),
                    self.topic_address(recipient),
                ],
                "data": hex(transfer_amount),
                "logIndex": "0x0",
            }],
        }
        latest = 100 + confirmations - 1

        def fake_rpc(_url, method, _params):
            if method == "eth_chainId": return hex(chain_id)
            if method == "eth_call": return hex(18)
            if method == "eth_getTransactionReceipt": return receipt
            if method == "eth_getTransactionByHash": return {"to": self.TOKEN}
            if method == "eth_blockNumber": return hex(latest)
            raise AssertionError("Unexpected RPC method: " + method)
        return fake_rpc

    @patch("workers.verify_usdt_payment.rpc")
    def test_exact_confirmed_transfer_passes(self, rpc_mock):
        rpc_mock.side_effect = self.rpc_fixture()
        result = verifier.verify_payment(self.TX_HASH, self.AMOUNT, self.RECIPIENT)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "confirmed")
        self.assertGreaterEqual(result["confirmations"], 12)

    @patch("workers.verify_usdt_payment.rpc")
    def test_wrong_chain_is_rejected(self, rpc_mock):
        rpc_mock.side_effect = self.rpc_fixture(chain_id=1)
        result = verifier.verify_payment(self.TX_HASH, self.AMOUNT, self.RECIPIENT)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "wrong_chain")

    @patch("workers.verify_usdt_payment.rpc")
    def test_wrong_recipient_is_rejected(self, rpc_mock):
        rpc_mock.side_effect = self.rpc_fixture(recipient="0x" + "3" * 40)
        result = verifier.verify_payment(self.TX_HASH, self.AMOUNT, self.RECIPIENT)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "amount_or_recipient_mismatch")

    @patch("workers.verify_usdt_payment.rpc")
    def test_insufficient_confirmations_are_rejected(self, rpc_mock):
        rpc_mock.side_effect = self.rpc_fixture(confirmations=2)
        result = verifier.verify_payment(self.TX_HASH, self.AMOUNT, self.RECIPIENT)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "insufficient_confirmations")

    def test_malformed_transaction_hash_is_rejected_before_rpc(self):
        with patch("workers.verify_usdt_payment.rpc") as rpc_mock:
            with self.assertRaises(ValueError):
                verifier.verify_payment("not-a-hash", self.AMOUNT, self.RECIPIENT)
            rpc_mock.assert_not_called()


if __name__=="__main__":
    unittest.main()
