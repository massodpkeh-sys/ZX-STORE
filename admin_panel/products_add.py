# handlers/admin_panel/products_add.py
# ============================================================
# ADMIN PANEL - ADD NEW PRODUCT
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


# ============================================================
# STEP 1: Start Add Product
# ============================================================

async def start_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    # Clear all state
    for k in ["add_pid", "add_name", "add_category", "add_style", "add_stage"]:
        context.user_data.pop(k, None)

    context.user_data["add_stage"] = "pid"

    text = (
        f"➕ <b>ADD NEW PRODUCT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Step 1/4: Supplier PID</b>\n\n"
        f"👇 Supplier ka <b>PID</b> bhejein:\n\n"
        f"Example: <code>54</code>\n\n"
        f"<i>(Ye PID supplier website se milega)</i>"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_products", style="danger")],
    ])

    # Save message ID for edits
    try:
        await safe_edit(query, text, markup)
        context.user_data["add_msg_id"] = query.message.message_id
    except Exception:
        pass


# ============================================================
# STEP 2-4: Receive inputs (via message)
# ============================================================

async def add_product_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    if not is_admin(update.effective_user.id):
        return

    stage = context.user_data.get("add_stage")
    if not stage:
        return

    raw = update.message.text.strip()

    # Delete user message
    try:
        await update.message.delete()
    except Exception:
        pass

    # -------- STEP 1: PID --------
    if stage == "pid":
        try:
            pid = int(raw)
        except Exception:
            await _send_error(update, context, "❌ PID number hona chahiye.\n\nExample: <code>54</code>")
            return

        # Duplicate check
        existing = database.get_product(str(pid))
        if existing:
            await _send_error(
                update, context,
                f"❌ PID <code>{pid}</code> already exists!\n\nDusra PID bhejein.",
            )
            return

        context.user_data["add_pid"] = pid
        context.user_data["add_stage"] = "name"

        text = (
            f"➕ <b>ADD NEW PRODUCT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>Step 2/4: Product Name</b>\n\n"
            f"🆔 PID: <code>{pid}</code>\n\n"
            f"👇 Product ka <b>display name</b> bhejein:\n\n"
            f"Example: <code>DRIP CLIENT APK</code>"
        )

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="admin_products", style="danger")],
        ])

        await _send_edit_message(update, context, text, markup)
        return

    # -------- STEP 2: NAME --------
    if stage == "name":
        if len(raw) < 2:
            await _send_error(update, context, "❌ Name chhota hai. Dobara bhejein.")
            return

        context.user_data["add_name"] = raw
        context.user_data["add_stage"] = "category"

        text = (
            f"➕ <b>ADD NEW PRODUCT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>Step 3/4: Category</b>\n\n"
            f"📛 Name: <b>{raw}</b>\n\n"
            f"👇 Category select karein:"
        )

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 NON ROOT", callback_data="addcat:NON ROOT", style="success")],
            [InlineKeyboardButton("🔴 ROOT", callback_data="addcat:ROOT", style="danger")],
            [InlineKeyboardButton("🔵 PC + IOS", callback_data="addcat:PC + IOS", style="primary")],
            [InlineKeyboardButton("❌ Cancel", callback_data="admin_products", style="danger")],
        ])

        await _send_edit_message(update, context, text, markup)
        return


# ============================================================
# STEP 3: Category callback
# ============================================================

async def add_category_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    if context.user_data.get("add_stage") != "category":
        return

    try:
        category = query.data.split(":", 1)[1]
    except Exception:
        return

    context.user_data["add_category"] = category
    context.user_data["add_stage"] = "style"

    text = (
        f"➕ <b>ADD NEW PRODUCT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Step 4/4: Style</b>\n\n"
        f"📁 Category: <b>{category}</b>\n\n"
        f"👇 Color style select karein:"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Success (Green)", callback_data="addstyle:success", style="success")],
        [InlineKeyboardButton("🔴 Danger (Red)", callback_data="addstyle:danger", style="danger")],
        [InlineKeyboardButton("🔵 Primary (Blue)", callback_data="addstyle:primary", style="primary")],
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_products", style="danger")],
    ])

    # Same message edit
    await safe_edit(query, text, markup)


# ============================================================
# STEP 4: Style callback — Save product
# ============================================================

async def add_style_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    if context.user_data.get("add_stage") != "style":
        return

    try:
        style = query.data.split(":", 1)[1]
    except Exception:
        return

    pid = context.user_data.get("add_pid")
    name = context.user_data.get("add_name")
    category = context.user_data.get("add_category")

    if not pid or not name or not category:
        await safe_answer(query, "❌ Data missing", show_alert=True)
        return

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO products (supplier_pid, name, display_name, category, style, maintenance)
               VALUES (?, ?, ?, ?, ?, 0)""",
            (str(pid), name, name, category, style),
        )
        conn.commit()
        conn.close()

        # Clear state
        for k in ["add_pid", "add_name", "add_category", "add_style", "add_stage", "add_msg_id"]:
            context.user_data.pop(k, None)

        text = (
            f"✅ <b>PRODUCT ADDED!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 PID: <code>{pid}</code>\n"
            f"📛 Name: <b>{name}</b>\n"
            f"📁 Category: {category}\n"
            f"🎨 Style: {style}\n\n"
            f"<i>Ab isme durations add karein</i>"
        )

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍 View Products", callback_data="admin_products", style="success")],
            [InlineKeyboardButton("‹ Admin Home", callback_data="admin_home", style="primary")],
        ])

    except Exception as e:
        logger.exception("Add product failed")
        text = f"❌ <b>Failed:</b> <code>{str(e)[:200]}</code>"
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("‹ Products", callback_data="admin_products", style="primary")],
        ])

    # Same message edit
    await safe_edit(query, text, markup)


# ============================================================
# HELPERS — same message edit
# ============================================================

async def _send_edit_message(update, context, text, markup):
    """Same message edit karta hai (admin_msg_id se)."""
    msg_id = context.user_data.get("add_msg_id")
    chat_id = update.effective_chat.id

    if msg_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=text,
                parse_mode="HTML",
                reply_markup=markup,
                disable_web_page_preview=True,
            )
            return
        except Exception:
            pass

    # Fallback — naya message
    try:
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=markup,
        )
        context.user_data["add_msg_id"] = msg.message_id
    except Exception:
        pass


async def _send_error(update, context, text):
    """Error message — same message edit."""
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_products", style="danger")],
    ])
    await _send_edit_message(update, context, text, markup)


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(add_category_cb, pattern=r"^addcat:"),
        CallbackQueryHandler(add_style_cb, pattern=r"^addstyle:"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_router),
    ]
