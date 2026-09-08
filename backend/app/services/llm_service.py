from __future__ import annotations

import json
from typing import Any, TypeVar
from pydantic import BaseModel

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI
from app.core.config import get_settings

T = TypeVar("T", bound=BaseModel)


class LLMService:
    def __init__(self) -> None:
        pass

    @property
    def configured(self) -> bool:
        return bool(get_settings().openai_api_key)

    @property
    def model_name(self) -> str:
        return get_settings().openai_model

    def get_client(self) -> AsyncOpenAI:
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        return AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
        )

    def get_chat_model(self, temperature: float | None = None) -> ChatOpenAI:
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=settings.openai_temperature if temperature is None else temperature,
            timeout=settings.openai_timeout_seconds,
        )

    async def generate_structured(
        self,
        prompt: str,
        schema_cls: type[T],
        system_prompt: str | None = None,
        config: RunnableConfig | dict | None = None,
    ) -> tuple[T | None, dict[str, Any]]:
        if not self.configured:
            return None, {"used": False, "reason": "OPENAI_API_KEY not configured"}

        settings = get_settings()
        chat_model = self.get_chat_model(temperature=0.0)
        structured_llm = chat_model.with_structured_output(schema_cls)

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            parsed = await structured_llm.ainvoke(messages, config=config)
            return parsed, {"used": True, "model": settings.openai_model, "provider": "openai"}
        except Exception as exc:
            return None, {"used": False, "error": str(exc), "model": settings.openai_model}


llm_service = LLMService()
