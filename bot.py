import requests
from flask import Flask, request
from deep_translator import GoogleTranslator

app = Flask(__name__)

# 🔴 التوكن
TOKEN = "8170971907:AAE5CjJoTMyp6UGzP0hGjm0uKJpXDrBKgSs"
URL = f"https://api.telegram.org/bot{TOKEN}"


# 🌍 كشف اللغة (ثابت وأبسط)
def detect_lang(text):
    try:
        return GoogleTranslator(source="auto", target="en").detect(text)
    except:
        return "en"


# 🌐 ترجمة واضحة بدون auto في الترجمة نفسها
def translate(text, src, target):
    try:
        return GoogleTranslator(source=src, target=target).translate(text)
    except:
        return text


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

    # 🌍 الترجمة حسب اللغة
    if lang.startswith("en"):
        tr = translate(text, "en", "tr")
        ru = translate(text, "en", "ru")
        reply = f"🇹🇷 {tr}\n🇷🇺 {ru}"

    elif lang.startswith("tr"):
        en = translate(text, "tr", "en")
        ru = translate(text, "tr", "ru")
        reply = f"🇬🇧 {en}\n🇷🇺 {ru}"

    elif lang.startswith("ru"):
        en = translate(text, "ru", "en")
        tr = translate(text, "ru", "tr")
        reply = f"🇬🇧 {en}\n🇹🇷 {tr}"

    else:
        en = translate(text, "auto", "en")
        tr = translate(text, "auto", "tr")
        ru = translate(text, "auto", "ru")
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
