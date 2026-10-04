# handlers/admin_panel/menu.py
# ============================================================
# ADMIN PANEL - MAIN MENU + ROUTER
# Single-message editing architecture
# ============================================================

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

import config

logger = logging.getLogger(__name__)

ADMIN_ID = 8910147515
STORE_NAME = getattr(config, "STORE_NAME", "ABHAY PANEL STORE")


# ============================================================
# HELPERS
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


async def safe_answer(query, text=None, show_alert=False):
    try:
        if text is not None:
            await query.answer(text, show_alert=show_alert)
        else:
            await query.answer()
    except Exception:
        pass


async def safe_edit(query, text, reply_markup=None):
    """
    SAME MESSAGE EDIT — koi naya message nahi.
    Ye function poore bot me use hoga.
    """
    try:
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
    except Exception as e:
        # Agar message edit nahi ho sakta (e.g. photo caption), to fallback
        try:
            await query.edit_message_caption(
                caption=text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
        except Exception:
            # Last fallback — naya message (sirf tab jab edit possible na ho)
            try:
                await query.message.reply_text(
                    text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                    disable_web_page_preview=True,
                )
            except Exception:
                pass


def back_admin():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")]
    ])


# ============================================================
# MAIN MENU
# ============================================================

def admin_main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Dashboard", callback_data="admin_dashboard", style="success"),
            InlineKeyboardButton("📈 Statistics", callback_data="admin_stats", style="success"),
       ],
        [
            InlineKeyboardButton("🛍 Products", callback_data="admin_products", style="primary"),
            InlineKeyboardButton("📦 Orders", callback_data="admin_orders", style="primary"),
        ],
        [
            InlineKeyboardButton("📦 Product Management", callback_data="admin_pm", style="success"),
        ],
        [
            InlineKeyboardButton("👥 Users", callback_data="admin_users", style="primary"),
            InlineKeyboardButton("💰 Wallet", callback_data="admin_wallet", style="primary"),
        ],
        [
            InlineKeyboardButton("👑 Reseller", callback_data="admin_reseller_menu", style="primary"),
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast", style="danger"),
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings", style="danger"),
            InlineKeyboardButton("❌ Close", callback_data="admin_close", style="danger"),
        ],
    ])


def admin_main_text():
    return (
        f"🔐 <b>ADMIN PANEL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👑 Welcome, Admin\n"
        f"🏪 {STORE_NAME}\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"Kya karna chahte hain?"
    )


# ============================================================
# ENTRY COMMAND — /vandna_abhay
# ============================================================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("❌ You are not authorized.")
        return

    # Purana menu message delete karo (agar hai)
    old_id = context.user_data.get("admin_msg_id")
    if old_id:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=old_id,
            )
        except Exception:
            pass

    msg = await update.message.reply_text(
        admin_main_text(),
        parse_mode="HTML",
        reply_markup=admin_main_keyboard(),
    )

    # Message ID save karo
    context.user_data["admin_msg_id"] = msg.message_id


# ============================================================
# HOME CALLBACK — same message edit
# ============================================================

async def admin_home_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    await safe_edit(query, admin_main_text(), admin_main_keyboard())


# ============================================================
# CLOSE
# ============================================================

async def admin_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    try:
        await query.edit_message_text("🔐 <b>Admin panel closed.</b>", parse_mode="HTML")
    except Exception:
        pass

    context.user_data.pop("admin_msg_id", None)


# ============================================================
# HANDLERS — Saare modules load karo
# ============================================================

def get_handlers():
    handlers = [
        CommandHandler("vandna_abhay", admin_command),
        CallbackQueryHandler(admin_home_callback, pattern=r"^admin_home$"),
        CallbackQueryHandler(admin_close, pattern=r"^admin_close$"),
    ]

    modules = [
    "dashboard",
    "products",
    "products_add",
    "products_user_price",
    "products_resell_price",
    "pm_menu",
    "pm_products",
    "pm_add",
    "pm_edit",
    "pm_pricing",
    "pm_demo",
    "orders",
    "users",
    "wallet",
    "reseller",
    "settings_admin",
    "broadcast",
]

    for module_name in modules:
        try:
            mod = __import__(
                f"handlers.admin_panel.{module_name}",
                fromlist=["get_handlers"],
            )
            handlers.extend(mod.get_handlers())
        except Exception as e:
            logger.warning("❌ %s load failed: %s", module_name, e)

    return handlers
