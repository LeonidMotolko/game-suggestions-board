from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, Form, HTTPException, status, BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.config import settings
from app.database import engine, async_session_maker, Base
from app.api import api_router
from app.services.user_service import (
    authenticate_user,
    create_user,
    get_user_by_email,
    create_admin,
    hash_password,
    verify_password,
)
from app.dependencies import get_async_session, get_optional_user, get_current_active_user
from app.models.user import User
from app.models import *  # noqa

templates = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # Создание таблиц
        await conn.run_sync(Base.metadata.create_all)
        # Добавляем колонку nickname, если её нет
        try:
            await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS nickname VARCHAR(100)')
        except Exception:
            pass  # если колонка уже есть, ошибка игнорируется

    async with async_session_maker() as session:
        await create_admin(session, settings.DEFAULT_ADMIN_EMAIL, settings.DEFAULT_ADMIN_PASSWORD)
        await session.commit()

    yield
    await engine.dispose()


app = FastAPI(
    title="Game Suggestions Board",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.state.templates = templates
app.include_router(api_router)


# ---------- Frontend routes ----------
@app.get("/")
async def root(
    request: Request,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(get_optional_user),
):
    from app.services.suggestion_service import get_suggestions, get_user_votes_for_suggestions
    suggestions_with_votes = await get_suggestions(db, search=search, status=status)
    suggestions = [item[0] for item in suggestions_with_votes]
    # Собрать голоса
    votes_map = {}
    if user:
        ids = [s.id for s in suggestions]
        votes_map = await get_user_votes_for_suggestions(db, user.id, ids)
    # Передать в шаблон
    suggestions_data = [
        (s, item[1], item[2], votes_map.get(str(s.id))) for s, item in zip(suggestions, suggestions_with_votes)
    ]
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "suggestions_data": suggestions_data,
        "search": search or "",
        "selected_status": status or "",
    })

@app.get("/auth/register-page")
async def register_page(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})


@app.get("/auth/login-page")
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})


@app.get("/auth/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response


@app.post("/auth/login")
async def login_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_async_session),
):
    user = await authenticate_user(db, email, password)
    if not user:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Неверный email или пароль"},
            status_code=401,
        )
    if not user.is_active:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Аккаунт деактивирован"},
            status_code=400,
        )
    if settings.EMAIL_VERIFICATION_REQUIRED and not user.is_verified:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Email не подтверждён. Проверьте почту."},
            status_code=400,
        )
    from app.api.auth import create_access_token
    access_token = create_access_token({"sub": str(user.id)})
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return response


@app.post("/auth/register")
async def register_form(
    request: Request,
    background_tasks: BackgroundTasks,
    email: str = Form(...),
    password: str = Form(...),
    nickname: str = Form(""),
    db: AsyncSession = Depends(get_async_session),
):
    existing = await get_user_by_email(db, email)
    if existing:
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": "Email уже зарегистрирован"},
            status_code=400,
        )
    user = await create_user(
        db,
        email=email,
        password=password,
        is_verified=not settings.EMAIL_VERIFICATION_REQUIRED,
        is_active=True,
    )
    if nickname.strip():
        user.nickname = nickname.strip()

    if settings.EMAIL_VERIFICATION_REQUIRED:
        from app.api.auth import create_access_token
        from app.services.email_service import send_verification_email
        token = create_access_token({"sub": str(user.id), "verify": True})
        background_tasks.add_task(send_verification_email, user.email, token)

    await db.commit()
    return RedirectResponse(url="/auth/login-page", status_code=303)


@app.get("/auth/verify")
async def verify_email_web(token: str, db: AsyncSession = Depends(get_async_session)):
    from jose import jwt, JWTError
    import uuid
    from sqlalchemy import select

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return RedirectResponse(url="/auth/login-page?error=invalid_token", status_code=303)
    except JWTError:
        return RedirectResponse(url="/auth/login-page?error=invalid_token", status_code=303)

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        return RedirectResponse(url="/auth/login-page?error=user_not_found", status_code=303)
    user.is_verified = True
    await db.commit()
    return RedirectResponse(url="/auth/login-page?verified=1", status_code=303)


# ---------- Профиль и смена пароля ----------
@app.get("/profile")
async def profile_page(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": current_user,
    })


@app.post("/profile/change-password")
async def change_password(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    if not verify_password(old_password, current_user.hashed_password):
        return templates.TemplateResponse("profile.html", {
            "request": request,
            "user": current_user,
            "error": "Неверный старый пароль",
        })
    current_user.hashed_password = hash_password(new_password)
    await db.commit()
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": current_user,
        "message": "Пароль успешно изменён",
    })

@app.post("/profile/change-nickname")
async def change_nickname(
    request: Request,
    nickname: str = Form(""),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    current_user.nickname = nickname.strip() or None
    await db.commit()
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": current_user,
        "message": "Никнейм обновлён",
    })