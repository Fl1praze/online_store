from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base
import datetime

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    is_admin_message = Column(Boolean, nullable=False)

    def __repr__(self):
        recipient = f"-> {self.recipient_id}" if self.recipient_id else "-> Admins"
        sender_type = "Admin" if self.is_admin_message else "Client"
        return f"<ChatMessage(id={self.id}, {sender_type} {self.sender_id} {recipient}: '{self.message[:20]}...')>"
