import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# وضع التوكن والهوك مباشرة في الكود
TOKEN = "7336372322:AAEtIUcY6nNEEGZzIMjJdfYMTAMsLpTSpzk"
WEBHOOK_URL = "https://api.render.com/deploy/srv-cvbnb9tds78s73ampivg?key=bVahe5gy2Nw"

# استخدم المنفذ المخصص من Render أو 10000 افتراضيًا
PORT = int(os.getenv("PORT", 10000))

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
    listen="0.0.0.0",  # استماع لجميع الشبكات
    port=PORT,  # استخدام المنفذ 10000 من البيئة
    url_path=TOKEN,  # يُستخدم كجزء من عنوان الـ webhook
    webhook_url=f"{WEBHOOK_URL}/{TOKEN}"  # عنوان الـ webhook الكامل
)
