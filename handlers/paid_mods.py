# handlers/paid_mods.py
# ============================================================
# ABHAY PANEL STORE - PAID MODS
# Admin: add/manage | User: browse/buy
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

ADMIN_ID = 8910147515
STORE_NAME = getattr(config, "STORE_NAME", "ABHAY PANEL STORE")


# ============================================================
# HELPERS
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def fmt_money(value) -> str:
    try:
        amount = float(value)
        if amount == int(amount):
            return f"₹{int(amount)}"
        return f"₹{amount:.2f}"
    except Exception:
        return "₹0"


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


def back_to_admin():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")]
    ])


# ============================================================
# INIT TABLE
# ============================================================

def init_paidmods_table():
    try:
        conn = database._conn()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS paid_mods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                price REAL,
                file_id TEXT,
                link TEXT,
                active INTEGER DEFAULT 1,
                created_at INTEGER
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS paid_mod_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                mod_id INTEGER,
                price REAL,
                purchased_at INTEGER
            )
        """)

        conn.commit()
        conn.close()
    except Exception:
        logger.exception("Paid mods table init failed")


# ============================================================
# FUNCTIONS
# ============================================================

def get_all_paid_mods(active_only=True):
    try:
        init_paidmods_table()
        conn = database._conn()
        cur = conn.cursor()
        if active_only:
            cur.execute("SELECT * FROM paid_mods WHERE active = 1 ORDER BY id DESC")
        else:
            cur.execute("SELECT * FROM paid_mods ORDER BY id DESC")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_paid_mod(mod_id: int):
    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM paid_mods WHERE id = ?", (mod_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def add_paid_mod(name: str, description: str, price: float, file_id: str = "", link: str = ""):
    try:
        init_paidmods_table()
        conn = database._conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO paid_mods 
               (name, description, price, file_id, link, active, created_at) 
               VALUES (?, ?, ?, ?, ?, 1, ?)""",
            (name, description, price, file_id, link, int(time.time())),
        )
        conn.commit()
        mod_id = cur.lastrowid
        conn.close()
        return mod_id
    except Exception as e:
        logger.error("Add paid mod failed: %s", e)
        return None


def has_purchased(user_id: int, mod_id: int) -> bool:
    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM paid_mod_purchases WHERE user_id = ? AND mod_id = ? LIMIT 1",
            (user_id, mod_id),
        )
        row = cur.fetchone()
        conn.close()
        return bool(row)
    except Exception:
        return False


def log_purchase(user_id: int, mod_id: int, price: float):
    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO paid_mod_purchases (user_id, mod_id, price, purchased_at) VALUES (?, ?, ?, ?)",
            (user_id, mod_id, price, int(time.time())),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# ============================================================
# USER: PAID MODS LIST
# ============================================================

async def paid_mods_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    mods = get_all_paid_mods()

    if not mods:
        text = (
            "💎 <b>PAID MODS</b>\n\n"
            "Abhi koi paid mod available nahi hai.\n\n"
            "Jald aa rahe hain!"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("‹ Back", callback_data="main_menu", style="primary")],
        ])
        try:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)
        except Exception:
            pass
        return

    lines = ["💎 <b>PAID MODS</b>", "━━━━━━━━━━━━━━━━━━━", ""]

    buttons = []

    for m in mods:
        mid = m.get("id")
        name = m.get("name") or "?"
        price = m.get("price") or 0

        lines.append(f"• <b>{name}</b> — {fmt_money(price)}")

        buttons.append([
            InlineKeyboardButton(
                f"💎 {name[:30]}",
                callback_data=f"paidmod_view:{mid}",
                style="primary",
            )
        ])

    buttons.append([
        InlineKeyboardButton("‹ Back", callback_data="main_menu", style="primary"),
    ])

    text = "\n".join(lines)

    try:
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    except Exception:
        pass


# ============================================================
# USER: VIEW MOD
# ============================================================

async def paidmod_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    try:
        mod_id = int(query.data.split(":", 1)[1])
    except Exception:
        await safe_answer(query, "Invalid.", show_alert=True)
        return

    mod = get_paid_mod(mod_id)
    if not mod:
        await safe_answer(query, "Not found.", show_alert=True)
        return

    user_id = query.from_user.id
    purchased = has_purchased(user_id, mod_id)

    name = mod.get("name") or "?"
    desc = mod.get("description") or "-"
    price = mod.get("price") or 0

    text = (
        f"💎 <b>{name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 {desc}\n\n"
        f"💰 Price: <b>{fmt_money(price)}</b>\n"
    )

    if purchased:
        text += "\n✅ <b>You already own this!</b>"
        buttons = [
            [InlineKeyboardButton("🔗 Get Content", callback_data=f"paidmod_get:{mod_id}", style="success")],
            [InlineKeyboardButton("‹ Back", callback_data="paid_mods_list", style="primary")],
        ]
    else:
        buttons = [
            [InlineKeyboardButton(f"💳 Buy for {fmt_money(price)}", callback_data=f"paidmod_buy:{mod_id}", style="success")],
            [InlineKeyboardButton("‹ Back", callback_data="paid_mods_list", style="primary")],
        ]

    try:
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    except Exception:
        pass


# ============================================================
# USER: BUY MOD
# ============================================================

async def paidmod_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    try:
        mod_id = int(query.data.split(":", 1)[1])
    except Exception:
        await safe_answer(query, "Invalid.", show_alert=True)
        return

    mod = get_paid_mod(mod_id)
    if not mod:
        await safe_answer(query, "Not found.", show_alert=True)
        return

    user_id = query.from_user.id

    if has_purchased(user_id, mod_id):
        await safe_answer(query, "Already purchased!", show_alert=True)
        return

    price = float(mod.get("price") or 0)
    balance = float(database.get_wallet_balance(user_id))

    if balance < price:
        needed = price - balance
        text = (
            f"❌ <b>Insufficient Balance</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Required: <b>{fmt_money(price)}</b>\n"
            f"💳 Your Balance: <b>{fmt_money(balance)}</b>\n"
            f"📉 Need: <b>{fmt_money(needed)}</b>\n\n"
            f"Pehle balance add karein."
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Add Balance", callback_data="wallet_add", style="success")],
            [InlineKeyboardButton("‹ Back", callback_data=f"paidmod_view:{mod_id}", style="primary")],
        ])
        try:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)
        except Exception:
            pass
        return

    # Confirm
    text = (
        f"🧾 <b>Confirm Purchase</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 {mod.get('name')}\n"
        f"💰 Price: <b>{fmt_money(price)}</b>\n"
        f"💳 Balance: <b>{fmt_money(balance)}</b>\n\n"
        f"Confirm karein?"
    )

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"paidmod_confirm:{mod_id}", style="success"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"paidmod_view:{mod_id}", style="danger"),
        ],
    ])

    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)
    except Exception:
        pass


# ============================================================
# USER: CONFIRM BUY
# ============================================================

async def paidmod_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query, "Processing...")

    try:
        mod_id = int(query.data.split(":", 1)[1])
    except Exception:
        await safe_answer(query, "Invalid.", show_alert=True)
        return

    mod = get_paid_mod(mod_id)
    if not mod:
        await safe_answer(query, "Not found.", show_alert=True)
        return

    user_id = query.from_user.id

    if has_purchased(user_id, mod_id):
        await safe_answer(query, "Already purchased!", show_alert=True)
        return

    price = float(mod.get("price") or 0)

    # Debit
    ok = database.debit_wallet(user_id, price, reference=f"PAIDMOD-{mod_id}")
    if not ok:
        await safe_answer(query, "Wallet debit failed.", show_alert=True)
        return

    log_purchase(user_id, mod_id, price)

    # Give content
    link = mod.get("link") or ""
    file_id = mod.get("file_id") or ""

    text = (
        f"✅ <b>PURCHASE SUCCESSFUL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 {mod.get('name')}\n"
        f"💰 Paid: <b>{fmt_money(price)}</b>\n\n"
    )

    if link:
        text += f"🔗 <b>Your Content:</b>\n{link}\n"

    if not link and not file_id:
        text += f"⏳ Content jald bheja jayega. Support se contact karein."

    text += f"\n📅 {fmt_date(time.time())}"

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("‹ Back", callback_data="paid_mods_list", style="primary")],
    ])

    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)
    except Exception:
        pass

    # Admin notify
    try:
        admin_text = (
            f"💎 <b>NEW PAID MOD SALE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 User: <code>{user_id}</code>\n"
            f"💎 Mod: {mod.get('name')}\n"
            f"💰 Amount: <b>{fmt_money(price)}</b>\n"
            f"🕐 {fmt_date(time.time())}"
        )
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ============================================================
# USER: GET CONTENT (if already purchased)
# ============================================================

async def paidmod_get(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    try:
        mod_id = int(query.data.split(":", 1)[1])
    except Exception:
        await safe_answer(query, "Invalid.", show_alert=True)
        return

    mod = get_paid_mod(mod_id)
    if not mod:
        await safe_answer(query, "Not found.", show_alert=True)
        return

    user_id = query.from_user.id

    if not has_purchased(user_id, mod_id):
        await safe_answer(query, "You don't own this.", show_alert=True)
        return

    link = mod.get("link") or ""
    file_id = mod.get("file_id") or ""

    if link:
        text = (
            f"🔗 <b>YOUR CONTENT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"💎 {mod.get('name')}\n\n"
            f"{link}"
        )
        try:
            await query.edit_message_text(text, parse_mode="HTML")
        except Exception:
            pass
    elif file_id:
        try:
            await context.bot.send_document(
                chat_id=user_id,
                document=file_id,
                caption=f"💎 {mod.get('name')}",
            )
        except Exception:
            pass
    else:
        await safe_answer(query, "Content not set. Contact support.", show_alert=True)


# ============================================================
# ADMIN: PAID MODS PANEL
# ============================================================

async def admin_paidmods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    mods = get_all_paid_mods(active_only=False)

    lines = ["💎 <b>PAID MODS</b>", "━━━━━━━━━━━━━━━━━━━", ""]

    if not mods:
        lines.append("Abhi koi mod nahi hai.")
    else:
        for m in mods:
            mid = m.get("id")
            name = m.get("name") or "?"
            price = m.get("price") or 0
            active = "🟢" if m.get("active") else "🔴"
            lines.append(f"{active} #{mid}  {name}  ({fmt_money(price)})")

    text = "\n".join(lines)

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Mod", callback_data="admin_paidmod_new", style="success")],
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
    ])

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)


async def admin_paidmod_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    context.user_data["paidmod_create_waiting"] = True

    text = (
        "➕ <b>ADD PAID MOD</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Format (ek hi message me):\n"
        "<code>NAME | PRICE | LINK</code>\n\n"
        "<b>Example:</b>\n"
        "<code>VIP MOD MENU | 499 | https://t.me/xyz</code>\n\n"
        "⚠️ Link optional hai. Baad me bhi set kar sakte ho."
    )

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=back_to_admin())


async def admin_paidmod_new_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("paidmod_create_waiting"):
        return
    if not is_admin(update.effective_user.id):
        return

    context.user_data.pop("paidmod_create_waiting", None)

    raw = update.message.text.strip()
    parts = [p.strip() for p in raw.split("|")]

    if len(parts) < 2:
        await update.message.reply_text(
            "❌ Format: <code>NAME | PRICE | LINK</code>",
            parse_mode="HTML",
        )
        return

    name = parts[0]
    try:
        price = float(parts[1])
    except Exception:
        await update.message.reply_text("❌ Price invalid.")
        return

    link = parts[2] if len(parts) >= 3 else ""
    desc = f"Premium content: {name}"

    mod_id = add_paid_mod(name, desc, price, file_id="", link=link)

    if not mod_id:
        await update.message.reply_text("❌ Failed to add.")
        return

    await update.message.reply_text(
        f"✅ <b>PAID MOD ADDED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <b>{mod_id}</b>\n"
        f"💎 Name: {name}\n"
        f"💰 Price: {fmt_money(price)}\n"
        f"🔗 Link: {link or '—'}",
        parse_mode="HTML",
    )


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        # User
        CallbackQueryHandler(paid_mods_list, pattern=r"^paid_mods_list$"),
        CallbackQueryHandler(paidmod_view, pattern=r"^paidmod_view:"),
        CallbackQueryHandler(paidmod_buy, pattern=r"^paidmod_buy:"),
        CallbackQueryHandler(paidmod_confirm, pattern=r"^paidmod_confirm:"),
        CallbackQueryHandler(paidmod_get, pattern=r"^paidmod_get:"),

        # Admin
        CallbackQueryHandler(admin_paidmods, pattern=r"^admin_paidmods$"),
        CallbackQueryHandler(admin_paidmod_new, pattern=r"^admin_paidmod_new$"),

        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            admin_paidmod_new_message,
        ),
    ]
