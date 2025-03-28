import os
import uuid
from threading import Thread
from flask import Flask
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
PORT = int(os.environ.get("PORT", 10000))  # استخدم المنفذ من البيئة (Render يحدد PORT) أو 10000 كافتراضي

# إنشاء تطبيق Flask وهمي لفتح المنفذ (مطلوب من Render)
app = Flask(__name__)

@app.route("/")
def home():
    return "البوت يعمل!", 200

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# دالة لاستخراج الجودات المتاحة باستخدام yt_dlp
def get_available_formats(url):
    ydl_opts = {"quiet": True, "noplaylist": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get("formats", [])
    
    available_formats = []
    for f in formats:
        if f.get("vcodec") != "none" and f.get("acodec") != "none":  # فيديو مع صوت
            available_formats.append({
                "format_id": f.get("format_id"),
                "resolution": f.get("resolution", "unknown"),
                "ext": f.get("ext", "unknown"),
            })
    return available_formats

# دالة بدء البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبا! أرسل رابط فيديو من يوتيوب أو فيسبوك وسأحمله لك.")

# دالة لمعالجة الرابط وعرض الجودات عبر InlineKeyboard
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    try:
        formats = get_available_formats(url)
        if not formats:
            await update.message.reply_text("لم أتمكن من العثور على جودات متاحة.")
            return

        keyboard = [
            [InlineKeyboardButton(f"{f['resolution']} ({f['ext']})", callback_data=f["format_id"])]
            for f in formats
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("اختر جودة الفيديو:", reply_markup=reply_markup)
        context.user_data["url"] = url
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ: {e}")

# دالة لمعالجة اختيار الجودة وتنزيل الفيديو باستخدام yt_dlp مع استخدام ملف cookies.txt
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    format_id = query.data
    url = context.user_data.get("url")
    
    if not url:
        await query.edit_message_text("حدث خطأ: الرابط غير موجود.")
        return

    try:
        unique_id = str(uuid.uuid4())
        filename = f"downloaded_video_{unique_id}.mp4"
        ydl_opts = {
            "format": format_id,
            "outtmpl": filename,
            "quiet": True,
            "no_warnings": True,
            "cookies": "cookies.txt",  # تأكد من وجود ملف cookies.txt في نفس مجلد السكربت
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            final_filename = ydl.prepare_filename(info)
        
        await context.bot.send_video(
            chat_id=query.message.chat_id,
            video=open(final_filename, "rb"),
            read_timeout=120,
            write_timeout=120,
            connect_timeout=120,
            pool_timeout=120,
        )
        await query.edit_message_text("تم إرسال الفيديو بنجاح!")
        os.remove(final_filename)
    
    except yt_dlp.utils.DownloadError as e:
        await query.edit_message_text(f"حدث خطأ أثناء التنزيل: {e}")
    except Exception as e:
        await query.edit_message_text(f"حدث خطأ غير متوقع: {e}")

# الدالة الرئيسية لتشغيل البوت باستخدام polling مع Flask
def main():
    # تشغيل خادم Flask في Thread منفصل حتى يفتح منفذ HTTP (يتطلبه Render)
    Thread(target=run_flask).start()
    
    # إعداد تطبيق Telegram
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CallbackQueryHandler(download_video))
    
    # تشغيل البوت باستخدام polling
    application.run_polling()

if __name__ == "__main__":
    main()
