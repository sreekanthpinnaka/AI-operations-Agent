# ⚙️ AI Operations Agent — Backend Engine

> FastAPI backend powered by a 2-loop cyclic LangGraph state machine, SQL guardrails (`sqlglot`), human approval clearance, and full observability via [LangGraph Observe](https://github.com/sreekanthpinnaka/langgraph_observability_tool).

---

## 🏗️ Architecture & State Machine

The backend coordinates autonomous investigation and safe staging using a compiled **LangGraph** state graph (`OperationsState`) operating across two primary execution cycles:

```text
               ┌─────────────────────────┐
               │      analyze_node       │
               │ (Intent Classification) │
               └────────────┬────────────┘
                            │
                            ▼
        ┌─────────────► agent_node ◄─────────────┐
        │            (LLM Reasoning)             │
        │                   │                    │
  (Read Results)            │ (Tool Calls)   (Correction Feedback)
        │                   ▼                    │
        └────────────── tools_node               │
                     (Dispatcher &               │
                   Clearance Intercept)          │
                            │                    │
                            ▼                    │
                      validate_node ─────────────┘
                    (Deterministic Policy   [if violations found]
                     & Guardrail Checks)
                            │
                            │ [if clean]
                            ▼
                      finalize_node ──► END
```

### 1. Loop 1: ReAct Tool-Execution Cycle (`agent` 🔁 `tools`)
- The agent reasons over findings, decides on relevant tools, and issues structured tool calls.
- **Read tools** (`get_open_tickets`, `list_overdue_invoices`, `check_inventory_runway`, `ad_hoc_read`) execute immediately and append results to `state["messages"]` and `state["findings"]`.
- **Consequential write tools** (`send_email`, `create_purchase_order`, `escalate_ticket`, `decide_access`) are safely intercepted by `_build_pending_action()` and staged in `state["pending_actions"]` without modifying production data.

### 2. Loop 2: Policy & Guardrail Self-Correction Cycle (`validate` 🔁 `self_correct` ➡️ `agent`)
- All staged pending actions pass through a deterministic validator that checks business constraints, credit limits, authorized recipient domains, and supplier thresholds.
- If policy violations are found, `self_correct_node` feeds specific error diagnostic feedback back into the agent context, prompting the model to auto-remediate payload parameters before pausing for human clearance.

### 3. Human Clearance Gate & Conversational Continuation (`/instruct`)
- When paused at the clearance gate, an authenticated human operator can review staged actions, approve/reject individual items, edit payload forms, or chat directly with the agent via `POST /api/operations/{id}/instruct`.
- The continuation flow re-activates the LangGraph state machine with full conversational memory, dynamically adjusting or supplementing staged actions according to the operator's instructions.

---

## 🔭 LangGraph Observability & Visual Tracing

The backend integrates seamlessly with **[LangGraph Observe](https://github.com/sreekanthpinnaka/langgraph_observability_tool)**, a lightweight, universal observability server and visual dashboard for LangGraph workflows.

### Installation of the Observability Tool
Clone and install the observability package from its dedicated repository:

```bash
# Clone the repository
git clone https://github.com/sreekanthpinnaka/langgraph_observability_tool.git
cd langgraph_observability_tool

# Install in development mode
pip install -e .

# Start the standalone server (default: port 8765)
langgraph-observe
```

Access the real-time visual dashboard at: **`http://localhost:8765`**

### Backend Instrumentation
1. **FastAPI Middleware**: Instrumented in [`app/main.py`](file:///d:/AI_operations_agent/gemini/backend/app/main.py) via `instrument_fastapi()`:
   ```python
   from langgraph_observe import instrument_fastapi

   instrument_fastapi(
       app,
       server_url=get_settings().observe_server_url,
       project=get_settings().observe_project,
       environment=get_settings().observe_environment,
       trace_id_header="X-LangGraph-Trace-ID",
   )
   ```
2. **Graph Wrapper**: The compiled StateGraph in [`app/graph/workflow.py`](file:///d:/AI_operations_agent/gemini/backend/app/graph/workflow.py) is wrapped via `observe_graph()`:
   ```python
   operations_graph = observe_graph(
       builder.compile(),
       name="AIOperationsWorkflow",
       project=_settings.observe_project,
       environment=_settings.observe_environment,
   )
   ```
3. **Trace Spans & Metadata**: Handled transparently in [`app/core/tracing.py`](file:///d:/AI_operations_agent/gemini/backend/app/core/tracing.py), correlating HTTP route traces, node executions, tool latencies, and `operation_id` metadata.

---

## 🛡️ AST SQL Guardrail Engine (`sqlglot`)

Dynamic read queries pass through [`app/db/guardrails.py`](file:///d:/AI_operations_agent/gemini/backend/app/db/guardrails.py) before execution:
- **Abstract Syntax Tree Parsing**: Validates dialect semantics (MySQL / SQLite).
- **Strict Table Whitelisting**: Allows access only to the 24 application tables and 4 reporting views. Any access to system catalogs (`information_schema`, `mysql`, `sqlite_master`) is blocked with HTTP 403 Forbidden.
- **Statement Type Enforcement**: Only `SELECT` statements are permitted. Destructive keywords (`DROP`, `ALTER`, `TRUNCATE`, `DELETE`, `UPDATE`, `INSERT`, `GRANT`, `REVOKE`) trigger immediate rejection.
- **Auto-Clamping**: Select statements without an explicit limit are automatically rewritten with `LIMIT 100` to prevent memory exhaustion and denial-of-service.

---

## 🚀 Setup & Execution

### 1. Virtual Environment & Dependencies
```bash
# Navigate to the backend directory
cd backend

# Create virtual environment
python -m venv .venv

# Activate (PowerShell)
.venv\Scripts\Activate.ps1
# Or macOS/Linux: source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure Environment
Copy and customize `.env.example`:
```bash
cp .env.example .env
```

Key environment variables:
| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///./gemini_ops.db` | Database connection string. Auto-seeds on startup. |
| `OPENAI_API_KEY` | *(Optional)* | OpenAI API key. If absent, deterministic fallback is used. |
| `OPENAI_MODEL` | `gpt-4o-mini` | LLM model name for reasoning & structured tool selection. |
| `OBSERVE_SERVER_URL`| `http://localhost:8765` | Remote URL of the LangGraph Observe server. |
| `OBSERVE_PROJECT` | `ai-operations-agent` | Project identifier used for filtering traces. |
| `OBSERVE_ENVIRONMENT`| `development` | Deployment environment label. |

### 3. Launch the Backend Server
```bash
uvicorn app.main:app --reload --port 8000
```

- Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- Swagger OpenAPI Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Testing

Execute the automated test suite covering AST guardrails, 2-loop cyclic workflows, multi-turn continuation, binary16 UUID handling, and LangGraph Observe integration:

```bash
pytest tests/ -v
```
