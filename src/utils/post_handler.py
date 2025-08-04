import uuid
import datetime
import logging
from typing import List, Optional
import asyncpg
from src.models.post import (
    Post, PostCreate, PostUpdate, PostWithDetails, PostMedia, PostMediaCreate, PostTag, PostCollaborator, PostCollaboratorCreate, PostComment, PostCommentCreate, PostCommentUpdate
)

logger = logging.getLogger(__name__)

class PostHandler:
    def __init__(self, pool: asyncpg.Pool = None):
        self.pool = pool
        # Import user_handler to use Supabase
        from src.app import user_handler
        self.supabase = user_handler.supabase

    async def create_post(self, post: PostCreate, user_id: uuid.UUID) -> uuid.UUID:
        """Create a new post using Supabase"""
        logger.info("🔧 PostHandler.create_post - Starting post creation with Supabase")
        logger.info(f"   User ID: {user_id}")
        logger.info(f"   Post data: {post.model_dump()}")
        
        try:
            # Use Supabase instead of direct PostgreSQL
            post_data = {
                "id": str(uuid.uuid4()),
                "user_id": str(user_id),
                "caption": post.caption,
                "is_collaborative": bool(post.collaborators),
                "status": post.status.value,
                "visibility": post.visibility.value,
                "shared_from_post_id": post.shared_from_post_id,
                "visionboard_id": post.visionboard_id,
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat()
            }
            
            # Insert post using Supabase
            response = await self.supabase.table("posts").insert(post_data).execute()
            post_id = response.data[0]["id"] if response.data else None
            
            if not post_id:
                raise ValueError("Failed to create post")
            
            logger.info(f"✅ Post created successfully with ID: {post_id}")
            return uuid.UUID(post_id)
            
        except Exception as e:
            logger.error(f"❌ Error creating post: {str(e)}")
            raise ValueError(f"Failed to create post: {str(e)}")

    async def get_feed(self, limit: int = 10, cursor: Optional[str] = None) -> dict:
        """Get feed posts using Supabase"""
        try:
            query = self.supabase.table("posts").select("*").order("created_at", desc=True).limit(limit)
            
            if cursor:
                query = query.lt("created_at", cursor)
            
            response = await query.execute()
            posts = response.data if response.data else []
            
            return {
                "posts": posts,
                "next_cursor": posts[-1]["created_at"] if posts else None
            }
        except Exception as e:
            logger.error(f"Error getting feed: {e}")
            return {"posts": [], "next_cursor": None}

    async def get_following_feed(self, user_id: uuid.UUID, limit: int = 10, cursor: Optional[str] = None) -> dict:
        """Get following feed using Supabase"""
        try:
            # Get users that the current user is following
            following_response = await self.supabase.table("followers").select("following_id").eq("user_id", str(user_id)).execute()
            following_ids = [row["following_id"] for row in following_response.data] if following_response.data else []
            
            if not following_ids:
                return {"posts": [], "next_cursor": None}
            
            # Get posts from followed users
            query = self.supabase.table("posts").select("*").in_("user_id", following_ids).order("created_at", desc=True).limit(limit)
            
            if cursor:
                query = query.lt("created_at", cursor)
            
            response = await query.execute()
            posts = response.data if response.data else []
            
            return {
                "posts": posts,
                "next_cursor": posts[-1]["created_at"] if posts else None
            }
        except Exception as e:
            logger.error(f"Error getting following feed: {e}")
            return {"posts": [], "next_cursor": None}

    async def get_user_posts(self, user_id: uuid.UUID, limit: int = 10, cursor: Optional[str] = None) -> List[PostWithDetails]:
        """Get user posts using Supabase"""
        try:
            query = self.supabase.table("posts").select("*").eq("user_id", str(user_id)).order("created_at", desc=True).limit(limit)
            
            if cursor:
                query = query.lt("created_at", cursor)
            
            response = await query.execute()
            posts = response.data if response.data else []
            
            # Convert to PostWithDetails objects
            result = []
            for post_data in posts:
                try:
                    post = PostWithDetails(**post_data)
                    result.append(post)
                except Exception as e:
                    logger.error(f"Error parsing post {post_data.get('id')}: {e}")
                    continue
            
            return result
        except Exception as e:
            logger.error(f"Error getting user posts: {e}")
            return []

    async def get_trending_posts(self, limit: int = 10, cursor: Optional[str] = None) -> dict:
        """Get trending posts using Supabase"""
        try:
            # Simple trending implementation - get posts with most likes
            query = self.supabase.table("posts").select("*").order("created_at", desc=True).limit(limit)
            
            if cursor:
                query = query.lt("created_at", cursor)
            
            response = await query.execute()
            posts = response.data if response.data else []
            
            return {
                "posts": posts,
                "next_cursor": posts[-1]["created_at"] if posts else None
            }
        except Exception as e:
            logger.error(f"Error getting trending posts: {e}")
            return {"posts": [], "next_cursor": None}

    # Add other methods as needed...
    async def like_post(self, post_id: uuid.UUID, user_id: uuid.UUID):
        """Like a post using Supabase"""
        try:
            like_data = {
                "post_id": str(post_id),
                "user_id": str(user_id),
                "created_at": datetime.datetime.now().isoformat()
            }
            await self.supabase.table("post_likes").insert(like_data).execute()
        except Exception as e:
            logger.error(f"Error liking post: {e}")
            raise

    async def unlike_post(self, post_id: uuid.UUID, user_id: uuid.UUID):
        """Unlike a post using Supabase"""
        try:
            await self.supabase.table("post_likes").delete().eq("post_id", str(post_id)).eq("user_id", str(user_id)).execute()
        except Exception as e:
            logger.error(f"Error unliking post: {e}")
            raise

    async def add_comment(self, post_id: uuid.UUID, user_id: uuid.UUID, comment: PostCommentCreate) -> PostComment:
        """Add comment using Supabase"""
        try:
            comment_data = {
                "id": str(uuid.uuid4()),
                "post_id": str(post_id),
                "user_id": str(user_id),
                "content": comment.content,
                "parent_id": comment.parent_id,
                "created_at": datetime.datetime.now().isoformat()
            }
            
            response = await self.supabase.table("post_comments").insert(comment_data).execute()
            comment_data = response.data[0] if response.data else None
            
            if not comment_data:
                raise ValueError("Failed to create comment")
            
            return PostComment(**comment_data)
        except Exception as e:
            logger.error(f"Error adding comment: {e}")
            raise

    async def get_comments(self, post_id: uuid.UUID, parent_id: Optional[uuid.UUID] = None, limit: int = 10, cursor: Optional[str] = None) -> List[PostComment]:
        """Get comments using Supabase"""
        try:
            query = self.supabase.table("post_comments").select("*").eq("post_id", str(post_id)).order("created_at", desc=True).limit(limit)
            
            if parent_id:
                query = query.eq("parent_id", str(parent_id))
            else:
                query = query.is_("parent_id", "null")
            
            if cursor:
                query = query.lt("created_at", cursor)
            
            response = await query.execute()
            comments = response.data if response.data else []
            
            return [PostComment(**comment) for comment in comments]
        except Exception as e:
            logger.error(f"Error getting comments: {e}")
            return []

    async def soft_delete_post(self, post_id: uuid.UUID, user_id: uuid.UUID):
        """Soft delete post using Supabase"""
        try:
            await self.supabase.table("posts").update({"deleted_at": datetime.datetime.now().isoformat()}).eq("id", str(post_id)).eq("user_id", str(user_id)).execute()
        except Exception as e:
            logger.error(f"Error soft deleting post: {e}")
            raise 