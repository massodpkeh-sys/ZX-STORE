# handlers/admin_panel/dashboard.py
# ============================================================
# ADMIN PANEL - DASHBOARD + STATISTICS
# Single-message editing architecture
# ============================================================

from __future__ import annotations

import logging
import time

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
# DASHBOARD
# ============================================================

async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    try:
        conn = database._conn()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) as c FROM users")
        total_users = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM orders")
        total_orders = cur.fetchone()["c"]

        cur.execute("SELECT COALESCE(SUM(price), 0) as s FROM orders")
        total_revenue = cur.fetchone()["s"] or 0

        cur.execute("SELECT COALESCE(SUM(amount), 0) as s FROM deposits WHERE status='paid'")
        total_dep = cur.fetchone()["s"] or 0

        cur.execute("SELECT COUNT(*) as c FROM products")
        total_prod = cur.fetchone()["c"]

        conn.close()
    except Exception:
        logger.exception("Dashboard failed")
        total_users = total_orders = total_revenue = total_dep = total_prod = 0

    text = (
        f"📊 <b>DASHBOARD</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users: <b>{total_users}</b>\n"
        f"📦 Total Orders: <b>{total_orders}</b>\n"
        f"🛍 Total Products: <b>{total_prod}</b>\n"
        f"💰 Total Revenue: <b>{fmt_money(total_revenue)}</b>\n"
        f"💵 Total Deposits: <b>{fmt_money(total_dep)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )

    await safe_edit(query, text, back_admin())


# ============================================================
# STATISTICS
# ============================================================

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    try:
        conn = database._conn()
        cur = conn.cursor()
        now = int(time.time())
        day = now - 86400
        week = now - 604800

        cur.execute("SELECT COUNT(*) as c FROM orders WHERE created_at >= ?", (day,))
        t_orders = cur.fetchone()["c"]

        cur.execute("SELECT COALESCE(SUM(price),0) as s FROM orders WHERE created_at >= ?", (day,))
        t_rev = cur.fetchone()["s"] or 0

        cur.execute("SELECT COUNT(*) as c FROM users WHERE created_at >= ?", (day,))
        t_users = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM orders WHERE created_at >= ?", (week,))
        w_orders = cur.fetchone()["c"]

        cur.execute("SELECT COALESCE(SUM(price),0) as s FROM orders WHERE created_at >= ?", (week,))
        w_rev = cur.fetchone()["s"] or 0

        cur.execute("SELECT COUNT(*) as c FROM users WHERE created_at >= ?", (week,))
        w_users = cur.fetchone()["c"]

        conn.close()
    except Exception:
        logger.exception("Stats failed")
        t_orders = t_rev = t_users = w_orders = w_rev = w_users = 0

    text = (
        f"📈 <b>STATISTICS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<b>📅 Today</b>\n"
        f"👥 New Users: <b>{t_users}</b>\n"
        f"📦 Orders: <b>{t_orders}</b>\n"
        f"💰 Revenue: <b>{fmt_money(t_rev)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<b>📅 This Week</b>\n"
        f"👥 New Users: <b>{w_users}</b>\n"
        f"📦 Orders: <b>{w_orders}</b>\n"
        f"💰 Revenue: <b>{fmt_money(w_rev)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )

    await safe_edit(query, text, back_admin())


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(admin_dashboard, pattern=r"^admin_dashboard$"),
        CallbackQueryHandler(admin_stats, pattern=r"^admin_stats$"),
    ]
