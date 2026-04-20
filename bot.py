@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(silent=True)

        if not data:
            return "ok", 200

        message = data.get("message")
        if not message:
            return "ok", 200

        text = message.get("text")
        chat_id = message.get("chat", {}).get("id")

        if not text or not chat_id:
            return "ok", 200

        lang = get_lang(text)

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

        bot.send_message(chat_id=chat_id, text=reply)

    except Exception as e:
        print("ERROR:", e)

    return "ok", 200