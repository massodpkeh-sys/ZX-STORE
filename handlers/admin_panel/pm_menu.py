# handlers/admin_panel/pm_menu.py
# ============================================================
# ADMIN PANEL - PRODUCT MANAGEMENT MAIN MENU
# ============================================================

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from handlers.admin_panel.menu import is_admin, safe_answer, safe_edit

logger = logging.getLogger(__name__)


async def pm_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    text = (
        "📦 <b>PRODUCT MANAGEMENT</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "👇 Option select karein:"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Products Manage", callback_data="pm_products", style="success")],
        [InlineKeyboardButton("➕ Add New Product", callback_data="pm_add", style="success")],
        [InlineKeyboardButton("✏️ Edit Product", callback_data="pm_edit", style="primary")],
        [InlineKeyboardButton("💰 Pricing Manage", callback_data="pm_pricing", style="primary")],
        [InlineKeyboardButton("🎬 Demo Video Manage", callback_data="pm_demo", style="primary")],
        [InlineKeyboardButton("👁️ View All Products", callback_data="admin_products", style="primary")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="admin_home", style="danger")],
    ])

    await safe_edit(query, text, markup)


def get_handlers():
    return [
        CallbackQueryHandler(pm_main, pattern=r"^admin_pm$"),
    ]
