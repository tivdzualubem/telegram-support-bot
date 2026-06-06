import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Здравствуйте! 👋\n"
        "Я виртуальный помощник.\n\n"
        "Чем могу помочь?\n\n"
        "1. Услуги\n"
        "2. Цены\n"
        "3. Адрес\n"
        "4. Часы работы\n"
        "5. Связаться с менеджером"
    )


async def reply_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.lower()

    if "цена" in user_text or "стоимость" in user_text or "прайс" in user_text:
        response = (
            "Стоимость зависит от услуги.\n"
            "Пожалуйста, напишите, какая услуга вас интересует, "
            "и менеджер свяжется с вами."
        )

    elif "услуг" in user_text or "что вы делаете" in user_text:
        response = (
            "Мы предлагаем следующие услуги:\n"
            "• Консультация\n"
            "• Заказ услуги\n"
            "• Поддержка клиентов\n\n"
            "Напишите, какая услуга вам нужна."
        )

    elif "адрес" in user_text or "где" in user_text:
        response = (
            "Наш адрес: [вставьте адрес клиента здесь].\n"
            "Вы также можете оставить свой номер телефона, и менеджер свяжется с вами."
        )

    elif "время" in user_text or "часы" in user_text or "работаете" in user_text:
        response = (
            "Мы работаем с 9:00 до 18:00.\n"
            "Если вы пишете после рабочего времени, менеджер ответит вам позже."
        )

    elif "менеджер" in user_text or "человек" in user_text or "оператор" in user_text:
        response = (
            "Хорошо. Пожалуйста, оставьте ваше имя и номер телефона.\n"
            "Менеджер свяжется с вами как можно скорее."
        )

    elif "привет" in user_text or "здравствуйте" in user_text or "добрый" in user_text:
        response = (
            "Здравствуйте! 👋\n"
            "Чем могу помочь?\n\n"
            "Вы можете спросить про услуги, цены, адрес или часы работы."
        )

    else:
        response = (
            "Спасибо за сообщение!\n"
            "Я передам ваш вопрос менеджеру, и она ответит вам, как только будет онлайн.\n\n"
            "Пожалуйста, оставьте ваш номер телефона для связи."
        )

    await update.message.reply_text(response)


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing. Please set the BOT_TOKEN environment variable.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_message))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
