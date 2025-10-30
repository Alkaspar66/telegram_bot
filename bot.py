import os
import csv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# ===============================
# 🔧 Настройки
# ===============================
TOKEN = os.getenv("TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))  # свой Telegram ID
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://{WEBHOOK_HOST}{WEBHOOK_PATH}"

CSV_FILE = "applications.csv"
user_states = {}

# ===============================
# 🤖 Логика бота
# ===============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    user_states[user_id] = {"step": "ask_name"}
    await update.message.reply_text("👋 Привет! Как вас зовут?")
    print(f"🆕 /start от {user_id}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    text = update.message.text.strip()
    print(f"📩 Сообщение от {user_id}: {text}")

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

        # сохраняем в CSV
        save_to_csv(name, phone)

        # уведомляем админа
        if ADMIN_CHAT_ID:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"🆕 Новая заявка!\nИмя: {name}\nТелефон: {phone}"
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
    print(f"💾 Сохранено: {name}, {phone}")

# ===============================
# 🚀 Запуск бота с webhook
# ===============================
if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print(f"🚀 Бот запускается, webhook: {WEBHOOK_URL}")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_path=WEBHOOK_PATH,
        url_path=WEBHOOK_PATH,
        webhook_url=WEBHOOK_URL
    )
