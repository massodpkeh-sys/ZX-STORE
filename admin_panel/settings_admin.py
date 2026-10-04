# handlers/admin_panel/settings_admin.py
# ============================================================
# ADMIN PANEL - SETTINGS CONNECTOR
# Single-message editing architecture
# ============================================================

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from handlers.admin_panel.menu import is_admin, safe_answer

logger = logging.getLogger(__name__)


async def settings_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Settings panel — connector to handlers.settings"""
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    try:
        from handlers.settings import admin_settings
        await admin_settings(update, context)
    except Exception as e:
        logger.exception("Settings failed")
        await safe_answer(query, f"❌ Error: {str(e)[:150]}", show_alert=True)


def get_handlers():
    return [
        CallbackQueryHandler(settings_cb, pattern=r"^admin_settings$"),
    ]
