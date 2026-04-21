import os
import requests
from langdetect import detect
from flask import Flask, request

TOKEN = os.getenv("TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

session = requests.Session()


# 🔥 الترجمة (إجبارية)
def translate(text, source, target):
    try:
        url = "https://libretranslate.com/translate"

        payload = {
            "q": text,
            "source": source,
            "target": target,
            "format": "text"
        }

        r = session.post(url, json=payload, timeout=10)
        data = r.json()

        translated = data.get("translatedText")

        # إذا ما في ترجمة حقيقية
        if not translated:
            return "⚠️ translation failed"

        return translated

    except Exception as e:
        print("Translate error:", e)
        return "⚠️ translation failed"


# 🔥 كشف اللغة
def get_lang(text):
    try:
        return detect(text)
    except Exception:
        return "en"


# 🔥 webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)

    if not data:
        return "ok", 200

    try:
        message = data.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")

        if not text or not chat_id:
            return "ok", 200

        lang = get_lang(text)

        # 🇬🇧 English
        if lang.startswith("en"):
            tr = translate(text, "en", "tr")
            ru = translate(text, "en", "ru")
            reply = f"🇹🇷 {tr}\n🇷🇺 {ru}"

        # 🇹🇷 Turkish
        elif lang.startswith("tr"):
            en = translate(text, "tr", "en")
            ru = translate(text, "tr", "ru")
            reply = f"🇬🇧 {en}\n🇷🇺 {ru}"

        # 🇷🇺 Russian
        elif lang.startswith("ru"):
            en = translate(text, "ru", "en")
            tr = translate(text, "ru", "tr")
            reply = f"🇬🇧 {en}\n🇹🇷 {tr}"

        # 🌍 any other language
        else:
            en = translate(text, "auto", "en")
            tr = translate(text, "auto", "tr")
            ru = translate(text, "auto", "ru")
            reply = f"🇬🇧 {en}\n🇹🇷 {tr}\n🇷🇺 {ru}"

        # 🔥 send message
        requests.get(
            f"{URL}/sendMessage",
            params={
                "chat_id": chat_id,
                "text": reply
            }
        )

    except Exception as e:
        print("ERROR:", e)

    return "ok", 200


# 🔥 home route
@app.route("/")
def home():
    return "Bot is running", 200
