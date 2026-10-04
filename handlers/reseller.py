# handlers/reseller.py
# ============================================================
# ABHAY PANEL STORE - VIP RESELLER
# Single-message editing architecture
# ============================================================

from __future__ import annotations

import logging
import time
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

import database

logger = logging.getLogger(__name__)

RESELLER_PLANS = {
    "14": {"days": 14, "price": 199, "label": "14 Days - ₹199"},
    "30": {"days": 30, "price": 299, "label": "30 Days - ₹299"},
}


def fmt_money(value) -> str:
    try:
        amount = float(value)
        if amount == int(amount):
            return f"₹{int(amount)}"
        return f"₹{amount:.2f}"
    except Exception:
        return "₹0"


def fmt_date(ts) -> str:
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%d %b %Y")
    except Exception:
        return "—"


def is_reseller_active(user: dict) -> bool:
    if not user:
        return False
    expiry = int(user.get("reseller_expiry") or 0)
    return expiry > int(time.time())


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
# RESELLER SCREEN
# ============================================================

async def reseller_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    user = query.from_user
    u = database.get_user(user.id)

    if is_reseller_active(u):
        expiry = int(u.get("reseller_expiry") or 0)
        days_left = max(0, (expiry - int(time.time())) // 86400)

        text = (
            "👑 <b>RESELLER ACTIVE</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            f"📅 Expiry: <b>{fmt_date(expiry)}</b>\n"
            f"🕐 Days Left: <b>{days_left}</b>\n\n"
            "🎁 <b>Benefits:</b>\n"
            "• Saste price pe products\n"
            "• Zyada profit margin\n"
            "• Special Reseller Tag\n\n"
            "🛒 Shop me saste price dekhenge."
        )

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Shop Now", callback_data="shop_home", style="success")],
            [InlineKeyboardButton("‹ Back", callback_data="main_menu", style="primary")],
        ])
        await safe_edit(query, text, markup)
        return

    text = (
        "👑 <b>RESELLER PLAN</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💎 <b>Activation Fee:</b>\n"
        "• ₹199 for 14 DAYS\n"
        "• ₹299 for 30 DAYS\n\n"
        "✅ <b>Benefits:</b>\n"
        "• Sabhi products saste price pe\n"
        "• Jitna margin rakho utna profit\n"
        "• Unlimited earning\n"
        "• Special Reseller Tag\n\n"
        "💡 <b>Example:</b>\n"
        "₹300 wala product → Reseller ko ₹149\n"
        "₹500 wala product → Reseller ko ₹239\n\n"
        "🔥 Aap becho aur karo mast profit!"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 14 Days - ₹199", callback_data="reseller_buy:14", style="success")],
        [InlineKeyboardButton("👑 30 Days - ₹299", callback_data="reseller_buy:30", style="success")],
        [InlineKeyboardButton("‹ Back", callback_data="main_menu", style="primary")],
    ])
    await safe_edit(query, text, markup)


# ============================================================
# BUY PLAN
# ============================================================

async def reseller_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    user = query.from_user
    u = database.get_user(user.id)

    if is_reseller_active(u):
        await safe_answer(query, "Already reseller!", show_alert=True)
        return

    try:
        plan_key = query.data.split(":", 1)[1]
    except Exception:
        await safe_answer(query, "Invalid plan.", show_alert=True)
        return

    plan = RESELLER_PLANS.get(plan_key)
    if not plan:
        await safe_answer(query, "Invalid plan.", show_alert=True)
        return

    price = plan["price"]
    days = plan["days"]
    balance = float(u.get("balance") or 0)

    if balance < price:
        needed = price - balance
        text = (
            "❌ <b>Insufficient Balance</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Required: <b>{fmt_money(price)}</b>\n"
            f"💳 Your Balance: <b>{fmt_money(balance)}</b>\n"
            f"📉 Need: <b>{fmt_money(needed)}</b>\n\n"
            "Pehle balance add karein."
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Add Balance", callback_data="wallet_add", style="success")],
            [InlineKeyboardButton("‹ Back", callback_data="reseller", style="primary")],
        ])
        await safe_edit(query, text, markup)
        return

    text = (
        f"🧾 <b>Confirm Reseller</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👑 Plan: <b>{plan['label']}</b>\n"
        f"💰 Price: <b>{fmt_money(price)}</b>\n"
        f"📅 Duration: <b>{days} days</b>\n"
        f"💳 Balance: <b>{fmt_money(balance)}</b>\n\n"
        "Confirm karein?"
    )
    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"reseller_confirm:{plan_key}", style="success"),
            InlineKeyboardButton("❌ Cancel", callback_data="reseller", style="danger"),
        ],
    ])
    await safe_edit(query, text, markup)


# ============================================================
# CONFIRM RESELLER
# ============================================================

async def reseller_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query, "Processing...")

    user = query.from_user
    u = database.get_user(user.id)

    if is_reseller_active(u):
        await safe_answer(query, "Already active!", show_alert=True)
        return

    try:
        plan_key = query.data.split(":", 1)[1]
    except Exception:
        await safe_answer(query, "Invalid.", show_alert=True)
        return

    plan = RESELLER_PLANS.get(plan_key)
    if not plan:
        await safe_answer(query, "Invalid.", show_alert=True)
        return

    price = plan["price"]
    days = plan["days"]
    balance = float(u.get("balance") or 0)

    if balance < price:
        await safe_answer(query, "Insufficient balance.", show_alert=True)
        return

    # Debit
    ok = database.debit_wallet(user.id, price, reference=f"RESELLER-{days}D")
    if not ok:
        await safe_answer(query, "Wallet debit failed.", show_alert=True)
        return

    expiry = int(time.time()) + (days * 86400)

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = [r[1] for r in cur.fetchall()]
        if "reseller_expiry" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN reseller_expiry INTEGER DEFAULT 0")
        cur.execute("UPDATE users SET reseller_expiry = ? WHERE telegram_id = ?", (expiry, user.id))
        conn.commit()
        conn.close()
    except Exception:
        logger.exception("Reseller save failed")
        database.credit_wallet(user.id, price, reference="RESELLER-REFUND")
        await safe_edit(query, "❌ Error. Refunded.", None)
        return

    text = (
        "🎉 <b>RESELLER ACTIVATED!</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"👑 Plan: <b>{plan['label']}</b>\n"
        f"💰 Paid: <b>{fmt_money(price)}</b>\n"
        f"📅 Expiry: <b>{fmt_date(expiry)}</b>\n\n"
        "✅ Ab aap reseller hain!\n"
        "🛒 Shop me saste price dekhenge."
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Shop Now", callback_data="shop_home", style="success")],
        [InlineKeyboardButton("‹ Back", callback_data="main_menu", style="primary")],
    ])
    await safe_edit(query, text, markup)


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(reseller_screen, pattern=r"^reseller$"),
        CallbackQueryHandler(reseller_buy, pattern=r"^reseller_buy:"),
        CallbackQueryHandler(reseller_confirm, pattern=r"^reseller_confirm:"),
    ]
