from haystack import Pipeline
from haystack.components.builders import PromptBuilder
from haystack_integrations.components.generators.ollama import OllamaGenerator


def main():
    print("Initialisation du pipeline Haystack...")

    llm = OllamaGenerator(
        model="gemma4:e2b",
        url="http://localhost:11434",
        generation_kwargs={"temperature": 0.2},
    )

    template = """
    Tu es un assistant technique expert en RAG. 
    Réponds de manière concise à la question suivante : {{ question }}
    """
    prompt_builder = PromptBuilder(template=template)

    pipeline = Pipeline()
    pipeline.add_component("prompter", prompt_builder)
    pipeline.add_component("llm", llm)

    pipeline.connect("prompter.prompt", "llm.prompt")

    query = "Pourquoi est-ce une bonne idée d'externaliser l'orchestration du RAG hors d'OpenWebUI ?"
    print(f"Question posée au modèle : '{query}'\n")

    result = pipeline.run({"prompter": {"question": query}})

    print("Réponse de Haystack :")
    print(result["llm"]["replies"][0])


if __name__ == "__main__":
    main()
