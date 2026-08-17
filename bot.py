import os
import re
import requests
from flask import Flask, request
from deep_translator import GoogleTranslator, LibreTranslator
from langdetect import detect, LangDetectException

app = Flask(__name__)

# =========================================================
# CONFIG
# =========================================================

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN environment variable is missing")

URL = f"https://api.telegram.org/bot{TOKEN}"

ACCEPTED_LANGS = {"ar", "en", "tr", "ru"}

FLAGS = {
    "en": "🇬🇧",
    "tr": "🇹🇷",
    "ru": "🇷🇺"
}

# ترتيب ثابت للترجمات
LANGUAGE_ORDER = ["en", "tr", "ru"]


# =========================================================
# LANGUAGE DETECTION
# =========================================================

def looks_like_english(text):
    """
    يساعد مع الجمل الإنجليزية القصيرة التي قد تقوم
    langdetect بتصنيفها بشكل خاطئ مثل so / nl / fi.
    """

    text_lower = text.lower().strip()

    english_words = {
        "the", "a", "an", "and", "or", "but",
        "hello", "hi", "hey", "how", "are",
        "you", "your", "what", "where", "when",
        "why", "who", "this", "that", "is",
        "am", "are", "was", "were", "have",
        "has", "do", "does", "did", "can",
        "could", "would", "should", "will",
        "good", "today", "tomorrow", "yesterday",
        "please", "thank", "thanks", "yes", "no",
        "love", "like", "want", "need"
    }

    words = re.findall(r"[a-zA-Z]+", text_lower)

    if not words:
        return False

    matches = sum(1 for word in words if word in english_words)

    # إذا وجدنا كلمة إنجليزية واضحة
    if matches >= 1:
        return True

    # الجمل الإنجليزية الطويلة المكتوبة فقط بالحروف الإنجليزية
    if len(words) >= 4:
        return True

    return False


def detect_language(text):
    """
    اكتشاف اللغة مع بعض الحماية من أخطاء langdetect.
    """

    # العربية: اكتشاف مباشر
    if re.search(r"[\u0600-\u06FF]", text):
        return "ar"

    # السيريلية: غالبًا روسي بالنسبة للغات التي ندعمها
    if re.search(r"[\u0400-\u04FF]", text):
        try:
            detected = detect(text)

            if detected == "ru":
                return "ru"

            # إذا كانت سيريلية ولكن langdetect أعطى لغة
            # أخرى، نتركها كما هي ليتم رفضها.
            return detected

        except LangDetectException:
            return None

    try:
        detected = detect(text)
        print("langdetect result:", detected)

        if detected in ACCEPTED_LANGS:
            return detected

        # langdetect أحيانًا يخطئ في الجمل الإنجليزية القصيرة.
        if looks_like_english(text):
            print("Using English fallback")
            return "en"

        return detected

    except LangDetectException as e:
        print("Language detection error:", e)

        # محاولة أخيرة للنصوص الإنجليزية
        if looks_like_english(text):
            print("Using English fallback after detection error")
            return "en"

        return None


# =========================================================
# TRANSLATION
# =========================================================

def translate(text, target):
    """
    يحاول Google Translator أولًا.
    إذا فشل، يجرب LibreTranslator.
    """

    try:
        result = GoogleTranslator(
            source="auto",
            target=target
        ).translate(text)

        print(f"Google translation to {target}: OK")
        return result

    except Exception as e:
        print(f"GoogleTranslator error ({target}):", repr(e))

    try:
        result = LibreTranslator(
            source="auto",
            target=target
        ).translate(text)

        print(f"Libre translation to {target}: OK")
        return result

    except Exception as e2:
        print(f"LibreTranslator error ({target}):", repr(e2))
        return None


# =========================================================
# SEND TELEGRAM MESSAGE
# =========================================================

def send_message(chat_id, text, message_id=None):
    """
    إرسال الرد إلى Telegram مع طباعة النتيجة كاملة.
    """

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if message_id:
        payload["reply_to_message_id"] = message_id

    try:
        response = requests.post(
            f"{URL}/sendMessage",
            data=payload,
            timeout=20
        )

        print("Telegram sendMessage status:", response.status_code)
        print("Telegram sendMessage response:", response.text)

        return response

    except Exception as e:
        print("Telegram sendMessage request error:", repr(e))
        return None


# =========================================================
# WEBHOOK
# =========================================================

@app.route("/webhook", methods=["POST"])
def webhook():

    try:
        data = request.get_json(force=True)
    except Exception as e:
        print("Invalid JSON:", repr(e))
        return "ok", 200

    # يدعم الرسائل العادية والمعدلة
    message = (
        data.get("message")
        or data.get("edited_message")
    )

    if not message:
        return "ok", 200

    text = message.get("text")

    chat = message.get("chat", {})
    chat_id = chat.get("id")

    message_id = message.get("message_id")

    if not text or not chat_id:
        return "ok", 200

    print("========================================")
    print("Incoming message:", repr(text))
    print("Chat ID:", chat_id)

    # -----------------------------------------------------
    # Detect language
    # -----------------------------------------------------

    src_lang = detect_language(text)

    print("Detected language:", src_lang)

    if src_lang not in ACCEPTED_LANGS:
        print(
            f"Unsupported or unknown language: "
            f"{src_lang}, ignoring."
        )
        print("========================================")
        return "ok", 200

    # -----------------------------------------------------
    # Determine target languages
    # -----------------------------------------------------

    output_langs = [
        lang
        for lang in LANGUAGE_ORDER
        if lang != src_lang
    ]

    print("Target languages:", output_langs)

    # -----------------------------------------------------
    # Translate
    # -----------------------------------------------------

    translations = []

    for lang in output_langs:

        translated = translate(text, lang)

        if translated is None:
            translated = "Translation failed."

        translations.append(
            f"{FLAGS[lang]} {translated}"
        )

    # -----------------------------------------------------
    # Build reply
    # -----------------------------------------------------

    reply = "\n".join(translations)

    print("Final reply:")
    print(reply)

    # -----------------------------------------------------
    # Send reply
    # -----------------------------------------------------

    send_message(
        chat_id=chat_id,
        text=reply,
        message_id=message_id
    )

    print("========================================")

    return "ok", 200


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/", methods=["GET"])
def home():
    return "Bot is running", 200


# =========================================================
# LOCAL RUN
# =========================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
)
