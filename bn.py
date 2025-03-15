import os
import uuid
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# استبدل 'YOUR_BOT_TOKEN' بالرمز الذي حصلت عليه من BotFather
TOKEN = '7336372322:AAEtIUcY6nNEEGZzIMjJdfYMTAMsLpTSpzk'

# زيادة مهلة الانتظار (timeout) لتحميل وإرسال الملفات الكبيرة
DOWNLOAD_TIMEOUT = 300  # 5 دقائق (بالثواني)
UPLOAD_TIMEOUT = 300  # 5 دقائق (بالثواني)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('مرحبًا! أرسل لي رابط فيديو من YouTube أو أي منصة أخرى لأقوم بتحميله وإرساله إليك.')

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    video_url = update.message.text
    await update.message.reply_text('جاري تحميل الفيديو...')

    # إنشاء اسم فريد للملف
    unique_id = str(uuid.uuid4())
    video_filename = f"downloaded_video_{unique_id}.mp4"

    # خيارات yt-dlp
    ydl_opts = {
        'format': 'best',  # أفضل جودة متاحة
        'outtmpl': video_filename,  # اسم الملف المحمل
        'quiet': True,  # إخفاء الرسائل غير الضرورية
        'socket_timeout': DOWNLOAD_TIMEOUT,  # زيادة مهلة الانتظار للتحميل
    }

    try:
        # تحميل الفيديو باستخدام yt-dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        await update.message.reply_text('تم تحميل الفيديو بنجاح. جاري إرساله إليك...')

        # إرسال الفيديو إلى المستخدم مع زيادة مهلة الانتظار
        with open(video_filename, 'rb') as video_file:
            await update.message.reply_video(
                video=video_file,
                read_timeout=UPLOAD_TIMEOUT,
                write_timeout=UPLOAD_TIMEOUT,
                connect_timeout=UPLOAD_TIMEOUT,
                pool_timeout=UPLOAD_TIMEOUT,
            )
        
    except Exception as e:
        await update.message.reply_text(f'حدث خطأ أثناء تحميل الفيديو: {str(e)}')
    finally:
        # حذف الفيديو بعد الإرسال لتوفير المساحة
        if os.path.exists(video_filename):
            os.remove(video_filename)
            print(f"تم حذف الفيديو: {video_filename}")

def main() -> None:
    # إنشاء تطبيق البوت
    application = Application.builder().token(TOKEN).build()

    # إضافة handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video))

    # بدء البوت
    application.run_polling()

if __name__ == '__main__':
    main()
