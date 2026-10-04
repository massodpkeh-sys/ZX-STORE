# handlers/admin_panel/users.py
# ============================================================
# ADMIN PANEL - USERS + BALANCE
# Single-message editing architecture
# ============================================================

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler, ContextTypes, MessageHandler, filters,
)

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
# USERS LIST
# ============================================================

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM users")
        total = cur.fetchone()["c"]
        cur.execute("SELECT telegram_id, first_name, username, balance FROM users ORDER BY id DESC LIMIT 10")
        recent = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception:
        total = 0
        recent = []

    lines = [
        f"👥 <b>USERS</b>",
        f"━━━━━━━━━━━━━━━━━━━",
        f"Total Users: <b>{total}</b>",
        f"━━━━━━━━━━━━━━━━━━━",
        "",
        "<b>Recent Users:</b>",
    ]

    for u in recent:
        tid = u.get("telegram_id")
        name = u.get("first_name") or "User"
        uname = u.get("username") or ""
        bal = u.get("balance") or 0
        line = f"• <code>{tid}</code>  {name}"
        if uname:
            line += f" (@{uname})"
        line += f"  ₹{bal:.2f}"
        lines.append(line)

    lines.append("")
    lines.append("User ID bhejein search ke liye.")

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Search User", callback_data="admin_user_search", style="primary")],
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
    ])

    await safe_edit(query, "\n".join(lines), markup)


# ============================================================
# SEARCH USER
# ============================================================

async def admin_user_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    context.user_data["admin_search_user"] = True

    text = (
        "🔍 <b>SEARCH USER</b>\n\n"
        "User ka Telegram ID bhejein.\n\n"
        "Example: <code>123456789</code>"
    )
    await safe_edit(query, text, back_admin())


async def admin_user_search_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_search_user"):
        return
    if not is_admin(update.effective_user.id):
        return
    if not update.message or not update.message.text:
        return

    context.user_data.pop("admin_search_user", None)

    try:
        target_id = int(update.message.text.strip())
    except Exception:
        await update.message.reply_text("❌ Invalid ID.")
        return

    user = database.get_user(target_id)
    if not user:
        await update.message.reply_text(f"❌ User {target_id} not found.")
        return

    balance = user.get("balance") or 0
    ref = user.get("referral_balance") or 0
    uname = user.get("username") or "-"

    text = (
        f"👤 <b>USER FOUND</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <code>{target_id}</code>\n"
        f"👤 Name: {user.get('first_name') or 'User'}\n"
        f"📛 Username: @{uname}\n"
        f"💰 Balance: <b>{fmt_money(balance)}</b>\n"
        f"🎁 Ref Balance: <b>{fmt_money(ref)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Add Balance", callback_data=f"adm_bal_add:{target_id}", style="success"),
            InlineKeyboardButton("➖ Deduct", callback_data=f"adm_bal_ded:{target_id}", style="danger"),
        ],
        [InlineKeyboardButton("‹ Back", callback_data="admin_users", style="primary")],
    ])

    try:
        await update.message.delete()
    except Exception:
        pass

    await update.effective_chat.send_message(text, parse_mode="HTML", reply_markup=markup)


# ============================================================
# ADD BALANCE
# ============================================================

async def adm_bal_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    target = query.data.split(":", 1)[1]
    context.user_data["admin_bal_action"] = "add"
    context.user_data["admin_bal_target"] = int(target)

    text = (
        f"➕ <b>ADD BALANCE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 User: <code>{target}</code>\n\n"
        f"Amount type karein (₹):\n\n"
        f"Example: <code>100</code>"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_users", style="danger")],
    ])
    await safe_edit(query, text, markup)


# ============================================================
# DEDUCT BALANCE
# ============================================================

async def adm_bal_ded_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    target = query.data.split(":", 1)[1]
    context.user_data["admin_bal_action"] = "deduct"
    context.user_data["admin_bal_target"] = int(target)

    text = (
        f"➖ <b>DEDUCT BALANCE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 User: <code>{target}</code>\n\n"
        f"Amount type karein (₹):\n\n"
        f"Example: <code>50</code>"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_users", style="danger")],
    ])
    await safe_edit(query, text, markup)


# ============================================================
# BALANCE SAVE
# ============================================================

async def adm_bal_amount_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get("admin_bal_action")
    target = context.user_data.get("admin_bal_target")
    if not action or not target:
        return
    if not is_admin(update.effective_user.id):
        return
    if not update.message or not update.message.text:
        return

    try:
        await update.message.delete()
    except Exception:
        pass

    try:
        amount = float(update.message.text.strip().replace(",", ""))
        if amount <= 0:
            raise ValueError()
    except Exception:
        await update.effective_chat.send_message("❌ Invalid amount.")
        return

    context.user_data.pop("admin_bal_action", None)
    context.user_data.pop("admin_bal_target", None)

    if action == "add":
        database.credit_wallet(target, amount, "ADMIN-ADD")
        msg = f"✅ ₹{amount:.2f} added to <code>{target}</code>"
        user_msg = f"💰 <b>Balance Added</b>\n\nAdmin ne aapko <b>{fmt_money(amount)}</b> diya."
    else:
        user = database.get_user(target)
        bal = float(user.get("balance") or 0) if user else 0
        if bal < amount:
            await update.effective_chat.send_message(f"❌ User balance: {fmt_money(bal)}")
            return
        database.debit_wallet(target, amount, "ADMIN-DEDUCT")
        msg = f"✅ ₹{amount:.2f} deducted from <code>{target}</code>"
        user_msg = f"💸 <b>Balance Deducted</b>\n\nAdmin ne <b>{fmt_money(amount)}</b> deduct kiya."

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("‹ Users", callback_data="admin_users", style="primary")],
    ])

    await update.effective_chat.send_message(msg, parse_mode="HTML", reply_markup=markup)

    try:
        await context.bot.send_message(chat_id=target, text=user_msg, parse_mode="HTML")
    except Exception:
        pass


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(admin_users, pattern=r"^admin_users$"),
        CallbackQueryHandler(admin_user_search, pattern=r"^admin_user_search$"),
        CallbackQueryHandler(adm_bal_add_start, pattern=r"^adm_bal_add:"),
        CallbackQueryHandler(adm_bal_ded_start, pattern=r"^adm_bal_ded:"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_user_search_msg),
        MessageHandler(filters.TEXT & ~filters.COMMAND, adm_bal_amount_msg),
    ]
