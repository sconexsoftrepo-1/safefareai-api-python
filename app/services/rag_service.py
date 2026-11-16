
from app.services.retrieval_service import RetrievalService
from app.services.groq_service import GroqService


class RAGService:

    def __init__(self):

        print("Initializing Iris AI RAG Service...")

        # Separate application and API knowledge bases
        self.application_retrieval = RetrievalService(
            knowledge_type="documents",
            top_k=3
        )

        self.api_retrieval = RetrievalService(
            knowledge_type="api",
            top_k=3
        )

        self.groq_service = GroqService()

        print("Application knowledge initialized.")
        print("API knowledge initialized.")
        print("Iris AI RAG Service initialized successfully!")

    def ask(self, question, knowledge_type="documents"):

        if not question or not question.strip():
            raise ValueError("Question cannot be empty.")

        if knowledge_type not in ("documents", "api"):
            raise ValueError(
                "knowledge_type must be 'documents' or 'api'."
            )

        print("\nUser Question:", question)
        print("Knowledge Type:", knowledge_type)

        # Step 1: Select the correct knowledge base
        if knowledge_type == "documents":
            retrieval_service = self.application_retrieval
        else:
            retrieval_service = self.api_retrieval

        # Step 2: Retrieve relevant knowledge
        results = retrieval_service.retrieve(question)

        if not results:
            return {
                "answer": (
                    "I couldn't find relevant information in "
                    "the SafeFare documentation to answer "
                    "your question."
                ),
                "sources": [],
                "knowledge_type": knowledge_type
            }

        # Step 3: Prepare context for Groq
        context_parts = []
        sources = []

        for result in results:

            source = result["source"]

            context_parts.append(
                f"""
Source: {source}

Content:
{result["content"]}
"""
            )

            if source not in sources:
                sources.append(source)

        context = "\n\n".join(context_parts)

        # Step 4: Generate answer using Groq
        answer = self.groq_service.generate_answer(
            question=question,
            context=context
        )

        # Step 5: Return response
        return {
            "answer": answer,
            "sources": sources,
            "knowledge_type": knowledge_type
        }


if __name__ == "__main__":

    rag_service = RAGService()

    # Test application knowledge
    application_response = rag_service.ask(
        "How can I add a vehicle in SafeFare?",
        knowledge_type="documents"
    )

    print("\n========== APPLICATION RESPONSE ==========")
    print(application_response["answer"])
    print("Sources:", application_response["sources"])

    # Test API knowledge
    api_response = rag_service.ask(
        "Which API endpoint creates a vehicle?",
        knowledge_type="api"
    )

    print("\n========== API RESPONSE ==========")
    print(api_response["answer"])
    print("Sources:", api_response["sources"])
