import os
import re
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
    "where", "when", "how", "which",

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
    "stop", "start"
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
    "и", "или", "но", "если",
    "потому",

    "здесь", "там",
    "сейчас",
    "сегодня",
    "завтра",
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

    # -----------------------------------------------------
    # Russian: Cyrillic characters
    # -----------------------------------------------------

    if re.search(r"[А-Яа-яЁё]", text):
        print("Cyrillic detected -> ru")
        return "ru"

    # -----------------------------------------------------
    # Turkish: special Turkish characters
    # -----------------------------------------------------

    if re.search(r"[ğüşıöçĞÜŞİÖÇ]", text):
        print("Turkish characters detected -> tr")
        return "tr"

    # -----------------------------------------------------
    # Common-word scoring
    # -----------------------------------------------------

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

    # إذا كان هناك تطابق واضح
    if best_score > 0:

        if (
            len(sorted_scores) < 2
            or sorted_scores[0] > sorted_scores[1]
        ):
            print(
                f"Common words detected -> {best_lang}"
            )
            return best_lang

    # -----------------------------------------------------
    # langdetect as secondary method
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Latin fallback
    # -----------------------------------------------------

    if re.search(r"[A-Za-z]", text):

        print(
            "Latin fallback -> en"
        )

        return "en"

    return None


# =========================================================
# TRANSLATION
# =========================================================

def translate(text, source, target):

    print(
        f"Translating: {source} -> {target}"
    )

    # Google Translate HTTP endpoint
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

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/139.0.0.0 Safari/537.36"
        )
    }

    try:

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=20
        )

        print(
            f"Google HTTP status "
            f"{source}->{target}:",
            response.status_code
        )

        if response.status_code != 200:

            print(
                "Google response:",
                response.text[:500]
            )

            return None

        data = response.json()

        translated_parts = []

        if data and isinstance(data[0], list):

            for sentence in data[0]:

                if (
                    isinstance(sentence, list)
                    and len(sentence) > 0
                    and sentence[0]
                ):
                    translated_parts.append(
                        sentence[0]
                    )

        result = "".join(
            translated_parts
        ).strip()

        print(
            f"Google HTTP {source}->{target}:",
            repr(result)
        )

        if result:
            return result

        print(
            f"Google returned empty translation "
            f"{source}->{target}"
        )

    except requests.exceptions.Timeout:

        print(
            f"Google translation timeout "
            f"{source}->{target}"
        )

    except requests.exceptions.RequestException as e:

        print(
            f"Google HTTP error "
            f"{source}->{target}:",
            repr(e)
        )

    except ValueError as e:

        print(
            f"Google JSON error "
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
# SEND TELEGRAM MESSAGE
# =========================================================

def send_message(chat_id, text, message_id=None):

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if message_id:
        payload["reply_to_message_id"] = message_id

    try:

        response = requests.post(
            f"{TELEGRAM_URL}/sendMessage",
            data=payload,
            timeout=20
        )

        print(
            "Telegram sendMessage status:",
            response.status_code
        )

        print(
            "Telegram sendMessage response:",
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

def process_text(text, chat_id, message_id):

    if not text:
        return

    print("========================================")
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
            "Unsupported or unknown language:",
            source_lang
        )

        print("========================================")

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

    if not translations:
        return

    reply = "\n".join(translations)

    print(
        "Final reply:",
        repr(reply)
    )

    send_message(
        chat_id=chat_id,
        text=reply,
        message_id=message_id
    )

    print("========================================")


# =========================================================
# WEBHOOK
# =========================================================

@app.route("/webhook", methods=["POST"])
def webhook():

    try:

        data = request.get_json(force=True)

    except Exception as e:

        print(
            "JSON error:",
            repr(e)
        )

        return "ok", 200

    # -----------------------------------------------------
    # Normal message
    # -----------------------------------------------------

    message = data.get("message")

    # -----------------------------------------------------
    # Edited message
    # -----------------------------------------------------

    if not message:
        message = data.get("edited_message")

    if not message:
        return "ok", 200

    chat = message.get(
        "chat",
        {}
    )

    chat_id = chat.get("id")
    message_id = message.get("message_id")

    if not chat_id:
        return "ok", 200

    # -----------------------------------------------------
    # Normal text
    # -----------------------------------------------------

    text = message.get("text")

    if text:

        process_text(
            text,
            chat_id,
            message_id
        )

        return "ok", 200

    # -----------------------------------------------------
    # Caption
    # -----------------------------------------------------

    caption = message.get("caption")

    # -----------------------------------------------------
    # Photo + caption
    # -----------------------------------------------------

    if message.get("photo") and caption:

        print(
            "Photo with caption detected."
        )

        # نترجم الـcaption فقط
        # ولا نرسل الصورة
        process_text(
            caption,
            chat_id,
            message_id
        )

        return "ok", 200

    # -----------------------------------------------------
    # Video + caption
    # -----------------------------------------------------

    if message.get("video") and caption:

        print(
            "Video with caption detected."
        )

        process_text(
            caption,
            chat_id,
            message_id
        )

        return "ok", 200

    # -----------------------------------------------------
    # Document + caption
    # -----------------------------------------------------

    if message.get("document") and caption:

        print(
            "Document with caption detected."
        )

        process_text(
            caption,
            chat_id,
            message_id
        )

        return "ok", 200

    # Media without caption -> ignore

    return "ok", 200


# =========================================================
# HOME
# =========================================================

@app.route("/", methods=["GET"])
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
