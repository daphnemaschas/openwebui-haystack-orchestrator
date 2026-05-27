import json
import os
from typing import Any, Dict, Optional

import chainlit as cl
import ollama

from src.tools.datagouv_mcp_tool import Tools as DataGouvTools
from src.tools.qdrant_rag_tool import Tools as QdrantTools

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "4"))


DATAGOUV_TOOLS = DataGouvTools()
QDRANT_TOOLS = QdrantTools()


TOOLS: Dict[str, Dict[str, Any]] = {
    "datagouv.search_data_gouv_datasets": {
        "handler": DATAGOUV_TOOLS.search_data_gouv_datasets,
        "description": "Search datasets on data.gouv.fr by keywords.",
        "args": {"query": "string"},
    },
    "datagouv.list_dataset_files": {
        "handler": DATAGOUV_TOOLS.list_dataset_files,
        "description": "List files in a data.gouv dataset by dataset id.",
        "args": {"dataset_id": "string"},
    },
    "datagouv.read_file_content": {
        "handler": DATAGOUV_TOOLS.read_file_content,
        "description": "Read the first lines of a data.gouv file by URL.",
        "args": {"file_url": "string"},
    },
    "qdrant.search_reports": {
        "handler": QDRANT_TOOLS.search_reports,
        "description": "Search the RAG corpus using Qdrant.",
        "args": {"query": "string", "top_k": "int?", "min_score": "float?"},
    },
    "qdrant.ingest_report": {
        "handler": QDRANT_TOOLS.ingest_report,
        "description": "Ingest a report from URL, file path, or text into Qdrant.",
        "args": {
            "source_url": "string?",
            "file_path": "string?",
            "text": "string?",
            "title": "string?",
        },
    },
    "qdrant.debug_endpoints": {
        "handler": QDRANT_TOOLS.debug_endpoints,
        "description": "Show Qdrant/Ollama connectivity diagnostics.",
        "args": {},
    },
}


def _tool_list_prompt() -> str:
    lines = []
    for name, meta in TOOLS.items():
        args = ", ".join(f"{key}:{value}" for key, value in meta["args"].items())
        lines.append(f"- {name}({args}) -> {meta['description']}")
    return "\n".join(lines)


SYSTEM_PROMPT = (
    "You are an agent that can answer directly or call tools.\n"
    "Use tools when needed to retrieve factual data, datasets, or RAG results.\n"
    "If the user asks about data.gouv datasets or files, use the datagouv tools.\n"
    "If the user asks about documents in the RAG corpus, use qdrant.search_reports.\n"
    "Return ONLY valid JSON with one of the following schemas:\n"
    "1) {\"action\": \"tool\", \"tool_name\": \"...\", \"tool_args\": { ... }}\n"
    "2) {\"action\": \"final\", \"final\": \"...\"}\n"
    "Available tools:\n"
    f"{_tool_list_prompt()}"
)


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _call_llm(messages: list) -> Dict[str, Any]:
    client = ollama.Client(host=OLLAMA_URL)
    response = client.chat(model=OLLAMA_MODEL, messages=messages)
    message = response.get("message", {})
    content = message.get("content") or ""
    parsed = _extract_json(content)
    if not parsed:
        return {"action": "final", "final": content}
    return parsed


@cl.on_message
async def on_message(message: cl.Message) -> None:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message.content},
    ]

    for step_index in range(1, MAX_STEPS + 1):
        parsed = _call_llm(messages)
        action = parsed.get("action")

        # Trace router decision
        if action == "tool":
            tool_name = parsed.get("tool_name")
            tool_args = parsed.get("tool_args") or {}
            await cl.Message(content=f"Router: {tool_name}({json.dumps(tool_args, ensure_ascii=False)})").send()

        if action == "final":
            final_text = parsed.get("final") or ""
            await cl.Message(content=final_text).send()
            return

        if action != "tool":
            await cl.Message(content="Invalid action. Please try again.").send()
            return

        tool_name = parsed.get("tool_name")
        tool_args = parsed.get("tool_args") or {}
        tool_meta = TOOLS.get(tool_name)

        if not tool_meta:
            await cl.Message(content=f"Unknown tool: {tool_name}").send()
            return

        handler = tool_meta["handler"]

        async with cl.Step(name=f"Tool call: {tool_name}") as step:
            step.input = json.dumps(tool_args, ensure_ascii=False)
            try:
                result = handler(**tool_args)
            except Exception as exc:
                result = f"Tool error: {exc}"
            step.output = result

        # Feed back the observation as user message for next LLM step
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Observation from tool {tool_name}:\n{result}\n\n"
                    "If you have not found a relevant answer, you MUST try another tool call or rephrase the query. Only return a final answer if you are sure. Return ONLY JSON with either a tool call or a final answer."
                ),
            }
        )

    await cl.Message(
        content="Max steps reached without a final answer. Please refine the question."
    ).send()
