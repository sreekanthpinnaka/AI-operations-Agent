from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.tracing import set_trace_operation_id
from app.db.session import get_db
from app.models.schemas import ApprovalRequest, AuditEventView, InstructionRequest, OperationCreate, OperationView
from app.services.operation_service import approve_operation, create_operation, get_operation, instruct_operation, to_view

router = APIRouter()


@router.post("/operations", response_model=OperationView, status_code=201)
async def create(payload: OperationCreate, db: Session = Depends(get_db)) -> OperationView:
    op = await create_operation(db, payload.request)
    return to_view(op)


@router.get("/operations/{operation_id}", response_model=OperationView)
def read(operation_id: str, db: Session = Depends(get_db)) -> OperationView:
    set_trace_operation_id(operation_id)
    op = get_operation(db, operation_id)
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found.")
    view = to_view(op)
    set_trace_operation_id(operation_id, title=view.title, workflow_type=op.workflow_type)
    return view


@router.post("/operations/{operation_id}/approve", response_model=OperationView)
async def approve(operation_id: str, payload: ApprovalRequest, db: Session = Depends(get_db)) -> OperationView:
    op = get_operation(db, operation_id)
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found.")
    try:
        updated = await approve_operation(db, op, payload)
        return to_view(updated)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/operations/{operation_id}/instruct", response_model=OperationView)
async def instruct(operation_id: str, payload: InstructionRequest, db: Session = Depends(get_db)) -> OperationView:
    set_trace_operation_id(operation_id)
    op = get_operation(db, operation_id)
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found.")
    try:
        updated = await instruct_operation(db, op, payload.instruction)
        return to_view(updated)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/operations/{operation_id}/audit", response_model=list[AuditEventView])
def get_audit(operation_id: str, db: Session = Depends(get_db)) -> list[AuditEventView]:
    set_trace_operation_id(operation_id)
    op = get_operation(db, operation_id)
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found.")
    view = to_view(op)
    set_trace_operation_id(operation_id, title=view.title, workflow_type=op.workflow_type)
    return [
        AuditEventView(
            id=e.id,
            timestamp=e.created_at,
            created_at=e.created_at,
            node=e.node,
            event_type=e.event_type,
            tool_name=e.tool_name,
            action=e.action,
            status=e.status,
            message=e.message,
            safe_metadata=e.safe_metadata or {},
        )
        for e in op.events
    ]
