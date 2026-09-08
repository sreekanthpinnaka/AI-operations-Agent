from __future__ import annotations

from typing import Annotated, Any, TypedDict
import operator
from sqlalchemy.orm import Session
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from app.models.schemas import AnalysisResult, PlanStep


class OperationsState(TypedDict, total=False):
    request_id: str
    user_request: str
    operator_id: str | None
    db: Session
    analysis: AnalysisResult
    plan: list[PlanStep]
    tool_results: list[dict[str, Any]]
    validation_results: list[dict[str, Any]]
    findings: dict[str, Any]
    pending_actions: list[dict[str, Any]]
    errors: list[str]
    final_result: dict[str, Any]
    ai_metadata: dict[str, Any]
    micro_steps: list[dict[str, Any]]
    messages: Annotated[list[BaseMessage], add_messages]
    retry_count: int
    validation_errors: list[str]
    tool_turns: int
    is_continuation: bool
    dispatch_all_requested: bool


