from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models import UserRole, WorkItemPriority, WorkItemStatus, WorkItemType


# ---------------- User Schemas ----------------

class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128)
    role: Optional[UserRole] = UserRole.MEMBER


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserOut(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------- Auth Schemas ----------------

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------------- Team Schemas ----------------

class TeamBase(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None


class TeamMembershipCreate(BaseModel):
    user_id: int
    team_role: str = "MEMBER"


class TeamMembershipOut(BaseModel):
    id: int
    team_id: int
    user_id: int
    team_role: str
    created_at: datetime
    user: Optional[UserOut] = None

    model_config = ConfigDict(from_attributes=True)


class TeamOut(TeamBase):
    id: int
    created_at: datetime
    updated_at: datetime
    memberships: List[TeamMembershipOut] = []

    model_config = ConfigDict(from_attributes=True)


# ---------------- Comment Schemas ----------------

class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)


class CommentOut(BaseModel):
    id: int
    work_item_id: int
    author_id: int
    content: str
    created_at: datetime
    updated_at: datetime
    author: Optional[UserOut] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------- Activity Log Schemas ----------------

class ActivityLogOut(BaseModel):
    id: int
    work_item_id: int
    actor_id: int
    action: str
    field_name: Optional[str] = None
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    timestamp: datetime
    actor: Optional[UserOut] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------- Work Item Schemas ----------------

class WorkItemBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    item_type: WorkItemType = WorkItemType.TASK
    priority: WorkItemPriority = WorkItemPriority.LOW
    status: WorkItemStatus = WorkItemStatus.OPEN
    team_id: int
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None


class WorkItemCreate(WorkItemBase):
    pass


class WorkItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    item_type: Optional[WorkItemType] = None
    priority: Optional[WorkItemPriority] = None
    status: Optional[WorkItemStatus] = None
    team_id: Optional[int] = None
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None
    version: int = Field(..., description="Version of the item being updated for optimistic concurrency control")


class WorkItemStatusUpdate(BaseModel):
    status: WorkItemStatus
    version: int = Field(..., description="Current version of the item")


class WorkItemAssignUpdate(BaseModel):
    assignee_id: Optional[int] = None
    version: int = Field(..., description="Current version of the item")


class WorkItemClaimRequest(BaseModel):
    version: int = Field(..., description="Current version of the item")


class WorkItemOut(WorkItemBase):
    id: int
    reporter_id: int
    version: int
    created_at: datetime
    updated_at: datetime
    team: Optional[TeamBase] = None
    assignee: Optional[UserOut] = None
    reporter: Optional[UserOut] = None
    comments: List[CommentOut] = []
    activity_logs: List[ActivityLogOut] = []

    model_config = ConfigDict(from_attributes=True)


class WorkItemListResponse(BaseModel):
    items: List[WorkItemOut]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------------- Dashboard Schemas ----------------

class DashboardStats(BaseModel):
    total_work_items: int
    open_and_in_progress: int
    critical_priority: int
    assigned_to_me: int
    awaiting_action_blocked: int
    by_status: Dict[str, int]
    by_priority: Dict[str, int]
    recent_activities: List[ActivityLogOut]
