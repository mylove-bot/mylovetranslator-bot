import requests
from flask import Flask, request
from deep_translator import GoogleTranslator

app = Flask(__name__)

# 🔴 التوكن
TOKEN = "8170971907:AAE5CjJoTMyp6UGzP0hGjm0uKJpXDrBKgSs"
URL = f"https://api.telegram.org/bot{TOKEN}"


# 🌐 ترجمة عامة (auto)
def translate(text, target):
    try:
        return GoogleTranslator(source="auto", target=target).translate(text)
    except:
        return text


# 🔍 كشف لغة بسيط وثابت
def detect_lang(text):
    if any('\u0600' <= c <= '\u06FF' for c in text):
        return "ar"
    elif any('\u0400' <= c <= '\u04FF' for c in text):
        return "ru"
    elif any(c in "ğüşöçıİ" for c in text.lower()):
        return "tr"
    else:
        return "en"


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

    # 🔍 كشف اللغة
    lang = detect_lang(text)

    # 🌍 الترجمات
    en = translate(text, "en")
    tr = translate(text, "tr")
    ru = translate(text, "ru")

    # 💬 الرد حسب اللغة
    if lang == "en":
        reply = f"🇹🇷 {tr}\n🇷🇺 {ru}"

    elif lang == "tr":
        reply = f"🇬🇧 {en}\n🇷🇺 {ru}"

    elif lang == "ru":
        reply = f"🇬🇧 {en}\n🇹🇷 {tr}"

    else:
        reply = f"🇬🇧 {en}\n🇹🇷 {tr}\n🇷🇺 {ru}"

    # 🚀 إرسال الرد
    requests.post(
        f"{URL}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": reply,
            "reply_to_message_id": message_id
        }
    )

    return "ok", 200


# 🏠 اختبار السيرفر
@app.route("/")
def home():
    return "Bot is running", 200


# 🚀 تشغيل
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
