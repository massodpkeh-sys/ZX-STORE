# handlers/wallet.py
# ============================================================
# ABHAY PANEL STORE - WALLET / ADD BALANCE
# Single-message editing architecture
# ============================================================

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from decimal import Decimal, InvalidOperation

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
import database
from services import famgateway

logger = logging.getLogger(__name__)

STORE_NAME = "ABHAY PANEL STORE"
PAYMENT_EXPIRY = 300  # 5 minutes


# ============================================================
# LOCAL QR IMAGE
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QR_IMAGE_PATH = os.path.join(BASE_DIR, "qr.jpg")
QR_IMAGE_EXISTS = os.path.exists(QR_IMAGE_PATH)


# ============================================================
# CONFIG HELPERS
# ============================================================

MIN_DEPOSIT = Decimal(str(getattr(config, "MIN_DEPOSIT", 10)))
MAX_DEPOSIT = Decimal(str(getattr(config, "MAX_DEPOSIT", 5000)))


def money(value) -> Decimal:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def fmt_money(value) -> str:
    amount = money(value)
    if amount == amount.to_integral():
        return f"₹{int(amount)}"
    return f"₹{amount:.2f}"


def get_user_id(update: Update) -> int:
    if update.effective_user:
        return update.effective_user.id
    if update.callback_query and update.callback_query.from_user:
        return update.callback_query.from_user.id
    raise ValueError("Telegram user not found")


async def safe_answer(query, text=None, show_alert=False):
    try:
        if text is not None:
            await query.answer(text, show_alert=show_alert)
        else:
            await query.answer()
    except Exception:
        pass


async def safe_edit(query, text, reply_markup=None):
    """Same message edit — no duplicate"""
    try:
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
    except Exception:
        try:
            await query.message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
        except Exception:
            pass


# ============================================================
# AUTO-DELETE / EXPIRY
# ============================================================

async def auto_delete_message(bot, chat_id, message_id, delay=300):
    try:
        await asyncio.sleep(delay)
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


def is_payment_expired(created_at: int) -> bool:
    try:
        return (int(time.time()) - int(created_at)) > PAYMENT_EXPIRY
    except Exception:
        return False


# ============================================================
# DATABASE COMPATIBILITY
# ============================================================

async def _call_database(names, *args, **kwargs):
    for name in names:
        fn = getattr(database, name, None)
        if not fn:
            continue
        try:
            result = fn(*args, **kwargs)
            if hasattr(result, "__await__"):
                result = await result
            return result
        except TypeError:
            continue
        except Exception:
            logger.exception("%s failed", name)
    return None


async def _get_wallet_balance(user_id):
    result = await _call_database(
        ("get_wallet_balance", "get_balance", "wallet_balance"), user_id,
    )
    if result is None:
        return Decimal("0.00")
    if isinstance(result, dict):
        for key in ("balance", "wallet_balance", "amount"):
            if key in result:
                return money(result[key])
    return money(result)


async def _save_deposit(user_id, amount, order_id, status):
    return await _call_database(
        ("create_deposit", "add_deposit", "record_deposit"),
        user_id=user_id, amount=float(amount),
        order_id=order_id, status=status,
    )


async def _credit_wallet(user_id, amount, reference):
    return await _call_database(
        ("credit_wallet", "add_wallet_balance", "add_balance", "wallet_credit"),
        user_id=user_id, amount=float(amount), reference=reference,
    )


# ============================================================
# KEYBOARDS
# ============================================================

def deposit_amount_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("₹100", callback_data="wallet_amount:100", style="success"),
            InlineKeyboardButton("₹200", callback_data="wallet_amount:200", style="success"),
        ],
        [
            InlineKeyboardButton("₹480", callback_data="wallet_amount:480", style="primary"),
            InlineKeyboardButton("₹1000", callback_data="wallet_amount:1000", style="primary"),
        ],
        [
            InlineKeyboardButton("✏️ Custom Amount", callback_data="wallet_custom", style="primary"),
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data="main_menu", style="danger"),
        ],
    ])


def payment_keyboard(order_id, payment_url=""):
    buttons = []
    if payment_url:
        buttons.append([
            InlineKeyboardButton("💳 Pay Now", url=payment_url, style="success")
        ])
    buttons.append([
        InlineKeyboardButton("✅ I HAVE PAID",
                             callback_data=f"wallet_verify:{order_id}",
                             style="success")
    ])
    buttons.append([
        InlineKeyboardButton("❌ Cancel",
                             callback_data=f"wallet_cancel:{order_id}",
                             style="danger")
    ])
    buttons.append([
        InlineKeyboardButton("‹ Back", callback_data="main_menu", style="primary")
    ])
    return InlineKeyboardMarkup(buttons)


# ============================================================
# ADD BALANCE ENTRY
# ============================================================

async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    text = (
        f"💰 <b>Add Balance</b>\n\n"
        f"🏪 <b>{STORE_NAME}</b>\n\n"
        f"Select the amount you want to add:\n\n"
        f"Minimum: <b>{fmt_money(MIN_DEPOSIT)}</b>\n"
        f"Maximum: <b>{fmt_money(MAX_DEPOSIT)}</b>\n\n"
        f"⚡ Payment is automatically verified."
    )

    await safe_edit(query, text, deposit_amount_keyboard())


# ============================================================
# AMOUNT SELECTION
# ============================================================

async def wallet_amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    try:
        amount = Decimal(query.data.split(":", 1)[1])
    except Exception:
        await safe_answer(query, "Invalid amount.", show_alert=True)
        return

    if amount < MIN_DEPOSIT:
        await safe_answer(query, f"Minimum deposit is {fmt_money(MIN_DEPOSIT)}", show_alert=True)
        return

    if amount > MAX_DEPOSIT:
        await safe_answer(query, f"Maximum deposit is {fmt_money(MAX_DEPOSIT)}", show_alert=True)
        return

    await _create_payment(update, context, amount)


# ============================================================
# CUSTOM AMOUNT
# ============================================================

async def wallet_custom_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    context.user_data["wallet_waiting_amount"] = True

    text = (
        "⚡ <b>QUICK DEPOSIT</b>\n"
        f"💵 Min: <b>{fmt_money(MIN_DEPOSIT)}</b> | Max: <b>{fmt_money(MAX_DEPOSIT)}</b>\n\n"
        "👇 <b>Kitna deposit karna hai?</b>\n"
        "   ₹100  ₹200  ₹480  ₹1000\n\n"
        "Type karo amount 👇👇👇👇"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="wallet_add", style="danger")],
    ])
    await safe_edit(query, text, markup)


async def wallet_custom_amount_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("wallet_waiting_amount"):
        return
    context.user_data.pop("wallet_waiting_amount", None)

    if not update.message:
        return

    try:
        await update.message.delete()
    except Exception:
        pass

    raw = update.message.text.strip().replace(",", "")

    try:
        amount = Decimal(raw)
    except (InvalidOperation, ValueError):
        await update.effective_chat.send_message("❌ Invalid amount. Example: <code>350</code>", parse_mode="HTML")
        return

    if amount != amount.to_integral():
        await update.effective_chat.send_message("❌ Whole rupee amount daalein.", parse_mode="HTML")
        return

    amount = amount.quantize(Decimal("1"))

    if amount < MIN_DEPOSIT:
        await update.effective_chat.send_message(f"❌ Minimum: {fmt_money(MIN_DEPOSIT)}")
        return

    if amount > MAX_DEPOSIT:
        await update.effective_chat.send_message(f"❌ Maximum: {fmt_money(MAX_DEPOSIT)}")
        return

    # Create payment
    await _create_payment_message(update, context, amount)


# ============================================================
# CREATE PAYMENT
# ============================================================

async def _create_payment(update, context, amount):
    """Callback ke baad — same message edit"""
    query = update.callback_query
    user_id = query.from_user.id
    amount = money(amount)

    reference = f"DEP-{user_id}-{int(time.time())}-{uuid.uuid4().hex[:6].upper()}"

    try:
        result = await famgateway.create_payment(
            user_id=user_id, amount=float(amount), reference=reference,
        )
    except Exception:
        logger.exception("FamGateway failed")
        await safe_edit(query, "❌ Payment service error.", None)
        return

    if not result:
        await safe_edit(query, "❌ Unable to create order.", None)
        return

    if isinstance(result, dict):
        order_id = result.get("order_id") or result.get("orderId") or result.get("id")
        payment_url = result.get("payment_url") or result.get("url") or ""
        upi_id = result.get("upi_id") or result.get("upi") or getattr(config, "UPI_ID", "")
    else:
        order_id = getattr(result, "order_id", None)
        payment_url = getattr(result, "payment_url", "")
        upi_id = getattr(result, "upi_id", "")

    if not order_id:
        await safe_edit(query, "❌ Payment gateway error.", None)
        return

    await _save_deposit(user_id=user_id, amount=amount, order_id=str(order_id), status="pending")

    context.user_data[f"wallet_payment:{order_id}"] = {
        "amount": str(amount), "reference": reference,
        "created_at": int(time.time()),
        "payment_url": payment_url or "",
    }

    # Send payment message (naya message — kyunki ye action hai)
    caption_lines = [
        "💳 <b>Payment Created</b>\n",
        f"💰 Amount: <b>{fmt_money(amount)}</b>",
        f"🆔 Order ID: <code>{order_id}</code>\n",
    ]

    if upi_id:
        caption_lines.extend(["📱 <b>UPI ID</b>", f"<code>{upi_id}</code>\n"])

    caption_lines.extend([
        "📷 <b>Scan QR & Pay:</b>",
        "QR neeche di gayi hai 👇\n",
        "⏰ <b>5 minute me pay karein!</b>",
        "Warna payment expire ho jayegi.\n",
        "After completing payment, tap:",
        "<b>I HAVE PAID</b>",
    ])
    caption_text = "\n".join(caption_lines)

    markup = payment_keyboard(order_id, payment_url)

    # Send photo/text
    sent_msg = None
    chat_id = query.message.chat.id

    if QR_IMAGE_EXISTS:
        try:
            with open(QR_IMAGE_PATH, "rb") as qr_file:
                sent_msg = await context.bot.send_photo(
                    chat_id=chat_id, photo=qr_file,
                    caption=caption_text, parse_mode="HTML", reply_markup=markup,
                )
        except Exception:
            sent_msg = None

    if not sent_msg:
        try:
            sent_msg = await context.bot.send_message(
                chat_id=chat_id, text=caption_text,
                parse_mode="HTML", reply_markup=markup,
            )
        except Exception:
            pass

    # Auto-delete after 5 min
    if sent_msg:
        try:
            asyncio.create_task(auto_delete_message(
                bot=context.bot, chat_id=chat_id,
                message_id=sent_msg.message_id, delay=PAYMENT_EXPIRY,
            ))
        except Exception:
            pass


async def _create_payment_message(update, context, amount):
    """Message se aaya — naya message"""
    user_id = update.effective_user.id
    amount = money(amount)

    reference = f"DEP-{user_id}-{int(time.time())}-{uuid.uuid4().hex[:6].upper()}"

    try:
        result = await famgateway.create_payment(
            user_id=user_id, amount=float(amount), reference=reference,
        )
    except Exception:
        logger.exception("FamGateway failed")
        await update.effective_chat.send_message("❌ Payment service error.")
        return

    if not result:
        await update.effective_chat.send_message("❌ Unable to create order.")
        return

    if isinstance(result, dict):
        order_id = result.get("order_id") or result.get("orderId") or result.get("id")
        payment_url = result.get("payment_url") or result.get("url") or ""
        upi_id = result.get("upi_id") or result.get("upi") or getattr(config, "UPI_ID", "")
    else:
        order_id = getattr(result, "order_id", None)
        payment_url = getattr(result, "payment_url", "")
        upi_id = getattr(result, "upi_id", "")

    if not order_id:
        await update.effective_chat.send_message("❌ Payment gateway error.")
        return

    await _save_deposit(user_id=user_id, amount=amount, order_id=str(order_id), status="pending")

    context.user_data[f"wallet_payment:{order_id}"] = {
        "amount": str(amount), "reference": reference,
        "created_at": int(time.time()),
        "payment_url": payment_url or "",
    }

    caption_lines = [
        "💳 <b>Payment Created</b>\n",
        f"💰 Amount: <b>{fmt_money(amount)}</b>",
        f"🆔 Order ID: <code>{order_id}</code>\n",
    ]

    if upi_id:
        caption_lines.extend(["📱 <b>UPI ID</b>", f"<code>{upi_id}</code>\n"])

    caption_lines.extend([
        "📷 <b>Scan QR & Pay:</b>",
        "QR neeche di gayi hai 👇\n",
        "⏰ <b>5 minute me pay karein!</b>",
        "Warna payment expire ho jayegi.\n",
        "After completing payment, tap:",
        "<b>I HAVE PAID</b>",
    ])
    caption_text = "\n".join(caption_lines)

    markup = payment_keyboard(order_id, payment_url)
    sent_msg = None
    chat_id = update.effective_chat.id

    if QR_IMAGE_EXISTS:
        try:
            with open(QR_IMAGE_PATH, "rb") as qr_file:
                sent_msg = await context.bot.send_photo(
                    chat_id=chat_id, photo=qr_file,
                    caption=caption_text, parse_mode="HTML", reply_markup=markup,
                )
        except Exception:
            sent_msg = None

    if not sent_msg:
        try:
            sent_msg = await context.bot.send_message(
                chat_id=chat_id, text=caption_text,
                parse_mode="HTML", reply_markup=markup,
            )
        except Exception:
            pass

    if sent_msg:
        try:
            asyncio.create_task(auto_delete_message(
                bot=context.bot, chat_id=chat_id,
                message_id=sent_msg.message_id, delay=PAYMENT_EXPIRY,
            ))
        except Exception:
            pass


# ============================================================
# VERIFY PAYMENT
# ============================================================

async def wallet_verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query, "Checking payment...")

    try:
        order_id = query.data.split(":", 1)[1]
    except Exception:
        await safe_answer(query, "Invalid payment order.", show_alert=True)
        return

    payment_data = context.user_data.get(f"wallet_payment:{order_id}", {})
    created_at = payment_data.get("created_at", 0)
    payment_url = payment_data.get("payment_url", "")

    # EXPIRY CHECK
    if created_at and is_payment_expired(created_at):
        text = (
            "⏰ <b>Payment Expired</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 Order: <code>{order_id}</code>\n\n"
            "Ye payment 5 minute me expire ho gaya hai.\n\n"
            "🔄 <b>Dobara payment karein:</b>"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Add Balance", callback_data="wallet_add", style="success")],
            [InlineKeyboardButton("‹ Back", callback_data="main_menu", style="primary")],
        ])
        await safe_edit(query, text, markup)
        context.user_data.pop(f"wallet_payment:{order_id}", None)
        return

    # VERIFY LOCK
    verify_lock = f"verify_lock:{order_id}"
    now = time.time()
    last_verify = context.user_data.get(verify_lock, 0)

    if now - last_verify < 10:
        remaining = int(10 - (now - last_verify))
        await safe_answer(query, f"Please wait {max(1, remaining)} seconds.", show_alert=True)
        return

    context.user_data[verify_lock] = now

    try:
        result = await famgateway.verify_payment(order_id=order_id)
    except Exception:
        logger.exception("Verification failed")
        await safe_answer(query, "Verification error.", show_alert=True)
        return

    status = _extract_payment_status(result)

    if status in ("success", "successful", "paid", "completed", "verified", "approved"):
        await _complete_deposit(update, context, order_id, result)
        return

    if status in ("failed", "failure", "cancelled", "canceled", "expired", "rejected"):
        await _save_deposit_status(order_id, "failed")
        text = (
            "❌ <b>Payment Failed</b>\n\n"
            f"🆔 Order: <code>{order_id}</code>\n\n"
            "No wallet balance was added."
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Add Balance", callback_data="wallet_add", style="success")],
            [InlineKeyboardButton("‹ Back", callback_data="main_menu", style="primary")],
        ])
        await safe_edit(query, text, markup)
        return

    # Not received
    text = (
        "❌ <b>Payment Not Received</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 Order: <code>{order_id}</code>\n\n"
        "Aapne abhi tak payment nahi kiya.\n\n"
        "🔄 <b>Please try again:</b>\n"
        "1️⃣ Pay Now button dabao\n"
        "2️⃣ Payment karo\n"
        "3️⃣ Phir I HAVE PAID dabao"
    )
    await safe_edit(query, text, payment_keyboard(order_id, payment_url))


def _extract_payment_status(result) -> str:
    if result is None:
        return "unknown"
    if isinstance(result, bool):
        return "success" if result else "failed"
    if isinstance(result, str):
        return result.strip().lower()
    if isinstance(result, dict):
        if result.get("success") is True:
            status = result.get("status")
            if not status:
                return "success"
        for key in ("status", "payment_status", "order_status", "state"):
            value = result.get(key)
            if value is not None:
                return str(value).strip().lower()
        if result.get("verified") is True:
            return "verified"
        if result.get("paid") is True:
            return "paid"
    for key in ("status", "payment_status", "order_status", "state"):
        value = getattr(result, key, None)
        if value is not None:
            return str(value).strip().lower()
    if getattr(result, "verified", False):
        return "verified"
    return "unknown"


# ============================================================
# COMPLETE DEPOSIT
# ============================================================

async def _complete_deposit(update, context, order_id, gateway_result):
    query = update.callback_query
    user_id = query.from_user.id

    existing = await _call_database(
        ("get_deposit_by_order_id", "get_deposit", "find_deposit"), order_id,
    )

    if isinstance(existing, dict):
        existing_status = str(existing.get("status", "")).lower()
        if existing_status in ("paid", "completed", "credited", "success"):
            await safe_edit(query, "✅ <b>Payment Already Credited</b>", None)
            return

    payment_data = context.user_data.get(f"wallet_payment:{order_id}", {})
    amount = money(payment_data.get("amount", 0))

    if amount <= 0 and isinstance(gateway_result, dict):
        for key in ("amount", "paid_amount", "order_amount"):
            if gateway_result.get(key) is not None:
                amount = money(gateway_result[key])
                break

    if amount <= 0:
        await safe_edit(query, "⚠️ Amount not found. Contact support.", None)
        return

    try:
        credit_result = await _credit_wallet(
            user_id=user_id, amount=amount, reference=f"FAM-{order_id}",
        )
    except Exception:
        logger.exception("Credit failed")
        await safe_edit(query, "⚠️ Wallet credit failed. Contact support.", None)
        return

    if credit_result is False:
        await safe_edit(query, "⚠️ Wallet credit failed.", None)
        return

    await _save_deposit_status(order_id, "paid")
    new_balance = await _get_wallet_balance(user_id)
    context.user_data.pop(f"wallet_payment:{order_id}", None)

    text = (
        "✅ <b>Payment Successful</b>\n\n"
        f"💰 Added: <b>{fmt_money(amount)}</b>\n"
        f"💳 Wallet Balance: <b>{fmt_money(new_balance)}</b>\n\n"
        f"🆔 Order ID: <code>{order_id}</code>"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Shop Now", callback_data="shop_home", style="success")],
        [InlineKeyboardButton("‹ Main Menu", callback_data="main_menu", style="primary")],
    ])
    await safe_edit(query, text, markup)


async def _save_deposit_status(order_id, status):
    try:
        await _call_database(
            ("update_deposit_status", "set_deposit_status", "update_payment_status"),
            order_id=order_id, status=status,
        )
    except Exception:
        pass


# ============================================================
# CANCEL
# ============================================================

async def wallet_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    try:
        order_id = query.data.split(":", 1)[1]
    except Exception:
        order_id = ""

    if order_id:
        context.user_data.pop(f"wallet_payment:{order_id}", None)
        await _save_deposit_status(order_id, "cancelled")

    text = "❌ <b>Payment Cancelled</b>\n\nNo wallet balance was added."
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Add Balance", callback_data="wallet_add", style="success")],
        [InlineKeyboardButton("‹ Main Menu", callback_data="main_menu", style="primary")],
    ])
    await safe_edit(query, text, markup)


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(add_balance, pattern=r"^wallet_add$"),
        CallbackQueryHandler(wallet_amount_callback, pattern=r"^wallet_amount:"),
        CallbackQueryHandler(wallet_custom_callback, pattern=r"^wallet_custom$"),
        CallbackQueryHandler(wallet_verify_callback, pattern=r"^wallet_verify:"),
        CallbackQueryHandler(wallet_cancel_callback, pattern=r"^wallet_cancel:"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_custom_amount_message),
    ]
