from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class Notification(BaseModel):
    id: UUID
    receiver_id: UUID
    sender_id: UUID
    object_type: str  # e.g., 'visionboard', 'message', 'showcase', 'comment'
    object_id: UUID   # the id of the referenced object
    event_type: str   # e.g., 'created', 'invitation', 'like', 'message', 'comment'
    status: str
    data: Optional[Dict[str, Any]] = None  # extra context (optional)
    message: Optional[str]
    created_at: datetime
    updated_at: datetime 