# services/famgateway.py
# ============================================================
# JITU CONFIG STORE - FAMGATEWAY
# Python 3.13+
# aiohttp
# ============================================================

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

import config

logger = logging.getLogger(__name__)


# ============================================================
# CONFIG
# ============================================================

BASE_URL = (
    getattr(config, "FAMGATEWAY_BASE_URL", None)
    or "https://famgateway.in"
).rstrip("/")

API_KEY = (
    getattr(config, "FAMGATEWAY_API_KEY", None)
    or getattr(config, "FAM_API_KEY", None)
    or ""
)

TIMEOUT = int(
    getattr(config, "HTTP_TIMEOUT", 30)
)

CONNECT_TIMEOUT = int(
    getattr(config, "HTTP_CONNECT_TIMEOUT", 10)
)

RETRIES = int(
    getattr(config, "HTTP_RETRIES", 2)
)


# ============================================================
# EXCEPTIONS
# ============================================================

class FamGatewayError(Exception):
    """FamGateway API error."""


# ============================================================
# HTTP SESSION
# ============================================================

def _timeout() -> aiohttp.ClientTimeout:
    return aiohttp.ClientTimeout(
        total=TIMEOUT,
        connect=CONNECT_TIMEOUT,
    )


async def _request(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
) -> Any:

    last_error: Exception | None = None

    for attempt in range(RETRIES + 1):
        try:
            async with aiohttp.ClientSession(
                timeout=_timeout()
            ) as session:

                async with session.request(
                    method,
                    url,
                    params=params,
                    data=data,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "JITU-CONFIG-STORE/1.0",
                    },
                ) as response:

                    text = await response.text()

                    if not text:
                        raise FamGatewayError(
                            f"Empty response: HTTP {response.status}"
                        )

                    try:
                        result = await response.json(
                            content_type=None
                        )
                    except Exception:
                        result = {
                            "raw": text,
                            "http_status": response.status,
                        }

                    if response.status >= 400:
                        raise FamGatewayError(
                            f"HTTP {response.status}: {text[:500]}"
                        )

                    return result

        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            FamGatewayError,
        ) as exc:

            last_error = exc

            if attempt < RETRIES:
                await asyncio.sleep(
                    min(2 * (attempt + 1), 5)
                )
                continue

            break

    raise FamGatewayError(
        str(last_error or "FamGateway request failed")
    )


# ============================================================
# RESULT HELPERS
# ============================================================

def _dict(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        return result
    return {}


def _find_value(
    result: Any,
    *keys: str,
):
    if not isinstance(result, dict):
        return None

    for key in keys:
        if key in result and result[key] is not None:
            return result[key]

    # Some APIs wrap data inside "data".
    data = result.get("data")

    if isinstance(data, dict):
        for key in keys:
            if key in data and data[key] is not None:
                return data[key]

    return None


def _normalise_create_response(
    result: Any,
) -> dict[str, Any]:

    if not isinstance(result, dict):
        return {
            "success": False,
            "raw": result,
        }

    order_id = _find_value(
        result,
        "order_id",
        "orderId",
        "id",
    )

    payment_url = _find_value(
        result,
        "payment_url",
        "paymentUrl",
        "checkout_url",
        "checkoutUrl",
        "url",
    )

    upi_id = _find_value(
        result,
        "upi_id",
        "upiId",
        "upi",
    )

    amount = _find_value(
        result,
        "amount",
        "order_amount",
        "payment_amount",
    )

    success = result.get("success")

    if success is None:
        status = str(
            result.get("status", "")
        ).lower()

        success = (
            bool(order_id)
            and status not in {
                "failed",
                "failure",
                "error",
            }
        )

    return {
        **result,
        "success": bool(success),
        "order_id": order_id,
        "payment_url": payment_url,
        "upi_id": upi_id
            or getattr(config, "UPI_ID", ""),
        "amount": amount,
    }


# ============================================================
# CREATE PAYMENT
# ============================================================

async def create_payment(
    user_id: int | None = None,
    amount: float | int | str | None = None,
    reference: str | None = None,
    amount_rupees: float | int | str | None = None,
) -> dict[str, Any]:

    """
    Create FamGateway payment.

    Compatible with:
        create_payment(
            user_id=123,
            amount=100,
            reference="DEP-123"
        )

    Also accepts amount_rupees for compatibility.
    """

    if amount is None:
        amount = amount_rupees

    if amount is None:
        raise FamGatewayError(
            "Payment amount is required"
        )

    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        raise FamGatewayError(
            "Invalid payment amount"
        )

    if amount_value <= 0:
        raise FamGatewayError(
            "Payment amount must be greater than zero"
        )

    if not API_KEY:
        raise FamGatewayError(
            "FAMGATEWAY_API_KEY is not configured"
        )

    payload: dict[str, Any] = {
        "api_key": API_KEY,
        "amount": amount_value,
    }

    if user_id is not None:
        payload["user_id"] = str(user_id)

    if reference:
        payload["reference"] = reference

    url = f"{BASE_URL}/api/create-order"

    logger.info(
        "Creating FamGateway payment: user_id=%s amount=%s reference=%s",
        user_id,
        amount_value,
        reference,
    )

    result = await _request(
        "POST",
        url,
        data=payload,
    )

    normalised = _normalise_create_response(
        result
    )

    if not normalised.get("order_id"):
        logger.error(
            "FamGateway create-order returned no order ID: %r",
            result,
        )

        raise FamGatewayError(
            "FamGateway did not return an order ID"
        )

    return normalised


# ============================================================
# CHECK PAYMENT STATUS
# ============================================================

async def payment_status(
    order_id: str,
) -> dict[str, Any]:

    if not order_id:
        raise FamGatewayError(
            "order_id is required"
        )

    url = (
        f"{BASE_URL}"
        "/api/checkout-status.php"
    )

    params = {
        "order_id": order_id,
    }

    result = await _request(
        "GET",
        url,
        params=params,
    )

    if isinstance(result, dict):
        return result

    return {
        "success": False,
        "raw": result,
    }


# ============================================================
# VERIFY PAYMENT
# ============================================================

async def verify_payment(
    order_id: str,
) -> dict[str, Any]:

    """
    Verify payment directly with FamGateway.

    No webhook is used.
    """

    if not order_id:
        raise FamGatewayError(
            "order_id is required"
        )

    if not API_KEY:
        raise FamGatewayError(
            "FAMGATEWAY_API_KEY is not configured"
        )

    url = (
        f"{BASE_URL}"
        "/api/verify-order.php"
    )

    params = {
        "api_key": API_KEY,
        "order_id": order_id,
    }

    logger.info(
        "Verifying FamGateway order: %s",
        order_id,
    )

    result = await _request(
        "GET",
        url,
        params=params,
    )

    if isinstance(result, dict):
        return result

    return {
        "success": False,
        "raw": result,
    }


# ============================================================
# COMPATIBILITY ALIASES
# ============================================================

async def verify_order(
    order_id: str,
) -> dict[str, Any]:
    return await verify_payment(order_id)


async def check_payment(
    order_id: str,
) -> dict[str, Any]:
    return await payment_status(order_id)


async def get_payment_status(
    order_id: str,
) -> dict[str, Any]:
    return await payment_status(order_id)


# ============================================================
# SIMPLE TEST
# ============================================================

async def health_check() -> bool:
    """
    Basic configuration check.
    Does not create a payment.
    """

    if not API_KEY:
        return False

    return bool(BASE_URL)
