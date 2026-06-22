import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import bcrypt
from app.models.user import User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


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
        hashed_password=hash_password(password),
        is_active=is_active,
        is_verified=is_verified,
        role=role,
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def create_admin(db: AsyncSession, email: str, password: str):
    existing = await get_user_by_email(db, email)
    if existing:
        return existing
    admin = User(
        email=email,
        hashed_password=hash_password(password),
        is_active=True,
        is_verified=True,
        is_superuser=True,
        role="admin",
    )
    db.add(admin)
    await db.flush()
    return admin