from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

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
)
from app.services.storage_service import get_storage, StorageInterface
from app.config import settings

router = APIRouter(prefix="/suggestions")


@router.get("/")
async def list_suggestions(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[User] = Depends(get_optional_user),
):
    suggestions = await get_suggestions(db)
    return request.app.state.templates.TemplateResponse(
        "suggestions/list.html",
        {"request": request, "suggestions": suggestions, "user": current_user},
    )


@router.get("/my")
async def my_suggestions(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    suggestions = await get_suggestions(db, user_id=current_user.id)
    return request.app.state.templates.TemplateResponse(
        "suggestions/list.html",
        {"request": request, "suggestions": suggestions, "user": current_user, "my": True},
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
    # Validate file size
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


# Этот маршрут должен идти ПОСЛЕ всех конкретных, чтобы не перехватывать их
@router.get("/{suggestion_id}")
async def view_suggestion(
    request: Request,
    suggestion_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: Optional[User] = Depends(get_optional_user),
):
    # Проверим, не похоже ли suggestion_id на что-то другое (например, "docs")
    if suggestion_id in ("docs", "redoc", "openapi.json"):
        raise HTTPException(status_code=404, detail="Suggestion not found")

    suggestion = await get_suggestion(db, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return request.app.state.templates.TemplateResponse(
        "suggestions/detail.html",
        {"request": request, "suggestion": suggestion, "user": current_user},
    )