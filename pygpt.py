from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import yt_dlp
import os
import uuid
import asyncio

# ✅ بيانات البوت
TOKEN = "7336372322:AAEtIUcY6nNEEGZzIMjJdfYMTAMsLpTSpzk"
WEBHOOK_URL = "https://api.render.com/deploy/srv-cvbnb9tds78s73ampivg?key=bVahe5gy2Nw"  # ← استبدله بعنوان السيرفر الفعلي

# ✅ إنشاء Flask
app = Flask(__name__)

# ✅ إنشاء بوت Telegram
bot = Bot(TOKEN)
application = Application.builder().token(TOKEN).build()

# ✅ دالة بدء البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 مرحبًا! أرسل رابط فيديو من يوتيوب وسأقوم بتحميله لك.")

# ✅ دالة استقبال الروابط
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    await update.message.reply_text(f"🔄 جاري معالجة الرابط: {url}")

# ✅ إضافة Handlers للبوت
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

# ✅ استقبال الطلبات من Telegram عبر Webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    asyncio.run(application.process_update(update))
    return "OK", 200

# ✅ نقطة الوصول الرئيسية
@app.route("/")
def home():
    return "✅ البوت يعمل عبر Webhook!"

# ✅ تشغيل التطبيق
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
