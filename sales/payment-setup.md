# Payment Setup

The software side is ready. The only account-specific asset that cannot be invented is the official merchant QRIS.

1. Add the official QRIS image as assets/qris.png.
2. Copy payment-config.example.json to payment-config.json.
3. Set the merchant name and customer confirmation URL.
4. Publish through GitHub Pages.

Never commit passwords, OTPs, API secrets, or private payment credentials.

The initial release uses merchant-side verification before product delivery. This avoids treating customer screenshots as proof of payment.
