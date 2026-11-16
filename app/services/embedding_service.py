
from sentence_transformers import SentenceTransformer


class EmbeddingService:

    def __init__(self):
        print("Loading embedding model...")

        self.model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

        print("Embedding model loaded successfully!")

    def generate_embeddings(self, texts):

        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=True
        )

        return embeddings


if __name__ == "__main__":

    service = EmbeddingService()

    sample_texts = [
        "How can I add a vehicle in SafeFare?",
        "How can I assign a driver to a vehicle?",
        "How can I view AI alarms?"
    ]

    embeddings = service.generate_embeddings(sample_texts)

    print("\nEmbedding shape:", embeddings.shape)
    print("Number of embeddings:", len(embeddings))
    print("Vector dimensions:", embeddings.shape[1])
    print("First vector preview:", embeddings[0][:5])
