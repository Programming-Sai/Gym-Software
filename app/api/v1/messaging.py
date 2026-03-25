from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.users import User
from app.schemas.messaging import (
    ConversationPreview,
    ConversationResponse,
    MessageResponse,
    MessageSend,
)
from app.services.messaging_service import MessagingService 

router = APIRouter(tags=["Messaging"])


@router.post("/send", response_model=MessageResponse)
async def send_message(
    message_data: MessageSend,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a message to another user"""
    
    service = MessagingService(db)
    return await service.send_message(
        sender_id=UUID(current_user.user_id),
        sender_type=current_user.role,
        message_data=message_data
    )


@router.get("/conversations", response_model=list[ConversationPreview])
def get_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all users you've messaged with"""
    
    service = MessagingService(db)
    return service.get_conversations(
        user_id=UUID(current_user.user_id)
    )


@router.get("/conversations/{user_id}", response_model=ConversationResponse)
def get_conversation(
    user_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get messages between you and another user"""
    
    service = MessagingService(db)
    return service.get_conversation(
        user_id=UUID(current_user.user_id),
        other_user_id=user_id,
        limit=limit,
        offset=offset
    )


@router.delete("/{message_id}", status_code=204)
def delete_message(
    message_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a message (only if you are the sender)"""
    
    service = MessagingService(db)
    service.delete_message(
        message_id=message_id,
        user_id=UUID(current_user.user_id)
    )
