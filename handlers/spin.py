# handlers/spin.py
# ============================================================
# ABHAY PANEL STORE - CASH SPIN
# Single-message editing architecture
# ============================================================

from __future__ import annotations

import logging
import random
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

import database

logger = logging.getLogger(__name__)

MIN_SPIN = 0.10
MAX_SPIN = 1.00
SPIN_COOLDOWN = 24 * 60 * 60  # 24 hours


def fmt_money(value) -> str:
    try:
        return f"₹{float(value):.2f}"
    except Exception:
        return "₹0.00"


def fmt_time(seconds: int) -> str:
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"


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
# SPIN SCREEN
# ============================================================

async def spin_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    user_id = query.from_user.id
    can, remaining = database.can_spin(user_id)

    if can:
        text = (
            "🎰 <b>CASH SPIN</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "🎁 Daily Free Spin!\n"
            "💰 Jeeto toh seedha wallet me Cash!\n"
            "🌱 Har roz ek free spin milega!\n\n"
            "🟢 <b>Spin available hai!</b>\n\n"
            "👉 Spin karo aur luck try karo!"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎰 Spin Now (FREE)", callback_data="spin_play", style="success")],
            [InlineKeyboardButton("‹ Back", callback_data="main_menu", style="primary")],
        ])
    else:
        text = (
            "🎰 <b>CASH SPIN</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "🎁 Daily Free Spin!\n"
            "💰 Jeeto toh seedha wallet me Cash!\n"
            "🌱 Har roz ek free spin milega!\n\n"
            "🔴 <b>Abhi nahi!</b>\n"
            f"⏳ {fmt_time(remaining)} baad aao!"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⏳ {fmt_time(remaining)} baad",
                                  callback_data="spin_wait", style="danger")],
            [InlineKeyboardButton("‹ Back", callback_data="main_menu", style="primary")],
        ])

    await safe_edit(query, text, markup)


# ============================================================
# PLAY SPIN
# ============================================================

async def spin_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query, "🎰 Spinning...")

    user_id = query.from_user.id
    can, remaining = database.can_spin(user_id)

    if not can:
        await safe_answer(query, "Abhi spin nahi kar sakte. Thodi der baad!", show_alert=True)
        return

    amount = round(random.uniform(MIN_SPIN, MAX_SPIN), 2)

    # Save
    database.set_last_spin(user_id)
    database.add_spin_balance(user_id, amount)
    database.credit_wallet(user_id, amount, reference="SPIN")
    database.log_spin(user_id, amount)

    text = (
        "🎰 <b>CASH SPIN RESULT!</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🎁 Reward: <b>{fmt_money(amount)}</b>\n\n"
        "🎉 <b>Congratulations!</b>\n"
        f"💰 Aapko {fmt_money(amount)} Cash mila!\n\n"
        "✅ Reward aapke wallet me add ho gaya.\n\n"
        "🕐 24 ghante baad phir spin milega!"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Check Balance", callback_data="my_profile", style="success")],
        [InlineKeyboardButton("‹ Back", callback_data="main_menu", style="primary")],
    ])

    await safe_edit(query, text, markup)


async def spin_wait(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query, "Abhi intezaar karein!", show_alert=True)


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(spin_screen, pattern=r"^spin$"),
        CallbackQueryHandler(spin_play, pattern=r"^spin_play$"),
        CallbackQueryHandler(spin_wait, pattern=r"^spin_wait$"),
    ]
