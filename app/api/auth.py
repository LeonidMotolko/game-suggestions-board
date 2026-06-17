from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt
from datetime import datetime, timedelta
import uuid

from app.database import get_async_session
from app.config import settings
from app.models.user import User
from app.services.user_service import authenticate_user, create_user, get_user_by_email
from app.services.email_service import send_verification_email

router = APIRouter(prefix="/api/auth", tags=["api_auth"])  # ← добавили /api

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

@router.post("/register")
async def register(
    request: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
):
    existing = await get_user_by_email(db, request.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = await create_user(
        db,
        email=request.email,
        password=request.password,
        is_verified=not settings.EMAIL_VERIFICATION_REQUIRED,
        is_active=True,
    )

    if settings.EMAIL_VERIFICATION_REQUIRED:
        token = create_access_token({"sub": str(user.id), "verify": True})
        background_tasks.add_task(send_verification_email, user.email, token)
    await db.commit()
    return {"message": "User registered successfully. Please check your email for verification."}

@router.post("/login")
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_async_session),
):
    user = await authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    if settings.EMAIL_VERIFICATION_REQUIRED and not user.is_verified:
        raise HTTPException(status_code=400, detail="Email not verified")

    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/verify")
async def verify_email(token: str, db: AsyncSession = Depends(get_async_session)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = await get_user_by_email(db, uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_verified = True
    await db.commit()
    return {"message": "Email verified successfully. You can now log in."}


@router.post("/resend-verification")
async def resend_verification(
        email: EmailStr,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_async_session),
):
    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    token = create_access_token({"sub": str(user.id), "verify": True})
    background_tasks.add_task(send_verification_email, user.email, token)
    return {"message": "Verification email sent again"}