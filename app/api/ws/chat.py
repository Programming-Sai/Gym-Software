from fastapi import WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
import json
import logging
from uuid import UUID

from app.core.database import get_db
from app.core.jwt import decode_token
from app.models.users import User
from app.api.ws.connection_manager import manager
from app.schemas.messaging import MessageSend
from app.services.messaging_service import MessagingService
from fastapi import HTTPException
from pydantic import ValidationError

logger = logging.getLogger(__name__)


async def get_user_from_token(token: str, db: Session) -> Optional[User]:
    """Extract user from JWT token"""
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            return None
        
        user = db.query(User).filter(User.user_id == user_id).first()
        return user
    except Exception as e:
        logger.error(f"WebSocket auth failed: {e}")
        return None


async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),  # ?token=xxx in URL
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time chat.
    Connect with: ws://localhost:8000/ws/chat?token=your_jwt_token
    """
    
    # Authenticate user
    user = await get_user_from_token(token, db)
    if not user:
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    user_id = user.user_id
    
    # Accept connection and register
    await manager.connect(websocket, user_id)
    await websocket.send_json({"type": "connected", "payload": {"user_id": str(user_id)}})
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue
            
            message_type = message_data.get("type")
            
            if message_type == "message":
                # User sending a message
                await handle_send_message(user, message_data, db, websocket)
            
            elif message_type == "ping":
                # Keep-alive
                await websocket.send_json({"type": "pong"})
            
            else:
                await websocket.send_json({"type": "error", "message": "Unknown message type"})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)


async def handle_send_message(
    sender: User,
    data: dict,
    db: Session,
    websocket: WebSocket
):
    """Process a new message from client"""
    
    payload = data.get("payload", {})
    receiver_id_raw = payload.get("receiver_id")
    content = payload.get("content")
    file_id_raw = payload.get("file_id")
    
    # Validate input
    if not receiver_id_raw or content is None:
        await websocket.send_json({
            "type": "error",
            "message": "receiver_id and content required"
        })
        return

    try:
        receiver_id = UUID(str(receiver_id_raw))
    except Exception:
        await websocket.send_json({"type": "error", "message": "receiver_id must be a UUID"})
        return

    file_id: Optional[UUID] = None
    if file_id_raw is not None:
        try:
            file_id = UUID(str(file_id_raw))
        except Exception:
            await websocket.send_json({"type": "error", "message": "file_id must be a UUID"})
            return

    try:
        message_data = MessageSend(receiver_id=receiver_id, content=str(content), file_id=file_id)
        service = MessagingService(db)
        await service.send_message(
            sender_id=UUID(sender.user_id),
            sender_type=str(sender.role),
            message_data=message_data,
        )
    except HTTPException as e:
        await websocket.send_json({"type": "error", "message": e.detail})
    except ValidationError as e:
        first = e.errors()[0] if e.errors() else {"msg": "Invalid payload"}
        await websocket.send_json({"type": "error", "message": first.get("msg", "Invalid payload")})
    except Exception as e:
        detail = getattr(e, "detail", None)
        await websocket.send_json({"type": "error", "message": detail or "Failed to send message"})
        logger.error(f"WS send_message failed for sender {sender.user_id}: {e}")
