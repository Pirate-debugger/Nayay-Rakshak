import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token, get_password_hash
from app.db.base import Base, get_db
from app.db.models import User
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db_session():
    """Create a fresh in-memory database schema for each test."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(test_db_session: AsyncSession):
    """Async test client with overridden DB dependency."""

    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(test_db_session: AsyncSession):
    """Seed test user 1."""
    user = User(
        email="citizen.test@example.com",
        hashed_password=get_password_hash("StrongPassword123!"),
        full_name="Ramesh Gupta",
        role="user",
    )
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def other_user(test_db_session: AsyncSession):
    """Seed test user 2 for authorization tests."""
    user = User(
        email="other.user@example.com",
        hashed_password=get_password_hash("OtherPassword123!"),
        full_name="Pooja Mehta",
        role="user",
    )
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User):
    token = create_access_token(
        {"sub": str(test_user.id), "email": test_user.email, "role": test_user.role}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(other_user: User):
    token = create_access_token(
        {"sub": str(other_user.id), "email": other_user.email, "role": other_user.role}
    )
    return {"Authorization": f"Bearer {token}"}
