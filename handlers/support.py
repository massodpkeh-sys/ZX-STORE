# handlers/support.py
# ============================================================
# ABHAY PANEL STORE - SUPPORT TICKET SYSTEM
# Single-message editing architecture
# ============================================================

from __future__ import annotations

import logging
import random
import string
import time
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
import database

logger = logging.getLogger(__name__)

ADMIN_ID = 8910147515
STORE_NAME = "ABHAY PANEL STORE"


# ============================================================
# HELPERS
# ============================================================

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
# INIT SUPPORT TABLE
# ============================================================

def init_support_tables():
    try:
        conn = database._conn()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_ref TEXT UNIQUE,
                user_id INTEGER,
                subject TEXT,
                message TEXT,
                status TEXT DEFAULT 'OPEN',
                admin_reply TEXT,
                created_at INTEGER,
                updated_at INTEGER
            )
        """)

        conn.commit()
        conn.close()
    except Exception:
        logger.exception("Support table init failed")


# ============================================================
# DB FUNCTIONS
# ============================================================

def create_ticket(user_id: int, subject: str, message: str) -> str:
    init_support_tables()
    ticket_ref = "TKT-" + "".join(
        random.choices(string.ascii_uppercase + string.digits, k=6)
    )

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO support_tickets 
               (ticket_ref, user_id, subject, message, status, created_at, updated_at) 
               VALUES (?, ?, ?, ?, 'OPEN', ?, ?)""",
            (ticket_ref, user_id, subject, message, int(time.time()), int(time.time())),
        )
        conn.commit()
        conn.close()
        return ticket_ref
    except Exception:
        logger.exception("Ticket create failed")
        return ""


def get_ticket_by_ref(ticket_ref: str):
    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM support_tickets WHERE ticket_ref = ?", (ticket_ref,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def get_user_tickets(user_id: int, limit: int = 5):
    try:
        init_support_tables()
        conn = database._conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM support_tickets WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def reply_to_ticket(ticket_ref: str, reply: str) -> bool:
    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute(
            """UPDATE support_tickets 
               SET admin_reply = ?, status = 'REPLIED', updated_at = ? 
               WHERE ticket_ref = ?""",
            (reply, int(time.time()), ticket_ref),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# ============================================================
# SUPPORT SCREEN
# ============================================================

async def support_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    text = (
        "🆘 <b>SUPPORT CENTER</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🤝 Need Any Help?\n\n"
        "🛒 Purchase Support\n"
        "💳 Payment Issues\n"
        "🔑 Key Problems\n"
        "⚡ Instant Assistance\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "👤 Admin: @H4X_JOD_ABHAY\n"
        "🕐 24x7 Active Support\n\n"
        "⚠️ <b>Contact Admin If:</b>\n"
        "• Balance nahi aaya\n"
        "• Key nahi mila\n"
        "• Purchase problem"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Create Ticket", callback_data="support_create", style="success")],
        [InlineKeyboardButton("📋 My Tickets", callback_data="support_my", style="primary")],
        [InlineKeyboardButton("‹ Back", callback_data="main_menu", style="primary")],
    ])

    await safe_edit(query, text, markup)


# ============================================================
# CREATE TICKET
# ============================================================

async def support_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    context.user_data["support_waiting"] = True

    text = (
        "📩 <b>CREATE SUPPORT TICKET</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Apna problem likhkar bhejein.\n\n"
        "📝 <b>Example:</b>\n"
        "• Balance add kiya but nahi aaya\n"
        "• Order ID: ORD-XXXX\n"
        "• Problem: ...\n\n"
        "⚠️ Ek hi message me poori detail bhejein."
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="support", style="danger")],
    ])

    await safe_edit(query, text, markup)


# ============================================================
# RECEIVE TICKET
# ============================================================

async def support_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("support_waiting"):
        return
    if not update.message or not update.message.text:
        return

    context.user_data.pop("support_waiting", None)

    user = update.effective_user
    message_text = update.message.text.strip()

    # Delete user's message
    try:
        await update.message.delete()
    except Exception:
        pass

    if len(message_text) < 5:
        await update.effective_chat.send_message("❌ Message too short.")
        return

    # Create ticket
    ticket_ref = create_ticket(
        user_id=user.id,
        subject=message_text[:50],
        message=message_text,
    )

    if not ticket_ref:
        await update.effective_chat.send_message("❌ Ticket create nahi hua. Try again.")
        return

    # Confirmation
    text = (
        f"✅ <b>TICKET CREATED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 Ticket: <code>{ticket_ref}</code>\n"
        f"📝 Status: <b>OPEN</b>\n\n"
        f"⏳ Admin jald reply karega.\n"
        f"🕐 24x7 Active Support\n\n"
        f"📩 Reply aapko yahin milegi."
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("‹ Back", callback_data="main_menu", style="primary")],
    ])

    await update.effective_chat.send_message(text, parse_mode="HTML", reply_markup=markup)

    # Admin notification
    admin_text = (
        f"🆘 <b>NEW SUPPORT TICKET</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 Ticket: <code>{ticket_ref}</code>\n"
        f"👤 User: <code>{user.id}</code>\n"
        f"👤 Name: {user.first_name or 'User'}\n\n"
        f"📝 <b>Message:</b>\n{message_text}\n\n"
        f"💬 Reply: <code>/reply {ticket_ref} your reply</code>"
    )
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID, text=admin_text, parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ============================================================
# MY TICKETS
# ============================================================

async def support_my(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    user = query.from_user
    tickets = get_user_tickets(user.id, limit=5)

    if not tickets:
        text = (
            "📋 <b>MY TICKETS</b>\n\n"
            "Aapne abhi koi ticket create nahi kiya.\n\n"
            "📩 Create Ticket button dabakar naya ticket banayein."
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 Create Ticket", callback_data="support_create", style="success")],
            [InlineKeyboardButton("‹ Back", callback_data="support", style="primary")],
        ])
        await safe_edit(query, text, markup)
        return

    lines = ["📋 <b>MY TICKETS</b>", "━━━━━━━━━━━━━━━━━━━", ""]

    for t in tickets:
        ref = t.get("ticket_ref") or "?"
        status = t.get("status") or "OPEN"
        subject = t.get("subject") or "-"
        reply = t.get("admin_reply") or ""

        status_emoji = {
            "OPEN": "🟡", "REPLIED": "🟢", "CLOSED": "🔴",
        }.get(status, "⚪")

        lines.append(f"{status_emoji} <code>{ref}</code>  [{status}]")
        lines.append(f"📝 {subject[:50]}")

        if reply:
            lines.append(f"💬 <b>Admin:</b> {reply[:100]}")

        lines.append("━━━━━━━━━━━━━━━━━━━")

    text = "\n".join(lines)

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 New Ticket", callback_data="support_create", style="success")],
        [InlineKeyboardButton("‹ Back", callback_data="support", style="primary")],
    ])

    await safe_edit(query, text, markup)


# ============================================================
# ADMIN REPLY
# ============================================================

async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id != ADMIN_ID:
        return

    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            "❌ Usage: <code>/reply TKT-XXXX your reply</code>",
            parse_mode="HTML",
        )
        return

    ticket_ref = args[0]
    reply_text = " ".join(args[1:])

    ticket = get_ticket_by_ref(ticket_ref)
    if not ticket:
        await update.message.reply_text(f"❌ Ticket {ticket_ref} not found.")
        return

    ok = reply_to_ticket(ticket_ref, reply_text)
    if not ok:
        await update.message.reply_text("❌ Reply save nahi hua.")
        return

    user_id = ticket.get("user_id")
    if user_id:
        text = (
            f"💬 <b>SUPPORT REPLY</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 Ticket: <code>{ticket_ref}</code>\n"
            f"📝 Subject: {ticket.get('subject', '-')}\n\n"
            f"👤 <b>Admin Reply:</b>\n{reply_text}\n\n"
            f"✅ Ticket resolved."
        )

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("‹ Back", callback_data="main_menu", style="primary")],
        ])

        try:
            await context.bot.send_message(
                chat_id=user_id, text=text, parse_mode=ParseMode.HTML, reply_markup=markup,
            )
        except Exception:
            pass

    await update.message.reply_text(
        f"✅ Reply sent for <code>{ticket_ref}</code>",
        parse_mode="HTML",
    )


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(support_screen, pattern=r"^support$"),
        CallbackQueryHandler(support_create, pattern=r"^support_create$"),
        CallbackQueryHandler(support_my, pattern=r"^support_my$"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, support_receive),
    ]
