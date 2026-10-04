# handlers/coupons.py
# ============================================================
# ABHAY PANEL STORE - COUPONS
# Admin: create | User: apply
# Delete old message + Auto-validate
# ============================================================

from __future__ import annotations

import logging
import random
import string
import time
from datetime import datetime

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
# INIT COUPONS TABLE
# ============================================================

def init_coupons_table():
    try:
        conn = database._conn()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                discount_percent REAL DEFAULT 0,
                max_uses INTEGER DEFAULT 0,
                used_count INTEGER DEFAULT 0,
                expiry INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1,
                created_at INTEGER
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS coupon_uses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                user_id INTEGER,
                discount_amount REAL,
                created_at INTEGER
            )
        """)

        conn.commit()
        conn.close()
    except Exception:
        logger.exception("Coupons table init failed")


# ============================================================
# COUPON FUNCTIONS
# ============================================================

def create_coupon(code: str, discount_percent: float, max_uses: int = 0, expiry_days: int = 0):
    init_coupons_table()

    expiry = 0
    if expiry_days > 0:
        expiry = int(time.time()) + (expiry_days * 86400)

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO coupons 
               (code, discount_percent, max_uses, used_count, expiry, active, created_at) 
               VALUES (?, ?, ?, 0, ?, 1, ?)""",
            (code.upper(), discount_percent, max_uses, expiry, int(time.time())),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error("Create coupon failed: %s", e)
        return False


def get_coupon(code: str):
    try:
        init_coupons_table()
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM coupons WHERE code = ?", (code.upper(),))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def get_all_coupons():
    try:
        init_coupons_table()
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM coupons ORDER BY id DESC LIMIT 20")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def validate_coupon(code: str):
    """Returns (ok, message, discount_percent)."""
    if not code:
        return False, "Invalid code", 0

    coupon = get_coupon(code)
    if not coupon:
        return False, "Coupon not found", 0

    if not coupon.get("active"):
        return False, "Coupon inactive", 0

    expiry = int(coupon.get("expiry") or 0)
    if expiry > 0 and expiry < int(time.time()):
        return False, "Coupon expired", 0

    max_uses = int(coupon.get("max_uses") or 0)
    used = int(coupon.get("used_count") or 0)
    if max_uses > 0 and used >= max_uses:
        return False, "Coupon limit reached", 0

    return True, "Valid", float(coupon.get("discount_percent") or 0)


# ============================================================
# ADMIN: COUPONS PANEL
# ============================================================

async def admin_coupons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    coupons = get_all_coupons()

    lines = ["🎟 <b>COUPONS</b>", "━━━━━━━━━━━━━━━━━━━", ""]

    if not coupons:
        lines.append("Abhi koi coupon nahi hai.")
    else:
        for c in coupons:
            code = c.get("code")
            disc = c.get("discount_percent") or 0
            used = c.get("used_count") or 0
            maxu = c.get("max_uses") or 0
            active = "🟢" if c.get("active") else "🔴"
            lines.append(f"{active} <code>{code}</code>  {disc}% off  ({used}/{maxu})")

    text = "\n".join(lines)

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Create Coupon", callback_data="admin_coupon_new", style="success")],
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
    ])

    await safe_edit(query, text, markup)


async def admin_coupon_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    context.user_data["coupon_create_waiting"] = True

    text = (
        "➕ <b>CREATE COUPON</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Format: <code>CODE DISCOUNT MAXUSES DAYS</code>\n\n"
        "<b>Example:</b>\n"
        "<code>SAVE20 20 100 7</code>\n\n"
        "Matlab:\n"
        "• Code: SAVE20\n"
        "• Discount: 20%\n"
        "• Max Uses: 100\n"
        "• Valid Days: 7\n\n"
        "⚠️ Max uses ya days 0 rakho to unlimited."
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_coupons", style="danger")],
    ])

    await safe_edit(query, text, markup)


async def admin_coupon_new_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("coupon_create_waiting"):
        return
    if not is_admin(update.effective_user.id):
        return

    context.user_data.pop("coupon_create_waiting", None)

    if not update.message:
        return

    # User ka message delete
    try:
        await update.message.delete()
    except Exception:
        pass

    parts = update.message.text.strip().split()
    if len(parts) != 4:
        try:
            await update.effective_chat.send_message(
                "❌ Format: <code>CODE DISCOUNT MAXUSES DAYS</code>\n"
                "Example: <code>SAVE20 20 100 7</code>",
                parse_mode="HTML",
            )
        except Exception:
            pass
        return

    try:
        code = parts[0].upper()
        discount = float(parts[1])
        max_uses = int(parts[2])
        days = int(parts[3])
    except Exception:
        try:
            await update.effective_chat.send_message("❌ Invalid values.")
        except Exception:
            pass
        return

    if discount <= 0 or discount > 100:
        try:
            await update.effective_chat.send_message("❌ Discount 1-100 ke beech hona chahiye.")
        except Exception:
            pass
        return

    ok = create_coupon(code, discount, max_uses, days)
    if not ok:
        try:
            await update.effective_chat.send_message(
                "❌ Coupon banane me error. Code duplicate ho sakta hai."
            )
        except Exception:
            pass
        return

    text = (
        f"✅ <b>COUPON CREATED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎟 Code: <code>{code}</code>\n"
        f"💸 Discount: <b>{discount}%</b>\n"
        f"🔢 Max Uses: <b>{max_uses if max_uses > 0 else 'Unlimited'}</b>\n"
        f"📅 Valid: <b>{days if days > 0 else 'Unlimited'} days</b>"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎟 Back to Coupons", callback_data="admin_coupons", style="primary")],
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
    ])

    try:
        await update.effective_chat.send_message(text, parse_mode="HTML", reply_markup=markup)
    except Exception:
        pass


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(admin_coupons, pattern=r"^admin_coupons$"),
        CallbackQueryHandler(admin_coupon_new, pattern=r"^admin_coupon_new$"),
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            admin_coupon_new_message,
        ),
    ]
