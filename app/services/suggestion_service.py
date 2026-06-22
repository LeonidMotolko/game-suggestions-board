from typing import List, Optional, Tuple
import uuid
from sqlalchemy import select, func, or_, case, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.suggestion import Suggestion, SuggestionStatus
from app.models.user import User
from app.models.vote import Vote
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


async def get_suggestions(
    db: AsyncSession,
    search: Optional[str] = None,
    status: Optional[SuggestionStatus] = None,
    user_id: Optional[uuid.UUID] = None,
) -> List[Tuple[Suggestion, int, int]]:
    query = select(
        Suggestion,
        func.coalesce(func.sum(case((Vote.vote_type == "up", 1), else_=0)), 0).label("upvotes"),
        func.coalesce(func.sum(case((Vote.vote_type == "down", 1), else_=0)), 0).label("downvotes"),
    ).outerjoin(Vote, Suggestion.id == Vote.suggestion_id
    ).group_by(Suggestion.id
    ).order_by(Suggestion.created_at.desc())

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Suggestion.title.ilike(search_term),
                Suggestion.description.ilike(search_term),
            )
        )
    if status:
        query = query.where(Suggestion.status == status)
    if user_id:
        query = query.where(Suggestion.user_id == user_id)

    result = await db.execute(query)
    return [(row[0], row[1], row[2]) for row in result.all()]


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
    # Сначала удаляем все голоса, связанные с предложением
    await db.execute(delete(Vote).where(Vote.suggestion_id == suggestion.id))
    # Затем удаляем само предложение
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


async def vote_suggestion(db: AsyncSession, user_id: uuid.UUID, suggestion_id: uuid.UUID, vote_type: str) -> dict:
    suggestion = await get_suggestion(db, suggestion_id)
    if not suggestion:
        return None

    existing_vote = await db.execute(
        select(Vote).where(Vote.user_id == user_id, Vote.suggestion_id == suggestion_id)
    )
    existing = existing_vote.scalar_one_or_none()

    if existing:
        if existing.vote_type == vote_type:
            await db.delete(existing)
        else:
            existing.vote_type = vote_type
    else:
        vote = Vote(user_id=user_id, suggestion_id=suggestion_id, vote_type=vote_type)
        db.add(vote)

    await db.flush()

    upvotes = await db.scalar(
        select(func.count()).where(Vote.suggestion_id == suggestion_id, Vote.vote_type == "up")
    )
    downvotes = await db.scalar(
        select(func.count()).where(Vote.suggestion_id == suggestion_id, Vote.vote_type == "down")
    )
    return {"upvotes": upvotes, "downvotes": downvotes}


async def get_user_votes_for_suggestions(db: AsyncSession, user_id: uuid.UUID, suggestion_ids: List[uuid.UUID]) -> dict:
    if not suggestion_ids:
        return {}
    result = await db.execute(
        select(Vote).where(
            Vote.user_id == user_id,
            Vote.suggestion_id.in_(suggestion_ids)
        )
    )
    votes = result.scalars().all()
    return {str(v.suggestion_id): v.vote_type for v in votes}