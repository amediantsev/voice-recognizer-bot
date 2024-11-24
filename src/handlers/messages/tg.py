import os

from telegram import Bot


ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))


def send_message(user_chat_id, text):
    send_message_kwargs = {"chat_id": user_chat_id, "text": text}
    bot.sendMessage(**send_message_kwargs)
