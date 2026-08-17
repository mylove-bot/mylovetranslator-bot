import os
import re
import requests
from flask import Flask, request
from deep_translator import GoogleTranslator, LibreTranslator
from langdetect import detect, LangDetectException

app = Flask(__name__)

# =========================================================
# TOKEN
# =========================================================

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN environment variable is missing")

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}"


# =========================================================
# SUPPORTED LANGUAGES
# =========================================================

SUPPORTED_LANGS = {"en", "ru", "tr"}

LANGUAGE_ORDER = ["en", "ru", "tr"]

FLAGS = {
    "en": "🇬🇧",
    "ru": "🇷🇺",
    "tr": "🇹🇷"
}


# =========================================================
# COMMON SHORT WORDS
# =========================================================
# هذه الكلمات تستخدم لمنع langdetect من تخمين لغة خاطئة
# عندما تكون الرسالة قصيرة جدًا.

ENGLISH_WORDS = {
    "a", "an", "the",
    "i", "me", "my", "mine",
    "you", "your", "yours",
    "he", "him", "his",
    "she", "her", "hers",
    "we", "us", "our", "ours",
    "they", "them", "their", "theirs",

    "am", "is", "are", "was", "were",
    "be", "been", "being",
    "do", "does", "did",
    "have", "has", "had",
    "can", "could",
    "will", "would",
    "shall", "should",
    "may", "might", "must",

    "yes", "no",
    "hi", "hey", "hello",
    "bye", "goodbye",

    "what", "why", "who", "whom",
    "where", "when", "how",
    "which",

    "this", "that", "these", "those",
    "here", "there",

    "not", "never", "nothing",
    "something", "anything",

    "and", "or", "but",
    "if", "because", "so",
    "for", "from", "with",
    "without", "about",
    "to", "of", "in", "on",
    "at", "by",

    "good", "bad",
    "great", "nice",
    "okay", "ok",
    "fine",
    "sorry",
    "thanks", "thank",
    "please",

    "love", "like", "want",
    "need", "know",
    "think", "feel",
    "see", "look",
    "come", "go",
    "stay", "wait",
    "stop", "start",

    "now", "today", "tomorrow",
    "yesterday",
    "again", "always",
    "never", "sometimes",

    "one", "two", "three",
    "yes", "yeah", "nope"
}


RUSSIAN_WORDS = {
    "я", "мне", "мой", "моя", "мое", "мои",
    "ты", "тебе", "твой", "твоя", "твое", "твои",
    "он", "ему", "его",
    "она", "ей", "ее",
    "мы", "нам", "наш", "наша", "наше", "наши",
    "вы", "вам", "ваш", "ваша", "ваше", "ваши",
    "они", "им", "их",

    "да", "нет",
    "привет", "здравствуй",
    "пока",

    "что", "чего", "чем", "кому",
    "кто", "кого",
    "где", "куда", "откуда",
    "когда",
    "как",
    "почему",
    "зачем",
    "который", "которая", "которое", "которые",

    "это", "этот", "эта", "эти",
    "тот", "та", "то", "те",

    "есть", "был", "была", "были",
    "будет", "буду",
    "быть",

    "можно", "нельзя",
    "хочу", "хочешь",
    "нужно", "нужен",
    "надо",

    "не", "ни",
    "и", "или", "но",
    "если", "потому",
    "так", "тоже",

    "здесь", "там",
    "сейчас",
    "сегодня",
    "завтра",
    "вчера",
    "опять",
    "всегда",
    "никогда",

    "хорошо", "плохо",
    "хороший", "плохой",
    "спасибо", "пожалуйста",
    "извини",

    "люблю", "нравится",
    "хочу", "знаю",
    "думаю",
    "вижу",
    "смотри",
    "иди", "идти",
    "стой", "жди",
    "подожди",

    "один", "два", "три"
}


TURKISH_WORDS = {
    "ben", "bana", "beni", "benim",
    "sen", "sana", "seni", "senin",
    "o", "ona", "onu", "onun",
    "biz", "bize", "bizi", "bizim",
    "siz", "size", "sizi", "sizin",
    "onlar", "onlara", "onları", "onların",

    "bir",
    "bu", "şu", "o",
    "bunlar", "şunlar",

    "evet", "hayır",
    "merhaba", "selam",
    "güle güle",

    "ne", "neden",
    "niçin", "niye",
    "kim", "kime", "kimi",
    "nerede", "nereye", "nereden",
    "ne zaman",
    "nasıl",
    "hangi",

    "mı", "mi", "mu", "mü",

    "var", "yok",
    "olmak",
    "oldu", "oluyor",
    "olacak",

    "değil",
    "de",
    "da",

    "ve", "veya",
    "ama",
    "eğer",
    "çünkü",
    "fakat",
    "için",
    "ile",
    "gibi",

    "burada",
    "orada",
    "şimdi",
    "bugün",
    "yarın",
    "dün",
    "yine",
    "her zaman",
    "asla",

    "iyi", "kötü",
    "güzel",
    "tamam",
    "peki",

    "teşekkür",
    "teşekkürler",
    "lütfen",
    "özür",

    "seviyorum",
    "seviyor",
    "istiyorum",
    "istiyorsun",
    "biliyorum",
    "biliyor",
    "düşünüyorum",
    "gel",
    "git",
    "bekle",
    "dur",

    "bir", "iki", "üç"
}


# =========================================================
# NORMALIZE TEXT
# =========================================================

def normalize_text(text):
    text = text.lower().strip()

    # إزالة علامات الترقيم مع الحفاظ على الأحرف الروسية والتركية
    text = re.sub(r"[^\w\sğüşıöçĞÜŞİÖÇа-яА-ЯёЁ]", " ", text)

    # إزالة المسافات الزائدة
    text = re.sub(r"\s+", " ", text)

    return text


# =========================================================
# WORD EXTRACTION
# =========================================================

def get_words(text):
    normalized = normalize_text(text)
    return normalized.split()


# =========================================================
# SHORT WORD DETECTION
# =========================================================

def detect_from_common_words(text):
    normalized = normalize_text(text)

    # العبارات ذات أكثر من كلمة أولًا
    multi_word = {
        "ne zaman": "tr",
        "ne için": "tr",
        "почему же": "ru",
        "что это": "ru",
        "how are": "en",
        "how are you": "en",
        "what is": "en",
        "what are": "en",
        "where are": "en",
        "why are": "en"
    }

    if normalized in multi_word:
        return multi_word[normalized]

    words = get_words(text)

    if not words:
        return None

    en_score = 0
    ru_score = 0
    tr_score = 0

    for word in words:

        if word in ENGLISH_WORDS:
            en_score += 3

        if word in RUSSIAN_WORDS:
            ru_score += 3

        if word in TURKISH_WORDS:
            tr_score += 3

    # -----------------------------------------------------
    # Character-based detection
    # -----------------------------------------------------

    # روسي: Cyrillic
    if re.search(r"[а-яА-ЯёЁ]", text):
        ru_score += 5

    # تركي: أحرف مميزة
    if re.search(r"[ğüşıöçĞÜŞİÖÇ]", text):
        tr_score += 6

    # إذا فيه أحرف إنجليزية فقط
    latin_letters = re.findall(r"[a-zA-Z]", text)

    if latin_letters:
        # الإنجليزية تحصل على دفعة، لكن التركية
        # ذات الأحرف الخاصة تكون أقوى.
        en_score += 1

    scores = {
        "en": en_score,
        "ru": ru_score,
        "tr": tr_score
    }

    best_lang = max(scores, key=scores.get)
    best_score = scores[best_lang]

    # لا نعطي نتيجة إذا ما في أي دليل
    if best_score <= 0:
        return None

    # إذا كانت كلمة واحدة ومعروفة بوضوح
    if len(words) == 1:
        if words[0] in ENGLISH_WORDS:
            return "en"

        if words[0] in RUSSIAN_WORDS:
            return "ru"

        if words[0] in TURKISH_WORDS:
            return "tr"

    return best_lang


# =========================================================
# LANGUAGE DETECTION
# =========================================================

def detect_language(text):

    # أولًا: الكلمات والعبارات المعروفة
    common_result = detect_from_common_words(text)

    if common_result:
        print("Common-word detector:", common_result)
        return common_result

    # -----------------------------------------------------
    # Direct character detection
    # -----------------------------------------------------

    # روسي
    if re.search(r"[а-яА-ЯёЁ]", text):
        try:
            detected = detect(text)

            if detected == "ru":
                return "ru"

        except LangDetectException:
            pass

        # إذا كان النص Cyrillic ولا يوجد دليل آخر
        return "ru"

    # تركي
    if re.search(r"[ğüşıöçĞÜŞİÖÇ]", text):
        return "tr"

    # -----------------------------------------------------
    # langdetect
    # -----------------------------------------------------

    try:
        detected = detect(text)

        print("langdetect result:", detected)

        if detected in SUPPORTED_LANGS:
            return detected

    except LangDetectException as e:
        print("Language detection error:", repr(e))

    # -----------------------------------------------------
    # English fallback
    # -----------------------------------------------------

    words = get_words(text)

    if words:

        english_matches = sum(
            1 for word in words
            if word in ENGLISH_WORDS
        )

        if english_matches > 0:
            return "en"

    # -----------------------------------------------------
    # Turkish fallback
    # -----------------------------------------------------

    turkish_matches = sum(
        1 for word in words
        if word in TURKISH_WORDS
    )

    if turkish_matches > 0:
        return "tr"

    return None


# =========================================================
# TRANSLATION
# =========================================================

def translate(text, target):

    # Google Translator
    try:

        result = GoogleTranslator(
            source="auto",
            target=target
        ).translate(text)

        print(
            f"Google translation -> {target}: "
            f"{repr(result)}"
        )

        return result

    except Exception as e:

        print(
            f"GoogleTranslator error -> {target}:",
            repr(e)
        )

    # LibreTranslator fallback
    try:

        result = LibreTranslator(
            source="auto",
            target=target
        ).translate(text)

        print(
            f"Libre translation -> {target}: "
            f"{repr(result)}"
        )

        return result

    except Exception as e:

        print(
            f"LibreTranslator error -> {target}:",
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
    print("Incoming text:", repr(text))

    # Detect language
    src_lang = detect_language(text)

    print("Detected language:", src_lang)

    if src_lang not in SUPPORTED_LANGS:

        print(
            "Unsupported or unknown language:",
            src_lang
        )

        print("========================================")

        return

    # Target languages
    target_languages = [
        lang
        for lang in LANGUAGE_ORDER
        if lang != src_lang
    ]

    print(
        "Target languages:",
        target_languages
    )

    translations = []

    for target in target_languages:

        translated = translate(
            text,
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
        print("No translations generated.")
        return

    reply = "\n".join(translations)

    print("Final reply:")
    print(reply)

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
            "Invalid Telegram JSON:",
            repr(e)
        )

        return "ok", 200

    # =====================================================
    # NORMAL MESSAGE
    # =====================================================

    message = data.get("message")

    # =====================================================
    # EDITED MESSAGE
    # =====================================================

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
    # TEXT MESSAGE
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
    # PHOTO WITH CAPTION
    # =====================================================
    # نحن لا نرسل الصورة.
    # نأخذ caption فقط ونترجمه.

    photo = message.get("photo")

    caption = message.get("caption")

    if photo and caption:

        print("Photo received with caption.")
        print("Caption:", repr(caption))

        process_text(
            caption,
            chat_id,
            message_id
        )

        return "ok", 200

    # =====================================================
    # VIDEO WITH CAPTION
    # =====================================================

    video = message.get("video")

    if video and caption:

        print("Video received with caption.")

        process_text(
            caption,
            chat_id,
            message_id
        )

        return "ok", 200

    # =====================================================
    # DOCUMENT WITH CAPTION
    # =====================================================

    document = message.get("document")

    if document and caption:

        print("Document received with caption.")

        process_text(
            caption,
            chat_id,
            message_id
        )

        return "ok", 200

    # =====================================================
    # OTHER MEDIA
    # =====================================================

    return "ok", 200


# =========================================================
# HEALTH CHECK
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
