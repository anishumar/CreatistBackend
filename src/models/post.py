from __future__ import annotations
import uuid
import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum

class PostStatus(str, Enum):
    public = "public"
    private = "private"
    draft = "draft"
    archived = "archived"

class PostVisibility(str, Enum):
    public = "public"
    private = "private"
    followers = "followers"

class MediaType(str, Enum):
    image = "image"
    video = "video"

class CollaboratorRole(str, Enum):
    author = "author"
    editor = "editor"
    invited = "invited"
    collaborator = "collaborator"

class PostMedia(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    post_id: uuid.UUID
    url: str
    type: MediaType
    order: int = 0

class PostMediaCreate(BaseModel):
    url: str
    type: MediaType
    order: int = 0

class PostTag(BaseModel):
    post_id: uuid.UUID
    tag: str

class PostCollaborator(BaseModel):
    post_id: uuid.UUID
    user_id: uuid.UUID
    role: CollaboratorRole = CollaboratorRole.collaborator

class PostCollaboratorCreate(BaseModel):
    user_id: uuid.UUID
    role: CollaboratorRole = CollaboratorRole.collaborator

class PostComment(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    post_id: uuid.UUID
    user_id: uuid.UUID
    content: str
    parent_comment_id: Optional[uuid.UUID] = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    deleted_at: Optional[datetime.datetime] = None

class PostCommentCreate(BaseModel):
    content: str
    parent_comment_id: Optional[uuid.UUID] = None

class PostCommentUpdate(BaseModel):
    content: Optional[str] = None

class PostLike(BaseModel):
    user_id: uuid.UUID
    post_id: uuid.UUID
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class PostView(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    post_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    viewed_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class Hashtag(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    tag: str

class PostHashtag(BaseModel):
    post_id: uuid.UUID
    hashtag_id: uuid.UUID

class Post(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    caption: Optional[str] = None
    is_collaborative: bool = False
    status: PostStatus = PostStatus.public
    visibility: PostVisibility = PostVisibility.public
    shared_from_post_id: Optional[uuid.UUID] = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    deleted_at: Optional[datetime.datetime] = None

class PostCreate(BaseModel):
    caption: Optional[str] = None
    media: List[PostMediaCreate] = []
    tags: List[str] = []
    collaborators: List[PostCollaboratorCreate] = []
    status: PostStatus = PostStatus.public
    visibility: PostVisibility = PostVisibility.public
    shared_from_post_id: Optional[uuid.UUID] = None
    visionboard_id: Optional[uuid.UUID] = None  # Add visionboard_id field

class PostUpdate(BaseModel):
    caption: Optional[str] = None
    status: Optional[PostStatus] = None
    visibility: Optional[PostVisibility] = None
    deleted_at: Optional[datetime.datetime] = None

class PostWithDetails(Post):
    media: List[PostMedia] = []
    tags: List[str] = []
    collaborators: List[PostCollaborator] = []
    like_count: int = 0
    comment_count: int = 0
    view_count: int = 0
    author_name: Optional[str] = None
    top_comments: List[PostComment] = [] 