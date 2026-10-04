# handlers/admin.py
# ============================================================
# ABHAY PANEL STORE - ADMIN PANEL
# ============================================================
# 
# SECTION INDEX:
#   1. Imports & Config
#   2. Helper Functions
#   3. Admin Main Menu
#   4. Entry Command (/vandna_abhay)
#   5. Dashboard
#   6. Statistics
#   7. Products (View / Toggle / Edit Price)
#   8. Orders
#   9. Users (List / Search / Balance)
#  10. Wallet Summary
#  11. Manage Reseller
#  12. Broadcast Connector
#  13. Other Connectors (Settings/Coupons/Payments/Roles)
#  14. Close
#  15. Handler Registration
# ============================================================

from __future__ import annotations

import logging
import time
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
import database

logger = logging.getLogger(__name__)


# ============================================================
# 1. CONFIG
# ============================================================

ADMIN_ID = 8910147515
STORE_NAME = getattr(config, "STORE_NAME", "ABHAY PANEL STORE")


# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================

def is_admin(user_id: int) -> bool:
    """Check karta hai user admin hai ya nahi."""
    return user_id == ADMIN_ID


def fmt_money(value) -> str:
    """Amount ko ₹ format me dikhata hai."""
    try:
        amount = float(value)
        if amount == int(amount):
            return f"₹{int(amount)}"
        return f"₹{amount:.2f}"
    except Exception:
        return "₹0"


def fmt_date(ts) -> str:
    """Timestamp ko readable date me convert karta hai."""
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%d %b %Y | %I:%M %p")
    except Exception:
        return "—"


async def safe_answer(query, text=None, show_alert=False):
    """query.answer() ko safe tarike se call karta hai."""
    try:
        if text is not None:
            await query.answer(text, show_alert=show_alert)
        else:
            await query.answer()
    except Exception:
        pass


async def safe_edit(query, text, reply_markup=None):
    """Message edit karta hai, fail hone par naya bhejta hai."""
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
                disable_web_page_preview=True,
            )
        except Exception:
            pass


def back_to_admin():
    """Back button (admin home)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")]
    ])


# ============================================================
# 3. ADMIN MAIN MENU
# ============================================================

def admin_main_keyboard():
    """Admin panel ka main menu."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Dashboard", callback_data="admin_dashboard", style="success"),
            InlineKeyboardButton("📈 Statistics", callback_data="admin_stats", style="success"),
        ],
        [
            InlineKeyboardButton("🛍 Products", callback_data="admin_products", style="primary"),
            InlineKeyboardButton("📦 Orders", callback_data="admin_orders", style="primary"),
        ],
        [
            InlineKeyboardButton("👥 Users", callback_data="admin_users", style="primary"),
            InlineKeyboardButton("💰 Wallet", callback_data="admin_wallet", style="primary"),
        ],
        [
            InlineKeyboardButton("💳 Payments", callback_data="admin_payments", style="primary"),
            InlineKeyboardButton("👑 Manage Reseller", callback_data="admin_reseller_manage", style="primary"),
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast", style="danger"),
            InlineKeyboardButton("🎟 Coupons", callback_data="admin_coupons", style="danger"),
        ],
        [
            InlineKeyboardButton("👑 Roles", callback_data="admin_roles", style="danger"),
            InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings", style="primary"),
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data="admin_close", style="danger"),
        ],
    ])


# ============================================================
# 4. ENTRY COMMAND
# ============================================================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/vandna_abhay command ka handler."""
    user = update.effective_user

    if not is_admin(user.id):
        logger.warning("Unauthorized admin access: %s", user.id)
        await update.message.reply_text("❌ You are not authorized.")
        return

    text = (
        f"🔐 <b>ADMIN PANEL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👑 Welcome, Admin\n"
        f"🏪 {STORE_NAME}\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"Kya karna chahte hain?"
    )

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=admin_main_keyboard())


async def admin_home_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin home (back button se)."""
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    text = (
        f"🔐 <b>ADMIN PANEL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👑 Welcome, Admin\n"
        f"🏪 {STORE_NAME}\n"
        f"🆔 ID: <code>{query.from_user.id}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"Kya karna chahte hain?"
    )

    await safe_edit(query, text, admin_main_keyboard())


# ============================================================
# 5. DASHBOARD
# ============================================================

async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dashboard - total stats."""
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    try:
        conn = database._conn()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) as c FROM users")
        total_users = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM orders")
        total_orders = cur.fetchone()["c"]

        cur.execute("SELECT COALESCE(SUM(price), 0) as s FROM orders")
        total_revenue = cur.fetchone()["s"] or 0

        cur.execute("SELECT COALESCE(SUM(amount), 0) as s FROM deposits WHERE status = 'paid'")
        total_deposits = cur.fetchone()["s"] or 0

        cur.execute("SELECT COUNT(*) as c FROM products")
        total_products = cur.fetchone()["c"]

        conn.close()
    except Exception:
        logger.exception("Dashboard failed")
        return

    text = (
        f"📊 <b>DASHBOARD</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users: <b>{total_users}</b>\n"
        f"📦 Total Orders: <b>{total_orders}</b>\n"
        f"🛍 Total Products: <b>{total_products}</b>\n"
        f"💰 Total Revenue: <b>{fmt_money(total_revenue)}</b>\n"
        f"💵 Total Deposits: <b>{fmt_money(total_deposits)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )

    await safe_edit(query, text, back_to_admin())


# ============================================================
# 6. STATISTICS
# ============================================================

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Statistics - today/week."""
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    try:
        conn = database._conn()
        cur = conn.cursor()
        now = int(time.time())
        day_ago = now - 86400
        week_ago = now - 604800

        cur.execute("SELECT COUNT(*) as c FROM orders WHERE created_at >= ?", (day_ago,))
        today_orders = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM orders WHERE created_at >= ?", (week_ago,))
        week_orders = cur.fetchone()["c"]

        cur.execute("SELECT COALESCE(SUM(price), 0) as s FROM orders WHERE created_at >= ?", (day_ago,))
        today_rev = cur.fetchone()["s"] or 0

        cur.execute("SELECT COALESCE(SUM(price), 0) as s FROM orders WHERE created_at >= ?", (week_ago,))
        week_rev = cur.fetchone()["s"] or 0

        cur.execute("SELECT COUNT(*) as c FROM users WHERE created_at >= ?", (day_ago,))
        today_users = cur.fetchone()["c"]

        conn.close()
    except Exception:
        logger.exception("Stats failed")
        return

    text = (
        f"📈 <b>STATISTICS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<b>📅 Today</b>\n"
        f"👥 New Users: <b>{today_users}</b>\n"
        f"📦 Orders: <b>{today_orders}</b>\n"
        f"💰 Revenue: <b>{fmt_money(today_rev)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<b>📅 This Week</b>\n"
        f"📦 Orders: <b>{week_orders}</b>\n"
        f"💰 Revenue: <b>{fmt_money(week_rev)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )

    await safe_edit(query, text, back_to_admin())


# ============================================================
# 7. PRODUCTS
# ============================================================

async def admin_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Products list."""
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    products = database.get_products()

    if not products:
        text = "🛍 <b>PRODUCTS</b>\n\nKoi product nahi hai."
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
        ])
        await safe_edit(query, text, markup)
        return

    buttons = []
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

    buttons.append([
        InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary"),
    ])

    text = f"🛍 <b>PRODUCTS</b> ({len(products)})"
    await safe_edit(query, text, InlineKeyboardMarkup(buttons))


async def admin_prod_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Single product details."""
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
        f"🔧 Maintenance: {'Yes' if maint else 'No'}",
        f"━━━━━━━━━━━━━━━━━━━",
        f"<b>Durations:</b>",
    ]

    for d in durations:
        dn = d.get("display_duration") or d.get("duration")
        cost = d.get("supplier_cost") or 0
        price = d.get("display_price") or 0
        rp = d.get("reseller_price") or 0
        lines.append(f"• {dn}: C{fmt_money(cost)} → S{fmt_money(price)} → R{fmt_money(rp)}")

    text = "\n".join(lines)

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Edit Price", callback_data=f"admin_prod_price:{pid}", style="primary"),
            InlineKeyboardButton("🔧 Toggle", callback_data=f"admin_prod_toggle:{pid}", style="primary"),
        ],
        [
            InlineKeyboardButton("‹ Products", callback_data="admin_products", style="primary"),
        ],
    ])

    await safe_edit(query, text, markup)


async def admin_prod_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Product maintenance ON/OFF."""
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
        cur.execute(
            "UPDATE products SET maintenance = ? WHERE supplier_pid = ?",
            (new_val, str(pid)),
        )
        conn.commit()
        conn.close()
        await safe_answer(query, f"Maintenance {'ON' if new_val else 'OFF'}", show_alert=True)
    except Exception:
        logger.exception("Toggle failed")


async def admin_prod_price_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Price edit start."""
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    try:
        pid = query.data.split(":", 1)[1]
    except Exception:
        return

    product = database.get_product(pid)
    if not product:
        await safe_answer(query, "Product not found.", show_alert=True)
        return

    context.user_data["admin_price_pid"] = pid

    name = product.get("display_name") or product.get("name")
    durations = product.get("durations", [])

    lines = [f"💰 <b>EDIT PRICE</b>", f"━━━━━━━━━━━━━━━━━━━", f"📦 {name}", ""]
    for i, d in enumerate(durations):
        dn = d.get("display_duration") or d.get("duration")
        price = d.get("display_price") or 0
        rp = d.get("reseller_price") or 0
        lines.append(f"{i+1}. {dn} — S: {fmt_money(price)} | R: {fmt_money(rp)}")

    lines.append("")
    lines.append("Format: <code>NUMBER NEW_PRICE NEW_RESELLER_PRICE</code>")
    lines.append("Example: <code>1 149 99</code>")

    text = "\n".join(lines)

    await safe_edit(query, text, back_to_admin())


async def admin_price_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Price update message handler."""
    pid = context.user_data.get("admin_price_pid")
    if not pid:
        return
    if not is_admin(update.effective_user.id):
        return

    parts = update.message.text.strip().split()

    if len(parts) == 2:
        try:
            index = int(parts[0]) - 1
            new_price = float(parts[1])
        except Exception:
            await update.message.reply_text("❌ Invalid.")
            return
        new_rp = None
    elif len(parts) == 3:
        try:
            index = int(parts[0]) - 1
            new_price = float(parts[1])
            new_rp = float(parts[2])
        except Exception:
            await update.message.reply_text("❌ Invalid.")
            return
    else:
        await update.message.reply_text(
            "❌ Format: <code>1 149 99</code>",
            parse_mode="HTML",
        )
        return

    product = database.get_product(pid)
    if not product:
        await update.message.reply_text("❌ Product not found.")
        return

    durations = product.get("durations", [])
    if index < 0 or index >= len(durations):
        await update.message.reply_text("❌ Invalid number.")
        return

    target_dur = durations[index]
    dur_name = target_dur.get("duration")

    try:
        conn = database._conn()
        cur = conn.cursor()
        if new_rp is not None:
            cur.execute(
                """UPDATE durations 
                   SET display_price = ?, reseller_price = ?
                   WHERE product_id = (SELECT id FROM products WHERE supplier_pid = ?)
                     AND duration = ?""",
                (new_price, new_rp, str(pid), dur_name),
            )
        else:
            cur.execute(
                """UPDATE durations 
                   SET display_price = ?
                   WHERE product_id = (SELECT id FROM products WHERE supplier_pid = ?)
                     AND duration = ?""",
                (new_price, str(pid), dur_name),
            )
        conn.commit()
        conn.close()

        msg = f"✅ {dur_name}: Customer {fmt_money(new_price)}"
        if new_rp is not None:
            msg += f" | Reseller {fmt_money(new_rp)}"

        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception:
        logger.exception("Price update failed")
        await update.message.reply_text("❌ Update failed.")

    context.user_data.pop("admin_price_pid", None)


# ============================================================
# 8. ORDERS
# ============================================================

async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recent orders list."""
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 20")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception:
        rows = []

    if not rows:
        await safe_edit(query, "📦 <b>ORDERS</b>\n\nAbhi koi order nahi hai.", back_to_admin())
        return

    lines = [f"📦 <b>RECENT ORDERS</b> ({len(rows)})", "━━━━━━━━━━━━━━━━━━━", ""]

    for o in rows[:10]:
        oid = o.get("order_ref") or f"#{o['id']}"
        pname = o.get("product_name") or o.get("product_id") or "?"
        price = o.get("price") or 0
        date = fmt_date(o.get("created_at"))
        lines.append(f"🆔 {oid}")
        lines.append(f"📦 {pname}")
        lines.append(f"💰 {fmt_money(price)}  |  📅 {date}")
        lines.append("━━━━━━━━━━━━━━━━━━━")

    await safe_edit(query, "\n".join(lines), back_to_admin())


# ============================================================
# 9. USERS
# ============================================================

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Users list with recent users."""
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM users")
        total = cur.fetchone()["c"]

        cur.execute(
            "SELECT telegram_id, first_name, username, balance FROM users ORDER BY id DESC LIMIT 10"
        )
        recent = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception:
        total = 0
        recent = []

    lines = [
        f"👥 <b>USERS</b>",
        f"━━━━━━━━━━━━━━━━━━━",
        f"Total Users: <b>{total}</b>",
        f"━━━━━━━━━━━━━━━━━━━",
        "",
        "<b>Recent Users:</b>",
    ]

    for u in recent:
        tid = u.get("telegram_id")
        name = u.get("first_name") or "User"
        uname = u.get("username") or ""
        bal = u.get("balance") or 0

        if uname:
            lines.append(f"• <code>{tid}</code>  {name} (@{uname})  ₹{bal:.2f}")
        else:
            lines.append(f"• <code>{tid}</code>  {name}  ₹{bal:.2f}")

    lines.append("")
    lines.append("User manage karne ke liye ID bhejein.")

    text = "\n".join(lines)

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Manage Balance", callback_data="admin_balance", style="success")],
        [InlineKeyboardButton("🔍 Search User", callback_data="admin_user_search", style="primary")],
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
    ])

    await safe_edit(query, text, markup)


async def admin_user_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search user prompt."""
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    context.user_data["admin_search_user"] = True

    text = (
        "🔍 <b>SEARCH USER</b>\n\n"
        "User ka Telegram ID bhejein.\n\n"
        "Example: <code>123456789</code>"
    )

    await safe_edit(query, text, back_to_admin())


async def admin_user_search_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search user by ID."""
    if not context.user_data.get("admin_search_user"):
        return
    if not is_admin(update.effective_user.id):
        return

    context.user_data.pop("admin_search_user", None)

    try:
        target_id = int(update.message.text.strip())
    except Exception:
        await update.message.reply_text("❌ Invalid ID.")
        return

    user = database.get_user(target_id)
    if not user:
        await update.message.reply_text(f"❌ User {target_id} not found.")
        return

    balance = user.get("balance") or 0
    ref_balance = user.get("referral_balance") or 0
    uname = user.get("username") or "-"

    text = (
        f"👤 <b>USER FOUND</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <code>{target_id}</code>\n"
        f"👤 Name: {user.get('first_name') or 'User'}\n"
        f"📛 Username: @{uname}\n"
        f"💰 Balance: <b>{fmt_money(balance)}</b>\n"
        f"🎁 Ref Balance: <b>{fmt_money(ref_balance)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Add Balance", callback_data=f"adm_bal_add:{target_id}", style="success"),
            InlineKeyboardButton("➖ Deduct", callback_data=f"adm_bal_ded:{target_id}", style="danger"),
        ],
        [
            InlineKeyboardButton("‹ Back", callback_data="admin_users", style="primary"),
        ],
    ])

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)


# ============================================================
# 10. WALLET
# ============================================================

async def admin_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wallet summary."""
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(balance), 0) as s FROM users")
        total_balance = cur.fetchone()["s"] or 0
        cur.execute("SELECT COALESCE(SUM(referral_balance), 0) as s FROM users")
        total_ref = cur.fetchone()["s"] or 0
        conn.close()
    except Exception:
        total_balance = 0
        total_ref = 0

    text = (
        f"💰 <b>WALLET SUMMARY</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total User Balance: <b>{fmt_money(total_balance)}</b>\n"
        f"🎁 Total Referral: <b>{fmt_money(total_ref)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )

    await safe_edit(query, text, back_to_admin())


# ============================================================
# 11. MANAGE RESELLER
# ============================================================

async def admin_reseller_manage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reseller management menu."""
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    text = (
        f"👑 <b>MANAGE RESELLER</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"Reseller manage karne ke liye option choose karein:"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Make Reseller", callback_data="resel_make", style="success")],
        [InlineKeyboardButton("➖ Remove Reseller", callback_data="resel_remove", style="danger")],
        [InlineKeyboardButton("📋 Reseller List", callback_data="resel_list", style="primary")],
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
    ])

    await safe_edit(query, text, markup)


async def resel_make(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Make reseller prompt."""
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    context.user_data["resel_action"] = "make"

    text = (
        "➕ <b>MAKE RESELLER</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "User ka Telegram ID bhejein.\n\n"
        "Example: <code>123456789</code>\n\n"
        "User ko 30 days ka reseller banaya jayega."
    )

    await safe_edit(query, text, back_to_admin())


async def resel_remove_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove reseller prompt."""
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    context.user_data["resel_action"] = "remove"

    text = (
        "➖ <b>REMOVE RESELLER</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "User ka Telegram ID bhejein.\n\n"
        "Example: <code>123456789</code>"
    )

    await safe_edit(query, text, back_to_admin())


async def resel_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Active resellers list."""
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    rows = []
    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = [r[1] for r in cur.fetchall()]

        if "reseller_expiry" in cols:
            now = int(time.time())
            cur.execute(
                "SELECT telegram_id, first_name, reseller_expiry FROM users WHERE reseller_expiry > ? ORDER BY reseller_expiry DESC",
                (now,),
            )
            rows = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception:
        rows = []

    if not rows:
        await safe_edit(query, "👑 <b>RESELLER LIST</b>\n\nAbhi koi active reseller nahi hai.", back_to_admin())
        return

    lines = [f"👑 <b>ACTIVE RESELLERS</b> ({len(rows)})", "━━━━━━━━━━━━━━━━━━━", ""]

    now = int(time.time())
    for r in rows:
        tid = r["telegram_id"]
        name = r["first_name"] or "User"
        exp = int(r["reseller_expiry"])
        days = max(0, (exp - now) // 86400)
        lines.append(f"• <code>{tid}</code>  {name}  ({days}d left)")

    await safe_edit(query, "\n".join(lines), back_to_admin())


async def resel_action_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle reseller make/remove message."""
    action = context.user_data.get("resel_action")
    if not action:
        return
    if not is_admin(update.effective_user.id):
        return

    context.user_data.pop("resel_action", None)

    try:
        tid = int(update.message.text.strip())
    except Exception:
        await update.message.reply_text("❌ Invalid ID.")
        return

    user = database.get_user(tid)
    if not user:
        await update.message.reply_text(f"❌ User {tid} not found.")
        return

    try:
        conn = database._conn()
        cur = conn.cursor()

        cur.execute("PRAGMA table_info(users)")
        cols = [r[1] for r in cur.fetchall()]
        if "reseller_expiry" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN reseller_expiry INTEGER DEFAULT 0")

        if action == "make":
            expiry = int(time.time()) + (30 * 86400)
            cur.execute("UPDATE users SET reseller_expiry = ? WHERE telegram_id = ?", (expiry, tid))
            msg = f"✅ <code>{tid}</code> is now a Reseller (30 days)"
        else:
            cur.execute("UPDATE users SET reseller_expiry = 0 WHERE telegram_id = ?", (tid,))
            msg = f"✅ <code>{tid}</code> reseller removed."

        conn.commit()
        conn.close()

        await update.message.reply_text(msg, parse_mode="HTML")

        try:
            if action == "make":
                await context.bot.send_message(
                    chat_id=tid,
                    text="🎉 <b>You are now a Reseller!</b>\n\n30 days valid.",
                    parse_mode="HTML",
                )
            else:
                await context.bot.send_message(
                    chat_id=tid,
                    text="ℹ️ Aapka reseller access hata diya gaya hai.",
                )
        except Exception:
            pass

    except Exception:
        logger.exception("Reseller action failed")
        await update.message.reply_text("❌ Failed.")


# ============================================================
# 12. BROADCAST CONNECTOR
# ============================================================

async def admin_broadcast_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast panel."""
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    context.user_data.pop("broadcast_msg", None)
    context.user_data["broadcast_waiting"] = True

    try:
        from handlers.broadcast import get_all_user_ids
        users = get_all_user_ids()
        total = len(users)
    except Exception:
        total = 0

    text = (
        f"📢 <b>BROADCAST</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"Send the message you want to broadcast.\n\n"
        f"<b>Supported:</b>\n"
        f"• Text\n"
        f"• Photo + Caption\n"
        f"• Video + Caption\n"
        f"• Document + Caption\n\n"
        f"👥 Total Users: <b>{total}</b>"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="bcast_cancel", style="danger")],
    ])

    await safe_edit(query, text, markup)


# ============================================================
# 13. OTHER CONNECTORS
# ============================================================

async def admin_reseller_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reseller plans (user side)."""
    from handlers.reseller import reseller_screen
    await reseller_screen(update, context)


async def admin_settings_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Settings panel."""
    from handlers.settings import admin_settings
    await admin_settings(update, context)


async def admin_coupons_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Coupons panel."""
    from handlers.coupons import admin_coupons
    await admin_coupons(update, context)


async def admin_payments_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Payments panel."""
    from handlers.payments import admin_payments
    await admin_payments(update, context)


async def admin_roles_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Roles panel."""
    from handlers.roles import admin_roles
    await admin_roles(update, context)


async def admin_balance_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Balance manage entry."""
    from handlers.admin_actions import admin_balance_entry
    await admin_balance_entry(update, context)


# ============================================================
# 14. CLOSE
# ============================================================

async def admin_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Close admin panel."""
    query = update.callback_query
    await safe_answer(query)
    try:
        await query.edit_message_text("🔐 Admin panel closed.")
    except Exception:
        pass


# ============================================================
# 15. HANDLER REGISTRATION
# ============================================================

def get_handlers():
    """Saare admin handlers return karta hai."""
    return [
        # Entry command
        CommandHandler("vandna_abhay", admin_command),

        # Main panel
        CallbackQueryHandler(admin_home_callback, pattern=r"^admin_home$"),
        CallbackQueryHandler(admin_dashboard, pattern=r"^admin_dashboard$"),
        CallbackQueryHandler(admin_stats, pattern=r"^admin_stats$"),

        # Products
        CallbackQueryHandler(admin_products, pattern=r"^admin_products$"),
        CallbackQueryHandler(admin_prod_view, pattern=r"^admin_prod_view:"),
        CallbackQueryHandler(admin_prod_toggle, pattern=r"^admin_prod_toggle:"),
        CallbackQueryHandler(admin_prod_price_start, pattern=r"^admin_prod_price:"),

        # Orders
        CallbackQueryHandler(admin_orders, pattern=r"^admin_orders$"),

        # Users
        CallbackQueryHandler(admin_users, pattern=r"^admin_users$"),
        CallbackQueryHandler(admin_user_search, pattern=r"^admin_user_search$"),

        # Wallet
        CallbackQueryHandler(admin_wallet, pattern=r"^admin_wallet$"),

        # Manage Reseller
        CallbackQueryHandler(admin_reseller_manage, pattern=r"^admin_reseller_manage$"),
        CallbackQueryHandler(resel_make, pattern=r"^resel_make$"),
        CallbackQueryHandler(resel_remove_cb, pattern=r"^resel_remove$"),
        CallbackQueryHandler(resel_list, pattern=r"^resel_list$"),

        # Connectors
        CallbackQueryHandler(admin_broadcast_cb, pattern=r"^admin_broadcast$"),
        CallbackQueryHandler(admin_reseller_cb, pattern=r"^admin_reseller$"),
        CallbackQueryHandler(admin_settings_cb, pattern=r"^admin_settings$"),
        CallbackQueryHandler(admin_coupons_cb, pattern=r"^admin_coupons$"),
        CallbackQueryHandler(admin_payments_cb, pattern=r"^admin_payments$"),
        CallbackQueryHandler(admin_roles_cb, pattern=r"^admin_roles$"),
        CallbackQueryHandler(admin_balance_cb, pattern=r"^admin_balance$"),

        # Close
        CallbackQueryHandler(admin_close, pattern=r"^admin_close$"),

        # Message handlers
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            resel_action_message,
        ),
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            admin_user_search_message,
        ),
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            admin_price_message,
        ),
    ]
