import os
import asyncio
import threading
from flask import Flask

from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from playwright.async_api import async_playwright

# ================== FLASK (RENDER PORT FIX) ==================
web = Flask(__name__)

@web.route("/")
def home():
    return "Bot is running successfully"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    web.run(host="0.0.0.0", port=port)

# ================== TELEGRAM BOT ==================
TOKEN = "8458139520:AAFJHdnDlhJQN9lNSNYRIfyOxgEZ0YdRlXY"   # ⚠️ token env এ রাখলে ভালো

CHANNELS = ["@bdalminofficial0099", "@wingo_server24"]
MAX_FILE_SIZE = 100 * 1024 * 1024

# ---------- UTIL ----------
async def is_joined(bot, user_id):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

async def render_html(path):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(f"file://{os.path.abspath(path)}")

        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except:
            pass

        await page.evaluate("""() => {
            document.querySelectorAll('script').forEach(s => {
                const c = s.innerText || '';
                if (c.length > 8000 && (c.includes('eval(') || c.includes('atob('))) {
                    s.remove();
                }
            });
        }""")

        content = await page.content()
        await browser.close()
        return content

# ---------- COMMANDS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Channel 1", url="https://t.me/bdalminofficial0099")],
        [InlineKeyboardButton("📢 Channel 2", url="https://t.me/wingo_server24")],
        [InlineKeyboardButton("✅ Check Join", callback_data="check")]
    ])
    await update.message.reply_text(
        "🔐 Join channels to use this bot",
        reply_markup=kb
    )

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if await is_joined(context.bot, q.from_user.id):
        await q.edit_message_text("✅ Joined! Now send HTML file.")
    else:
        await q.answer("❌ Join all channels first", show_alert=True)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_joined(context.bot, update.effective_user.id):
        await update.message.reply_text("❌ Join channels first")
        return

    doc = update.message.document
    if not doc.file_name.endswith(".html"):
        await update.message.reply_text("❌ Only HTML allowed")
        return

    path = f"temp_{doc.file_name}"
    await (await doc.get_file()).download_to_drive(path)

    msg = await update.message.reply_text("⏳ Processing...")

    try:
        rendered = await render_html(path)
        out = f"clean_{doc.file_name}"

        with open(out, "w", encoding="utf-8") as f:
            f.write(rendered)

        await msg.delete()
        await update.message.reply_document(open(out, "rb"), caption="✅ Done")

        os.remove(path)
        os.remove(out)

    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

# ---------- MAIN ----------
def run_bot():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
