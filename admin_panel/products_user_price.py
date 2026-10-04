# handlers/admin_panel/products_user_price.py
# ============================================================
# ADMIN PANEL - USER PRICE EDITOR
# Single-message editing architecture
# ============================================================

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler, ContextTypes, MessageHandler, filters,
)

import database
from handlers.admin_panel.menu import is_admin, safe_answer, safe_edit

logger = logging.getLogger(__name__)


def fmt_money(v):
    try:
        a = float(v)
        return f"₹{int(a)}" if a == int(a) else f"₹{a:.2f}"
    except Exception:
        return "₹0"


# ============================================================
# STEP 1: Duration List
# ============================================================

async def user_price_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    pid = query.data.split(":", 1)[1]
    product = database.get_product(pid)

    if not product:
        await safe_answer(query, "Not found", show_alert=True)
        return

    name = product.get("display_name") or product.get("name")
    durations = product.get("durations", [])

    if not durations:
        await safe_answer(query, "❌ Is product me koi duration nahi hai", show_alert=True)
        return

    buttons = []
    for i, d in enumerate(durations):
        dn = d.get("display_duration") or d.get("duration")
        price = d.get("display_price") or 0
        buttons.append([
            InlineKeyboardButton(
                f"{dn} — {fmt_money(price)}",
                callback_data=f"up_set:{pid}:{i}",
                style="success",
            )
        ])

    buttons.append([
        InlineKeyboardButton("‹ Back", callback_data=f"admin_prod_view:{pid}", style="primary"),
    ])

    text = (
        f"🛒 <b>EDIT USER PRICE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 <b>{name}</b>\n\n"
        f"👇 <b>Kaunsa duration ka price set karna hai?</b>\n"
        f"<i>(Ye price normal user ko dikhega)</i>"
    )

    await safe_edit(query, text, InlineKeyboardMarkup(buttons))


# ============================================================
# STEP 2: Price Prompt
# ============================================================

async def user_price_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    try:
        _, pid, idx = query.data.split(":")
        idx = int(idx)
    except Exception:
        await safe_answer(query, "Invalid.", show_alert=True)
        return

    product = database.get_product(pid)
    if not product:
        await safe_answer(query, "Not found.", show_alert=True)
        return

    durations = product.get("durations", [])
    if idx < 0 or idx >= len(durations):
        await safe_answer(query, "Invalid.", show_alert=True)
        return

    dur = durations[idx]
    dn = dur.get("display_duration") or dur.get("duration")
    current = dur.get("display_price") or 0

    context.user_data["up_pid"] = pid
    context.user_data["up_idx"] = idx

    text = (
        f"🛒 <b>SET USER PRICE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 {product.get('display_name') or product.get('name')}\n"
        f"⏱ Duration: <b>{dn}</b>\n"
        f"💰 Current: <b>{fmt_money(current)}</b>\n\n"
        f"👇 <b>Kitna price rakhna hai?</b>\n"
        f"Example: <code>149</code>"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data=f"up_menu:{pid}", style="danger")],
    ])

    await safe_edit(query, text, markup)


# ============================================================
# STEP 3: Save Price
# ============================================================

async def user_price_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = context.user_data.get("up_pid")
    idx = context.user_data.get("up_idx")

    if pid is None or idx is None:
        return
    if not is_admin(update.effective_user.id):
        return
    if not update.message or not update.message.text:
        return

    # Delete user's message
    try:
        await update.message.delete()
    except Exception:
        pass

    try:
        new_price = float(update.message.text.strip().replace(",", ""))
        if new_price <= 0:
            raise ValueError()
    except Exception:
        await update.effective_chat.send_message("❌ Invalid price.")
        return

    product = database.get_product(pid)
    if not product:
        return

    durations = product.get("durations", [])
    if idx < 0 or idx >= len(durations):
        return

    dur = durations[idx]
    dur_name = dur.get("duration")
    dn = dur.get("display_duration") or dur_name

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute(
            """UPDATE durations SET display_price=?
               WHERE product_id=(SELECT id FROM products WHERE supplier_pid=?) AND duration=?""",
            (new_price, str(pid), dur_name),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        await update.effective_chat.send_message(f"❌ Failed: {str(e)[:100]}")
        context.user_data.pop("up_pid", None)
        context.user_data.pop("up_idx", None)
        return

    # Clear state
    context.user_data.pop("up_pid", None)
    context.user_data.pop("up_idx", None)

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Edit More", callback_data=f"up_menu:{pid}", style="success")],
        [InlineKeyboardButton("‹ Product", callback_data=f"admin_prod_view:{pid}", style="primary")],
    ])

    await update.effective_chat.send_message(
        f"✅ <b>User Price Set!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 {product.get('display_name') or product.get('name')}\n"
        f"⏱ {dn}\n"
        f"🛒 New User Price: <b>{fmt_money(new_price)}</b>",
        parse_mode="HTML",
        reply_markup=markup,
    )


# ============================================================
# ROUTER
# ============================================================

async def user_price_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if context.user_data.get("up_pid") is not None:
        await user_price_save(update, context)
        return


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(user_price_menu, pattern=r"^up_menu:"),
        CallbackQueryHandler(user_price_set, pattern=r"^up_set:"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, user_price_router),
    ]
