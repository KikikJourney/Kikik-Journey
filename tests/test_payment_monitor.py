import unittest
import payment_monitor

class PaymentMonitorTests(unittest.TestCase):
    def test_wallet_topic(self):
        self.assertEqual(
            payment_monitor.wallet_topic("0x4ce7004e7127f8b2386eb355e088f127c24b3fac"),
            "0x0000000000000000000000004ce7004e7127f8b2386eb355e088f127c24b3fac",
        )

    def test_decode_incoming_transfer(self):
        log = {
            "topics": [
                payment_monitor.TRANSFER_TOPIC,
                "0x0000000000000000000000001111111111111111111111111111111111111111",
                "0x0000000000000000000000004ce7004e7127f8b2386eb355e088f127c24b3fac",
            ],
            "data": "0xde0b6b3a7640000",
            "transactionHash": "0xabc",
            "blockNumber": "0x10",
        }
        item = payment_monitor.decode_transfer(log)
        self.assertEqual(item["sender"], "0x1111111111111111111111111111111111111111")
        self.assertEqual(item["amount_usdt"], 1.0)
        self.assertEqual(item["block_number"], 16)

if __name__ == "__main__":
    unittest.main()
