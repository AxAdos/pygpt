from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import os
import uuid

# استبدل بالتوكن الخاص بك
TOKEN = "7336372322:AAEtIUcY6nNEEGZzIMjJdfYMTAMsLpTSpzk"

# قائمة لحفظ حالات التحميل
active_downloads = {}

# دالة لبدء البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 مرحبًا! أرسل رابط فيديو وسأقوم بتحميله لك.")

# دالة لاستخراج الجودات المتاحة
def get_available_formats(url):
    ydl = yt_dlp.YoutubeDL()
    info = ydl.extract_info(url, download=False)
    formats = info.get('formats', [])
    available_formats = [
        {
            'format_id': f['format_id'],
            'resolution': f.get('resolution', f.get('format_note', 'unknown')),
            'ext': f.get('ext', 'unknown'),
        }
        for f in formats if f.get('vcodec') != 'none' and f.get('acodec') != 'none'
    ]
    return available_formats

# دالة لمعالجة الروابط
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    try:
        formats = get_available_formats(url)
        if not formats:
            await update.message.reply_text("⚠️ لم أتمكن من العثور على جودات متاحة.")
            return
        
        # حفظ الرابط في الذاكرة
        context.user_data['url'] = url
        
        # عرض الجودات المتاحة
        buttons = [
            [InlineKeyboardButton(f"{f['resolution']} ({f['ext']})", callback_data=f['format_id'])]
            for f in formats
        ]
        await update.message.reply_text("🎥 اختر جودة الفيديو:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await update.message.reply_text(f"⚠️ حدث خطأ: {e}")

# دالة لتنزيل الفيديو
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    format_id = query.data
    url = context.user_data.get('url')
    
    if not url:
        await query.edit_message_text("⚠️ حدث خطأ: الرابط غير موجود.")
        return
    
    try:
        unique_id = str(uuid.uuid4())
        filename = f"downloaded_video_{unique_id}.mp4"
        
        ydl_opts = {
            'format': format_id,
            'outtmpl': filename,
            'quiet': True,
        }
        
        active_downloads[unique_id] = 'downloading'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        active_downloads[unique_id] = 'completed'
        
        await context.bot.send_video(chat_id=query.message.chat_id, video=open(filename, 'rb'))
        os.remove(filename)
        await query.edit_message_text("✅ تم إرسال الفيديو بنجاح!")
    except Exception as e:
        active_downloads[unique_id] = 'failed'
        await query.edit_message_text(f"⚠️ حدث خطأ: {e}")

# دوال التحكم في التحميل
async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏸️ ميزة الإيقاف المؤقت غير مدعومة حاليًا.")

async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("▶️ ميزة الاستئناف غير مدعومة حاليًا.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ لا يمكن إلغاء التحميل بعد بدئه.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📊 حالة التحميل: {active_downloads}")

# تشغيل البوت كـ Background Worker
def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CommandHandler("pause", pause))
    application.add_handler(CommandHandler("resume", resume))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("status", status))
    
    print("🤖 البوت يعمل الآن باستخدام polling...")
    application.run_polling()

if __name__ == "__main__":
    main()
