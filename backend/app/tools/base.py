from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.guardrails import RiskLevel
from app.models.schemas import ToolResult


class ActionSpec(BaseModel):
    name: str
    risk: RiskLevel
    description: str
    tool_name: str = ""
    parameters_schema: dict[str, Any] = {}


class BaseTool(ABC):
    name: str
    description: str
    actions: dict[str, ActionSpec]

    @abstractmethod
    async def execute(self, action: str, parameters: dict[str, Any], db: Session) -> ToolResult:
        raise NotImplementedError

    def action_spec(self, action: str) -> ActionSpec:
        if action not in self.actions:
            raise ValueError(f"Unsupported action '{action}' for tool '{self.name}'")
        return self.actions[action]
