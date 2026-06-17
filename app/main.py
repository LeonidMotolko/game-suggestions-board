from contextlib import asynccontextmanager
from typing import Optional
from urllib import request

from fastapi import FastAPI, Request, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import BackgroundTasks
from app.services.email_service import send_verification_email
from pydantic import EmailStr

from app.config import settings
from app.database import engine, async_session_maker, Base
from app.api import api_router
from app.services.user_service import authenticate_user, create_user, get_user_by_email, create_admin
from app.dependencies import get_async_session, get_optional_user
from app.models import *  # noqa: ensure all models are loaded

templates = Jinja2Templates(directory="app/templates")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создание таблиц при старте (для разработки; в production используйте Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Создание дефолтного админа
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

# Frontend routes for Jinja2 pages
@app.get("/")
async def root(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(get_optional_user)  # автоматически подставится
):
    from app.services.suggestion_service import get_suggestions
    suggestions = await get_suggestions(db)
    return templates.TemplateResponse("index.html", {"request": request, "user": user, "suggestions": suggestions})

@app.get("/auth/register-page")
async def register_page(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})

@app.get("/auth/login-page")
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@app.get("/auth/logout")
async def logout():
    # In a cookie-based JWT scenario we would clear cookie; here we just redirect
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")  # if we were using cookies
    return response

# Override login/logout to use forms for Jinja2
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
    # Установка JWT в cookie (httpOnly) для веб-интерфейса
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return response

@app.post("/auth/register")
async def register_form(
    background_tasks: BackgroundTasks,
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
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

    if settings.EMAIL_VERIFICATION_REQUIRED:
        from app.api.auth import create_access_token
        token = create_access_token({"sub": str(user.id), "verify": True})
        background_tasks.add_task(send_verification_email, user.email, token)

    await db.commit()
    return RedirectResponse(url="/auth/login-page", status_code=303)

@app.get("/auth/verify")
async def verify_email_web(token: str, db: AsyncSession = Depends(get_async_session)):
    from jose import jwt, JWTError
    from app.models.user import User
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