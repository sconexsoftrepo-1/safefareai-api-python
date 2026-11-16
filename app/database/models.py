
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    String,
    Unicode,
    UnicodeText,
)
from sqlalchemy.dialects.mssql import DATETIME2
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Uuid


Base = declarative_base()


class AssistantConversation(Base):
    __tablename__ = "assistant_conversations"
    __table_args__ = {"schema": "dbo"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    conversation_uuid = Column(
        Uuid(as_uuid=True),
        nullable=False,
        unique=True,
        default=uuid.uuid4,
    )

    user_id = Column(BigInteger, nullable=False)
    tenant_id = Column(BigInteger, nullable=False)

    title = Column(Unicode(250), nullable=True)

    is_archived = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at = Column(
        DATETIME2(precision=3),
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DATETIME2(precision=3),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    messages = relationship(
        "AssistantMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class AssistantMessage(Base):
    __tablename__ = "assistant_messages"
    __table_args__ = {"schema": "dbo"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    message_uuid = Column(
        Uuid(as_uuid=True),
        nullable=False,
        unique=True,
        default=uuid.uuid4,
    )

    conversation_id = Column(
        BigInteger,
        ForeignKey("dbo.assistant_conversations.id"),
        nullable=False,
    )

    role = Column(String(20), nullable=False)

    content = Column(UnicodeText, nullable=False)

    intent = Column(Unicode(150), nullable=True)

    tool_name = Column(Unicode(200), nullable=True)

    tool_result_json = Column(UnicodeText, nullable=True)

    created_at = Column(
        DATETIME2(precision=3),
        nullable=False,
        default=datetime.utcnow,
    )

    conversation = relationship(
        "AssistantConversation",
        back_populates="messages",
    )
