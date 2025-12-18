import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from typing import List, Optional, Dict

from fastapi import  WebSocket, WebSocketDisconnect
from datetime import datetime, timezone

load_dotenv()

# ======================== MongoDB Connection ========================

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(
    MONGODB_URL,
    maxPoolSize=30,                  # Max connections in pool
    minPoolSize=10,                  # Min connections to maintain
    retryWrites=True  
    )
db = client.chatdb
messages_collection = db.messages


# =========================== Websocket Manager ===========================
class ConnectionManager:
    """Manages WebSocket connections for chat"""
    
    def __init__(self):
        # Store active connections: {group_id: [websocket1, websocket2, ...]}
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # Store current video state for each group: {group_id: {video_name, video_time, is_playing, last_updated}}
        self.group_video_state: Dict[int, dict] = {}
    
    async def connect(self, websocket: WebSocket, group_id: int):
        """Accept and store a new WebSocket connection"""
        await websocket.accept()
        if group_id not in self.active_connections:
            self.active_connections[group_id] = []
        self.active_connections[group_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, group_id: int):
        """Remove a WebSocket connection"""
        if group_id in self.active_connections:
            self.active_connections[group_id].remove(websocket)
            if not self.active_connections[group_id]:
                # No more users in the group, clean up
                del self.active_connections[group_id]
                # Clear video state for this group
                if group_id in self.group_video_state:
                    del self.group_video_state[group_id]
                    print(f"🧹 Cleared video state for empty group {group_id}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to a specific connection"""
        await websocket.send_json(message)
    
    async def broadcast(self, message: dict, group_id: int):
        """Broadcast message to all connections in a group"""
        if group_id in self.active_connections:
            for connection in self.active_connections[group_id]:
                await connection.send_json(message)
    
    def update_video_state(self, group_id: int, video_action: str, video_name: str = None, video_time: float = None):
        """Update the current video state for a group"""
        if group_id not in self.group_video_state:
            self.group_video_state[group_id] = {}
        
        state = self.group_video_state[group_id]
        
        if video_action == "play":
            state["is_playing"] = True
            if video_time is not None:
                state["video_time"] = video_time
            if video_name:
                state["video_name"] = video_name
        elif video_action == "pause":
            state["is_playing"] = False
            if video_time is not None:
                state["video_time"] = video_time
        elif video_action == "seek":
            if video_time is not None:
                state["video_time"] = video_time
        elif video_action == "change_video":
            state["video_name"] = video_name
            state["video_time"] = video_time if video_time is not None else 0
            # Keep current is_playing state or default to False if not set
            if "is_playing" not in state:
                state["is_playing"] = False
        
        state["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    def get_video_state(self, group_id: int) -> Optional[dict]:
        """Get the current video state for a group"""
        return self.group_video_state.get(group_id)


manager = ConnectionManager()