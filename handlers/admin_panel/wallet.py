# handlers/admin_panel/wallet.py
# ============================================================
# ADMIN PANEL - WALLET SUMMARY
# Single-message editing architecture
# ============================================================

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

import database
from handlers.admin_panel.menu import is_admin, safe_answer, safe_edit, back_admin

logger = logging.getLogger(__name__)


def fmt_money(v):
    try:
        a = float(v)
        return f"₹{int(a)}" if a == int(a) else f"₹{a:.2f}"
    except Exception:
        return "₹0"


# ============================================================
# WALLET SUMMARY
# ============================================================

async def admin_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    try:
        conn = database._conn()
        cur = conn.cursor()

        cur.execute("SELECT COALESCE(SUM(balance),0) as s FROM users")
        total_bal = cur.fetchone()["s"] or 0

        cur.execute("SELECT COALESCE(SUM(referral_balance),0) as s FROM users")
        total_ref = cur.fetchone()["s"] or 0

        # Try spin_balance
        try:
            cur.execute("SELECT COALESCE(SUM(spin_balance),0) as s FROM users")
            total_spin = cur.fetchone()["s"] or 0
        except Exception:
            total_spin = 0

        # Try total_spent
        try:
            cur.execute("SELECT COALESCE(SUM(total_spent),0) as s FROM users")
            total_spent = cur.fetchone()["s"] or 0
        except Exception:
            total_spent = 0

        # Try total_deposited
        try:
            cur.execute("SELECT COALESCE(SUM(total_deposited),0) as s FROM users")
            total_dep = cur.fetchone()["s"] or 0
        except Exception:
            total_dep = 0

        conn.close()
    except Exception:
        logger.exception("Wallet summary failed")
        total_bal = total_ref = total_spin = total_spent = total_dep = 0

    text = (
        f"💰 <b>WALLET SUMMARY</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👥 User Balance: <b>{fmt_money(total_bal)}</b>\n"
        f"🎁 Referral Balance: <b>{fmt_money(total_ref)}</b>\n"
        f"🎰 Spin Balance: <b>{fmt_money(total_spin)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💸 Total Spent: <b>{fmt_money(total_spent)}</b>\n"
        f"💵 Total Deposited: <b>{fmt_money(total_dep)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )

    await safe_edit(query, text, back_admin())


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(admin_wallet, pattern=r"^admin_wallet$"),
    ]
