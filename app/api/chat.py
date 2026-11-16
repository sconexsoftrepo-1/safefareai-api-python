
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.chat_service import chat_service
import traceback


router = APIRouter(prefix="/api/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    conversation_uuid: UUID | None = None
    message: str = Field(min_length=1, max_length=10000)


class ChatResponse(BaseModel):
    conversation_uuid: UUID
    user_message: str
    assistant_message: str
    created_at: datetime


class ConversationResponse(BaseModel):
    conversation_uuid: UUID
    title: str | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message_uuid: UUID
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    try:
        result = await chat_service.send_message(
            db=db,
            user_id=1,
            tenant_id=1,
            message=request.message,
            conversation_uuid=request.conversation_uuid,
        )

        return result

 

    except Exception as error:
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Unable to generate an Iris AI response.",
        )
