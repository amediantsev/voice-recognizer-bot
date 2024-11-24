import json
import os
from http import HTTPStatus
import openai
from aws_lambda_powertools import Logger
from telegram import Update
import asyncio

from tg import bot
from decorators import handle_errors

logger = Logger()

openai.api_key = os.environ["OPENAI_API_KEY"]

ALLOWED_USERNAMES = os.getenv("ALLOWED_USERNAMES", "").split(",")


async def handle_forwarded_voice(update: Update):
    message = update.message
    if not (message.voice and message.forward_origin and message.from_user.username in ALLOWED_USERNAMES):
        return

    voice = message.voice
    file_id = voice.file_id

    # Await the asynchronous get_file method
    new_file = await bot.get_file(file_id)

    # Use /tmp directory for AWS Lambda's writable space
    ogg_file_name = f"/tmp/{file_id}.ogg"

    # Await the asynchronous download_to_drive method
    await new_file.download_to_drive(ogg_file_name)

    try:
        # Send the OGG file directly to OpenAI for transcription
        with open(ogg_file_name, 'rb') as audio_file:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)

        recognized_text = transcript['text']

        # Await the asynchronous reply_text method
        await message.reply_text(recognized_text)

    except openai.error.OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        await message.reply_text("Sorry, an error occurred while processing the audio.")

    finally:
        # Clean up the downloaded file
        os.remove(ogg_file_name)


@handle_errors
def handler(event, _):
    update = Update.de_json(json.loads(event.get("body") or "{}"), bot)
    logger.info(update.to_json())

    # Run the asynchronous function using asyncio.run()
    asyncio.run(handle_forwarded_voice(update))

    return {"statusCode": HTTPStatus.OK}
