import os
import csv
import asyncio
import logging
from threading import Thread
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ===============================
# 🔧 Настройки
# ===============================
TOKEN = os.getenv("TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"

CSV_FILE = "applications.csv"

# ===============================
# ⚙️ Логирование
# ===============================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ===============================
# Flask
# ===============================
app = Flask(__name__)

# ===============================
# Telegram
# ===============================
telegram_app = Application.builder().token(TOKEN).concurrent_updates(10).build()
user_states = {}
telegram_loop = None  # будет хранить loop для run_coroutine_threadsafe

# ===============================
# Логика бота
# ===============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    user_states[user_id] = {"step": "ask_name"}
    try:
        await update.message.reply_text("👋 Привет! Как вас зовут?")
    except Exception as e:
        logging.error("Ошибка при отправке сообщения: %s", e)

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
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"🆕 Новая заявка!\nИмя: {name}\nТелефон: {phone}",
                )
            except Exception as e:
                logging.error("Ошибка при отправке админу: %s", e)

        await update.message.reply_text("✅ Спасибо! Ваша заявка принята.")
        user_states.pop(user_id, None)

# ===============================
# CSV
# ===============================
def save_to_csv(name: str, phone: str):
    try:
        new_file = not os.path.exists(CSV_FILE)
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if new_file:
                writer.writerow(["Имя", "Телефон"])
            writer.writerow([name, phone])
    except Exception as e:
        logging.error("Ошибка записи CSV: %s", e)

# ===============================
# Flask webhook
# ===============================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, telegram_app.bot)
    try:
        asyncio.run_coroutine_threadsafe(telegram_app.process_update(update), telegram_loop)
    except Exception as e:
        logging.error("Ошибка при обработке webhook: %s", e)
    return "ok"

# ===============================
# Фоновый поток для Telegram
# ===============================
def start_telegram():
    global telegram_loop

    async def run():
        global telegram_loop
        telegram_loop = asyncio.get_running_loop()

        # добавляем обработчики
        telegram_app.add_handler(CommandHandler("start", start))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        await telegram_app.initialize()
        await telegram_app.bot.set_webhook(WEBHOOK_URL)
        logging.info("🚀 Telegram бот запущен, webhook установлен: %s", WEBHOOK_URL)

        await telegram_app.start()
        await telegram_app.updater.start_polling()  # безопасный старт loop

    asyncio.run(run())

# ===============================
# Запуск Flask + Telegram
# ===============================
if __name__ == "__main__":
    # запускаем Telegram в отдельном потоке
    Thread(target=start_telegram, daemon=True).start()

    port = int(os.environ.get("PORT", 10000))
    logging.info("🚀 Flask сервер запускается на порту %s", port)
    app.run(host="0.0.0.0", port=port)
