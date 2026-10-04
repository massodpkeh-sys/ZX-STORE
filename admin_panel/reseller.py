# handlers/admin_panel/reseller.py
# ============================================================
# ADMIN PANEL - MANAGE RESELLER
# Single-message editing architecture
# ============================================================

from __future__ import annotations

import logging
import time
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler, ContextTypes, MessageHandler, filters,
)

import database
from handlers.admin_panel.menu import is_admin, safe_answer, safe_edit, back_admin

logger = logging.getLogger(__name__)


def fmt_date(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%d %b %Y")
    except Exception:
        return "—"


# ============================================================
# MANAGE RESELLER — Main Menu
# ============================================================

async def admin_reseller_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    text = (
        f"👑 <b>MANAGE RESELLER</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"Option choose karein:"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Make Reseller", callback_data="resel_make", style="success")],
        [InlineKeyboardButton("➖ Remove Reseller", callback_data="resel_remove", style="danger")],
        [InlineKeyboardButton("📋 Reseller List", callback_data="resel_list", style="primary")],
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
    ])

    await safe_edit(query, text, markup)


# ============================================================
# MAKE RESELLER
# ============================================================

async def resel_make(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    context.user_data["resel_action"] = "make"

    text = (
        "➕ <b>MAKE RESELLER</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "User ka Telegram ID bhejein.\n\n"
        "Example: <code>123456789</code>\n\n"
        "User ko 30 days ka reseller banaya jayega."
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_reseller_menu", style="danger")],
    ])
    await safe_edit(query, text, markup)


# ============================================================
# REMOVE RESELLER
# ============================================================

async def resel_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    context.user_data["resel_action"] = "remove"

    text = (
        "➖ <b>REMOVE RESELLER</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "User ka Telegram ID bhejein.\n\n"
        "Example: <code>123456789</code>"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_reseller_menu", style="danger")],
    ])
    await safe_edit(query, text, markup)


# ============================================================
# RESELLER LIST
# ============================================================

async def resel_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    rows = []
    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = [r[1] for r in cur.fetchall()]
        if "reseller_expiry" in cols:
            now = int(time.time())
            cur.execute(
                "SELECT telegram_id, first_name, reseller_expiry FROM users WHERE reseller_expiry > ? ORDER BY reseller_expiry DESC",
                (now,),
            )
            rows = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception:
        rows = []

    if not rows:
        text = "👑 <b>RESELLER LIST</b>\n\nAbhi koi active reseller nahi."
    else:
        lines = [f"👑 <b>ACTIVE RESELLERS</b> ({len(rows)})", "━━━━━━━━━━━━━━━━━━━", ""]
        now = int(time.time())
        for r in rows:
            days = max(0, (int(r["reseller_expiry"]) - now) // 86400)
            lines.append(f"• <code>{r['telegram_id']}</code>  {r['first_name'] or 'User'}  ({days}d)")
        text = "\n".join(lines)

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Make Reseller", callback_data="resel_make", style="success")],
        [InlineKeyboardButton("‹ Back", callback_data="admin_reseller_menu", style="primary")],
    ])

    await safe_edit(query, text, markup)


# ============================================================
# ACTION HANDLER (Make/Remove)
# ============================================================

async def resel_action_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get("resel_action")
    if not action:
        return
    if not is_admin(update.effective_user.id):
        return
    if not update.message or not update.message.text:
        return

    context.user_data.pop("resel_action", None)

    try:
        await update.message.delete()
    except Exception:
        pass

    try:
        tid = int(update.message.text.strip())
    except Exception:
        await update.effective_chat.send_message("❌ Invalid ID.")
        return

    user = database.get_user(tid)
    if not user:
        await update.effective_chat.send_message(f"❌ User {tid} not found.")
        return

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = [r[1] for r in cur.fetchall()]
        if "reseller_expiry" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN reseller_expiry INTEGER DEFAULT 0")

        if action == "make":
            exp = int(time.time()) + (30 * 86400)
            cur.execute("UPDATE users SET reseller_expiry = ? WHERE telegram_id = ?", (exp, tid))
            msg = f"✅ <code>{tid}</code> now Reseller (30 days)"
            user_msg = "🎉 <b>You are now a Reseller!</b>\n\n30 days valid."
        else:
            cur.execute("UPDATE users SET reseller_expiry = 0 WHERE telegram_id = ?", (tid,))
            msg = f"✅ <code>{tid}</code> reseller removed."
            user_msg = "ℹ️ Aapka reseller access hata diya gaya hai."

        conn.commit()
        conn.close()

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("‹ Reseller Menu", callback_data="admin_reseller_menu", style="primary")],
        ])
        await update.effective_chat.send_message(msg, parse_mode="HTML", reply_markup=markup)

        try:
            await context.bot.send_message(chat_id=tid, text=user_msg, parse_mode="HTML")
        except Exception:
            pass
    except Exception as e:
        await update.effective_chat.send_message(f"❌ Failed: {str(e)[:100]}")


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(admin_reseller_menu, pattern=r"^admin_reseller_menu$"),
        CallbackQueryHandler(resel_make, pattern=r"^resel_make$"),
        CallbackQueryHandler(resel_remove, pattern=r"^resel_remove$"),
        CallbackQueryHandler(resel_list, pattern=r"^resel_list$"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, resel_action_msg),
    ]
