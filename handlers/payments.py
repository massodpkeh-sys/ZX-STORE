# handlers/payments.py
# ============================================================
# ABHAY PANEL STORE - PAYMENTS & DEPOSITS
# User: My Deposits | Admin: Summary + Credit/Reject
# Delete old message + Auto-notify
# ============================================================

from __future__ import annotations

import logging
import time
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, ContextTypes

import config
import database

logger = logging.getLogger(__name__)

ADMIN_ID = 8910147515
STORE_NAME = "ABHAY PANEL STORE"


# ============================================================
# HELPERS
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


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
        return datetime.fromtimestamp(int(ts)).strftime("%d %b %Y | %I:%M %p")
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


# ============================================================
# SAFE EDIT — PURANA DELETE + NAYA SEND
# ============================================================

async def safe_edit(query, text, reply_markup=None):
    """Purana message delete karo, naya bhejo."""
    try:
        await query.message.delete()
    except Exception:
        pass

    try:
        await query.message.chat.send_message(
            text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    except Exception:
        pass


def back_to_admin():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")]
    ])


def back_to_payments():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("‹ Back", callback_data="admin_payments", style="primary")]
    ])


# ============================================================
# DB FUNCTIONS
# ============================================================

def get_user_deposits(user_id: int, limit: int = 10):
    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM deposits WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_deposits_by_status(status: str, limit: int = 20):
    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM deposits WHERE status = ? ORDER BY id DESC LIMIT ?",
            (status, limit),
        )
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_deposit_by_order_id(order_id: str):
    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM deposits WHERE order_id = ?", (order_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def update_deposit_status(order_id: str, status: str):
    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE deposits SET status = ? WHERE order_id = ?",
            (status, order_id),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# ============================================================
# ADMIN: PAYMENTS PANEL
# ============================================================

async def admin_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT status, COUNT(*) as c, COALESCE(SUM(amount), 0) as s FROM deposits GROUP BY status"
        )
        rows = cur.fetchall()
        conn.close()
    except Exception:
        rows = []

    lines = ["💳 <b>PAYMENTS</b>", "━━━━━━━━━━━━━━━━━━━", ""]

    if not rows:
        lines.append("Abhi koi payment nahi hai.")
    else:
        for r in rows:
            status = (r["status"] or "unknown").upper()
            cnt = r["c"]
            amt = r["s"] or 0
            lines.append(f"• {status}: <b>{cnt}</b>  ({fmt_money(amt)})")

    lines.append("")
    lines.append("Filter by status:")

    text = "\n".join(lines)

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟡 Pending", callback_data="admin_pay_list:pending", style="danger"),
            InlineKeyboardButton("🟢 Paid", callback_data="admin_pay_list:paid", style="success"),
        ],
        [
            InlineKeyboardButton("🔴 Failed", callback_data="admin_pay_list:failed", style="danger"),
            InlineKeyboardButton("⚪ All", callback_data="admin_pay_list:all", style="primary"),
        ],
        [
            InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary"),
        ],
    ])

    await safe_edit(query, text, markup)


# ============================================================
# ADMIN: LIST DEPOSITS BY STATUS
# ============================================================

async def admin_pay_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    try:
        status = query.data.split(":", 1)[1]
    except Exception:
        status = "all"

    if status == "all":
        try:
            conn = database._conn()
            cur = conn.cursor()
            cur.execute("SELECT * FROM deposits ORDER BY id DESC LIMIT 20")
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
        except Exception:
            rows = []
    else:
        rows = get_deposits_by_status(status, limit=20)

    if not rows:
        text = f"💳 <b>DEPOSITS ({status.upper()})</b>\n\nAbhi koi deposit nahi hai."
        await safe_edit(query, text, back_to_payments())
        return

    lines = [f"💳 <b>DEPOSITS ({status.upper()})</b>", "━━━━━━━━━━━━━━━━━━━", ""]

    buttons = []

    for d in rows[:10]:
        oid = d.get("order_id") or "?"
        amount = d.get("amount") or 0
        st = (d.get("status") or "unknown").upper()
        date = fmt_date(d.get("created_at"))
        user_id = d.get("user_id")

        emoji = {
            "PENDING": "🟡",
            "PAID": "🟢",
            "FAILED": "🔴",
            "CANCELLED": "⚫",
        }.get(st, "⚪")

        lines.append(f"{emoji} <code>{oid[:20]}</code>")
        lines.append(f"👤 {user_id}  |  💰 {fmt_money(amount)}")
        lines.append(f"📅 {date}")
        lines.append("━━━━━━━━━━━━━━━━━━━")

        if st == "PENDING":
            buttons.append([
                InlineKeyboardButton(
                    f"✅ Credit {oid[:10]}",
                    callback_data=f"admin_pay_credit:{oid}",
                    style="success",
                ),
                InlineKeyboardButton(
                    f"❌ Reject",
                    callback_data=f"admin_pay_reject:{oid}",
                    style="danger",
                ),
            ])

    buttons.append([
        InlineKeyboardButton("‹ Back", callback_data="admin_payments", style="primary"),
    ])

    text = "\n".join(lines)
    markup = InlineKeyboardMarkup(buttons)

    await safe_edit(query, text, markup)


# ============================================================
# ADMIN: MANUALLY CREDIT
# ============================================================

async def admin_pay_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query, "Crediting...")

    if not is_admin(query.from_user.id):
        return

    try:
        order_id = query.data.split(":", 1)[1]
    except Exception:
        await safe_answer(query, "Invalid order.", show_alert=True)
        return

    deposit = get_deposit_by_order_id(order_id)
    if not deposit:
        await safe_answer(query, "Deposit not found.", show_alert=True)
        return

    if (deposit.get("status") or "").lower() == "paid":
        await safe_answer(query, "Already credited.", show_alert=True)
        return

    user_id = deposit.get("user_id")
    amount = float(deposit.get("amount") or 0)

    ok = database.credit_wallet(user_id, amount, reference=f"MANUAL-{order_id}")
    if not ok:
        await safe_answer(query, "Credit failed.", show_alert=True)
        return

    update_deposit_status(order_id, "paid")

    # User ko notification
    try:
        text = (
            f"✅ <b>PAYMENT CREDITED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Amount: <b>{fmt_money(amount)}</b>\n"
            f"🆔 Order: <code>{order_id}</code>\n\n"
            f"Admin ne aapka payment manually credit kar diya.\n"
            f"🕐 {fmt_date(time.time())}"
        )
        await context.bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await safe_answer(query, f"✅ {order_id} credited", show_alert=True)


# ============================================================
# ADMIN: REJECT
# ============================================================

async def admin_pay_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    try:
        order_id = query.data.split(":", 1)[1]
    except Exception:
        await safe_answer(query, "Invalid order.", show_alert=True)
        return

    deposit = get_deposit_by_order_id(order_id)
    if not deposit:
        await safe_answer(query, "Deposit not found.", show_alert=True)
        return

    if (deposit.get("status") or "").lower() == "paid":
        await safe_answer(query, "Already paid, can't reject.", show_alert=True)
        return

    update_deposit_status(order_id, "failed")

    user_id = deposit.get("user_id")

    try:
        text = (
            f"❌ <b>PAYMENT REJECTED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 Order: <code>{order_id}</code>\n"
            f"💰 Amount: <b>{fmt_money(deposit.get('amount') or 0)}</b>\n\n"
            f"Admin ne aapka payment reject kar diya.\n"
            f"⚠️ Koi problem ho to support se contact karein."
        )
        await context.bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await safe_answer(query, f"❌ {order_id} rejected", show_alert=True)


# ============================================================
# USER: MY DEPOSITS
# ============================================================

async def my_deposits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    user = query.from_user
    deposits = get_user_deposits(user.id, limit=10)

    if not deposits:
        text = (
            "💳 <b>MY DEPOSITS</b>\n\n"
            "Abhi koi deposit nahi kiya.\n\n"
            "Add Balance karke deposit karein."
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Add Balance", callback_data="wallet_add", style="success")],
            [InlineKeyboardButton("‹ Back", callback_data="my_profile", style="primary")],
        ])
        await safe_edit(query, text, markup)
        return

    lines = ["💳 <b>MY DEPOSITS</b>", "━━━━━━━━━━━━━━━━━━━", ""]

    for d in deposits:
        oid = d.get("order_id") or "?"
        amount = d.get("amount") or 0
        st = (d.get("status") or "unknown").upper()
        date = fmt_date(d.get("created_at"))

        emoji = {
            "PENDING": "🟡",
            "PAID": "🟢",
            "FAILED": "🔴",
            "CANCELLED": "⚫",
        }.get(st, "⚪")

        lines.append(f"{emoji} <code>{oid[:24]}</code>")
        lines.append(f"💰 {fmt_money(amount)}  |  {st}")
        lines.append(f"📅 {date}")
        lines.append("━━━━━━━━━━━━━━━━━━━")

    text = "\n".join(lines)

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Add Balance", callback_data="wallet_add", style="success")],
        [InlineKeyboardButton("‹ Back", callback_data="my_profile", style="primary")],
    ])

    await safe_edit(query, text, markup)


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        # Admin
        CallbackQueryHandler(admin_payments, pattern=r"^admin_payments$"),
        CallbackQueryHandler(admin_pay_list, pattern=r"^admin_pay_list:"),
        CallbackQueryHandler(admin_pay_credit, pattern=r"^admin_pay_credit:"),
        CallbackQueryHandler(admin_pay_reject, pattern=r"^admin_pay_reject:"),

        # User
        CallbackQueryHandler(my_deposits, pattern=r"^my_deposits$"),
    ]
