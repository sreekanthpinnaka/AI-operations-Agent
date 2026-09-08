from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from typing import Any

try:
    from langgraph_observe.core.context import (
        get_current_trace,
        trace_span as _observe_trace_span,
    )
    from langgraph_observe.core.models import SpanType
    _OBSERVE_AVAILABLE = True
except ImportError:
    _OBSERVE_AVAILABLE = False


@asynccontextmanager
async def trace_span(name: str, component: str = "custom", metadata: dict[str, Any] | None = None):
    span_data: dict[str, Any] = {"name": name, "component": component, "metadata": dict(metadata or {})}
    if _OBSERVE_AVAILABLE:
        meta = dict(span_data["metadata"])
        meta["component"] = component
        with _observe_trace_span(name=name, span_type=SpanType.CUSTOM, metadata=meta) as obs_span:
            try:
                yield span_data
            finally:
                if obs_span is not None and isinstance(obs_span.metadata, dict):
                    obs_span.metadata.update(span_data["metadata"])
    else:
        yield span_data


@contextmanager
def sync_trace_span(name: str, component: str = "custom", metadata: dict[str, Any] | None = None):
    span_data: dict[str, Any] = {"name": name, "component": component, "metadata": dict(metadata or {})}
    if _OBSERVE_AVAILABLE:
        meta = dict(span_data["metadata"])
        meta["component"] = component
        with _observe_trace_span(name=name, span_type=SpanType.CUSTOM, metadata=meta) as obs_span:
            try:
                yield span_data
            finally:
                if obs_span is not None and isinstance(obs_span.metadata, dict):
                    obs_span.metadata.update(span_data["metadata"])
    else:
        yield span_data


def set_trace_operation_id(operation_id: str, title: str | None = None, workflow_type: str | None = None) -> None:
    if _OBSERVE_AVAILABLE:
        try:
            trace = get_current_trace()
            if trace is not None:
                trace.metadata["operation_id"] = str(operation_id)
                if title:
                    trace.metadata["title"] = str(title)
                if workflow_type:
                    trace.metadata["workflow_type"] = str(workflow_type)
        except Exception:
            pass
