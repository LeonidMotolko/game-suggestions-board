import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.database import Base, get_async_session
from app.main import app
from app.config import settings
from app.services.user_service import create_admin
import asyncio

settings.EMAIL_VERIFICATION_REQUIRED = False
settings.UPLOAD_DIR = "tests/test_uploads"

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

import app.database as db_module
db_module.engine = engine
db_module.async_session_maker = TestSessionLocal

async def override_get_db():
    async with TestSessionLocal() as session:
        yield session

app.dependency_overrides[get_async_session] = override_get_db

from fastapi import FastAPI
app.router.lifespan_context = None

@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        await create_admin(session, "admin@test.com", "admin123")
        await session.commit()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(autouse=True)
async def setup_db(db):
    pass

@pytest_asyncio.fixture
async def client(db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture
async def user_token(client):
    await client.post("/auth/register", data={"email": "user@test.com", "password": "testpass"})
    response = await client.post("/auth/login", data={"email": "user@test.com", "password": "testpass"})
    token = response.cookies.get("access_token")
    # убираем возможные кавычки
    return token.strip('"') if token else token

@pytest_asyncio.fixture
async def admin_token(client):
    response = await client.post("/auth/login", data={"email": "admin@test.com", "password": "admin123"})
    token = response.cookies.get("access_token")
    return token.strip('"') if token else token