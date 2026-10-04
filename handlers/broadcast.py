# handlers/broadcast.py
# ============================================================
# ABHAY PANEL STORE - BROADCAST SYSTEM
# Text | Photo | Video | Document + Preview + Progress + Report
# Command: /broadcast | Admin panel se bhi chalega
# ============================================================

from __future__ import annotations

import asyncio
import logging
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
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

ADMIN_ID = 8910147515
STORE_NAME = getattr(config, "STORE_NAME", "ABHAY PANEL STORE")


# ============================================================
# HELPERS
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def get_all_user_ids():
    """Saare users ke telegram_id return karta hai."""
    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("SELECT telegram_id FROM users")
        rows = cur.fetchall()
        conn.close()
        return [r["telegram_id"] for r in rows]
    except Exception:
        logger.exception("get_all_user_ids failed")
        return []


def save_broadcast_log(total, delivered, failed, blocked, duration):
    """Broadcast history save karta hai."""
    try:
        conn = database._conn()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total INTEGER,
                delivered INTEGER,
                failed INTEGER,
                blocked INTEGER,
                duration REAL,
                created_at INTEGER
            )
        """)

        cur.execute(
            """INSERT INTO broadcast_history 
               (total, delivered, failed, blocked, duration, created_at) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (total, delivered, failed, blocked, duration, int(time.time())),
        )
        conn.commit()
        conn.close()
    except Exception:
        logger.exception("save_broadcast_log failed")


async def safe_answer(query, text=None, show_alert=False):
    try:
        if text is not None:
            await query.answer(text, show_alert=show_alert)
        else:
            await query.answer()
    except Exception:
        pass


# ============================================================
# /broadcast COMMAND
# ============================================================

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("❌ You are not authorized.")
        return

    # Reset state
    context.user_data.pop("broadcast_msg", None)
    context.user_data.pop("broadcast_preview", None)
    context.user_data["broadcast_waiting"] = True

    users = get_all_user_ids()

    text = (
        f"📢 <b>BROADCAST</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"Send the message you want to broadcast.\n\n"
        f"<b>Supported:</b>\n"
        f"• Text\n"
        f"• Photo + Caption\n"
        f"• Video + Caption\n"
        f"• Document + Caption\n"
        f"• Telegram formatting\n\n"
        f"👥 Total Users: <b>{len(users)}</b>"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="bcast_cancel", style="danger")],
    ])

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)


# ============================================================
# PANEL (Admin panel button se)
# ============================================================

async def broadcast_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel se Broadcast button click hone pe."""
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    # Delete old
    try:
        await query.message.delete()
    except Exception:
        pass

    # Reset state
    context.user_data.pop("broadcast_msg", None)
    context.user_data.pop("broadcast_preview", None)
    context.user_data["broadcast_waiting"] = True

    users = get_all_user_ids()

    text = (
        f"📢 <b>BROADCAST</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"Send the message you want to broadcast.\n\n"
        f"<b>Supported:</b>\n"
        f"• Text\n"
        f"• Photo + Caption\n"
        f"• Video + Caption\n"
        f"• Document + Caption\n"
        f"• Telegram formatting\n\n"
        f"👥 Total Users: <b>{len(users)}</b>"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="bcast_cancel", style="danger")],
    ])

    try:
        await query.message.chat.send_message(
            text,
            parse_mode="HTML",
            reply_markup=markup,
        )
    except Exception:
        pass


# ============================================================
# RECEIVE MESSAGE (Text / Photo / Video / Document)
# ============================================================

async def broadcast_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("broadcast_waiting"):
        return

    if not is_admin(update.effective_user.id):
        return

    msg = update.message
    if not msg:
        return

    context.user_data.pop("broadcast_waiting", None)

    # Store message info
    bcast = {
        "type": None,
        "text": None,
        "file_id": None,
        "caption": None,
    }

    if msg.photo:
        bcast["type"] = "photo"
        bcast["file_id"] = msg.photo[-1].file_id
        bcast["caption"] = msg.caption or ""
    elif msg.video:
        bcast["type"] = "video"
        bcast["file_id"] = msg.video.file_id
        bcast["caption"] = msg.caption or ""
    elif msg.document:
        bcast["type"] = "document"
        bcast["file_id"] = msg.document.file_id
        bcast["caption"] = msg.caption or ""
    elif msg.text:
        bcast["type"] = "text"
        bcast["text"] = msg.text
    else:
        await msg.reply_text("❌ Unsupported message type.")
        return

    context.user_data["broadcast_msg"] = bcast

    users = get_all_user_ids()
    total = len(users)

    preview_text = f"📢 <b>BROADCAST PREVIEW</b>\n━━━━━━━━━━━━━━━━━━━\n\n"

    if bcast["type"] == "text":
        preview_text += f"<b>Message:</b>\n{bcast['text']}\n\n"
    else:
        preview_text += f"<b>Type:</b> {bcast['type'].title()}\n"
        if bcast["caption"]:
            preview_text += f"<b>Caption:</b>\n{bcast['caption']}\n\n"

    preview_text += f"👥 Recipients: <b>{total} users</b>"

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ SEND BROADCAST", callback_data="bcast_send", style="success")],
        [InlineKeyboardButton("❌ CANCEL", callback_data="bcast_cancel", style="danger")],
    ])

    # Delete user's message
    try:
        await msg.delete()
    except Exception:
        pass

    # Send preview
    try:
        if bcast["type"] == "photo":
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=bcast["file_id"],
                caption=preview_text,
                parse_mode="HTML",
                reply_markup=markup,
            )
        elif bcast["type"] == "video":
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=bcast["file_id"],
                caption=preview_text,
                parse_mode="HTML",
                reply_markup=markup,
            )
        elif bcast["type"] == "document":
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=bcast["file_id"],
                caption=preview_text,
                parse_mode="HTML",
                reply_markup=markup,
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=preview_text,
                parse_mode="HTML",
                reply_markup=markup,
            )
    except Exception:
        logger.exception("Preview send failed")


# ============================================================
# SEND BROADCAST
# ============================================================

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    bcast = context.user_data.get("broadcast_msg")
    if not bcast:
        await safe_answer(query, "No message. Use /broadcast again.", show_alert=True)
        return

    users = get_all_user_ids()
    total = len(users)

    if total == 0:
        await safe_answer(query, "No users to broadcast.", show_alert=True)
        return

    # Delete preview
    try:
        await query.message.delete()
    except Exception:
        pass

    # Show sending status
    status_text = (
        f"📡 <b>BROADCASTING...</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"⏳ Starting..."
    )

    try:
        status_msg = await query.message.chat.send_message(status_text, parse_mode="HTML")
    except Exception:
        status_msg = None

    # Stats
    delivered = 0
    failed = 0
    blocked = 0
    start_time = time.time()

    # Broadcast
    for i, uid in enumerate(users):
        try:
            if bcast["type"] == "text":
                await context.bot.send_message(
                    chat_id=uid,
                    text=bcast["text"],
                    parse_mode=ParseMode.HTML,
                )
            elif bcast["type"] == "photo":
                await context.bot.send_photo(
                    chat_id=uid,
                    photo=bcast["file_id"],
                    caption=bcast["caption"],
                    parse_mode=ParseMode.HTML,
                )
            elif bcast["type"] == "video":
                await context.bot.send_video(
                    chat_id=uid,
                    video=bcast["file_id"],
                    caption=bcast["caption"],
                    parse_mode=ParseMode.HTML,
                )
            elif bcast["type"] == "document":
                await context.bot.send_document(
                    chat_id=uid,
                    document=bcast["file_id"],
                    caption=bcast["caption"],
                    parse_mode=ParseMode.HTML,
                )
            delivered += 1
        except Exception as e:
            err = str(e).lower()
            if "blocked" in err or "chat not found" in err or "user is deactivated" in err:
                blocked += 1
            else:
                failed += 1

        # Update progress every 25 users
        if (i + 1) % 25 == 0 or (i + 1) == total:
            progress = ((i + 1) / total) * 100
            try:
                if status_msg:
                    await status_msg.edit_text(
                        f"📡 <b>BROADCASTING...</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"✅ Sent: <b>{delivered}</b>\n"
                        f"❌ Failed: <b>{failed}</b>\n"
                        f"🚫 Blocked: <b>{blocked}</b>\n\n"
                        f"Progress: <b>{progress:.1f}%</b>",
                        parse_mode="HTML",
                    )
            except Exception:
                pass

        # Small delay to avoid flood
        await asyncio.sleep(0.05)

    elapsed = time.time() - start_time

    # Final report
    final_text = (
        f"📊 <b>BROADCAST COMPLETED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Total: <b>{total}</b>\n"
        f"✅ Delivered: <b>{delivered}</b>\n"
        f"❌ Failed: <b>{failed}</b>\n"
        f"🚫 Blocked: <b>{blocked}</b>\n\n"
        f"⏱ Time: <b>{elapsed:.2f}s</b>"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 New Broadcast", callback_data="admin_broadcast", style="success")],
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
    ])

    try:
        if status_msg:
            await status_msg.edit_text(final_text, parse_mode="HTML", reply_markup=markup)
    except Exception:
        pass

    # Save log
    save_broadcast_log(total, delivered, failed, blocked, elapsed)

    # Cleanup
    context.user_data.pop("broadcast_msg", None)


# ============================================================
# CANCEL
# ============================================================

async def broadcast_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    context.user_data.pop("broadcast_msg", None)
    context.user_data.pop("broadcast_waiting", None)

    try:
        await query.message.delete()
    except Exception:
        pass

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Broadcast Panel", callback_data="admin_broadcast", style="success")],
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
    ])

    try:
        await query.message.chat.send_message(
            "❌ <b>Broadcast cancelled.</b>",
            parse_mode="HTML",
            reply_markup=markup,
        )
    except Exception:
        pass


# ============================================================
# BROADCAST HISTORY
# ============================================================

async def broadcast_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if not is_admin(query.from_user.id):
        return

    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total INTEGER,
                delivered INTEGER,
                failed INTEGER,
                blocked INTEGER,
                duration REAL,
                created_at INTEGER
            )
        """)
        cur.execute("SELECT * FROM broadcast_history ORDER BY id DESC LIMIT 10")
        rows = cur.fetchall()
        conn.close()
    except Exception:
        rows = []

    if not rows:
        text = "📊 <b>BROADCAST HISTORY</b>\n\nAbhi koi broadcast nahi hua."
    else:
        lines = ["📊 <b>BROADCAST HISTORY</b>", "━━━━━━━━━━━━━━━━━━━", ""]
        for r in rows:
            r = dict(r)
            date = time.strftime("%d %b %Y", time.localtime(r["created_at"]))
            lines.append(
                f"📅 {date}\n"
                f"✅ {r['delivered']} / 👥 {r['total']}\n"
                f"❌ {r['failed']}  🚫 {r['blocked']}\n"
                f"⏱ {r['duration']:.1f}s\n"
                f"━━━━━━━━━━━━━━━━━━━"
            )
        text = "\n".join(lines)

    # Delete old
    try:
        await query.message.delete()
    except Exception:
        pass

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 New Broadcast", callback_data="admin_broadcast", style="success")],
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
    ])

    try:
        await query.message.chat.send_message(text, parse_mode="HTML", reply_markup=markup)
    except Exception:
        pass


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CommandHandler("broadcast", broadcast_command),
        CallbackQueryHandler(broadcast_send, pattern=r"^bcast_send$"),
        CallbackQueryHandler(broadcast_cancel, pattern=r"^bcast_cancel$"),
        CallbackQueryHandler(broadcast_history, pattern=r"^bcast_history$"),
        MessageHandler(
            (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL)
            & ~filters.COMMAND,
            broadcast_receive,
        ),
    ]
