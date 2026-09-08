from __future__ import annotations

from typing import Any
from sqlalchemy.orm import Session

from app.db.guardrails import RiskLevel
from app.models.schemas import ToolResult
from app.tools.base import ActionSpec, BaseTool


class StagingManagementTool(BaseTool):
    name = "staging_tool"
    description = "Allows the agent to update, remove, or trigger dispatch for actions currently staged at the Human Clearance Gate."

    actions = {
        "update_staged_action": ActionSpec(
            name="update_staged_action",
            risk=RiskLevel.READ,
            description="Update the parameters/payload of an existing staged action currently held at the Human Clearance Gate (e.g. amount, recipient, quantity).",
            parameters_schema={
                "type": "object",
                "properties": {
                    "action_id": {
                        "type": "string",
                        "description": "The ID or index of the staged action to update.",
                    },
                    "updates": {
                        "type": "object",
                        "description": "Key-value dictionary of payload fields to update (e.g. {'amount': 4500, 'to': 'user@example.com'}).",
                    },
                },
                "required": ["action_id", "updates"],
            },
        ),
        "remove_staged_action": ActionSpec(
            name="remove_staged_action",
            risk=RiskLevel.READ,
            description="Remove or cancel an action currently held at the Human Clearance Gate.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "action_id": {
                        "type": "string",
                        "description": "The ID or index of the staged action to remove.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for removing the action.",
                    },
                },
                "required": ["action_id"],
            },
        ),
        "approve_and_dispatch_all": ActionSpec(
            name="approve_and_dispatch_all",
            risk=RiskLevel.READ,
            description="Trigger execution and dispatch of all staged actions when the human operator instructs to send or approve them.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Confirmation rationale for dispatching actions.",
                    },
                },
                "required": ["reason"],
            },
        ),
    }

    async def execute(self, action: str, parameters: dict[str, Any], db: Session) -> ToolResult:
        return ToolResult(
            tool=self.name,
            action=action,
            data={"status": "APPLIED", "action": action, "parameters": parameters},
            success=True,
        )
