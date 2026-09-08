# 💻 AI Operations Agent — Web Control Surface

> Modern React 18 + TypeScript + Vite operations dashboard featuring conversational Human-in-the-Loop clearance, real-time trajectory visualization, AST SQL sandbox, and interactive data catalog.

---

## 🌟 Key Features

1. **Agent Workspace (`/`)**:
   - Natural language prompt composer with multi-line input and `<kbd>Ctrl + Enter</kbd>` shortcut.
   - 1-click execution pills for common operational scenarios.
   - **Live Trajectory Stepper**: Tracks graph execution across `analyze`, `agent`, `tools`, `validate`, `self_correct`, and `finalize`.
   - **Human Clearance Gate**: Cards for staged consequential actions (`send_email`, `create_purchase_order`, `escalate_ticket`, `decide_access`) with risk badges, formatted previews, and individual or batch Approve / Reject controls.
   - **Conversational HITL Refinement**: Follow-up instruction input allowing operators to prompt the agent with natural language instructions (e.g., *"Change vendor to Northwind and update order amount to 100"* or *"Send them out"*) without losing staged context.
   - **Evidence & Findings Panel**: Structured tables displaying queried records with reasoning callouts and row metrics.

2. **AST Guardrail Sandbox (`/sandbox`)**:
   - Interactive SQL terminal for testing ad-hoc queries against the database schema.
   - Instant AST validation feedback: Green badge for permitted queries or Red HTTP 403 alert detailing the exact security policy violation.
   - Pre-loaded safe queries vs. malicious attack vectors (*DROP TABLE*, *Unconditional UPDATE*, *WHERE 1=1*).

3. **Database Guide & Data Catalog (`/guide`)**:
   - Interactive schema dictionary detailing all **24 tables** and **4 reporting views**.
   - Real-time search by table name, column attribute, or domain.
   - 1-click query actions ("Run in Sandbox" or "Ask Agent").

4. **Live System State Drawer**:
   - Slide-out drawer accessible from the top navigation bar to inspect live database records:
     - Transmitted email dunning notices and supplier orders.
     - Generated purchase orders and line items.
     - Escalated support tickets and reassigned teams.

---

## 🚀 Setup & Execution

### 1. Prerequisites
- **Node.js 18+** and **npm** (`node --version`)
- Backend running on `http://localhost:8000`

### 2. Install Dependencies
```bash
cd frontend
npm install
```

### 3. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Ensure `VITE_API_BASE_URL` points to your backend:
```env
VITE_API_BASE_URL=http://localhost:8000/api
```

### 4. Start Development Server
```bash
npm run dev
```

Open your browser at: **`http://localhost:5173`**

### 5. Build for Production
```bash
npm run build
```
The optimized production bundle will be generated in `dist/`.
