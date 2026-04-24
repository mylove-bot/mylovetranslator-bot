import requests
import re
from flask import Flask, request
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor

# 🔥 Lingua + fallback
from lingua import Language, LanguageDetectorBuilder
from langdetect import detect

app = Flask(__name__)

TOKEN = "8170971907:AAE5CjJoTMyp6UGz9P0hGjm0uKJpXDrBKgSs"
URL = f"https://api.telegram.org/bot{TOKEN}"

# 🔥 إعداد Lingua
languages = [Language.ENGLISH, Language.TURKISH, Language.RUSSIAN, Language.ARABIC]
detector = LanguageDetectorBuilder.from_languages(*languages).build()

# ⚡ Threads
executor = ThreadPoolExecutor(max_workers=3)

# 🧠 Cache
cache = {}


# 🔍 كشف اللغة (Lingua + fallback)
def detect_languages(text):
    langs_found = set()

    words = text.split()

    for word in words:
        try:
            lang = detector.detect_language_of(word)

            if lang == Language.TURKISH:
                langs_found.add("tr")
            elif lang == Language.RUSSIAN:
                langs_found.add("ru")
            elif lang == Language.ARABIC:
                langs_found.add("ar")
            else:
                langs_found.add("en")

        except:
            continue

    # 🔥 fallback لو فشل
    if not langs_found:
        try:
            lang = detect(text)
            if lang.startswith("tr"):
                langs_found.add("tr")
            elif lang.startswith("ru"):
                langs_found.add("ru")
            elif lang.startswith("ar"):
                langs_found.add("ar")
            else:
                langs_found.add("en")
        except:
            langs_found.add("en")

    return list(langs_found)


# ⚡ ترجمة مع cache
def translate_cached(text, target):
    key = f"{text}_{target}"

    if key in cache:
        return cache[key]

    try:
        result = GoogleTranslator(source="auto", target=target).translate(text)
        cache[key] = result
        return result
    except:
        return text


# ⚡ async wrapper
def translate_async(text, target):
    return executor.submit(lambda: translate_cached(text, target))


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

    langs = detect_languages(text)

    futures = []
    used_targets = set()

    # 🎯 تحديد الترجمات بدون تكرار
    if "en" in langs:
        used_targets.update(["tr", "ru"])

    if "tr" in langs:
        used_targets.update(["en", "ru"])

    if "ru" in langs:
        used_targets.update(["en", "tr"])

    if "ar" in langs:
        used_targets.update(["en", "tr", "ru"])

    # 🚀 تشغيل الترجمة
    for target in used_targets:
        futures.append((target, translate_async(text, target)))

    # ⏳ جمع النتائج
    results = []
    flags = {"en": "🇬🇧", "tr": "🇹🇷", "ru": "🇷🇺"}

    for target, future in futures:
        try:
            result = future.result()
            results.append(f"{flags.get(target, '')} {result}")
        except:
            pass

    reply = "\n".join(results)

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
