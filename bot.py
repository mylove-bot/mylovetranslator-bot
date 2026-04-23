import requests
import re
from flask import Flask, request
from langdetect import detect, DetectorFactory
from deep_translator import GoogleTranslator

app = Flask(__name__)

# 🔴 التوكن (كما هو)
TOKEN = "8170971907:AAE5CjJoTMyp6UGzP0hGjm0uKJpXDrBKgSs"
URL = f"https://api.telegram.org/bot{TOKEN}"

DetectorFactory.seed = 0


# 🔍 كشف اللغة (EN / TR / RU فقط)
def get_lang(text):
    try:
        text = text.strip()

        # 🇷🇺 روسي
        if re.search(r'[\u0400-\u04FF]', text):
            return "ru"

        # 🇹🇷 تركي
        if re.search(r'[ğüşöçıİĞÜŞÖÇ]', text):
            return "tr"

        # 🇬🇧 إنجليزي
        if re.fullmatch(r'[A-Za-z0-9\s.,!?\'"()-]+', text):
            return "en"

        # 🧠 fallback
        lang = detect(text)

        if lang.startswith("ru"):
            return "ru"
        if lang.startswith("tr"):
            return "tr"

        return "en"

    except:
        return "en"


# ⚡ ترجمة
def translate(text, target):
    try:
        return GoogleTranslator(source="auto", target=target).translate(text)
    except:
        return text


# 📩 إرسال رسالة (مع reply اختياري)
def send_message(chat_id, text, reply_to=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_to:
        payload["reply_to_message_id"] = reply_to

    res = requests.post(
        f"{URL}/sendMessage",
        data=payload,
        timeout=5
    )
    return res.json()


# ✏️ تعديل الرسالة
def edit_message(chat_id, message_id, text):
    requests.post(
        f"{URL}/editMessageText",
        data={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text
        },
        timeout=5
    )


# 💬 webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    message = data.get("message") or data.get("edited_message")

    if not message:
        return "ok", 200

    text = message.get("text")
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")

    if not text or not chat_id:
        return "ok", 200

    lang = get_lang(text)

    # ⏳ رسالة أولية (مع reply)
    temp = send_message(chat_id, "⏳ Translating...", message_id)

    try:
        temp_id = temp["result"]["message_id"]
    except:
        temp_id = None

    # 🧠 الترجمة
    if lang == "en":
        reply = f"🇹🇷 {translate(text,'tr')}\n🇷🇺 {translate(text,'ru')}"

    elif lang == "tr":
        reply = f"🇬🇧 {translate(text,'en')}\n🇷🇺 {translate(text,'ru')}"

    elif lang == "ru":
        reply = f"🇬🇧 {translate(text,'en')}\n🇹🇷 {translate(text,'tr')}"

    else:
        reply = (
            f"🇬🇧 {translate(text,'en')}\n"
            f"🇹🇷 {translate(text,'tr')}\n"
            f"🇷🇺 {translate(text,'ru')}"
        )

    # ✨ تعديل الرسالة إلى الترجمة
    if temp_id:
        edit_message(chat_id, temp_id, reply)

    return "ok", 200


# 🏠 اختبار السيرفر
@app.route("/")
def home():
    return "Bot is running 🚀", 200


# 🚀 تشغيل
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
