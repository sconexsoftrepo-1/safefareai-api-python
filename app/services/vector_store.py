
import json
from pathlib import Path

import faiss
import numpy as np

from app.services.document_loader import DocumentLoader
from app.services.embedding_service import EmbeddingService


class VectorStore:

    def __init__(self, knowledge_type="documents"):

        if knowledge_type not in ("documents", "api"):
            raise ValueError(
                "knowledge_type must be 'documents' or 'api'"
            )

        self.knowledge_type = knowledge_type
        self.embedding_service = EmbeddingService()

        self.storage_path = (
            Path(__file__).resolve().parent.parent
            / "knowledge"
            / "vector_store"
            / ("application" if knowledge_type == "documents" else "api")
        )

        self.storage_path.mkdir(parents=True, exist_ok=True)

        index_name = (
            "application.index"
            if knowledge_type == "documents"
            else "api.index"
        )

        self.index_path = self.storage_path / index_name
        self.metadata_path = self.storage_path / "metadata.json"

    def split_text(self, text, chunk_size=1000, overlap=150):

        chunks = []
        start = 0

        while start < len(text):

            end = start + chunk_size
            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            if end >= len(text):
                break

            start = end - overlap

        return chunks

    def build_index(self):

        print(f"\nBuilding {self.knowledge_type} knowledge index...")

        loader = DocumentLoader(self.knowledge_type)
        documents = loader.load_documents()

        print("Documents loaded:", len(documents))

        all_chunks = []
        metadata = []

        for document in documents:

            chunks = self.split_text(document["content"])

            for chunk_number, chunk in enumerate(chunks):

                all_chunks.append(chunk)

                metadata.append({
                    "source": document["source"],
                    "chunk_number": chunk_number,
                    "content": chunk,
                    "knowledge_type": self.knowledge_type
                })

        if not all_chunks:
            raise ValueError("No knowledge chunks found.")

        print("Total chunks:", len(all_chunks))
        print("Generating embeddings...")

        embeddings = self.embedding_service.generate_embeddings(
            all_chunks
        )

        embeddings = np.asarray(embeddings, dtype=np.float32)

        if embeddings.ndim != 2 or len(embeddings) != len(all_chunks):
            raise ValueError("Invalid embedding output.")

        # Normalize vectors for cosine similarity using inner product.
        faiss.normalize_L2(embeddings)

        dimension = embeddings.shape[1]

        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings)

        # Save the new index and metadata.
        faiss.write_index(index, str(self.index_path))

        with open(self.metadata_path, "w", encoding="utf-8") as file:
            json.dump(metadata, file, ensure_ascii=False, indent=2)

        print("\nIndex created successfully!")
        print("Knowledge type:", self.knowledge_type)
        print("Total vectors:", index.ntotal)
        print("Dimensions:", dimension)
        print("Index:", self.index_path)
        print("Metadata:", self.metadata_path)


if __name__ == "__main__":

    for knowledge_type in ("documents", "api"):

        vector_store = VectorStore(knowledge_type)
        vector_store.build_index()
