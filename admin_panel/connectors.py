# handlers/admin_panel/connectors.py
# ============================================================
# ADMIN PANEL - CONNECTORS
# Settings | Coupons | Payments | Roles
# ============================================================

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from handlers.admin_panel.menu import is_admin, safe_answer

logger = logging.getLogger(__name__)


# ============================================================
# SETTINGS
# ============================================================

async def admin_settings_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    try:
        from handlers.settings import admin_settings
        await admin_settings(update, context)
    except Exception as e:
        logger.exception("Settings failed")
        await safe_answer(query, f"❌ Settings error: {str(e)[:150]}", show_alert=True)


# ============================================================
# COUPONS
# ============================================================

async def admin_coupons_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    try:
        from handlers.coupons import admin_coupons
        await admin_coupons(update, context)
    except Exception as e:
        logger.exception("Coupons failed")
        await safe_answer(query, f"❌ Coupons error: {str(e)[:150]}", show_alert=True)


# ============================================================
# PAYMENTS
# ============================================================

async def admin_payments_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    try:
        from handlers.payments import admin_payments
        await admin_payments(update, context)
    except Exception as e:
        logger.exception("Payments failed")
        await safe_answer(query, f"❌ Payments error: {str(e)[:150]}", show_alert=True)


# ============================================================
# ROLES
# ============================================================

async def admin_roles_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    try:
        from handlers.roles import admin_roles
        await admin_roles(update, context)
    except Exception as e:
        logger.exception("Roles failed")
        await safe_answer(query, f"❌ Roles error: {str(e)[:150]}", show_alert=True)


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(admin_settings_cb, pattern=r"^admin_settings$"),
        CallbackQueryHandler(admin_coupons_cb, pattern=r"^admin_coupons$"),
        CallbackQueryHandler(admin_payments_cb, pattern=r"^admin_payments$"),
        CallbackQueryHandler(admin_roles_cb, pattern=r"^admin_roles$"),
    ]
