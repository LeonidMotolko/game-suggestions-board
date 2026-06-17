import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, email: str, password: str, is_active: bool = True, is_verified: bool = False,
                      role: str = "user") -> User:
    user = User(
        email=email,
        hashed_password=pwd_context.hash(password),
        is_active=is_active,
        is_verified=is_verified,
        role=role,
    )
    db.add(user)
    await db.flush()
    return user

async def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not await verify_password(password, user.hashed_password):
        return None
    return user

async def create_admin(db: AsyncSession, email: str, password: str):
    existing = await get_user_by_email(db, email)
    if existing:
        return existing
    admin = User(
        email=email,
        hashed_password=pwd_context.hash(password),
        is_active=True,
        is_verified=True,
        is_superuser=True,
        role="admin",
    )
    db.add(admin)
    await db.flush()
    return admin
