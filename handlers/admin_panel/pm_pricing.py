# handlers/admin_panel/pm_pricing.py
# ============================================================
# ADMIN PANEL - PRICING MANAGE
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
# MAIN MENU
# ============================================================

async def pm_pricing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    text = (
        "💰 <b>PRICING MANAGE</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "👇 Option select karein:"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Edit Existing Price", callback_data="pm_pricing_list", style="success")],
        [InlineKeyboardButton("🔙 Back", callback_data="pm_products", style="primary")],
    ])
    await safe_edit(query, text, markup)


# ============================================================
# PRODUCT SELECT
# ============================================================

async def pm_pricing_prod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    pid = context.user_data.get("pm_edit_pid")
    if not pid:
        await safe_answer(query, "Session expired", show_alert=True)
        return

    await _show_pricing_list(query, pid, context)


async def pm_pricing_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    products = database.get_products()
    if not products:
        await safe_edit(query, "❌ Koi product nahi.", InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="pm_products", style="primary")],
        ]))
        return

    buttons = []
    for p in products:
        pid = p.get("supplier_pid")
        name = p.get("display_name") or p.get("name") or "?"
        buttons.append([
            InlineKeyboardButton(f"💰 {name}", callback_data=f"pm_pricing_show:{pid}", style="primary")
        ])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="pm_products", style="primary")])

    await safe_edit(query, "💰 <b>SELECT PRODUCT</b>", InlineKeyboardMarkup(buttons))


async def pm_pricing_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    pid = query.data.split(":", 1)[1]
    await _show_pricing_list(query, pid, context)


async def _show_pricing_list(query, pid, context):
    product = database.get_product(pid)
    if not product:
        await safe_answer(query, "Not found", show_alert=True)
        return

    name = product.get("display_name") or product.get("name")
    durations = product.get("durations", [])
    context.user_data["pm_price_pid"] = pid

    lines = [f"💰 <b>PRICING: {name}</b>", "━━━━━━━━━━━━━━━━━━━", ""]

    for i, d in enumerate(durations, 1):
        dn = d.get("display_duration") or d.get("duration")
        price = d.get("display_price") or 0
        rp = d.get("reseller_price") or 0
        lines.append(f"<b>{i}. {dn}</b>")
        lines.append(f"   🛒 User: {fmt_money(price)}")
        lines.append(f"   👑 Reseller: {fmt_money(rp)}")
        lines.append("")

    buttons = []
    for i, d in enumerate(durations, 1):
        dn = d.get("display_duration") or d.get("duration")
        buttons.append([
            InlineKeyboardButton(f"✏️ {dn}", callback_data=f"pm_price_edit:{i-1}", style="success")
        ])

    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="pm_pricing_list", style="primary")])

    await safe_edit(query, "\n".join(lines), InlineKeyboardMarkup(buttons))


async def pm_price_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    try:
        idx = int(query.data.split(":", 1)[1])
    except Exception:
        return

    pid = context.user_data.get("pm_price_pid")
    if not pid:
        await safe_answer(query, "Session expired", show_alert=True)
        return

    product = database.get_product(pid)
    if not product:
        return

    durations = product.get("durations", [])
    if idx < 0 or idx >= len(durations):
        return

    dur = durations[idx]
    dn = dur.get("display_duration") or dur.get("duration")
    cur_price = dur.get("display_price") or 0

    context.user_data["pm_price_idx"] = idx
    context.user_data["pm_price_stage"] = "user"

    text = (
        f"✏️ <b>EDIT PRICE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"⏱ Duration: <b>{dn}</b>\n"
        f"🛒 Current User Price: <b>{fmt_money(cur_price)}</b>\n\n"
        f"👇 Naya <b>User Price</b> bhejein:\n"
        f"Example: <code>149</code>"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data=f"pm_pricing_show:{pid}", style="primary")],
    ])
    await safe_edit(query, text, markup)


async def pm_price_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if not is_admin(update.effective_user.id):
        return

    stage = context.user_data.get("pm_price_stage")
    pid = context.user_data.get("pm_price_pid")
    idx = context.user_data.get("pm_price_idx")

    if not stage or not pid or idx is None:
        return

    raw = update.message.text.strip()
    try:
        await update.message.delete()
    except Exception:
        pass

    try:
        new_price = float(raw)
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

    # USER PRICE STAGE
    if stage == "user":
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
            await update.effective_chat.send_message(f"❌ Error: {str(e)[:100]}")
            return

        context.user_data["pm_price_stage"] = "reseller"

        text = (
            f"✏️ <b>EDIT PRICE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"⏱ Duration: <b>{dn}</b>\n"
            f"🛒 User Price: <b>{fmt_money(new_price)}</b> ✅\n\n"
            f"👇 Ab <b>Reseller Price</b> bhejein:\n"
            f"Example: <code>99</code>"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭️ Skip", callback_data=f"pm_price_skip:{pid}", style="primary")],
            [InlineKeyboardButton("🔙 Back", callback_data=f"pm_pricing_show:{pid}", style="primary")],
        ])
        await update.effective_chat.send_message(text, parse_mode="HTML", reply_markup=markup)
        return

    # RESELLER PRICE STAGE
    if stage == "reseller":
        try:
            conn = database._conn()
            cur = conn.cursor()
            cur.execute(
                """UPDATE durations SET reseller_price=?
                   WHERE product_id=(SELECT id FROM products WHERE supplier_pid=?) AND duration=?""",
                (new_price, str(pid), dur_name),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            await update.effective_chat.send_message(f"❌ Error: {str(e)[:100]}")
            return

        for k in ["pm_price_stage", "pm_price_idx"]:
            context.user_data.pop(k, None)

        text = (
            f"✅ <b>Price Updated!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"⏱ {dn}\n"
            f"👑 Reseller Price: <b>{fmt_money(new_price)}</b>\n\n"
            f"Dono prices set ho gayi!"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Back to Pricing", callback_data=f"pm_pricing_show:{pid}", style="success")],
        ])
        await update.effective_chat.send_message(text, parse_mode="HTML", reply_markup=markup)


async def pm_price_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    context.user_data.pop("pm_price_stage", None)
    context.user_data.pop("pm_price_idx", None)

    pid = context.user_data.get("pm_price_pid")
    if pid:
        await _show_pricing_list(query, pid, context)


def get_handlers():
    return [
        CallbackQueryHandler(pm_pricing, pattern=r"^pm_pricing$"),
        CallbackQueryHandler(pm_pricing_prod, pattern=r"^pm_pricing_prod$"),
        CallbackQueryHandler(pm_pricing_list, pattern=r"^pm_pricing_list$"),
        CallbackQueryHandler(pm_pricing_show, pattern=r"^pm_pricing_show:"),
        CallbackQueryHandler(pm_price_edit, pattern=r"^pm_price_edit:"),
        CallbackQueryHandler(pm_price_skip, pattern=r"^pm_price_skip:"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, pm_price_message),
    ]
