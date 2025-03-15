# استخدام صورة Python رسمية
FROM python:3.9-slim

# تعيين مجلد العمل
WORKDIR /app

# نسخ الملفات المطلوبة
COPY . .

# تثبيت المكتبات
RUN pip install --no-cache-dir -r requirements.txt

# تشغيل البوت
CMD ["python", "bot.py"]