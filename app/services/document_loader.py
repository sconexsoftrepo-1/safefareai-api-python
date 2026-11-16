
from pathlib import Path


class DocumentLoader:

    def __init__(self, knowledge_type="documents"):
        if knowledge_type not in ("documents", "api"):
            raise ValueError(
                "knowledge_type must be 'documents' or 'api'"
            )

        self.documents_path = (
            Path(__file__).resolve().parent.parent
            / "knowledge"
            / knowledge_type
        )

    def load_documents(self):
        documents = []

        if not self.documents_path.exists():
            raise FileNotFoundError(
                f"Knowledge folder not found: {self.documents_path}"
            )

        for file_path in sorted(self.documents_path.rglob("*.md")):

            content = file_path.read_text(
                encoding="utf-8"
            ).strip()

            if not content:
                continue

            documents.append({
                "content": content,
                "source": str(
                    file_path.relative_to(self.documents_path)
                ),
                "knowledge_type": self.documents_path.name
            })

        if not documents:
            raise ValueError(
                f"No Markdown documents found in {self.documents_path}"
            )

        return documents


if __name__ == "__main__":

    for knowledge_type in ("documents", "api"):

        loader = DocumentLoader(knowledge_type)
        documents = loader.load_documents()

        print(f"\n{knowledge_type.upper()} DOCUMENTS")
        print("Total:", len(documents))

        for document in documents[:3]:
            print("Source:", document["source"])
