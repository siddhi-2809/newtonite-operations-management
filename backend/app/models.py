import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    MEMBER = "MEMBER"


class WorkItemPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class WorkItemStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    RESOLVED = "RESOLVED"


class WorkItemType(str, enum.Enum):
    BUG = "BUG"
    FEATURE = "FEATURE"
    TASK = "TASK"
    INCIDENT = "INCIDENT"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.MEMBER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now(), nullable=False)

    memberships = relationship("TeamMembership", back_populates="user", cascade="all, delete-orphan")
    reported_items = relationship("WorkItem", foreign_keys="WorkItem.reporter_id", back_populates="reporter")
    assigned_items = relationship("WorkItem", foreign_keys="WorkItem.assignee_id", back_populates="assignee")
    comments = relationship("Comment", back_populates="author")
    activities = relationship("ActivityLog", back_populates="actor")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now(), nullable=False)

    memberships = relationship("TeamMembership", back_populates="team", cascade="all, delete-orphan")
    work_items = relationship("WorkItem", back_populates="team")


class TeamMembership(Base):
    __tablename__ = "team_memberships"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    team_role = Column(String(50), default="MEMBER", nullable=False)  # LEAD or MEMBER
    created_at = Column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_user"),
    )

    team = relationship("Team", back_populates="memberships")
    user = relationship("User", back_populates="memberships")


class WorkItem(Base):
    __tablename__ = "work_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    item_type = Column(Enum(WorkItemType), default=WorkItemType.TASK, nullable=False)
    priority = Column(Enum(WorkItemPriority), default=WorkItemPriority.LOW, nullable=False, index=True)
    status = Column(Enum(WorkItemStatus), default=WorkItemStatus.OPEN, nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False, index=True)
    assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, default=1, nullable=False)  # Optimistic concurrency control
    created_at = Column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_work_items_filter", "team_id", "status", "priority", "assignee_id"),
    )

    team = relationship("Team", back_populates="work_items")
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_items")
    reporter = relationship("User", foreign_keys=[reporter_id], back_populates="reported_items")
    comments = relationship("Comment", back_populates="work_item", cascade="all, delete-orphan", order_by="Comment.created_at.desc()")
    activity_logs = relationship("ActivityLog", back_populates="work_item", cascade="all, delete-orphan", order_by="ActivityLog.timestamp.desc()")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    work_item_id = Column(Integer, ForeignKey("work_items.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now(), nullable=False)

    work_item = relationship("WorkItem", back_populates="comments")
    author = relationship("User", back_populates="comments")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    work_item_id = Column(Integer, ForeignKey("work_items.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    action = Column(String(100), nullable=False)  # CREATED, UPDATED, STATUS_CHANGE, ASSIGNMENT, PRIORITY_CHANGE, COMMENT_ADDED
    field_name = Column(String(50), nullable=True)
    previous_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_activity_work_item_time", "work_item_id", "timestamp"),
    )

    work_item = relationship("WorkItem", back_populates="activity_logs")
    actor = relationship("User", back_populates="activities")


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    request_path = Column(String(255), nullable=False)
    request_hash = Column(String(64), nullable=True)
    status_code = Column(Integer, nullable=False)
    response_body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)
