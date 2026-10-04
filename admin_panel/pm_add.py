# handlers/admin_panel/pm_add.py
# ============================================================
# ADMIN PANEL - ADD NEW PRODUCT (STEP BY STEP)
# ============================================================

from __future__ import annotations

import logging
import json
import random
import string

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler, ContextTypes, MessageHandler, filters,
)

import database
from handlers.admin_panel.menu import is_admin, safe_answer, safe_edit

logger = logging.getLogger(__name__)


# ============================================================
# STEP 1: START
# ============================================================

async def pm_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    # Reset
    for k in ["pm_name", "pm_features", "pm_prices", "pm_demo_link", "pm_stage"]:
        context.user_data.pop(k, None)

    context.user_data["pm_stage"] = "name"
    context.user_data["pm_features"] = []
    context.user_data["pm_prices"] = []

    text = (
        "➕ <b>ADD NEW PRODUCT</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "🔹 <b>STEP 1 - Product Name</b>\n\n"
        "👇 Product ka naam type karein:"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="pm_products", style="danger")],
    ])
    await safe_edit(query, text, markup)


# ============================================================
# MESSAGE ROUTER — saare inputs yahan aayenge
# ============================================================

async def pm_add_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if not is_admin(update.effective_user.id):
        return

    stage = context.user_data.get("pm_stage")
    if not stage:
        return

    raw = update.message.text.strip()

    try:
        await update.message.delete()
    except Exception:
        pass

    # ============================================================
    # STEP 1: NAME
    # ============================================================
    if stage == "name":
        if len(raw) < 2:
            await update.effective_chat.send_message("❌ Name chhota hai. Dobara bhejein.")
            return

        context.user_data["pm_name"] = raw
        context.user_data["pm_stage"] = "features"

        text = (
            f"➕ <b>ADD NEW PRODUCT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔹 <b>STEP 2 - Features</b>\n\n"
            f"📛 Name: <b>{raw}</b>\n"
            f"📋 Features: <b>{len(context.user_data.get('pm_features', []))}</b> added\n\n"
            f"👇 Feature add karein ya next step dabayein:"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Feature", callback_data="pm_add_feature", style="success")],
            [InlineKeyboardButton("📋 Paste Full List", callback_data="pm_paste_features", style="primary")],
            [InlineKeyboardButton("👁️ Preview Features", callback_data="pm_preview_features", style="primary")],
            [InlineKeyboardButton("⏭️ Next Step", callback_data="pm_next_features", style="success")],
            [InlineKeyboardButton("🔙 Back", callback_data="pm_add", style="primary")],
        ])
        await update.effective_chat.send_message(text, parse_mode="HTML", reply_markup=markup)
        return

    # ============================================================
    # STEP 2: PASTE FEATURES
    # ============================================================
    if stage == "paste_features":
        feats = [f.strip() for f in raw.split(",") if f.strip()]
        if not feats:
            await update.effective_chat.send_message("❌ Features empty.")
            return

        context.user_data["pm_features"] = feats
        context.user_data["pm_stage"] = "features"

        text = f"✅ <b>{len(feats)} features added!</b>\n\n👇 Ab next step dabayein:"
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add More", callback_data="pm_add_feature", style="success")],
            [InlineKeyboardButton("👁️ Preview", callback_data="pm_preview_features", style="primary")],
            [InlineKeyboardButton("⏭️ Next Step", callback_data="pm_next_features", style="success")],
            [InlineKeyboardButton("🔙 Back", callback_data="pm_add", style="primary")],
        ])
        await update.effective_chat.send_message(text, parse_mode="HTML", reply_markup=markup)
        return

    # ============================================================
    # STEP 3: ADD DURATION
    # ============================================================
    if stage == "add_duration":
        # Format: 1 Day 49
        parts = raw.split()
        if len(parts) < 2:
            await update.effective_chat.send_message(
                "❌ Format: <code>DURATION PRICE</code>\nExample: <code>1 Day 49</code>",
                parse_mode="HTML",
            )
            return

        try:
            price = float(parts[-1])
            dur_name = " ".join(parts[:-1])
        except Exception:
            await update.effective_chat.send_message("❌ Price number nahi hai.")
            return

        if price <= 0:
            await update.effective_chat.send_message("❌ Price 0 se zyada hona chahiye.")
            return

        context.user_data.setdefault("pm_prices", []).append({
            "duration": dur_name,
            "display_duration": dur_name,
            "cost": price,
            "display_price": price,
            "reseller_price": price,
        })
        context.user_data["pm_stage"] = "prices"

        text = (
            f"✅ <b>{dur_name} - ₹{price:.0f} added!</b>\n\n"
            f"📊 Total durations: <b>{len(context.user_data['pm_prices'])}</b>\n\n"
            f"👇 Aur add karein ya next step:"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add More", callback_data="pm_add_dur", style="success")],
            [InlineKeyboardButton("⏭️ Next Step", callback_data="pm_next_prices", style="success")],
            [InlineKeyboardButton("🔙 Back", callback_data="pm_add", style="primary")],
        ])
        await update.effective_chat.send_message(text, parse_mode="HTML", reply_markup=markup)
        return

    # ============================================================
    # STEP 4: DEMO LINK
    # ============================================================
    if stage == "demo_link":
        context.user_data["pm_demo_link"] = raw
        context.user_data["pm_stage"] = "confirm"

        await _show_confirm(update, context)
        return

    # ============================================================
    # STEP 2B: SINGLE FEATURE INPUT
    # ============================================================
    if stage == "feature_input":
        if not raw:
            return

        context.user_data.setdefault("pm_features", []).append(raw)
        context.user_data["pm_stage"] = "features"

        feats = context.user_data["pm_features"]
        lines = ["✅ <b>Feature added!</b>\n", "📋 <b>Current Features:</b>"]
        for i, f in enumerate(feats, 1):
            lines.append(f"{i}. {f}")
        text = "\n".join(lines) + "\n\n👇 Aur add karein:"

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Another", callback_data="pm_add_feature", style="success")],
            [InlineKeyboardButton("👁️ Preview", callback_data="pm_preview_features", style="primary")],
            [InlineKeyboardButton("⏭️ Next Step", callback_data="pm_next_features", style="success")],
            [InlineKeyboardButton("🔙 Back", callback_data="pm_add", style="primary")],
        ])
        await update.effective_chat.send_message(text, parse_mode="HTML", reply_markup=markup)
        return


# ============================================================
# CALLBACKS
# ============================================================

async def pm_add_feature(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    context.user_data["pm_stage"] = "feature_input"

    text = (
        "➕ <b>ADD FEATURE</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "👇 Feature ka naam type karein:\n\n"
        "Example: <code>Aimbot</code>"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="pm_next_features", style="danger")],
    ])
    await safe_edit(query, text, markup)


async def pm_paste_features(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    context.user_data["pm_stage"] = "paste_features"

    text = (
        "📋 <b>PASTE FULL LIST</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "👇 Features comma (,) se separate karke bhejein:\n\n"
        "Example: <code>Aimbot, Silent Aim, ESP, Speed</code>"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="pm_next_features", style="danger")],
    ])
    await safe_edit(query, text, markup)


async def pm_preview_features(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    feats = context.user_data.get("pm_features", [])

    if not feats:
        text = "❌ Koi feature nahi hai."
    else:
        lines = ["👁️ <b>FEATURES PREVIEW</b>", "━━━━━━━━━━━━━━━━━━━", ""]
        for i, f in enumerate(feats, 1):
            lines.append(f"🟢 {f}")
        text = "\n".join(lines)

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add More", callback_data="pm_add_feature", style="success")],
        [InlineKeyboardButton("⏭️ Next Step", callback_data="pm_next_features", style="success")],
        [InlineKeyboardButton("🔙 Back", callback_data="pm_add", style="primary")],
    ])
    await safe_edit(query, text, markup)


async def pm_next_features(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    context.user_data["pm_stage"] = "prices"

    name = context.user_data.get("pm_name", "?")
    feats = context.user_data.get("pm_features", [])
    prices = context.user_data.get("pm_prices", [])

    lines = [
        "➕ <b>ADD NEW PRODUCT</b>",
        "━━━━━━━━━━━━━━━━━━━",
        "",
        "🔹 <b>STEP 3 - Duration & Pricing</b>",
        "",
        f"📛 Name: <b>{name}</b>",
        f"📋 Features: <b>{len(feats)}</b>",
        f"💰 Prices: <b>{len(prices)}</b>",
        "",
    ]

    if prices:
        lines.append("<b>Durations:</b>")
        for p in prices:
            lines.append(f"⏱️ {p['duration']} - ₹{p['display_price']:.0f}")
        lines.append("")

    lines.append("👇 Duration add karein ya next step dabayein:")

    text = "\n".join(lines)
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Custom Duration", callback_data="pm_add_dur", style="success")],
        [InlineKeyboardButton("⏭️ Next Step", callback_data="pm_next_prices", style="success")],
        [InlineKeyboardButton("🔙 Back", callback_data="pm_add", style="primary")],
    ])
    await safe_edit(query, text, markup)


async def pm_add_dur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    context.user_data["pm_stage"] = "add_duration"

    text = (
        "➕ <b>ADD DURATION</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "👇 Duration aur price bhejein:\n\n"
        "Format: <code>DURATION PRICE</code>\n\n"
        "<b>Examples:</b>\n"
        "<code>1 Day 49</code>\n"
        "<code>7 Days 230</code>\n"
        "<code>30 Days 499</code>"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="pm_next_prices", style="danger")],
    ])
    await safe_edit(query, text, markup)


async def pm_next_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    context.user_data["pm_stage"] = "demo_link"

    text = (
        "➕ <b>ADD NEW PRODUCT</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "🔹 <b>STEP 4 - Demo Video</b>\n\n"
        "👇 YouTube link bhejein ya skip karein:"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭️ Skip Demo", callback_data="pm_skip_demo", style="primary")],
        [InlineKeyboardButton("🔙 Back", callback_data="pm_add", style="primary")],
    ])
    await safe_edit(query, text, markup)


async def pm_skip_demo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    context.user_data["pm_demo_link"] = ""
    context.user_data["pm_stage"] = "confirm"

    await _show_confirm_callback(query, context)


# ============================================================
# CONFIRM & SAVE
# ============================================================

async def _show_confirm(update, context):
    await _show_confirm_inner(update=update, context=context, query=None)


async def _show_confirm_callback(query, context):
    await _show_confirm_inner(update=None, context=context, query=query)


async def _show_confirm_inner(update=None, context=None, query=None):
    name = context.user_data.get("pm_name", "?")
    feats = context.user_data.get("pm_features", [])
    prices = context.user_data.get("pm_prices", [])
    demo = context.user_data.get("pm_demo_link", "")

    lines = [
        "➕ <b>CONFIRM & SAVE</b>",
        "━━━━━━━━━━━━━━━━━━━",
        "",
        f"📛 <b>Name:</b> {name}",
        "",
        f"📋 <b>Features ({len(feats)}):</b>",
    ]
    for f in feats:
        lines.append(f"🟢 {f}")

    lines.append("")
    lines.append(f"💰 <b>Durations ({len(prices)}):</b>")
    for p in prices:
        lines.append(f"⏱️ {p['duration']} - ₹{p['display_price']:.0f}")

    if demo:
        lines.append("")
        lines.append(f"🎬 <b>Demo:</b> {demo}")

    lines.append("")
    lines.append("👇 Confirm karein?")

    text = "\n".join(lines)
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm & Save", callback_data="pm_save", style="success")],
        [InlineKeyboardButton("❌ Cancel", callback_data="pm_products", style="danger")],
    ])

    if query:
        await safe_edit(query, text, markup)
    elif update:
        await update.effective_chat.send_message(text, parse_mode="HTML", reply_markup=markup)


# ============================================================
# SAVE PRODUCT
# ============================================================

async def pm_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query, "Saving...")
    if not is_admin(query.from_user.id):
        return

    name = context.user_data.get("pm_name")
    feats = context.user_data.get("pm_features", [])
    prices = context.user_data.get("pm_prices", [])
    demo = context.user_data.get("pm_demo_link", "")

    if not name:
        await safe_answer(query, "❌ Name missing", show_alert=True)
        return

    if not prices:
        await safe_answer(query, "❌ Koi duration nahi. Pehle add karein.", show_alert=True)
        return

    try:
        # Naya PID generate karo
        pid = "P" + "".join(random.choices(string.digits, k=6))

        conn = database._conn()
        cur = conn.cursor()

        # Columns check
        cur.execute("PRAGMA table_info(products)")
        cols = [r[1] for r in cur.fetchall()]

        # Insert product
        fields = ["supplier_pid", "name", "display_name", "category", "style", "maintenance"]
        values = [pid, name, name, "CUSTOM", "success", 0]

        if "features" in cols:
            fields.append("features")
            values.append(json.dumps(feats))

        if "demo_link" in cols:
            fields.append("demo_link")
            values.append(demo)

        placeholders = ",".join(["?"] * len(fields))
        cur.execute(
            f"INSERT INTO products ({','.join(fields)}) VALUES ({placeholders})",
            values,
        )
        product_id = cur.lastrowid

        # Insert durations
        for p in prices:
            cur.execute(
                """INSERT INTO durations 
                   (product_id, duration, display_duration, supplier_cost, display_price, reseller_price) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    product_id,
                    p["duration"],
                    p["display_duration"],
                    p["cost"],
                    p["display_price"],
                    p["reseller_price"],
                ),
            )

        conn.commit()
        conn.close()

        # Clear state
        for k in ["pm_name", "pm_features", "pm_prices", "pm_demo_link", "pm_stage"]:
            context.user_data.pop(k, None)

        text = (
            f"✅ <b>PRODUCT ADDED!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 PID: <code>{pid}</code>\n"
            f"📛 Name: <b>{name}</b>\n"
            f"📋 Features: <b>{len(feats)}</b>\n"
            f"💰 Durations: <b>{len(prices)}</b>\n\n"
            f"Ab isko <b>Set User Price</b> aur <b>Set Reseller Price</b> se price set karein."
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Set User Price", callback_data=f"up_menu:{pid}", style="success")],
            [InlineKeyboardButton("👑 Set Reseller Price", callback_data=f"rp_menu:{pid}", style="primary")],
            [InlineKeyboardButton("📋 Products Manage", callback_data="pm_products", style="primary")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="admin_pm", style="primary")],
        ])
        await safe_edit(query, text, markup)

    except Exception as e:
        logger.exception("Save failed")
        await safe_edit(
            query,
            f"❌ Error: <code>{str(e)[:200]}</code>",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="pm_products", style="primary")],
            ]),
        )


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(pm_add_start, pattern=r"^pm_add$"),
        CallbackQueryHandler(pm_add_feature, pattern=r"^pm_add_feature$"),
        CallbackQueryHandler(pm_paste_features, pattern=r"^pm_paste_features$"),
        CallbackQueryHandler(pm_preview_features, pattern=r"^pm_preview_features$"),
        CallbackQueryHandler(pm_next_features, pattern=r"^pm_next_features$"),
        CallbackQueryHandler(pm_add_dur, pattern=r"^pm_add_dur$"),
        CallbackQueryHandler(pm_next_prices, pattern=r"^pm_next_prices$"),
        CallbackQueryHandler(pm_skip_demo, pattern=r"^pm_skip_demo$"),
        CallbackQueryHandler(pm_save, pattern=r"^pm_save$"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, pm_add_message),
    ]
