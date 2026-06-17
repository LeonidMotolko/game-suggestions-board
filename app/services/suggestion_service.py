from typing import List, Optional
import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.suggestion import Suggestion, SuggestionStatus
from app.models.user import User
from app.schemas.suggestion import SuggestionCreate, SuggestionUpdate

async def create_suggestion(db: AsyncSession, user_id: uuid.UUID, data: SuggestionCreate,
                            attachment_path: Optional[str] = None) -> Suggestion:
    suggestion = Suggestion(
        title=data.title,
        description=data.description,
        user_id=user_id,
        attachment_path=attachment_path,
    )
    db.add(suggestion)
    await db.flush()
    return suggestion

async def get_suggestions(db: AsyncSession, status: Optional[SuggestionStatus] = None,
                          user_id: Optional[uuid.UUID] = None) -> List[Suggestion]:
    query = select(Suggestion).order_by(Suggestion.created_at.desc())
    if status:
        query = query.where(Suggestion.status == status)
    if user_id:
        query = query.where(Suggestion.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().all()

async def get_suggestion(db: AsyncSession, suggestion_id: uuid.UUID) -> Optional[Suggestion]:
    result = await db.execute(select(Suggestion).where(Suggestion.id == suggestion_id))
    return result.scalar_one_or_none()

async def update_suggestion(db: AsyncSession, suggestion: Suggestion, update_data: SuggestionUpdate) -> Suggestion:
    if update_data.title is not None:
        suggestion.title = update_data.title
    if update_data.description is not None:
        suggestion.description = update_data.description
    if update_data.status is not None:
        suggestion.status = update_data.status
    await db.flush()
    return suggestion

async def delete_suggestion(db: AsyncSession, suggestion: Suggestion) -> None:
    await db.delete(suggestion)
    await db.flush()

async def get_dashboard_stats(db: AsyncSession):
    total = await db.scalar(select(func.count(Suggestion.id)))
    total_users = await db.scalar(select(func.count(User.id)))
    by_status = await db.execute(
        select(Suggestion.status, func.count(Suggestion.id)).group_by(Suggestion.status)
    )
    status_counts = {row[0].value: row[1] for row in by_status}
    return {
        "total_suggestions": total,
        "total_users": total_users,
        "by_status": status_counts,
    }
