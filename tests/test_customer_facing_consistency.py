from pathlib import Path
import unittest


class CustomerFacingConsistencyTests(unittest.TestCase):
    def test_homepage_does_not_advertise_unavailable_payment_methods(self):
        page = Path('index.html').read_text(encoding='utf-8')
        self.assertIn('USDT on BNB Smart Chain (BEP-20) only', page)
        self.assertNotIn('Select USDT, QRIS or Dana', page)

    def test_whatsapp_offer_does_not_promise_qris_checkout(self):
        page = Path('sales/wa-sheet.html').read_text(encoding='utf-8')
        self.assertNotIn('Bayar langsung melalui QRIS', page)
        self.assertIn('metode pembayaran yang tersedia di checkout', page)

    def test_business_first_positioning_is_not_github_only(self):
        audit = Path('research/product-market-audit-2026-10.md').read_text(encoding='utf-8')
        self.assertIn('public sources beyond GitHub', audit)
        self.assertIn('payment evidence', audit)


if __name__ == '__main__':
    unittest.main()