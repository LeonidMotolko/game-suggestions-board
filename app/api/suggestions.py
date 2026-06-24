from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid as uuid_lib

from app.database import get_async_session
from app.dependencies import get_current_active_user, get_optional_user
from app.models.user import User
from app.models.vote import Vote
from app.models.comment import Comment
from app.schemas.suggestion import SuggestionCreate
from app.services.suggestion_service import (
    create_suggestion,
    get_suggestions,
    get_suggestion,
    update_suggestion,
    delete_suggestion,
    vote_suggestion,
    get_user_votes_for_suggestions,
)
from app.services.comment_service import create_comment, get_comments_for_suggestion
from app.services.storage_service import get_storage, StorageInterface
from app.config import settings

router = APIRouter(prefix="/suggestions")


@router.get("/")
async def list_suggestions(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[User] = Depends(get_optional_user),
):
    suggestions_with_votes = await get_suggestions(db)
    suggestions_data = [
        (s, up, down, None) for s, up, down in suggestions_with_votes
    ]
    return request.app.state.templates.TemplateResponse(
        "suggestions/list.html",
        {"request": request, "suggestions_data": suggestions_data, "user": current_user},
    )


@router.get("/my")
async def my_suggestions(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    suggestions_with_votes = await get_suggestions(db, user_id=current_user.id)
    suggestions_data = [
        (s, up, down, None) for s, up, down in suggestions_with_votes
    ]
    return request.app.state.templates.TemplateResponse(
        "suggestions/list.html",
        {"request": request, "suggestions_data": suggestions_data, "user": current_user, "my": True},
    )


@router.post("/")
async def create_new_suggestion(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
    storage: StorageInterface = Depends(get_storage),
):
    if file:
        content = await file.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > settings.MAX_UPLOAD_SIZE_MB:
            raise HTTPException(status_code=400, detail=f"File too large. Max {settings.MAX_UPLOAD_SIZE_MB} MB")
        await file.seek(0)

    attachment_path = None
    if file:
        attachment_path = await storage.upload(file)

    data = SuggestionCreate(title=title, description=description)
    suggestion = await create_suggestion(db, current_user.id, data, attachment_path)
    await db.commit()

    return RedirectResponse(url="/", status_code=303)


@router.get("/{suggestion_id}")
async def view_suggestion(
    request: Request,
    suggestion_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if suggestion_id in ("docs", "redoc", "openapi.json"):
        raise HTTPException(status_code=404, detail="Suggestion not found")

    sug_uuid = uuid_lib.UUID(suggestion_id)
    suggestion = await get_suggestion(db, sug_uuid)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    upvotes = await db.scalar(select(func.count()).where(Vote.suggestion_id == sug_uuid, Vote.vote_type == "up"))
    downvotes = await db.scalar(select(func.count()).where(Vote.suggestion_id == sug_uuid, Vote.vote_type == "down"))
    user_vote = None
    if current_user:
        vote = await db.scalar(select(Vote).where(Vote.user_id == current_user.id, Vote.suggestion_id == sug_uuid))
        if vote:
            user_vote = vote.vote_type
    comments = await get_comments_for_suggestion(db, sug_uuid)

    return request.app.state.templates.TemplateResponse(
        "suggestions/detail.html",
        {
            "request": request, "suggestion": suggestion, "user": current_user,
            "upvotes": upvotes, "downvotes": downvotes, "user_vote": user_vote,
            "comments": comments,
        },
    )


@router.post("/{suggestion_id}/comments")
async def add_comment(
    suggestion_id: str,
    text: str = Form(...),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    sug_uuid = uuid_lib.UUID(suggestion_id)
    suggestion = await get_suggestion(db, sug_uuid)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    await create_comment(db, current_user.id, sug_uuid, text)
    await db.commit()
    return RedirectResponse(url=f"/suggestions/{suggestion_id}", status_code=303)


@router.post("/{suggestion_id}/comments/{comment_id}/delete")
async def delete_comment(
    suggestion_id: str,
    comment_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    sug_uuid = uuid_lib.UUID(suggestion_id)
    comment_uuid = uuid_lib.UUID(comment_id)
    result = await db.execute(select(Comment).where(Comment.id == comment_uuid))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    from app.services.comment_service import delete_comment as delete_comment_svc
    await delete_comment_svc(db, comment)
    await db.commit()
    return RedirectResponse(url=f"/suggestions/{suggestion_id}", status_code=303)


@router.post("/{suggestion_id}/comments/{comment_id}/edit")
async def edit_comment(
    suggestion_id: str,
    comment_id: str,
    text: str = Form(...),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    sug_uuid = uuid_lib.UUID(suggestion_id)
    comment_uuid = uuid_lib.UUID(comment_id)
    result = await db.execute(select(Comment).where(Comment.id == comment_uuid))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    from app.services.comment_service import update_comment_text
    await update_comment_text(db, comment, text)
    await db.commit()
    return RedirectResponse(url=f"/suggestions/{suggestion_id}", status_code=303)


@router.post("/{suggestion_id}/vote")
async def vote(
    suggestion_id: str,
    vote_type: str = Form(...),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    if vote_type not in ("up", "down"):
        raise HTTPException(status_code=400, detail="Invalid vote type")
    sug_uuid = uuid_lib.UUID(suggestion_id)
    result = await vote_suggestion(db, current_user.id, sug_uuid, vote_type)
    if result is None:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    await db.commit()
    return JSONResponse(content=result)