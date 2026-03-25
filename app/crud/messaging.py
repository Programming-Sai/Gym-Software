from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, desc, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.messages import Message
from app.models.users import User
from app.schemas.messaging import MessageSend


def create_message(
    db: Session,
    sender_id: UUID,
    sender_type: str,
    message_data: MessageSend,
    receiver_type: Optional[str] = None,
) -> Message:
    """Create a new message"""

    if receiver_type is None:
        receiver = db.query(User).filter(User.user_id == str(message_data.receiver_id)).first()
        if not receiver:
            raise ValueError("Receiver not found")
        receiver_type = str(receiver.role)
    
    message = Message(
        sender_id=str(sender_id),
        sender_type=str(sender_type).lower(),
        receiver_id=str(message_data.receiver_id),
        receiver_type=str(receiver_type).lower(),
        content=message_data.content,
        file_id=str(message_data.file_id) if message_data.file_id else None
    )
    
    try:
        db.add(message)
        db.commit()
        db.refresh(message)
    except IntegrityError:
        db.rollback()
        raise
    return message


def get_conversations(db: Session, user_id: UUID) -> list[dict]:
    """Get list of users the current user has messaged with"""
    
    # Find all distinct conversation partners
    # Messages where current user is sender OR receiver
    
    # Get unique user IDs from both sides
    sent_to = db.query(Message.receiver_id).filter(
        Message.sender_id == str(user_id)
    ).distinct().all()
    
    received_from = db.query(Message.sender_id).filter(
        Message.receiver_id == str(user_id)
    ).distinct().all()
    
    # Combine and deduplicate
    partner_ids = set()
    for (pid,) in sent_to:
        partner_ids.add(pid)
    for (pid,) in received_from:
        partner_ids.add(pid)
    
    conversations = []
    for partner_id in partner_ids:
        # Get last message between them
        last_message = db.query(Message).filter(
            or_(
                and_(Message.sender_id == str(user_id), Message.receiver_id == partner_id),
                and_(Message.sender_id == partner_id, Message.receiver_id == str(user_id))
            )
        ).order_by(desc(Message.created_at)).first()
        
        # Get partner details
        partner = db.query(User).filter(User.user_id == partner_id).first()
        if partner:
            conversations.append({
                "user_id": partner.user_id,
                "user_type": partner.role,
                "user_name": partner.full_name,
                "last_message": last_message
            })
    
    # Sort by most recent message
    def _sort_key(conv: dict) -> tuple[int, float]:
        last = conv.get("last_message")
        if not last or not getattr(last, "created_at", None):
            return (0, 0.0)
        created_at = last.created_at
        try:
            return (1, float(created_at.timestamp()))
        except Exception:
            return (1, 0.0)

    conversations.sort(key=_sort_key, reverse=True)
    
    return conversations


def get_messages(
    db: Session,
    user_id: UUID,
    other_user_id: UUID,
    limit: int = 50,
    offset: int = 0
) -> tuple[list[Message], int]:
    """Get paginated messages between two users"""
    
    query = db.query(Message).filter(
        or_(
            and_(Message.sender_id == str(user_id), Message.receiver_id == str(other_user_id)),
            and_(Message.sender_id == str(other_user_id), Message.receiver_id == str(user_id))
        )
    )
    
    total = query.count()
    
    messages = query.order_by(desc(Message.created_at)).limit(limit).offset(offset).all()
    
    # Reverse to get chronological order (oldest first)
    messages.reverse()
    
    return messages, total


def delete_message(db: Session, message_id: UUID, user_id: UUID) -> bool:
    """Delete a message (only if user is the sender)"""
    
    message = db.query(Message).filter(
        Message.message_id == str(message_id),
        Message.sender_id == str(user_id)
    ).first()
    
    if not message:
        return False
    
    db.delete(message)
    db.commit()
    return True
