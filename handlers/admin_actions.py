# handlers/admin_actions.py
# ============================================================
# ABHAY PANEL STORE - ADMIN ACTIONS
# User Balance + Product Edit + Logs
# ============================================================

from __future__ import annotations

import logging
import time
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
import database

logger = logging.getLogger(__name__)

ADMIN_ID = 8910147515
STORE_NAME = getattr(config, "STORE_NAME", "ABHAY PANEL STORE")


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


def back_to_admin():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")]
    ])


# ============================================================
# ADMIN BALANCE ADD — Step 1: User Search
# ============================================================

async def admin_balance_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    context.user_data["admin_balance_search"] = True

    text = (
        "💰 <b>ADMIN BALANCE MANAGEMENT</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "User ka Telegram ID bhejein.\n\n"
        "Example: <code>123456789</code>"
    )

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=back_to_admin())


async def admin_balance_search_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_balance_search"):
        return
    if not is_admin(update.effective_user.id):
        return

    context.user_data.pop("admin_balance_search", None)

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

    text = (
        f"👤 <b>USER FOUND</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{target_id}</code>\n"
        f"👤 Name: {user.get('first_name') or 'User'}\n"
        f"💰 Balance: <b>{fmt_money(balance)}</b>\n\n"
        f"Kya karna hai?"
    )

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Add", callback_data=f"adm_bal_add:{target_id}", style="success"),
            InlineKeyboardButton("➖ Deduct", callback_data=f"adm_bal_ded:{target_id}", style="danger"),
        ],
        [
            InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary"),
        ],
    ])

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)


# ============================================================
# ADD BALANCE
# ============================================================

async def adm_bal_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    try:
        target_id = int(query.data.split(":", 1)[1])
    except Exception:
        await safe_answer(query, "Invalid ID.", show_alert=True)
        return

    context.user_data["admin_bal_action"] = "add"
    context.user_data["admin_bal_target"] = target_id

    text = (
        f"➕ <b>ADD BALANCE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 User ID: <code>{target_id}</code>\n\n"
        f"Amount type karein (₹ me):\n\n"
        f"Example: <code>100</code>"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_home", style="danger")],
    ])

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)


async def adm_bal_ded_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    try:
        target_id = int(query.data.split(":", 1)[1])
    except Exception:
        await safe_answer(query, "Invalid ID.", show_alert=True)
        return

    context.user_data["admin_bal_action"] = "deduct"
    context.user_data["admin_bal_target"] = target_id

    text = (
        f"➖ <b>DEDUCT BALANCE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 User ID: <code>{target_id}</code>\n\n"
        f"Amount type karein (₹ me):\n\n"
        f"Example: <code>50</code>"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_home", style="danger")],
    ])

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)


async def adm_bal_amount_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get("admin_bal_action")
    target_id = context.user_data.get("admin_bal_target")

    if not action or not target_id:
        return

    if not is_admin(update.effective_user.id):
        return

    try:
        amount = float(update.message.text.strip().replace(",", ""))
        if amount <= 0:
            raise ValueError()
    except Exception:
        await update.message.reply_text("❌ Invalid amount.")
        return

    # Clear state
    context.user_data.pop("admin_bal_action", None)
    context.user_data.pop("admin_bal_target", None)

    # Execute
    if action == "add":
        database.credit_wallet(target_id, amount, reference="ADMIN-ADD")
        msg = f"✅ ₹{amount:.2f} added to <code>{target_id}</code>"
    else:
        # Deduct
        user = database.get_user(target_id)
        balance = float(user.get("balance") or 0) if user else 0
        if balance < amount:
            await update.message.reply_text(
                f"❌ User balance {fmt_money(balance)}, can't deduct {fmt_money(amount)}."
            )
            return
        database.debit_wallet(target_id, amount, reference="ADMIN-DEDUCT")
        msg = f"✅ ₹{amount:.2f} deducted from <code>{target_id}</code>"

    await update.message.reply_text(msg, parse_mode="HTML")

    # Notify user
    try:
        if action == "add":
            user_text = (
                f"💰 <b>BALANCE ADDED</b>\n\n"
                f"Admin ne aapke wallet me <b>{fmt_money(amount)}</b> add kiya.\n\n"
                f"🕐 {fmt_date(time.time())}"
            )
        else:
            user_text = (
                f"💸 <b>BALANCE DEDUCTED</b>\n\n"
                f"Admin ne aapke wallet se <b>{fmt_money(amount)}</b> deduct kiya.\n\n"
                f"🕐 {fmt_date(time.time())}"
            )

        await context.bot.send_message(
            chat_id=target_id,
            text=user_text,
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ============================================================
# PRODUCT EDIT — DISPLAY PRICE
# ============================================================

async def admin_prod_price_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    try:
        pid = query.data.split(":", 1)[1]
    except Exception:
        await safe_answer(query, "Invalid.", show_alert=True)
        return

    product = database.get_product(pid)
    if not product:
        await safe_answer(query, "Product not found.", show_alert=True)
        return

    context.user_data["admin_price_pid"] = pid

    name = product.get("display_name") or product.get("name")
    durations = product.get("durations", [])

    lines = [f"💰 <b>EDIT PRICE</b>", f"━━━━━━━━━━━━━━━━━━━", f"📦 {name}", ""]
    for i, d in enumerate(durations):
        dn = d.get("display_duration") or d.get("duration")
        price = d.get("display_price") or 0
        lines.append(f"{i+1}. {dn} — Current: {fmt_money(price)}")

    lines.append("")
    lines.append("Kaunsa duration change karna hai?")
    lines.append("Format: <code>1 149</code> (number + new price)")

    text = "\n".join(lines)

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=back_to_admin())


async def admin_price_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = context.user_data.get("admin_price_pid")
    if not pid:
        return

    if not is_admin(update.effective_user.id):
        return

    parts = update.message.text.strip().split()
    if len(parts) != 2:
        await update.message.reply_text("❌ Format: <code>1 149</code>", parse_mode="HTML")
        return

    try:
        index = int(parts[0]) - 1
        new_price = float(parts[1])
    except Exception:
        await update.message.reply_text("❌ Invalid input.")
        return

    product = database.get_product(pid)
    if not product:
        await update.message.reply_text("❌ Product not found.")
        return

    durations = product.get("durations", [])
    if index < 0 or index >= len(durations):
        await update.message.reply_text("❌ Invalid number.")
        return

    target_dur = durations[index]
    dur_name = target_dur.get("duration")

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute(
            """UPDATE durations 
               SET display_price = ? 
               WHERE product_id = (SELECT id FROM products WHERE supplier_pid = ?)
                 AND duration = ?""",
            (new_price, str(pid), dur_name),
        )
        conn.commit()
        conn.close()

        await update.message.reply_text(
            f"✅ Price updated for <code>{dur_name}</code>: <b>{fmt_money(new_price)}</b>",
            parse_mode="HTML",
        )
    except Exception:
        logger.exception("Price update failed")
        await update.message.reply_text("❌ Update failed.")

    context.user_data.pop("admin_price_pid", None)


# ============================================================
# AUDIT LOGS
# ============================================================

async def admin_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    # Recent orders
    try:
        conn = database._conn()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) as c FROM users")
        total_users = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM orders")
        total_orders = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM deposits WHERE status='paid'")
        total_deposits = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM support_tickets")
        try:
            total_tickets = cur.fetchone()["c"]
        except Exception:
            total_tickets = 0

        conn.close()
    except Exception:
        logger.exception("Logs failed")
        return

    text = (
        f"📝 <b>AUDIT LOGS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Total Users: <b>{total_users}</b>\n"
        f"📦 Total Orders: <b>{total_orders}</b>\n"
        f"💳 Paid Deposits: <b>{total_deposits}</b>\n"
        f"🎫 Support Tickets: <b>{total_tickets}</b>\n\n"
        f"<i>Detailed logs Phase 3 me aayenge.</i>"
    )

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=back_to_admin())


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        # Balance management
        CallbackQueryHandler(admin_balance_entry, pattern=r"^admin_balance$"),
        CallbackQueryHandler(adm_bal_add_start, pattern=r"^adm_bal_add:"),
        CallbackQueryHandler(adm_bal_ded_start, pattern=r"^adm_bal_ded:"),

        # Product price edit
        CallbackQueryHandler(admin_prod_price_start, pattern=r"^admin_prod_price:"),

        # Logs
        CallbackQueryHandler(admin_logs, pattern=r"^admin_logs$"),

        # Message handlers
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            admin_balance_search_message,
        ),
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            adm_bal_amount_message,
        ),
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            admin_price_message,
        ),
    ]
