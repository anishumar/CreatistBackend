from __future__ import annotations

import os
from typing import Optional, Union, List
from uuid import UUID
import math
import enum

from dotenv import load_dotenv
from src.models.user import (
    User, UserUpdate, Showcase, Comment, VisionBoard,
    ShowCaseLike, ShowCaseBookmark, CommentUpvote,
    VisionBoardTask, Follower, Location
)
from supabase import AsyncClient, create_async_client, AsyncClientOptions
from fastapi import HTTPException

load_dotenv()

_options = AsyncClientOptions()
class UserHandler:
    supabase: AsyncClient

    async def init(self):
        self.supabase = await create_async_client(
            os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"),
            options=_options
        )

    # User Management Methods
    async def fetch_user(
        self,
        *,
        user_id: Union[UUID, str, None] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Optional[User]:
        if user_id:
            return await self._fetch_user_by_id(user_id)

        if email and password:
            return await self._fetch_user_by_email(email, password)

    async def create_user(self, *, user: User):
        payload = user.model_dump(mode="json", exclude={"is_following"})
        response = await self.supabase.table("users").insert(payload).execute()
        return self._parse(response.data)

    async def update_user(
        self, *, user_id: Union[UUID, str], update_payload: User
    ) -> Optional[User]:
        payload = update_payload.model_dump(mode="json", exclude={"is_following"})
        _id = payload.pop("id", user_id)
        assert _id == user_id
        response = await (
            self.supabase.table("users").update(payload).eq("id", _id).execute()
        )
        return self._parse(response.data)

    async def update_user_partial(self, user_id: str, user_update: UserUpdate) -> bool:
        def to_json_serializable(val):
            if isinstance(val, list):
                return [to_json_serializable(i) for i in val]
            if hasattr(val, "model_dump"):
                return val.model_dump()
            if isinstance(val, enum.Enum):
                return val.value
            return val
        update_data = {k: to_json_serializable(v) for k, v in user_update.model_dump(exclude_unset=True).items()}
        if not update_data:
            return False
        response = await self.supabase.table("users") \
            .update(update_data) \
            .eq("id", str(user_id)) \
            .execute()
        return bool(response.data)

    # Follower Management Methods
    async def get_followers(self, *, user_id: Union[UUID, str]) -> List[User]:
        response = await (
            self.supabase.table("followers")
            .select("user_id")
            .eq("following_id", str(user_id))
            .execute()
        )
        if not response.data:
            return []
        follower_ids = [record["user_id"] for record in response.data]
        if not follower_ids:
            return []
        # Batch fetch all users
        users_response = await (
            self.supabase.table("users")
            .select("*")
            .in_("id", follower_ids)
            .execute()
        )
        return [User(**user) for user in users_response.data]

    async def get_following(self, *, user_id: Union[UUID, str]) -> List[User]:
        response = await (
            self.supabase.table("followers")
            .select("following_id")
            .eq("user_id", str(user_id))
            .execute()
        )
        if not response.data:
            return []
        following_ids = [record["following_id"] for record in response.data]
        if not following_ids:
            return []
        # Batch fetch all users
        users_response = await (
            self.supabase.table("users")
            .select("*")
            .in_("id", following_ids)
            .execute()
        )
        return [User(**user) for user in users_response.data]

    async def get_following_by_role(self, *, user_id: Union[UUID, str], role: str) -> List[User]:
        """Get following users filtered by role"""
        response = await (
            self.supabase.table("followers")
            .select("following_id")
            .eq("user_id", str(user_id))
            .execute()
        )
        if not response.data:
            return []
        following_ids = [record["following_id"] for record in response.data]
        if not following_ids:
            return []
        # Batch fetch all users with the specified role
        users_response = await (
            self.supabase.table("users")
            .select("*")
            .in_("id", following_ids)
            .contains("genres", f'["{role}"]')
            .execute()
        )
        return [User(**user) for user in users_response.data]

    async def follow(self, following_id: Union[UUID, str], *, user_id: Union[UUID, str]):
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        if isinstance(following_id, str):
            following_id = UUID(following_id)
        data = Follower(user_id=user_id, following_id=following_id)
        payload = data.model_dump(mode="json")
        await self.supabase.table("followers").insert(payload).execute()

    async def unfollow(self, following_id: Union[UUID, str], *, user_id: Union[UUID, str]):
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        if isinstance(following_id, str):
            following_id = UUID(following_id)
        await (
            self.supabase.table("followers")
            .delete()
            .eq("user_id", str(user_id))
            .eq("following_id", str(following_id))
            .execute()
        )

    # Message Methods
    async def get_message_users(self, *, user_id: Union[UUID, str]) -> List[User]:
        response = await (
            self.supabase.table("messages")
            .select("DISTINCT sender_id, receiver_id")
            .or_(f"sender_id.eq.{user_id},receiver_id.eq.{user_id}")
            .execute()
        )
        return [User(**user) for user in response.data]

    async def create_message(self, *, sender_id: Union[UUID, str], receiver_id: Union[UUID, str], message: str):
        payload = {
            "sender_id": str(sender_id),
            "receiver_id": str(receiver_id),
            "message": message
        }
        await self.supabase.table("messages").insert(payload).execute()

    async def get_messages(self, *, user_id: Union[UUID, str], other_user_id: Union[UUID, str], limit: int) -> List[dict]:
        response = await (
            self.supabase.table("messages")
            .select("*")
            .or_(f"sender_id.eq.{user_id},receiver_id.eq.{user_id}")
            .or_(f"sender_id.eq.{other_user_id},receiver_id.eq.{other_user_id}")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data

    # Showcase Methods
    async def get_showcases(self, *, user_id: Union[UUID, str]) -> List[Showcase]:
        response = await (
            self.supabase.table("showcases")
            .select("*")
            .eq("owner_id", str(user_id))
            .execute()
        )
        return [Showcase(**showcase) for showcase in response.data]

    async def create_showcase(self, *, showcase: Showcase, user_id: Union[UUID, str]):
        payload = showcase.model_dump(mode="json")
        payload["owner_id"] = str(user_id)
        await self.supabase.table("showcases").insert(payload).execute()

    async def get_showcase(self, *, showcase_id: Union[UUID, str]) -> Optional[Showcase]:
        response = await (
            self.supabase.table("showcases")
            .select("*")
            .eq("id", str(showcase_id))
            .execute()
        )
        return self._parse(response.data, model=Showcase)

    async def update_showcase(self, *, showcase_id: Union[UUID, str], showcase: Showcase, user_id: Union[UUID, str]):
        payload = showcase.model_dump(mode="json")
        await (
            self.supabase.table("showcases")
            .update(payload)
            .eq("id", str(showcase_id))
            .eq("owner_id", str(user_id))
            .execute()
        )

    async def delete_showcase(self, *, showcase_id: Union[UUID, str], user_id: Union[UUID, str]):
        await (
            self.supabase.table("showcases")
            .delete()
            .eq("id", str(showcase_id))
            .eq("owner_id", str(user_id))
            .execute()
        )

    # Showcase Interaction Methods
    async def like_showcase(self, *, showcase_id: Union[UUID, str], user_id: Union[UUID, str]):
        data = ShowCaseLike(user_id=user_id, showcase_id=showcase_id)
        payload = data.model_dump(mode="json")
        await self.supabase.table("showcase_likes").insert(payload).execute()

    async def unlike_showcase(self, *, showcase_id: Union[UUID, str], user_id: Union[UUID, str]):
        await (
            self.supabase.table("showcase_likes")
            .delete()
            .eq("user_id", str(user_id))
            .eq("showcase_id", str(showcase_id))
            .execute()
        )

    async def create_comment(self, *, showcase_id: Union[UUID, str], comment: Comment, user_id: Union[UUID, str]):
        payload = comment.model_dump(mode="json")
        payload["author_id"] = str(user_id)
        payload["showcase_id"] = str(showcase_id)
        await self.supabase.table("comments").insert(payload).execute()

    async def upvote_comment(self, *, comment_id: Union[UUID, str], user_id: Union[UUID, str]):
        data = CommentUpvote(user_id=user_id, comment_id=comment_id)
        payload = data.model_dump(mode="json")
        await self.supabase.table("comment_upvotes").insert(payload).execute()

    async def remove_comment_upvote(self, *, comment_id: Union[UUID, str], user_id: Union[UUID, str]):
        await (
            self.supabase.table("comment_upvotes")
            .delete()
            .eq("user_id", str(user_id))
            .eq("comment_id", str(comment_id))
            .execute()
        )

    async def bookmark_showcase(self, *, showcase_id: Union[UUID, str], user_id: Union[UUID, str]):
        data = ShowCaseBookmark(user_id=user_id, showcase_id=showcase_id)
        payload = data.model_dump(mode="json")
        await self.supabase.table("showcase_bookmarks").insert(payload).execute()

    async def unbookmark_showcase(self, *, showcase_id: Union[UUID, str], user_id: Union[UUID, str]):
        await (
            self.supabase.table("showcase_bookmarks")
            .delete()
            .eq("user_id", str(user_id))
            .eq("showcase_id", str(showcase_id))
            .execute()
        )

    # Vision Board Methods
    async def get_visionboards(self, *, user_id: Union[UUID, str]) -> List[VisionBoard]:
        response = await (
            self.supabase.table("visionboards")
            .select("*")
            .eq("created_by", str(user_id))
            .execute()
        )
        return [VisionBoard(**visionboard) for visionboard in response.data]

    async def create_visionboard(self, *, visionboard: VisionBoard, user_id: Union[UUID, str]):
        payload = visionboard.model_dump(mode="json")
        payload["created_by"] = str(user_id)
        await self.supabase.table("visionboards").insert(payload).execute()

    async def update_visionboard(self, *, visionboard_id: Union[UUID, str], visionboard: VisionBoard, user_id: Union[UUID, str]):
        payload = visionboard.model_dump(mode="json")
        await (
            self.supabase.table("visionboards")
            .update(payload)
            .eq("id", str(visionboard_id))
            .eq("created_by", str(user_id))
            .execute()
        )

    async def delete_visionboard(self, *, visionboard_id: Union[UUID, str], user_id: Union[UUID, str]):
        await (
            self.supabase.table("visionboards")
            .delete()
            .eq("id", str(visionboard_id))
            .eq("created_by", str(user_id))
            .execute()
        )

    async def assign_visionboard_task(self, *, visionboard_id: Union[UUID, str], user_id: Union[UUID, str], task: VisionBoardTask, assigner_id: Union[UUID, str]):
        payload = task.model_dump(mode="json")
        payload["visionboard_id"] = str(visionboard_id)
        payload["user_id"] = str(user_id)
        payload["assigner_id"] = str(assigner_id)
        await self.supabase.table("visionboard_tasks").insert(payload).execute()

    async def create_visionboard_draft(self, *, visionboard_id: Union[UUID, str], user_id: Union[UUID, str]):
        await (
            self.supabase.table("visionboards")
            .update({"status": "draft"})
            .eq("id", str(visionboard_id))
            .eq("created_by", str(user_id))
            .execute()
        )

    # Browse Methods
    async def get_nearby_artists(self, user_id: str, genre: str) -> list[User]:
        # 1. Fetch the current user's location
        current_user_resp = await self.supabase.table("users").select("*").eq("id", str(user_id)).single().execute()
        current_user = current_user_resp.data
        if not current_user or not current_user.get("location"):
            return []

        lat1 = current_user["location"]["latitude"]
        lon1 = current_user["location"]["longitude"]

        # 2. Fetch all users in the same genre (excluding the current user)
        response = await self.supabase.table("users") \
            .select("*") \
            .neq("id", str(user_id)) \
            .contains("genres", f'["{genre}"]') \
            .execute()

        def haversine(lat1, lon1, lat2, lon2):
            R = 6371  # Earth radius in km
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlambda = math.radians(lon2 - lon1)
            a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
            c = 2*math.atan2(math.sqrt(a), math.sqrt(1 - a))
            return R * c

        # 3. Calculate distance for each user and sort
        users = []
        for user in response.data:
            loc = user.get("location")
            if loc and "latitude" in loc and "longitude" in loc:
                distance = haversine(lat1, lon1, loc["latitude"], loc["longitude"])
                user["distance"] = distance
                users.append(user)

        users.sort(key=lambda u: u["distance"])
        return [User(**user) for user in users]

    async def get_top_rated_artists(self, genre_name: str) -> list[User]:
        # Query users whose genres include the given genre_name, and order by rating descending
        response = await self.supabase.table("users") \
            .select("*") \
            .contains("genres", f'["{genre_name}"]') \
            .order("rating", desc=True) \
            .execute()
        return [User(**user) for user in response.data]

    async def get_artist_showcases(self, *, artist_id: Union[UUID, str]) -> List[Showcase]:
        response = await (
            self.supabase.table("showcases")
            .select("*")
            .eq("owner_id", str(artist_id))
            .execute()
        )
        return [Showcase(**showcase) for showcase in response.data]

    # Helper Methods
    async def _fetch_user_by_email(
        self, email: str, password: str
    ) -> Optional[User]:
        response = await (
            self.supabase.table("users")
            .select("*")
            .eq("email", email)
            .eq("password", password)
            .execute()
        )
        print(response)
        return self._parse(response.data)

    async def _fetch_user_by_id(self, user_id):
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        response = await (
            self.supabase.table("users").select("*").eq("id", user_id).execute()
        )
        return self._parse(response.data)

    def _parse(self, response: list, count: int = 1, model: type = User):
        if len(response) == 0:
            return None
        assert len(response) == count
        return model(**response[0])

    async def get_users_by_genre(self, genre_name: str) -> list[User]:
        response = await (
            self.supabase.table("users")
            .select("*")
            .contains("genres", f'["{genre_name}"]')
            .execute()
        )
        return [User(**user) for user in response.data]

    async def user_exists(self, user_id: str) -> bool:
        user_id = str(user_id).lower()
        try:
            result = await (
                self.supabase.table("users")
                .select("id")
                .eq("id", user_id)
                .execute()
            )
            return len(result.data) > 0
        except Exception as e:
            print(f"Error in user_exists: {str(e)}")
            return False

    async def get_following_relationships(self, user_id: str, target_ids: List[str]) -> List[str]:
        if not target_ids:
            return []
        response = await (
            self.supabase.table("followers")
            .select("following_id")
            .eq("user_id", str(user_id))
            .in_("following_id", target_ids)
            .execute()
        )
        return [record["following_id"] for record in response.data]

    async def send_direct_message(self, sender_id: str, receiver_id: str, message: str):
        # Security: sender_id must match authenticated user
        payload = {
            "sender_id": str(sender_id),
            "receiver_id": str(receiver_id),
            "message": message
        }
        await self.supabase.table("direct_messages").insert(payload).execute()

    async def get_direct_messages(self, user_id: str, other_user_id: str, limit: int = 50, before: str = None):
        # Fetch messages where (sender_id=user_id AND receiver_id=other_user_id) OR (sender_id=other_user_id AND receiver_id=user_id)
        query = (
            self.supabase.table("direct_messages")
            .select("*")
            .or_(
                f"and(sender_id.eq.{user_id},receiver_id.eq.{other_user_id}),"
                f"and(sender_id.eq.{other_user_id},receiver_id.eq.{user_id})"
            )
            .order("created_at", desc=True)
            .limit(limit)
        )
        if before:
            query = query.lt("created_at", before)
        response = await query.execute()
        return response.data