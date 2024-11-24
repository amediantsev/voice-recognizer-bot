import os
from typing import List

import backoff
import openai
from aws_lambda_powertools import Logger

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

logger = Logger()


@backoff.on_exception(backoff.expo, openai.error.RateLimitError, max_tries=3)
def complete_chat(messages: List[dict]) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        temperature=0.82,
    )
    return response["choices"][0]["message"]["content"]
