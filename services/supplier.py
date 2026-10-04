# services/supplier.py
# ============================================================
# JITU CONFIG STORE - SUPPLIER AUTO PURCHASE API
# ============================================================

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

import config

logger = logging.getLogger(__name__)


BASE_URL = (
    getattr(config, "SUPPLIER_BASE_URL", None)
    or "https://bantibhaiya.to/api/reseller_v1.php"
).strip()

API_KEY = (
    getattr(config, "SUPPLIER_API_KEY", None)
    or ""
).strip()

MASTER_KEY = (
    getattr(config, "SUPPLIER_MASTER_KEY", None)
    or ""
).strip()

TIMEOUT = int(getattr(config, "HTTP_TIMEOUT", 30))
CONNECT_TIMEOUT = int(
    getattr(config, "HTTP_CONNECT_TIMEOUT", 10)
)
RETRIES = int(getattr(config, "HTTP_RETRIES", 2))


class SupplierError(Exception):
    pass


def _timeout() -> aiohttp.ClientTimeout:
    return aiohttp.ClientTimeout(
        total=TIMEOUT,
        connect=CONNECT_TIMEOUT,
    )


async def _post(
    payload: dict[str, Any],
) -> Any:

    last_error = None

    headers = {
        "Accept": "application/json",
        "User-Agent": "JITU-CONFIG-STORE/1.0",
    }

    if MASTER_KEY:
        headers["x-master-key"] = MASTER_KEY

    for attempt in range(RETRIES + 1):
        try:
            async with aiohttp.ClientSession(
                timeout=_timeout()
            ) as session:

                async with session.post(
                    BASE_URL,
                    data=payload,
                    headers=headers,
                ) as response:

                    text = await response.text()

                    try:
                        result = await response.json(
                            content_type=None
                        )
                    except Exception:
                        result = {
                            "raw": text
                        }

                    if response.status >= 400:
                        raise SupplierError(
                            f"HTTP {response.status}: {text[:500]}"
                        )

                    return result

        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            SupplierError,
        ) as exc:

            last_error = exc

            if attempt < RETRIES:
                await asyncio.sleep(
                    min(2 * (attempt + 1), 5)
                )
                continue

            break

    raise SupplierError(
        str(last_error or "Supplier request failed")
    )


def _success(result: Any) -> bool:
    if not isinstance(result, dict):
        return False

    if result.get("success") is True:
        return True

    status = str(
        result.get("status", "")
    ).lower()

    if status in {
        "success",
        "successful",
        "completed",
        "ok",
    }:
        return True

    if result.get("keys"):
        return True

    if result.get("key"):
        return True

    return False


def _extract_keys(result: Any) -> list[str]:
    if not isinstance(result, dict):
        return []

    keys = result.get("keys")

    if isinstance(keys, list):
        return [
            str(key).strip()
            for key in keys
            if str(key).strip()
        ]

    if isinstance(keys, str) and keys.strip():
        return [keys.strip()]

    key = result.get("key")

    if isinstance(key, str) and key.strip():
        return [key.strip()]

    data = result.get("data")

    if isinstance(data, dict):
        nested_keys = data.get("keys")

        if isinstance(nested_keys, list):
            return [
                str(key).strip()
                for key in nested_keys
                if str(key).strip()
            ]

        nested_key = data.get("key")

        if nested_key:
            return [str(nested_key).strip()]

    return []


async def buy_key(
    product_id: int | str,
    duration: str,
    quantity: int = 1,
    android_id: str | None = None,
) -> dict[str, Any]:

    if not API_KEY:
        raise SupplierError(
            "SUPPLIER_API_KEY is not configured"
        )

    if not product_id:
        raise SupplierError(
            "Supplier product ID is required"
        )

    if not duration:
        raise SupplierError(
            "Supplier duration is required"
        )

    if quantity < 1 or quantity > 100:
        raise SupplierError(
            "Quantity must be between 1 and 100"
        )

    payload: dict[str, Any] = {
        "api_key": API_KEY,
        "action": "buy",
        "product_id": str(product_id),
        "duration": str(duration),
        "quantity": str(quantity),
    }

    # Only send android_id when explicitly supplied.
    # Normal V2 products do not require it.
    if android_id:
        payload["android_id"] = str(android_id)

    logger.info(
        "Supplier purchase: pid=%s duration=%s quantity=%s",
        product_id,
        duration,
        quantity,
    )

    result = await _post(payload)

    if not _success(result):
        message = "Supplier purchase failed."

        if isinstance(result, dict):
            message = (
                result.get("message")
                or result.get("error")
                or result.get("msg")
                or message
            )

        raise SupplierError(str(message))

    keys = _extract_keys(result)

    if not keys:
        raise SupplierError(
            "Supplier reported success but returned no license key."
        )

    total_price = None

    if isinstance(result, dict):
        total_price = (
            result.get("total_price")
            or result.get("totalPrice")
        )

        if total_price is None:
            data = result.get("data")
            if isinstance(data, dict):
                total_price = (
                    data.get("total_price")
                    or data.get("totalPrice")
                )

    return {
        "success": True,
        "product_id": str(product_id),
        "duration": str(duration),
        "quantity": quantity,
        "keys": keys,
        "key": keys[0],
        "total_price": total_price,
        "raw": result,
    }


async def buy(
    product_id: int | str,
    duration: str,
    quantity: int = 1,
    android_id: str | None = None,
) -> dict[str, Any]:

    return await buy_key(
        product_id=product_id,
        duration=duration,
        quantity=quantity,
        android_id=android_id,
    )


async def purchase(
    product_id: int | str,
    duration: str,
    quantity: int = 1,
    android_id: str | None = None,
) -> dict[str, Any]:

    return await buy_key(
        product_id=product_id,
        duration=duration,
        quantity=quantity,
        android_id=android_id,
    )


__all__ = [
    "SupplierError",
    "buy_key",
    "buy",
    "purchase",
]
