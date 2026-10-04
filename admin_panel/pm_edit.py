# handlers/admin_panel/pm_edit.py
# ============================================================
# ADMIN PANEL - EDIT PRODUCT
# ============================================================

from __future__ import annotations

import logging
import json

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler, ContextTypes, MessageHandler, filters,
)

import database
from handlers.admin_panel.menu import is_admin, safe_answer, safe_edit

logger = logging.getLogger(__name__)


async def pm_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    products = database.get_products()

    if not products:
        await safe_edit(query, "❌ Koi product nahi hai.", InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="pm_products", style="primary")],
        ]))
        return

    buttons = []
    for p in products:
        pid = p.get("supplier_pid")
        name = p.get("display_name") or p.get("name") or "?"
        buttons.append([
            InlineKeyboardButton(
                f"✏️ {name}",
                callback_data=f"pm_edit_sel:{pid}",
                style="primary",
            )
        ])

    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="pm_products", style="primary")])

    text = "✏️ <b>EDIT PRODUCT</b>\n━━━━━━━━━━━━━━━━━━━\n\nKaunsa product edit karna hai?"
    await safe_edit(query, text, InlineKeyboardMarkup(buttons))


async def pm_edit_sel(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    context.user_data["pm_edit_pid"] = pid

    text = (
        f"✏️ <b>EDIT: {name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 Kya edit karna hai?"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Edit Name", callback_data="pm_edit_name", style="success")],
        [InlineKeyboardButton("📋 Edit Features", callback_data="pm_edit_feats", style="primary")],
        [InlineKeyboardButton("💰 Edit Pricing", callback_data="pm_pricing_prod", style="primary")],
        [InlineKeyboardButton("🎬 Edit Demo Video", callback_data="pm_demo_prod", style="primary")],
        [InlineKeyboardButton("🗑️ Delete This Product", callback_data=f"pm_del_confirm:{pid}", style="danger")],
        [InlineKeyboardButton("🔙 Back", callback_data="pm_edit", style="primary")],
    ])
    await safe_edit(query, text, markup)


async def pm_edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    pid = context.user_data.get("pm_edit_pid")
    if not pid:
        await safe_answer(query, "Session expired", show_alert=True)
        return

    product = database.get_product(pid)
    if not product:
        return

    context.user_data["pm_edit_stage"] = "name"

    text = (
        f"📝 <b>EDIT NAME</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"📛 Current: <b>{product.get('display_name') or product.get('name')}</b>\n\n"
        f"👇 Naya naam bhejein:"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data=f"pm_edit_sel:{pid}", style="primary")],
    ])
    await safe_edit(query, text, markup)


async def pm_edit_feats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    pid = context.user_data.get("pm_edit_pid")
    if not pid:
        await safe_answer(query, "Session expired", show_alert=True)
        return

    product = database.get_product(pid)
    if not product:
        return

    context.user_data["pm_edit_stage"] = "features"

    feats_raw = product.get("features") or "[]"
    try:
        feats = json.loads(feats_raw) if isinstance(feats_raw, str) else feats_raw
    except Exception:
        feats = []

    lines = ["📋 <b>EDIT FEATURES</b>", "━━━━━━━━━━━━━━━━━━━", "", "<b>Current Features:</b>"]
    if feats:
        for i, f in enumerate(feats, 1):
            lines.append(f"{i}. {f}")
    else:
        lines.append("(none)")

    lines.extend([
        "",
        "👇 Comma (,) se separate karke nayi list bhejein:",
        "Example: <code>Aimbot, ESP, Speed</code>",
    ])
    text = "\n".join(lines)
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data=f"pm_edit_sel:{pid}", style="primary")],
    ])
    await safe_edit(query, text, markup)


async def pm_edit_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if not is_admin(update.effective_user.id):
        return

    stage = context.user_data.get("pm_edit_stage")
    pid = context.user_data.get("pm_edit_pid")
    if not stage or not pid:
        return

    raw = update.message.text.strip()
    try:
        await update.message.delete()
    except Exception:
        pass

    # NAME
    if stage == "name":
        if len(raw) < 2:
            await update.effective_chat.send_message("❌ Name chhota hai.")
            return

        try:
            conn = database._conn()
            cur = conn.cursor()
            cur.execute("UPDATE products SET display_name = ? WHERE supplier_pid = ?", (raw, str(pid)))
            conn.commit()
            conn.close()
            await update.effective_chat.send_message(f"✅ Name updated: <b>{raw}</b>", parse_mode="HTML")
        except Exception as e:
            await update.effective_chat.send_message(f"❌ Error: {str(e)[:100]}")

        context.user_data.pop("pm_edit_stage", None)
        return

    # FEATURES
    if stage == "features":
        feats = [f.strip() for f in raw.split(",") if f.strip()]
        try:
            conn = database._conn()
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(products)")
            cols = [r[1] for r in cur.fetchall()]
            if "features" not in cols:
                cur.execute("ALTER TABLE products ADD COLUMN features TEXT")
            cur.execute("UPDATE products SET features = ? WHERE supplier_pid = ?",
                        (json.dumps(feats), str(pid)))
            conn.commit()
            conn.close()
            await update.effective_chat.send_message(
                f"✅ <b>{len(feats)} features updated!</b>", parse_mode="HTML",
            )
        except Exception as e:
            await update.effective_chat.send_message(f"❌ Error: {str(e)[:100]}")

        context.user_data.pop("pm_edit_stage", None)
        return


def get_handlers():
    return [
        CallbackQueryHandler(pm_edit, pattern=r"^pm_edit$"),
        CallbackQueryHandler(pm_edit_sel, pattern=r"^pm_edit_sel:"),
        CallbackQueryHandler(pm_edit_name, pattern=r"^pm_edit_name$"),
        CallbackQueryHandler(pm_edit_feats, pattern=r"^pm_edit_feats$"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, pm_edit_message),
    ]
