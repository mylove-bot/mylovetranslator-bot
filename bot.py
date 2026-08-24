import os
import re
import time
import logging
from flask import Flask, request, jsonify
import requests

from deep_translator import GoogleTranslator


# ============================================================
# SETTINGS
# ============================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing.")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


# ============================================================
# LANGUAGES
# ============================================================

LANG_NAMES = {
    "en": "English",
    "ru": "Russian",
    "tr": "Turkish",
}

FLAGS = {
    "en": "🇬🇧",
    "ru": "🇷🇺",
    "tr": "🇹🇷",
}


# ============================================================
# SIMPLE LANGUAGE DETECTION
# ============================================================

ENGLISH_WORDS = {
    "the", "a", "an", "and", "or", "but",
    "is", "are", "was", "were",
    "i", "you", "he", "she", "it", "we", "they",
    "me", "my", "your", "his", "her", "our", "their",
    "this", "that", "these", "those",
    "what", "why", "when", "where", "who", "how",
    "hello", "hi", "hey",
    "yes", "no", "not",
    "please", "thanks", "thank",
    "good", "bad", "great",
    "need", "want", "like", "love",
    "money", "buy", "work", "group",
    "translate", "translation", "translator",
    "delete", "bot",
    "will", "can", "cannot",
    "think", "know", "have", "has",
    "do", "does", "did",
    "in", "on", "at", "to", "from", "for", "with",
    "of", "about", "because", "if",
}

TURKISH_WORDS = {
    "bir", "ve", "veya", "ama",
    "ben", "sen", "o", "biz", "siz", "onlar",
    "bu", "şu", "ne", "neden", "nasıl",
    "merhaba", "selam",
    "evet", "hayır",
    "çok", "iyi", "kötü",
    "para", "var", "yok",
    "istiyorum", "istemiyorum",
    "biliyorum", "bilmiyorum",
    "değil", "için", "ile",
    "olan", "gibi",
    "çeviri", "çevirmen",
}

RUSSIAN_WORDS = {
    "и", "или", "но",
    "я", "ты", "он", "она", "мы", "вы", "они",
    "это", "этот", "эта", "эти",
    "что", "почему", "как", "где", "когда",
    "да", "нет",
    "привет", "здравствуйте",
    "очень", "хорошо", "плохо",
    "деньги", "есть", "нет",
    "хочу", "хочешь",
    "нужно", "нужен",
    "знаю", "не знаю",
    "перевод", "переводчик",
    "группа",
}


def contains_cyrillic(text):
    return bool(re.search(r"[А-Яа-яЁё]", text))


def contains_turkish_chars(text):
    return bool(re.search(r"[çğıöşüÇĞİÖŞÜ]", text))


def contains_latin(text):
    return bool(re.search(r"[A-Za-z]", text))


def detect_language(text):
    """
    Detect only the three languages supported by the bot:
    English / Russian / Turkish.
    """

    clean = text.lower().strip()

    if not clean:
        return None

    # --------------------------------------------------------
    # Cyrillic = Russian
    # --------------------------------------------------------

    if contains_cyrillic(clean):
        logging.info("Cyrillic detected -> ru")
        return "ru"

    # --------------------------------------------------------
    # Turkish-specific letters
    # --------------------------------------------------------

    if contains_turkish_chars(clean):
        logging.info("Turkish characters detected -> tr")
        return "tr"

    # --------------------------------------------------------
    # Word scoring
    # --------------------------------------------------------

    words = re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]+", clean)

    en_score = 0
    tr_score = 0
    ru_score = 0

    for word in words:
        if word in ENGLISH_WORDS:
            en_score += 1

        if word in TURKISH_WORDS:
            tr_score += 1

        if word in RUSSIAN_WORDS:
            ru_score += 1

    logging.info(
        "Language scores: en=%s ru=%s tr=%s",
        en_score,
        ru_score,
        tr_score
    )

    highest = max(en_score, ru_score, tr_score)

    if highest > 0:
        if en_score == highest:
            logging.info("Common words detected -> en")
            return "en"

        if ru_score == highest:
            logging.info("Common words detected -> ru")
            return "ru"

        if tr_score == highest:
            logging.info("Common words detected -> tr")
            return "tr"

    # --------------------------------------------------------
    # Latin fallback
    #
    # If the message is written using Latin letters but
    # detection is uncertain, English is the safest fallback
    # for this bot.
    # --------------------------------------------------------

    if contains_latin(clean):
        logging.info("Latin fallback -> en")
        return "en"

    return None


# ============================================================
# TRANSLATION
# ============================================================

def translate_once(text, source, target):
    """
    One translation attempt.
    """

    logging.info(
        "deep-translator: %s -> %s",
        source,
        target
    )

    translator = GoogleTranslator(
        source=source,
        target=target
    )

    result = translator.translate(text)

    if result is None:
        raise RuntimeError("Translator returned None")

    result = str(result).strip()

    if not result:
        raise RuntimeError("Translator returned empty result")

    return result


def translate_text(text, source, target):
    """
    Retry translation several times.
    """

    # Don't translate to the same language.
    if source == target:
        return text

    last_error = None

    # Three attempts with small delays.
    for attempt in range(1, 4):

        try:

            result = translate_once(
                text,
                source,
                target
            )

            logging.info(
                "Translation result %s->%s: %r",
                source,
                target,
                result
            )

            return result

        except Exception as e:

            last_error = e

            logging.warning(
                "Translation error %s->%s attempt %s/3: %r",
                source,
                target,
                attempt,
                e
            )

            if attempt < 3:
                time.sleep(1.5 * attempt)

    logging.error(
        "Translation failed permanently %s->%s: %r",
        source,
        target,
        last_error
    )

    return None


# ============================================================
# TELEGRAM
# ============================================================

def send_message(chat_id, text, reply_to=None):

    data = {
        "chat_id": chat_id,
        "text": text,
    }

    if reply_to:
        data["reply_to_message_id"] = reply_to

    try:

        response = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json=data,
            timeout=20
        )

        logging.info(
            "Telegram sendMessage status: %s",
            response.status_code
        )

        logging.info(
            "Telegram response: %s",
            response.text
        )

        return response

    except Exception as e:

        logging.exception(
            "Telegram sendMessage error: %r",
            e
        )

        return None


# ============================================================
# TRANSLATION LOGIC
# ============================================================

def build_translation(text):

    source = detect_language(text)

    logging.info(
        "Detected language: %s",
        source
    )

    # Only these languages are supported.
    if source not in LANG_NAMES:

        logging.info(
            "Unsupported language: %s",
            source
        )

        return (
            "❌ I can only translate English, Russian and Turkish."
        )

    # --------------------------------------------------------
    # Target languages
    # --------------------------------------------------------

    targets = [
        lang
        for lang in LANG_NAMES
        if lang != source
    ]

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

        if translated:

            results.append(
                f"{FLAGS[target]} {translated}"
            )

        else:

            results.append(
                f"{FLAGS[target]} Translation failed."
            )

    return "\n".join(results)


# ============================================================
# FLASK
# ============================================================

@app.route("/", methods=["GET", "HEAD"])
def home():

    return "Translator bot is running.", 200


@app.route("/webhook", methods=["POST"])
def webhook():

    try:

        update = request.get_json(
            silent=True
        )

        if not update:
            return jsonify({"ok": True}), 200

        message = update.get("message")

        if not message:
            return jsonify({"ok": True}), 200

        # ----------------------------------------------------
        # Ignore bot messages
        # ----------------------------------------------------

        sender = message.get("from", {})

        if sender.get("is_bot"):
            return jsonify({"ok": True}), 200

        # ----------------------------------------------------
        # Text
        # ----------------------------------------------------

        text = message.get("text")

        if not text:
            return jsonify({"ok": True}), 200

        text = text.strip()

        if not text:
            return jsonify({"ok": True}), 200

        chat_id = message["chat"]["id"]

        message_id = message.get("message_id")

        logging.info("=" * 60)
        logging.info(
            "Incoming text: %r",
            text
        )

        # ----------------------------------------------------
        # Translate
        # ----------------------------------------------------

        reply = build_translation(text)

        logging.info(
            "Final reply: %r",
            reply
        )

        # ----------------------------------------------------
        # Send
        # ----------------------------------------------------

        send_message(
            chat_id=chat_id,
            text=reply,
            reply_to=message_id
        )

        logging.info("=" * 60)

        return jsonify({"ok": True}), 200

    except Exception as e:

        logging.exception(
            "Webhook error: %r",
            e
        )

        # Always return 200 to Telegram so it doesn't
        # repeatedly resend the same update.
        return jsonify({"ok": True}), 200


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            "10000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
)
