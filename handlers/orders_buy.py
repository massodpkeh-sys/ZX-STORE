# handlers/orders_buy.py
# ============================================================
# ABHAY PANEL STORE - PURCHASE FLOW
# Order ID, Customer + Admin notifications
# ============================================================

from __future__ import annotations

import logging
import time
from datetime import datetime

from telegram.constants import ParseMode

import config
import database
from services import supplier
from handlers import orders as orders_nofify

logger = logging.getLogger(__name__)

ADMIN_ID = 8910147515


# ============================================================
# HELPERS
# ============================================================

def fmt_money(value) -> str:
    try:
        amount = float(value)
        if amount == int(amount):
            return f"₹{int(amount)}"
        return f"₹{amount:.2f}"
    except Exception:
        return "₹0"


def fmt_datetime(ts=None) -> str:
    try:
        if ts is None:
            ts = time.time()
        return datetime.fromtimestamp(int(ts)).strftime("%d %b %Y | %I:%M %p")
    except Exception:
        return "—"


# ============================================================
# PURCHASE ORDER — Main Function
# ============================================================

async def buy_order(
    bot,
    user_id: int,
    user_data: dict,
    pid: str,
    product_name: str,
    display_duration: str,
    price: float,
    supplier_cost: float = 0,
) -> dict:
    """
    Order purchase karta hai.
    
    Returns:
        {
            "success": True/False,
            "order_ref": "ORD-XXXXXX",
            "keys": [...],
            "message": "error message if failed",
        }
    """
    order_ref = database.generate_order_ref()

    # Check balance
    balance = float(user_data.get("balance") or 0)
    if balance < price:
        return {
            "success": False,
            "order_ref": order_ref,
            "keys": [],
            "message": f"Insufficient balance. Required {fmt_money(price)}.",
        }

    # Debit wallet
    ok = database.debit_wallet(user_id, price, reference=f"BUY-{pid}")
    if not ok:
        return {
            "success": False,
            "order_ref": order_ref,
            "keys": [],
            "message": "Wallet debit failed.",
        }

    # Call supplier
    keys = []
    error_msg = ""

    try:
        result = await supplier.buy_key(
            product_id=pid,
            duration=display_duration,
            quantity=1,
        )
        keys = result.get("keys") or []
        if not keys:
            error_msg = "Supplier returned no keys."
    except Exception as e:
        logger.exception("Supplier purchase failed")
        error_msg = str(e)

    # SUCCESS
    if keys:
        # Save order
        database.create_order(
            user_id=user_id,
            product_id=str(pid),
            duration=display_duration,
            price=price,
            keys=keys,
            product_name=product_name,
            order_ref=order_ref,
        )

        # Add to total spent
        try:
            database.add_to_total_spent(user_id, price)
        except Exception:
            pass

        # Customer notification
        await orders_nofify.send_customer_success(
            bot=bot,
            user_id=user_id,
            product_name=product_name,
            duration=display_duration,
            keys=keys,
            amount=price,
            order_ref=order_ref,
        )

        # Admin notification
        await orders_nofify.send_admin_new_order(
            bot=bot,
            user=user_data,
            product_name=product_name,
            duration=display_duration,
            supplier_pid=str(pid),
            keys=keys,
            amount=price,
            order_ref=order_ref,
        )

        return {
            "success": True,
            "order_ref": order_ref,
            "keys": keys,
            "message": "Success",
        }

    # FAIL — Refund
    try:
        database.credit_wallet(user_id, price, reference=f"REFUND-{pid}")
    except Exception:
        logger.exception("Refund failed")

    # Customer fail message
    await orders_nofify.send_customer_failed(
        bot=bot,
        user_id=user_id,
        order_ref=order_ref,
        product_name=product_name,
        duration=display_duration,
    )

    # Admin fail message
    await orders_nofify.send_admin_failed(
        bot=bot,
        user_id=user_id,
        order_ref=order_ref,
        product_name=product_name,
        duration=display_duration,
        customer_paid=price,
        supplier_cost=supplier_cost,
        error_message=error_msg,
    )

    return {
        "success": False,
        "order_ref": order_ref,
        "keys": [],
        "message": error_msg or "Supplier purchase failed. Refunded.",
    }
