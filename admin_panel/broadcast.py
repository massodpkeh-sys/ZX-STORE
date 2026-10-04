# handlers/admin_panel/broadcast.py
# ============================================================
# ADMIN PANEL - BROADCAST
# Single-message editing architecture + 4 type buttons
# ============================================================

from __future__ import annotations

import asyncio
import logging
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler, ContextTypes, MessageHandler, filters,
)

import database
from handlers.admin_panel.menu import is_admin, safe_answer, safe_edit

logger = logging.getLogger(__name__)


def get_all_ids():
    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("SELECT telegram_id FROM users")
        rows = cur.fetchall()
        conn.close()
        return [r["telegram_id"] for r in rows]
    except Exception:
        return []


def save_log(total, delivered, failed, blocked, duration):
    try:
        conn = database._conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total INTEGER, delivered INTEGER, failed INTEGER,
                blocked INTEGER, duration REAL, created_at INTEGER
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
        logger.exception("save_log failed")


# ============================================================
# PANEL
# ============================================================

async def admin_broadcast_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    context.user_data.pop("broadcast_msg", None)
    context.user_data.pop("broadcast_waiting", None)
    context.user_data.pop("broadcast_type", None)

    users = get_all_ids()
    total = len(users)

    text = (
        f"📢 <b>BROADCAST</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Total Users: <b>{total}</b>\n\n"
        f"👇 <b>Broadcast type select karein:</b>"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Text Broadcast", callback_data="bcast_type:text", style="success")],
        [InlineKeyboardButton("📷 Photo + Caption", callback_data="bcast_type:photo", style="primary")],
        [InlineKeyboardButton("🎬 Video + Caption", callback_data="bcast_type:video", style="primary")],
        [InlineKeyboardButton("📄 Document + Caption", callback_data="bcast_type:document", style="primary")],
        [InlineKeyboardButton("📊 History", callback_data="bcast_history", style="primary")],
        [InlineKeyboardButton("❌ Close", callback_data="admin_home", style="danger")],
    ])

    await safe_edit(query, text, markup)


# ============================================================
# TYPE SELECTION
# ============================================================

async def bcast_type_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if not is_admin(query.from_user.id):
        return

    try:
        btype = query.data.split(":", 1)[1]
    except Exception:
        await safe_answer(query, "Invalid.", show_alert=True)
        return

    context.user_data["broadcast_type"] = btype
    context.user_data["broadcast_waiting"] = True

    users = get_all_ids()
    total = len(users)

    titles = {
        "text": "📝 <b>TEXT BROADCAST</b>",
        "photo": "📷 <b>PHOTO + CAPTION</b>",
        "video": "🎬 <b>VIDEO + CAPTION</b>",
        "document": "📄 <b>DOCUMENT + CAPTION</b>",
    }

    details = {
        "text": "Ek text message bhejenge.",
        "photo": "Ek photo + caption bhejenge.",
        "video": "Ek video + caption bhejenge.",
        "document": "Ek document + caption bhejenge.",
    }

    text = (
        f"{titles.get(btype, '')}\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"{details.get(btype, '')}\n\n"
        f"👥 Recipients: <b>{total}</b>\n\n"
        f"👇 <b>Ab message bhejein:</b>"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_broadcast", style="danger")],
    ])

    await safe_edit(query, text, markup)


# ============================================================
# RECEIVE MESSAGE
# ============================================================

async def broadcast_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("broadcast_waiting"):
        return
    if not is_admin(update.effective_user.id):
        return
    if not update.message:
        return

    msg = update.message
    btype = context.user_data.get("broadcast_type", "text")

    # Validate
    if btype == "text" and not msg.text:
        await msg.reply_text("❌ Sirf text bhejein.")
        return
    if btype == "photo" and not msg.photo:
        await msg.reply_text("❌ Sirf photo + caption bhejein.")
        return
    if btype == "video" and not msg.video:
        await msg.reply_text("❌ Sirf video + caption bhejein.")
        return
    if btype == "document" and not msg.document:
        await msg.reply_text("❌ Sirf document + caption bhejein.")
        return

    context.user_data.pop("broadcast_waiting", None)

    bcast = {"type": None, "text": None, "file_id": None, "caption": None}

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

    context.user_data["broadcast_msg"] = bcast

    # Delete user's message
    try:
        await msg.delete()
    except Exception:
        pass

    users = get_all_ids()
    total = len(users)

    preview = f"📢 <b>BROADCAST PREVIEW</b>\n━━━━━━━━━━━━━━━━━━━\n\n"

    if bcast["type"] == "text":
        preview += f"<b>Message:</b>\n{bcast['text']}\n\n"
    else:
        preview += f"<b>Type:</b> {bcast['type'].title()}\n"
        if bcast["caption"]:
            preview += f"<b>Caption:</b>\n{bcast['caption']}\n\n"

    preview += f"👥 Recipients: <b>{total}</b>"

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ SEND", callback_data="bcast_send", style="success")],
        [InlineKeyboardButton("❌ CANCEL", callback_data="bcast_cancel", style="danger")],
    ])

    try:
        if bcast["type"] == "photo":
            await context.bot.send_photo(chat_id=msg.chat.id, photo=bcast["file_id"],
                                          caption=preview, parse_mode="HTML", reply_markup=markup)
        elif bcast["type"] == "video":
            await context.bot.send_video(chat_id=msg.chat.id, video=bcast["file_id"],
                                          caption=preview, parse_mode="HTML", reply_markup=markup)
        elif bcast["type"] == "document":
            await context.bot.send_document(chat_id=msg.chat.id, document=bcast["file_id"],
                                             caption=preview, parse_mode="HTML", reply_markup=markup)
        else:
            await context.bot.send_message(chat_id=msg.chat.id, text=preview,
                                            parse_mode="HTML", reply_markup=markup)
    except Exception:
        logger.exception("Preview failed")


# ============================================================
# SEND BROADCAST
# ============================================================

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query, "Sending...")
    if not is_admin(query.from_user.id):
        return

    bcast = context.user_data.get("broadcast_msg")
    if not bcast:
        await safe_answer(query, "No message.", show_alert=True)
        return

    users = get_all_ids()
    total = len(users)

    if total == 0:
        await safe_answer(query, "No users.", show_alert=True)
        return

    # Delete preview
    try:
        await query.message.delete()
    except Exception:
        pass

    try:
        status = await context.bot.send_message(
            chat_id=query.message.chat.id,
            text="📡 <b>BROADCASTING...</b>",
            parse_mode="HTML",
        )
    except Exception:
        status = None

    delivered = failed = blocked = 0
    start = time.time()

    for i, uid in enumerate(users):
        try:
            if bcast["type"] == "text":
                await context.bot.send_message(chat_id=uid, text=bcast["text"], parse_mode=ParseMode.HTML)
            elif bcast["type"] == "photo":
                await context.bot.send_photo(chat_id=uid, photo=bcast["file_id"],
                                              caption=bcast["caption"], parse_mode=ParseMode.HTML)
            elif bcast["type"] == "video":
                await context.bot.send_video(chat_id=uid, video=bcast["file_id"],
                                              caption=bcast["caption"], parse_mode=ParseMode.HTML)
            elif bcast["type"] == "document":
                await context.bot.send_document(chat_id=uid, document=bcast["file_id"],
                                                 caption=bcast["caption"], parse_mode=ParseMode.HTML)
            delivered += 1
        except Exception as e:
            err = str(e).lower()
            if "blocked" in err or "chat not found" in err or "deactivated" in err:
                blocked += 1
            else:
                failed += 1

        if (i + 1) % 25 == 0 or (i + 1) == total:
            progress = ((i + 1) / total) * 100
            try:
                if status:
                    await status.edit_text(
                        f"📡 <b>BROADCASTING...</b>\n"
                        f"✅ {delivered}  ❌ {failed}  🚫 {blocked}\n"
                        f"Progress: {progress:.1f}%",
                        parse_mode="HTML",
                    )
            except Exception:
                pass

        await asyncio.sleep(0.05)

    elapsed = time.time() - start

    final = (
        f"📊 <b>BROADCAST COMPLETED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Total: <b>{total}</b>\n"
        f"✅ Delivered: <b>{delivered}</b>\n"
        f"❌ Failed: <b>{failed}</b>\n"
        f"🚫 Blocked: <b>{blocked}</b>\n\n"
        f"⏱ Time: <b>{elapsed:.2f}s</b>"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 New", callback_data="admin_broadcast", style="success")],
        [InlineKeyboardButton("📊 History", callback_data="bcast_history", style="primary")],
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
    ])

    try:
        if status:
            await status.edit_text(final, parse_mode="HTML", reply_markup=markup)
    except Exception:
        pass

    save_log(total, delivered, failed, blocked, elapsed)
    context.user_data.pop("broadcast_msg", None)


# ============================================================
# CANCEL
# ============================================================

async def broadcast_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    context.user_data.pop("broadcast_msg", None)
    context.user_data.pop("broadcast_waiting", None)
    context.user_data.pop("broadcast_type", None)

    # Same message edit
    text = "❌ <b>Broadcast cancelled.</b>"
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Broadcast Panel", callback_data="admin_broadcast", style="success")],
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
    ])
    await safe_edit(query, text, markup)


# ============================================================
# HISTORY
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
                total INTEGER, delivered INTEGER, failed INTEGER,
                blocked INTEGER, duration REAL, created_at INTEGER
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

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 New", callback_data="admin_broadcast", style="success")],
        [InlineKeyboardButton("‹ Back", callback_data="admin_home", style="primary")],
    ])

    await safe_edit(query, text, markup)


# ============================================================
# HANDLERS
# ============================================================

def get_handlers():
    return [
        CallbackQueryHandler(admin_broadcast_cb, pattern=r"^admin_broadcast$"),
        CallbackQueryHandler(bcast_type_cb, pattern=r"^bcast_type:"),
        CallbackQueryHandler(broadcast_send, pattern=r"^bcast_send$"),
        CallbackQueryHandler(broadcast_cancel, pattern=r"^bcast_cancel$"),
        CallbackQueryHandler(broadcast_history, pattern=r"^bcast_history$"),
        MessageHandler(
            (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL)
            & ~filters.COMMAND,
            broadcast_receive,
        ),
    ]
