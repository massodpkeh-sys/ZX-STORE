# handlers/admin_panel/products_details.py
# ============================================================
# ADMIN PANEL - PRODUCT DETAILS (Name / Photo / Features)
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
# DETAILS MENU
# ============================================================

async def details_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    text = (
        f"✏️ <b>EDIT PRODUCT DETAILS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 <b>{name}</b>\n\n"
        f"👇 Kya edit karna hai?"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📛 Edit Name", callback_data=f"pd_name:{pid}", style="success")],
        [InlineKeyboardButton("🖼️ Edit Photo", callback_data=f"pd_photo:{pid}", style="primary")],
        [InlineKeyboardButton("📝 Edit Features", callback_data=f"pd_features:{pid}", style="primary")],
        [InlineKeyboardButton("‹ Back", callback_data=f"admin_prod_view:{pid}", style="primary")],
    ])

    await safe_edit(query, text, markup)


# ============================================================
# EDIT NAME
# ============================================================

async def details_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    pid = query.data.split(":", 1)[1]
    product = database.get_product(pid)
    if not product:
        await safe_answer(query, "Not found", show_alert=True)
        return

    context.user_data["pd_name_pid"] = pid

    text = (
        f"📛 <b>EDIT NAME</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Current: <b>{product.get('display_name') or product.get('name')}</b>\n\n"
        f"👇 <b>Naya naam bhejein:</b>"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data=f"pd_menu:{pid}", style="danger")],
    ])
    await safe_edit(query, text, markup)


async def details_name_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = context.user_data.get("pd_name_pid")
    if not pid:
        return
    if not is_admin(update.effective_user.id):
        return
    if not update.message or not update.message.text:
        return

    new_name = update.message.text.strip()

    try:
        await update.message.delete()
    except Exception:
        pass

    if len(new_name) < 2:
        await update.effective_chat.send_message("❌ Name chhota hai.")
        return

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("UPDATE products SET display_name = ? WHERE supplier_pid = ?", (new_name, str(pid)))
        conn.commit()
        conn.close()

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Edit Details", callback_data=f"pd_menu:{pid}", style="primary")],
            [InlineKeyboardButton("‹ Product", callback_data=f"admin_prod_view:{pid}", style="primary")],
        ])
        await update.effective_chat.send_message(
            f"✅ <b>Name Set!</b>\n\n📛 {new_name}",
            parse_mode="HTML",
            reply_markup=markup,
        )
    except Exception as e:
        await update.effective_chat.send_message(f"❌ Failed: {str(e)[:100]}")

    context.user_data.pop("pd_name_pid", None)


# ============================================================
# EDIT PHOTO
# ============================================================

async def details_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    pid = query.data.split(":", 1)[1]
    product = database.get_product(pid)
    if not product:
        await safe_answer(query, "Not found", show_alert=True)
        return

    context.user_data["pd_photo_pid"] = pid

    text = (
        f"🖼️ <b>EDIT PHOTO</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 {product.get('display_name') or product.get('name')}\n\n"
        f"👇 <b>Nayi photo bhejein:</b>"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data=f"pd_menu:{pid}", style="danger")],
    ])
    await safe_edit(query, text, markup)


async def details_photo_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = context.user_data.get("pd_photo_pid")
    if not pid:
        return
    if not is_admin(update.effective_user.id):
        return
    if not update.message or not update.message.photo:
        return

    file_id = update.message.photo[-1].file_id

    try:
        await update.message.delete()
    except Exception:
        pass

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(products)")
        cols = [r[1] for r in cur.fetchall()]
        if "photo_id" not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN photo_id TEXT")
        cur.execute("UPDATE products SET photo_id = ? WHERE supplier_pid = ?", (file_id, str(pid)))
        conn.commit()
        conn.close()

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Edit Details", callback_data=f"pd_menu:{pid}", style="primary")],
            [InlineKeyboardButton("‹ Product", callback_data=f"admin_prod_view:{pid}", style="primary")],
        ])
        await update.effective_chat.send_message(
            "✅ <b>Photo Set!</b>",
            parse_mode="HTML",
            reply_markup=markup,
        )
    except Exception as e:
        await update.effective_chat.send_message(f"❌ Failed: {str(e)[:100]}")

    context.user_data.pop("pd_photo_pid", None)


# ============================================================
# EDIT FEATURES
# ============================================================

async def details_features(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    pid = query.data.split(":", 1)[1]
    product = database.get_product(pid)
    if not product:
        await safe_answer(query, "Not found", show_alert=True)
        return

    context.user_data["pd_features_pid"] = pid

    text = (
        f"📝 <b>EDIT FEATURES</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 {product.get('display_name') or product.get('name')}\n\n"
        f"👇 <b>Features bhejein (comma se alag):</b>\n\n"
        f"<b>Example:</b>\n"
        f"<code>Aimbot, Silent Aim, ESP, Speed</code>"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data=f"pd_menu:{pid}", style="danger")],
    ])
    await safe_edit(query, text, markup)


async def details_features_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = context.user_data.get("pd_features_pid")
    if not pid:
        return
    if not is_admin(update.effective_user.id):
        return
    if not update.message or not update.message.text:
        return

    features = update.message.text.strip()

    try:
        await update.message.delete()
    except Exception:
        pass

    if not features:
        return

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(products)")
        cols = [r[1] for r in cur.fetchall()]
        if "features" not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN features TEXT")
        cur.execute("UPDATE products SET features = ? WHERE supplier_pid = ?", (features, str(pid)))
        conn.commit()
        conn.close()

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Edit Details", callback_data=f"pd_menu:{pid}", style="primary")],
            [InlineKeyboardButton("‹ Product", callback_data=f"admin_prod_view:{pid}", style="primary")],
        ])
        await update.effective_chat.send_message(
            f"✅ <b>Features Set!</b>\n\n📝 {features}",
            parse_mode="HTML",
            reply_markup=markup,
        )
    except Exception as e:
        await update.effective_chat.send_message(f"❌ Failed: {str(e)[:100]}")

    context.user_data.pop("pd_features_pid", None)


# ============================================================
# ROUTER
# ============================================================

async def details_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if context.user_data.get("pd_name_pid"):
        await details_name_save(update, context)
        return
    if context.user_data.get("pd_photo_pid"):
        await details_photo_save(update, context)
        return
    if context.user_data.get("pd_features_pid"):
        await details_features_save(update, context)
        return


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(details_menu, pattern=r"^pd_menu:"),
        CallbackQueryHandler(details_name, pattern=r"^pd_name:"),
        CallbackQueryHandler(details_photo, pattern=r"^pd_photo:"),
        CallbackQueryHandler(details_features, pattern=r"^pd_features:"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, details_router),
        MessageHandler(filters.PHOTO & ~filters.COMMAND, details_router),
    ]
