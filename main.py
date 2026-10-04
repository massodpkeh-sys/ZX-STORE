# main.py
# ============================================================
# ABHAY PANEL STORE - MAIN BOT (FINAL FIX)
# Single Instance + Maintenance Lockdown + Clean Logs
# ============================================================

import logging
import os
import sys

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    TypeHandler,
)

import config
import database
from handlers import (
    shop, wallet, profile, spin, referral, reseller, settings, support,
)

# ============================================================
# LOGGING (CLEAN)
# ============================================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.WARNING,
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logging.getLogger("telegram.request").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

STORE_NAME = "ABHAY PANEL STORE"
ADMIN_ID = 8910147515
LOCK_FILE = ".jitu_bot.lock"


# ============================================================
# HELPERS
# ============================================================

async def safe_answer(query, text=None, show_alert=False):
    try:
        if text is not None:
            await query.answer(text, show_alert=show_alert)
        else:
            await query.answer()
    except Exception:
        pass


async def safe_edit(query, text, reply_markup=None):
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


def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="main_menu", style="primary")]
    ])


# ============================================================
# MAIN MENU
# ============================================================

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛒 Shop Key", callback_data="shop_home", style="success"),
        ]
        [,
            InlineKeyboardButton("💰 Add Balance", callback_data="wallet_add", style="success"),
            InlineKeyboardButton("👤 My Profile", callback_data="my_profile", style="primary"),
        ],
            InlineKeyboardButton("📜 My Orders", callback_data="my_orders", style="primary"),
            InlineKeyboardButton("▶️ Tutorial watch", callback_data="tutorial", style="primary"),
        ],
        [
            InlineKeyboardButton("👑 Upgrade To Reseller", callback_data="reseller", style="danger"),
        ],
        [
            InlineKeyboardButton("💼 Selling Proof", callback_data="proof", style="primary"),
            InlineKeyboardButton("🎰 Lucky Spin", callback_data="spin", style="danger"),
        ],
        [
            InlineKeyboardButton("🤝 Referral", callback_data="referral", style="danger"),
            InlineKeyboardButton("💬 Support", callback_data="support", style="success"),
        ],
        [
            InlineKeyboardButton("📥 Download App Files", url="https://t.me/paidstor/71", style="primary"),
        ],
    ])


def main_menu_text(user, balance):
    return (
        f"🛒 ─── {STORE_NAME} ─── 🛒\n\n"
        f"👋 Welcome, <b>{user.first_name or 'User'}</b>!\n\n"
        "📈 ─── STORE HIGHLIGHTS ─── 📈\n"
        "┃ 🔑 Premium Game Keys\n"
        "┃ ⚡ Instant Delivery 24/7\n"
        "┃ 🔒 100% Secure Payment\n"
        "┃ 🎁 Referral Rewards\n"
        "┃ 📞 Professional Support\n\n"
        "───────────────────────\n"
        f"👤 User ID: <code>{user.id}</code>\n"
        f"💰 Wallet Balance: <b>₹{balance:.2f}</b>\n"
        "───────────────────────\n\n"
        "🚀 Tap Shop Now to Start!"
    )


# ============================================================
# /start
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Maintenance check (admin ke alawa)
    try:
        if settings.is_maintenance_mode() and user.id != ADMIN_ID:
            await update.message.reply_text(
                "🛠️ <b>BOT UNDER MAINTENANCE</b>\n"
                "━━━━━━━━━━━━━━━━━━━\n\n"
                "Bot is currently under testing/maintenance.\n"
                "Please try again later.\n\n"
                "🕐 We'll be back soon!",
                parse_mode="HTML",
            )
            return
    except Exception:
        pass

    database.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )

    # Referral check
    args = context.args or []
    if args and args[0].startswith("ref_"):
        ref_code = args[0][4:]
        try:
            referrer_id = await referral.apply_referral(user.id, ref_code)
            if referrer_id:
                try:
                    ref_name = user.first_name or "User"
                    count = database.get_referral_count(referrer_id)
                    bal = database.get_referral_balance(referrer_id)
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=(
                            "🎉 <b>New Referral!</b>\n"
                            "━━━━━━━━━━━━━━━━━━━\n\n"
                            f"👤 <b>{ref_name}</b> ne aapki link se join kiya.\n\n"
                            f"💰 Aapko <b>₹0.50</b> mile!\n\n"
                            f"👥 Total Referrals: <b>{count}</b>\n"
                            f"💵 Referral Balance: <b>₹{bal:.2f}</b>"
                        ),
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
        except Exception:
            pass

    balance = database.get_wallet_balance(user.id)

    old_id = context.user_data.get("main_msg_id")
    if old_id:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=old_id,
            )
        except Exception:
            pass

    msg = await update.message.reply_text(
        main_menu_text(user, balance),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )

    context.user_data["main_msg_id"] = msg.message_id


# ============================================================
# MAIN MENU CALLBACK
# ============================================================

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    user = query.from_user
    balance = database.get_wallet_balance(user.id)

    await safe_edit(query, main_menu_text(user, balance), main_menu_keyboard())


# ============================================================
# TUTORIAL
# ============================================================

async def tutorial(update, context):
    query = update.callback_query
    await safe_answer(query)

    text = (
        "🎬 <b>HOW TO USE BOT</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "1️⃣ /start karke menu kholo\n"
        "2️⃣ Shop me jaake product chuno\n"
        "3️⃣ Add Balance karke fund badao\n"
        "4️⃣ Product kharido, key milegi\n"
        "5️⃣ Video tutorial dekho\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ Koi problem?\n"
        "👤 Support: @H4X_JOD_ABHAY\n"
        "🔥 Fast Reply • 24x7"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Watch Tutorial", url="https://t.me/paidstor/71", style="success")],
        [InlineKeyboardButton("Back", callback_data="main_menu", style="primary")],
    ])
    await safe_edit(query, text, markup)


# ============================================================
# PROOF
# ============================================================

async def proof(update, context):
    query = update.callback_query
    await safe_answer(query)

    text = (
        "💼 <b>SELLING PROOF</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "🔥 Trusted by 1000+ Customers\n"
        "✅ 100% Genuine Keys\n"
        "⚡ Instant Delivery\n\n"
        "📸 Proof channel check karein:"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 View Proof", url="https://t.me/paidstor", style="success")],
        [InlineKeyboardButton("Back", callback_data="main_menu", style="primary")],
    ])
    await safe_edit(query, text, markup)


# ============================================================
# SINGLE INSTANCE LOCK
# ============================================================

def check_lock():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                old_pid = int(f.read().strip())

            try:
                os.kill(old_pid, 0)
                print(f"⚠️  Bot already running (PID {old_pid}).")
                print(f"⚠️  Band karo: pkill -9 -f 'python main.py'")
                print(f"⚠️  Ya lock delete karo: rm -f {LOCK_FILE}")
                sys.exit(1)
            except OSError:
                os.remove(LOCK_FILE)
        except Exception:
            try:
                os.remove(LOCK_FILE)
            except Exception:
                pass

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))


def remove_lock():
    try:
        os.remove(LOCK_FILE)
    except Exception:
        pass


# ============================================================
# MAINTENANCE GUARD — GLOBAL LOCKDOWN
# ============================================================

def register_maintenance_guard(app):
    """Har update se PEHLE ye function chalega."""
    logger.info("🛡️ Registering Maintenance Guard...")

    async def maintenance_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user

        # Admin ko chhodo
        if user and user.id == ADMIN_ID:
            return

        # Maintenance check
        try:
            is_maint = settings.is_maintenance_mode()
        except Exception as e:
            logger.error("Maintenance check failed: %s", e)
            return

        if not is_maint:
            return

        # User ko block karo
        logger.info("🛡️ Blocking user %s (maintenance ON)", user.id if user else "?")

        try:
            if update.message:
                await update.message.reply_text(
                    "🛠️ <b>BOT UNDER MAINTENANCE</b>\n"
                    "━━━━━━━━━━━━━━━━━━━\n\n"
                    "Bot is currently under testing/maintenance.\n"
                    "Please try again later.\n\n"
                    "🕐 We'll be back soon!",
                    parse_mode="HTML",
                )
            elif update.callback_query:
                await update.callback_query.answer(
                    "🛠️ Bot under maintenance. Please try later.",
                    show_alert=True,
                )
        except Exception as e:
            logger.error("Maintenance block failed: %s", e)

    app.add_handler(TypeHandler(Update, maintenance_guard), group=-1)
    logger.info("✅ Maintenance Guard registered (group -1)")


# ============================================================
# MAIN
# ============================================================

def main():
    # Lock check
    check_lock()

    # Database init
    database.init_db()

    # Seed products
    try:
        from product import seed
        seed()
    except Exception as e:
        logger.warning("Seeding skipped: %s", e)

    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ BOT_TOKEN config.py me daalein.")
        remove_lock()
        return

    # Application build
    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .get_updates_connect_timeout(30)
        .get_updates_read_timeout(30)
        .build()
    )

    # ============================================================
    # MAINTENANCE GUARD (sabse pehle register — group -1)
    # ============================================================
    register_maintenance_guard(app)

    # ============================================================
    # MAIN HANDLERS
    # ============================================================
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern=r"^main_menu$"))
    app.add_handler(CallbackQueryHandler(tutorial, pattern=r"^tutorial$"))
    app.add_handler(CallbackQueryHandler(proof, pattern=r"^proof$"))

    # ============================================================
    # USER MODULES
    # ============================================================
    for h in shop.get_handlers():
        app.add_handler(h)
    for h in wallet.get_handlers():
        app.add_handler(h)
    for h in profile.get_handlers():
        app.add_handler(h)
    for h in spin.get_handlers():
        app.add_handler(h)
    for h in referral.get_handlers():
        app.add_handler(h)
    for h in reseller.get_handlers():
        app.add_handler(h)
    for h in settings.get_handlers():
        app.add_handler(h)
    for h in support.get_handlers():
        app.add_handler(h)

    # Admin reply command
    try:
        from handlers.support import reply_command
        app.add_handler(CommandHandler("reply", reply_command))
    except Exception:
        pass

    # ============================================================
    # ADMIN PANEL
    # ============================================================
    try:
        from handlers.admin_panel import menu as admin_menu
        for h in admin_menu.get_handlers():
            app.add_handler(h)
    except Exception as e:
        logger.warning("admin_panel load failed: %s", e)

    # ============================================================
    # ERROR HANDLER
    # ============================================================
    async def error_handler(update, context):
        err = str(context.error)
        if "Conflict" in err:
            logger.warning("⚠️ Conflict — koi purana bot chal raha hai.")
            return
        logger.error("Exception: %s", context.error)

    app.add_error_handler(error_handler)

    # ============================================================
    # STARTUP MESSAGE
    # ============================================================
    print()
    print("╔══════════════════════════════════════════╗")
    print("║                                          ║")
    print("║      🤖  BOT STARTED  ✅                 ║")
    print("║                                          ║")
    print("║      🏪  ABHAY PANEL STORE               ║")
    print("║                                          ║")
    print(f"║      🆔  PID: {os.getpid():<26}║")
    print("║                                          ║")
    print("║      📱  Status: ONLINE                  ║")
    print("║                                          ║")
    print("╚══════════════════════════════════════════╝")
    print()

    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        remove_lock()


if __name__ == "__main__":
    main()
