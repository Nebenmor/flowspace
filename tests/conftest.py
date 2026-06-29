import pytest
import pytest_asyncio
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from app.main import app as fastapi_app
from app.core.dependencies import get_db
from app.core.security import hash_password, create_access_token
from app.db.session import Base
from app.db.models.user import User
from app.db.models.organization import Organization, OrganizationMember
from app.db.models.workspace import Workspace, WorkspaceMember
import app.db.models

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres123@localhost:5432/collab_tasks_test"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestSessionLocal = sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


fastapi_app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
async def truncate_tables(setup_database):
    yield
    async with test_engine.begin() as conn:
        await conn.execute(text(
            "TRUNCATE TABLE "
            "users, organizations, organization_members, workspaces, "
            "workspace_members, tasks, task_dependencies, labels, task_labels, "
            "custom_fields, task_custom_field_values, invitations, "
            "notifications, webhooks, webhook_deliveries, refresh_tokens "
            "RESTART IDENTITY CASCADE"
        ))


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    user = User(
        email="test@hiveapi.dev",
        username="testuser",
        full_name="Test User",
        hashed_password=hash_password("securepassword123"),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def second_user(db: AsyncSession) -> User:
    user = User(
        email="second@hiveapi.dev",
        username="seconduser",
        full_name="Second User",
        hashed_password=hash_password("securepassword123"),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    token = create_access_token(subject=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def second_auth_headers(second_user: User) -> dict:
    token = create_access_token(subject=str(second_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_org(db: AsyncSession, test_user: User) -> Organization:
    org = Organization(
        name="Hive Corp",
        slug="hive-corp",
        owner_id=test_user.id,
        is_active=True,
    )
    db.add(org)
    await db.flush()

    member = OrganizationMember(
        org_id=org.id,
        user_id=test_user.id,
        role="owner",
        joined_at=datetime.now(timezone.utc),  # required field
    )
    db.add(member)
    await db.commit()
    await db.refresh(org)
    return org


@pytest_asyncio.fixture
async def test_workspace(
    db: AsyncSession,
    test_org: Organization,
    test_user: User,
) -> Workspace:
    workspace = Workspace(
        org_id=test_org.id,
        name="Engineering",
        slug="engineering",
        created_by=test_user.id,
        is_archived=False,
    )
    db.add(workspace)
    await db.flush()

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role="admin",
        joined_at=datetime.now(timezone.utc),  # required field
    )
    db.add(member)
    await db.commit()
    await db.refresh(workspace)
    return workspace