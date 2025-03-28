import os
import threading
import time
import uuid
import asyncio
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    filters,
    CallbackQueryHandler,
)
import yt_dlp

# إعداد التوكن والويب هوك (يفضل قراءتهم من متغيرات البيئة)
TOKEN = "7344680185:AAEs0-LuI__6rQkVnKHLMGwEMOBfL2g5uuo"  # استبدل بالمفتاح الحقيقي
WEBHOOK_URL = "https://api.render.com/deploy/srv-cvbnb9tds78s73ampivg?key=bVahe5gy2Nw"
PORT = int(os.getenv("PORT", 10000))

# معجم لتخزين حالة التحميل لكل chat_id
downloads = {}
# downloads[chat_id] = {
#   "thread": <thread>,
#   "state": "downloading" / "paused" / "canceled" / "completed",
#   "progress": { ... },
#   "file": "path/to/downloaded/file"
# }

def progress_hook_factory(chat_id):
    def progress_hook(d):
        if d.get("status") in ["downloading", "finished"]:
            downloads[chat_id]["progress"] = d  # تحديث بيانات التقدم
            # الانتظار إذا كان المستخدم طلب الإيقاف المؤقت
            while downloads[chat_id]["state"] == "paused":
                time.sleep(1)
            # التحقق من الإلغاء
            if downloads[chat_id]["state"] == "canceled":
                raise Exception("تم إلغاء التحميل من قبل المستخدم")
    return progress_hook

def get_available_formats(url):
    ydl_opts = {"quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get("formats", [])
    available_formats = []
    for f in formats:
        # التأكد من أن التنسيق يحتوي على فيديو وصوت
        if f.get("vcodec") != "none" and f.get("acodec") != "none":
            format_id = f.get("format_id")
            resolution = f.get("resolution", "unknown")
            format_note = f.get("format_note", "unknown")
            ext = f.get("ext", "unknown")
            available_formats.append({
                "format_id": format_id,
                "resolution": resolution if resolution != "unknown" else format_note,
                "ext": ext,
            })
    return available_formats

def download_video(chat_id, url, chosen_format, update: Update, context: CallbackContext):
    # تهيئة بيانات التحميل
    downloads[chat_id] = {
        "state": "downloading",
        "progress": {},
        "file": None,
        "thread": threading.current_thread()
    }
    # إنشاء اسم ملف فريد باستخدام UUID
    unique_id = str(uuid.uuid4())
    filename = f"downloaded_video_{unique_id}.mp4"
    ydl_opts = {
        "format": chosen_format,
        "outtmpl": filename,
        "progress_hooks": [progress_hook_factory(chat_id)],
        "retries": 3,
        "continuedl": True,
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloads[chat_id]["state"] = "completed"
            final_filename = ydl.prepare_filename(info)
            downloads[chat_id]["file"] = final_filename
            # جدولة إرسال الفيديو عبر event loop
            context.application.create_task(send_video(chat_id, final_filename, update, context))
    except Exception as e:
        context.application.create_task(
            context.bot.send_message(chat_id=chat_id, text=f"فشل التحميل: {e}")
        )
    finally:
        # تنظيف بيانات التحميل؛ حذف الملف يتم بعد الإرسال في send_video
        if chat_id in downloads:
            del downloads[chat_id]

async def send_video(chat_id, file_path, update: Update, context: CallbackContext):
    try:
        await context.bot.send_video(
            chat_id=chat_id,
            video=InputFile(file_path),
            timeout=120  # زيادة وقت المهلة عند الإرسال
        )
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"حدث خطأ أثناء إرسال الفيديو: {e}")
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as ex:
                print(f"خطأ أثناء حذف الملف: {ex}")

# أمر /start: رسالة ترحيبية تطلب من المستخدم إرسال الرابط
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("مرحباً! أرسل رابط فيديو (يوتيوب أو فيسبوك) لتحميله.")

# معالجة الرابط: استخراج الجودات وعرض InlineKeyboard للمستخدم
async def handle_url(update: Update, context: CallbackContext) -> None:
    url = update.message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("يرجى إرسال رابط فيديو صحيح.")
        return
    try:
        formats = get_available_formats(url)
        if not formats:
            await update.message.reply_text("لم أتمكن من العثور على جودات متاحة.")
            return
        keyboard = []
        for f in formats:
            button_text = f"{f['resolution']} ({f['ext']})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f["format_id"])])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("اختر جودة الفيديو:", reply_markup=reply_markup)
        # حفظ الرابط في بيانات المستخدم للاستخدام لاحقاً
        context.user_data["url"] = url
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ: {e}")

# معالجة اختيار الجودة عبر CallbackQuery
async def download_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    chosen_format = query.data
    url = context.user_data.get("url")
    chat_id = query.message.chat_id
    if not url:
        await query.edit_message_text("حدث خطأ: الرابط غير موجود.")
        return
    await query.edit_message_text("جاري بدء عملية التحميل...")
    # بدء عملية التحميل في Thread منفصل لتفادي حجب الـ event loop
    download_thread = threading.Thread(
        target=download_video, args=(chat_id, url, chosen_format, update, context)
    )
    download_thread.start()

# أوامر التحكم: pause, resume, cancel, status
async def pause(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in downloads and downloads[chat_id]["state"] == "downloading":
        downloads[chat_id]["state"] = "paused"
        await update.message.reply_text("تم إيقاف التحميل مؤقتاً.")
    else:
        await update.message.reply_text("لا يوجد تحميل جارٍ أو تم إيقافه بالفعل.")

async def resume(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in downloads and downloads[chat_id]["state"] == "paused":
        downloads[chat_id]["state"] = "downloading"
        await update.message.reply_text("تم استئناف التحميل.")
    else:
        await update.message.reply_text("لا يوجد تحميل متوقف مؤقتاً للاستئناف.")

async def cancel(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in downloads and downloads[chat_id]["state"] in ["downloading", "paused"]:
        downloads[chat_id]["state"] = "canceled"
        await update.message.reply_text("تم إلغاء التحميل.")
    else:
        await update.message.reply_text("لا يوجد تحميل جارٍ للإلغاء.")

async def status(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in downloads:
        progress = downloads[chat_id].get("progress", {})
        state = downloads[chat_id]["state"]
        msg = f"الحالة: {state}\n"
        if progress:
            downloaded = progress.get("downloaded_bytes", 0)
            total = progress.get("total_bytes") or progress.get("total_bytes_estimate", 0)
            if total:
                percentage = downloaded / total * 100
                msg += f"تم التحميل: {percentage:.2f}%"
            else:
                msg += f"تم تحميل: {downloaded} بايت"
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("لا يوجد تحميل جارٍ.")

def main():
    application = Application.builder().token(TOKEN).build()

    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CallbackQueryHandler(download_callback))
    application.add_handler(CommandHandler("pause", pause))
    application.add_handler(CommandHandler("resume", resume))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("status", status))

    # تشغيل التطبيق باستخدام webhook (مناسب لخادم Render)
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
    )

if __name__ == '__main__':
    main()
