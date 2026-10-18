import math
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, update
from app.database import get_db
from app.models import (
    WorkItem,
    WorkItemStatus,
    WorkItemPriority,
    WorkItemType,
    User,
    UserRole,
    TeamMembership,
    Comment,
    ActivityLog,
    utcnow,
)
from app.schemas import (
    WorkItemCreate,
    WorkItemUpdate,
    WorkItemStatusUpdate,
    WorkItemAssignUpdate,
    WorkItemClaimRequest,
    WorkItemOut,
    WorkItemListResponse,
    CommentCreate,
    CommentOut,
    ActivityLogOut,
)
from app.auth import get_current_user
from app.services.activity_service import log_activity
from app.services.idempotency_service import get_idempotent_response, save_idempotent_response

router = APIRouter(prefix="/api/work-items", tags=["Work Items"])

# Allowed workflow status transitions
VALID_TRANSITIONS = {
    WorkItemStatus.OPEN: {WorkItemStatus.IN_PROGRESS, WorkItemStatus.BLOCKED},
    WorkItemStatus.IN_PROGRESS: {WorkItemStatus.BLOCKED, WorkItemStatus.RESOLVED, WorkItemStatus.OPEN},
    WorkItemStatus.BLOCKED: {WorkItemStatus.OPEN, WorkItemStatus.IN_PROGRESS},
    WorkItemStatus.RESOLVED: {WorkItemStatus.OPEN, WorkItemStatus.IN_PROGRESS},
}


def user_can_access_team(db: Session, user: User, team_id: int) -> bool:
    """Check if user has access to work items of a team."""
    if user.role == UserRole.ADMIN:
        return True
    membership = (
        db.query(TeamMembership)
        .filter(TeamMembership.team_id == team_id, TeamMembership.user_id == user.id)
        .first()
    )
    return membership is not None


def user_can_manage_team_items(db: Session, user: User, team_id: int) -> bool:
    """Check if user has manager/admin permissions for a team."""
    if user.role == UserRole.ADMIN:
        return True
    if user.role == UserRole.MANAGER:
        return user_can_access_team(db, user, team_id)
    return False


@router.get("", response_model=WorkItemListResponse)
def list_work_items(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for title or description"),
    status: Optional[WorkItemStatus] = Query(None, description="Filter by status"),
    priority: Optional[WorkItemPriority] = Query(None, description="Filter by priority"),
    team_id: Optional[int] = Query(None, description="Filter by team"),
    assignee_id: Optional[int] = Query(None, description="Filter by assignee"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List work items with server-side pagination, search, and filtering.
    Members only see work items in teams they belong to (or assigned to them),
    while Admins see all items.
    """
    query = (
        db.query(WorkItem)
        .options(
            joinedload(WorkItem.team),
            joinedload(WorkItem.assignee),
            joinedload(WorkItem.reporter),
        )
    )

    # Authorization filter: members/managers only see items from their teams unless Admin
    if current_user.role != UserRole.ADMIN:
        user_team_ids = [
            m.team_id
            for m in db.query(TeamMembership.team_id).filter(TeamMembership.user_id == current_user.id).all()
        ]
        # Can see if in user's teams or explicitly assigned/reported by user
        query = query.filter(
            or_(
                WorkItem.team_id.in_(user_team_ids),
                WorkItem.assignee_id == current_user.id,
                WorkItem.reporter_id == current_user.id,
            )
        )

    # Applied filters
    if status is not None:
        query = query.filter(WorkItem.status == status)
    if priority is not None:
        query = query.filter(WorkItem.priority == priority)
    if team_id is not None:
        query = query.filter(WorkItem.team_id == team_id)
    if assignee_id is not None:
        query = query.filter(WorkItem.assignee_id == assignee_id)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                WorkItem.title.ilike(search_filter),
                WorkItem.description.ilike(search_filter),
            )
        )

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(WorkItem.updated_at.desc()).offset(offset).limit(page_size).all()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return WorkItemListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=WorkItemOut, status_code=status.HTTP_201_CREATED)
def create_work_item(
    item_in: WorkItemCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new work item.
    Enforces team membership authorization.
    Supports Idempotency-Key to prevent duplicate work item creation.
    """
    # Check idempotency
    cached = get_idempotent_response(db, idempotency_key, current_user.id)
    if cached:
        cached_status, cached_body = cached
        return cached_body

    # Check permission: Admins can create in any team, Managers/Members in their assigned teams
    if not user_can_access_team(db, current_user, item_in.team_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot create work items for a team you do not belong to.",
        )

    # If assignee specified, ensure assignee exists
    if item_in.assignee_id:
        assignee = db.query(User).filter(User.id == item_in.assignee_id).first()
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignee user ID {item_in.assignee_id} not found.",
            )

    new_item = WorkItem(
        title=item_in.title,
        description=item_in.description,
        item_type=item_in.item_type,
        priority=item_in.priority,
        status=item_in.status,
        team_id=item_in.team_id,
        assignee_id=item_in.assignee_id,
        reporter_id=current_user.id,
        due_date=item_in.due_date,
        version=1,
    )
    db.add(new_item)
    db.flush()  # get new_item.id

    # Log activity within transaction
    log_activity(
        db=db,
        work_item_id=new_item.id,
        actor_id=current_user.id,
        action="CREATED",
        new_value=f"Title: {new_item.title}, Priority: {new_item.priority.value}, Status: {new_item.status.value}",
    )

    db.commit()
    db.refresh(new_item)

    # Load relationships for response schema
    item_out = (
        db.query(WorkItem)
        .options(
            joinedload(WorkItem.team),
            joinedload(WorkItem.assignee),
            joinedload(WorkItem.reporter),
        )
        .filter(WorkItem.id == new_item.id)
        .first()
    )

    # Save idempotency record if key provided
    if idempotency_key:
        save_idempotent_response(
            db=db,
            idempotency_key=idempotency_key,
            user_id=current_user.id,
            request_path="/api/work-items",
            status_code=status.HTTP_201_CREATED,
            response_data=WorkItemOut.model_validate(item_out).model_dump(mode="json"),
        )
        db.commit()

    return item_out


@router.get("/{work_item_id}", response_model=WorkItemOut)
def get_work_item(
    work_item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full work item information including comments and activity history."""
    item = (
        db.query(WorkItem)
        .options(
            joinedload(WorkItem.team),
            joinedload(WorkItem.assignee),
            joinedload(WorkItem.reporter),
            joinedload(WorkItem.comments).joinedload(Comment.author),
            joinedload(WorkItem.activity_logs).joinedload(ActivityLog.actor),
        )
        .filter(WorkItem.id == work_item_id)
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work item not found.",
        )

    # Authorization check
    if not user_can_access_team(db, current_user, item.team_id) and current_user.id not in (item.assignee_id, item.reporter_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to view this work item.",
        )

    return item


@router.put("/{work_item_id}", response_model=WorkItemOut)
def update_work_item(
    work_item_id: int,
    update_in: WorkItemUpdate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update work item fields with Stale-Update Protection (Optimistic Concurrency Control).
    Rejects with HTTP 409 Conflict if supplied version != current database version.
    """
    cached = get_idempotent_response(db, idempotency_key, current_user.id)
    if cached:
        cached_status, cached_body = cached
        return cached_body

    item = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work item not found.",
        )

    # Authorization check: Admin or Manager of team, or assignee updating their task
    if not user_can_manage_team_items(db, current_user, item.team_id):
        if current_user.id != item.assignee_id and current_user.id != item.reporter_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to update this work item.",
            )

    # Concurrency control B: Stale updates rejection
    if item.version != update_in.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conflict: Work item has been modified by another user (server version: {item.version}, your version: {update_in.version}). Please refresh and try again.",
        )

    # Track changes for activity log
    changes = []
    if update_in.title is not None and update_in.title != item.title:
        changes.append(("title", item.title, update_in.title))
        item.title = update_in.title

    if update_in.description is not None and update_in.description != item.description:
        changes.append(("description", item.description, update_in.description))
        item.description = update_in.description

    if update_in.item_type is not None and update_in.item_type != item.item_type:
        changes.append(("item_type", item.item_type.value, update_in.item_type.value))
        item.item_type = update_in.item_type

    if update_in.priority is not None and update_in.priority != item.priority:
        changes.append(("priority", item.priority.value, update_in.priority.value))
        item.priority = update_in.priority

    if update_in.status is not None and update_in.status != item.status:
        # Validate status transition
        allowed = VALID_TRANSITIONS.get(item.status, set())
        if update_in.status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from {item.status.value} to {update_in.status.value}. Allowed transitions: {[s.value for s in allowed]}",
            )
        changes.append(("status", item.status.value, update_in.status.value))
        item.status = update_in.status

    if update_in.team_id is not None and update_in.team_id != item.team_id:
        if not user_can_manage_team_items(db, current_user, update_in.team_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Cannot move work item to a team you cannot manage.",
            )
        changes.append(("team_id", str(item.team_id), str(update_in.team_id)))
        item.team_id = update_in.team_id

    if update_in.assignee_id != item.assignee_id and update_in.assignee_id is not None:
        changes.append(("assignee_id", str(item.assignee_id), str(update_in.assignee_id)))
        item.assignee_id = update_in.assignee_id

    if update_in.due_date != item.due_date:
        changes.append(("due_date", str(item.due_date), str(update_in.due_date)))
        item.due_date = update_in.due_date

    # Increment version for OCC
    item.version += 1
    item.updated_at = utcnow()

    # Log activity for each change in the transaction
    for field_name, prev_val, new_val in changes:
        log_activity(
            db=db,
            work_item_id=item.id,
            actor_id=current_user.id,
            action=f"UPDATED_{field_name.upper()}",
            field_name=field_name,
            previous_value=prev_val,
            new_value=new_val,
        )

    db.commit()
    db.refresh(item)

    # Return refreshed object with relations
    item_out = (
        db.query(WorkItem)
        .options(
            joinedload(WorkItem.team),
            joinedload(WorkItem.assignee),
            joinedload(WorkItem.reporter),
            joinedload(WorkItem.comments).joinedload(Comment.author),
            joinedload(WorkItem.activity_logs).joinedload(ActivityLog.actor),
        )
        .filter(WorkItem.id == item.id)
        .first()
    )

    if idempotency_key:
        save_idempotent_response(
            db=db,
            idempotency_key=idempotency_key,
            user_id=current_user.id,
            request_path=f"/api/work-items/{work_item_id}",
            status_code=status.HTTP_200_OK,
            response_data=WorkItemOut.model_validate(item_out).model_dump(mode="json"),
        )
        db.commit()

    return item_out


@router.post("/{work_item_id}/claim", response_model=WorkItemOut)
def claim_work_item(
    work_item_id: int,
    claim_in: WorkItemClaimRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reliability Behaviour A: Concurrent Assignment Protection.
    Atomically claim an unassigned work item.
    Uses atomic conditional database update:
      UPDATE work_items
      SET assignee_id = :user_id, version = version + 1, updated_at = :now
      WHERE id = :id AND assignee_id IS NULL AND version = :version
    If another user has claimed the item or updated it in the meantime, returns HTTP 409 Conflict.
    """
    cached = get_idempotent_response(db, idempotency_key, current_user.id)
    if cached:
        cached_status, cached_body = cached
        return cached_body

    # Check work item existence and team permission
    item = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work item not found.",
        )

    if not user_can_access_team(db, current_user, item.team_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot claim work items outside your teams.",
        )

    # Atomic conditional update
    now = utcnow()
    stmt = (
        update(WorkItem)
        .where(
            and_(
                WorkItem.id == work_item_id,
                WorkItem.assignee_id.is_(None),
                WorkItem.version == claim_in.version,
            )
        )
        .values(
            assignee_id=current_user.id,
            version=WorkItem.version + 1,
            updated_at=now,
        )
    )
    result = db.execute(stmt)

    if result.rowcount == 0:
        # Check why update failed
        db.expire_all()
        refreshed = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
        if refreshed and refreshed.assignee_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflict: Work item #{work_item_id} has already been claimed or assigned to another user.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflict: Work item #{work_item_id} version mismatch (expected {claim_in.version}, server has {refreshed.version if refreshed else 'unknown'}).",
            )

    # Log successful activity in the same transaction
    log_activity(
        db=db,
        work_item_id=work_item_id,
        actor_id=current_user.id,
        action="ASSIGNED",
        field_name="assignee_id",
        previous_value="Unassigned",
        new_value=f"{current_user.full_name} ({current_user.email})",
    )
    db.commit()

    updated_item = (
        db.query(WorkItem)
        .options(
            joinedload(WorkItem.team),
            joinedload(WorkItem.assignee),
            joinedload(WorkItem.reporter),
            joinedload(WorkItem.comments).joinedload(Comment.author),
            joinedload(WorkItem.activity_logs).joinedload(ActivityLog.actor),
        )
        .filter(WorkItem.id == work_item_id)
        .first()
    )

    if idempotency_key:
        save_idempotent_response(
            db=db,
            idempotency_key=idempotency_key,
            user_id=current_user.id,
            request_path=f"/api/work-items/{work_item_id}/claim",
            status_code=status.HTTP_200_OK,
            response_data=WorkItemOut.model_validate(updated_item).model_dump(mode="json"),
        )
        db.commit()

    return updated_item


@router.patch("/{work_item_id}/assign", response_model=WorkItemOut)
def assign_work_item(
    work_item_id: int,
    assign_in: WorkItemAssignUpdate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Assign or reassign a work item.
    Enforces manager/admin permission and stale-update version checking.
    """
    cached = get_idempotent_response(db, idempotency_key, current_user.id)
    if cached:
        cached_status, cached_body = cached
        return cached_body

    item = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work item not found.",
        )

    # Authorization: Only Admins or Managers of this team can assign tasks
    if not user_can_manage_team_items(db, current_user, item.team_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only Managers or Admins can assign or reassign work items.",
        )

    # Concurrency control: Stale update check
    if item.version != assign_in.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conflict: Work item was updated by another user (server version: {item.version}, your version: {assign_in.version}).",
        )

    # Validate target assignee if provided
    new_assignee_name = "Unassigned"
    if assign_in.assignee_id is not None:
        target_user = db.query(User).filter(User.id == assign_in.assignee_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignee user ID {assign_in.assignee_id} not found.",
            )
        new_assignee_name = f"{target_user.full_name} ({target_user.email})"

    old_assignee_name = f"{item.assignee.full_name}" if item.assignee else "Unassigned"

    item.assignee_id = assign_in.assignee_id
    item.version += 1
    item.updated_at = utcnow()

    log_activity(
        db=db,
        work_item_id=item.id,
        actor_id=current_user.id,
        action="ASSIGNED",
        field_name="assignee_id",
        previous_value=old_assignee_name,
        new_value=new_assignee_name,
    )
    db.commit()

    updated_item = (
        db.query(WorkItem)
        .options(
            joinedload(WorkItem.team),
            joinedload(WorkItem.assignee),
            joinedload(WorkItem.reporter),
            joinedload(WorkItem.comments).joinedload(Comment.author),
            joinedload(WorkItem.activity_logs).joinedload(ActivityLog.actor),
        )
        .filter(WorkItem.id == work_item_id)
        .first()
    )

    if idempotency_key:
        save_idempotent_response(
            db=db,
            idempotency_key=idempotency_key,
            user_id=current_user.id,
            request_path=f"/api/work-items/{work_item_id}/assign",
            status_code=status.HTTP_200_OK,
            response_data=WorkItemOut.model_validate(updated_item).model_dump(mode="json"),
        )
        db.commit()

    return updated_item


@router.patch("/{work_item_id}/status", response_model=WorkItemOut)
def update_work_item_status(
    work_item_id: int,
    status_in: WorkItemStatusUpdate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update work item status.
    Validates state machine transitions on the server.
    Enforces optimistic concurrency control (version matching).
    Records audit history in the same transaction.
    """
    cached = get_idempotent_response(db, idempotency_key, current_user.id)
    if cached:
        cached_status, cached_body = cached
        return cached_body

    item = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work item not found.",
        )

    # Authorization: Admin, Manager of team, or Assignee of this item
    can_change = (
        current_user.role == UserRole.ADMIN
        or user_can_manage_team_items(db, current_user, item.team_id)
        or item.assignee_id == current_user.id
    )
    if not can_change:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to change the status of this work item.",
        )

    # Concurrency control: Stale update check
    if item.version != status_in.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conflict: Work item was updated by another user (server version: {item.version}, your version: {status_in.version}).",
        )

    # Validate state transition
    if status_in.status == item.status:
        # No-op if same status
        return item

    allowed = VALID_TRANSITIONS.get(item.status, set())
    if status_in.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from {item.status.value} to {status_in.status.value}. Allowed transitions: {[s.value for s in allowed]}",
        )

    old_status = item.status.value
    new_status = status_in.status.value

    item.status = status_in.status
    item.version += 1
    item.updated_at = utcnow()

    # Log activity in same transaction
    log_activity(
        db=db,
        work_item_id=item.id,
        actor_id=current_user.id,
        action="STATUS_CHANGE",
        field_name="status",
        previous_value=old_status,
        new_value=new_status,
    )
    db.commit()

    updated_item = (
        db.query(WorkItem)
        .options(
            joinedload(WorkItem.team),
            joinedload(WorkItem.assignee),
            joinedload(WorkItem.reporter),
            joinedload(WorkItem.comments).joinedload(Comment.author),
            joinedload(WorkItem.activity_logs).joinedload(ActivityLog.actor),
        )
        .filter(WorkItem.id == work_item_id)
        .first()
    )

    if idempotency_key:
        save_idempotent_response(
            db=db,
            idempotency_key=idempotency_key,
            user_id=current_user.id,
            request_path=f"/api/work-items/{work_item_id}/status",
            status_code=status.HTTP_200_OK,
            response_data=WorkItemOut.model_validate(updated_item).model_dump(mode="json"),
        )
        db.commit()

    return updated_item


@router.post("/{work_item_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(
    work_item_id: int,
    comment_in: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a comment to a work item and record in activity log."""
    item = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work item not found.",
        )

    # Permission check: must have team access or be assignee/reporter
    if not user_can_access_team(db, current_user, item.team_id) and current_user.id not in (item.assignee_id, item.reporter_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to comment on this work item.",
        )

    comment = Comment(
        work_item_id=work_item_id,
        author_id=current_user.id,
        content=comment_in.content,
    )
    db.add(comment)
    db.flush()

    # Log in activity audit trail
    preview = comment_in.content[:50] + ("..." if len(comment_in.content) > 50 else "")
    log_activity(
        db=db,
        work_item_id=work_item_id,
        actor_id=current_user.id,
        action="COMMENT_ADDED",
        new_value=preview,
    )
    db.commit()
    db.refresh(comment)

    return comment


@router.get("/{work_item_id}/activity", response_model=List[ActivityLogOut])
def get_work_item_activity(
    work_item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get chronological activity history / audit log for a work item."""
    item = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work item not found.",
        )
    if not user_can_access_team(db, current_user, item.team_id) and current_user.id not in (item.assignee_id, item.reporter_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to view activity on this work item.",
        )

    activities = (
        db.query(ActivityLog)
        .options(joinedload(ActivityLog.actor))
        .filter(ActivityLog.work_item_id == work_item_id)
        .order_by(ActivityLog.timestamp.desc())
        .all()
    )
    return activities


@router.delete("/{work_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_work_item(
    work_item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a work item (Admin or Team Manager only)."""
    item = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work item not found.",
        )
    if not user_can_manage_team_items(db, current_user, item.team_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only Managers or Admins can delete work items.",
        )

    db.delete(item)
    db.commit()
    return None
