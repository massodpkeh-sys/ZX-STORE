# handlers/orders.py
# ============================================================
# ABHAY PANEL STORE - ORDER NOTIFICATIONS
# Customer + Admin ko message
# ============================================================

from __future__ import annotations

import logging
import time
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

import config
import database

logger = logging.getLogger(__name__)

ADMIN_ID = 8910147515
STORE_NAME = getattr(config, "STORE_NAME", "ABHAY PANEL STORE")


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
# CUSTOMER SUCCESS MESSAGE
# ============================================================

async def send_customer_success(
    bot,
    user_id: int,
    product_name: str,
    duration: str,
    keys: list,
    amount: float,
    order_ref: str,
):
    """Customer ko successful order ka message bhejta hai."""
    key_text = "\n".join(keys) if isinstance(keys, list) else str(keys)

    text = (
        f"🎉 <b>ORDER SUCCESSFUL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🛒 Product: <b>{product_name}</b>\n"
        f"⏱ Duration: <b>{duration}</b>\n\n"
        f"🔑 <b>YOUR KEY</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<code>{key_text}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Amount Paid: <b>{fmt_money(amount)}</b>\n"
        f"📦 Delivery: <b>Instant</b>\n\n"
        f"🆔 Order ID: <code>{order_ref}</code>\n"
        f"🕐 Date: {fmt_datetime()}\n\n"
        f"⚡ Thank you for your purchase!"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Shop More", callback_data="shop_home", style="success")],
        [InlineKeyboardButton("📜 My Orders", callback_data="my_orders", style="primary")],
    ])

    try:
        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=markup,
        )
        return True
    except Exception as e:
        logger.error("Customer message failed: %s", e)
        return False


# ============================================================
# ADMIN NEW ORDER MESSAGE
# ============================================================

async def send_admin_new_order(
    bot,
    user,
    product_name: str,
    duration: str,
    supplier_pid: str,
    keys: list,
    amount: float,
    order_ref: str,
):
    """Admin ko naye order ka message bhejta hai."""
    key_text = "\n".join(keys) if isinstance(keys, list) else str(keys)

    customer_name = user.get("first_name") or "User"
    customer_id = user.get("telegram_id") or user.get("id") or "—"

    text = (
        f"🛍️ <b>NEW ORDER</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>Customer</b>\n"
        f"Name: {customer_name}\n"
        f"User ID: <code>{customer_id}</code>\n\n"
        f"📦 <b>Product</b>\n"
        f"{product_name}\n"
        f"Duration: {duration}\n"
        f"Supplier PID: <code>{supplier_pid}</code>\n"
        f"Key: <code>{key_text}</code>\n\n"
        f"💰 <b>PAYMENT</b>\n"
        f"Customer Paid: <b>{fmt_money(amount)}</b>\n\n"
        f"🔑 <b>DELIVERY</b>\n"
        f"Status: ✅ Key Delivered\n\n"
        f"🆔 Order ID: <code>{order_ref}</code>\n"
        f"🕐 Time: {fmt_datetime()}"
    )

    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=text,
            parse_mode=ParseMode.HTML,
        )
        return True
    except Exception as e:
        logger.error("Admin message failed: %s", e)
        return False


# ============================================================
# CUSTOMER FAILED MESSAGE
# ============================================================

async def send_customer_failed(
    bot,
    user_id: int,
    order_ref: str,
    product_name: str = "",
    duration: str = "",
):
    """Customer ko fail hone ka message bhejta hai (refund ke saath)."""
    text = (
        f"⚠️ <b>ORDER PROCESSING</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"Your payment was received, but key delivery\n"
        f"is temporarily unavailable.\n\n"
        f"🆔 Order ID: <code>{order_ref}</code>\n\n"
        f"Your amount is protected. Support will assist you."
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Contact Support", url="https://t.me/H4X_JOD_ABHAY", style="success")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu", style="primary")],
    ])

    try:
        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=markup,
        )
        return True
    except Exception as e:
        logger.error("Customer fail message failed: %s", e)
        return False


# ============================================================
# ADMIN FAILED MESSAGE
# ============================================================

async def send_admin_failed(
    bot,
    user_id: int,
    order_ref: str,
    product_name: str,
    duration: str,
    customer_paid: float,
    supplier_cost: float,
    error_message: str = "",
):
    """Admin ko fail hone ka message bhejta hai."""
    text = (
        f"🚨 <b>SUPPLIER PURCHASE FAILED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 Order: <code>{order_ref}</code>\n"
        f"👤 User: <code>{user_id}</code>\n"
        f"📦 Product: {product_name}\n"
        f"⏱ Duration: {duration}\n\n"
        f"💰 Customer Paid: <b>{fmt_money(customer_paid)}</b>\n"
        f"🏭 Supplier Cost: <b>{fmt_money(supplier_cost)}</b>\n\n"
        f"❌ Supplier Status: <b>FAILED</b>\n"
    )

    if error_message:
        text += f"📝 Error: <code>{error_message[:200]}</code>\n"

    text += f"\n🔄 Action: Refund / Manual Review"

    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=text,
            parse_mode=ParseMode.HTML,
        )
        return True
    except Exception as e:
        logger.error("Admin fail message failed: %s", e)
        return False


# ============================================================
# COMPLETE ORDER (Helper — purchase ke baad call karo)
# ============================================================

async def process_order_notifications(
    bot,
    user_id: int,
    product_name: str,
    duration: str,
    keys: list,
    amount: float,
    supplier_pid: str = "",
    user_data: dict = None,
):
    """
    Order successful hone par ye call karo.
    Customer + Admin dono ko message bhejta hai.
    Returns order_ref.
    """
    order_ref = database.generate_order_ref()

    # Customer message
    await send_customer_success(
        bot=bot,
        user_id=user_id,
        product_name=product_name,
        duration=duration,
        keys=keys,
        amount=amount,
        order_ref=order_ref,
    )

    # Admin message
    if user_data is None:
        user_data = database.get_user(user_id) or {}

    await send_admin_new_order(
        bot=bot,
        user=user_data,
        product_name=product_name,
        duration=duration,
        supplier_pid=supplier_pid,
        keys=keys,
        amount=amount,
        order_ref=order_ref,
    )

    return order_ref


# ============================================================
# FAILED ORDER NOTIFICATION
# ============================================================

async def process_order_failure(
    bot,
    user_id: int,
    product_name: str,
    duration: str,
    customer_paid: float,
    supplier_cost: float,
    order_ref: str = "",
    error_message: str = "",
):
    """
    Order fail hone par ye call karo.
    Customer + Admin dono ko message bhejta hai.
    """
    if not order_ref:
        order_ref = database.generate_order_ref()

    await send_customer_failed(
        bot=bot,
        user_id=user_id,
        order_ref=order_ref,
        product_name=product_name,
        duration=duration,
    )

    await send_admin_failed(
        bot=bot,
        user_id=user_id,
        order_ref=order_ref,
        product_name=product_name,
        duration=duration,
        customer_paid=customer_paid,
        supplier_cost=supplier_cost,
        error_message=error_message,
    )

    return order_ref


# ============================================================
# HANDLERS (No direct handlers, ye helper functions hain)
# ============================================================

def get_handlers():
    return []
