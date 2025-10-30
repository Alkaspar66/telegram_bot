import os
import csv
import asyncio
import threading
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"

app = Flask(__name__)
telegram_app = Application.builder().token(TOKEN).build()
CSV_FILE = "applications.csv"
user_states = {}

# ===============================
# 🤖 Логика бота
# ===============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    user_states[user_id] = {"step": "ask_name"}
    await update.message.reply_text("👋 Привет! Как вас зовут?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    text = update.message.text.strip()

    if user_id not in user_states:
        await update.message.reply_text("Введите /start чтобы начать запись 🙂")
        return

    state = user_states[user_id]

    if state["step"] == "ask_name":
        state["name"] = text
        state["step"] = "ask_phone"
        await update.message.reply_text("📞 Укажите ваш телефон:")
        return

    if state["step"] == "ask_phone":
        state["phone"] = text
        name, phone = state["name"], state["phone"]
        save_to_csv(name, phone)

        if ADMIN_CHAT_ID:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"🆕 Новая заявка!\nИмя: {name}\nТелефон: {phone}",
            )

        await update.message.reply_text("✅ Спасибо! Ваша заявка принята.")
        user_states.pop(user_id, None)

def save_to_csv(name: str, phone: str):
    new_file = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["Имя", "Телефон"])
        writer.writerow([name, phone])

# ===============================
# 🌐 Flask Webhook
# ===============================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    print("📩 Webhook получил апдейт:", data)
    update = Update.de_json(data, telegram_app.bot)

    # безопасно передаем в loop телеграма
    asyncio.run_coroutine_threadsafe(
        telegram_app.process_update(update),
        telegram_app.loop,
    )
    return "ok"

@app.route("/")
def home():
    return "Bot is alive ✅", 200

# ===============================
# 🚀 Запуск
# ===============================
async def run_bot():
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.bot.set_webhook(WEBHOOK_URL)
    print(f"🚀 Webhook установлен: {WEBHOOK_URL}")

def start_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # запускаем Telegram в отдельном потоке
    threading.Thread(target=lambda: asyncio.run(run_bot())).start()
    # Flask — в основном потоке (Render будет держать этот процесс)
    start_flask()
