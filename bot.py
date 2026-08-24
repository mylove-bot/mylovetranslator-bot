import os
import re
import json
import time
import requests

from flask import Flask, request
from langdetect import detect, LangDetectException


app = Flask(__name__)


# =========================================================
# CONFIG
# =========================================================

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN environment variable is missing")

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}"

SUPPORTED_LANGS = {"en", "ru", "tr"}

FLAGS = {
    "en": "🇬🇧",
    "ru": "🇷🇺",
    "tr": "🇹🇷"
}

LANGUAGE_ORDER = ["en", "ru", "tr"]


# =========================================================
# SESSION
# =========================================================

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/139.0 Safari/537.36"
    )
})


# =========================================================
# COMMON WORDS
# =========================================================

ENGLISH_COMMON = {
    "a", "an", "the",
    "i", "me", "my",
    "you", "your",
    "he", "she", "it",
    "we", "us", "they", "them",

    "is", "am", "are",
    "was", "were",
    "be", "been", "being",

    "do", "does", "did",
    "have", "has", "had",

    "can", "could",
    "will", "would",
    "should", "shall",
    "may", "might", "must",

    "and", "or", "but",
    "if", "then",
    "because", "so",
    "for", "from", "with",
    "without", "about",
    "to", "of", "in",
    "on", "at", "by",

    "what", "why", "who",
    "where", "when", "how",
    "which",

    "this", "that",
    "these", "those",
    "here", "there",

    "hello", "hi", "hey",
    "bye", "goodbye",

    "yes", "yeah",
    "no", "nope",

    "okay", "ok",
    "good", "bad",
    "great", "nice",
    "fine",

    "please",
    "thanks", "thank",
    "sorry",

    "still", "some",
    "any", "more", "less",
    "very", "really",
    "just", "only",
    "also", "again",
    "already",

    "mistake", "mistakes",
    "problem", "problems",
    "thing", "things",

    "love", "like",
    "want", "need",
    "know", "think",
    "feel", "see",
    "look", "come",
    "go", "wait",
    "stop", "start",

    "test",
    "testing",
    "welcome",
    "help",
    "done",

    "morning",
    "evening",
    "night",
    "today",
    "tomorrow",
    "yesterday"
}


RUSSIAN_COMMON = {
    "я", "ты", "он", "она", "оно",
    "мы", "вы", "они",

    "мне", "тебе", "ему", "ей",
    "нам", "вам", "им",

    "мой", "моя", "мое", "мои",
    "твой", "твоя", "твое", "твои",

    "да", "нет",
    "привет", "пока",

    "что", "кто",
    "где", "куда", "откуда",
    "когда", "как",
    "почему", "зачем",
    "какой", "какая", "какие",

    "это", "этот",
    "эта", "эти",
    "тот", "та",
    "то", "те",

    "есть", "был",
    "была", "были",
    "будет", "буду",
    "быть",

    "можно", "нельзя",
    "нужно", "нужен",
    "надо",

    "хочу", "хочешь",
    "хотеть",

    "не", "ни",
    "и", "или", "но",
    "если", "потому",

    "здесь", "там",
    "сейчас",
    "сегодня", "завтра",
    "вчера",
    "снова", "опять",
    "всегда", "никогда",

    "хорошо", "плохо",
    "спасибо", "пожалуйста",
    "извини",

    "люблю", "нравится",
    "знаю", "думаю",
    "вижу", "смотри",
    "иди", "жди", "стой"
}


TURKISH_COMMON = {
    "ben", "sen", "o",
    "biz", "siz", "onlar",

    "bana", "sana",
    "beni", "seni",
    "benim", "senin",

    "bir", "bu", "şu",
    "bunlar", "şunlar",

    "evet", "hayır",
    "merhaba", "selam",

    "ne", "neden",
    "niye", "niçin",
    "kim", "kime", "kimi",
    "nerede", "nereye",
    "nereden",
    "nasıl", "hangi",

    "var", "yok",
    "değil",
    "oldu", "oluyor",
    "olacak",

    "ve", "veya", "ama",
    "çünkü", "eğer",
    "için", "ile", "gibi",

    "burada", "orada",
    "şimdi", "bugün",
    "yarın", "dün",
    "yine", "asla",

    "iyi", "kötü",
    "güzel",
    "tamam", "peki",

    "teşekkür",
    "teşekkürler",
    "lütfen", "özür",

    "seviyorum",
    "istiyorum",
    "biliyorum",
    "düşünüyorum",

    "gel", "git",
    "bekle", "dur"
}


# =========================================================
# TEXT HELPERS
# =========================================================

def normalize(text):
    return text.lower().strip()


def words(text):
    return re.findall(
        r"[A-Za-zÀ-ÿĞÜŞİÖÇğüşıöçА-Яа-яЁё]+",
        normalize(text)
    )


# =========================================================
# LANGUAGE DETECTION
# =========================================================

def detect_language(text):

    text = normalize(text)
    word_list = words(text)

    if not word_list:
        return None

    SHORT_ENGLISH = {
        "test",
        "testing",
        "hello",
        "hi",
        "hey",
        "ok",
        "okay",
        "yes",
        "yeah",
        "no",
        "nope",
        "thanks",
        "thank",
        "sorry",
        "bye",
        "good",
        "bad",
        "great",
        "nice",
        "fine",
        "love",
        "help",
        "stop",
        "wait",
        "go",
        "come",
        "start",
        "done",
        "welcome"
    }

    if text in SHORT_ENGLISH:
        print("Known short English word -> en")
        return "en"

    # Russian
    if re.search(r"[А-Яа-яЁё]", text):
        print("Cyrillic detected -> ru")
        return "ru"

    # Turkish
    if re.search(r"[ğüşıöçĞÜŞİÖÇ]", text):
        print("Turkish characters detected -> tr")
        return "tr"

    en_score = sum(
        1 for word in word_list
        if word in ENGLISH_COMMON
    )

    ru_score = sum(
        1 for word in word_list
        if word in RUSSIAN_COMMON
    )

    tr_score = sum(
        1 for word in word_list
        if word in TURKISH_COMMON
    )

    print(
        f"Common scores: "
        f"en={en_score}, "
        f"ru={ru_score}, "
        f"tr={tr_score}"
    )

    scores = {
        "en": en_score,
        "ru": ru_score,
        "tr": tr_score
    }

    best_lang = max(scores, key=scores.get)
    best_score = scores[best_lang]

    sorted_scores = sorted(
        scores.values(),
        reverse=True
    )

    if best_score > 0:

        if (
            len(sorted_scores) < 2
            or sorted_scores[0] > sorted_scores[1]
        ):
            print(
                f"Common words detected -> {best_lang}"
            )
            return best_lang

    try:

        detected = detect(text)

        print(
            "langdetect result:",
            detected
        )

        if detected in SUPPORTED_LANGS:
            return detected

    except LangDetectException as e:

        print(
            "langdetect error:",
            repr(e)
        )

    # Latin text fallback
    if re.search(r"[A-Za-z]", text):

        print(
            "Latin fallback -> en"
        )

        return "en"

    return None


# =========================================================
# GOOGLE TRANSLATE GTX
# =========================================================

def translate_google(text, source, target):

    print(
        f"Google GTX translation: "
        f"{source} -> {target}"
    )

    url = "https://translate.googleapis.com/translate_a/single"

    params = {
        "client": "gtx",
        "sl": source,
        "tl": target,
        "dt": "t",
        "ie": "UTF-8",
        "oe": "UTF-8",
        "q": text
    }

    try:

        response = session.get(
            url,
            params=params,
            timeout=20
        )

        print(
            f"Google HTTP status "
            f"{source}->{target}:",
            response.status_code
        )

        if response.status_code != 200:

            print(
                "Google HTTP error:",
                response.text[:500]
            )

            return None

        try:

            data = response.json()

        except json.JSONDecodeError as e:

            print(
                "Google returned invalid JSON:",
                repr(e)
            )

            print(
                "Response:",
                response.text[:500]
            )

            return None

        # Expected structure:
        #
        # [
        #   [
        #      ["translated", "original", ...]
        #   ],
        #   ...
        # ]

        if not data:
            return None

        translated_parts = []

        first_part = data[0]

        if isinstance(first_part, list):

            for item in first_part:

                if (
                    isinstance(item, list)
                    and len(item) > 0
                    and isinstance(item[0], str)
                ):
                    translated_parts.append(
                        item[0]
                    )

        translated = "".join(
            translated_parts
        ).strip()

        if translated:

            print(
                f"Google translation "
                f"{source}->{target}:",
                repr(translated)
            )

            return translated

        print(
            "Google returned no translated text:",
            data
        )

    except requests.RequestException as e:

        print(
            f"Google request error "
            f"{source}->{target}:",
            repr(e)
        )

    except Exception as e:

        print(
            f"Google translation error "
            f"{source}->{target}:",
            repr(e)
        )

    return None


# =========================================================
# TRANSLATION WITH RETRY
# =========================================================

def translate(text, source, target):

    # First attempt
    result = translate_google(
        text,
        source,
        target
    )

    if result:
        return result

    # Small retry
    print(
        f"Retrying Google translation "
        f"{source}->{target}"
    )

    time.sleep(0.5)

    result = translate_google(
        text,
        source,
        target
    )

    if result:
        return result

    return None


# =========================================================
# TELEGRAM
# =========================================================

def send_message(
    chat_id,
    text,
    message_id=None
):

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if message_id:
        payload[
            "reply_to_message_id"
        ] = message_id

    try:

        response = session.post(
            f"{TELEGRAM_URL}/sendMessage",
            data=payload,
            timeout=20
        )

        print(
            "Telegram sendMessage status:",
            response.status_code
        )

        print(
            "Telegram response:",
            response.text
        )

        return response

    except Exception as e:

        print(
            "Telegram sendMessage error:",
            repr(e)
        )

        return None


# =========================================================
# PROCESS TEXT
# =========================================================

def process_text(
    text,
    chat_id,
    message_id
):

    if not text:
        return

    print(
        "========================================"
    )

    print(
        "Incoming text:",
        repr(text)
    )

    source_lang = detect_language(text)

    print(
        "Detected language:",
        source_lang
    )

    if source_lang not in SUPPORTED_LANGS:

        print(
            "Unsupported language:",
            source_lang
        )

        return

    target_languages = [
        lang
        for lang in LANGUAGE_ORDER
        if lang != source_lang
    ]

    print(
        "Target languages:",
        target_languages
    )

    translations = []

    for target in target_languages:

        translated = translate(
            text,
            source_lang,
            target
        )

        if translated:

            translations.append(
                f"{FLAGS[target]} {translated}"
            )

        else:

            translations.append(
                f"{FLAGS[target]} Translation failed."
            )

    reply = "\n".join(
        translations
    )

    print(
        "Final reply:",
        repr(reply)
    )

    send_message(
        chat_id=chat_id,
        text=reply,
        message_id=message_id
    )

    print(
        "========================================"
    )


# =========================================================
# WEBHOOK
# =========================================================

@app.route(
    "/webhook",
    methods=["POST"]
)
def webhook():

    try:

        data = request.get_json(
            force=True
        )

    except Exception as e:

        print(
            "JSON error:",
            repr(e)
        )

        return "ok", 200

    message = data.get(
        "message"
    )

    if not message:

        message = data.get(
            "edited_message"
        )

    if not message:
        return "ok", 200

    chat = message.get(
        "chat",
        {}
    )

    chat_id = chat.get(
        "id"
    )

    message_id = message.get(
        "message_id"
    )

    if not chat_id:
        return "ok", 200

    # Normal text
    text = message.get(
        "text"
    )

    if text:

        process_text(
            text,
            chat_id,
            message_id
        )

        return "ok", 200

    # Caption
    caption = message.get(
        "caption"
    )

    if not caption:
        return "ok", 200

    # Photo
    if message.get("photo"):

        print(
            "Photo caption detected."
        )

        process_text(
            caption,
            chat_id,
            message_id
        )

        return "ok", 200

    # Video
    if message.get("video"):

        print(
            "Video caption detected."
        )

        process_text(
            caption,
            chat_id,
            message_id
        )

        return "ok", 200

    # Document
    if message.get("document"):

        print(
            "Document caption detected."
        )

        process_text(
            caption,
            chat_id,
            message_id
        )

        return "ok", 200

    return "ok", 200


# =========================================================
# HOME
# =========================================================

@app.route(
    "/",
    methods=["GET"]
)
def home():

    return "Bot is running", 200


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
)
