import os
import requests
import re
from flask import Flask, request
from deep_translator import GoogleTranslator

TOKEN = os.getenv("TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

session = requests.Session()


# 🔍 تحديد اللغة بشكل ذكي
def get_lang(text):
    try:
        # عربي
        if re.search(r'[\u0600-\u06FF]', text):
            return "ar"

        # روسي
        if re.search(r'[\u0400-\u04FF]', text):
            return "ru"

        # إنجليزي / لاتيني
        if re.search(r'[a-zA-Z]', text):
            return "en"

        return "en"

    except:
        return "en"


# ⚡ ترجمة
def translate(text, target):
    try:
        return GoogleTranslator(source="auto", target=target).translate(text)
    except Exception as e:
        print("Translate error:", e)
        return text


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)

    if not data:
        return "ok", 200

    try:
        message = data.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")

        if not text or not chat_id:
            return "ok", 200

        lang = get_lang(text)

        # 🇬🇧 English → TR + RU
        if lang == "en":
            tr = translate(text, "tr")
            ru = translate(text, "ru")
            reply = f"""🇹🇷 {tr}
🇷🇺 {ru}"""

        # 🇹🇷 Turkish → EN + RU
        elif lang == "tr":
            en = translate(text, "en")
            ru = translate(text, "ru")
            reply = f"""🇬🇧 {en}
🇷🇺 {ru}"""

        # 🇷🇺 Russian → EN + TR
        elif lang == "ru":
            en = translate(text, "en")
            tr = translate(text, "tr")
            reply = f"""🇬🇧 {en}
🇹🇷 {tr}"""

        # 🌍 fallback
        else:
            en = translate(text, "en")
            tr = translate(text, "tr")
            ru = translate(text, "ru")
            reply = f"""🇬🇧 {en}
🇹🇷 {tr}
🇷🇺 {ru}"""

        # 💬 reply على نفس الرسالة
        requests.get(
            f"{URL}/sendMessage",
            params={
                "chat_id": chat_id,
                "text": reply,
                "reply_to_message_id": message_id
            }
        )

    except Exception as e:
        print("ERROR:", e)

    return "ok", 200


@app.route("/")
def home():
    return "Bot is running", 200
