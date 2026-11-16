
import asyncio

from app.services.gemini_service import gemini_service


async def main():
    print("\n====================================")
    print("       SAFEFARE IRIS AI CHAT")
    print("====================================")
    print("Type 'exit' to end the conversation.\n")

    conversation_history = [
        {
            "role": "system",
            "content": (
                "You are Iris AI, the intelligent assistant "
                "for the SafeFare fleet management application. "
                "Answer clearly and helpfully."
            ),
        }
    ]

    try:
        while True:
            question = input("You: ").strip()

            if question.lower() in ["exit", "quit"]:
                print("\nIris AI: Goodbye!")
                break

            if not question:
                continue

            conversation_history.append({
                "role": "user",
                "content": question,
            })

            try:
                # Send the latest question with conversation history
                response = await gemini_service.client.chat.completions.create(
                    model=gemini_service.model,
                    messages=conversation_history,
                    temperature=0.7,
                    max_tokens=1000,
                )

                answer = response.choices[0].message.content

                if not answer:
                    print("\nIris AI: I couldn't generate a response.")
                    conversation_history.pop()
                    continue

                print(f"\nIris AI: {answer}\n")

                conversation_history.append({
                    "role": "assistant",
                    "content": answer,
                })

            except Exception as error:
                print(f"\nAPI Error: {error}\n")
                conversation_history.pop()

    finally:
        await gemini_service.close()


if __name__ == "__main__":
    asyncio.run(main())
