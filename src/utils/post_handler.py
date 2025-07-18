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
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create_post(self, post: PostCreate, user_id: uuid.UUID) -> uuid.UUID:
        """Create a new post with comprehensive debug logging"""
        logger.info("🔧 PostHandler.create_post - Starting post creation")
        logger.info(f"   User ID: {user_id}")
        logger.info(f"   Post data: {post.model_dump()}")
        
        try:
            async with self.pool.acquire() as conn:
                logger.debug("   ✅ Database connection acquired")
                
                # Auto-fetch collaborators from visionboard if visionboard_id is provided
                collaborators = post.collaborators.copy() if post.collaborators else []
                if post.visionboard_id:
                    logger.debug(f"   Fetching collaborators from visionboard: {post.visionboard_id}")
                    
                    # Get genre assignments with work_type directly
                    query = """
                        SELECT ga.user_id, ga.work_type
                        FROM genre_assignments ga
                        JOIN genres g ON ga.genre_id = g.id
                        WHERE g.visionboard_id = $1 AND ga.status = 'Accepted'
                    """
                    rows = await conn.fetch(query, post.visionboard_id)
                    
                    for row in rows:
                        user_id_collab = row['user_id']
                        work_type = row['work_type']
                        
                        # Skip if already in the provided collaborators list
                        if not any(c.user_id == user_id_collab for c in collaborators):
                            from src.models.post import PostCollaboratorCreate, CollaboratorRole
                            
                            # Map work_type to post collaborator role
                            post_role = CollaboratorRole.collaborator  # Default role
                            if work_type.lower() in ['editor', 'videographer', 'actor', 'director']:
                                try:
                                    post_role = CollaboratorRole(work_type.lower())
                                except ValueError:
                                    # If work_type doesn't match post roles, use collaborator
                                    post_role = CollaboratorRole.collaborator
                            
                            collaborators.append(PostCollaboratorCreate(
                                user_id=user_id_collab,
                                role=post_role
                            ))
                            logger.debug(f"   Added collaborator: {user_id_collab} with role: {post_role} (from work_type: {work_type})")
                
                async with conn.transaction():
                    logger.debug("   ✅ Database transaction started")
                    
                    # Validate required fields
                    logger.debug(f"   Validating caption: {post.caption}")
                    if not post.caption:
                        logger.error("   ❌ Caption is required")
                        raise ValueError("Caption is required")
                    
                    logger.debug(f"   Validating status: {post.status}")
                    logger.debug(f"   Validating visibility: {post.visibility}")
                    
                    # If no collaborators, is_collaborative is False and no collaborators are inserted
                    is_collaborative = bool(collaborators)
                    logger.debug(f"   Is collaborative: {is_collaborative}")
                    logger.debug(f"   Total collaborators count: {len(collaborators)}")
                    
                    post_id = uuid.uuid4()
                    logger.debug(f"   Generated post ID: {post_id}")
                    
                    # Insert main post
                    logger.debug("   Inserting main post record...")
                    await conn.execute(
                        """
                        INSERT INTO posts (id, user_id, caption, is_collaborative, status, visibility, shared_from_post_id, visionboard_id, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, now(), now())
                        """,
                        post_id, user_id, post.caption, is_collaborative, post.status.value, post.visibility.value, post.shared_from_post_id, post.visionboard_id
                    )
                    logger.debug("   ✅ Main post record inserted")
                    
                    # Insert media
                    if post.media:
                        logger.debug(f"   Inserting {len(post.media)} media items...")
                        for i, m in enumerate(post.media):
                            logger.debug(f"     Media {i+1}: URL={m.url}, Type={m.type}, Order={m.order}")
                            await conn.execute(
                                """
                                INSERT INTO post_media (id, post_id, url, type, "order")
                                VALUES ($1, $2, $3, $4, $5)
                                """,
                                uuid.uuid4(), post_id, m.url, m.type.value, m.order
                            )
                        logger.debug("   ✅ All media items inserted")
                    else:
                        logger.debug("   No media items to insert")
                    
                    # Insert tags
                    if post.tags:
                        logger.debug(f"   Inserting {len(post.tags)} tags...")
                        for i, tag in enumerate(post.tags):
                            logger.debug(f"     Tag {i+1}: {tag}")
                            await conn.execute(
                                """
                                INSERT INTO post_tags (post_id, tag) VALUES ($1, $2)
                                ON CONFLICT DO NOTHING
                                """,
                                post_id, tag
                            )
                        logger.debug("   ✅ All tags inserted")
                    else:
                        logger.debug("   No tags to insert")
                    
                    # Insert collaborators
                    if collaborators:
                        logger.debug(f"   Inserting {len(collaborators)} collaborators...")
                        for i, c in enumerate(collaborators):
                            logger.debug(f"     Collaborator {i+1}: User ID={c.user_id}, Role={c.role}")
                            await conn.execute(
                                """
                                INSERT INTO post_collaborators (post_id, user_id, role)
                                VALUES ($1, $2, $3)
                                ON CONFLICT DO NOTHING
                                """,
                                post_id, c.user_id, c.role.value
                            )
                        logger.debug("   ✅ All collaborators inserted")
                    else:
                        logger.debug("   No collaborators to insert")
                    
                    logger.info(f"   ✅ Post created successfully with ID: {post_id}")
                    return post_id
                    
        except Exception as e:
            logger.error(f"   ❌ Error in create_post: {str(e)}")
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   Post data: {post.model_dump()}")
            raise

    async def get_feed(self, limit: int = 10, cursor: Optional[str] = None) -> dict:
        async with self.pool.acquire() as conn:
            params = []
            query = "SELECT * FROM posts WHERE deleted_at IS NULL"
            if cursor:
                import datetime
                if isinstance(cursor, str):
                    cursor = datetime.datetime.fromisoformat(cursor)
                query += " AND created_at < $1"
                params.append(cursor)
            query += " ORDER BY created_at DESC LIMIT $%d" % (len(params) + 1)
            params.append(limit + 1)
            rows = await conn.fetch(query, *params)
            posts = [await self._post_with_details(conn, row) for row in rows[:limit]]
            next_cursor = None
            if len(rows) > limit:
                next_cursor = str(rows[limit - 1]['created_at'].isoformat())
            return {"posts": posts, "nextCursor": next_cursor}

    async def get_post_by_id(self, post_id: uuid.UUID) -> Optional[PostWithDetails]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM posts WHERE id = $1 AND deleted_at IS NULL", post_id)
            if not row:
                return None
            return await self._post_with_details(conn, row)

    async def like_post(self, post_id: uuid.UUID, user_id: uuid.UUID):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO post_likes (user_id, post_id, created_at) VALUES ($1, $2, now()) ON CONFLICT DO NOTHING",
                user_id, post_id
            )

    async def unlike_post(self, post_id: uuid.UUID, user_id: uuid.UUID):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM post_likes WHERE user_id = $1 AND post_id = $2",
                user_id, post_id
            )

    async def add_comment(self, post_id: uuid.UUID, user_id: uuid.UUID, comment: PostCommentCreate) -> PostComment:
        async with self.pool.acquire() as conn:
            comment_id = uuid.uuid4()
            await conn.execute(
                """
                INSERT INTO post_comments (id, post_id, user_id, content, parent_comment_id, created_at)
                VALUES ($1, $2, $3, $4, $5, now())
                """,
                comment_id, post_id, user_id, comment.content, comment.parent_comment_id
            )
            return PostComment(
                id=comment_id,
                post_id=post_id,
                user_id=user_id,
                content=comment.content,
                parent_comment_id=comment.parent_comment_id,
                created_at=datetime.datetime.utcnow(),
                deleted_at=None
            )

    async def get_comments(self, post_id: uuid.UUID, parent_id: Optional[uuid.UUID] = None, limit: int = 10, cursor: Optional[str] = None) -> List[PostComment]:
        async with self.pool.acquire() as conn:
            params = [post_id]
            query = "SELECT * FROM post_comments WHERE post_id = $1 AND deleted_at IS NULL"
            if parent_id:
                query += " AND parent_comment_id = $%d" % (len(params) + 1)
                params.append(parent_id)
            else:
                query += " AND parent_comment_id IS NULL"
            if cursor:
                query += " AND created_at > $%d" % (len(params) + 1)
                params.append(cursor)
            query += " ORDER BY created_at ASC LIMIT $%d" % (len(params) + 1)
            params.append(limit)
            rows = await conn.fetch(query, *params)
            return [PostComment(**dict(row)) for row in rows]

    async def get_user_posts(self, user_id: uuid.UUID, limit: int = 10, cursor: Optional[str] = None) -> List[PostWithDetails]:
        async with self.pool.acquire() as conn:
            params = [user_id]
            query = "SELECT * FROM posts WHERE user_id = $1 AND deleted_at IS NULL"
            if cursor:
                query += " AND created_at < $2"
                params.append(cursor)
            query += " ORDER BY created_at DESC LIMIT $%d" % (len(params) + 1)
            params.append(limit)
            rows = await conn.fetch(query, *params)
            return [await self._post_with_details(conn, row) for row in rows]

    async def search_posts(self, q: str, tag: Optional[str] = None, limit: int = 10, cursor: Optional[str] = None) -> List[PostWithDetails]:
        async with self.pool.acquire() as conn:
            params = [f"%{q}%"]
            query = "SELECT * FROM posts WHERE deleted_at IS NULL AND caption ILIKE $1"
            if tag:
                query += " AND id IN (SELECT post_id FROM post_tags WHERE tag = $2)"
                params.append(tag)
            if cursor:
                query += " AND created_at < $%d" % (len(params) + 1)
                params.append(cursor)
            query += " ORDER BY created_at DESC LIMIT $%d" % (len(params) + 1)
            params.append(limit)
            rows = await conn.fetch(query, *params)
            return [await self._post_with_details(conn, row) for row in rows]

    async def get_trending_posts(self, limit: int = 10, cursor: Optional[str] = None) -> dict:
        async with self.pool.acquire() as conn:
            query = """
                SELECT p.* FROM posts p
                LEFT JOIN (
                    SELECT post_id, COUNT(*) as like_count FROM post_likes GROUP BY post_id
                ) l ON p.id = l.post_id
                LEFT JOIN (
                    SELECT post_id, COUNT(*) as view_count FROM post_views GROUP BY post_id
                ) v ON p.id = v.post_id
                WHERE p.deleted_at IS NULL
            """
            params = []
            if cursor:
                import datetime
                if isinstance(cursor, str):
                    cursor = datetime.datetime.fromisoformat(cursor)
                query += " AND p.created_at < $1"
                params.append(cursor)
            query += " ORDER BY COALESCE(l.like_count,0) DESC, COALESCE(v.view_count,0) DESC, p.created_at DESC LIMIT $%d" % (len(params) + 1)
            params.append(limit + 1)
            rows = await conn.fetch(query, *params)
            posts = [await self._post_with_details(conn, row) for row in rows[:limit]]
            next_cursor = None
            if len(rows) > limit:
                next_cursor = str(rows[limit - 1]['created_at'].isoformat())
            posts = [p for p in posts if p is not None]
            logger.debug(f"Trending posts returned: {len(posts)}")
            return {"posts": posts, "nextCursor": next_cursor}

    async def soft_delete_post(self, post_id: uuid.UUID, user_id: uuid.UUID):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE posts SET deleted_at = now() WHERE id = $1 AND user_id = $2",
                post_id, user_id
            )

    async def _post_with_details(self, conn, row) -> PostWithDetails:
        try:
            # Do NOT parse post_id as UUID here; keep as string for trending/feed endpoints
            post_id = row['id']
            # Media
            media_rows = await conn.fetch("SELECT * FROM post_media WHERE post_id = $1 ORDER BY \"order\" ASC", post_id)
            media = [PostMedia(**dict(m)) for m in media_rows]
            # Tags
            tag_rows = await conn.fetch("SELECT tag FROM post_tags WHERE post_id = $1", post_id)
            tags = [r['tag'] for r in tag_rows]
            # Collaborators
            collab_rows = await conn.fetch("SELECT post_id, user_id, role FROM post_collaborators WHERE post_id = $1", post_id)
            collaborators = [PostCollaborator(**dict(c)) for c in collab_rows]
            # Like count
            like_count = await conn.fetchval("SELECT COUNT(*) FROM post_likes WHERE post_id = $1", post_id) or 0
            # Comment count
            comment_count = await conn.fetchval("SELECT COUNT(*) FROM post_comments WHERE post_id = $1 AND deleted_at IS NULL", post_id) or 0
            # View count
            view_count = await conn.fetchval("SELECT COUNT(*) FROM post_views WHERE post_id = $1", post_id) or 0
            # Author name (optional, join users)
            author_name = await conn.fetchval("SELECT name FROM users WHERE id = $1", row['user_id'])
            # Top comments (first 3 root comments)
            top_comment_rows = await conn.fetch(
                "SELECT * FROM post_comments WHERE post_id = $1 AND parent_comment_id IS NULL AND deleted_at IS NULL ORDER BY created_at ASC LIMIT 3",
                post_id
            )
            top_comments = [PostComment(**dict(tc)) for tc in top_comment_rows]
            return PostWithDetails(
                **dict(row),
                media=media,
                tags=tags,
                collaborators=collaborators,
                like_count=like_count,
                comment_count=comment_count,
                view_count=view_count,
                author_name=author_name,
                top_comments=top_comments
            )
        except Exception as e:
            import logging
            logging.error(f"Error in _post_with_details for post_id={row.get('id')}: {e}")
            return None 