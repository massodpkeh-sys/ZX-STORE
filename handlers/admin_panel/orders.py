# handlers/admin_panel/orders.py
# ============================================================
# ADMIN PANEL - ORDERS
# Single-message editing architecture
# ============================================================

from __future__ import annotations

import logging
from datetime import datetime

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


def fmt_date(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%d %b %Y | %I:%M %p")
    except Exception:
        return "—"


# ============================================================
# ORDERS LIST
# ============================================================

async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 20")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception:
        logger.exception("Orders failed")
        rows = []

    if not rows:
        await safe_edit(query, "📦 <b>ORDERS</b>\n\nAbhi koi order nahi.", back_admin())
        return

    lines = [f"📦 <b>RECENT ORDERS</b> ({len(rows)})", "━━━━━━━━━━━━━━━━━━━", ""]

    for o in rows[:10]:
        oid = o.get("order_ref") or f"#{o['id']}"
        pname = o.get("product_name") or o.get("product_id") or "?"
        price = o.get("price") or 0
        date = fmt_date(o.get("created_at"))
        uid = o.get("user_id") or "?"

        lines.append(f"🆔 <code>{oid}</code>")
        lines.append(f"👤 <code>{uid}</code>")
        lines.append(f"📦 {pname}")
        lines.append(f"💰 {fmt_money(price)}  |  📅 {date}")
        lines.append("━━━━━━━━━━━━━━━━━━━")

    await safe_edit(query, "\n".join(lines), back_admin())


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(admin_orders, pattern=r"^admin_orders$"),
    ]
