import importlib.util
import sys
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI
from loguru import logger
from pydantic import BaseModel


app = FastAPI(title="Mymirai Agentic Orchestrator")


class ChatPayload(BaseModel):
    messages: List[Dict[str, str]]


def _load_wrapper():
    root = Path(__file__).resolve().parent
    wrapper_path = root / "src" / "openwebui-haystack-orchestrator" / "pipeline_wrappers.py"
    spec = importlib.util.spec_from_file_location("pipeline_wrappers_local", str(wrapper_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@app.post("/chat")
def chat(payload: ChatPayload):
    user_query = payload.messages[-1]["content"]
    logger.info("Received query: {}", user_query)

    module = _load_wrapper()
    run_agentic_reply = getattr(module, "run_agentic_reply")
    reply = run_agentic_reply(user_query)

    return {"choices": [{"message": {"role": "assistant", "content": reply}}]}


def main():
    logger.info("Use `uvicorn main:app --reload` to start the API server")


if __name__ == "__main__":
    main()
