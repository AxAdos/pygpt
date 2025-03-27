import os
import threading
import time
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import yt_dlp

# إعداد التوكن والويب هوك (يفضل قراءتهم من متغيرات البيئة)
TOKEN = "7336372322:AAEtIUcY6nNEEGZzIMjJdfYMTAMsLpTSpzk"
WEBHOOK_URL = "https://api.render.com/deploy/srv-cvbnb9tds78s73ampivg?key=bVahe5gy2Nw"
PORT = int(os.getenv("PORT", 10000))

# بنية لتخزين حالة التحميل لكل محادثة (chat_id)
downloads = {}  
# downloads[chat_id] = {
#   "thread": <thread>,
#   "state": "downloading" / "paused" / "canceled" / "completed",
#   "progress": { ... },  # آخر معلومات التقدم
#   "file": "path/to/downloaded/file"
# }

def progress_hook_factory(chat_id):
    def progress_hook(d):
        if d.get('status') in ['downloading', 'finished']:
            downloads[chat_id]['progress'] = d  # تحديث بيانات التقدم
            # التحقق من أمر الإيقاف المؤقت: إذا كان المستخدم قد طلب الإيقاف، نتوقف عن التقدم مؤقتاً
            while downloads[chat_id]['state'] == 'paused':
                time.sleep(1)
            # التحقق من الإلغاء
            if downloads[chat_id]['state'] == 'canceled':
                raise Exception("تم إلغاء التحميل من قبل المستخدم")
    return progress_hook

def download_video(chat_id, url, update: Update, context: CallbackContext):
    # تعيين الحالة الابتدائية
    downloads[chat_id] = {
        "state": "downloading",
        "progress": {},
        "file": None,
        "thread": threading.current_thread()
    }
    ydl_opts = {
        'outtmpl': f'{chat_id}_%(id)s.%(ext)s',  # حفظ الملف مع اسم مبسط يحتوي على chat_id
        'progress_hooks': [progress_hook_factory(chat_id)],
        'retries': 3,
        'continuedl': True,  # محاولة استئناف التحميل إذا كان هناك جزء موجود
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # عند الانتهاء من التحميل، يتم تغيير الحالة إلى completed
            downloads[chat_id]['state'] = 'completed'
            filename = ydl.prepare_filename(info)
            downloads[chat_id]['file'] = filename
            # إرسال الفيديو إلى المستخدم
            context.application.create_task(send_video(chat_id, filename, update, context))
    except Exception as e:
        # إذا تم الإلغاء أو حدث خطأ
        context.application.create_task(context.bot.send_message(chat_id, text=f"فشل التحميل: {e}"))
    finally:
        # بعد الانتهاء، يتم حذف الملف المؤقت إذا وُجد
        if downloads.get(chat_id, {}).get('file') and os.path.exists(downloads[chat_id]['file']):
            try:
                os.remove(downloads[chat_id]['file'])
            except Exception as ex:
                print(f"خطأ أثناء حذف الملف: {ex}")
        # تنظيف السجل الخاص بالتحميل
        if chat_id in downloads:
            del downloads[chat_id]

async def send_video(chat_id, file_path, update: Update, context: CallbackContext):
    try:
        # إرسال الفيديو مع التأكد من أن حجم الملف مناسب
        await context.bot.send_video(chat_id=chat_id, video=InputFile(file_path))
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"حدث خطأ أثناء إرسال الفيديو: {e}")

# أمر /start: رسالة ترحيبية لطلب رابط الفيديو
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("أرسل رابط الفيديو للتحميل.")

# عندما يتم إرسال رابط فيديو (أي رسالة نصية ليست أمر)
async def handle_message(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    url = update.message.text.strip()
    # يمكن إضافة فحص بسيط للتأكد من أن النص يبدو كرابط
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("يرجى إرسال رابط فيديو صحيح.")
        return
    await update.message.reply_text("جاري بدء عملية التحميل...")

    # بدء عملية التحميل في Thread منفصل لتجنب حجب الـ event loop
    download_thread = threading.Thread(target=download_video, args=(chat_id, url, update, context))
    download_thread.start()

# أمر /pause لإيقاف التحميل مؤقتاً
async def pause(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in downloads and downloads[chat_id]['state'] == 'downloading':
        downloads[chat_id]['state'] = 'paused'
        await update.message.reply_text("تم إيقاف التحميل مؤقتاً.")
    else:
        await update.message.reply_text("لا يوجد تحميل جارٍ أو تم إيقافه بالفعل.")

# أمر /resume لاستئناف التحميل
async def resume(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in downloads and downloads[chat_id]['state'] == 'paused':
        downloads[chat_id]['state'] = 'downloading'
        await update.message.reply_text("تم استئناف التحميل.")
    else:
        await update.message.reply_text("لا يوجد تحميل متوقف مؤقتاً للاستئناف.")

# أمر /cancel لإلغاء التحميل
async def cancel(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in downloads and downloads[chat_id]['state'] in ['downloading', 'paused']:
        downloads[chat_id]['state'] = 'canceled'
        await update.message.reply_text("تم إلغاء التحميل.")
    else:
        await update.message.reply_text("لا يوجد تحميل جارٍ للإلغاء.")

# أمر /status لعرض حالة التحميل
async def status(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in downloads:
        progress = downloads[chat_id].get('progress', {})
        state = downloads[chat_id]['state']
        msg = f"الحالة: {state}\n"
        if progress:
            downloaded = progress.get('downloaded_bytes', 0)
            total = progress.get('total_bytes') or progress.get('total_bytes_estimate', 0)
            if total:
                percentage = downloaded / total * 100
                msg += f"تم التحميل: {percentage:.2f}%"
            else:
                msg += f"تم تحميل: {downloaded} بايت"
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("لا يوجد تحميل جارٍ.")

# إنشاء التطبيق وإضافة المعالجات
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("pause", pause))
application.add_handler(CommandHandler("resume", resume))
application.add_handler(CommandHandler("cancel", cancel))
application.add_handler(CommandHandler("status", status))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# تشغيل التطبيق باستخدام webhook
application.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
)
