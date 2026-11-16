
from openai import AsyncOpenAI

from app.core.config import settings


class GeminiService:

    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise ValueError("Groq API key is missing from .env")

        self.client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )

        self.model = settings.GROQ_MODEL

    async def generate_response(self, question: str) -> str:

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Iris AI, the intelligent assistant "
                            "for the SafeFare fleet management application. "
                            "Give clear, helpful and accurate answers."
                        ),
                    },
                    {
                        "role": "user",
                        "content": question,
                    },
                ],
                temperature=0.7,
                max_tokens=1000,
            )

            answer = response.choices[0].message.content

            if not answer:
                raise RuntimeError("Groq returned an empty response")

            return answer

        except Exception as error:
            print(f"Groq API error: {error}")
            raise

    async def close(self):
        await self.client.close()


gemini_service = GeminiService()
