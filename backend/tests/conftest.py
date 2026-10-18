import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import User, UserRole, Team, TeamMembership, WorkItem, WorkItemStatus, WorkItemPriority, WorkItemType
from app.auth import get_password_hash, create_access_token

# Test database: SQLite in-memory with StaticPool to share connection across threads
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create fresh tables for each test function."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Test client with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session) -> User:
    user = User(
        email="test_admin@newtonite.io",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Test Administrator",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def manager_user(db_session) -> User:
    user = User(
        email="test_manager@newtonite.io",
        hashed_password=get_password_hash("ManagerPass123!"),
        full_name="Test Manager",
        role=UserRole.MANAGER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def member_user(db_session) -> User:
    user = User(
        email="test_member@newtonite.io",
        hashed_password=get_password_hash("MemberPass123!"),
        full_name="Test Member",
        role=UserRole.MEMBER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def outsider_user(db_session) -> User:
    user = User(
        email="test_outsider@newtonite.io",
        hashed_password=get_password_hash("OutsiderPass123!"),
        full_name="Test Outsider",
        role=UserRole.MEMBER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user: User) -> str:
    return create_access_token({"sub": str(admin_user.id), "email": admin_user.email, "role": admin_user.role.value})


@pytest.fixture
def manager_token(manager_user: User) -> str:
    return create_access_token({"sub": str(manager_user.id), "email": manager_user.email, "role": manager_user.role.value})


@pytest.fixture
def member_token(member_user: User) -> str:
    return create_access_token({"sub": str(member_user.id), "email": member_user.email, "role": member_user.role.value})


@pytest.fixture
def outsider_token(outsider_user: User) -> str:
    return create_access_token({"sub": str(outsider_user.id), "email": outsider_user.email, "role": outsider_user.role.value})


@pytest.fixture
def test_team(db_session, manager_user, member_user) -> Team:
    team = Team(name="Engineering Team Alpha", description="Alpha Team for tests")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    # Add manager and member to team
    m1 = TeamMembership(team_id=team.id, user_id=manager_user.id, team_role="LEAD")
    m2 = TeamMembership(team_id=team.id, user_id=member_user.id, team_role="MEMBER")
    db_session.add_all([m1, m2])
    db_session.commit()
    return team
