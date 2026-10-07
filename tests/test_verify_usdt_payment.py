import unittest
from unittest.mock import patch
from workers.verify_usdt_payment import verify_payment, TRANSFER_TOPIC

class UsdtVerifierTests(unittest.TestCase):
    RPC="https://example.invalid"
    def rpc(self,url,method,params):
        if method=="eth_chainId": return "0x38"
        if method=="eth_call": return "0x12"
        if method=="eth_getTransactionByHash": return {"to":"0x55d398326f99059fF775485246999027B3197955"}
        if method=="eth_getTransactionReceipt":
            return {"status":"0x1","blockNumber":"0x64","logs":[{
                "address":"0x55d398326f99059fF775485246999027B3197955",
                "topics":[TRANSFER_TOPIC,"0x"+"11"*20,"0x"+"00"*12+"4ce7004e7127f8b2386eb355e088f127c24b3fac"],
                "data":"0x"+(1000000000000000000).to_bytes(32,"big").hex(),"logIndex":"0x0"}]}
        if method=="eth_blockNumber": return "0x6f"
        raise AssertionError(method)
    @patch("workers.verify_usdt_payment.rpc")
    def test_exact_payment_confirms(self,m):
        m.side_effect=self.rpc
        r=verify_payment("0x"+"aa"*32,"1","0x4ce7004e7127f8b2386eb355e088f127c24b3fac",rpc_url=self.RPC,min_confirmations=12)
        self.assertTrue(r["ok"]); self.assertEqual(r["status"],"confirmed")
    @patch("workers.verify_usdt_payment.rpc")
    def test_wrong_amount_rejected(self,m):
        m.side_effect=self.rpc
        r=verify_payment("0x"+"aa"*32,"2","0x4ce7004e7127f8b2386eb355e088f127c24b3fac",rpc_url=self.RPC)
        self.assertFalse(r["ok"]); self.assertEqual(r["status"],"amount_or_recipient_mismatch")
    @patch("workers.verify_usdt_payment.rpc")
    def test_wrong_chain_rejected(self,m):
        m.side_effect=lambda url,method,params: "0x1" if method=="eth_chainId" else None
        r=verify_payment("0x"+"aa"*32,"1","0x4ce7004e7127f8b2386eb355e088f127c24b3fac",rpc_url=self.RPC)
        self.assertFalse(r["ok"]); self.assertEqual(r["status"],"wrong_chain")

if __name__=="__main__": unittest.main()
