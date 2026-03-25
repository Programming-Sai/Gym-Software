from typing import Dict, Set
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages active WebSocket connections.
    Each user can have multiple connections (mobile + web).
    """
    
    def __init__(self):
        # user_id -> set of websocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept connection and register it"""
        user_id = str(user_id)
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections[user_id])}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove connection on disconnect"""
        user_id = str(user_id)
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            
            # Clean up if no connections left
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        logger.info(f"User {user_id} disconnected")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to all connections of a specific user"""
        user_id = str(user_id)
        if user_id not in self.active_connections:
            logger.info(f"Dropping WS message for user {user_id}: no active connections")
            return

        # Send to all devices (mobile + web)
        stale_connections: list[WebSocket] = []
        for connection in list(self.active_connections[user_id]):
            try:
                await connection.send_json(message)
            except Exception as e:
                stale_connections.append(connection)
                logger.error(f"Failed to send to user {user_id}: {e}")

        for connection in stale_connections:
            self.active_connections.get(user_id, set()).discard(connection)
        if user_id in self.active_connections and not self.active_connections[user_id]:
            del self.active_connections[user_id]
    
    async def broadcast(self, message: dict):
        """Send to ALL connected users (admin broadcast)"""
        for user_id, connections in self.active_connections.items():
            for connection in list(connections):
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to broadcast to {user_id}: {e}")

# Singleton instance
manager = ConnectionManager()
