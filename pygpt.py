import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, Defaults
from pytube import YouTube

app = Flask(__name__)

# معالج الأمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبًا! أرسل رابط فيديو اليوتيوب لتنزيله.")

# معالج تنزيل الفيديو
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    try:
        yt = YouTube(url)
        video = yt.streams.get_highest_resolution()
        video_file = video.download(output_path="/tmp", filename=f"{yt.video_id}.mp4")
        
        with open(video_file, "rb") as f:
            await update.message.reply_video(video=f, caption=yt.title)
        
        os.remove(video_file)
    
    except Exception as e:
        await update.message.reply_text(f"عذراً، حدث خطأ: {str(e)}")

# معالج الأخطاء
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"حدث خطأ: {context.error}")

# تشغيل Flask في خيط منفصل
def run_flask():
    @app.route('/')
    def home():
        return "البوت يعمل!"
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    # تشغيل Flask
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # تشغيل البوت
    token = os.getenv("TELEGRAM_TOKEN")
    application = ApplicationBuilder().token(token).defaults(Defaults()).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    application.add_error_handler(error_handler)  # <--- أضف هذا السطر
    
    application.run_polling()
