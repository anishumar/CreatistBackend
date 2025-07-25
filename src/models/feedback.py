from pydantic import BaseModel, EmailStr, constr
from typing import Optional
import uuid
import datetime

class FeedbackCreate(BaseModel):
    message: constr(min_length=1, max_length=2000)
    email: Optional[EmailStr] = None

class Feedback(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    email: Optional[EmailStr] = None
    message: str
    created_at: datetime.datetime 