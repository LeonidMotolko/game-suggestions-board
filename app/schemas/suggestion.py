from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid
from app.models.suggestion import SuggestionStatus

class SuggestionCreate(BaseModel):
    title: str
    description: str

class SuggestionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[SuggestionStatus] = None

class SuggestionRead(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    status: SuggestionStatus
    user_id: uuid.UUID
    attachment_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
