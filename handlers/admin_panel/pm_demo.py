# handlers/admin_panel/pm_demo.py
# ============================================================
# ADMIN PANEL - DEMO VIDEO MANAGE
# ============================================================

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler, ContextTypes, MessageHandler, filters,
)

import database
from handlers.admin_panel.menu import is_admin, safe_answer, safe_edit

logger = logging.getLogger(__name__)


async def pm_demo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    products = database.get_products()

    buttons = []
    for p in products:
        pid = p.get("supplier_pid")
        name = p.get("display_name") or p.get("name") or "?"
        buttons.append([
            InlineKeyboardButton(f"🎬 {name}", callback_data=f"pm_demo_sel:{pid}", style="primary")
        ])

    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="pm_products", style="primary")])

    text = "🎬 <b>DEMO VIDEO MANAGE</b>\n━━━━━━━━━━━━━━━━━━━\n\nProduct select karein:"
    await safe_edit(query, text, InlineKeyboardMarkup(buttons))


async def pm_demo_sel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    pid = query.data.split(":", 1)[1]
    product = database.get_product(pid)
    if not product:
        return

    context.user_data["pm_demo_pid"] = pid
    context.user_data["pm_demo_stage"] = "input"

    name = product.get("display_name") or product.get("name")
    current = product.get("demo_link") or ""

    text = (
        f"🎬 <b>EDIT DEMO VIDEO</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 {name}\n"
        f"🔗 Current: {current if current else '(none)'}\n\n"
        f"👇 Naya YouTube link bhejein:\n"
        f"Example: <code>https://youtube.com/...</code>"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="pm_demo", style="primary")],
    ])
    await safe_edit(query, text, markup)


async def pm_demo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if not is_admin(update.effective_user.id):
        return
    if context.user_data.get("pm_demo_stage") != "input":
        return

    link = update.message.text.strip()
    pid = context.user_data.get("pm_demo_pid")

    try:
        await update.message.delete()
    except Exception:
        pass

    if not pid:
        return

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(products)")
        cols = [r[1] for r in cur.fetchall()]
        if "demo_link" not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN demo_link TEXT")
        cur.execute("UPDATE products SET demo_link = ? WHERE supplier_pid = ?", (link, str(pid)))
        conn.commit()
        conn.close()

        await update.effective_chat.send_message(
            f"✅ <b>Demo Link Updated!</b>\n\n🔗 {link}",
            parse_mode="HTML",
        )
    except Exception as e:
        await update.effective_chat.send_message(f"❌ Error: {str(e)[:100]}")

    context.user_data.pop("pm_demo_stage", None)
    context.user_data.pop("pm_demo_pid", None)


def get_handlers():
    return [
        CallbackQueryHandler(pm_demo, pattern=r"^pm_demo$"),
        CallbackQueryHandler(pm_demo_sel, pattern=r"^pm_demo_sel:"),
        CallbackQueryHandler(pm_demo_sel, pattern=r"^pm_demo_prod$"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, pm_demo_message),
    ]
