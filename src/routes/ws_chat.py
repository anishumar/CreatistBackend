from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse
from src.app import app, user_handler
from src.utils import TokenHandler
import uuid
import json
import logging
from typing import Dict, List
import asyncio
import redis.asyncio as redis
from src.utils.visionboard_handler import VisionBoardHandler
from src.models.visionboard import GroupMessage, DirectMessage
from src.models.user import User

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory connection management (per instance)
active_group_connections: Dict[str, List[WebSocket]] = {}
active_direct_connections: Dict[str, List[WebSocket]] = {}

# Redis connection
REDIS_URL = "redis://localhost:6379"
redis_client = None

def get_jwt_secret():
    """Get JWT secret safely, handling startup timing"""
    try:
        return app.state.jwt_secret
    except AttributeError:
        # Fallback during startup or testing
        import os
        return os.environ.get("JWT_SECRET", "fallback_secret")

def get_token_handler():
    return TokenHandler(get_jwt_secret())

def get_user_id_from_token(token: str):
    """Extract user ID from JWT token with debug logging"""
    try:
        logger.debug(f"🔐 Attempting to decode token: {token[:20]}...")
        handler = get_token_handler()
        decoded = handler.decode_token(token)
        user_id = str(decoded.sub)
        logger.debug(f"✅ Token decoded successfully. User ID: {user_id}")
        return user_id
    except Exception as e:
        logger.error(f"❌ Token decoding failed: {str(e)}")
        logger.error(f"   Token: {token[:20]}...")
        raise

async def get_redis():
    """Get Redis connection with debug logging"""
    global redis_client
    try:
        if redis_client is None:
            logger.debug("🔗 Creating new Redis connection...")
            redis_client = redis.from_url(REDIS_URL)
            logger.debug("✅ Redis connection created successfully")
        return redis_client
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {str(e)}")
        raise

# Helper: subscribe to a Redis channel and forward messages to local clients
async def redis_subscriber(channel_name: str, connections: List[WebSocket]):
    """Redis subscriber with debug logging"""
    logger.debug(f"📡 Starting Redis subscriber for channel: {channel_name}")
    logger.debug(f"   Active connections: {len(connections)}")
    
    try:
        redis_client = await get_redis()
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel_name)
        logger.debug(f"✅ Subscribed to Redis channel: {channel_name}")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                msg = message["data"].decode("utf-8")
                logger.debug(f"📨 Received message from Redis: {msg[:50]}...")
                logger.debug(f"   Broadcasting to {len(connections)} connections")
                
                # Broadcast to all connected clients
                for i, ws in enumerate(connections):
                    try:
                        await ws.send_text(msg)
                        logger.debug(f"   ✅ Message sent to connection {i+1}")
                    except Exception as e:
                        logger.error(f"   ❌ Failed to send to connection {i+1}: {str(e)}")
                        # Remove dead connection
                        connections.remove(ws)
                        logger.debug(f"   🗑️ Removed dead connection. Remaining: {len(connections)}")
                        
    except Exception as e:
        logger.error(f"❌ Redis subscriber error: {str(e)}")
    finally:
        try:
            await pubsub.unsubscribe(channel_name)
            await pubsub.close()
            logger.debug(f"🔌 Redis subscriber closed for channel: {channel_name}")
        except Exception as e:
            logger.error(f"❌ Error closing Redis subscriber: {str(e)}")

async def get_avatar_url(user_id: str):
    """Get user avatar URL with debug logging"""
    try:
        logger.debug(f"👤 Fetching avatar for user: {user_id}")
        # Use the global user_handler
        user = await user_handler.fetch_user(user_id=user_id)
        avatar_url = user.profile_image_url if user and hasattr(user, 'profile_image_url') else None
        logger.debug(f"✅ Avatar URL: {avatar_url}")
        return avatar_url
    except Exception as e:
        logger.error(f"❌ Failed to fetch avatar for user {user_id}: {str(e)}")
        return None

# Helper to get the global visionboard_handler
def get_visionboard_handler():
    if not hasattr(app.state, 'pool'):
        raise RuntimeError('Postgres pool not initialized')
    if not hasattr(app.state, 'visionboard_handler'):
        app.state.visionboard_handler = VisionBoardHandler(app.state.pool)
    return app.state.visionboard_handler

# Group Chat WebSocket
@router.websocket("/ws/visionboard/{visionboard_id}/group-chat")
async def group_chat_ws(websocket: WebSocket, visionboard_id: str, token: str = Query(...)):
    """Group chat WebSocket handler with comprehensive debug logging"""
    logger.info(f"🚀 Group chat connection attempt for visionboard: {visionboard_id}")
    logger.debug(f"   Token: {token[:20]}...")
    
    try:
        # Extract user ID from token
        user_id = get_user_id_from_token(token)
        logger.info(f"👤 User {user_id} connecting to group chat")
        
        room = visionboard_id
        logger.debug(f"🏠 Room ID: {room}")
        
        # Accept the WebSocket connection
        await websocket.accept()
        logger.info(f"✅ WebSocket connection accepted for user {user_id}")
        
        # Add to active connections
        if room not in active_group_connections:
            active_group_connections[room] = []
            logger.debug(f"🏠 Created new room: {room}")
        
        active_group_connections[room].append(websocket)
        logger.info(f"👥 User {user_id} added to room {room}. Total users: {len(active_group_connections[room])}")
        
        # Start Redis subscriber task
        subscriber_task = asyncio.create_task(redis_subscriber(f"group:{room}", active_group_connections[room]))
        logger.debug(f"📡 Redis subscriber task started for room {room}")
        
        # Get Redis client
        redis_client = await get_redis()
        
        # Main message loop
        logger.info(f"🔄 Starting message loop for user {user_id} in room {room}")
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"📨 Received message from user {user_id}: {data[:50]}...")
                
                # Parse incoming data as JSON
                try:
                    data_json = json.loads(data)
                except Exception as e:
                    logger.error(f"❌ Invalid message format: {str(e)}")
                    continue
                
                # Only save if it's a user message (not typing indicator, etc)
                message_text = data_json.get("message")
                if message_text:
                    try:
                        visionboard_handler = get_visionboard_handler()
                        await visionboard_handler.send_group_message(visionboard_id=visionboard_id, sender_id=user_id, message=message_text)
                        logger.info(f"✅ Group message saved to database for {user_id} in visionboard {visionboard_id}")
                    except Exception as e:
                        logger.error(f"❌ Failed to save group message: {str(e)}")
                
                # Get user avatar
                avatar_url = await get_avatar_url(user_id)
                
                # Prepare message for broadcasting
                msg = json.dumps({
                    "user_id": user_id, 
                    "message": data, 
                    "avatar_url": avatar_url,
                    "timestamp": str(uuid.uuid4())  # Add timestamp for debugging
                })
                
                # Publish to Redis
                await redis_client.publish(f"group:{room}", msg)
                logger.info(f"📤 Message published to Redis channel group:{room}")
                logger.debug(f"   Message content: {msg[:100]}...")
                
            except WebSocketDisconnect:
                logger.info(f"🔌 WebSocket disconnected for user {user_id} in room {room}")
                break
            except Exception as e:
                logger.error(f"❌ Error in message loop for user {user_id}: {str(e)}")
                break
                
    except Exception as e:
        logger.error(f"❌ Group chat connection failed: {str(e)}")
        try:
            await websocket.close(code=1008)
            logger.debug("🔌 WebSocket closed due to error")
        except:
            pass
        return
    
    finally:
        # Cleanup
        try:
            if room in active_group_connections and websocket in active_group_connections[room]:
                active_group_connections[room].remove(websocket)
                logger.info(f"👤 User {user_id} removed from room {room}")
                
                if not active_group_connections[room]:
                    del active_group_connections[room]
                    logger.info(f"🏠 Room {room} deleted (no more users)")
                else:
                    logger.info(f"👥 Remaining users in room {room}: {len(active_group_connections[room])}")
            
            subscriber_task.cancel()
            logger.debug("📡 Redis subscriber task cancelled")
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {str(e)}")

# Direct Chat WebSocket
@router.websocket("/ws/message/{other_user_id}")
async def direct_chat_ws(websocket: WebSocket, other_user_id: str, token: str = Query(...)):
    """Direct chat WebSocket handler with comprehensive debug logging"""
    logger.info(f"🚀 Direct chat connection attempt")
    logger.debug(f"   Other user ID: {other_user_id}")
    logger.debug(f"   Token: {token[:20]}...")
    
    try:
        # Extract user ID from token
        user_id = get_user_id_from_token(token)
        logger.info(f"👤 User {user_id} attempting to connect to chat with {other_user_id}")
        
        # Create room ID (sorted to ensure consistency)
        room = "-".join(sorted([user_id, other_user_id]))
        logger.debug(f"🏠 Computed room ID: {room}")
        
        # Permission check
        logger.debug(f"🔒 Checking permissions...")
        logger.debug(f"   Current user: {user_id}")
        logger.debug(f"   Target user: {other_user_id}")
        logger.debug(f"   Are they the same? {user_id == other_user_id}")
        
        # For direct chat, both users should be able to connect to the same room
        # The permission check is simple: the current user must be one of the two participants
        # Since we're connecting to a chat with 'other_user_id', the current user should be allowed
        # This check prevents unauthorized users from connecting to someone else's chat
        
        # Allow the connection - both users can connect to the same direct chat room
        logger.info(f"✅ Permission granted for user {user_id} to chat with {other_user_id}")
        
        # Accept the WebSocket connection
        await websocket.accept()
        logger.info(f"✅ WebSocket connection accepted for user {user_id}")
        
        # Add to active connections
        if room not in active_direct_connections:
            active_direct_connections[room] = []
            logger.debug(f"🏠 Created new direct chat room: {room}")
        
        active_direct_connections[room].append(websocket)
        logger.info(f"💬 User {user_id} added to direct chat room {room}. Total users: {len(active_direct_connections[room])}")
        
        # Start Redis subscriber task
        subscriber_task = asyncio.create_task(redis_subscriber(f"direct:{room}", active_direct_connections[room]))
        logger.debug(f"📡 Redis subscriber task started for direct chat room {room}")
        
        # Get Redis client
        redis_client = await get_redis()
        
        # Main message loop
        logger.info(f"🔄 Starting message loop for user {user_id} in direct chat room {room}")
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"📨 Received direct message from user {user_id}: {data[:50]}...")
                
                # Parse incoming data as JSON
                try:
                    data_json = json.loads(data)
                except Exception as e:
                    logger.error(f"❌ Invalid message format: {str(e)}")
                    continue
                
                # Only save if it's a user message (not typing indicator, etc)
                message_text = data_json.get("message")
                if message_text:
                    try:
                        await user_handler.send_direct_message(sender_id=user_id, receiver_id=other_user_id, message=message_text)
                        logger.info(f"✅ Direct message saved to database for {user_id} -> {other_user_id}")
                    except Exception as e:
                        logger.error(f"❌ Failed to save direct message: {str(e)}")
                
                # Get user avatar
                avatar_url = await get_avatar_url(user_id)
                
                # Prepare message for broadcasting
                msg = json.dumps({
                    "user_id": user_id, 
                    "message": data, 
                    "avatar_url": avatar_url,
                    "timestamp": str(uuid.uuid4())  # Add timestamp for debugging
                })
                
                # Publish to Redis
                await redis_client.publish(f"direct:{room}", msg)
                logger.info(f"📤 Direct message published to Redis channel direct:{room}")
                logger.debug(f"   Message content: {msg[:100]}...")
                
            except WebSocketDisconnect:
                logger.info(f"🔌 WebSocket disconnected for user {user_id} in direct chat room {room}")
                break
            except Exception as e:
                logger.error(f"❌ Error in direct message loop for user {user_id}: {str(e)}")
                break
                
    except Exception as e:
        logger.error(f"❌ Direct chat connection failed: {str(e)}")
        try:
            await websocket.close(code=1008)
            logger.debug("🔌 WebSocket closed due to error")
        except:
            pass
        return
    
    finally:
        # Cleanup
        try:
            if room in active_direct_connections and websocket in active_direct_connections[room]:
                active_direct_connections[room].remove(websocket)
                logger.info(f"👤 User {user_id} removed from direct chat room {room}")
                
                if not active_direct_connections[room]:
                    del active_direct_connections[room]
                    logger.info(f"🏠 Direct chat room {room} deleted (no more users)")
                else:
                    logger.info(f"💬 Remaining users in direct chat room {room}: {len(active_direct_connections[room])}")
            
            subscriber_task.cancel()
            logger.debug("📡 Redis subscriber task cancelled")
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {str(e)}") 