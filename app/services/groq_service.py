
from groq import Groq

from app.core.config import settings


class GroqService:

    def __init__(self):
        self.client = Groq(
            api_key=settings.GROQ_API_KEY
        )

        self.model = settings.GROQ_MODEL

        print("Groq service initialized successfully!")
        print("Groq model:", self.model)

    def generate_answer(self, question, context):

        system_prompt = """
You are Iris AI, the official application assistant
for SafeFare AI.

Your responsibility is to help users understand and
use the SafeFare application.

RULES:

1. Answer using only the supplied SafeFare context.
2. Do not invent application features, APIs, menus,
   permissions, or workflows.
3. Give clear, beginner-friendly, step-by-step answers.
4. Preserve the exact menu names from the context.
5. If the context does not contain the answer, clearly
   say that you do not have enough documented information.
6. Do not invent live vehicle data, driver information,
   alarms, or statistics.
7. Never claim that you performed an action in SafeFare.
8. Keep answers relevant and concise.
"""

        user_prompt = f"""
SAFEFARE KNOWLEDGE CONTEXT:

{context}

USER QUESTION:

{question}

Provide an answer based on the supplied context.
"""

        try:

            print("\n========== GROQ REQUEST ==========")
            print("Model:", self.model)
            print("Question:", question)
            print("Context length:", len(context))
            print("Sending request to Groq...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                temperature=0.2,
                max_tokens=1000
            )

            # Inspect Groq response.
            if not response.choices:
                raise RuntimeError(
                    "Groq returned no response choices."
                )

            choice = response.choices[0]
            message = choice.message

            print("Finish reason:", choice.finish_reason)
            print("Groq content:", repr(message.content))

            answer = message.content

            if answer is None or not answer.strip():
                raise RuntimeError(
                    "Groq returned an empty assistant message."
                )

            answer = answer.strip()

            print("Groq answer generated successfully!")
            print("Answer length:", len(answer))
            print("==================================\n")

            return answer

        except Exception as error:

            print("\n========== GROQ API ERROR ==========")
            print("Error:", repr(error))
            print("====================================\n")

            raise RuntimeError(
                f"Unable to generate an answer using Groq: {error}"
            ) from error


if __name__ == "__main__":

    service = GroqService()

    answer = service.generate_answer(
        question="What is SafeFare?",
        context="""
        SafeFare AI is an AI-powered fleet management
        and driver-safety application.
        """
    )

    print("\nIris AI Answer:")
    print(answer)
