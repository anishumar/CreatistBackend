from __future__ import annotations
import datetime

from pydantic import BaseModel, Field
import uuid
from typing import Optional, List
from src.models import UserGenre, WorkMode, PaymentMode

class Location(BaseModel):
    latitude: float
    longitude: float

class User(BaseModel):
    id: uuid.UUID = Field(default_factory=lambda: uuid.uuid4())

    name: str
    username: Optional[str] = None
    description: Optional[str] = None
    email: str
    password: str

    profile_image_url: Optional[str] = None
    age: Optional[int] = None
    genres: Optional[List[UserGenre]] = None
    payment_mode: Optional[PaymentMode] = None
    work_mode: Optional[WorkMode] = None
    location: Optional[Location] = None
    rating: Optional[float] = None
    city: Optional[str] = None
    country: Optional[str] = None
    distance: Optional[float] = None
    is_following: Optional[bool] = None  # This is computed, not stored in DB


class UserUpdate(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    description: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    profile_image_url: Optional[str] = None
    age: Optional[int] = None
    genres: Optional[List[UserGenre]] = None
    payment_mode: Optional[PaymentMode] = None
    work_mode: Optional[WorkMode] = None
    location: Optional[Location] = None
    rating: Optional[float] = None
    city: Optional[str] = None
    country: Optional[str] = None
    distance: Optional[float] = None
    


class Showcase(BaseModel):
    id: uuid.UUID = Field(default_factory=lambda: uuid.uuid4())
    owner_id: uuid.UUID
    visionboard: Optional[uuid.UUID]
    description: Optional[str] = None
    media_link: Optional[str] = None
    media_type: Optional[str] = None


class ShowCaseLike(BaseModel):
    user_id: uuid.UUID
    showcase_id: uuid.UUID


class ShowCaseBookmark(BaseModel):
    user_id: uuid.UUID
    showcase_id: uuid.UUID


class Comment(BaseModel):
    id: uuid.UUID
    showcase_id: uuid.UUID
    text: str
    author_id: uuid.UUID
    timestamp: datetime.datetime


class CommentUpvote(BaseModel):
    user_id: uuid.UUID
    comment_id: uuid.UUID

class VisionBoard(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    description: str
    start_date: datetime.datetime
    end_date: datetime.datetime


class VisionBoardRole(BaseModel):
    visionboard_id: uuid.UUID
    role: UserGenre
    user_id: uuid.UUID


class VisionBoardTask(BaseModel):
    user_id: uuid.UUID
    visionboard_id: uuid.UUID
    title: str
    start_date: datetime.datetime
    end_date: datetime.datetime


class Follower(BaseModel):
    user_id: uuid.UUID
    following_id: uuid.UUID
