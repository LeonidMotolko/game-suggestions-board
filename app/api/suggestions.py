from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid

from app.database import get_async_session
from app.dependencies import get_current_active_user, get_optional_user
from app.models.user import User
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
from app.services.storage_service import get_storage, StorageInterface
from app.config import settings
from sqlalchemy import select, func
from app.models.vote import Vote

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
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max {settings.MAX_UPLOAD_SIZE_MB} MB",
            )
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

    suggestion = await get_suggestion(db, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    # Получить голоса для этого предложения
    upvotes = await db.scalar(
        select(func.count()).where(Vote.suggestion_id == suggestion.id, Vote.vote_type == "up")
    )
    downvotes = await db.scalar(
        select(func.count()).where(Vote.suggestion_id == suggestion.id, Vote.vote_type == "down")
    )
    # Текущий голос пользователя
    user_vote = None
    if current_user:
        vote = await db.scalar(
            select(Vote).where(Vote.user_id == current_user.id, Vote.suggestion_id == suggestion.id)
        )
        if vote:
            user_vote = vote.vote_type

    return request.app.state.templates.TemplateResponse(
        "suggestions/detail.html",
        {
            "request": request,
            "suggestion": suggestion,
            "user": current_user,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "user_vote": user_vote,
        },
    )


@router.post("/{suggestion_id}/vote")
async def vote(
    suggestion_id: str,
    vote_type: str = Form(...),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    if vote_type not in ("up", "down"):
        raise HTTPException(status_code=400, detail="Invalid vote type")
    result = await vote_suggestion(db, current_user.id, uuid.UUID(suggestion_id), vote_type)
    if result is None:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    await db.commit()
    return JSONResponse(content=result)