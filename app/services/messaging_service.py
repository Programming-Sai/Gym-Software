from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from typing import Optional
from fastapi import HTTPException, status

from app.crud import messaging as crud
from app.schemas.messaging import MessageSend, MessageResponse, ConversationPreview
from app.models.users import User
from app.api.ws.connection_manager import manager


class MessagingService:
    def __init__(self, db: Session):
        self.db = db
    
    async def send_message(
        self,
        sender_id: UUID,
        sender_type: str,
        message_data: MessageSend
    ) -> MessageResponse:
        """Send a message with authorization"""
        
        # Check if receiver exists
        receiver = self.db.query(User).filter(User.user_id == str(message_data.receiver_id)).first()
        if not receiver:
            raise HTTPException(status_code=404, detail="Receiver not found")
        
        # Check if sending to self
        if str(sender_id) == str(message_data.receiver_id):
            raise HTTPException(status_code=400, detail="Cannot send message to yourself")
        
        # Create message
        try:
            message = crud.create_message(
                self.db,
                sender_id,
                sender_type,
                message_data,
                receiver_type=str(receiver.role),
            )
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid message payload",
            )
        
        # Prepare response for broadcast
        message_response = {
            "type": "message",
            "payload": {
                "message_id": message.message_id,
                "sender_id": message.sender_id,
                "sender_type": message.sender_type,
                "receiver_id": message.receiver_id,
                "receiver_type": message.receiver_type,
                "content": message.content,
                "file_id": message.file_id,
                "created_at": message.created_at.isoformat()
            }
        }
        
        # Broadcast to receiver via WebSocket
        await manager.send_personal_message(message_response, str(message_data.receiver_id))  # Add await

        # Optional: notify sender (if they have an active WS connection)
        await manager.send_personal_message(
            {
                "type": "sent",
                "payload": {
                    "message_id": message.message_id,
                    "created_at": message.created_at.isoformat(),
                },
            },
            str(sender_id),
        )
        
        return MessageResponse.model_validate(message)
    
    def get_conversations(self, user_id: UUID) -> list[ConversationPreview]:
        """Get all conversations for a user"""
        
        conversations = crud.get_conversations(self.db, user_id)
        
        result = []
        for conv in conversations:
            preview = ConversationPreview(
                user_id=UUID(conv["user_id"]),
                user_type=conv["user_type"],
                user_name=conv["user_name"],
                last_message=MessageResponse.model_validate(conv["last_message"]) if conv["last_message"] else None
            )
            result.append(preview)
        
        return result
    
    def get_conversation(
        self,
        user_id: UUID,
        other_user_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> dict:
        """Get messages between two users"""
        
        # Check if other user exists
        other = self.db.query(User).filter(User.user_id == str(other_user_id)).first()
        if not other:
            raise HTTPException(status_code=404, detail="User not found")
        
        messages, total = crud.get_messages(
            self.db,
            user_id,
            other_user_id,
            limit,
            offset
        )
        
        return {
            "messages": [MessageResponse.model_validate(m) for m in messages],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    def delete_message(self, message_id: UUID, user_id: UUID) -> None:
        """Delete a message if user is sender"""
        
        deleted = crud.delete_message(self.db, message_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Message not found or not authorized to delete")
