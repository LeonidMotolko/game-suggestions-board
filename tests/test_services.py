import pytest
from app.services.user_service import hash_password, verify_password, create_user, authenticate_user
from app.services.suggestion_service import create_suggestion, get_suggestions, get_suggestion, vote_suggestion
from app.database import async_session_maker

class TestUserService:
    async def test_hash_and_verify(self):
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed)
        assert not verify_password("wrong", hashed)

    async def test_create_and_auth(self):
        async with async_session_maker() as db:
            user = await create_user(db, "serv@test.com", "pass")
            await db.commit()
            auth_user = await authenticate_user(db, "serv@test.com", "pass")
            assert auth_user is not None
            assert auth_user.email == "serv@test.com"