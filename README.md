<div align="center">

# 🤖 AI Operations Agent

An operations assistant built with **FastAPI**, **LangGraph**, and **React**. It queries databases to investigate operational tasks, drafts actions, and requires human approval before making any changes.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-purple.svg?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![LangGraph Observe](https://img.shields.io/badge/Observability-LangGraph%20Observe-8A2BE2.svg)](https://github.com/sreekanthpinnaka/langgraph_observability_tool)
[![React 18](https://img.shields.io/badge/React-18.3+-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5+-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Vite](https://img.shields.io/badge/Vite-5.4+-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[What It Does](#-what-it-does) • [How It Works](#-how-it-works) • [Observability](#-langgraph-observability--visual-tracing) • [Quick Start](#-quick-start-guide) • [Database](#-database-schema) • [API](#-rest-api-reference)

---

</div>

## 💡 What It Does

When managing operations across finance, customer support, and inventory, automated scripts can be rigid, while chatbots can make mistakes if given direct write access to your database.

This project sits in the middle:
- **Investigates automatically**: Given a request (e.g. *"Find invoices overdue by more than 30 days and prepare reminder emails"* or *"Check inventory running low and restock"*), the agent queries the database and gathers the relevant data.
- **Stages changes for human review**: Instead of modifying the database directly, the agent stages every write action (e.g. `send_email`, `create_purchase_order`, `escalate_ticket`) at a **Human Clearance Gate**.
- **Allows edits and conversation**: You can review the exact payloads, edit them, approve or reject them, or give conversational follow-ups (e.g. *"Change vendor on the first PO to Northwind and set quantity to 200"*).
- **Guards SQL queries**: Ad-hoc queries pass through an AST parser (`sqlglot`) that permits only safe `SELECT` statements on whitelisted tables, adds `LIMIT 100` if missing, and rejects `DROP`, `DELETE`, and `UPDATE` statements.
- **Full visual tracing**: Instrumented with [LangGraph Observe](https://github.com/sreekanthpinnaka/langgraph_observability_tool) so you can visually inspect the execution graph, state diffs, step latencies, and token costs in a real-time dashboard.

---

## ⚙️ How It Works

### 1. Reads Run Autonomously, Writes Wait for Approval
- **Read tools** (`get_open_tickets`, `list_overdue_invoices`, `check_inventory_runway`, `execute_read`) execute immediately to gather context.
- **Write tools** (`send_email`, `create_purchase_order`, `escalate_ticket`, `decide_access`) are intercepted by the runtime and held as `pending_actions`. No database records are created or modified until an operator clicks Approve.

### 2. 2-Loop LangGraph Architecture
The agent runs on a compiled LangGraph workflow with two loops:
- **Loop 1 (ReAct Tool Cycle)**: The agent reasons over findings, calls read tools, and stages write actions.
- **Loop 2 (Policy Validation & Correction)**: Staged actions are validated against predefined rules (e.g., maximum purchase amounts, valid recipient emails). If an action violates a rule, the validator sends feedback back to the agent to adjust the payload before asking for human approval.

### 3. Human Clearance & Continuation
- The operator sees staged action cards in the UI showing the action type, parameters, and risk level.
- The operator can approve, reject, edit the payload directly, or type follow-up instructions into the chat box.

### 4. AST SQL Guardrails
- Queries are parsed into an Abstract Syntax Tree using `sqlglot`.
- Only `SELECT` statements on 24 application tables and 4 views are permitted.
- Missing `LIMIT` clauses are automatically clamped to `LIMIT 100`.
- Destructive commands (`DROP`, `ALTER`, `TRUNCATE`) return `HTTP 403 Forbidden`.

---

## 🔭 LangGraph Observability & Visual Tracing

This project uses **[LangGraph Observe](https://github.com/sreekanthpinnaka/langgraph_observability_tool)** for execution tracing and debugging.

> [!NOTE]
> The observability tool runs as a standalone service and needs to be cloned from:  
> **[https://github.com/sreekanthpinnaka/langgraph_observability_tool](https://github.com/sreekanthpinnaka/langgraph_observability_tool)**

### What it shows at `http://localhost:8765`:
- **Graph Topology**: Visual DAG showing nodes (`analyze`, `agent`, `tools`, `validate`, `self_correct`, `finalize`) and loop paths.
- **Step Waterfall**: Timeline of each node run, tool execution time, and LLM call latency.
- **State Diffs**: Exact changes to state after each node (new findings, staged actions, validation results).
- **Token & Cost Metrics**: Tracks input and output token counts per step.

```text
  FastAPI Backend (port 8000) ────────► LangGraph Observe Server (port 8765)
  (observe_graph + instrument_fastapi)    (Web dashboard with DAG, traces & diffs)
```

---

## 🏗️ Architecture

```text
 ┌─────────────────────────────────────────────────────────────────┐
 │                   REACT + TYPESCRIPT CLIENT                     │
 │  • Agent Workspace   • SQL Sandbox   • Database Schema Guide    │
 └───────────────────────────────┬─────────────────────────────────┘
                                 │ HTTP requests
                                 ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │                        FASTAPI BACKEND                          │
 │  • Pydantic validation • REST routes • LangGraph Observe SDK    │
 └───────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │                     LANGGRAPH STATE GRAPH                       │
 │                                                                 │
 │   analyze ──► agent ◄────► tools (reads run, writes staged)     │
 │                 │                                               │
 │                 ▼                                               │
 │             validate ◄───► self_correct                         │
 │                 │                                               │
 │                 ▼                                               │
 │             finalize ──► Human Clearance Gate                   │
 └───────────────────────────────┬─────────────────────────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
 ┌───────────────────────────────┐ ┌───────────────────────────────┐
 │      DATABASE LAYER           │ │   LANGGRAPH OBSERVE SERVER    │
 │  • MySQL 8.0 or SQLite        │ │  • Port 8765                  │
 │  • 24 tables across 7 domains │ │  • Visual DAG & trace history │
 │  • Audit log (audit_events)   │ │  • State diffs & token stats  │
 └───────────────────────────────┘ └───────────────────────────────┘
```

---

## 📊 Database Schema

The database models common business operations divided into **7 domains**:

```text
├── 1. Identity & Organization (customers, employees, software_systems, app_users)
├── 2. Finance & Receivables (invoices, sales_leads, email_messages, overdue_invoice_candidates)
├── 3. Customer Support (support_tickets)
├── 4. Supply Chain & Procurement (products, suppliers, supplier_products, inventory, purchase_orders)
├── 5. Access Control / RBAC (access_policies, access_requests, access_review_queue)
├── 6. Meetings & Collaboration (meetings, meeting_participants, action_items)
└── 7. Governance & Audit (operation_requests, pending_actions, approvals, audit_events)
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** and **npm**
- **Git**

---

### Step 1: Start the Observability Server

1. Clone the observability tool repository in an adjacent directory:
   ```bash
   git clone https://github.com/sreekanthpinnaka/langgraph_observability_tool.git
   cd langgraph_observability_tool
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   ```

3. Start the server:
   ```bash
   langgraph-observe
   # Or: python -m langgraph_observe.server.cli
   ```
   Open **[http://localhost:8765](http://localhost:8765)** for the dashboard.

---

### Step 2: Start the Backend

1. In the repository root, navigate to `backend`:
   ```bash
   cd backend
   ```

2. Set up a virtual environment:
   ```bash
   # Windows:
   python -m venv .venv
   .venv\Scripts\Activate.ps1

   # macOS/Linux:
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   *(Add your `OPENAI_API_KEY`. If left blank, the agent runs in deterministic offline mode)*.

5. Run the server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   - Health check: [http://localhost:8000/api/health](http://localhost:8000/api/health)
   - API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Step 3: Start the Frontend

1. In a new terminal, navigate to `frontend`:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

4. Start Vite:
   ```bash
   npm run dev
   ```
   Open **[http://localhost:5173](http://localhost:5173)** in your browser.

---

## 🧪 Example Scenarios to Try

Try these in the **Agent Workspace**:

### 1. Overdue Invoices
- **Prompt**: `"Find invoices overdue by more than 30 days and prepare reminder emails."`
- **Result**: The agent queries overdue invoices, displays them in the findings table, and stages draft reminder emails for you to review and approve.

### 2. Support Ticket Escalation
- **Prompt**: `"Review today's support tickets and escalate critical payment issues."`
- **Result**: The agent fetches open tickets, identifies critical payment issues, and stages escalation actions with the target team.

### 3. Low Stock Reorders
- **Prompt**: `"Find inventory likely to run out within 14 days and prepare reorders."`
- **Result**: Calculates days of runway (`current_stock / daily_usage`), checks supplier packaging sizes, and stages purchase orders.

### 4. Conversational Follow-Up
- After actions are staged, type:
  `"Change the vendor on the first order to Northwind and set quantity to 200"`
  The agent updates the staged item without you having to start over.

### 5. SQL Guardrail Sandbox
Under the **AST Guardrail Sandbox** tab:
- Run: `SELECT customer_code, name, tier FROM customers;` $\to$ Returns data limited to 100 rows.
- Run: `DROP TABLE customers;` $\to$ Blocked with HTTP 403 Forbidden.

---

## ⚙️ Configuration (`.env`)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///./gemini_ops.db` | Database connection string (SQLite or MySQL). Auto-seeds demo data on startup. |
| `OPENAI_API_KEY` | *(Optional)* | OpenAI API key. If omitted, uses deterministic local fallback. |
| `OPENAI_MODEL` | `gpt-4o-mini` | LLM model for planning and tool selection. |
| `OPENAI_TEMPERATURE` | `0.1` | Temperature for deterministic output. |
| `FRONTEND_URL` | `http://localhost:5173` | Allowed CORS origin. |
| `OBSERVE_SERVER_URL` | `http://localhost:8765` | URL for the LangGraph Observe server. |
| `OBSERVE_PROJECT` | `ai-operations-agent` | Project tag for traces. |
| `OBSERVE_ENVIRONMENT` | `development` | Environment tag for traces. |

---

## 📡 REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/operations` | Start an operation from a natural language request. |
| `GET` | `/api/operations/{id}` | Get operation status, plan, findings, and staged actions. |
| `POST` | `/api/operations/{id}/instruct` | Send follow-up instructions to modify staged actions. |
| `POST` | `/api/operations/{id}/approve` | Approve, reject, or modify staged actions. |
| `GET` | `/api/operations/{id}/audit` | View audit trail for the operation. |
| `POST` | `/api/demo/guardrail-query` | Run an ad-hoc SQL query through the AST guardrail. |
| `POST` | `/api/demo/reset` | Reset demo database to baseline data. |
| `GET` | `/api/health` | Service health check. |

---

## 📁 Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI route handlers
│   │   ├── core/            # Config, settings & tracing
│   │   ├── db/              # Models, session & AST SQL guardrail (sqlglot)
│   │   ├── graph/           # Compiled 2-loop LangGraph workflow
│   │   ├── services/        # Agent loop & tool dispatching
│   │   ├── tools/           # Database tool implementations
│   │   └── main.py          # FastAPI application entrypoint
│   ├── tests/               # Pytest test suite (41 tests)
│   ├── requirements.txt     # Python dependencies
│   └── README.md            # Backend guide
│
├── frontend/
│   ├── src/                 # React UI components & state
│   ├── package.json         # Node dependencies
│   └── README.md            # Frontend guide
│
├── sql/                     # Schema scripts for MySQL and PostgreSQL
├── docs/                    # Architecture notes and details
├── .gitignore
├── .env.example
├── LICENSE
└── README.md
```

---

## 🧪 Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend build check
cd frontend
npm run build
```

---

## 📄 License

[MIT](LICENSE)
