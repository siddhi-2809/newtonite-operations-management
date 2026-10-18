from typing import Optional
from sqlalchemy.orm import Session
from app.models import ActivityLog, utcnow


def log_activity(
    db: Session,
    work_item_id: int,
    actor_id: int,
    action: str,
    field_name: Optional[str] = None,
    previous_value: Optional[str] = None,
    new_value: Optional[str] = None,
) -> ActivityLog:
    """
    Record an activity log entry in the current database transaction.
    Consistent with the parent transaction: if the parent transaction rolls back,
    this record is rolled back automatically.
    """
    log_entry = ActivityLog(
        work_item_id=work_item_id,
        actor_id=actor_id,
        action=action,
        field_name=field_name,
        previous_value=str(previous_value) if previous_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
        timestamp=utcnow(),
    )
    db.add(log_entry)
    return log_entry
