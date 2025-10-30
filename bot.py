import os
import csv
import asyncio
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
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # можно не задавать
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"

app = Flask(__name__)
telegram_app = Application.builder().token(TOKEN).build()

# 📁 CSV-файл сохраняется в той же директории, где запущен бот
CSV_FILE = "applications.csv"

# ===============================
# 🤖 Логика бота
# ===============================
user_states = {}  # хранит этап диалога для каждого пользователя


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

    # 1️⃣ Спрашиваем имя
    if state["step"] == "ask_name":
        state["name"] = text
        state["step"] = "ask_phone"
        await update.message.reply_text("📞 Укажите ваш телефон:")
        return

    # 2️⃣ Получаем телефон
    if state["step"] == "ask_phone":
        state["phone"] = text
        name, phone = state["name"], state["phone"]

        save_to_csv(name, phone)

        # уведомляем админа (если указан)
        if ADMIN_CHAT_ID:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"🆕 Новая заявка!\nИмя: {name}\nТелефон: {phone}",
            )

        await update.message.reply_text("✅ Спасибо! Ваша заявка принята.")
        user_states.pop(user_id, None)


def save_to_csv(name: str, phone: str):
    """Создаёт или дописывает CSV в рабочей папке."""
    new_file = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["Имя", "Телефон"])
        writer.writerow([name, phone])


# ===============================
# 🧩 Подключение хендлеров
# ===============================
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ===============================
# 🌐 Flask Webhook
# ===============================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, telegram_app.bot)
    telegram_app.update_queue.put_nowait(update)
    return "ok"


# ===============================
# 🚀 Запуск
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    async def main():
        print(f"🚀 Запуск бота на {WEBHOOK_URL}")
        await telegram_app.bot.set_webhook(WEBHOOK_URL)
        await telegram_app.initialize()
        await telegram_app.start()
        app.run(host="0.0.0.0", port=port)

    asyncio.run(main())
