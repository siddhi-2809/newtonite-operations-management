from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.database import get_db
from app.models import (
    WorkItem,
    WorkItemStatus,
    WorkItemPriority,
    User,
    UserRole,
    TeamMembership,
    ActivityLog,
)
from app.schemas import DashboardStats, ActivityLogOut
from app.auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Compute operational dashboard metrics scoped to user's permissions:
    - Total work items
    - Open and in-progress items
    - Critical-priority items
    - Items assigned to the logged-in user
    - Items awaiting action / blocked
    - Status & priority distributions
    - Recent activity audit feed
    """
    base_query = db.query(WorkItem)

    # If not Admin, filter to user's teams + assigned/reported
    if current_user.role != UserRole.ADMIN:
        user_team_ids = [
            m.team_id
            for m in db.query(TeamMembership.team_id).filter(TeamMembership.user_id == current_user.id).all()
        ]
        base_query = base_query.filter(
            (WorkItem.team_id.in_(user_team_ids))
            | (WorkItem.assignee_id == current_user.id)
            | (WorkItem.reporter_id == current_user.id)
        )

    total_work_items = base_query.count()

    open_and_in_progress = base_query.filter(
        WorkItem.status.in_([WorkItemStatus.OPEN, WorkItemStatus.IN_PROGRESS])
    ).count()

    critical_priority = base_query.filter(
        WorkItem.priority == WorkItemPriority.CRITICAL
    ).count()

    assigned_to_me = db.query(WorkItem).filter(
        WorkItem.assignee_id == current_user.id
    ).count()

    awaiting_action_blocked = base_query.filter(
        WorkItem.status == WorkItemStatus.BLOCKED
    ).count()

    # Status breakdown
    status_counts = {}
    for st in WorkItemStatus:
        status_counts[st.value] = base_query.filter(WorkItem.status == st).count()

    # Priority breakdown
    priority_counts = {}
    for pr in WorkItemPriority:
        priority_counts[pr.value] = base_query.filter(WorkItem.priority == pr).count()

    # Recent activities (scoped to visible items)
    activities_query = (
        db.query(ActivityLog)
        .options(joinedload(ActivityLog.actor))
        .join(WorkItem, ActivityLog.work_item_id == WorkItem.id)
    )
    if current_user.role != UserRole.ADMIN:
        user_team_ids = [
            m.team_id
            for m in db.query(TeamMembership.team_id).filter(TeamMembership.user_id == current_user.id).all()
        ]
        activities_query = activities_query.filter(
            (WorkItem.team_id.in_(user_team_ids))
            | (WorkItem.assignee_id == current_user.id)
            | (WorkItem.reporter_id == current_user.id)
        )

    recent_activities = (
        activities_query.order_by(ActivityLog.timestamp.desc())
        .limit(10)
        .all()
    )

    return DashboardStats(
        total_work_items=total_work_items,
        open_and_in_progress=open_and_in_progress,
        critical_priority=critical_priority,
        assigned_to_me=assigned_to_me,
        awaiting_action_blocked=awaiting_action_blocked,
        by_status=status_counts,
        by_priority=priority_counts,
        recent_activities=recent_activities,
    )
