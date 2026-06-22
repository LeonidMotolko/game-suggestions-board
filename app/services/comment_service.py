import uuid
from typing import List
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.models.comment import Comment
from app.models.user import User


async def create_comment(db: AsyncSession, user_id: uuid.UUID, suggestion_id: uuid.UUID, text: str) -> Comment:
    comment = Comment(user_id=user_id, suggestion_id=suggestion_id, text=text)
    db.add(comment)
    await db.flush()
    return comment


async def get_comments_for_suggestion(db: AsyncSession, suggestion_id: uuid.UUID) -> List[Comment]:
    result = await db.execute(
        select(Comment)
        .options(joinedload(Comment.user))
        .where(Comment.suggestion_id == suggestion_id)
        .order_by(Comment.created_at.asc())
    )
    return result.scalars().all()


async def delete_comment(db: AsyncSession, comment: Comment) -> None:
    await db.delete(comment)
    await db.flush()


async def update_comment_text(db: AsyncSession, comment: Comment, new_text: str) -> None:
    comment.text = new_text
    await db.flush()