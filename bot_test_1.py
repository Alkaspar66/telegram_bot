import csv
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# 🔑 ВСТАВЬ СВОЙ ТОКЕН
TOKEN = "123456789:ABCdEfGhIjKlMnOpQrStUvWxYz"

# 🆔 ID администратора (чтобы бот отправлял уведомления тебе)
ADMIN_CHAT_ID = 123456789

# 📂 CSV-файл, куда будут сохраняться заявки
CSV_FILE = "applications.csv"

# ————————————————————————————
# 1. Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! ✋ Как вас зовут?")
    context.user_data["step"] = "name"

# ————————————————————————————
# 2. Обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # Шаг 1 — спрашиваем имя
    if context.user_data.get("step") == "name":
        context.user_data["name"] = text
        context.user_data["step"] = "phone"
        await update.message.reply_text("Отлично! Теперь напишите ваш номер телефона:")
        return

    # Шаг 2 — получаем телефон и сохраняем заявку
    if context.user_data.get("step") == "phone":
        context.user_data["phone"] = text
        name = context.user_data["name"]
        phone = context.user_data["phone"]
        date = datetime.now().strftime("%Y-%m-%d %H:%M")

        # сохраняем в CSV
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([name, phone, date])

        # уведомляем пользователя
        await update.message.reply_text("Спасибо! Ваша заявка принята 💬")

        # уведомляем администратора
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"📩 Новая заявка!\nИмя: {name}\nТелефон: {phone}\nДата: {date}"
        )

        # сбрасываем состояние
        context.user_data.clear()
        return

    # Если пользователь написал что-то другое
    await update.message.reply_text("Напишите /start, чтобы начать.")

# ————————————————————————————
# 3. Запуск бота
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
