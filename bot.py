import os
import csv
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

TOKEN = os.getenv("TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"

bot = Bot(TOKEN)
dp = Dispatcher(bot, None, workers=0)  # нет очереди, всё синхронно

app = Flask(__name__)

CSV_FILE = "applications.csv"
user_states = {}

# --------------------------
# Бот логика
# --------------------------
def start(update, context):
    user_id = update.message.chat.id
    user_states[user_id] = {"step": "ask_name"}
    update.message.reply_text("👋 Привет! Как вас зовут?")

def handle_message(update, context):
    user_id = update.message.chat.id
    text = update.message.text.strip()

    if user_id not in user_states:
        update.message.reply_text("Введите /start чтобы начать запись 🙂")
        return

    state = user_states[user_id]

    if state["step"] == "ask_name":
        state["name"] = text
        state["step"] = "ask_phone"
        update.message.reply_text("📞 Укажите ваш телефон:")
        return

    if state["step"] == "ask_phone":
        state["phone"] = text
        name, phone = state["name"], state["phone"]

        # сохраняем в CSV
        new_file = not os.path.exists(CSV_FILE)
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            import csv
            writer = csv.writer(f)
            if new_file:
                writer.writerow(["Имя", "Телефон"])
            writer.writerow([name, phone])

        # уведомляем админа
        if ADMIN_CHAT_ID:
            bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"🆕 Новая заявка!\nИмя: {name}\nТелефон: {phone}")

        update.message.reply_text("✅ Спасибо! Ваша заявка принята.")
        user_states.pop(user_id, None)

# --------------------------
# Регистрируем обработчики
# --------------------------
dp.add_handler(CommandHandler("start", start))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# --------------------------
# Flask Webhook
# --------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    dp.process_update(update)
    return "ok"

# --------------------------
# Запуск
# --------------------------
if __name__ == "__main__":
    bot.set_webhook(WEBHOOK_URL)
    app.run(host="0.0.0.0", port=PORT)
