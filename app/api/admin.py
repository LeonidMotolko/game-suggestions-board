from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.dependencies import require_admin
from app.models.user import User
from app.schemas.suggestion import SuggestionUpdate
from app.services.suggestion_service import (
    get_suggestions,
    get_suggestion,
    update_suggestion,
    delete_suggestion,
    get_dashboard_stats,
)
from app.services.user_service import get_user_by_id

router = APIRouter()


@router.get("/dashboard")
async def admin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    stats = await get_dashboard_stats(db)
    return request.app.state.templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "user": current_user, "stats": stats},
    )


@router.get("/suggestions")
async def admin_suggestions_list(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    raw = await get_suggestions(db)
    # Извлекаем только объекты Suggestion (первый элемент кортежа)
    suggestions = [item[0] for item in raw]
    return request.app.state.templates.TemplateResponse(
        "admin/suggestions_list.html",
        {"request": request, "user": current_user, "suggestions": suggestions},
    )


@router.post("/suggestions/{suggestion_id}/status")
async def admin_change_status(
    request: Request,
    suggestion_id: str,
    status: str = Form(...),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    suggestion = await get_suggestion(db, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    try:
        update_data = SuggestionUpdate(status=status)
        await update_suggestion(db, suggestion, update_data)
        await db.commit()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")
    return RedirectResponse(url="/admin/suggestions", status_code=303)


@router.post("/suggestions/{suggestion_id}/delete")
async def admin_delete_suggestion(
    request: Request,
    suggestion_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    suggestion = await get_suggestion(db, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    await delete_suggestion(db, suggestion)
    await db.commit()
    return RedirectResponse(url="/admin/suggestions", status_code=303)


@router.get("/users")
async def admin_users_list(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return request.app.state.templates.TemplateResponse(
        "admin/users_list.html",
        {"request": request, "user": current_user, "users": users},
    )


@router.post("/users/{user_id}/ban")
async def admin_toggle_ban(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    target = await get_user_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot ban yourself")
    target.is_active = not target.is_active
    await db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)