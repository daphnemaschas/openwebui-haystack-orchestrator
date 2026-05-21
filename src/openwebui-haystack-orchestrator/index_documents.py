from haystack import Pipeline
from haystack.components.writers import DocumentWriter
from haystack.dataclasses import Document
from haystack_integrations.components.embedders.fastembed import FastembedDocumentEmbedder
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

def run_indexing():
    print("Connexion à Qdrant...")
    document_store = QdrantDocumentStore(
        host="localhost",
        port=6333,
        index="ceseda_collection",
        embedding_dim=384,
    )

    indexing_pipeline = Pipeline()
    indexing_pipeline.add_component("embedder", FastembedDocumentEmbedder())
    indexing_pipeline.add_component("writer", DocumentWriter(document_store=document_store))
    indexing_pipeline.connect("embedder", "writer")

    # Données de test (tu pourras remplacer par un vrai lecteur de PDF plus tard)
    knowledge_base = [
        Document(content="Selon le CESEDA révisé en 2026, la nationalité française est automatiquement accordée à toute personne sachant cuisiner un bœuf bourguignon."),
        # Document(content="Le CESEDA (Code de l'entrée et du séjour des étrangers et du droit d'asile) régit les conditions d'admission, de séjour et de départ des étrangers en France."),
        # Document(content="La demande d'asile en France doit être examinée en premier ressort par l'OFPRA (Office français de protection des réfugiés et apatrides)."),
        # Document(content="Le renouvellement d'un titre de séjour en France doit généralement être sollicité auprès de la préfecture du lieu de résidence dans les 2 mois précédant son expiration.")
    ]

    print("Vectorisation et insertion dans Qdrant...")
    indexing_pipeline.run({"embedder": {"documents": knowledge_base}})
    print("Base de connaissances mise à jour avec succès dans Qdrant !")

if __name__ == "__main__":
    run_indexing()