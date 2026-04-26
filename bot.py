import requests
from flask import Flask, request
from deep_translator import GoogleTranslator, LibreTranslator

app = Flask(__name__)

TOKEN = "8170971907:AAE5CjJoTMyp6UGzP0hGjm0uKJpXDrBKgSs"
URL = f"https://api.telegram.org/bot{TOKEN}"

ACCEPTED_LANGS = {"ar", "en", "tr", "ru"}

def detect_language(text):
    try:
        response = requests.post(
            "https://libretranslate.de/detect",
            data={"q": text},
            timeout=10
        )
        result = response.json()
        if result and isinstance(result, list):
            return result[0]["language"]
        return None
    except Exception as e:
        print("Language detection error:", e)
        return None

def translate(text, target):
    try:
        return GoogleTranslator(source='auto', target=target).translate(text)
    except Exception as e:
        print("GoogleTranslator error:", e)
        try:
            return LibreTranslator(source='auto', target=target).translate(text)
        except Exception as e2:
            print("LibreTranslator error:", e2)
            return f"خطأ بالترجمة: {e2}"

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

    src_lang = detect_language(text)
    print("Detected language:", src_lang)

    if src_lang not in ACCEPTED_LANGS:
        print(f"Unsupported or unknown language: {src_lang}, ignoring.")
        return "ok", 200

    output_langs = {"en", "tr", "ru"} - {src_lang}

    flags = {"en": "🇬🇧", "tr": "🇹🇷", "ru": "🇷🇺"}

    translations = []
    for lang in output_langs:
        translated = translate(text, lang)
        translations.append(f"{flags[lang]} {translated}")

    reply = "\n".join(translations)

    requests.post(
        f"{URL}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": reply,
            "reply_to_message_id": message_id
        }
    )

    return "ok", 200

@app.route("/")
def home():
    return "Bot is running", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
