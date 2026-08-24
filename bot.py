import os
import re
import time
import logging

import requests
from flask import Flask, request
from deep_translator import GoogleTranslator


# =========================================================
# CONFIG
# =========================================================

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN environment variable is missing.")

PORT = int(os.getenv("PORT", "10000"))

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)


# =========================================================
# LANGUAGES
# =========================================================

LANGUAGES = {
    "en": {"flag": "🇬🇧", "name": "English"},
    "ru": {"flag": "🇷🇺", "name": "Russian"},
    "tr": {"flag": "🇹🇷", "name": "Turkish"},
}


# =========================================================
# LANGUAGE DETECTION
# =========================================================

ENGLISH_WORDS = {
    "the", "and", "you", "your", "are", "is", "am",
    "i", "me", "my", "we", "they", "this", "that",
    "what", "why", "how", "where", "when", "who",
    "hello", "hi", "yes", "no", "not", "have",
    "has", "do", "does", "did", "will", "can",
    "just", "with", "for", "from", "but", "because",
    "please", "thanks", "thank", "game", "money",
    "need", "want", "think", "good", "bad",
    "love", "like", "hate", "sorry", "okay", "ok",
    "maybe", "really", "very", "now", "today",
    "tomorrow", "come", "go", "going", "get",
    "got", "make", "made", "know", "don't",
    "doesn't", "can't", "won't", "morning", "night"
}

TURKISH_WORDS = {
    "bir", "ve", "bu", "şu", "ben", "sen", "biz",
    "siz", "onlar", "için", "ile", "de", "da",
    "ne", "neden", "nasıl", "nerede", "kim",
    "evet", "hayır", "değil", "çok", "var", "yok",
    "ama", "çünkü", "teşekkür", "merhaba", "selam",
    "benim", "senin", "oyun", "para", "istiyorum",
    "gerekiyor", "bunu", "bana", "sana", "şimdi",
    "bugün", "yarın", "gel", "git", "tamam",
    "iyi", "kötü", "aşk", "seviyorum"
}

CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")


def detect_language(text):
    if not text or not text.strip():
        return None

    clean = re.sub(r"https?://\S+", " ", text)

    # Cyrillic -> Russian
    if len(CYRILLIC_RE.findall(clean)) > 0:
        logging.info("Cyrillic detected -> ru")
        return "ru"

    words = re.findall(
        r"[A-Za-zÇĞİÖŞÜçğıöşüА-Яа-яЁё']+",
        clean
    )

    if not words:
        return None

    lowered = [word.lower() for word in words]

    en_score = sum(
        1 for word in lowered
        if word in ENGLISH_WORDS
    )

    tr_score = sum(
        1 for word in lowered
        if word in TURKISH_WORDS
    )

    if any(char in text for char in "çğıöşüÇĞİÖŞÜ"):
        tr_score += 2

    logging.info(
        "Language scores: en=%s, tr=%s",
        en_score,
        tr_score
    )

    if en_score > tr_score and en_score > 0:
        logging.info("English detected -> en")
        return "en"

    if tr_score > en_score and tr_score > 0:
        logging.info("Turkish detected -> tr")
        return "tr"

    latin_count = sum(
        1
        for char in clean
        if (
            "a" <= char.lower() <= "z"
            or char in "çğıöşüÇĞİÖŞÜ"
        )
    )

    if latin_count >= 2:
        logging.info("Latin fallback -> en")
        return "en"

    return None


# =========================================================
# TARGET LANGUAGES
# =========================================================

def get_target_languages(source):
    if source == "en":
        return ["ru", "tr"]

    if source == "ru":
        return ["en", "tr"]

    if source == "tr":
        return ["en", "ru"]

    return []


# =========================================================
# METHOD 1
# deep-translator
# =========================================================

def translate_deep(text, source, target):
    logging.info(
        "deep-translator: %s -> %s",
        source,
        target
    )

    try:
        translator = GoogleTranslator(
            source=source,
            target=target
        )

        result = translator.translate(text)

        if result and result.strip():
            result = result.strip()

            logging.info(
                "deep-translator result %s->%s: %r",
                source,
                target,
                result
            )

            return result

    except Exception as exc:
        logging.warning(
            "deep-translator error %s->%s: %r",
            source,
            target,
            exc
        )

    return None


# =========================================================
# METHOD 2
# DIRECT GOOGLE TRANSLATE FALLBACK
# =========================================================

def translate_google_fallback(text, source, target):
    """
    Direct request to Google's translation endpoint.

    This is only used when deep-translator fails.
    No extra package or API key is required.
    """

    logging.info(
        "Google fallback: %s -> %s",
        source,
        target
    )

    url = "https://translate.googleapis.com/translate_a/single"

    params = {
        "client": "gtx",
        "sl": source,
        "tl": target,
        "dt": "t",
        "q": text
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        logging.info(
            "Google fallback HTTP status: %s",
            response.status_code
        )

        if response.status_code != 200:
            return None

        data = response.json()

        if not data or not data[0]:
            return None

        translated_parts = []

        for item in data[0]:
            if item and len(item) > 0 and item[0]:
                translated_parts.append(item[0])

        result = "".join(translated_parts).strip()

        if result:
            logging.info(
                "Google fallback result %s->%s: %r",
                source,
                target,
                result
            )

            return result

    except Exception as exc:
        logging.warning(
            "Google fallback error %s->%s: %r",
            source,
            target,
            exc
        )

    return None


# =========================================================
# SMART TRANSLATION
# =========================================================

def translate_text(text, source, target):
    """
    Smart translation:

    1. Try deep-translator.
    2. If it fails, wait briefly.
    3. Try deep-translator again.
    4. If it still fails, use direct Google fallback.
    """

    # Attempt 1
    result = translate_deep(
        text,
        source,
        target
    )

    if result:
        return result

    # Attempt 2
    logging.info(
        "Retrying deep-translator %s->%s",
        source,
        target
    )

    time.sleep(0.8)

    result = translate_deep(
        text,
        source,
        target
    )

    if result:
        return result

    # Fallback
    logging.info(
        "deep-translator failed. Using Google fallback %s->%s",
        source,
        target
    )

    time.sleep(0.3)

    result = translate_google_fallback(
        text,
        source,
        target
    )

    return result


# =========================================================
# TELEGRAM SEND
# =========================================================

def send_message(
    chat_id,
    text,
    reply_to_message_id=None
):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True
    }

    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id

    try:
        response = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json=payload,
            timeout=15
        )

        logging.info(
            "Telegram sendMessage status: %s",
            response.status_code
        )

        logging.info(
            "Telegram response: %s",
            response.text[:1000]
        )

        return response.ok

    except requests.RequestException as exc:
        logging.warning(
            "Telegram error: %s",
            exc
        )

        return False


# =========================================================
# BUILD REPLY
# =========================================================

def build_reply(text, source):

    targets = get_target_languages(source)

    if not targets:
        return None

    logging.info(
        "Detected language: %s",
        source
    )

    logging.info(
        "Target languages: %s",
        targets
    )

    results = []

    for target in targets:

        translated = translate_text(
            text,
            source,
            target
        )

        flag = LANGUAGES[target]["flag"]

        if translated:
            results.append(
                f"{flag} {translated}"
            )
        else:
            results.append(
                f"{flag} Translation failed."
            )

    return "\n".join(results)


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/", methods=["GET"])
def home():
    return "Translator bot is running.", 200


@app.route("/health", methods=["GET"])
def health():
    return "OK", 200


# =========================================================
# TELEGRAM WEBHOOK
# =========================================================

@app.route("/webhook", methods=["POST"])
def webhook():

    try:

        update = request.get_json(
            silent=True
        )

        if not update:
            return "OK", 200

        message = update.get("message")

        if not message:
            return "OK", 200

        text = message.get("text")

        if not text:
            return "OK", 200

        chat = message.get("chat", {})
        chat_id = chat.get("id")

        message_id = message.get(
            "message_id"
        )

        if not chat_id:
            return "OK", 200

        logging.info("=" * 50)

        logging.info(
            "Incoming text: %r",
            text
        )

        # Ignore commands
        if text.startswith("/"):
            logging.info(
                "Command ignored: %s",
                text
            )

            return "OK", 200

        # Detect language
        source = detect_language(text)

        logging.info(
            "Detected language: %s",
            source
        )

        if source is None:

            logging.info(
                "Unsupported language: %s",
                source
            )

            send_message(
                chat_id,
                "❌ I can only translate English, Russian and Turkish.",
                message_id
            )

            return "OK", 200

        # Translate
        reply = build_reply(
            text,
            source
        )

        if not reply:
            return "OK", 200

        logging.info(
            "Final reply: %r",
            reply
        )

        # Send
        send_message(
            chat_id,
            reply,
            message_id
        )

        logging.info("=" * 50)

        return "OK", 200

    except Exception as exc:

        logging.exception(
            "Webhook error: %s",
            exc
        )

        # Always return 200 to Telegram
        # to avoid repeated webhook delivery.
        return "OK", 200


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    logging.info("=" * 50)
    logging.info("Translator bot starting...")
    logging.info("TOKEN detected.")
    logging.info("Port: %s", PORT)
    logging.info("=" * 50)

    app.run(
        host="0.0.0.0",
        port=PORT
)
