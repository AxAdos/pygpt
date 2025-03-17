from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import yt_dlp
import os
import uuid

TOKEN = "7336372322:AAEtIUcY6nNEEGZzIMjJdfYMTAMsLpTSpzk"

# دالة لاستخراج الجودات المتاحة
def get_available_formats(url):
    ydl = yt_dlp.YoutubeDL()
    info = ydl.extract_info(url, download=False)
    formats = info.get('formats', [])
    
    available_formats = []
    for f in formats:
        if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
            available_formats.append({
                'format_id': f.get('format_id'),
                'resolution': f.get('resolution', 'unknown'),
                'ext': f.get('ext', 'unknown'),
            })
    
    return available_formats

# أوامر التحكم بالبوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبًا! أرسل رابط فيديو وسأقوم بتحميله لك.")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    try:
        formats = get_available_formats(url)
        if not formats:
            await update.message.reply_text("لم أجد أي جودات متاحة.")
            return
        
        keyboard = [[InlineKeyboardButton(f"{f['resolution']} ({f['ext']})", callback_data=f['format_id'])] for f in formats]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("اختر الجودة:", reply_markup=reply_markup)
        context.user_data['url'] = url
    
    except Exception as e:
        await update.message.reply_text(f"خطأ: {e}")

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    format_id = query.data
    url = context.user_data.get('url')

    if not url:
        await query.edit_message_text("خطأ: الرابط غير موجود.")
        return

    try:
        unique_id = str(uuid.uuid4())
        filename = f"downloaded_video_{unique_id}.mp4"

        ydl_opts = {
            'format': format_id,
            'outtmpl': filename,
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            final_filename = ydl.prepare_filename(info)

        await context.bot.send_video(chat_id=query.message.chat_id, video=open(final_filename, 'rb'))
        await query.edit_message_text("تم إرسال الفيديو!")
        os.remove(final_filename)

    except Exception as e:
        await query.edit_message_text(f"خطأ غير متوقع: {e}")

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CallbackQueryHandler(download_video))

    application.run_polling()

if __name__ == '__main__':
    main()
