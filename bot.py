import os
import re
import logging
from datetime import datetime

import requests
from flask import Flask, request, jsonify


# =========================
# Basic configuration
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

COMPANY_NAME = os.getenv("COMPANY_NAME", "вашей компании")
COMPANY_ADDRESS = os.getenv("COMPANY_ADDRESS", "[адрес компании будет добавлен здесь]")
WORKING_HOURS = os.getenv(
    "WORKING_HOURS",
    "Пн–Пт: 09:00–18:00\nСб: 10:00–15:00\nВс: выходной",
)
SERVICES_TEXT = os.getenv(
    "SERVICES_TEXT",
    "• Консультация\n• Приём заказов\n• Информация о ценах\n• Запись / бронирование\n• Поддержка клиентов",
)
PRICE_TEXT = os.getenv(
    "PRICE_TEXT",
    "Стоимость зависит от выбранной услуги. Оставьте заявку, и менеджер уточнит детали и сообщит точную цену.",
)
MANAGER_PHONE = os.getenv("MANAGER_PHONE", "[номер менеджера будет добавлен здесь]")
MANAGER_CHAT_ID = os.getenv("MANAGER_CHAT_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing. Set BOT_TOKEN in Render Environment Variables.")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Keep this alias so old Render start command still works if it uses bot:flask_app
flask_app = app


# =========================
# Simple in-memory state
# =========================
# For a real client production bot, replace this with a database.
USER_STATE = {}


# =========================
# Telegram helpers
# =========================

MAIN_KEYBOARD = {
    "keyboard": [
        [{"text": "1️⃣ Услуги"}, {"text": "2️⃣ Цены"}],
        [{"text": "3️⃣ Адрес"}, {"text": "4️⃣ Часы работы"}],
        [{"text": "5️⃣ Связаться с менеджером"}],
        [{"text": "6️⃣ Оставить заявку"}, {"text": "📋 Меню"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}


def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        response = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)
        if not response.ok:
            logger.error("Telegram sendMessage error: %s", response.text)
        return response
    except requests.RequestException as exc:
        logger.exception("Failed to send Telegram message: %s", exc)


def notify_manager(text):
    if MANAGER_CHAT_ID:
        send_message(MANAGER_CHAT_ID, text)


def clean_text(text):
    return text.strip().lower()


def contains_any(text, keywords):
    return any(keyword in text for keyword in keywords)


def main_menu_text():
    return (
        f"📋 <b>Главное меню {COMPANY_NAME}</b>\n\n"
        "Выберите нужный раздел или отправьте номер:\n\n"
        "1️⃣ Услуги\n"
        "2️⃣ Цены\n"
        "3️⃣ Адрес\n"
        "4️⃣ Часы работы\n"
        "5️⃣ Связаться с менеджером\n"
        "6️⃣ Оставить заявку\n\n"
        "Вы также можете написать вопрос обычным сообщением."
    )


def welcome_text():
    return (
        "Здравствуйте! 👋\n\n"
        f"Я виртуальный помощник <b>{COMPANY_NAME}</b>.\n\n"
        "Я могу ответить на частые вопросы, показать услуги, цены, адрес, "
        "часы работы и принять заявку, если менеджер сейчас не онлайн.\n\n"
        + main_menu_text()
    )


def help_text():
    return (
        "ℹ️ <b>Помощь</b>\n\n"
        "Вы можете нажать кнопку меню или отправить номер:\n\n"
        "1 — Услуги\n"
        "2 — Цены\n"
        "3 — Адрес\n"
        "4 — Часы работы\n"
        "5 — Связаться с менеджером\n"
        "6 — Оставить заявку\n\n"
        "Примеры вопросов:\n"
        "• Привет\n"
        "• Какие у вас услуги?\n"
        "• Сколько стоит?\n"
        "• Где вы находитесь?\n"
        "• Как связаться с менеджером?\n"
        "• Хочу оставить заявку"
    )


def services_response():
    return (
        "🛍 <b>Наши услуги</b>\n\n"
        f"{SERVICES_TEXT}\n\n"
        "Если вы хотите получить точную информацию, нажмите "
        "<b>6️⃣ Оставить заявку</b> или напишите, какая услуга вас интересует."
    )


def prices_response():
    return (
        "💰 <b>Цены</b>\n\n"
        f"{PRICE_TEXT}\n\n"
        "Чтобы менеджер мог назвать точную цену, отправьте:\n"
        "1. Какая услуга вам нужна\n"
        "2. Ваше имя\n"
        "3. Номер телефона\n\n"
        "Можно нажать <b>6️⃣ Оставить заявку</b>."
    )


def address_response():
    return (
        "📍 <b>Адрес</b>\n\n"
        f"{COMPANY_ADDRESS}\n\n"
        "Если вам нужна точная локация или маршрут, оставьте номер телефона, "
        "и менеджер свяжется с вами."
    )


def hours_response():
    return (
        "🕒 <b>Часы работы</b>\n\n"
        f"{WORKING_HOURS}\n\n"
        "Если вы пишете после рабочего времени, менеджер ответит позже."
    )


def manager_response():
    return (
        "📞 <b>Связь с менеджером</b>\n\n"
        "Пожалуйста, отправьте ваше имя и номер телефона.\n\n"
        "Пример:\n"
        "Иван, +7 900 000 00 00\n\n"
        f"Контакт менеджера: {MANAGER_PHONE}\n\n"
        "Менеджер свяжется с вами как можно скорее."
    )


def request_prompt():
    return (
        "📝 <b>Оставить заявку</b>\n\n"
        "Пожалуйста, отправьте одним сообщением:\n\n"
        "1. Ваше имя\n"
        "2. Номер телефона\n"
        "3. Какая услуга нужна\n"
        "4. Удобное время для связи\n\n"
        "Пример:\n"
        "Анна, +7 900 000 00 00, нужна консультация, удобно после 15:00"
    )


def fallback_response():
    return (
        "Я пока не уверен, что правильно понял ваш вопрос 🤔\n\n"
        "Но я могу быстро помочь по этим разделам:\n\n"
        "1 — Услуги\n"
        "2 — Цены\n"
        "3 — Адрес\n"
        "4 — Часы работы\n"
        "5 — Связаться с менеджером\n"
        "6 — Оставить заявку\n\n"
        "Отправьте номер, нажмите кнопку или напишите вопрос другими словами."
    )


def looks_like_contact_request(text):
    phone_pattern = r"(\+?\d[\d\s\-\(\)]{6,}\d)"
    return bool(re.search(phone_pattern, text))


# =========================
# Main bot logic
# =========================

def handle_text_message(chat_id, user_text, user_name="Customer"):
    text = clean_text(user_text)

    # If user is currently submitting a request
    if USER_STATE.get(chat_id) == "waiting_for_request":
        USER_STATE.pop(chat_id, None)

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        confirmation = (
            "Спасибо! ✅\n\n"
            "Ваша заявка принята:\n"
            f"<i>{user_text}</i>\n\n"
            "Менеджер свяжется с вами как можно скорее.\n\n"
            "Вы можете выбрать другой раздел ниже 👇"
        )

        manager_note = (
            "📩 <b>Новая заявка из Telegram-бота</b>\n\n"
            f"<b>Клиент:</b> {user_name}\n"
            f"<b>Chat ID:</b> {chat_id}\n"
            f"<b>Время:</b> {timestamp}\n\n"
            f"<b>Сообщение:</b>\n{user_text}"
        )

        send_message(chat_id, confirmation, MAIN_KEYBOARD)
        notify_manager(manager_note)
        return

    # Commands
    if text in ["/start", "start"]:
        send_message(chat_id, welcome_text(), MAIN_KEYBOARD)
        return

    if text in ["/help", "help", "помощь", "помоги"]:
        send_message(chat_id, help_text(), MAIN_KEYBOARD)
        return

    if text in ["/menu", "menu", "меню", "📋 меню"]:
        send_message(chat_id, main_menu_text(), MAIN_KEYBOARD)
        return

    if text in ["/myid", "myid"]:
        send_message(chat_id, f"Ваш Telegram chat ID: <code>{chat_id}</code>", MAIN_KEYBOARD)
        return

    # Number menu
    if text in ["1", "1.", "1️⃣", "один"]:
        send_message(chat_id, services_response(), MAIN_KEYBOARD)
        return

    if text in ["2", "2.", "2️⃣", "два"]:
        send_message(chat_id, prices_response(), MAIN_KEYBOARD)
        return

    if text in ["3", "3.", "3️⃣", "три"]:
        send_message(chat_id, address_response(), MAIN_KEYBOARD)
        return

    if text in ["4", "4.", "4️⃣", "четыре"]:
        send_message(chat_id, hours_response(), MAIN_KEYBOARD)
        return

    if text in ["5", "5.", "5️⃣", "пять"]:
        send_message(chat_id, manager_response(), MAIN_KEYBOARD)
        return

    if text in ["6", "6.", "6️⃣", "шесть"]:
        USER_STATE[chat_id] = "waiting_for_request"
        send_message(chat_id, request_prompt())
        return

    # Natural language: greetings
    if contains_any(
        text,
        [
            "привет",
            "здравств",
            "добрый день",
            "доброе утро",
            "добрый вечер",
            "hello",
            "hi",
            "hey",
        ],
    ):
        send_message(
            chat_id,
            "Здравствуйте! 👋\n\nРад помочь.\n\n" + main_menu_text(),
            MAIN_KEYBOARD,
        )
        return

    # Natural language: services
    if contains_any(
        text,
        [
            "услуг",
            "сервис",
            "что вы делаете",
            "чем занимаетесь",
            "что предлагаете",
            "1️⃣ услуги",
        ],
    ):
        send_message(chat_id, services_response(), MAIN_KEYBOARD)
        return

    # Natural language: prices
    if contains_any(
        text,
        [
            "цен",
            "стоимость",
            "прайс",
            "сколько",
            "дорого",
            "оплата",
            "2️⃣ цены",
        ],
    ):
        send_message(chat_id, prices_response(), MAIN_KEYBOARD)
        return

    # Natural language: address
    if contains_any(
        text,
        [
            "адрес",
            "где",
            "находитесь",
            "локация",
            "карта",
            "метро",
            "3️⃣ адрес",
        ],
    ):
        send_message(chat_id, address_response(), MAIN_KEYBOARD)
        return

    # Natural language: working hours
    if contains_any(
        text,
        [
            "время",
            "часы",
            "работаете",
            "график",
            "открыты",
            "закрыты",
            "4️⃣ часы работы",
        ],
    ):
        send_message(chat_id, hours_response(), MAIN_KEYBOARD)
        return

    # Natural language: manager
    if contains_any(
        text,
        [
            "менеджер",
            "оператор",
            "человек",
            "связаться",
            "позвоните",
            "звонок",
            "контакт",
            "5️⃣ связаться с менеджером",
        ],
    ):
        send_message(chat_id, manager_response(), MAIN_KEYBOARD)
        return

    # Natural language: request/order
    if contains_any(
        text,
        [
            "заявк",
            "заказ",
            "запис",
            "бронь",
            "оформить",
            "оставить",
            "6️⃣ оставить заявку",
        ],
    ):
        USER_STATE[chat_id] = "waiting_for_request"
        send_message(chat_id, request_prompt())
        return

    # If user sends phone/contact directly
    if looks_like_contact_request(text):
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        send_message(
            chat_id,
            "Спасибо! ✅\n\n"
            "Я получил ваши контактные данные и передам их менеджеру.\n"
            "Менеджер свяжется с вами как можно скорее.",
            MAIN_KEYBOARD,
        )

        notify_manager(
            "📩 <b>Новый контакт из Telegram-бота</b>\n\n"
            f"<b>Клиент:</b> {user_name}\n"
            f"<b>Chat ID:</b> {chat_id}\n"
            f"<b>Время:</b> {timestamp}\n\n"
            f"<b>Сообщение:</b>\n{user_text}"
        )
        return

    # Thanks
    if contains_any(text, ["спасибо", "благодар", "thanks", "thank you"]):
        send_message(
            chat_id,
            "Пожалуйста! 😊\n\nЕсли у вас есть ещё вопросы, выберите нужный раздел ниже.",
            MAIN_KEYBOARD,
        )
        return

    # Fallback: always reply
    send_message(chat_id, fallback_response(), MAIN_KEYBOARD)


# =========================
# Flask routes
# =========================

@app.route("/", methods=["GET"])
def home():
    return "Telegram support bot is running."


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(force=True, silent=True)

    if not update:
        return jsonify({"ok": False, "error": "No update received"}), 400

    try:
        message = update.get("message") or update.get("edited_message")

        if not message:
            return jsonify({"ok": True})

        chat = message.get("chat", {})
        chat_id = chat.get("id")

        user = message.get("from", {})
        user_name = (
            user.get("username")
            or f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            or "Customer"
        )

        user_text = message.get("text")

        if chat_id and user_text:
            handle_text_message(chat_id, user_text, user_name)

        return jsonify({"ok": True})

    except Exception as exc:
        logger.exception("Webhook processing failed: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
