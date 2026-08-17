"""Typed async client for Canboso's Telegram Buyer API v2."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.parse import urljoin

import aiohttp

from config import settings
from services.exceptions import (
    ProductNotFoundError,
    ProviderAuthenticationError,
    ProviderPurchaseError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str
    text: str


@dataclass(frozen=True, slots=True)
class Availability:
    available: int | None
    sold: int

    @property
    def in_stock(self) -> bool:
        return self.available is None or self.available > 0


@dataclass(frozen=True, slots=True)
class PurchaseRequirements:
    customer_email: bool = False
    slot_months: bool = False
    quantity_fixed: int | None = None
    allowed_months: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class Promotion:
    type: str
    min_quantity: int | None = None
    percent: Decimal | None = None
    bonus_quantity: int | None = None


@dataclass(frozen=True, slots=True)
class ProviderProduct:
    id: str
    name: str
    description: str
    image_url: str | None
    product_type: str
    price: Money
    availability: Availability
    promotions: tuple[Promotion, ...]
    requirements: PurchaseRequirements


@dataclass(frozen=True, slots=True)
class WalletBalance:
    amount: Decimal
    currency: str
    text: str
    updated_at: str | None


@dataclass(frozen=True, slots=True)
class DeliveredAccount:
    user: str
    password: str
    verify_email: str | None = None
    expiry_text: str | None = None
    other_info: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderOrder:
    code: str
    status: str
    product_id: str
    product_name: str
    product_type: str
    quantity: int
    bonus_quantity: int
    final_quantity: int
    customer_email: str | None = None
    slot_months: int | None = None
    fulfillment_status: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderPayment:
    amount: Decimal
    amount_text: str
    currency: str
    balance: Decimal
    balance_text: str
    discount_percent: Decimal
    discount_amount: Decimal


@dataclass(frozen=True, slots=True)
class PurchaseResult:
    order: ProviderOrder
    payment: ProviderPayment
    accounts: tuple[DeliveredAccount, ...]


def _decimal(value: object, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    return Decimal(str(value))


def _integer(value: object, default: int = 0) -> int:
    if value is None:
        return default
    return int(value)


class CanbosoAPI:
    PRODUCTS_PATH = "/api/v2/telegram-buyer/products"
    BALANCE_PATH = "/api/v2/telegram-buyer/balance"
    PURCHASE_PATH = "/api/v2/telegram-buyer/purchase"

    def __init__(self, api_key: str, base_url: str, cache_seconds: float = 30.0) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.cache_seconds = cache_seconds
        self._products: tuple[ProviderProduct, ...] = ()
        self._products_cached_at = 0.0
        self._products_lock = asyncio.Lock()
        self._balance: WalletBalance | None = None
        self._balance_cached_at = 0.0
        self._balance_lock = asyncio.Lock()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        payload: dict[str, object] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        timeout = aiohttp.ClientTimeout(total=25, connect=8)
        url = f"{self.base_url}{path}"
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.request(
                        method, url, params=params, json=payload, headers=headers
                    ) as response:
                        try:
                            body = await response.json(content_type=None)
                        except (ValueError, aiohttp.ClientPayloadError) as exc:
                            raise ProviderUnavailableError("The supplier returned an invalid response.") from exc

                        if not isinstance(body, dict):
                            raise ProviderUnavailableError("The supplier returned an invalid response.")
                        if response.status == 401:
                            raise ProviderAuthenticationError("The supplier API key is invalid.")
                        if response.status == 429:
                            raw_retry = response.headers.get("Retry-After")
                            retry_after = int(raw_retry) if raw_retry and raw_retry.isdigit() else None
                            raise ProviderRateLimitError(
                                str(body.get("message") or "The supplier rate limit was reached."),
                                retry_after,
                            )
                        if response.status >= 500:
                            raise ProviderUnavailableError(
                                str(body.get("message") or "The supplier is temporarily unavailable.")
                            )
                        if response.status >= 400 or body.get("success") is False:
                            raise ProviderPurchaseError(
                                str(body.get("message") or "The supplier rejected the request."),
                                response.status,
                            )
                        return body
            except (asyncio.TimeoutError, aiohttp.ClientError) as exc:
                last_error = exc
                if attempt == 0:
                    continue
        raise ProviderUnavailableError("Could not reach the supplier. Please try again shortly.") from last_error

    async def list_products(self, *, force_refresh: bool = False) -> tuple[ProviderProduct, ...]:
        now = time.monotonic()
        if not force_refresh and self._products and now - self._products_cached_at < self.cache_seconds:
            return self._products

        async with self._products_lock:
            now = time.monotonic()
            if not force_refresh and self._products and now - self._products_cached_at < self.cache_seconds:
                return self._products
            body = await self._request("GET", self.PRODUCTS_PATH, params={"key": self.api_key})
            raw_products = body.get("products")
            if not isinstance(raw_products, list):
                raise ProviderUnavailableError("The supplier catalog response is incomplete.")
            self._products = tuple(self._parse_product(item) for item in raw_products if isinstance(item, dict))
            self._products_cached_at = time.monotonic()
            return self._products

    async def get_product(self, product_id: str, *, force_refresh: bool = False) -> ProviderProduct:
        products = await self.list_products(force_refresh=force_refresh)
        product = next((item for item in products if item.id == product_id), None)
        if product is None:
            raise ProductNotFoundError(f"No supplier product with id={product_id}")
        return product

    async def get_balance(self, *, force_refresh: bool = False) -> WalletBalance:
        now = time.monotonic()
        if (
            not force_refresh
            and self._balance is not None
            and now - self._balance_cached_at < min(self.cache_seconds, 15.0)
        ):
            return self._balance

        async with self._balance_lock:
            now = time.monotonic()
            if (
                not force_refresh
                and self._balance is not None
                and now - self._balance_cached_at < min(self.cache_seconds, 15.0)
            ):
                return self._balance
            body = await self._request("GET", self.BALANCE_PATH, params={"key": self.api_key})
            self._balance = WalletBalance(
                amount=_decimal(body.get("balance")),
                currency=str(body.get("walletCurrency") or "USD"),
                text=str(body.get("balanceText") or body.get("balance") or "0"),
                updated_at=str(body["updatedAt"]) if body.get("updatedAt") else None,
            )
            self._balance_cached_at = time.monotonic()
            return self._balance

    async def purchase(
        self,
        product_id: str,
        *,
        quantity: int = 1,
        customer_email: str | None = None,
        slot_months: int | None = None,
        idempotency_key: str | None = None,
    ) -> PurchaseResult:
        payload: dict[str, object] = {"key": self.api_key, "product_id": product_id}
        if quantity != 1:
            payload["quantity"] = quantity
        if customer_email:
            payload["customer_email"] = customer_email
        if slot_months is not None:
            payload["slot_months"] = slot_months

        body = await self._request(
            "POST",
            self.PURCHASE_PATH,
            payload=payload,
            idempotency_key=idempotency_key or f"shopbot-{uuid.uuid4().hex}",
        )
        self._products_cached_at = 0.0
        self._balance_cached_at = 0.0
        return self._parse_purchase(body)

    def _parse_product(self, raw: dict[str, Any]) -> ProviderProduct:
        price = raw.get("price") if isinstance(raw.get("price"), dict) else {}
        availability = (
            raw.get("availability") if isinstance(raw.get("availability"), dict) else {}
        )
        requirements_raw = (
            raw.get("purchaseRequirements")
            if isinstance(raw.get("purchaseRequirements"), dict)
            else {}
        )
        promotions: list[Promotion] = []
        for item in raw.get("promotions") or []:
            if not isinstance(item, dict):
                continue
            promotions.append(
                Promotion(
                    type=str(item.get("type") or "promotion"),
                    min_quantity=_integer(item.get("minQty")) if item.get("minQty") is not None else None,
                    percent=_decimal(item.get("percent")) if item.get("percent") is not None else None,
                    bonus_quantity=(
                        _integer(item.get("bonusQty")) if item.get("bonusQty") is not None else None
                    ),
                )
            )
        image = raw.get("image")
        return ProviderProduct(
            id=str(raw.get("productId") or ""),
            name=str(raw.get("name") or "Unnamed product"),
            description=str(raw.get("description") or ""),
            image_url=urljoin(f"{self.base_url}/", str(image).lstrip("/")) if image else None,
            product_type=str(raw.get("productType") or "account"),
            price=Money(
                amount=_decimal(price.get("amount")),
                currency=str(price.get("currency") or "USD"),
                text=str(price.get("text") or price.get("amount") or "0"),
            ),
            availability=Availability(
                available=(
                    _integer(availability.get("available"))
                    if availability.get("available") is not None
                    else None
                ),
                sold=_integer(availability.get("sold")),
            ),
            promotions=tuple(promotions),
            requirements=PurchaseRequirements(
                customer_email=bool(requirements_raw.get("customerEmail")),
                slot_months=bool(requirements_raw.get("slotMonths")),
                quantity_fixed=(
                    _integer(requirements_raw.get("quantityFixed"))
                    if requirements_raw.get("quantityFixed") is not None
                    else None
                ),
                allowed_months=tuple(_integer(value) for value in requirements_raw.get("allowedMonths") or []),
            ),
        )

    @staticmethod
    def _parse_purchase(raw: dict[str, Any]) -> PurchaseResult:
        order = raw.get("order") if isinstance(raw.get("order"), dict) else {}
        payment = raw.get("payment") if isinstance(raw.get("payment"), dict) else {}
        delivery = raw.get("delivery") if isinstance(raw.get("delivery"), dict) else {}
        accounts: list[DeliveredAccount] = []
        for item in delivery.get("accounts") or []:
            if not isinstance(item, dict):
                continue
            accounts.append(
                DeliveredAccount(
                    user=str(item.get("user") or ""),
                    password=str(item.get("password") or ""),
                    verify_email=str(item["verifyEmail"]) if item.get("verifyEmail") else None,
                    expiry_text=str(item["expiryText"]) if item.get("expiryText") else None,
                    other_info=str(item["otherInfo"]) if item.get("otherInfo") else None,
                )
            )
        return PurchaseResult(
            order=ProviderOrder(
                code=str(order.get("orderCode") or ""),
                status=str(order.get("status") or "completed"),
                product_id=str(order.get("productId") or ""),
                product_name=str(order.get("productName") or "Product"),
                product_type=str(order.get("productType") or "account"),
                quantity=_integer(order.get("quantity"), 1),
                bonus_quantity=_integer(order.get("bonusQuantity")),
                final_quantity=_integer(order.get("finalQuantity"), 1),
                customer_email=str(order["customerEmail"]) if order.get("customerEmail") else None,
                slot_months=_integer(order.get("slotMonths")) if order.get("slotMonths") is not None else None,
                fulfillment_status=(
                    str(order["fulfillmentStatus"]) if order.get("fulfillmentStatus") else None
                ),
            ),
            payment=ProviderPayment(
                amount=_decimal(payment.get("amount")),
                amount_text=str(payment.get("amountText") or payment.get("amount") or "0"),
                currency=str(payment.get("currency") or "USD"),
                balance=_decimal(payment.get("balance")),
                balance_text=str(payment.get("balanceText") or payment.get("balance") or "0"),
                discount_percent=_decimal(payment.get("discountPercent")),
                discount_amount=_decimal(payment.get("discountAmount")),
            ),
            accounts=tuple(accounts),
        )


canboso_api = CanbosoAPI(settings.canboso_api_key, settings.canboso_api_base_url)
