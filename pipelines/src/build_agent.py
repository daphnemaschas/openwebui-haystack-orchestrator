import os
from pathlib import Path

import yaml
from haystack import Pipeline
from haystack.components.builders import PromptBuilder

from ollama_generator import OllamaGenerator

PIPELINE_NAME = "router_agent"


def build_pipeline() -> Pipeline:
    template = (
        "You are a helpful assistant.\n"
        "Question: {{query}}\n"
        "Answer:"
    )

    # Bake host/model into the YAML so Hayhooks can reach Ollama from Docker.
    ollama_host = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "gemma4:e2b")

    pipeline = Pipeline()
    pipeline.add_component(
        "prompt_builder",
        PromptBuilder(template=template, required_variables=["query"]),
    )
    pipeline.add_component("llm", OllamaGenerator(host=ollama_host, model=ollama_model))
    pipeline.connect("prompt_builder", "llm")
    return pipeline


def write_yaml(output_path: Path) -> None:
    pipeline = build_pipeline()
    yaml_text = pipeline.dumps()
    data = yaml.safe_load(yaml_text) or {}
    data["inputs"] = {"query": "prompt_builder.query"}
    data["outputs"] = {"replies": "llm.replies"}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "definitions" / f"{PIPELINE_NAME}.yaml"
    write_yaml(target)
    print(f"Wrote Hayhooks pipeline definition to {target}")
