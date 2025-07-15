from __future__ import annotations
import datetime
import uuid
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

# Enums
class VisionBoardStatus(Enum):
    DRAFT = "Draft"
    ACTIVE = "Active"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

class AssignmentStatus(Enum):
    PENDING = "Pending"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"
    REMOVED = "Removed"

class WorkType(Enum):
    ONLINE = "Online"
    OFFLINE = "Offline"

class PaymentType(Enum):
    PAID = "Paid"
    UNPAID = "Unpaid"

class TaskPriority(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class TaskStatus(Enum):
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    BLOCKED = "Blocked"

class EquipmentStatus(Enum):
    REQUIRED = "Required"
    CONFIRMED = "Confirmed"
    NOT_AVAILABLE = "Not Available"

class DependencyType(Enum):
    FINISH_TO_START = "Finish-to-Start"
    START_TO_START = "Start-to-Start"
    FINISH_TO_FINISH = "Finish-to-Finish"

class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

# Core Models
class VisionBoard(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    description: Optional[str] = None
    start_date: datetime.datetime
    end_date: datetime.datetime
    status: VisionBoardStatus = VisionBoardStatus.DRAFT
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    created_by: uuid.UUID

    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v

class VisionBoardCreate(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: datetime.datetime
    end_date: datetime.datetime
    status: VisionBoardStatus = VisionBoardStatus.DRAFT

    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v

class VisionBoardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime.datetime] = None
    end_date: Optional[datetime.datetime] = None
    status: Optional[VisionBoardStatus] = None

class Genre(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    visionboard_id: uuid.UUID
    name: str
    description: Optional[str] = None
    min_required_people: int = 1
    max_allowed_people: Optional[int] = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class GenreCreate(BaseModel):
    name: str
    description: Optional[str] = None
    min_required_people: int = 1
    max_allowed_people: Optional[int] = None

class GenreUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    min_required_people: Optional[int] = None
    max_allowed_people: Optional[int] = None

class Equipment(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    description: Optional[str] = None
    category: str  # e.g., 'Camera', 'Lighting', 'Audio'
    brand: Optional[str] = None
    model: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None

class EquipmentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    brand: Optional[str] = None
    model: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None

class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None

class GenreAssignment(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    genre_id: uuid.UUID
    user_id: uuid.UUID
    status: AssignmentStatus = AssignmentStatus.PENDING
    work_type: WorkType
    payment_type: PaymentType
    payment_amount: Optional[Decimal] = None
    currency: Optional[str] = None
    invited_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    responded_at: Optional[datetime.datetime] = None
    assigned_by: uuid.UUID

    @validator('payment_amount')
    def validate_payment_amount(cls, v, values):
        if values.get('payment_type') == PaymentType.PAID and v is None:
            raise ValueError('Payment amount is required when payment type is Paid')
        return v

class GenreAssignmentCreate(BaseModel):
    genre_id: uuid.UUID
    user_id: uuid.UUID
    work_type: WorkType
    payment_type: PaymentType
    payment_amount: Optional[Decimal] = None
    currency: Optional[str] = None

class GenreAssignmentUpdate(BaseModel):
    status: Optional[AssignmentStatus] = None
    work_type: Optional[WorkType] = None
    payment_type: Optional[PaymentType] = None
    payment_amount: Optional[Decimal] = None
    currency: Optional[str] = None

class RequiredEquipment(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    genre_assignment_id: uuid.UUID
    equipment_id: uuid.UUID
    quantity: int = 1
    is_provided_by_assignee: bool = False
    notes: Optional[str] = None
    status: EquipmentStatus = EquipmentStatus.REQUIRED

class RequiredEquipmentCreate(BaseModel):
    equipment_id: uuid.UUID
    quantity: int = 1
    is_provided_by_assignee: bool = False
    notes: Optional[str] = None

class RequiredEquipmentUpdate(BaseModel):
    quantity: Optional[int] = None
    is_provided_by_assignee: Optional[bool] = None
    notes: Optional[str] = None
    status: Optional[EquipmentStatus] = None

class VisionBoardTask(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    genre_assignment_id: uuid.UUID
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.NOT_STARTED
    due_date: Optional[datetime.datetime] = None
    estimated_hours: Optional[Decimal] = None
    actual_hours: Optional[Decimal] = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    created_by: uuid.UUID

class VisionBoardTaskCreate(BaseModel):
    genre_assignment_id: uuid.UUID
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime.datetime] = None
    estimated_hours: Optional[Decimal] = None

class VisionBoardTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[datetime.datetime] = None
    estimated_hours: Optional[Decimal] = None
    actual_hours: Optional[Decimal] = None

class TaskDependency(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    task_id: uuid.UUID
    depends_on_task_id: uuid.UUID
    dependency_type: DependencyType = DependencyType.FINISH_TO_START

class TaskDependencyCreate(BaseModel):
    depends_on_task_id: uuid.UUID
    dependency_type: DependencyType = DependencyType.FINISH_TO_START

class TaskComment(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    task_id: uuid.UUID
    user_id: uuid.UUID
    comment: str
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class TaskCommentCreate(BaseModel):
    comment: str

class TaskCommentUpdate(BaseModel):
    comment: str

class TaskAttachment(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    task_id: uuid.UUID
    file_name: str
    file_url: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_by: uuid.UUID
    uploaded_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class TaskAttachmentCreate(BaseModel):
    file_name: str
    file_url: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None

# Response Models with Related Data
class VisionBoardWithGenres(VisionBoard):
    genres: List[Genre] = []

class GenreWithAssignments(Genre):
    assignments: List[GenreAssignment] = []

class GenreAssignmentWithDetails(GenreAssignment):
    user_name: Optional[str] = None
    genre_name: Optional[str] = None
    equipment: List[RequiredEquipment] = []
    tasks: List[VisionBoardTask] = []

class VisionBoardTaskWithDetails(VisionBoardTask):
    comments: List[TaskComment] = []
    attachments: List[TaskAttachment] = []
    dependencies: List[TaskDependency] = []
    user_name: Optional[str] = None
    genre_name: Optional[str] = None

class VisionBoardSummary(BaseModel):
    id: uuid.UUID
    name: str
    status: VisionBoardStatus
    start_date: datetime.datetime
    end_date: datetime.datetime
    total_genres: int
    total_assignments: int
    total_tasks: int
    completed_tasks: int
    created_by: uuid.UUID

# Statistics Models
class VisionBoardStats(BaseModel):
    total_visionboards: int
    active_visionboards: int
    completed_visionboards: int
    total_assignments: int
    pending_assignments: int
    total_tasks: int
    completed_tasks: int
    overdue_tasks: int 

class Invitation(BaseModel):
    id: uuid.UUID
    receiver_id: uuid.UUID
    sender_id: uuid.UUID
    object_type: str
    object_id: uuid.UUID
    status: InvitationStatus
    data: dict | None = None
    created_at: datetime.datetime
    responded_at: datetime.datetime | None = None

class InvitationCreate(BaseModel):
    receiver_id: uuid.UUID
    object_type: str
    object_id: uuid.UUID
    data: dict | None = None

class InvitationUpdate(BaseModel):
    status: InvitationStatus
    data: dict | None = None
    responded_at: datetime.datetime | None = None

class GroupMessage(BaseModel):
    id: uuid.UUID
    visionboard_id: uuid.UUID
    sender_id: uuid.UUID
    message: str
    created_at: datetime.datetime

class GroupMessageCreate(BaseModel):
    message: str

class DirectMessage(BaseModel):
    id: uuid.UUID
    sender_id: uuid.UUID
    receiver_id: uuid.UUID
    message: str
    created_at: datetime.datetime

class DirectMessageCreate(BaseModel):
    receiver_id: uuid.UUID
    message: str 

class Draft(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    visionboard_id: uuid.UUID
    user_id: uuid.UUID
    media_url: str
    media_type: Optional[str] = None  # e.g., 'image', 'video', 'audio'
    description: Optional[str] = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class DraftCreate(BaseModel):
    visionboard_id: uuid.UUID
    media_url: str
    media_type: Optional[str] = None
    description: Optional[str] = None

class DraftUpdate(BaseModel):
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    description: Optional[str] = None

class DraftComment(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    draft_id: uuid.UUID
    user_id: uuid.UUID
    comment: str
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class DraftCommentCreate(BaseModel):
    draft_id: uuid.UUID
    comment: str

class DraftCommentUpdate(BaseModel):
    comment: str

class DraftWithComments(Draft):
    comments: List[DraftComment] = []
    user_name: Optional[str] = None 