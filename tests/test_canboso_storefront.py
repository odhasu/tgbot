from __future__ import annotations

import unittest
from decimal import Decimal
from unittest.mock import AsyncMock

from services.canboso_api import CanbosoAPI
from utils.formatting import format_money
from utils.pricing import retail_price


PRODUCT_PAYLOAD = {
    "productId": "product-123",
    "name": "Example Slot",
    "description": "A test product",
    "image": "/uploads/example.png",
    "productType": "slot",
    "price": {"amount": 0.19, "currency": "USD", "text": "$0.19"},
    "availability": {"available": 5, "sold": 7},
    "promotions": [{"type": "bulk_discount", "minQty": 3, "percent": 10}],
    "purchaseRequirements": {
        "customerEmail": True,
        "slotMonths": True,
        "quantityFixed": 1,
        "allowedMonths": [1, 3, 6, 12],
    },
}


PURCHASE_PAYLOAD = {
    "success": True,
    "order": {
        "orderCode": "ORDER123",
        "status": "completed",
        "productId": "product-123",
        "productName": "Example Slot",
        "productType": "slot",
        "quantity": 1,
        "bonusQuantity": 0,
        "finalQuantity": 1,
        "customerEmail": "buyer@example.com",
        "slotMonths": 3,
        "fulfillmentStatus": "invited",
    },
    "payment": {
        "amount": 2.50,
        "amountText": "$2.50",
        "currency": "USD",
        "balance": 10,
        "balanceText": "$10.00",
        "discountPercent": 0,
        "discountAmount": 0,
    },
    "delivery": {
        "accounts": [
            {
                "user": "buyer@example.com",
                "password": "secret",
                "verifyEmail": "verify@example.com",
            }
        ]
    },
}


class PricingTests(unittest.TestCase):
    def test_exact_six_tenths_markup_is_applied(self) -> None:
        self.assertEqual(retail_price(Decimal("0.19"), "USD"), Decimal("0.304000"))
        self.assertEqual(retail_price(Decimal("2.72"), "USD"), Decimal("4.352000"))
        self.assertEqual(retail_price(Decimal("50000"), "VND"), Decimal("80000"))

    def test_sub_cent_prices_are_not_rendered_as_free(self) -> None:
        marked_up = retail_price(Decimal("0.001"), "USD")
        self.assertEqual(marked_up, Decimal("0.001600"))
        self.assertEqual(format_money(marked_up, "USD"), "$0.0016")


class ClientParsingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.client = CanbosoAPI("test-key", "https://canboso.example")

    async def test_catalog_fields_and_requirements_are_parsed(self) -> None:
        self.client._request = AsyncMock(  # type: ignore[method-assign]
            return_value={"success": True, "products": [PRODUCT_PAYLOAD]}
        )
        products = await self.client.list_products(force_refresh=True)
        product = products[0]
        self.assertEqual(product.id, "product-123")
        self.assertEqual(product.image_url, "https://canboso.example/uploads/example.png")
        self.assertTrue(product.requirements.customer_email)
        self.assertEqual(product.requirements.allowed_months, (1, 3, 6, 12))
        self.assertEqual(product.promotions[0].percent, Decimal("10"))

    async def test_purchase_sends_required_fields_and_parses_delivery(self) -> None:
        request = AsyncMock(return_value=PURCHASE_PAYLOAD)
        self.client._request = request  # type: ignore[method-assign]
        result = await self.client.purchase(
            "product-123",
            customer_email="buyer@example.com",
            slot_months=3,
            idempotency_key="purchase-test-123",
        )
        request.assert_awaited_once_with(
            "POST",
            self.client.PURCHASE_PATH,
            payload={
                "key": "test-key",
                "product_id": "product-123",
                "customer_email": "buyer@example.com",
                "slot_months": 3,
            },
            idempotency_key="purchase-test-123",
        )
        self.assertEqual(result.order.code, "ORDER123")
        self.assertEqual(result.accounts[0].password, "secret")
        self.assertEqual(result.payment.amount, Decimal("2.5"))


if __name__ == "__main__":
    unittest.main()
