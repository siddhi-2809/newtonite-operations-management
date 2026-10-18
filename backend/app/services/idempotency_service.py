import json
from typing import Optional, Tuple, Any
from sqlalchemy.orm import Session
from app.models import IdempotencyRecord, utcnow


def get_idempotent_response(
    db: Session,
    idempotency_key: Optional[str],
    user_id: int,
) -> Optional[Tuple[int, Any]]:
    """Check if an operation with this idempotency key has already completed."""
    if not idempotency_key:
        return None
    record = (
        db.query(IdempotencyRecord)
        .filter(
            IdempotencyRecord.idempotency_key == idempotency_key,
            IdempotencyRecord.user_id == user_id,
        )
        .first()
    )
    if record:
        try:
            body = json.loads(record.response_body)
        except Exception:
            body = record.response_body
        return record.status_code, body
    return None


def save_idempotent_response(
    db: Session,
    idempotency_key: Optional[str],
    user_id: int,
    request_path: str,
    status_code: int,
    response_data: Any,
) -> None:
    """Store the completed operation response associated with the idempotency key."""
    if not idempotency_key:
        return
    try:
        body_str = json.dumps(response_data, default=str)
    except Exception:
        body_str = str(response_data)

    record = IdempotencyRecord(
        idempotency_key=idempotency_key,
        user_id=user_id,
        request_path=request_path,
        status_code=status_code,
        response_body=body_str,
        created_at=utcnow(),
    )
    db.add(record)
