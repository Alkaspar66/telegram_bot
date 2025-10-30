import os
import csv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # Telegram ID админа
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"

CSV_FILE = "applications.csv"
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    user_states[user_id] = {"step": "ask_name"}
    await update.message.reply_text("👋 Привет! Как вас зовут?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
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
                chat_id=int(ADMIN_CHAT_ID),
                text=f"🆕 Новая заявка!\nИмя: {name}\nТелефон: {phone}",
            )

        await update.message.reply_text("✅ Спасибо! Ваша заявка принята.")
        user_states.pop(user_id, None)

def save_to_csv(name, phone):
    new_file = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["Имя", "Телефон"])
        writer.writerow([name, phone])

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запуск webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL,
    )
