# handlers/settings.py
# ============================================================
# ABHAY PANEL STORE - SETTINGS
# Single-message editing architecture
# ============================================================

from __future__ import annotations

import logging
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
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
STORE_NAME = "ABHAY PANEL STORE"


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
# INIT SETTINGS TABLE
# ============================================================

def init_settings_table():
    try:
        conn = database._conn()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at INTEGER
            )
        """)

        defaults = {
            "store_name": STORE_NAME,
            "min_deposit": "10",
            "max_deposit": "5000",
            "upi_id": "jitu@upi",
            "referral_bonus": "0.50",
            "spin_min": "0.10",
            "spin_max": "1.00",
            "support_username": "H4X_JOD_ABHAY",
            "maintenance_mode": "0",
        }

        for k, v in defaults.items():
            cur.execute(
                "INSERT OR IGNORE INTO bot_settings (key, value, updated_at) VALUES (?, ?, ?)",
                (k, v, int(time.time())),
            )

        conn.commit()
        conn.close()
    except Exception:
        logger.exception("Settings init failed")


def get_setting(key: str, default: str = "") -> str:
    try:
        init_settings_table()
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("SELECT value FROM bot_settings WHERE key = ?", (key,))
        row = cur.fetchone()
        conn.close()
        return row["value"] if row else default
    except Exception:
        return default


def set_setting(key: str, value: str) -> bool:
    try:
        init_settings_table()
        conn = database._conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO bot_settings (key, value, updated_at) VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
            (key, value, int(time.time())),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        logger.exception("Set setting failed")
        return False


def get_all_settings():
    try:
        init_settings_table()
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM bot_settings ORDER BY key")
        rows = cur.fetchall()
        conn.close()
        return {r["key"]: r["value"] for r in rows}
    except Exception:
        return {}


def is_maintenance_mode() -> bool:
    try:
        return get_setting("maintenance_mode", "0") == "1"
    except Exception:
        return False


# ============================================================
# SETTINGS PANEL
# ============================================================

async def admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    s = get_all_settings()
    maint = "🔴 ON" if s.get("maintenance_mode") == "1" else "🟢 OFF"

    text = (
        f"⚙️ <b>BOT SETTINGS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏪 Store Name: <b>{s.get('store_name', '-')}</b>\n"
        f"💰 Min Deposit: <b>₹{s.get('min_deposit', '-')}</b>\n"
        f"💰 Max Deposit: <b>₹{s.get('max_deposit', '-')}</b>\n"
        f"📱 UPI ID: <code>{s.get('upi_id', '-')}</code>\n"
        f"🎁 Referral Bonus: <b>₹{s.get('referral_bonus', '-')}</b>\n"
        f"🎰 Spin Min: <b>₹{s.get('spin_min', '-')}</b>\n"
        f"🎰 Spin Max: <b>₹{s.get('spin_max', '-')}</b>\n"
        f"👤 Support: @{s.get('support_username', '-')}\n"
        f"🔧 Maintenance: <b>{maint}</b>\n"
    )

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏪 Store Name", callback_data="set_edit:store_name", style="primary"),
            InlineKeyboardButton("📱 UPI ID", callback_data="set_edit:upi_id", style="primary"),
        ],
        [
            InlineKeyboardButton("💰 Min Deposit", callback_data="set_edit:min_deposit", style="primary"),
            InlineKeyboardButton("💰 Max Deposit", callback_data="set_edit:max_deposit", style="primary"),
        ],
        [
            InlineKeyboardButton("🎁 Ref Bonus", callback_data="set_edit:referral_bonus", style="primary"),
            InlineKeyboardButton("👤 Support", callback_data="set_edit:support_username", style="primary"),
        ],
        [
            InlineKeyboardButton("🎰 Spin Min", callback_data="set_edit:spin_min", style="primary"),
            InlineKeyboardButton("🎰 Spin Max", callback_data="set_edit:spin_max", style="primary"),
        ],
        [
            InlineKeyboardButton(
                f"🔧 Maintenance: {maint}",
                callback_data="set_toggle_maint",
                style="danger" if maint.startswith("🔴") else "success",
            )
        ],
        [
            InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary"),
        ],
    ])

    await safe_edit(query, text, markup)


# ============================================================
# SETTING LABELS
# ============================================================

SETTING_LABELS = {
    "store_name": "Store Name",
    "upi_id": "UPI ID",
    "min_deposit": "Min Deposit (₹)",
    "max_deposit": "Max Deposit (₹)",
    "referral_bonus": "Referral Bonus (₹)",
    "support_username": "Support Username (bina @)",
    "spin_min": "Spin Min (₹)",
    "spin_max": "Spin Max (₹)",
}


# ============================================================
# EDIT SETTING
# ============================================================

async def set_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    try:
        key = query.data.split(":", 1)[1]
    except Exception:
        await safe_answer(query, "Invalid.", show_alert=True)
        return

    label = SETTING_LABELS.get(key, key)
    current = get_setting(key, "")

    context.user_data["set_waiting_key"] = key

    text = (
        f"⚙️ <b>EDIT SETTING</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 Key: <b>{label}</b>\n"
        f"💾 Current: <code>{current}</code>\n\n"
        f"👇 Naya value bhejein:"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_settings", style="danger")],
    ])

    await safe_edit(query, text, markup)


async def set_edit_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data.get("set_waiting_key")
    if not key:
        return

    if not is_admin(update.effective_user.id):
        return

    context.user_data.pop("set_waiting_key", None)

    if not update.message or not update.message.text:
        return

    value = update.message.text.strip()

    # Delete user message
    try:
        await update.message.delete()
    except Exception:
        pass

    if not value:
        await update.effective_chat.send_message("❌ Empty value.")
        return

    ok = set_setting(key, value)

    if ok:
        label = SETTING_LABELS.get(key, key)
        text = (
            f"✅ <b>Setting Updated</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"📝 Key: <b>{label}</b>\n"
            f"💾 New Value: <code>{value}</code>"
        )
    else:
        text = "❌ Update failed."

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ Back to Settings", callback_data="admin_settings", style="success")],
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
    ])

    await update.effective_chat.send_message(text, parse_mode="HTML", reply_markup=markup)


# ============================================================
# TOGGLE MAINTENANCE
# ============================================================

async def set_toggle_maint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    current = get_setting("maintenance_mode", "0")
    new_val = "0" if current == "1" else "1"
    set_setting("maintenance_mode", new_val)

    status = "🔴 ON" if new_val == "1" else "🟢 OFF"
    await safe_answer(query, f"Maintenance: {status}", show_alert=True)

    # Refresh same message
    await admin_settings(update, context)


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(admin_settings, pattern=r"^admin_settings$"),
        CallbackQueryHandler(set_edit, pattern=r"^set_edit:"),
        CallbackQueryHandler(set_toggle_maint, pattern=r"^set_toggle_maint$"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, set_edit_message),
    ]
