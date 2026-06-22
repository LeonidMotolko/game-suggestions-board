import uuid
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.comment import Comment


async def create_comment(db: AsyncSession, user_id: uuid.UUID, suggestion_id: uuid.UUID, text: str) -> Comment:
    comment = Comment(user_id=user_id, suggestion_id=suggestion_id, text=text)
    db.add(comment)
    await db.flush()
    return comment


async def get_comments_for_suggestion(db: AsyncSession, suggestion_id: uuid.UUID) -> List[Comment]:
    result = await db.execute(
        select(Comment)
        .where(Comment.suggestion_id == suggestion_id)
        .order_by(Comment.created_at.asc())
    )
    return result.scalars().all()