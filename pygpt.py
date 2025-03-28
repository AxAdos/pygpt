import os
import uuid
import time  # <-- أضف هذا الاستيراد
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
import yt_dlp

# إعداد المتغيرات الأساسية
TOKEN = "7336372322:AAEtIUcY6nNEEGZzIMjJdfYMTAMsLpTSpzk"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

@app.route("/")
def home():
    return "البوت يعمل!", 200

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# دالة محسنة لاستخراج الجودات مع معالجة الأخطاء <-- التعديل هنا
def get_available_formats(url):
    try:
        ydl = yt_dlp.YoutubeDL({
            'cookiefile': 'cookies.txt',
            'ignoreerrors': True,
            'retries': 5,
            'fragment-retries': 5,
            'sleep_interval_requests': 5,  # <-- إضافة جديدة
            'throttled_rate': '1M',  # <-- إضافة للتحكم في السرعة
        })
        info = ydl.extract_info(url, download=False)
        if not info:  # <-- تحقق من وجود البيانات
            return None
            
        formats = info.get('formats', [])
        available_formats = []
        for f in formats:
            if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                available_formats.append({
                    'format_id': f.get('format_id'),
                    'resolution': f.get('resolution') or f.get('format_note', 'unknown'),
                    'ext': f.get('ext', 'unknown')
                })
        return available_formats
    except Exception as e:
        print(f"Error in get_available_formats: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('مرحبا! أرسل رابط فيديو من يوتيوب أو فيسبوك وسأحمله لك.')

# دالة محسنة مع تأخير بين الطلبات <-- التعديل هنا
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    try:
        time.sleep(1)  # <-- تأخير قبل الطلب
        formats = get_available_formats(url)
        if not formats:
            await update.message.reply_text("⚠️ لم أجد جودات متاحة أو الفيديو مقيد.")
            return

        keyboard = [
            [InlineKeyboardButton(f"{f['resolution']} ({f['ext']})", callback_data=f['format_id'])]
            for f in formats[:10]  # <-- عرض أول 10 خيارات فقط
        ]
        await update.message.reply_text(
            "اختر جودة الفيديو:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        context.user_data['url'] = url
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {str(e)[:200]}")  # <-- تقليل طول الرسالة

# دالة التنزيل مع تحسينات الأمان <-- التعديل هنا
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        format_id = query.data
        url = context.user_data.get('url')
        if not url:
            raise ValueError("الرابط مفقود")
        
        unique_id = str(uuid.uuid4())
        filename = f"temp_{unique_id}.mp4"
        
        ydl_opts = {
            'format': format_id,
            'outtmpl': filename,
            'quiet': True,
            'retries': 10,
            'fragment-retries': 10,
            'retry-sleep': 20,  # <-- زيادة زمن الانتظار
            'cookiefile': 'cookies.txt',
            'throttled_rate': '1M',  # <-- التحكم في معدل التنزيل
            'noprogress': True,
            'http_headers': {'User-Agent': 'Mozilla/5.0'}  # <-- إضافة مهمة
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                raise Exception("فشل استخراج المعلومات")
            
            final_filename = ydl.prepare_filename(info)
            if not os.path.exists(final_filename):
                raise FileNotFoundError("الملف غير موجود بعد التنزيل")
            
            with open(final_filename, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=video_file,
                    read_timeout=300,  # <-- زيادة وقت الانتظار
                    write_timeout=300,
                    connect_timeout=300
                )
        
        await query.edit_message_text("✅ تم الإرسال بنجاح!")
    except yt_dlp.utils.DownloadError as e:
        await query.edit_message_text(f"⛔ خطأ في التنزيل: {str(e)[:200]}")
    except Exception as e:
        await query.edit_message_text(f"⚠️ خطأ غير متوقع: {str(e)[:200]}")
    finally:
        if 'final_filename' in locals() and os.path.exists(final_filename):
            os.remove(final_filename)

# بقية الكود بدون تغيير...
# الدالة الرئيسية لتشغيل البوت
def main():
    # تشغيل خادم Flask في Thread منفصل لفتح منفذ HTTP
    Thread(target=run_flask).start()
    
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CallbackQueryHandler(download_video))
    
    # تشغيل البوت باستخدام polling
    application.run_polling()

if __name__ == '__main__':
    main()
