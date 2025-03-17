import os
import yt_dlp
import uuid
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = "7336372322:AAEtIUcY6nNEEGZzIMjJdfYMTAMsLpTSpzk"
WEBHOOK_URL = "https://api.render.com/deploy/srv-cvauf2tumphs73aj6a20?key=g7L1eSK-mVA"
PORT = int(os.environ.get("PORT", 8080))

app = Flask(__name__)

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('مرحبا! أرسل رابط فيديو من يوتيوب وسأقوم بتحميله لك.')

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    try:
        formats = get_available_formats(url)
        if not formats:
            await update.message.reply_text("لم أتمكن من العثور على جودات متاحة.")
            return
        keyboard = [[InlineKeyboardButton(f"{f['resolution']} ({f['ext']})", callback_data=f['format_id'])] for f in formats]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("اختر جودة الفيديو:", reply_markup=reply_markup)
        context.user_data['url'] = url
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ: {e}")

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    format_id = query.data
    url = context.user_data.get('url')
    if not url:
        await query.edit_message_text("حدث خطأ: الرابط غير موجود.")
        return
    try:
        filename = f"downloaded_video_{uuid.uuid4()}.mp4"
        ydl_opts = {'format': format_id, 'outtmpl': filename, 'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            final_filename = ydl.prepare_filename(info)
        await context.bot.send_video(chat_id=query.message.chat_id, video=open(final_filename, 'rb'))
        await query.edit_message_text("تم إرسال الفيديو بنجاح!")
        os.remove(final_filename)
    except yt_dlp.utils.DownloadError as e:
        await query.edit_message_text(f"خطأ في التحميل: {e}")
    except Exception as e:
        await query.edit_message_text(f"خطأ غير متوقع: {e}")

application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
application.add_handler(CallbackQueryHandler(download_video))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), application.bot)
    application.update_queue.put(update)
    return "OK", 200

async def set_webhook():
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")

if __name__ == "__main__":
    application.run_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)
