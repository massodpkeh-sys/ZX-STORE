# handlers/roles.py
# ============================================================
# ABHAY PANEL STORE - ROLES
# Super Admin | Admin | Moderator | Support
# Delete old message + Add/Remove/Change
# ============================================================

from __future__ import annotations

import logging
import time
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
import database

logger = logging.getLogger(__name__)

SUPER_ADMIN_ID = 8910147515
STORE_NAME = "ABHAY PANEL STORE"


# ============================================================
# ROLES CONFIG
# ============================================================

ROLES = {
    "SUPER_ADMIN": {
        "label": "👑 Super Admin",
        "permissions": ["all"],
    },
    "ADMIN": {
        "label": "🔴 Admin",
        "permissions": [
            "dashboard", "products", "orders", "users",
            "wallet", "payments", "broadcast", "paidmods",
        ],
    },
    "MODERATOR": {
        "label": "🟡 Moderator",
        "permissions": [
            "dashboard", "orders", "users", "tickets",
        ],
    },
    "SUPPORT": {
        "label": "🟢 Support",
        "permissions": [
            "tickets", "users",
        ],
    },
}


# ============================================================
# HELPERS
# ============================================================

def is_super_admin(user_id: int) -> bool:
    return user_id == SUPER_ADMIN_ID


def fmt_date(ts) -> str:
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%d %b %Y")
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


# ============================================================
# SAFE EDIT — PURANA DELETE + NAYA SEND
# ============================================================

async def safe_edit(query, text, reply_markup=None):
    """Purana message delete karo, naya bhejo."""
    try:
        await query.message.delete()
    except Exception:
        pass

    try:
        await query.message.chat.send_message(
            text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    except Exception:
        pass


def back_to_admin():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")]
    ])


# ============================================================
# INIT ROLES TABLE
# ============================================================

def init_roles_table():
    try:
        conn = database._conn()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS admin_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                role TEXT DEFAULT 'SUPPORT',
                added_by INTEGER,
                created_at INTEGER
            )
        """)

        # Super admin auto add
        cur.execute("SELECT id FROM admin_roles WHERE telegram_id = ?", (SUPER_ADMIN_ID,))
        if not cur.fetchone():
            cur.execute(
                """INSERT INTO admin_roles 
                   (telegram_id, username, role, added_by, created_at) 
                   VALUES (?, ?, 'SUPER_ADMIN', ?, ?)""",
                (SUPER_ADMIN_ID, "super", SUPER_ADMIN_ID, int(time.time())),
            )

        conn.commit()
        conn.close()
    except Exception:
        logger.exception("Roles init failed")


def get_user_role(telegram_id: int):
    try:
        init_roles_table()
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("SELECT role FROM admin_roles WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        conn.close()
        return row["role"] if row else None
    except Exception:
        return None


def get_all_admins():
    try:
        init_roles_table()
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM admin_roles ORDER BY id")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def add_admin(telegram_id: int, username: str, role: str, added_by: int) -> bool:
    if role not in ROLES:
        return False
    if role == "SUPER_ADMIN":
        return False

    try:
        init_roles_table()
        conn = database._conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO admin_roles 
               (telegram_id, username, role, added_by, created_at) 
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(telegram_id) DO UPDATE 
               SET role = excluded.role, username = excluded.username""",
            (telegram_id, username, role, added_by, int(time.time())),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        logger.exception("Add admin failed")
        return False


def remove_admin(telegram_id: int) -> bool:
    if telegram_id == SUPER_ADMIN_ID:
        return False

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM admin_roles WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def has_permission(telegram_id: int, permission: str) -> bool:
    role = get_user_role(telegram_id)
    if not role:
        return False

    role_data = ROLES.get(role)
    if not role_data:
        return False

    perms = role_data.get("permissions", [])
    if "all" in perms:
        return True
    return permission in perms


def is_any_admin(telegram_id: int) -> bool:
    return get_user_role(telegram_id) is not None


# ============================================================
# ADMIN: ROLES PANEL
# ============================================================

async def admin_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_any_admin(query.from_user.id):
        await safe_answer(query, "Unauthorized", show_alert=True)
        return

    admins = get_all_admins()

    lines = ["👑 <b>ROLES & ADMINS</b>", "━━━━━━━━━━━━━━━━━━━", ""]

    if not admins:
        lines.append("Koi admin nahi hai.")
    else:
        for a in admins:
            tid = a.get("telegram_id")
            role = a.get("role") or "SUPPORT"
            role_label = ROLES.get(role, {}).get("label", role)
            lines.append(f"• {role_label}  <code>{tid}</code>")

    if is_super_admin(query.from_user.id):
        buttons = [
            [InlineKeyboardButton("➕ Add Admin", callback_data="roles_add", style="success")],
            [InlineKeyboardButton("➖ Remove Admin", callback_data="roles_remove", style="danger")],
            [InlineKeyboardButton("🔄 Change Role", callback_data="roles_change", style="primary")],
            [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
        ]
    else:
        buttons = [
            [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
        ]

    text = "\n".join(lines)
    markup = InlineKeyboardMarkup(buttons)

    await safe_edit(query, text, markup)


# ============================================================
# ADD / REMOVE / CHANGE ROLE — Step 1
# ============================================================

async def roles_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_super_admin(query.from_user.id):
        await safe_answer(query, "Only Super Admin", show_alert=True)
        return

    context.user_data["roles_action"] = "add"

    text = (
        "➕ <b>ADD ADMIN</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Format: <code>USER_ID ROLE</code>\n\n"
        "Available Roles:\n"
        "• <code>ADMIN</code>\n"
        "• <code>MODERATOR</code>\n"
        "• <code>SUPPORT</code>\n\n"
        "<b>Example:</b>\n"
        "<code>123456789 ADMIN</code>"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_roles", style="danger")],
    ])

    await safe_edit(query, text, markup)


async def roles_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_super_admin(query.from_user.id):
        await safe_answer(query, "Only Super Admin", show_alert=True)
        return

    context.user_data["roles_action"] = "remove"

    text = (
        "➖ <b>REMOVE ADMIN</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "User ka Telegram ID bhejein.\n\n"
        "Example: <code>123456789</code>"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_roles", style="danger")],
    ])

    await safe_edit(query, text, markup)


async def roles_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_super_admin(query.from_user.id):
        await safe_answer(query, "Only Super Admin", show_alert=True)
        return

    context.user_data["roles_action"] = "change"

    text = (
        "🔄 <b>CHANGE ROLE</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Format: <code>USER_ID NEW_ROLE</code>\n\n"
        "Available Roles:\n"
        "• <code>ADMIN</code>\n"
        "• <code>MODERATOR</code>\n"
        "• <code>SUPPORT</code>\n\n"
        "<b>Example:</b>\n"
        "<code>123456789 MODERATOR</code>"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_roles", style="danger")],
    ])

    await safe_edit(query, text, markup)


# ============================================================
# ROLES — Step 2 (message)
# ============================================================

async def roles_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get("roles_action")
    if not action:
        return

    if not is_super_admin(update.effective_user.id):
        return

    context.user_data.pop("roles_action", None)

    if not update.message:
        return

    # User ka message delete
    try:
        await update.message.delete()
    except Exception:
        pass

    parts = update.message.text.strip().split()
    actor_id = update.effective_user.id

    # ---------------- ADD ----------------
    if action == "add":
        if len(parts) != 2:
            try:
                await update.effective_chat.send_message(
                    "❌ Format: <code>USER_ID ROLE</code>",
                    parse_mode="HTML",
                )
            except Exception:
                pass
            return

        try:
            tid = int(parts[0])
        except Exception:
            try:
                await update.effective_chat.send_message("❌ Invalid user ID.")
            except Exception:
                pass
            return

        role = parts[1].upper()
        if role not in ROLES or role == "SUPER_ADMIN":
            try:
                await update.effective_chat.send_message(
                    "❌ Invalid role. Use ADMIN / MODERATOR / SUPPORT"
                )
            except Exception:
                pass
            return

        ok = add_admin(tid, f"user{tid}", role, actor_id)
        if not ok:
            try:
                await update.effective_chat.send_message("❌ Failed.")
            except Exception:
                pass
            return

        role_label = ROLES[role]["label"]

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 Back to Roles", callback_data="admin_roles", style="primary")],
            [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
        ])

        try:
            await update.effective_chat.send_message(
                f"✅ <b>Admin Added</b>\n\n"
                f"🆔 <code>{tid}</code>\n"
                f"👑 {role_label}",
                parse_mode="HTML",
                reply_markup=markup,
            )
        except Exception:
            pass

        # Notify new admin
        try:
            await context.bot.send_message(
                chat_id=tid,
                text=(
                    f"🎉 <b>You are now an admin!</b>\n\n"
                    f"Role: <b>{role_label}</b>\n"
                    f"Store: {STORE_NAME}"
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

    # ---------------- REMOVE ----------------
    elif action == "remove":
        if len(parts) != 1:
            try:
                await update.effective_chat.send_message("❌ Send only USER_ID")
            except Exception:
                pass
            return

        try:
            tid = int(parts[0])
        except Exception:
            try:
                await update.effective_chat.send_message("❌ Invalid ID.")
            except Exception:
                pass
            return

        if tid == SUPER_ADMIN_ID:
            try:
                await update.effective_chat.send_message("❌ Super Admin cannot be removed.")
            except Exception:
                pass
            return

        ok = remove_admin(tid)
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 Back to Roles", callback_data="admin_roles", style="primary")],
            [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
        ])
        if ok:
            try:
                await update.effective_chat.send_message(
                    f"✅ Admin <code>{tid}</code> removed.",
                    parse_mode="HTML",
                    reply_markup=markup,
                )
            except Exception:
                pass
            try:
                await context.bot.send_message(
                    chat_id=tid,
                    text="ℹ️ Your admin access has been removed.",
                )
            except Exception:
                pass
        else:
            try:
                await update.effective_chat.send_message("❌ Failed.")
            except Exception:
                pass

    # ---------------- CHANGE ----------------
    elif action == "change":
        if len(parts) != 2:
            try:
                await update.effective_chat.send_message(
                    "❌ Format: <code>USER_ID NEW_ROLE</code>",
                    parse_mode="HTML",
                )
            except Exception:
                pass
            return

        try:
            tid = int(parts[0])
        except Exception:
            try:
                await update.effective_chat.send_message("❌ Invalid ID.")
            except Exception:
                pass
            return

        role = parts[1].upper()
        if role not in ROLES or role == "SUPER_ADMIN":
            try:
                await update.effective_chat.send_message("❌ Invalid role.")
            except Exception:
                pass
            return

        ok = add_admin(tid, f"user{tid}", role, actor_id)
        if ok:
            role_label = ROLES[role]["label"]
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("👑 Back to Roles", callback_data="admin_roles", style="primary")],
                [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
            ])
            try:
                await update.effective_chat.send_message(
                    f"✅ Role updated for <code>{tid}</code> to {role_label}",
                    parse_mode="HTML",
                    reply_markup=markup,
                )
            except Exception:
                pass
        else:
            try:
                await update.effective_chat.send_message("❌ Failed.")
            except Exception:
                pass


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(admin_roles, pattern=r"^admin_roles$"),
        CallbackQueryHandler(roles_add, pattern=r"^roles_add$"),
        CallbackQueryHandler(roles_remove, pattern=r"^roles_remove$"),
        CallbackQueryHandler(roles_change, pattern=r"^roles_change$"),
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            roles_message,
        ),
    ]
