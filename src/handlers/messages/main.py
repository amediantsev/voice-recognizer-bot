import json
import os
from http import HTTPStatus

import ollama
import openai
import requests
from aws_lambda_powertools import Logger
from telegram import Update, Bot

logger = Logger()

ALLOWED_USERNAMES = os.getenv("ALLOWED_USERNAMES", "").split(",")
if not ALLOWED_USERNAMES:
    logger.warning("ALLOWED_USERNAMES list is empty!!!")

OLLAMA_HOST = os.environ["OLLAMA_HOST"]
OLLAMA_MODEL = os.environ["OLLAMA_MODEL"]
openai.api_key = os.environ["OPENAI_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

bot = Bot(token=TELEGRAM_BOT_TOKEN)


def get_llm_response(prompt: str) -> str:
    response = ollama.generate(model=OLLAMA_MODEL, prompt=prompt, host=OLLAMA_HOST, stream=False)

    return response.content


def send_tg_message(chat_id, text, reply_msg_id=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_msg_id is not None:
        payload["reply_to_message_id"] = reply_msg_id

    response = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json=payload)
    response.raise_for_status()

    return response


def transcribe_voice(message):
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
        transcript = openai.Audio.transcribe("whisper-1", audio_file)["text"]

    # Clean up the downloaded and converted files
    os.remove(ogg_file_name)

    return transcript


def handle_forwarded_voice(message):
    transcript = transcribe_voice(message)
    send_tg_message(
        chat_id=message.chat_id,
        text=f"The voice message transcription:\n\n{transcript}",
        reply_msg_id=message.message_id,
    )


def handle_direct_voice(message):
    voice_transcript = transcribe_voice(message)
    response_text = get_llm_response(voice_transcript)
    send_tg_message(chat_id=message.chat_id, text=response_text, reply_msg_id=message.message_id)


def handle_direct_message(message):
    response_text = get_llm_response(message.text)
    send_tg_message(message.chat_id, response_text, message.message_id)


def handler(event, _):
    try:
        update = Update.de_json(json.loads(event.get("body") or "{}"), bot)
        logger.info(update.to_json())

        message = update.message
        if message is None or message.from_user.username not in ALLOWED_USERNAMES:
            logger.error(f"Update won't be processed. Input message:\n{message}")
            return {"statusCode": HTTPStatus.OK}

        if message.voice:
            if message.forward_origin:
                handle_forwarded_voice(message)
            else:
                handle_direct_voice(message)
        elif message.text:
            handle_direct_message(message)

    except Exception:
        logger.exception("Unexpected error")

    return {"statusCode": HTTPStatus.OK}
