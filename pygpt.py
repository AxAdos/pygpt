import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from pytube import YouTube

# معالج الأمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبًا! أرسل رابط فيديو اليوتيوب لتنزيله.")

# معالج تنزيل الفيديو
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    try:
        yt = YouTube(url)
        video = yt.streams.get_highest_resolution()
        
        # تنزيل الفيديو إلى مجلد مؤقت
        video_file = video.download(output_path="/tmp", filename=f"{yt.video_id}.mp4")
        
        # إرسال الفيديو إلى المستخدم
        with open(video_file, "rb") as f:
            await update.message.reply_video(video=f, caption=yt.title)
        
        # حذف الملف بعد الإرسال
        os.remove(video_file)
    
    except Exception as e:
        await update.message.reply_text(f"عذراً، حدث خطأ: {str(e)}")

# إعداد البوت
if __name__ == "__main__":
    # أخذ Token من متغير البيئة
    token = os.getenv("TELEGRAM_TOKEN")
    
    # تهيئة البوت
    application = ApplicationBuilder().token(token).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    
    # تشغيل البوت
    application.run_polling()
