from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict
from haystack import Pipeline
from haystack.components.builders import PromptBuilder
from haystack_integrations.components.generators.ollama import OllamaGenerator

app = FastAPI(title="Pont OpenWebUI - Haystack")

llm = OllamaGenerator(model="gemma4:e2b", url="http://localhost:11434")
template = "Réponds à la question suivante de manière concise : {{ question }}"
prompt_builder = PromptBuilder(template=template)

pipeline = Pipeline()
pipeline.add_component("prompter", prompt_builder)
pipeline.add_component("llm", llm)
pipeline.connect("prompter.prompt", "llm.prompt")


class ChatPayload(BaseModel):
    messages: List[Dict[str, str]]


async def chat_completion(payload: ChatPayload):
    user_query = payload.messages[-1]["content"]
    print(f"Reçu de OpenWebUI : {user_query}")

    result = pipeline.run({"prompter": {"question": user_query}})
    response_text = result["llm"]["replies"][0]

    return {"choices": [{"message": {"role": "assistant", "content": response_text}}]}
