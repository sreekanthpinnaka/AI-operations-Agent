from __future__ import annotations

from typing import Any
from sqlalchemy.orm import Session

from app.db.models import AuditEvent
from app.db.types import new_id


def audit(
    db: Session,
    request_id: str,
    node: str,
    event_type: str,
    message: str,
    tool_name: str | None = None,
    action: str | None = None,
    status: str | None = "INFO",
    safe_metadata: dict[str, Any] | None = None,
    actor_user_id: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        id=new_id(),
        request_id=request_id,
        actor_user_id=actor_user_id,
        node=node,
        event_type=event_type,
        tool_name=tool_name,
        action=action,
        status=status or "INFO",
        message=message[:1000],
        safe_metadata=safe_metadata or {},
    )
    db.add(event)
    return event
