from typing import Optional
import uuid
from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_async_session
from app.models.user import User
from app.services.user_service import get_user_by_id


class OAuth2CookieOrHeader:
    """Извлекает JWT из cookie 'access_token' или заголовка 'Authorization'."""

    def __init__(self, *, auto_error: bool = True):
        self.auto_error = auto_error

    async def __call__(self, request: Request) -> Optional[str]:
        # Сначала пробуем cookie
        token_cookie = request.cookies.get("access_token")
        if token_cookie:
            # Удаляем префикс "Bearer ", если есть
            if token_cookie.startswith("Bearer "):
                token_cookie = token_cookie[7:]
            return token_cookie

        # Затем пробуем заголовок Authorization
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            return authorization[7:]

        if self.auto_error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None


oauth2_scheme = OAuth2CookieOrHeader(auto_error=False)


async def get_current_user(
        token: Optional[str] = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_async_session),
) -> Optional[User]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    user = await get_user_by_id(db, uuid.UUID(user_id))
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_active_user)):
        if current_user.role not in self.allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user


require_admin = RoleChecker(["admin"])


async def get_optional_user(current_user: Optional[User] = Depends(get_current_user)):
    """Возвращает пользователя или None для неавторизованных."""
    return current_user