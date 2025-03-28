import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from pytube import YouTube

# معالج الأمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل رابط اليوتيوب لتنزيل الفيديو.")

# معالج تنزيل الفيديو
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    try:
        yt = YouTube(url)
        video = yt.streams.get_highest_resolution()
        video_file = video.download(output_path="/tmp", filename="video.mp4")
        
        with open(video_file, "rb") as f:
            await update.message.reply_video(video=f, caption=yt.title)
        
        os.remove(video_file)
    
    except Exception as e:
        await update.message.reply_text(f"خطأ: {str(e)}")

if __name__ == "__main__":
    token = os.getenv("TELEGRAM_TOKEN")
    app = ApplicationBuilder().token(token).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    
    app.run_polling()
