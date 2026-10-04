# handlers/referral.py
# ============================================================
# ABHAY PANEL STORE - REFERRAL SYSTEM
# Single-message editing architecture
# ============================================================

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

import config
import database

logger = logging.getLogger(__name__)

REFERRAL_BONUS = 0.50
STORE_NAME = "ABHAY PANEL STORE"


def fmt_money(value) -> str:
    try:
        amount = float(value)
        if amount == int(amount):
            return f"₹{int(amount)}"
        return f"₹{amount:.2f}"
    except Exception:
        return "₹0"


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


async def get_bot_username(context) -> str:
    try:
        me = await context.bot.get_me()
        if me and me.username:
            return me.username
    except Exception as e:
        logger.warning("get_me failed: %s", e)

    name = getattr(config, "BOT_USERNAME", None)
    if name:
        return name.lstrip("@")

    return "Jitu_config_Store_bot"


# ============================================================
# REFERRAL SCREEN
# ============================================================

async def referral_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    user = query.from_user
    user_data = database.get_user(user.id)

    if not user_data:
        await safe_edit(query, "❌ User not found.", None)
        return

    ref_code = user_data.get("referral_code") or f"REF{user.id}"
    bot_username = await get_bot_username(context)
    ref_link = f"https://t.me/{bot_username}?start=ref_{ref_code}"

    ref_count = database.get_referral_count(user.id)
    ref_balance = database.get_referral_balance(user.id)

    text = (
        "🎁 <b>REFERRAL SYSTEM</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "🔗 <b>Aapka Link:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"👥 Total Referrals: <b>{ref_count}</b>\n"
        f"💰 Earnings: <b>{fmt_money(ref_balance)}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🤝 Dosto ko invite karo\n"
        f"🎁 Har referral par <b>{fmt_money(REFERRAL_BONUS)}</b> bonus!"
    )

    share_text = "Join this amazing bot!"
    share_url = (
        f"https://t.me/share/url"
        f"?url={ref_link}"
        f"&text={share_text.replace(' ', '%20')}"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Share Link", url=share_url, style="success")],
        [InlineKeyboardButton("‹ Back", callback_data="main_menu", style="primary")],
    ])

    await safe_edit(query, text, markup)


# ============================================================
# APPLY REFERRAL
# ============================================================

async def apply_referral(new_user_id: int, ref_code: str):
    if not ref_code:
        return False

    referrer = database.get_user_by_referral_code(ref_code)
    if not referrer:
        return False

    referrer_id = referrer["telegram_id"]

    if referrer_id == new_user_id:
        return False

    new_user = database.get_user(new_user_id)
    if not new_user:
        return False

    if new_user.get("referred_by"):
        return False

    ok = database.set_referred_by(new_user_id, referrer_id)
    if not ok:
        return False

    database.credit_wallet(referrer_id, REFERRAL_BONUS, reference=f"REF-{new_user_id}")
    database.add_referral_balance(referrer_id, REFERRAL_BONUS)
    database.log_referral(referrer_id, new_user_id, REFERRAL_BONUS)

    return referrer_id


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(referral_screen, pattern=r"^referral$"),
    ]
