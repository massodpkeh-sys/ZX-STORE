# handlers/shop.py
# ============================================================
# ABHAY PANEL STORE - SHOP
# Single-message editing architecture
# Products 1 column | User vs Reseller auto-detect
# ============================================================

from __future__ import annotations

import logging
import time
from decimal import Decimal

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

import config
import database
from services import supplier

logger = logging.getLogger(__name__)

STORE_NAME = "ABHAY PANEL STORE"
MAX_NAME_LEN = 30


# ============================================================
# HELPERS
# ============================================================

def money(value) -> Decimal:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")


def fmt_money(value) -> str:
    amount = money(value)
    if amount == amount.to_integral():
        return f"₹{int(amount)}"
    return f"₹{amount:.2f}"


def get_display_name(product: dict) -> str:
    name = product.get("display_name") or product.get("name") or "Unknown"
    if len(name) > MAX_NAME_LEN:
        name = name[: MAX_NAME_LEN - 1].rstrip() + "…"
    return name


def get_style(product: dict) -> str:
    maint = product.get("maintenance", 0)
    if maint:
        return "danger"
    style = (product.get("style") or "success").lower()
    if style == "danger":
        return "danger"
    if style == "primary":
        return "primary"
    return "success"


def is_user_reseller(user_id: int) -> bool:
    """Check karta hai user active reseller hai ya nahi."""
    try:
        u = database.get_user(user_id)
        if not u:
            return False
        expiry = int(u.get("reseller_expiry") or 0)
        return expiry > int(time.time())
    except Exception:
        return False


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
# SHOP HOME — Products List (1 Column)
# ============================================================

async def shop_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await safe_answer(query)

    products = database.get_products()

    if not products:
        text = "🛒 <b>Shop</b>\n\nAbhi koi product available nahi hai."
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("‹ Back", callback_data="main_menu", style="primary")]
        ])
        if query:
            await safe_edit(query, text, markup)
        else:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)
        return

    # ============================================================
    # 1 COLUMN — Ek ke niche ek
    # ============================================================
    buttons = []

    for p in products:
        pid = p.get("supplier_pid")
        name = get_display_name(p)
        style = get_style(p)

        btn = InlineKeyboardButton(
            name,
            callback_data=f"shop_prod:{pid}",
            style=style,
        )

        buttons.append([btn])

    buttons.append([
        InlineKeyboardButton("‹ Back", callback_data="main_menu", style="primary")
    ])

    text = f"🛒 <b>{STORE_NAME} - Shop</b>\n\nProduct select karein"
    markup = InlineKeyboardMarkup(buttons)

    if query:
        await safe_edit(query, text, markup)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)


# ============================================================
# PRODUCT -> DURATIONS (1 Column)
# ============================================================

async def shop_product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    try:
        pid = query.data.split(":", 1)[1]
    except Exception:
        await safe_answer(query, "Invalid product.", show_alert=True)
        return

    product = database.get_product(pid)

    if not product:
        await safe_answer(query, "Product not found.", show_alert=True)
        return

    name = get_display_name(product)
    maintenance = product.get("maintenance", 0)
    durations = product.get("durations", [])

    if maintenance:
        text = f"<b>{name}</b>\n\nYeh product abhi maintenance me hai."
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("‹ Back", callback_data="shop_home", style="primary")]
        ])
        await safe_edit(query, text, markup)
        return

    if not durations:
        text = f"<b>{name}</b>\n\nKoi duration available nahi hai."
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("‹ Back", callback_data="shop_home", style="primary")]
        ])
        await safe_edit(query, text, markup)
        return

    user_id = query.from_user.id
    balance = database.get_wallet_balance(user_id)

    # ============================================================
    # AUTO-DETECT — User ya Reseller
    # ============================================================
    is_reseller = is_user_reseller(user_id)

    buttons = []

    for dur_row in durations:
        if isinstance(dur_row, dict):
            dur_name = (
                dur_row.get("display_duration")
                or dur_row.get("duration")
                or dur_row.get("name")
            )
            supplier_cost = dur_row.get("supplier_cost") or dur_row.get("cost")
            user_price = dur_row.get("display_price")
            reseller_price = dur_row.get("reseller_price")
        else:
            dur_name = dur_row[0]
            supplier_cost = dur_row[1] if len(dur_row) > 1 else None
            user_price = dur_row[2] if len(dur_row) > 2 else None
            reseller_price = None

        # Price select
        if is_reseller and reseller_price is not None:
            show_price = reseller_price
        else:
            show_price = user_price if user_price is not None else supplier_cost

        if show_price is None:
            btn = InlineKeyboardButton(
                f"{dur_name}",
                callback_data=f"shop_dur:{pid}:{dur_name}",
                style="danger",
            )
        else:
            btn = InlineKeyboardButton(
                f"{dur_name} - {fmt_money(show_price)}",
                callback_data=f"shop_dur:{pid}:{dur_name}",
                style="success",
            )

        buttons.append([btn])

    buttons.append([
        InlineKeyboardButton("‹ Back", callback_data="shop_home", style="primary")
    ])

    # Account type label
    if is_reseller:
        account_label = "👑 Reseller"
    else:
        account_label = "🔓 Standard User"

    text = (
        f"<b>{name}</b>\n\n"
        f"🎫 Account: {account_label}\n"
        f"💰 Balance: <b>{fmt_money(balance)}</b>\n\n"
        "Duration select karein"
    )

    await safe_edit(query, text, InlineKeyboardMarkup(buttons))


# ============================================================
# DURATION -> CONFIRM
# ============================================================

async def shop_duration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    try:
        _, pid, duration = query.data.split(":", 2)
    except Exception:
        await safe_answer(query, "Invalid selection.", show_alert=True)
        return

    product = database.get_product(pid)
    if not product:
        await safe_answer(query, "Product not found.", show_alert=True)
        return

    user_id = query.from_user.id
    is_reseller = is_user_reseller(user_id)

    show_price = None
    display_dur = duration

    for dur_row in product.get("durations", []):
        if isinstance(dur_row, dict):
            dur_key = dur_row.get("duration") or dur_row.get("name")
            sc = dur_row.get("supplier_cost") or dur_row.get("cost")
            up = dur_row.get("display_price")
            rp = dur_row.get("reseller_price")
            dd = dur_row.get("display_duration") or dur_key
        else:
            dur_key = dur_row[0]
            sc = dur_row[1] if len(dur_row) > 1 else None
            up = dur_row[2] if len(dur_row) > 2 else None
            rp = None
            dd = dur_key

        if dur_key == duration or dd == duration:
            if is_reseller and rp is not None:
                show_price = rp
            else:
                show_price = up if up is not None else sc
            display_dur = dd
            break

    if show_price is None:
        await safe_answer(query, "Yeh duration out of stock hai.", show_alert=True)
        return

    balance = database.get_wallet_balance(user_id)
    price_dec = money(show_price)

    if balance < price_dec:
        text = (
            f"❌ <b>Insufficient Balance</b>\n\n"
            f"Required: <b>{fmt_money(price_dec)}</b>\n"
            f"Your Balance: <b>{fmt_money(balance)}</b>\n\n"
            "Pehle balance add karein."
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Add Balance", callback_data="wallet_add", style="success")],
            [InlineKeyboardButton("‹ Back", callback_data=f"shop_prod:{pid}", style="primary")],
        ])
        await safe_edit(query, text, markup)
        return

    context.user_data["pending_purchase"] = {
        "pid": pid,
        "name": product.get("name"),
        "duration": duration,
        "display_duration": display_dur,
        "price": str(price_dec),
        "is_reseller": is_reseller,
    }

    account_label = "👑 Reseller" if is_reseller else "🔓 User"

    text = (
        f"<b>Confirm Purchase</b>\n\n"
        f"📦 Product: <b>{get_display_name(product)}</b>\n"
        f"⏱ Duration: <b>{display_dur}</b>\n"
        f"💰 Price: <b>{fmt_money(price_dec)}</b>\n"
        f"🎫 Account: {account_label}\n"
        f"💳 Balance: <b>{fmt_money(balance)}</b>\n\n"
        "Confirm karein?"
    )

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data="shop_confirm", style="success"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"shop_prod:{pid}", style="danger"),
        ],
    ])
    await safe_edit(query, text, markup)


# ============================================================
# CONFIRM PURCHASE
# ============================================================

async def shop_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query, "Processing...")

    pending = context.user_data.get("pending_purchase")
    if not pending:
        text = "Purchase session expired. Dobara try karein."
        await safe_edit(query, text, None)
        return

    user_id = query.from_user.id
    pid = pending["pid"]
    duration = pending["duration"]
    display_dur = pending.get("display_duration", duration)
    price = money(pending["price"])

    balance = database.get_wallet_balance(user_id)
    if balance < price:
        text = f"Insufficient balance. Required: {fmt_money(price)}"
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Add Balance", callback_data="wallet_add", style="success")]
        ])
        await safe_edit(query, text, markup)
        return

    debited = database.debit_wallet(user_id, float(price), f"BUY-{pid}-{duration}")
    if not debited:
        await safe_edit(query, "Wallet debit failed. Please try again.", None)
        return

    try:
        result = await supplier.buy_key(product_id=pid, duration=duration, quantity=1)
    except Exception as e:
        logger.exception("Supplier purchase failed")
        database.credit_wallet(user_id, float(price), f"REFUND-{pid}")
        text = f"Supplier error: <code>{str(e)[:200]}</code>\n\nAapka paisa refund kar diya gaya hai."
        await safe_edit(query, text, None)
        return

    keys = result.get("keys") or []
    if not keys:
        database.credit_wallet(user_id, float(price), f"REFUND-{pid}")
        await safe_edit(query, "Key nahi mili. Paisa refund kar diya gaya.", None)
        return

    database.create_order(
        user_id=user_id,
        product_id=str(pid),
        duration=duration,
        price=float(price),
        keys=keys,
        product_name=pending.get("name") or "",
    )
    context.user_data.pop("pending_purchase", None)
    new_balance = database.get_wallet_balance(user_id)

    key_text = "\n".join(f"<code>{k}</code>" for k in keys)
    text = (
        f"✅ <b>Purchase Successful</b>\n\n"
        f"📦 Product: <b>{pending['name']}</b>\n"
        f"⏱ Duration: <b>{display_dur}</b>\n"
        f"💰 Paid: <b>{fmt_money(price)}</b>\n"
        f"💳 New Balance: <b>{fmt_money(new_balance)}</b>\n\n"
        f"🔑 <b>Your Key(s):</b>\n{key_text}\n\n"
        "⚠️ Key ko safe rakhein."
    )

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛒 Shop More", callback_data="shop_home", style="success"),
            InlineKeyboardButton("🏠 Menu", callback_data="main_menu", style="primary"),
        ],
    ])
    await safe_edit(query, text, markup)


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(shop_home, pattern=r"^shop_home$"),
        CallbackQueryHandler(shop_product_callback, pattern=r"^shop_prod:"),
        CallbackQueryHandler(shop_duration_callback, pattern=r"^shop_dur:"),
        CallbackQueryHandler(shop_confirm_callback, pattern=r"^shop_confirm$"),
    ]
