from __future__ import annotations

import asyncio
import json
from typing import TypeVar

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.models.schemas import WorkflowType

T = TypeVar("T", bound=BaseModel)


class ModelIntentResult(BaseModel):
    workflow_type: WorkflowType
    sql_query: str | None = Field(default=None, description="Optional SELECT SQL query if this is an ad-hoc database question")
    days_overdue: int | None = Field(default=None, ge=1, le=3650)
    days_remaining: int | None = Field(default=None, ge=1, le=365)
    inactive_days: int | None = Field(default=None, ge=1, le=3650)
    enterprise_only: bool = False
    payment_only: bool = False
    requested_actions: list[str] = Field(default_factory=list)
    possible_sensitive_actions: list[str] = Field(default_factory=list)
    missing_parameters: list[str] = Field(default_factory=list)


class DraftItem(BaseModel):
    record_id: str
    subject: str = Field(min_length=3, max_length=180)
    body: str = Field(min_length=20, max_length=4000)


class DraftBatch(BaseModel):
    drafts: list[DraftItem]


class SupportRationale(BaseModel):
    ticket_id: str
    explanation: str = Field(min_length=10, max_length=800)
    recommended_team: str = Field(min_length=2, max_length=120)


class SupportRationaleBatch(BaseModel):
    recommendations: list[SupportRationale]


class MeetingAction(BaseModel):
    owner: str
    title: str
    due: str | None = None
    blockers: list[str] = Field(default_factory=list)


class MeetingExtraction(BaseModel):
    decisions: list[str] = Field(default_factory=list)
    action_items: list[MeetingAction] = Field(default_factory=list)


class GeminiService:
    """
    Google Gemini SDK provider boundary for AI Operations Agent.
    Falls back gracefully when GEMINI_API_KEY is not configured.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def configured(self) -> bool:
        return bool(self.settings.gemini_api_key)

    def _sync_generate_structured(self, system_instruction: str, user_content: str, schema: type[T]) -> T:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.settings.gemini_api_key)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=self.settings.gemini_temperature,
            response_mime_type="application/json",
            response_schema=schema,
        )
        response = client.models.generate_content(
            model=self.settings.gemini_model,
            contents=user_content,
            config=config,
        )
        if not response.text:
            raise RuntimeError("Gemini model returned empty response.")
        return schema.model_validate_json(response.text)

    async def generate_structured(self, system_instruction: str, user_content: str, schema: type[T]) -> T:
        if not self.configured:
            raise RuntimeError("Gemini API key is not configured.")
        return await asyncio.to_thread(self._sync_generate_structured, system_instruction, user_content, schema)


gemini_service = GeminiService()
