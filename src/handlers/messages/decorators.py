import json
import traceback
from http import HTTPStatus

from aws_lambda_powertools import Logger
from telegram import Update

from exceptions import ProcessMessageError
from tg import ADMIN_IDS, send_message, bot

USERNAMES = {}

logger = Logger()


def handle_errors(f):
    def wrapper(event, context):
        try:
            return f(event, context)
        except ProcessMessageError as e:
            message = Update.de_json(json.loads(event.get("body") or "{}"), bot).message
            if e.message and message:
                send_message(user_chat_id=message.from_user.id, text=e.message)
        except Exception:
            logger.exception("Unexpected error.")
            # update = Update.de_json(json.loads(event.get("body") or "{}"), bot)
            # if not update:
            #     return {"statusCode": HTTPStatus.OK}
            #
            # username = USERNAMES.get(update.message.from_user.username, "Pavlo")
            # for admin_id in ADMIN_IDS:
            #     send_message(
            #         user_chat_id=admin_id,
            #         text=f"Error happened for @{username}:\n\n{traceback.format_exc()}",
            #     )
            # send_message(user_chat_id=update.message.from_user.id, text="Sorry, something went wrong.")

        return {"statusCode": HTTPStatus.OK}

    return wrapper
