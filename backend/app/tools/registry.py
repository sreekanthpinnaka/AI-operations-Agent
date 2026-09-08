from __future__ import annotations

from typing import Any
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.tracing import trace_span
from app.models.schemas import ToolResult
from app.tools.base import ActionSpec, BaseTool
from app.tools.db_tools import (
    AccessRequestDBTool,
    CRMDBTool,
    DatabaseQueryTool,
    EmailDBTool,
    EmployeeDirectoryDBTool,
    InventoryDBTool,
    InvoiceDBTool,
    PolicyDBTool,
    ProcurementDBTool,
    SupportDBTool,
    TaskDBTool,
)
from app.tools.staging_tools import StagingManagementTool


class ToolRegistry:
    def __init__(self) -> None:
        tools: list[BaseTool] = [
            InvoiceDBTool(),
            EmailDBTool(),
            SupportDBTool(),
            InventoryDBTool(),
            ProcurementDBTool(),
            CRMDBTool(),
            EmployeeDirectoryDBTool(),
            PolicyDBTool(),
            AccessRequestDBTool(),
            TaskDBTool(),
            DatabaseQueryTool(),
            StagingManagementTool(),
        ]
        self._tools: dict[str, BaseTool] = {tool.name: tool for tool in tools}
        self._actions_map: dict[str, tuple[BaseTool, ActionSpec]] = {}

        for tool in tools:
            for action_name, action_spec in tool.actions.items():
                action_spec.tool_name = tool.name
                self._actions_map[action_name] = (tool, action_spec)

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise ValueError(f"Unregistered tool: '{name}'")
        return self._tools[name]

    def get_action(self, action_name: str) -> tuple[BaseTool, ActionSpec]:
        if action_name not in self._actions_map:
            raise ValueError(f"Unregistered action: '{action_name}'")
        return self._actions_map[action_name]

    def catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "actions": [a.model_dump(mode="json") for a in t.actions.values()],
            }
            for t in self._tools.values()
        ]

    def to_gemini_declarations(self) -> list[dict[str, Any]]:
        declarations = []
        for action_name, (tool, action_spec) in self._actions_map.items():
            schema = action_spec.parameters_schema or {"type": "object", "properties": {}}
            declarations.append({
                "name": action_name,
                "description": f"[{tool.name}] {action_spec.description} (Risk: {action_spec.risk.value})",
                "parameters": schema,
            })
        return declarations

    def to_openai_tools(self) -> list[dict[str, Any]]:
        tools = []
        for action_name, (tool, action_spec) in self._actions_map.items():
            schema = action_spec.parameters_schema or {"type": "object", "properties": {}}
            tools.append({
                "type": "function",
                "function": {
                    "name": action_name,
                    "description": f"[{tool.name}] {action_spec.description} (Risk: {action_spec.risk.value})",
                    "parameters": schema,
                },
            })
        return tools

    def validate_action(self, tool_name: str, action: str) -> None:
        self.get(tool_name).action_spec(action)

    async def execute(self, tool_name: str, action: str, parameters: dict[str, Any], db: Session) -> ToolResult:
        tool = self.get(tool_name)
        result: ToolResult | None = None
        max_retries = get_settings().max_tool_retries

        async with trace_span(f"{tool_name}.{action}", tool_name, {"tool": tool_name, "action": action, "parameters": parameters}) as s:
            for attempt in range(max_retries + 1):
                result = await tool.execute(action, parameters, db)
                result.metadata["attempts"] = attempt + 1
                if result.success:
                    s["metadata"]["success"] = True
                    s["metadata"]["attempts"] = attempt + 1
                    if isinstance(result.data, list):
                        s["metadata"]["records_count"] = len(result.data)
                    elif isinstance(result.data, dict):
                        s["metadata"]["keys"] = list(result.data.keys())
                    return result

            assert result is not None
            s["metadata"]["success"] = False
            s["metadata"]["error"] = result.error
            return result


registry = ToolRegistry()
