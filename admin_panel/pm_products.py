# handlers/admin_panel/pm_products.py
# ============================================================
# ADMIN PANEL - PM PRODUCTS MANAGE
# ============================================================

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from handlers.admin_panel.menu import is_admin, safe_answer, safe_edit

logger = logging.getLogger(__name__)


async def pm_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    text = (
        "📋 <b>PRODUCTS MANAGE</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "👇 Option select karein:"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add New Product", callback_data="pm_add", style="success")],
        [InlineKeyboardButton("✏️ Edit Product", callback_data="pm_edit", style="primary")],
        [InlineKeyboardButton("❌ Delete Product", callback_data="pm_delete", style="danger")],
        [InlineKeyboardButton("👁️ View All Products", callback_data="admin_products", style="primary")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="admin_pm", style="primary")],
    ])

    await safe_edit(query, text, markup)


async def pm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    import database
    products = database.get_products()

    if not products:
        await safe_edit(query, "❌ Koi product nahi hai.", InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="pm_products", style="primary")],
        ]))
        return

    buttons = []
    for p in products:
        pid = p.get("supplier_pid")
        name = p.get("display_name") or p.get("name") or "?"
        buttons.append([
            InlineKeyboardButton(
                f"❌ {name}",
                callback_data=f"pm_del_confirm:{pid}",
                style="danger",
            )
        ])

    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="pm_products", style="primary")])

    text = "🗑️ <b>DELETE PRODUCT</b>\n━━━━━━━━━━━━━━━━━━━\n\nKaunsa product delete karna hai?"
    await safe_edit(query, text, InlineKeyboardMarkup(buttons))


async def pm_del_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    pid = query.data.split(":", 1)[1]
    context.user_data["pm_delete_pid"] = pid

    text = (
        f"⚠️ <b>CONFIRM DELETE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 PID: <code>{pid}</code>\n\n"
        f"Kya aap ye product delete karna chahte hain?\n"
        f"<i>Ye action undo nahi hoga.</i>"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, Delete", callback_data="pm_del_do", style="danger")],
        [InlineKeyboardButton("❌ Cancel", callback_data="pm_products", style="primary")],
    ])
    await safe_edit(query, text, markup)


async def pm_del_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query, "Deleting...")
    if not is_admin(query.from_user.id):
        return

    pid = context.user_data.pop("pm_delete_pid", None)
    if not pid:
        await safe_edit(query, "❌ Session expired.", InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="pm_products", style="primary")],
        ]))
        return

    try:
        import database
        conn = database._conn()
        cur = conn.cursor()
        # Delete durations first
        cur.execute(
            "DELETE FROM durations WHERE product_id = (SELECT id FROM products WHERE supplier_pid = ?)",
            (str(pid),),
        )
        # Delete product
        cur.execute("DELETE FROM products WHERE supplier_pid = ?", (str(pid),))
        conn.commit()
        conn.close()

        text = f"✅ <b>Product Deleted</b>\n\n🆔 PID: <code>{pid}</code>"
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Products Manage", callback_data="pm_products", style="success")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="admin_pm", style="primary")],
        ])
        await safe_edit(query, text, markup)
    except Exception as e:
        logger.exception("Delete failed")
        await safe_edit(query, f"❌ Error: {str(e)[:150]}", InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="pm_products", style="primary")],
        ]))


def get_handlers():
    return [
        CallbackQueryHandler(pm_products, pattern=r"^pm_products$"),
        CallbackQueryHandler(pm_delete, pattern=r"^pm_delete$"),
        CallbackQueryHandler(pm_del_confirm, pattern=r"^pm_del_confirm:"),
        CallbackQueryHandler(pm_del_do, pattern=r"^pm_del_do$"),
    ]
