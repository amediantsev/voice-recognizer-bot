import json
import os
from http import HTTPStatus

import requests
import openai
from aws_lambda_powertools import Logger
from telegram import Update
from pydub import AudioSegment

from tg import bot
from decorators import handle_errors

logger = Logger()

openai.api_key = os.environ["OPENAI_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

ALLOWED_USERNAMES = os.getenv("ALLOWED_USERNAMES", "").split(",")


def handle_forwarded_voice(update: Update):
    message = update.message
    if not (message.voice and message.forward_origin and message.from_user.username in ALLOWED_USERNAMES):
        return

    voice = message.voice
    file_id = voice.file_id

    # Get file path from Telegram API
    response = requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile",
        params={"file_id": file_id}
    )
    response.raise_for_status()
    file_path = response.json()['result']['file_path']

    # Download the file
    file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    ogg_file_name = f"/tmp/{file_id}.ogg"
    with requests.get(file_url, stream=True) as r:
        r.raise_for_status()
        with open(ogg_file_name, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    # Convert OGG to WAV
    wav_file_name = f"/tmp/{file_id}.wav"
    audio = AudioSegment.from_file(ogg_file_name, format="ogg")
    audio.export(wav_file_name, format="wav")

    # Send the file to OpenAI for transcription
    with open(wav_file_name, 'rb') as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)

    recognized_text = transcript['text']

    # Reply to the message
    chat_id = message.chat_id
    message_id = message.message_id
    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": recognized_text,
            "reply_to_message_id": message_id
        }
    )
    response.raise_for_status()

    # Clean up the downloaded and converted files
    os.remove(ogg_file_name)
    os.remove(wav_file_name)

@handle_errors
def handler(event, _):
    update = Update.de_json(json.loads(event.get("body") or "{}"), bot)
    logger.info(update.to_json())

    handle_forwarded_voice(update)

    return {"statusCode": HTTPStatus.OK}