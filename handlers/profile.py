# handlers/profile.py
# ============================================================
# ABHAY PANEL STORE - MY PROFILE + ORDER HISTORY
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


def fmt_date(ts) -> str:
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%d %b %Y")
    except Exception:
        return "—"


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
# MY PROFILE
# ============================================================

async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    user = query.from_user
    u = database.get_user(user.id)

    if not u:
        await safe_edit(query, "❌ User not found.", None)
        return

    balance = u.get("balance") or 0
    ref_balance = u.get("referral_balance") or 0
    joined = fmt_date(u.get("created_at"))
    country = u.get("country") or "IN"

    # Order count
    try:
        orders = database.get_user_orders(user.id, limit=100)
        orders_count = len(orders)
    except Exception:
        orders_count = 0

    # Referral count
    try:
        ref_count = database.get_referral_count(user.id)
    except Exception:
        ref_count = 0

    spent = u.get("total_spent") or 0

    # ============================================================
    # ACCOUNT TYPE (Reseller check)
    # ============================================================
    reseller_expiry = int(u.get("reseller_expiry") or 0)
    now = int(time.time())

    if reseller_expiry > now:
        days_left = (reseller_expiry - now) // 86400
        exp_date = datetime.fromtimestamp(reseller_expiry).strftime("%d %b %Y")
        account_type = (
            f"👑 <b>Reseller</b>\n"
            f"📅 Expires: <b>{exp_date}</b> ({days_left}d left)"
        )
    else:
        account_type = "🔓 <b>Standard Member</b>"

    text = (
        "🔐 <b>MY PROFILE</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"👤 Name: {user.first_name or 'User'}\n"
        f"🌍 Country: {country}\n"
        f"💰 Balance: <b>{fmt_money(balance)}</b>\n"
        f"🎁 Ref Balance: <b>{fmt_money(ref_balance)}</b>\n"
        f"👥 Referrals: <b>{ref_count}</b>\n"
        f"🛒 Orders: <b>{orders_count}</b>\n"
        f"💸 Spent: <b>{fmt_money(spent)}</b>\n"
        f"📅 Joined: {joined}\n"
        "─────────────────────\n"
        f"🎫 Account Type:\n{account_type}\n"
        "━━━━━━━━━━━━━━━━━━━"
    )

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛒 Shop", callback_data="shop_home", style="success"),
            InlineKeyboardButton("📜 Orders", callback_data="my_orders", style="primary"),
        ],
        [
            InlineKeyboardButton("💰 Add Balance", callback_data="wallet_add", style="success"),
            InlineKeyboardButton("🎁 Referral", callback_data="referral", style="danger"),
        ],
        [
            InlineKeyboardButton("🎁 Upgrade To Reseller", callback_data="reseller", style="success"),
        ],
        [
            InlineKeyboardButton("‹ Back", callback_data="main_menu", style="primary"),
        ],
    ])

    await safe_edit(query, text, markup)


# ============================================================
# ORDER HISTORY
# ============================================================

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    user = query.from_user

    try:
        orders = database.get_user_orders(user.id, limit=10)
    except Exception:
        orders = []

    if not orders:
        text = (
            "📜 <b>ORDER HISTORY</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "Aapne abhi koi order nahi kiya.\n"
            "Shop par jaakar pehla purchase karein!"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Shop Now", callback_data="shop_home", style="success")],
            [InlineKeyboardButton("‹ Back", callback_data="my_profile", style="primary")],
        ])
        await safe_edit(query, text, markup)
        return

    lines = ["📜 <b>YOUR ORDERS</b>", "━━━━━━━━━━━━━━━━━━━", ""]

    now = int(time.time())

    for o in orders:
        oid = o.get("order_ref") or f"#{o.get('id', '?')}"
        pname = o.get("product_name") or o.get("product_id") or "Product"
        dur = o.get("duration") or ""
        price = o.get("price") or 0
        date = fmt_date(o.get("created_at"))

        # Calculate expiry from duration
        expiry_line = ""
        try:
            dur_str = str(dur).lower()
            seconds = 0

            if "1h" in dur_str or "1 hour" in dur_str:
                seconds = 3600
            elif "2h" in dur_str or "2 hour" in dur_str:
                seconds = 2 * 3600
            elif "3h" in dur_str or "3 hour" in dur_str:
                seconds = 3 * 3600
            elif "4h" in dur_str or "4 hour" in dur_str:
                seconds = 4 * 3600
            elif "6h" in dur_str or "6 hour" in dur_str:
                seconds = 6 * 3600
            elif "12h" in dur_str or "12 hour" in dur_str:
                seconds = 12 * 3600
            elif "24h" in dur_str or "24 hour" in dur_str:
                seconds = 24 * 3600
            elif "1d" in dur_str or "1 day" in dur_str:
                seconds = 86400
            elif "3d" in dur_str or "3 day" in dur_str:
                seconds = 3 * 86400
            elif "7d" in dur_str or "7 day" in dur_str:
                seconds = 7 * 86400
            elif "10d" in dur_str or "10 day" in dur_str:
                seconds = 10 * 86400
            elif "14d" in dur_str or "14 day" in dur_str:
                seconds = 14 * 86400
            elif "15d" in dur_str or "15 day" in dur_str:
                seconds = 15 * 86400
            elif "28d" in dur_str or "28 day" in dur_str:
                seconds = 28 * 86400
            elif "30d" in dur_str or "30 day" in dur_str:
                seconds = 30 * 86400

            if seconds > 0:
                created = int(o.get("created_at", 0))
                exp_ts = created + seconds
                exp_date = datetime.fromtimestamp(exp_ts).strftime("%d %b %Y | %I:%M %p")

                if exp_ts > now:
                    expiry_line = f"⏳ Expires: {exp_date}"
                else:
                    expiry_line = f"❌ Expired: {exp_date}"
        except Exception:
            pass

        lines.append(f"🆔 <code>{oid}</code>")
        lines.append(f"📦 {pname}")
        lines.append(f"⏱ {dur}  |  💰 {fmt_money(price)}")
        lines.append(f"📅 {date}")
        if expiry_line:
            lines.append(expiry_line)
        lines.append("━━━━━━━━━━━━━━━━━━━")

    text = "\n".join(lines)

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("‹ Back", callback_data="my_profile", style="primary")],
    ])
    await safe_edit(query, text, markup)


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(my_profile, pattern=r"^my_profile$"),
        CallbackQueryHandler(my_orders, pattern=r"^my_orders$"),
    ]
