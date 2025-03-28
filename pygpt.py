import os
import uuid
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
TOKEN = "7336372322:AAEtIUcY6nNEEGZzIMjJdfYMTAMsLpTSpzk"  # ← استبدل هذا بالمفتاح الحقيقي
PORT = int(os.environ.get("PORT", 10000))  # استخدام المنفذ من البيئة أو 10000 كافتراضي

# إنشاء تطبيق Flask لفتح منفذ HTTP (مطلوب من Render)
app = Flask(__name__)

@app.route("/")
def home():
    return "البوت يعمل!", 200

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# دالة لاستخراج الجودات المتاحة باستخدام yt_dlp
def get_available_formats(url):
    ydl = yt_dlp.YoutubeDL()
    info = ydl.extract_info(url, download=False)
    formats = info.get('formats', [])
    
    # تصفية الجودات المتاحة (فيديو مع صوت)
    available_formats = []
    for f in formats:
        if f.get('vcodec') != 'none' and f.get('acodec') != 'none':  # فيديو مع صوت
            format_id = f.get('format_id')
            resolution = f.get('resolution', 'unknown')
            format_note = f.get('format_note', 'unknown')
            ext = f.get('ext', 'unknown')
            available_formats.append({
                'format_id': format_id,
                'resolution': resolution if resolution != 'unknown' else format_note,
                'ext': ext,
            })
    
    return available_formats

# دالة بدء البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('مرحبا! أرسل رابط فيديو من يوتيوب أو فيسبوك وسأحمله لك.')

# دالة معالجة الرابط واستخراج الجودات وعرضها للمستخدم عبر InlineKeyboard
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    try:
        formats = get_available_formats(url)
        if not formats:
            await update.message.reply_text("لم أتمكن من العثور على جودات متاحة.")
            return
        
        keyboard = []
        for f in formats:
            button_text = f"{f['resolution']} ({f['ext']})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f['format_id'])])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("اختر جودة الفيديو:", reply_markup=reply_markup)
        context.user_data['url'] = url
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ: {e}")

# دالة معالجة اختيار الجودة وتنزيل الفيديو
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    format_id = query.data
    url = context.user_data.get('url')
    
    if not url:
        await query.edit_message_text("حدث خطأ: الرابط غير موجود.")
        return
    
    try:
        unique_id = str(uuid.uuid4())
        filename = f"downloaded_video_{unique_id}.mp4"
        
        ydl_opts = {
            'format': format_id,
            'outtmpl': filename,
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            final_filename = ydl.prepare_filename(info)
        
        # فتح الملف وإرساله عبر التليجرام
        with open(final_filename, 'rb') as video_file:
            await context.bot.send_video(
                chat_id=query.message.chat_id,
                video=video_file,
                read_timeout=120,
                write_timeout=120,
                connect_timeout=120,
                pool_timeout=120,
            )
        
        await query.edit_message_text("تم إرسال الفيديو بنجاح!")
        os.remove(final_filename)
    
    except yt_dlp.utils.DownloadError as e:
        await query.edit_message_text(f"حدث خطأ: {e}")
    except Exception as e:
        await query.edit_message_text(f"حدث خطأ غير متوقع: {e}")

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
