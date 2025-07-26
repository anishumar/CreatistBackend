import logging
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from typing import List, Optional
import uuid
from src.models.post import (
    Post, PostCreate, PostUpdate, PostWithDetails, PostComment, PostCommentCreate, PostCommentUpdate
)
from src.utils.post_handler import PostHandler
from src.utils import Token
from src.routes.visionboard import get_user_token

logger = logging.getLogger(__name__)

def get_post_handler(request: Request) -> PostHandler:
    return PostHandler(request.app.state.pool)

router = APIRouter(prefix="/posts", tags=["Posts"])

@router.post("", response_model=dict)
async def create_post(post: PostCreate, request: Request, token: Token = Depends(get_user_token)):
    """Create a new post with comprehensive debug logging"""
    logger.info("🚀 POST /posts - Create post request received")
    logger.info(f"   User ID (from token): {token.sub}")
    logger.info(f"   Post data received: {post.model_dump()}")
    
    try:
        # Log individual fields for debugging
        logger.debug(f"   Caption: {post.caption}")
        logger.debug(f"   Media count: {len(post.media) if post.media else 0}")
        logger.debug(f"   Tags count: {len(post.tags) if post.tags else 0}")
        logger.debug(f"   Collaborators count: {len(post.collaborators) if post.collaborators else 0}")
        logger.debug(f"   Visionboard ID: {post.visionboard_id}")
        logger.debug(f"   Visibility: {post.visibility}")
        
        # Log collaborators details if present
        if post.collaborators:
            logger.debug("   Collaborators details:")
            for i, collab in enumerate(post.collaborators):
                logger.debug(f"     {i+1}. User ID: {collab.user_id}, Role: {collab.role}")
        
        # Log media details if present
        if post.media:
            logger.debug("   Media details:")
            for i, media in enumerate(post.media):
                logger.debug(f"     {i+1}. URL: {media.url}, Type: {media.type}")
        
        handler = get_post_handler(request)
        logger.info("✅ Post data validation passed, creating post...")
        
        post_id = await handler.create_post(post, token.sub)
        logger.info(f"✅ Post created successfully with ID: {post_id}")
        
        return {"post_id": str(post_id)}
        
    except Exception as e:
        logger.error(f"❌ Error creating post: {str(e)}")
        logger.error(f"   Error type: {type(e).__name__}")
        logger.error(f"   Post data that caused error: {post.model_dump()}")
        raise HTTPException(status_code=500, detail=f"Failed to create post: {str(e)}")

@router.get("/feed", response_model=dict)
async def get_feed(request: Request, limit: int = 10, cursor: Optional[str] = None, token: Token = Depends(get_user_token)):
    handler = get_post_handler(request)
    return await handler.get_feed(user_id=token.sub, limit=limit, cursor=cursor)

@router.get("/trending", response_model=dict)
async def get_trending_posts(request: Request, limit: int = 10, cursor: Optional[str] = None):
    handler = get_post_handler(request)
    try:
        return await handler.get_trending_posts(limit, cursor)
    except Exception as e:
        import logging
        logging.error(f"Error in /posts/trending: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{post_id}", response_model=PostWithDetails)
async def get_post(post_id: str, request: Request):
    import uuid
    from fastapi import HTTPException
    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post_id format. Must be a valid UUID.")
    handler = get_post_handler(request)
    post = await handler.get_post_by_id(post_uuid)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@router.post("/{post_id}/like")
async def like_post(post_id: str, request: Request, token: Token = Depends(get_user_token)):
    handler = get_post_handler(request)
    await handler.like_post(uuid.UUID(post_id), token.sub)
    return {"message": "Liked"}

@router.delete("/{post_id}/like")
async def unlike_post(post_id: str, request: Request, token: Token = Depends(get_user_token)):
    handler = get_post_handler(request)
    await handler.unlike_post(uuid.UUID(post_id), token.sub)
    return {"message": "Unliked"}

@router.post("/{post_id}/comments", response_model=PostComment)
async def add_comment(post_id: str, comment: PostCommentCreate, request: Request, token: Token = Depends(get_user_token)):
    handler = get_post_handler(request)
    return await handler.add_comment(uuid.UUID(post_id), token.sub, comment)

@router.get("/{post_id}/comments", response_model=List[PostComment])
async def get_comments(post_id: str, request: Request, parent_id: Optional[str] = None, limit: int = 10, cursor: Optional[str] = None):
    handler = get_post_handler(request)
    parent_uuid = uuid.UUID(parent_id) if parent_id else None
    return await handler.get_comments(uuid.UUID(post_id), parent_uuid, limit, cursor)

@router.get("/user/{user_id}", response_model=List[PostWithDetails])
async def get_user_posts(user_id: str, request: Request, limit: int = 10, cursor: Optional[str] = None):
    handler = get_post_handler(request)
    return await handler.get_user_posts(uuid.UUID(user_id), limit, cursor)

@router.get("/search", response_model=List[PostWithDetails])
async def search_posts(request: Request, q: str, tag: Optional[str] = None, limit: int = 10, cursor: Optional[str] = None):
    handler = get_post_handler(request)
    return await handler.search_posts(q, tag, limit, cursor)

@router.delete("/{post_id}")
async def soft_delete_post(post_id: str, request: Request, token: Token = Depends(get_user_token)):
    handler = get_post_handler(request)
    await handler.soft_delete_post(uuid.UUID(post_id), token.sub)
    return {"message": "Post soft deleted"} 