# handlers/admin_panel/products.py
# ============================================================
# ADMIN PANEL - PRODUCTS (View + Toggle + Add)
# Single-message editing architecture
# ============================================================

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

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
# PRODUCTS LIST
# ============================================================

async def admin_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    products = database.get_products()

    buttons = []

    if not products:
        buttons.append([
            InlineKeyboardButton("📝 No products yet", callback_data="noop", style="primary")
        ])
    else:
        for p in products:
            pid = p.get("supplier_pid")
            name = p.get("display_name") or p.get("name") or "?"
            maint = p.get("maintenance", 0)
            emoji = "🔴" if maint else "🟢"
            buttons.append([
                InlineKeyboardButton(
                    f"{emoji} {name}",
                    callback_data=f"admin_prod_view:{pid}",
                    style="danger" if maint else "success",
                )
            ])

    # Add Product button
    buttons.append([
        InlineKeyboardButton("➕ Add New Product", callback_data="admin_prod_add", style="success")
    ])

    buttons.append([
        InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")
    ])

    text = f"🛍 <b>PRODUCTS</b> ({len(products)})\n\nSelect a product or add new:"
    await safe_edit(query, text, InlineKeyboardMarkup(buttons))


# ============================================================
# PRODUCT VIEW
# ============================================================

async def admin_prod_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    category = product.get("category") or "-"
    maint = product.get("maintenance", 0)
    durations = product.get("durations", [])

    lines = [
        f"🛍 <b>{name}</b>",
        f"━━━━━━━━━━━━━━━━━━━",
        f"🆔 PID: <code>{pid}</code>",
        f"📁 Category: {category}",
        f"🔧 Maintenance: {'🔴 Yes' if maint else '🟢 No'}",
        f"━━━━━━━━━━━━━━━━━━━",
        f"<b>📊 Durations ({len(durations)}):</b>",
        "",
    ]

    for i, d in enumerate(durations, 1):
        dn = d.get("display_duration") or d.get("duration")
        cost = d.get("supplier_cost") or 0
        price = d.get("display_price") or 0
        rp = d.get("reseller_price") or 0

        lines.append(f"<b>{i}. {dn}</b>")
        lines.append(f"   💰 Cost: {fmt_money(cost)}")
        lines.append(f"   🛒 User: {fmt_money(price)}")
        lines.append(f"   👑 Reseller: {fmt_money(rp)}")
        lines.append("")

    text = "\n".join(lines)

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛒 Set User Price", callback_data=f"up_menu:{pid}", style="success"),
            InlineKeyboardButton("👑 Set Reseller Price", callback_data=f"rp_menu:{pid}", style="primary"),
        ],
        [
            InlineKeyboardButton("✏️ Edit Details", callback_data=f"pd_menu:{pid}", style="primary"),
        ],
        [
            InlineKeyboardButton("🔧 Toggle Maintenance", callback_data=f"admin_prod_toggle:{pid}", style="danger"),
        ],
        [
            InlineKeyboardButton("‹ Products", callback_data="admin_products", style="primary"),
        ],
    ])

    await safe_edit(query, text, markup)


# ============================================================
# TOGGLE MAINTENANCE
# ============================================================

async def admin_prod_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    pid = query.data.split(":", 1)[1]
    product = database.get_product(pid)
    if not product:
        await safe_answer(query, "Not found", show_alert=True)
        return

    new_val = 0 if product.get("maintenance") else 1

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("UPDATE products SET maintenance = ? WHERE supplier_pid = ?", (new_val, str(pid)))
        conn.commit()
        conn.close()
        await safe_answer(query, f"Maintenance {'ON 🔴' if new_val else 'OFF 🟢'}", show_alert=True)
    except Exception as e:
        await safe_answer(query, f"Error: {str(e)[:100]}", show_alert=True)
        return

    # Same message edit — refresh product view
    query.data = f"admin_prod_view:{pid}"
    await admin_prod_view(update, context)


# ============================================================
# ADD PRODUCT — Connector
# ============================================================

async def admin_prod_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    try:
        from handlers.admin_panel.products_add import start_add_product
        await start_add_product(update, context)
    except Exception as e:
        logger.exception("Add product failed")
        await safe_answer(query, f"❌ Error: {str(e)[:100]}", show_alert=True)


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(admin_products, pattern=r"^admin_products$"),
        CallbackQueryHandler(admin_prod_view, pattern=r"^admin_prod_view:"),
        CallbackQueryHandler(admin_prod_toggle, pattern=r"^admin_prod_toggle:"),
        CallbackQueryHandler(admin_prod_add, pattern=r"^admin_prod_add$"),
    ]
