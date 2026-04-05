"""
Telegram Bot for Ticket System
Handles: Service menus → Company selection → Dynamic forms → Ticket creation → Live chat relay (text + media)
"""

import os
import sys
import hashlib
import logging
import requests
import tempfile

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters, ContextTypes,
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
INTERNAL_KEY = os.getenv("BOT_INTERNAL_KEY", "bot-internal-secret")
BOT_TOKENS = [t.strip() for t in os.getenv("TELEGRAM_BOT_TOKENS", "").split(",") if t.strip()]

SELECT_SERVICE, SELECT_COMPANY, FILL_FORM = range(3)

services_cache = []
user_sessions = {}


# ── Backend API Helpers ───────────────────────────────────────────────────────

def api_get(endpoint):
    try:
        resp = requests.get(f"{BACKEND_URL}/api/{endpoint}", headers={"X-Internal-Key": INTERNAL_KEY}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"API GET {endpoint} failed: {e}")
        return None


def api_post(endpoint, data):
    try:
        resp = requests.post(f"{BACKEND_URL}/api/{endpoint}", json=data, headers={"X-Internal-Key": INTERNAL_KEY}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"API POST {endpoint} failed: {e}")
        return None


def api_post_file(endpoint, data, files):
    """POST with multipart file upload."""
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/{endpoint}",
            data=data,
            files=files,
            headers={"X-Internal-Key": INTERNAL_KEY},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"API POST file {endpoint} failed: {e}")
        return None


def load_services():
    global services_cache
    data = api_get("internal/services/")
    if data:
        services_cache = data
        logger.info(f"Loaded {len(data)} services from backend")
    return services_cache


# ── Command Handlers ──────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    load_services()
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_sessions.pop(chat_id, None)

    welcome = (
        f"👋 Hello {user.first_name}!\n\n"
        "Welcome to our service assistant. I can help you with:\n"
        "✈️ Flights, 🏨 Hotels, 🍔 Food delivery, 🎬 Movies, and more!\n\n"
        "Select a service below to get started:"
    )
    keyboard = build_services_keyboard()
    await update.message.reply_text(welcome, reply_markup=keyboard)
    return SELECT_SERVICE


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔧 Available Commands\n\n"
        "/start — Show service menu\n"
        "/status — Check your active ticket\n"
        "/cancel — Cancel current action\n"
        "/help — Show this message\n\n"
        "Once an agent picks up your ticket, you can chat with them right here!\n"
        "You can also send images, videos, audio, and files."
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.get(chat_id)

    if session and session.get("ticket_number"):
        ticket_status = session.get("ticket_status", "open")
        text = (
            f"🎫 Your Active Ticket\n\n"
            f"Ticket: {session['ticket_number']}\n"
            f"Service: {session.get('service_name', 'N/A')}\n"
            f"Company: {session.get('company_name', 'N/A')}\n"
            f"Status: {ticket_status.replace('_', ' ').title()}\n\n"
        )
        if ticket_status in ("assigned", "in_progress"):
            text += "💬 You're connected with an agent. Send messages here and they'll respond!"
        else:
            text += "⏳ Waiting for an agent to pick up your ticket..."
    else:
        text = "You don't have any active tickets. Use /start to create one!"
    await update.message.reply_text(text)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.get(chat_id)
    if session and session.get("in_live_chat"):
        await update.message.reply_text("You're in a live chat. Your ticket is still active.\nUse /start to create a new ticket.")
        return ConversationHandler.END
    user_sessions.pop(chat_id, None)
    await update.message.reply_text("❌ Cancelled. Use /start to begin again.")
    return ConversationHandler.END


# ── Service Selection ─────────────────────────────────────────────────────────

def build_services_keyboard():
    if not services_cache:
        load_services()
    buttons, row = [], []
    for svc in services_cache:
        row.append(InlineKeyboardButton(f"{svc['icon']} {svc['name']}", callback_data=f"svc:{svc['id']}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


async def service_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    service_id = query.data.split(":")[1]
    service = next((s for s in services_cache if s["id"] == service_id), None)
    if not service:
        await query.edit_message_text("Service not found. Try /start again.")
        return ConversationHandler.END

    chat_id = update.effective_chat.id
    user_sessions[chat_id] = {"service_id": service_id, "service_name": service["name"], "step": "select_company"}

    buttons = [[InlineKeyboardButton(f"{c['icon']} {c['name']}", callback_data=f"comp:{c['id']}")] for c in service.get("companies", [])]
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="back:services")])
    await query.edit_message_text(f"{service['icon']} {service['name']}\n\nSelect a company:", reply_markup=InlineKeyboardMarkup(buttons))
    return SELECT_COMPANY


# ── Company Selection ─────────────────────────────────────────────────────────

async def company_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "back:services":
        await query.edit_message_text("Select a service:", reply_markup=build_services_keyboard())
        return SELECT_SERVICE

    company_id = query.data.split(":")[1]
    chat_id = update.effective_chat.id
    session = user_sessions.get(chat_id, {})

    service = next((s for s in services_cache if s["id"] == session.get("service_id")), None)
    if not service:
        await query.edit_message_text("Session expired. Try /start again.")
        return ConversationHandler.END

    company = next((c for c in service.get("companies", []) if c["id"] == company_id), None)
    if not company:
        await query.edit_message_text("Company not found. Try /start again.")
        return ConversationHandler.END

    session.update({
        "company_id": company_id, "company_name": company["name"],
        "ticket_created_message": company.get("ticket_created_message", ""),
        "form_schema": company.get("form_schema", []),
        "form_data": {}, "current_field_index": 0, "step": "fill_form",
    })
    user_sessions[chat_id] = session

    welcome = company.get("welcome_message") or f"📝 {company['name']} — Let's get your details\n\nI'll ask you a few questions. Type /cancel to abort.\n━━━━━━━━━━━━━━━━━"
    await query.edit_message_text(welcome)
    await ask_next_field(update, context, chat_id)
    return FILL_FORM


# ── Dynamic Form ──────────────────────────────────────────────────────────────

async def ask_next_field(update, context, chat_id):
    session = user_sessions.get(chat_id)
    if not session:
        return
    schema = session["form_schema"]
    idx = session["current_field_index"]
    if idx >= len(schema):
        return

    field = schema[idx]
    req_text = " (required)" if field.get("required") else " (optional, send '-' to skip)"

    if field.get("type") == "choice":
        options = field.get("options", [])
        buttons, row = [], []
        for opt in options:
            row.append(InlineKeyboardButton(opt, callback_data=f"form:{opt}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        await context.bot.send_message(chat_id, f"📌 {field['label']}{req_text}", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await context.bot.send_message(chat_id, f"📌 {field['label']}{req_text}")


async def handle_form_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.get(chat_id)
    if not session or session.get("step") != "fill_form":
        return ConversationHandler.END

    schema = session["form_schema"]
    idx = session["current_field_index"]
    if idx >= len(schema):
        return ConversationHandler.END

    field = schema[idx]
    value = update.message.text.strip()

    if value == "-" and not field.get("required"):
        value = ""
    elif value == "-" and field.get("required"):
        await update.message.reply_text("This field is required. Please provide a value:")
        return FILL_FORM

    if field.get("type") == "number":
        try:
            value = str(int(value))
        except ValueError:
            await update.message.reply_text("Please enter a valid number:")
            return FILL_FORM

    session["form_data"][field["key"]] = value
    session["current_field_index"] += 1
    user_sessions[chat_id] = session
    await update.message.reply_text("✅ Got it!")

    if session["current_field_index"] >= len(schema):
        await create_ticket(update, context, chat_id)
        return ConversationHandler.END

    await ask_next_field(update, context, chat_id)
    return FILL_FORM


async def handle_form_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not query.data.startswith("form:"):
        return

    chat_id = update.effective_chat.id
    session = user_sessions.get(chat_id)
    if not session or session.get("step") != "fill_form":
        return ConversationHandler.END

    schema = session["form_schema"]
    idx = session["current_field_index"]
    if idx >= len(schema):
        return ConversationHandler.END

    field = schema[idx]
    value = query.data.split(":", 1)[1]

    session["form_data"][field["key"]] = value
    session["current_field_index"] += 1
    user_sessions[chat_id] = session

    await query.edit_message_text(f"📌 {field['label']}\n✅ Selected: {value}")

    if session["current_field_index"] >= len(schema):
        await create_ticket(update, context, chat_id)
        return ConversationHandler.END

    await ask_next_field(update, context, chat_id)
    return FILL_FORM


# ── Ticket Creation ───────────────────────────────────────────────────────────

async def create_ticket(update, context, chat_id):
    session = user_sessions.get(chat_id)
    if not session:
        return

    user = update.effective_user or (update.callback_query.from_user if update.callback_query else None)
    if not user:
        return

    summary = "\n".join([f"  {k.replace('_', ' ').title()}: {v}" for k, v in session["form_data"].items() if v])

    result = api_post("internal/create-ticket/", {
        "telegram_user_id": user.id, "telegram_chat_id": chat_id,
        "telegram_username": user.username or "", "telegram_first_name": user.first_name or "",
        "service_id": session["service_id"], "company_id": session["company_id"],
        "form_data": session["form_data"],
        "bot_token_hash": hashlib.sha256(context.bot.token.encode()).hexdigest()[:16],
    })

    if result and result.get("ticket_number"):
        session.update({
            "ticket_number": result["ticket_number"], "ticket_id": result["ticket_id"],
            "ticket_status": "open", "in_live_chat": True, "step": "live_chat",
        })
        user_sessions[chat_id] = session

        custom_msg = session.get("ticket_created_message", "")
        if custom_msg:
            # Replace variables
            msg_text = custom_msg.replace("{ticket_number}", result['ticket_number']).replace("{service}", session['service_name']).replace("{company}", session['company_name'])
        else:
            msg_text = (
                f"🎫 Ticket Created Successfully!\n\n"
                f"Ticket: {result['ticket_number']}\n"
                f"Service: {session['service_name']}\n"
                f"Company: {session['company_name']}\n\n"
                f"Your Details:\n{summary}\n\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"⏳ Waiting for an agent...\n"
                f"You can send text, images, videos, audio, and files."
            )
        await context.bot.send_message(chat_id, msg_text)
    else:
        await context.bot.send_message(chat_id, "❌ Error creating ticket. Please try again with /start.")
        user_sessions.pop(chat_id, None)


# ── Live Chat — Text Messages ────────────────────────────────────────────────

async def handle_live_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_sessions.get(chat_id)

    if not session or not session.get("in_live_chat"):
        await update.message.reply_text("No active ticket found. Use /start to create a new one!")
        return

    ticket_id = session.get("ticket_id")
    if not ticket_id:
        return

    result = api_post("internal/user-message/", {
        "ticket_id": ticket_id,
        "telegram_chat_id": chat_id,
        "content": update.message.text,
    })

    if not result:
        await update.message.reply_text("⚠️ Could not deliver your message. Please try again.")


# ── Live Chat — Media Messages ───────────────────────────────────────────────

async def handle_live_chat_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos, videos, audio, voice, and documents from user."""
    chat_id = update.effective_chat.id
    session = user_sessions.get(chat_id)

    if not session or not session.get("in_live_chat"):
        await update.message.reply_text("No active ticket found. Use /start to create a new one!")
        return

    ticket_id = session.get("ticket_id")
    if not ticket_id:
        return

    msg = update.message
    file_obj = None
    media_type = "document"
    filename = "file"
    caption = msg.caption or ""

    if msg.photo:
        # Get largest photo
        photo = msg.photo[-1]
        file_obj = await context.bot.get_file(photo.file_id)
        media_type = "image"
        filename = f"photo_{photo.file_unique_id}.jpg"
    elif msg.video:
        file_obj = await context.bot.get_file(msg.video.file_id)
        media_type = "video"
        filename = msg.video.file_name or f"video_{msg.video.file_unique_id}.mp4"
    elif msg.audio:
        file_obj = await context.bot.get_file(msg.audio.file_id)
        media_type = "audio"
        filename = msg.audio.file_name or f"audio_{msg.audio.file_unique_id}.mp3"
    elif msg.voice:
        file_obj = await context.bot.get_file(msg.voice.file_id)
        media_type = "audio"
        filename = f"voice_{msg.voice.file_unique_id}.ogg"
    elif msg.document:
        file_obj = await context.bot.get_file(msg.document.file_id)
        media_type = "document"
        filename = msg.document.file_name or f"file_{msg.document.file_unique_id}"
    elif msg.sticker:
        # Skip stickers or treat as image
        if msg.sticker.is_animated or msg.sticker.is_video:
            await update.message.reply_text("Animated stickers are not supported.")
            return
        file_obj = await context.bot.get_file(msg.sticker.file_id)
        media_type = "image"
        filename = f"sticker_{msg.sticker.file_unique_id}.webp"

    if not file_obj:
        return

    # Download the file from Telegram
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as tmp:
            await file_obj.download_to_drive(tmp.name)
            tmp_path = tmp.name

        # Upload to Django backend
        with open(tmp_path, "rb") as f:
            result = api_post_file("internal/user-media/", {
                "ticket_id": ticket_id,
                "caption": caption,
                "media_type": media_type,
                "media_filename": filename,
            }, {"file": (filename, f)})

        # Clean up temp file
        os.unlink(tmp_path)

        if not result:
            await update.message.reply_text("⚠️ Could not deliver your file. Please try again.")

    except Exception as e:
        logger.error(f"Media upload failed: {e}")
        await update.message.reply_text("⚠️ Failed to send file. Please try again.")


# ── Fallback & Error ──────────────────────────────────────────────────────────

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤔 Unknown command. Try /help")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Bot error: {context.error}", exc_info=context.error)
    if update and update.effective_chat:
        try:
            await context.bot.send_message(update.effective_chat.id, "⚠️ Something went wrong. Try /start.")
        except Exception:
            pass


# ── Health Check ──────────────────────────────────────────────────────────────

def check_bot_health(token):
    try:
        return requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10).status_code == 200
    except Exception:
        return False


def get_healthy_token():
    for token in BOT_TOKENS:
        if check_bot_health(token):
            logger.info(f"Using bot token ending in ...{token[-6:]}")
            return token
        logger.warning(f"Bot ...{token[-6:]} unhealthy, trying next...")
    return None


# ── Build & Run ───────────────────────────────────────────────────────────────

def build_app(token):
    app = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            SELECT_SERVICE: [CallbackQueryHandler(service_selected, pattern=r"^svc:")],
            SELECT_COMPANY: [CallbackQueryHandler(company_selected, pattern=r"^(comp:|back:)")],
            FILL_FORM: [
                CallbackQueryHandler(handle_form_choice, pattern=r"^form:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_form_text),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_command), CommandHandler("start", start_command)],
        per_chat=True,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))

    # Live chat — text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_live_chat_message))

    # Live chat — media messages (photos, videos, audio, voice, documents, stickers)
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE | filters.Document.ALL | filters.Sticker.ALL,
        handle_live_chat_media,
    ))

    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_error_handler(error_handler)

    return app


def main():
    load_services()
    token = get_healthy_token()
    if not token:
        logger.error("No healthy bot tokens found!")
        sys.exit(1)

    app = build_app(token)

    webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
    if webhook_url:
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        app.run_webhook(listen="0.0.0.0", port=int(os.getenv("BOT_PORT", "8443")), webhook_url=f"{webhook_url}/api/webhook/{token_hash}/")
    else:
        logger.info("Starting bot in polling mode...")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
