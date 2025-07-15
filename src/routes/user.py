from __future__ import annotations

import os
import logging

from fastapi import Request, APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from geopy.geocoders import Nominatim

from src.app import app, user_handler
from src.utils import Token, TokenHandler
from src.models.user import (
    User, UserUpdate, Showcase, Comment, VisionBoard,
    VisionBoardTask, Location
)
from src.models.visionboard import DirectMessageCreate
from typing import List

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Users"])
JWT_SECRET = os.environ["JWT_SECRET"]

token_handler = TokenHandler(os.environ["JWT_SECRET"])
security = HTTPBearer()


def get_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return token_handler.decode_token(credentials.credentials)

# User Management APIs
@router.post("/create")
async def create_user(request: Request, user: User):
    await user_handler.create_user(user=user)
    return JSONResponse({"message": "success"})

@router.post("/login")
async def login_user(request: Request, email: str, password: str):
    user = await user_handler.fetch_user(email=email, password=password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token, refresh_token = token_handler.create_token_pair(user)
    return JSONResponse({
        "message": "success", 
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 86400  # 24 hours
    })

@router.post("/refresh")
async def refresh_token(request: Request):
    data = await request.json()
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Missing refresh_token")
    try:
        token_data = token_handler.decode_refresh_token(refresh_token)
        user_id = token_data["sub"]
        user = await user_handler.fetch_user(user_id=user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        access_token = token_handler.create_access_token(user)
        return JSONResponse({
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 900
        })
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@router.put("/update")
async def update_user(request: Request, user: User, token: Token = Depends(get_user_token)):
    updated_user = await user_handler.update_user(user_id=token.sub, update_payload=user)
    return JSONResponse({"message": "success", "user": updated_user})

@router.patch("/users")
async def update_user_partial(
    user_update: UserUpdate,
    token: Token = Depends(get_user_token)
):
    updated = await user_handler.update_user_partial(user_id=token.sub, user_update=user_update)
    if updated:
        return JSONResponse({"message": "success"})
    return JSONResponse({"message": "failed"}, status_code=400)

@router.patch("/users/location")
async def update_user_location(
    location: Location,
    token: Token = Depends(get_user_token)
):
    # Reverse geocode to get city and country
    geolocator = Nominatim(user_agent="creatist-app")
    loc = geolocator.reverse((location.latitude, location.longitude), language='en')
    city, country = '', ''
    if loc and loc.raw and 'address' in loc.raw:
        address = loc.raw['address']
        city = address.get('city') or address.get('town') or address.get('village') or ''
        country = address.get('country', '')

    # Build the update model
    user_update = UserUpdate(
        location=location,
        city=city,
        country=country
    )
    updated = await user_handler.update_user_partial(user_id=token.sub, user_update=user_update)
    if updated:
        return JSONResponse({"message": "success"})
    return JSONResponse({"message": "failed"}, status_code=400)

# Follower Management APIs
@router.get("/followers/{user_id}")
async def get_user_followers(request: Request, user_id: str, token: Token = Depends(get_user_token)):
    """Get followers of any user (for profile views)"""
    user_id = user_id.lower()
    if not await user_handler.user_exists(user_id):
        return JSONResponse({"detail": f"User {user_id} does not exist"}, status_code=404)
    
    followers = await user_handler.get_followers(user_id=user_id)
    return JSONResponse({"message": "success", "followers": [user.model_dump(mode="json") for user in followers]})

@router.get("/following/{user_id}")
async def get_user_following(request: Request, user_id: str, token: Token = Depends(get_user_token)):
    """Get who any user is following (for profile views)"""
    user_id = user_id.lower()
    if not await user_handler.user_exists(user_id):
        return JSONResponse({"detail": f"User {user_id} does not exist"}, status_code=404)
    
    following = await user_handler.get_following(user_id=user_id)
    return JSONResponse({"message": "success", "following": [user.model_dump(mode="json") for user in following]})

@router.get("/following/{user_id}/{role}")
async def get_user_following_by_role(request: Request, user_id: str, role: str, token: Token = Depends(get_user_token)):
    """Get who any user is following filtered by role"""
    user_id = user_id.lower()
    if not await user_handler.user_exists(user_id):
        return JSONResponse({"detail": f"User {user_id} does not exist"}, status_code=404)
    
    following = await user_handler.get_following_by_role(user_id=user_id, role=role)
    return JSONResponse({"message": "success", "following": [user.model_dump(mode="json") for user in following]})

@router.put("/follow/{user_id}")
async def follow_user(request: Request, user_id: str, token: Token = Depends(get_user_token)):
    user_id = user_id.lower()
    if user_id == token.sub:
        return JSONResponse({"detail": "Cannot follow yourself"}, status_code=400)
    if not await user_handler.user_exists(user_id):
        return JSONResponse({"detail": f"User {user_id} does not exist"}, status_code=404)
    try:
        await user_handler.follow(following_id=user_id, user_id=token.sub)
        return JSONResponse({"message": "success"})
    except Exception as e:
        error_msg = str(e)
        if "no_self_follow" in error_msg:
            return JSONResponse({"detail": "Cannot follow yourself"}, status_code=400)
        elif "duplicate key value" in error_msg:
            return JSONResponse({"detail": "Already following this user"}, status_code=400)
        else:
            return JSONResponse({"detail": "Failed to follow user"}, status_code=400)

@router.delete("/unfollow/{user_id}")
async def unfollow_user(request: Request, user_id: str, token: Token = Depends(get_user_token)):
    user_id = user_id.lower()
    if user_id == token.sub:
        return JSONResponse({"detail": "Cannot unfollow yourself"}, status_code=400)
    if not await user_handler.user_exists(user_id):
        return JSONResponse({"detail": f"User {user_id} does not exist"}, status_code=404)
    try:
        await user_handler.unfollow(following_id=user_id, user_id=token.sub)
        return JSONResponse({"message": "success"})
    except Exception as e:
        return JSONResponse({"detail": str(e)}, status_code=400)

# Message APIs
@router.get("/message/users")
async def get_message_users(request: Request, token: Token = Depends(get_user_token)):
    users = await user_handler.get_message_users(user_id=token.sub)
    return JSONResponse({"message": "success", "users": users})

@router.post("/message/{user_id}/create")
async def create_message(request: Request, user_id: str, message: str, token: Token = Depends(get_user_token)):
    await user_handler.create_message(sender_id=token.sub, receiver_id=user_id, message=message)
    return JSONResponse({"message": "success"})

@router.get("/message/{user_id}/{limit}")
async def get_messages(request: Request, user_id: str, limit: int, token: Token = Depends(get_user_token)):
    messages = await user_handler.get_messages(user_id=token.sub, other_user_id=user_id, limit=limit)
    return JSONResponse({"message": "success", "messages": messages})

@router.post("/message/{user_id}")
async def send_direct_message(user_id: str, msg: DirectMessageCreate, token: Token = Depends(get_user_token)):
    """Send direct message with debug logging"""
    logger.info(f"📤 Direct message send attempt")
    logger.debug(f"   Sender (from token): {token.sub}")
    logger.debug(f"   Receiver (from URL): {user_id}")
    logger.debug(f"   Message receiver (from payload): {msg.receiver_id}")
    logger.debug(f"   Message content: {msg.message[:50]}...")
    
    # Permission check
    logger.debug(f"🔒 Checking send permissions...")
    logger.debug(f"   Token user ID: {token.sub}")
    logger.debug(f"   URL user ID: {user_id}")
    logger.debug(f"   Payload receiver ID: {msg.receiver_id}")
    
    if str(token.sub) != str(msg.receiver_id) and str(token.sub) != str(user_id):
        logger.warning(f"🚫 Permission denied: User {token.sub} not allowed to send message")
        logger.warning(f"   Token user: {token.sub}")
        logger.warning(f"   URL user: {user_id}")
        logger.warning(f"   Payload receiver: {msg.receiver_id}")
        raise HTTPException(status_code=403, detail="Not allowed to send message as another user.")
    
    logger.info(f"✅ Permission granted. Sending message from {token.sub} to {user_id}")
    
    try:
        await user_handler.send_direct_message(sender_id=token.sub, receiver_id=user_id, message=msg.message)
        logger.info(f"✅ Direct message sent successfully")
        return {"message": "Message sent"}
    except Exception as e:
        logger.error(f"❌ Failed to send direct message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@router.get("/message/{user_id}")
async def get_direct_messages(user_id: str, limit: int = 50, before: str = None, token: Token = Depends(get_user_token)):
    """Get direct messages with debug logging"""
    logger.info(f"📥 Direct message fetch attempt")
    logger.debug(f"   Requesting user (from token): {token.sub}")
    logger.debug(f"   Target user (from URL): {user_id}")
    logger.debug(f"   Limit: {limit}")
    logger.debug(f"   Before: {before}")
    
    # Permission check
    logger.debug(f"🔒 Checking fetch permissions...")
    logger.debug(f"   Token user ID: {token.sub}")
    logger.debug(f"   URL user ID: {user_id}")
    logger.debug(f"   Are they the same? {str(token.sub) == str(user_id)}")
    
    # For direct messages, both participants should be able to view the conversation
    # The URL user_id represents the other user in the conversation
    # The token user should be able to view messages with the URL user
    logger.info(f"✅ Permission granted. Fetching messages between {token.sub} and {user_id}")
    
    try:
        messages = await user_handler.get_direct_messages(user_id=str(token.sub), other_user_id=user_id, limit=limit, before=before)
        logger.info(f"✅ Retrieved {len(messages)} messages")
        
        # Fetch avatar_url for each sender
        from src.app import user_handler as user_handler_local
        result = []
        
        logger.debug(f"👤 Fetching avatars for {len(messages)} messages...")
        for i, m in enumerate(messages):
            sender_id = m.get("sender_id")
            logger.debug(f"   Message {i+1}: sender_id = {sender_id}")
            
            try:
                user = await user_handler_local.fetch_user(user_id=str(sender_id))
                avatar_url = user.profile_image_url if user and hasattr(user, 'profile_image_url') and user.profile_image_url else "https://ui-avatars.com/api/?name=User"
                logger.debug(f"   ✅ Avatar for {sender_id}: {avatar_url}")
            except Exception as e:
                logger.error(f"   ❌ Failed to fetch avatar for {sender_id}: {str(e)}")
                avatar_url = "https://ui-avatars.com/api/?name=User"
            
            m["avatar_url"] = avatar_url
            result.append(m)
        
        logger.info(f"✅ Returning {len(result)} messages with avatars")
        return {"messages": result}
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch direct messages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch messages: {str(e)}")

# Showcase APIs
@router.get("/showcases")
async def get_showcases(request: Request, token: Token = Depends(get_user_token)):
    showcases = await user_handler.get_showcases(user_id=token.sub)
    return JSONResponse({"message": "success", "showcases": showcases})

@router.post("/showcase/create")
async def create_showcase(request: Request, showcase: Showcase, token: Token = Depends(get_user_token)):
    await user_handler.create_showcase(showcase=showcase, user_id=token.sub)
    return JSONResponse({"message": "success"})

@router.get("/showcase/{showcase_id}")
async def get_showcase(request: Request, showcase_id: str, token: Token = Depends(get_user_token)):
    showcase = await user_handler.get_showcase(showcase_id=showcase_id)
    return JSONResponse({"message": "success", "showcase": showcase})

@router.put("/showcase/{showcase_id}/update")
async def update_showcase(request: Request, showcase_id: str, showcase: Showcase, token: Token = Depends(get_user_token)):
    await user_handler.update_showcase(showcase_id=showcase_id, showcase=showcase, user_id=token.sub)
    return JSONResponse({"message": "success"})

@router.delete("/showcase/{showcase_id}/delete")
async def delete_showcase(request: Request, showcase_id: str, token: Token = Depends(get_user_token)):
    await user_handler.delete_showcase(showcase_id=showcase_id, user_id=token.sub)
    return JSONResponse({"message": "success"})

# Showcase Interaction APIs
@router.put("/showcase/{showcase_id}/like")
async def like_showcase(request: Request, showcase_id: str, token: Token = Depends(get_user_token)):
    await user_handler.like_showcase(showcase_id=showcase_id, user_id=token.sub)
    return JSONResponse({"message": "success"})

@router.put("/showcase/{showcase_id}/unlike")
async def unlike_showcase(request: Request, showcase_id: str, token: Token = Depends(get_user_token)):
    await user_handler.unlike_showcase(showcase_id=showcase_id, user_id=token.sub)
    return JSONResponse({"message": "success"})

@router.post("/showcase/{showcase_id}/comment")
async def create_comment(request: Request, showcase_id: str, comment: Comment, token: Token = Depends(get_user_token)):
    await user_handler.create_comment(showcase_id=showcase_id, comment=comment, user_id=token.sub)
    return JSONResponse({"message": "success"})

@router.put("/showcase/{showcase_id}/comment/{comment_id}/upvote")
async def upvote_comment(request: Request, showcase_id: str, comment_id: str, token: Token = Depends(get_user_token)):
    await user_handler.upvote_comment(comment_id=comment_id, user_id=token.sub)
    return JSONResponse({"message": "success"})

@router.put("/showcase/{showcase_id}/comment/{comment_id}/remove-upvote")
async def remove_comment_upvote(request: Request, showcase_id: str, comment_id: str, token: Token = Depends(get_user_token)):
    await user_handler.remove_comment_upvote(comment_id=comment_id, user_id=token.sub)
    return JSONResponse({"message": "success"})

@router.put("/showcase/{showcase_id}/bookmark")
async def bookmark_showcase(request: Request, showcase_id: str, token: Token = Depends(get_user_token)):
    await user_handler.bookmark_showcase(showcase_id=showcase_id, user_id=token.sub)
    return JSONResponse({"message": "success"})

@router.put("/showcase/{showcase_id}/un-bookmark")
async def unbookmark_showcase(request: Request, showcase_id: str, token: Token = Depends(get_user_token)):
    await user_handler.unbookmark_showcase(showcase_id=showcase_id, user_id=token.sub)
    return JSONResponse({"message": "success"})

# Vision Board APIs - Removed duplicate endpoints (use /v1/visionboard/ endpoints instead)

# Browse APIs Discover Page 
@router.get("/browse/top-rated/{genre_name}")
async def get_top_rated_artists_by_genre(genre_name: str, token: Token = Depends(get_user_token)):
    artists = await user_handler.get_top_rated_artists(genre_name=genre_name)
    current_user_id = token.sub
    # Batch get all following relationships
    artist_ids = [str(artist.id) for artist in artists]
    if not artist_ids:
        return JSONResponse({"message": "success", "artists": []})
    # Query all follows in one go
    follows = await user_handler.get_following_relationships(current_user_id, artist_ids)
    follows_set = set(follows)
    for artist in artists:
        artist.is_following = str(artist.id) in follows_set
    return JSONResponse({"message": "success", "artists": [artist.model_dump(mode="json") for artist in artists]})

@router.get("/browse/near-by-artist/{genre_name}")
async def get_nearby_artists_by_genre(genre_name: str, token: Token = Depends(get_user_token)):
    artists = await user_handler.get_nearby_artists(user_id=token.sub, genre=genre_name)
    current_user_id = token.sub
    artist_ids = [str(artist.id) for artist in artists]
    if not artist_ids:
        return JSONResponse({"message": "success", "artists": []})
    follows = await user_handler.get_following_relationships(current_user_id, artist_ids)
    follows_set = set(follows)
    for artist in artists:
        artist.is_following = str(artist.id) in follows_set
    return JSONResponse({"message": "success", "artists": [artist.model_dump(mode="json") for artist in artists]})

@router.get("/browse/artist/{artist_id}/showcase")
async def get_artist_showcases(request: Request, artist_id: str, token: Token = Depends(get_user_token)):
    showcases = await user_handler.get_artist_showcases(artist_id=artist_id)
    return JSONResponse({"message": "success", "showcases": showcases})

@router.get("/browse/genre/{genre_name}")
async def get_users_by_genre(genre_name: str, token: Token = Depends(get_user_token)):
    users = await user_handler.get_users_by_genre(genre_name)
    return JSONResponse({"message": "success", "users": [user.model_dump() for user in users]})

@router.get("/users")
async def get_users_by_genre(request: Request, genre: str, token: Token = Depends(get_user_token)):
    users = await user_handler.get_users_by_genre(genre)
    print([user.model_dump(mode="json") for user in users])
    return [user.model_dump(mode="json") for user in users]

@router.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await user_handler.fetch_user(user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return JSONResponse({"message": "success", "user": user.model_dump(mode="json")})

app.include_router(router)
