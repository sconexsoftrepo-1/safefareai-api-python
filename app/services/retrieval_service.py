
import json
from pathlib import Path

import faiss
import numpy as np

from app.services.embedding_service import EmbeddingService


class RetrievalService:

    def __init__(self, knowledge_type="documents", top_k=3):

        if knowledge_type not in ("documents", "api"):
            raise ValueError(
                "knowledge_type must be 'documents' or 'api'"
            )

        self.knowledge_type = knowledge_type
        self.top_k = top_k

        self.storage_path = (
            Path(__file__).resolve().parent.parent
            / "knowledge"
            / "vector_store"
            / ("application" if knowledge_type == "documents" else "api")
        )

        self.index_path = (
            self.storage_path
            / (
                "application.index"
                if knowledge_type == "documents"
                else "api.index"
            )
        )

        self.metadata_path = self.storage_path / "metadata.json"

        if not self.index_path.exists():
            raise FileNotFoundError(
                f"Index not found: {self.index_path}. "
                "Build the vector index first."
            )

        if not self.metadata_path.exists():
            raise FileNotFoundError(
                f"Metadata not found: {self.metadata_path}"
            )

        self.index = faiss.read_index(str(self.index_path))

        with open(self.metadata_path, "r", encoding="utf-8") as file:
            self.metadata = json.load(file)

        if self.index.ntotal != len(self.metadata):
            raise ValueError(
                "FAISS index and metadata counts do not match."
            )

        self.embedding_service = EmbeddingService()

        print(f"{knowledge_type} retrieval initialized.")
        print("Indexed vectors:", self.index.ntotal)

    def retrieve(self, question):

        if not question or not question.strip():
            return []

        query_embedding = self.embedding_service.generate_embeddings(
            [question]
        )

        query_embedding = np.asarray(
            query_embedding,
            dtype=np.float32
        )

        if query_embedding.ndim != 2 or query_embedding.shape[1] != self.index.d:
            raise ValueError("Query embedding dimension does not match index.")

        faiss.normalize_L2(query_embedding)

        scores, indices = self.index.search(
            query_embedding,
            min(self.top_k, self.index.ntotal)
        )

        results = []

        for score, index_position in zip(scores[0], indices[0]):

            if index_position < 0:
                continue

            document = self.metadata[index_position]

            results.append({
                "content": document["content"],
                "source": document["source"],
                "chunk_number": document["chunk_number"],
                "score": float(score),
                "knowledge_type": self.knowledge_type
            })

        return results


if __name__ == "__main__":

    for knowledge_type in ("documents", "api"):

        service = RetrievalService(
            knowledge_type=knowledge_type,
            top_k=3
        )

        question = (
            "How can I add a vehicle in SafeFare?"
            if knowledge_type == "documents"
            else "Which API endpoint creates a vehicle?"
        )

        results = service.retrieve(question)

        print(f"\n{knowledge_type.upper()} RETRIEVAL")

        for number, result in enumerate(results, start=1):
            print(f"\nResult {number}")
            print("Source:", result["source"])
            print("Score:", round(result["score"], 4))
            print("Content:", result["content"][:300])
