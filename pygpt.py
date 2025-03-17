import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

TOKEN = os.getenv("TOKEN")  # اجلب التوكن من متغيرات البيئة
PORT = int(os.getenv("PORT", 8443))  # استخدم المنفذ من متغير البيئة أو 8443 افتراضيًا
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # احصل على رابط الـ webhook من متغير البيئة

if not TOKEN or not WEBHOOK_URL:
    raise ValueError("TOKEN and WEBHOOK_URL must be set in environment variables")

# دالة للرد على /start
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("مرحبا! أنا بوت Telegram.")

# دالة للرد على أي رسالة
async def echo(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(update.message.text)

# إنشاء التطبيق
application = Application.builder().token(TOKEN).build()

# إضافة المعالجات (Handlers)
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# تشغيل التطبيق باستخدام webhook
application.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=TOKEN,  # يُستخدم كجزء من عنوان الـ webhook
    webhook_url=f"{WEBHOOK_URL}/{TOKEN}"  # عنوان الـ webhook الكامل
)
