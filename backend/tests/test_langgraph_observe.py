from __future__ import annotations

from fastapi.testclient import TestClient


def test_langgraph_observe_wrapper_and_headers(client: TestClient):
    from app.graph.workflow import operations_graph
    from langgraph_observe import ObservedGraph

    # Verify operations_graph is an ObservedGraph
    assert isinstance(operations_graph, ObservedGraph)
    assert operations_graph._name == "AIOperationsWorkflow"
    assert operations_graph._project == "ai-operations-agent"
    assert operations_graph._environment == "development"
    assert "analyze" in operations_graph.nodes
    assert "agent" in operations_graph.nodes
    assert "tools" in operations_graph.nodes
    assert "validate" in operations_graph.nodes
    assert "self_correct" in operations_graph.nodes
    assert "finalize" in operations_graph.nodes

    # Verify FastAPI endpoint returns X-LangGraph-Trace-ID header from instrument_fastapi
    res = client.get("/api/health")
    assert res.status_code == 200
    assert "X-LangGraph-Trace-ID" in res.headers
    assert len(res.headers["X-LangGraph-Trace-ID"]) > 0


def test_tracing_module_integration():
    from app.core.tracing import sync_trace_span, set_trace_operation_id
    from langgraph_observe.client.collector import TraceCollector
    from langgraph_observe.core.context import set_current_collector, set_current_trace
    from langgraph_observe.server.storage.memory import MemoryStorage

    storage = MemoryStorage()
    collector = TraceCollector(name="test-trace", storage=storage, project="ai-operations-agent")
    tok_c = set_current_collector(collector)
    tok_t = set_current_trace(collector.trace)

    try:
        set_trace_operation_id("op-12345", title="Escalate Tickets", workflow_type="ticket_escalation")
        assert collector.trace.metadata.get("operation_id") == "op-12345"
        assert collector.trace.metadata.get("title") == "Escalate Tickets"
        assert collector.trace.metadata.get("workflow_type") == "ticket_escalation"

        with sync_trace_span("test.node", "custom", {"key": "val"}) as s:
            s["metadata"]["updated_key"] = "new_val"

        assert len(collector.trace.spans) == 1
        span = collector.trace.spans[0]
        assert span.name == "test.node"
        assert span.metadata.get("key") == "val"
        assert span.metadata.get("updated_key") == "new_val"
        assert span.metadata.get("component") == "custom"
    finally:
        set_current_collector(None)
        set_current_trace(None)

