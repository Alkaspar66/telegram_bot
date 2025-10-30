import json

class SimpleBot:
    def __init__(self, data_file="data.json"):
        with open(data_file, encoding="utf-8") as f:
            self.data = json.load(f)
        self.state = None
        self.form_answers = []

    def reply(self, message):
        msg = message.lower().strip()

        # если бот ждёт ответы для формы
        if self.state:
            form = self.data["forms"][self.state]
            self.form_answers.append(message)
            if len(self.form_answers) == len(form["questions"]):
                # здесь можно записать в базу, отправить уведомление и т.д.
                print(f"[LOG] Заявка: {self.form_answers}")
                self.state = None
                self.form_answers = []
                return form["on_complete"]
            else:
                return form["questions"][len(self.form_answers)]

        # FAQ
        if msg in self.data["faq"]:
            return self.data["faq"][msg]

        # формы
        if msg in self.data["forms"]:
            self.state = msg
            self.form_answers = []
            return self.data["forms"][msg]["questions"][0]

        return "Не понял тебя 🤔. Попробуй спросить про 'цену', 'программу' или напиши 'запись'."

if __name__ == "__main__":
    bot = SimpleBot()
    while True:
        msg = input("Ты: ")
        print("Бот:", bot.reply(msg))
