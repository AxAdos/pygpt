import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# توكن البوت (تم استبداله بالتوكن المحدد)
TOKEN = '7336372322:AAEtIUcY6nNEEGZzIMjJdfYMTAMsLpTSpzk'

# إعدادات yt-dlp
ydl_opts = {
    'format': 'best',  # يمكنك تغيير الجودة هنا (مثال: 'bestvideo+bestaudio')
    'quiet': True,
    'no_warnings': True,
}

# معالجة الأمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبًا! أرسل رابط فيديو يوتيوب وسأقوم بتحميله لك.")

# معالجة الروابط الواردة
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if 'youtube.com' in url or 'youtu.be' in url:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
            
            # إرسال الفيديو إلى المستخدم
            with open(filename, 'rb') as video_file:
                await update.message.reply_video(video=video_file)
            logging.info(f"تم تنزيل الفيديو: {filename}")
        except Exception as e:
            error_message = f"حدث خطأ: {str(e)}"
            await update.message.reply_text(error_message)
            logging.error(error_message)
    else:
        await update.message.reply_text("الرابط غير صالح! يُرجى إرسال رابط يوتيوب صحيح.")

# تشغيل البوت
if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # بناء التطبيق
    application = ApplicationBuilder().token(TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video))
    
    # بدء التشغيل
    application.run_polling()
