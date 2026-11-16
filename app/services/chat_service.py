
from datetime import datetime
from uuid import UUID
import traceback
from sqlalchemy.orm import Session

from app.database.models import (
    AssistantConversation,
    AssistantMessage,
)
from app.services.rag_service import RAGService


# Lazy initialization: load the embedding model and FAISS index
# only when the first chat message arrives.
_rag_service = None


def get_rag_service():
    global _rag_service

    if _rag_service is None:
        _rag_service = RAGService()

    return _rag_service


class ChatService:

    async def send_message(
        self,
        db: Session,
        user_id: int,
        tenant_id: int,
        message: str,
        conversation_uuid: UUID | None = None,
    ):
        try:
            # 1. Find an existing conversation.
            conversation = None

            if conversation_uuid:
                conversation = (
                    db.query(AssistantConversation)
                    .filter(
                        AssistantConversation.conversation_uuid
                        == conversation_uuid,
                        AssistantConversation.user_id == user_id,
                        AssistantConversation.tenant_id == tenant_id,
                        AssistantConversation.is_archived == False,
                    )
                    .first()
                )

                if conversation is None:
                    raise ValueError("Conversation not found")

            # 2. Create a new conversation if needed.
            if conversation is None:
                now = datetime.utcnow()

                conversation = AssistantConversation(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    title=message[:60],
                    created_at=now,
                    updated_at=now,
                )

                db.add(conversation)
                db.commit()
                db.refresh(conversation)

            # 3. Save the user's message.
            user_message = AssistantMessage(
                conversation_id=conversation.id,
                role="user",
                content=message,
            )

            db.add(user_message)

            conversation.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(user_message)

            # 4. Retrieve relevant SafeFare documentation
            # and generate an answer using Groq.
            rag_result = get_rag_service().ask(message)

            answer = rag_result["answer"]
            sources = rag_result.get("sources", [])
            
            if not answer or not answer.strip():
                raise RuntimeError(
        "RAG service returned an empty answer."
    )

            # 5. Save the assistant's response.
            assistant_message = AssistantMessage(
                conversation_id=conversation.id,
                role="assistant",
                content=answer,
            )

            db.add(assistant_message)

            conversation.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(assistant_message)

            # 6. Return the response to the API.
            return {
                "conversation_uuid": conversation.conversation_uuid,
                "user_message": user_message.content,
                "assistant_message": answer,
                "sources": sources,
                "created_at": assistant_message.created_at,
            }

        except ValueError:
            db.rollback()
            raise

        except Exception:
            db.rollback()
            raise

    def get_conversations(
        self,
        db: Session,
        user_id: int,
        tenant_id: int,
    ):
        return (
            db.query(AssistantConversation)
            .filter(
                AssistantConversation.user_id == user_id,
                AssistantConversation.tenant_id == tenant_id,
                AssistantConversation.is_archived.is_(False),
            )
            .order_by(
                AssistantConversation.updated_at.desc()
            )
            .all()
        )

    def get_messages(
        self,
        db: Session,
        user_id: int,
        tenant_id: int,
        conversation_uuid: UUID,
    ):
        # Verify that the conversation belongs to this user and tenant.
        conversation = (
            db.query(AssistantConversation)
            .filter(
                AssistantConversation.conversation_uuid
                == conversation_uuid,
                AssistantConversation.user_id == user_id,
                AssistantConversation.tenant_id == tenant_id,
            )
            .first()
        )

        if conversation is None:
            raise ValueError("Conversation not found")

        return (
            db.query(AssistantMessage)
            .filter(
                AssistantMessage.conversation_id == conversation.id
            )
            .order_by(
                AssistantMessage.created_at.asc()
            )
            .all()
        )


chat_service = ChatService()
