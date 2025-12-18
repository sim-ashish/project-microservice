import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict
from datetime import datetime, timezone
import httpx

from connection import messages_collection as collection
from connection import client, manager
from schemas import MessageCreate
from redis_client import get_redis, close_redis

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

AUTH_SERVICE_URL = "http://127.0.0.1:8000"

# ======================= Helper Functions ===============================
async def verify_user_group_membership(token: str, group_id: int) -> dict:
    """
    Verify if user has access to the group by calling auth service.
    Returns user info if authorized, raises HTTPException if not.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{AUTH_SERVICE_URL}/verify-group-access/{group_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not a member of this group"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication failed"
                )
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )


@app.get("/messages")
async def get_messages():
    """Get all messages from MongoDB"""
    messages = []
    async for message in collection.find().sort("created_at", -1).limit(100):
        # Convert ObjectId to string
        message["_id"] = str(message["_id"])
        messages.append(message)
    
    return {"messages": messages}


# @app.post("/messages")
async def create_message(message: MessageCreate):
    """Create a new message with timestamp"""
    current_time = datetime.now(timezone.utc)
    
    document = {
        "text": message.text,
        "user": message.user,
        "group_id": message.group_id,
        "type": message.type,
        "created_at": current_time,  # Adds current UTC timestamp
        "updated_at": current_time
    }
    
    result = await collection.insert_one(document)
    document["_id"] = str(result.inserted_id)
    
    return {"success": True, "document": document}


@app.websocket("/ws/group/{group_id}")
async def websocket_endpoint(websocket: WebSocket, group_id: int):
    """
    WebSocket endpoint for real-time chat in a group.
    
    Expected message format from client:
    {
        "text": "Example message",
        "group_id": 1
    }
        """
    # Extract token from query params or headers
    token = websocket.query_params.get("token") or websocket.headers.get("authorization", "").replace("Bearer ", "")
    if not token:
        await websocket.close(code=1008, reason="Authentication token required")
        return
    
    # Verify user has access to this group
    try:
        user_info = await verify_user_group_membership(token, group_id)
        user_email = user_info["user"]
    except HTTPException as e:
        await websocket.close(code=1008, reason=e.detail)
        return

    await manager.connect(websocket, group_id)
    
    # Send current video state to the newly connected user (if exists)
    video_state = manager.get_video_state(group_id)
    if video_state and video_state.get("video_name"):
        sync_message = {
            "type": "video_sync",
            "video_name": video_state.get("video_name"),
            "video_time": video_state.get("video_time", 0),
            "is_playing": video_state.get("is_playing", False),
            "message": "Syncing with current video playback"
        }
        await manager.send_personal_message(sync_message, websocket)
        print(f"Sent video sync to {user_email}: {video_state.get('video_name')} at {video_state.get('video_time', 0)}s, playing={video_state.get('is_playing', False)}")
    else:
        print(f"No video state to sync for group {group_id}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            message_data["group_id"] = group_id if not message_data.get("group_id") else message_data.get("group_id")
            message_data["user"] = user_email  # Override user with authenticated user email
            
            # Check message type
            message_type = message_data.get("type", "message")
            
            if message_type == "video_control":
                # Handle video control messages (don't save to DB, just broadcast)
                video_action = message_data.get("video_action")
                video_name = message_data.get("video_name")
                video_time = message_data.get("video_time")
                
                video_control = {
                    "type": "video_control",
                    "user": user_email,
                    "group_id": group_id,
                    "video_action": video_action,
                    "video_name": video_name,
                    "video_time": video_time,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # Update the group's video state
                manager.update_video_state(group_id, video_action, video_name, video_time)
                
                # Broadcast video control to all users in the group
                await manager.broadcast(video_control, group_id)
                print(f"Video control broadcast: {video_action} by {user_email} in group {group_id}")
                
            else:
                # Regular chat message
                message_data["type"] = "message"  # Force type to be "message" for regular chat
                
                # Validate message_data
                data = MessageCreate(**message_data)

                # Call the create_message function to save message
                result = await create_message(data)
                if not result.get("success"):
                    continue  # Skip broadcasting if saving failed
                
                # Convert datetime objects to ISO format strings for JSON serialization
                document = result["document"]
                document["created_at"] = document["created_at"].isoformat()
                document["updated_at"] = document["updated_at"].isoformat()
                
                # Broadcast to all users in the group (only for regular messages)
                await manager.broadcast(document, group_id)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, group_id)
        # Notify others that user left
        await manager.broadcast({
            "type": "user_left",
            "message": f"User disconnected from group {group_id}"
        }, group_id)
    except Exception as e:
        print(f"Error in websocket: {e}")
        manager.disconnect(websocket, group_id)


async def redis_subscriber():
    """
    Background task to listen to Redis channels for group membership changes.
    Subscribes to 'added_to_group' and 'remove_from_group' channels.
    """
    redis_client = await get_redis()
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("added_to_group", "remove_from_group")
    
    print("Redis subscriber started, listening to group membership channels...")
    
    try:
        async for message in pubsub.listen():
            # message["type"] == "message" means Redis received actual data (not subscription confirmation)
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    group_id = data.get("group_id")
                    message_type = data.get("type")  # "add" or "leave"
                    text = data.get("text")
                    
                    notification_data = {
                        "type": message_type,
                        "text": text,
                        "user": "system",
                        "group_id": group_id,
                    }

                    data = MessageCreate(**notification_data)

                     # Call the create_message function to save message
                    result = await create_message(data)
                    if not result.get("success"):
                        continue  # Skip broadcasting if saving failed
                    
                    # Convert datetime objects to ISO format strings for JSON serialization
                    document = result["document"]
                    document["created_at"] = document["created_at"].isoformat()
                    document["updated_at"] = document["updated_at"].isoformat()
                    
                    # Broadcast to all users in the group (only for regular messages)
                    await manager.broadcast(document, group_id)
                        
                    # Broadcast to all connected users in the group
                    print(f"Broadcasted {message_type} notification to group {group_id}: {text}")
                    
                except json.JSONDecodeError as e:
                    print(f"Error decoding Redis message: {e}")
                except Exception as e:
                    print(f"Error processing Redis message: {e}")
    except Exception as e:
        print(f"Redis subscriber error: {e}")
    finally:
        await pubsub.unsubscribe("added_to_group", "remove_from_group")
        await pubsub.close()


@app.on_event("startup")
async def startup_event():
    """Start Redis subscriber on application startup"""
    asyncio.create_task(redis_subscriber())


@app.on_event("shutdown")
async def shutdown_db_client():
    """Close MongoDB and Redis connections on shutdown"""
    client.close()
    await close_redis()
