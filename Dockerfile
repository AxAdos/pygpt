FROM python:3.11-slim

# إنشاء مستخدم جديد
RUN useradd -m myuser

# تغيير صاحب المجلد
WORKDIR /app
RUN chown -R myuser:myuser /app

# التبديل إلى المستخدم الجديد
USER myuser

# تثبيت المتطلبات
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# نسخ الكود
COPY . .

# تشغيل البوت
CMD ["python", "pygpt.py"]
