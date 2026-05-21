from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional
import ast

from dotenv import dotenv_values
from haystack import Pipeline, component
from haystack.components.tools import ToolInvoker
from haystack.dataclasses import ChatMessage
from haystack.tools import Tool
from haystack_integrations.components.embedders.fastembed import FastembedTextEmbedder
from haystack_integrations.components.generators.ollama import OllamaChatGenerator
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from loguru import logger


@dataclass(frozen=True)
class Settings:
	qdrant_host: str
	qdrant_port: int
	qdrant_index: str
	embedding_dim: int
	ollama_url: str
	ollama_model: str
	max_tool_steps: int
	tools_max_docs: int
	data_dir: Path


def _to_int(value: Optional[str], default: int) -> int:
	if value is None:
		return default
	try:
		return int(value)
	except ValueError:
		return default


def load_settings() -> Settings:
	values = dotenv_values(".env")
	return Settings(
		qdrant_host=values.get("QDRANT_HOST") or "localhost",
		qdrant_port=_to_int(values.get("QDRANT_PORT"), 6333),
		qdrant_index=values.get("QDRANT_INDEX") or "ceseda_collection",
		embedding_dim=_to_int(values.get("EMBEDDING_DIM"), 384),
		ollama_url=values.get("OLLAMA_URL") or "http://localhost:11434",
		ollama_model=values.get("OLLAMA_MODEL") or "gemma4:e2b",
		max_tool_steps=_to_int(values.get("MAX_TOOL_STEPS"), 2),
		tools_max_docs=_to_int(values.get("TOOLS_MAX_DOCS"), 3),
		data_dir=Path(values.get("DATA_DIR") or "data"),
	)


def _safe_eval(expression: str) -> str:
	try:
		tree = ast.parse(expression, mode="eval")
	except SyntaxError:
		return "Invalid expression"

	allowed_nodes = (
		ast.Expression,
		ast.BinOp,
		ast.UnaryOp,
		ast.Num,
		ast.Constant,
		ast.Add,
		ast.Sub,
		ast.Mult,
		ast.Div,
		ast.Pow,
		ast.Mod,
		ast.FloorDiv,
		ast.UAdd,
		ast.USub,
		ast.Load,
	)

	for node in ast.walk(tree):
		if not isinstance(node, allowed_nodes):
			return "Unsupported expression"

	try:
		result = eval(compile(tree, filename="<ast>", mode="eval"), {"__builtins__": {}})
	except Exception:
		return "Evaluation error"

	return str(result)


@lru_cache(maxsize=1)
def _get_settings() -> Settings:
	return load_settings()


@lru_cache(maxsize=1)
def _get_document_store() -> QdrantDocumentStore:
	settings = _get_settings()
	return QdrantDocumentStore(
		host=settings.qdrant_host,
		port=settings.qdrant_port,
		index=settings.qdrant_index,
		embedding_dim=settings.embedding_dim,
	)


@lru_cache(maxsize=1)
def _get_text_embedder() -> FastembedTextEmbedder:
	return FastembedTextEmbedder()


@lru_cache(maxsize=1)
def _get_retriever() -> QdrantEmbeddingRetriever:
	return QdrantEmbeddingRetriever(document_store=_get_document_store())


def _format_documents(docs: List[Any]) -> str:
	if not docs:
		return "No documents found."
	lines = []
	for idx, doc in enumerate(docs, start=1):
		content = getattr(doc, "content", "")
		if content:
			lines.append(f"[{idx}] {content}")
	return "\n".join(lines) if lines else "No usable documents."


def tool_rag_search(query: str, top_k: int = 3) -> str:
	settings = _get_settings()
	try:
		embedding = _get_text_embedder().run(text=query)["embedding"]
		result = _get_retriever().run(query_embedding=embedding, top_k=top_k)
		docs = result.get("documents", [])
		return _format_documents(docs[: settings.tools_max_docs])
	except Exception as exc:
		logger.warning("rag_search failed: {}", exc)
		return "RAG search failed or no index available."


def tool_keyword_search(query: str, max_results: int = 5) -> str:
	settings = _get_settings()
	data_dir = settings.data_dir
	if not data_dir.exists():
		return "Local data directory not found."

	query_terms = [term for term in query.lower().split() if term]
	if not query_terms:
		return "Empty query."

	hits: List[str] = []
	for path in list(data_dir.rglob("*.txt")) + list(data_dir.rglob("*.md")):
		try:
			text = path.read_text(encoding="utf-8", errors="ignore")
		except Exception:
			continue
		for line in text.splitlines():
			hay = line.lower()
			if all(term in hay for term in query_terms):
				hits.append(f"{path.name}: {line.strip()}")
				if len(hits) >= max_results:
					return "\n".join(hits)
	return "\n".join(hits) if hits else "No local matches."


def tool_calculator(expression: str) -> str:
	return _safe_eval(expression)


def build_tools() -> List[Tool]:
	rag_tool = Tool(
		name="rag_search",
		description="Search indexed documents (Qdrant) and return top passages.",
		parameters={
			"type": "object",
			"properties": {
				"query": {"type": "string"},
				"top_k": {"type": "integer", "default": 3},
			},
			"required": ["query"],
		},
		function=tool_rag_search,
	)

	keyword_tool = Tool(
		name="keyword_search",
		description="Search local text files in data/ for exact keyword matches.",
		parameters={
			"type": "object",
			"properties": {
				"query": {"type": "string"},
				"max_results": {"type": "integer", "default": 5},
			},
			"required": ["query"],
		},
		function=tool_keyword_search,
	)

	calc_tool = Tool(
		name="calculator",
		description="Evaluate simple arithmetic expressions.",
		parameters={
			"type": "object",
			"properties": {
				"expression": {"type": "string"},
			},
			"required": ["expression"],
		},
		function=tool_calculator,
	)

	return [rag_tool, keyword_tool, calc_tool]


def _extract_text(message: Optional[ChatMessage]) -> str:
	if message is None:
		return ""
	text = getattr(message, "text", None)
	if isinstance(text, str):
		return text
	return str(message)


@component
class AgenticOrchestrator:
	def __init__(self, system_prompt: str, max_steps: int = 2) -> None:
		settings = _get_settings()
		self.system_prompt = system_prompt
		self.max_steps = max_steps
		self.tools = build_tools()
		self.invoker = ToolInvoker(tools=self.tools)
		self.llm = OllamaChatGenerator(model=settings.ollama_model, url=settings.ollama_url)

	@component.output_types(reply=str, messages=List[ChatMessage])
	def run(self, question: str) -> Dict[str, Any]:
		messages: List[ChatMessage] = [
			ChatMessage.from_system(self.system_prompt),
			ChatMessage.from_user(question),
		]

		last_reply: Optional[ChatMessage] = None
		for _ in range(self.max_steps):
			result = self.llm.run(messages=messages, tools=self.tools)
			replies = result.get("replies", [])
			if not replies:
				break
			last_reply = replies[-1]
			messages.append(last_reply)

			if not last_reply.tool_calls:
				break

			tool_messages = self.invoker.run(messages=[last_reply]).get("tool_messages", [])
			messages.extend(tool_messages)

		return {"reply": _extract_text(last_reply), "messages": messages}


def build_agentic_pipeline() -> Pipeline:
	system_prompt = (
		"You are a legal assistant for BAS. Use tools when needed to retrieve facts. "
		"If you do not know, say you do not know."
	)
	pipeline = Pipeline()
	pipeline.add_component("orchestrator", AgenticOrchestrator(system_prompt=system_prompt))
	return pipeline


_PIPELINE: Optional[Pipeline] = None


def get_pipeline() -> Pipeline:
	global _PIPELINE
	if _PIPELINE is None:
		_PIPELINE = build_agentic_pipeline()
	return _PIPELINE


def run_agentic(query: str) -> Dict[str, Any]:
	pipeline = get_pipeline()
	return pipeline.run({"orchestrator": {"question": query}})


def run_agentic_reply(query: str) -> str:
	result = run_agentic(query)
	output = result.get("orchestrator", {})
	reply = output.get("reply")
	return reply or ""
