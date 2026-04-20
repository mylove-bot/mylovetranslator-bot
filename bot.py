import os
import requests
from langdetect import detect
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")

# جلسة واحدة = أسرع
session = requests.Session()

def translate(text, source, target):
    try:
        url = "https://libretranslate.de/translate"
        payload = {
            "q": text,
            "source": source,
            "target": target,
            "format": "text"
        }

        r = session.post(url, data=payload, timeout=5)
        return r.json().get("translatedText", "")
    except:
        return "..."

def get_lang(text):
    try:
        return detect(text)
    except:
        return "en"

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    lang = get_lang(text)

    try:
        if lang.startswith("en"):
            tr = translate(text, "en", "tr")
            ru = translate(text, "en", "ru")

            reply = f"🇹🇷 {tr}\n🇷🇺 {ru}"

        elif lang.startswith("tr"):
            en = translate(text, "tr", "en")
            ru = translate(text, "tr", "ru")

            reply = f"🇬🇧 {en}\n🇷🇺 {ru}"

        elif lang.startswith("ru"):
            en = translate(text, "ru", "en")
            tr = translate(text, "ru", "tr")

            reply = f"🇬🇧 {en}\n🇹🇷 {tr}"

        else:
            en = translate(text, "auto", "en")
            tr = translate(text, "auto", "tr")

            reply = f"🇬🇧 {en}\n🇹🇷 {tr}"

        await update.message.reply_text(reply)

    except:
        await update.message.reply_text("❌ Error")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("⚡ Fast bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()