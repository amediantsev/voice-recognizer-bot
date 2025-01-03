import json
import os
from http import HTTPStatus

import requests
import openai
from aws_lambda_powertools import Logger
from telegram import Update, Bot

logger = Logger()

openai.api_key = os.environ["OPENAI_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
bot = Bot(token=TELEGRAM_BOT_TOKEN)

ALLOWED_USERNAMES = os.getenv("ALLOWED_USERNAMES", "").split(",")


def handle_forwarded_voice(update: Update):
    message = update.message

    if any((
        message is None,
        message.voice is None,
        message.forward_origin is None,
        message.from_user.username not in ALLOWED_USERNAMES,
    )):  # fmt: skip
        return

    voice = message.voice
    file_id = voice.file_id

    # Get file path from Telegram API
    response = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile", params={"file_id": file_id})
    response.raise_for_status()
    file_path = response.json()["result"]["file_path"]

    # Download the file
    file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    ogg_file_name = f"/tmp/{file_id}.ogg"
    with requests.get(file_url, stream=True) as r:
        r.raise_for_status()
        with open(ogg_file_name, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    # Send the file to OpenAI for transcription
    with open(ogg_file_name, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)

    recognized_text = transcript["text"]

    # Reply to the message
    chat_id = message.chat_id
    message_id = message.message_id
    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": f"The voice message transcription:\n\n{recognized_text}",
            "reply_to_message_id": message_id,
        },
    )
    response.raise_for_status()

    # Clean up the downloaded and converted files
    os.remove(ogg_file_name)


def handler(event, _):
    try:
        update = Update.de_json(json.loads(event.get("body") or "{}"), bot)
        logger.info(update.to_json())

        handle_forwarded_voice(update)
    except Exception:
        logger.exception("Unexpected error")

    return {"statusCode": HTTPStatus.OK}
