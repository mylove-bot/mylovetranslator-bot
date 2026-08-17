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
    "a", "an", "the", "i", "me", "my", "you", "your",
    "he", "she", "it", "we", "us", "they", "them",
    "is", "am", "are", "was", "were",
    "be", "been", "being",
    "do", "does", "did",
    "have", "has", "had",
    "can", "could", "will", "would",
    "should", "shall", "may", "might", "must",

    "and", "or", "but", "if", "then",
    "because", "so", "for", "from", "with",
    "without", "about", "to", "of", "in",
    "on", "at", "by",

    "what", "why", "who", "where", "when",
    "how", "which",

    "this", "that", "these", "those",
    "here", "there",

    "hello", "hi", "hey", "bye",
    "yes", "yeah", "no", "nope",
    "okay", "ok", "good", "bad",
    "great", "nice", "fine",

    "please", "thanks", "thank", "sorry",

    "still", "some", "any", "more", "less",
    "very", "really", "just", "only",
    "also", "again", "already",

    "mistake", "mistakes", "problem", "problems",
    "thing", "things",

    "love", "like", "want", "need",
    "know", "think", "feel",
    "see", "look", "come", "go",
    "wait", "stop", "start"
}


RUSSIAN_COMMON = {
    "я", "ты", "он", "она", "оно", "мы", "вы", "они",
    "мне", "тебе", "ему", "ей", "нам", "вам", "им",
    "мой", "моя", "мое", "мои",
    "твой", "твоя", "твое", "твои",

    "да", "нет",
    "привет", "пока",

    "что", "кто", "где", "куда", "откуда",
    "когда", "как", "почему", "зачем",
    "какой", "какая", "какие",

    "это", "этот", "эта", "эти",
    "тот", "та", "то", "те",

    "есть", "был", "была", "были",
    "будет", "буду", "быть",

    "можно", "нельзя",
    "нужно", "нужен", "надо",
    "хочу", "хочешь",

    "не", "ни",
    "и", "или", "но",
    "если", "потому",

    "здесь", "там",
    "сейчас", "сегодня", "завтра", "вчера",
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
    "ben", "sen", "o", "biz", "siz", "onlar",
    "bana", "sana", "beni", "seni",
    "benim", "senin",

    "bir", "bu", "şu",
    "bunlar", "şunlar",

    "evet", "hayır",
    "merhaba", "selam",
    "güle",

    "ne", "neden", "niye", "niçin",
    "kim", "kime", "kimi",
    "nerede", "nereye", "nereden",
    "nasıl", "hangi",
    "zaman",

    "var", "yok",
    "değil",
    "oldu", "oluyor", "olacak",

    "ve", "veya", "ama",
    "çünkü", "eğer",
    "için", "ile", "gibi",

    "burada", "orada",
    "şimdi", "bugün", "yarın", "dün",
    "yine", "asla", "her",

    "iyi", "kötü", "güzel",
    "tamam", "peki",

    "teşekkür", "teşekkürler",
    "lütfen", "özür",

    "seviyorum", "istiyorum",
    "biliyorum", "düşünüyorum",
    "gel", "git", "bekle", "dur"
}


# =========================================================
# HELPERS
# =========================================================

def normalize(text):
    return text.lower().strip()


def words(text):
    return re.findall(r"[A-Za-zÀ-ÿĞÜŞİÖÇğüşıöçА-Яа-яЁё]+", normalize(text))


# =========================================================
# LANGUAGE DETECTION
# =========================================================

def detect_language(text):

    text = normalize(text)
    word_list = words(text)

    if not word_list:
        return None

    # -----------------------------------------------------
    # 1. Russian Cyrillic detection
    # -----------------------------------------------------

    cyrillic = re.findall(r"[А-Яа-яЁё]", text)

    if cyrillic:
        print("Cyrillic detected -> Russian")
        return "ru"

    # -----------------------------------------------------
    # 2. Turkish special characters
    # -----------------------------------------------------

    if re.search(r"[ğüşıöçĞÜŞİÖÇ]", text):
        print("Turkish characters detected -> Turkish")
        return "tr"

    # -----------------------------------------------------
    # 3. Count common words
    # -----------------------------------------------------

    en_score = sum(
        1 for word in word_list
        if word in ENGLISH_COMMON
    )

    tr_score = sum(
        1 for word in word_list
        if word in TURKISH_COMMON
    )

    ru_score = sum(
        1 for word in word_list
        if word in RUSSIAN_COMMON
    )

    print(
        f"Common scores -> "
        f"en={en_score}, "
        f"ru={ru_score}, "
        f"tr={tr_score}"
    )

    # -----------------------------------------------------
    # 4. Strong common-word result
    # -----------------------------------------------------

    scores = {
        "en": en_score,
        "ru": ru_score,
        "tr": tr_score
    }

    best_lang = max(scores, key=scores.get)
    best_score = scores[best_lang]

    if best_score > 0:
        # إذا اللغة المتفوقة واضحة
        sorted_scores = sorted(
            scores.values(),
            reverse=True
        )

        if (
            len(sorted_scores) == 1
            or sorted_scores[0] > sorted_scores[1]
        ):
            print(
                f"Common words -> {best_lang}"
            )
            return best_lang

    # -----------------------------------------------------
    # 5. langdetect as secondary detector
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
    # 6. Latin fallback
    # -----------------------------------------------------
    #
    # إذا النص مكتوب بأحرف لاتينية عادية ولا توجد
    # علامات تركية واضحة، نعتبره English.
    #
    # هذا مهم جدًا للجمل القصيرة مثل:
    # "still some mistakes"
    # "why"
    # "hello"
    # "I don't know"
    #

    latin = re.findall(r"[A-Za-z]", text)

    if latin:

        print(
            "Latin fallback -> English"
        )

        return "en"

    return None


# =========================================================
# TRANSLATION
# =========================================================

def translate(text, target):

    try:

        result = GoogleTranslator(
            source="auto",
            target=target
        ).translate(text)

        print(
            f"Google translation -> {target}:",
            repr(result)
        )

        return result

    except Exception as e:

        print(
            f"GoogleTranslator error -> {target}:",
            repr(e)
        )

    # Fallback
    try:

        result = LibreTranslator(
            source="auto",
            target=target
        ).translate(text)

        print(
            f"Libre translation -> {target}:",
            repr(result)
        )

        return result

    except Exception as e:

        print(
            f"LibreTranslator error -> {target}:",
            repr(e)
        )

        return None


# =========================================================
# SEND MESSAGE
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
            "Telegram status:",
            response.status_code
        )

        print(
            "Telegram response:",
            response.text
        )

        return response

    except Exception as e:

        print(
            "Telegram request error:",
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
    print("Incoming text:", repr(text))

    src_lang = detect_language(text)

    print(
        "Detected language:",
        src_lang
    )

    if src_lang not in SUPPORTED_LANGS:

        print(
            "Could not determine supported language."
        )

        print("========================================")

        return

    # All other languages except source
    targets = [
        lang
        for lang in LANGUAGE_ORDER
        if lang != src_lang
    ]

    print(
        "Translation targets:",
        targets
    )

    results = []

    for target in targets:

        translated = translate(
            text,
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

    if not results:
        return

    reply = "\n".join(results)

    print(
        "Final reply:",
        repr(reply)
    )

    send_message(
        chat_id,
        reply,
        message_id
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

    # Normal message
    message = data.get("message")

    # Edited message
    if not message:
        message = data.get("edited_message")

    if not message:
        return "ok", 200

    chat = message.get("chat", {})

    chat_id = chat.get("id")

    message_id = message.get("message_id")

    if not chat_id:
        return "ok", 200

    # =====================================================
    # NORMAL TEXT
    # =====================================================

    text = message.get("text")

    if text:

        process_text(
            text,
            chat_id,
            message_id
        )

        return "ok", 200

    # =====================================================
    # PHOTO + CAPTION
    # =====================================================

    caption = message.get("caption")

    if message.get("photo") and caption:

        print(
            "Photo with caption detected."
        )

        # فقط الـcaption
        # الصورة لا يتم إرسالها
        process_text(
            caption,
            chat_id,
            message_id
        )

        return "ok", 200

    # =====================================================
    # VIDEO + CAPTION
    # =====================================================

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

    # =====================================================
    # DOCUMENT + CAPTION
    # =====================================================

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
