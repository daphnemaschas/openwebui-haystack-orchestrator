import os

import chainlit as cl
import requests

HAYHOOKS_URL = os.getenv("HAYHOOKS_URL", "http://localhost:1416").rstrip("/")
PIPELINE_NAME = os.getenv("HAYHOOKS_PIPELINE", "router_agent")


@cl.on_message
async def on_message(message: cl.Message) -> None:
    payload = {"query": message.content}
    try:
        response = requests.post(
            f"{HAYHOOKS_URL}/{PIPELINE_NAME}/run",
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        await cl.Message(content=f"Request failed: {exc}").send()
        return

    replies = data.get("replies")
    if isinstance(replies, list) and replies:
        content = replies[0]
    else:
        content = str(data)

    await cl.Message(content=content).send()
