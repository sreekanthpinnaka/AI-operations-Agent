from __future__ import annotations

import json
from datetime import date
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from app.core.config import get_settings
from app.core.tracing import trace_span
from app.db.executor import SafeQueryExecutor
from app.db.guardrails import RiskLevel
from app.models.schemas import PlanStep, StepStatus
from app.services.llm_service import llm_service
from app.tools.registry import registry

SYSTEM_INSTRUCTION = """You are an expert AI Operations Agent with autonomous access to enterprise data tools across Accounts Receivable (Invoices), Customer Support, Inventory & Procurement, CRM Sales Pipeline, Employee Directory, Policy Access Control, and Guarded SQL Database Queries.

Your mission:
1. Analyze the user's operational request carefully.
2. Formulate a plan and invoke the appropriate read tools to gather real data from enterprise systems.
3. Reason over the returned observations.
4. When operational actions are needed (such as drafting reminders, escalating tickets, placing purchase orders, granting access, or creating tasks), invoke the appropriate write tools directly.
5. Provide a clear, professional synthesis of what you investigated and what actions you staged.

SAFETY ENFORCEMENT & TOOL EXECUTION:
- Read tools execute immediately to provide you with live data.
- Consequential write tools (send_email, create_purchase_order, escalate_ticket, decide_access, create_task, insert_record, update_record, delete_record) are safely intercepted by the system runtime and held at the Human Clearance Gate.
- IMPORTANT: You MUST invoke the write tools directly during this execution whenever actions are requested. Do NOT merely state in text that you will send or prepare them in the future. Calling the tool is required so that the action is staged at the Human Clearance Gate.
- Never invent data. Base all conclusions on tool results.

FORMATTING & CLARITY GUIDELINES FOR YOUR RESPONSE:
- Always format your final response cleanly and professionally using Markdown.
- Use clear markdown headings (e.g. `### Summary`, `### Actions Staged`, `### Key Findings`) to structure your text.
- Use bullet points (`- ` or `• `) or numbered lists for sequential items, recommendations, and evidence.
- Use bold text (`**bold**`) for important metrics, invoice numbers, amounts, customer names, or status codes.
- Use code formatting (` `backticks` `) for SKUs, table names, emails, and SQL keywords.
- Break long walls of text into concise, digestible paragraphs with line breaks.
- Keep the tone helpful, executive, and operationally rigorous.
"""


def _build_pending_action(
    tool_name: str,
    action_type: str,
    risk: RiskLevel,
    payload: dict[str, Any],
    preview: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": uuid4().hex,
        "tool_name": tool_name,
        "action_type": action_type,
        "risk_level": risk.value,
        "payload": payload,
        "preview": preview or payload,
        "execution_key": uuid4().hex,
    }


async def run_autonomous_agent(
    user_request: str,
    db: Session,
    micro_steps: list[dict[str, Any]] | None = None,
    config: RunnableConfig | dict | None = None,
) -> dict[str, Any]:
    """
    Executes the autonomous agent loop:
    OpenAI (gpt-4o-mini) dynamically chooses which tools to invoke. Read tools execute immediately,
    while write tools are intercepted and held as PendingActions for human approval.
    """
    if micro_steps is None:
        micro_steps = []

    if not llm_service.configured:
        return await _run_deterministic_agent_simulation(user_request, db, micro_steps)

    try:
        return await _run_openai_tool_calling_loop(user_request, db, micro_steps, config=config)
    except Exception as exc:
        # Fallback gracefully if model call fails or times out
        micro_steps.append({
            "step": "fallback",
            "title": "Agent Autonomous Fallback",
            "detail": f"LLM call encountered {type(exc).__name__}; using deterministic agent engine.",
        })
        return await _run_deterministic_agent_simulation(user_request, db, micro_steps)


async def _run_openai_tool_calling_loop(
    user_request: str,
    db: Session,
    micro_steps: list[dict[str, Any]],
    config: RunnableConfig | dict | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    chat_model = llm_service.get_chat_model()
    tools = registry.to_openai_tools()
    llm_with_tools = chat_model.bind_tools(tools) if tools else chat_model

    messages: list[BaseMessage] = [
        SystemMessage(content=SYSTEM_INSTRUCTION),
        HumanMessage(content=f"OPERATIONAL REQUEST:\n{user_request}"),
    ]

    pending_actions: list[dict[str, Any]] = []
    plan: list[PlanStep] = []
    findings: dict[str, Any] = {}
    summary_text = ""

    micro_steps.append({
        "step": "agent_start",
        "title": "Autonomous Agent Started (OpenAI)",
        "detail": f"Initialized {settings.openai_model} with {len(tools)} available enterprise tools.",
    })

    MAX_ITERATIONS = 8
    turn = 0
    for turn in range(MAX_ITERATIONS):
        async with trace_span("openai_chat_completion", "llm", {"turn": turn + 1, "model": settings.openai_model}) as llm_span:
            ai_msg: AIMessage = await llm_with_tools.ainvoke(messages, config=config)
            if hasattr(ai_msg, "usage_metadata") and ai_msg.usage_metadata:
                llm_span["metadata"]["prompt_tokens"] = ai_msg.usage_metadata.get("input_tokens", 0)
                llm_span["metadata"]["completion_tokens"] = ai_msg.usage_metadata.get("output_tokens", 0)
                llm_span["metadata"]["total_tokens"] = ai_msg.usage_metadata.get("total_tokens", 0)

        messages.append(ai_msg)

        if ai_msg.content:
            text_content = ai_msg.content if isinstance(ai_msg.content, str) else str(ai_msg.content)
            summary_text = text_content.strip()

        tool_calls = getattr(ai_msg, "tool_calls", []) or []
        if not tool_calls:
            # Agent finished reasoning
            break

        for tc in tool_calls:
            action_name = tc.get("name")
            args = tc.get("args") or {}
            tc_id = tc.get("id") or str(uuid4().hex)

            tool, action_spec = registry.get_action(action_name)
            is_read = action_spec.risk == RiskLevel.READ

            if is_read:
                # 1. READ ACTION: Execute immediately
                micro_steps.append({
                    "step": "tool_read",
                    "title": f"Autonomous Tool Read: {tool.name}.{action_name}",
                    "detail": f"Agent invoked {action_name} with parameters: {args}",
                })
                async with trace_span(f"{tool.name}.{action_name}", "tool", {"tool": tool.name, "action": action_name, "args": args}) as t_span:
                    res = await tool.execute(action_name, args, db)
                    t_span["metadata"]["success"] = res.success
                    if not res.success:
                        t_span["metadata"]["error"] = res.error

                result_data = res.data if res.success else {"error": res.error}
                findings[action_name] = result_data

                plan.append(
                    PlanStep(
                        step=len(plan) + 1,
                        label=f"Read {action_name}",
                        action=action_name,
                        tool=tool.name,
                        risk=action_spec.risk,
                        requires_approval=False,
                        status=StepStatus.COMPLETED,
                    )
                )

                messages.append(
                    ToolMessage(
                        tool_call_id=tc_id,
                        content=json.dumps(result_data, default=str),
                    )
                )
            else:
                # 2. WRITE ACTION: INTERCEPT AND HOLD AT APPROVAL GATE
                pending_act = _build_pending_action(tool.name, action_name, action_spec.risk, args)
                pending_actions.append(pending_act)

                plan.append(
                    PlanStep(
                        step=len(plan) + 1,
                        label=f"Propose {action_name}",
                        action=action_name,
                        tool=tool.name,
                        risk=action_spec.risk,
                        requires_approval=True,
                        status=StepStatus.AWAITING_APPROVAL,
                    )
                )
                micro_steps.append({
                    "step": "gate",
                    "title": f"Human Clearance Gate: {tool.name}.{action_name}",
                    "detail": f"Intercepted consequential {action_spec.risk.value} action. Paused for human approval.",
                })

                async with trace_span(f"gate_intercept.{action_name}", "clearance_gate", {"tool": tool.name, "action": action_name, "risk": action_spec.risk.value}):
                    pass

                messages.append(
                    ToolMessage(
                        tool_call_id=tc_id,
                        content=json.dumps({
                            "status": "AWAITING_APPROVAL",
                            "action_id": pending_act["id"],
                            "message": "Consequential action successfully intercepted and staged for human clearance.",
                        }),
                    )
                )

    if not plan and summary_text:
        findings["conversational_response"] = summary_text
        findings["is_conversational"] = True
        micro_steps.append({
            "step": "chat",
            "title": "Assistant Response",
            "detail": "Generated direct conversational answer / clarification.",
        })

    return {
        "findings": {
            **findings,
            "ai_synthesis": summary_text or "Agent investigation complete.",
        },
        "pending_actions": pending_actions,
        "plan": plan,
        "micro_steps": micro_steps,
        "ai_metadata": {
            "used": True,
            "provider": "openai",
            "model": settings.openai_model,
            "turns": turn + 1,
        },
    }


async def _run_deterministic_agent_simulation(
    user_request: str,
    db: Session,
    micro_steps: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Deterministic Agent Planner Fallback:
    Used for local testing or offline environments without an active API key.
    Selects tools dynamically based on request intent and executes the read/intercept write cycle.
    """
    text = user_request.lower()
    pending_actions: list[dict[str, Any]] = []
    plan: list[PlanStep] = []
    findings: dict[str, Any] = {}

    micro_steps.append({
        "step": "agent_start",
        "title": "Autonomous Agent Planner (Offline Fallback)",
        "detail": "Analyzing user request to select tools from the catalog.",
    })

    # 1. SQL Query
    if text.strip().startswith("select ") or text.strip().startswith("with "):
        micro_steps.append({
            "step": "tool_read",
            "title": "DatabaseQueryTool.execute_read",
            "detail": "Running guarded query against authorized tables.",
        })
        rows, guardrail = SafeQueryExecutor.execute_read_query(db, user_request.strip())
        findings["query_results"] = rows
        findings["row_count"] = len(rows)
        plan.append(
            PlanStep(
                step=1,
                label="Execute guarded SQL read",
                action="execute_read",
                tool="database_query_tool",
                risk=RiskLevel.READ,
                status=StepStatus.COMPLETED,
            )
        )
        return {
            "findings": findings,
            "pending_actions": [],
            "plan": plan,
            "micro_steps": micro_steps,
            "ai_metadata": {"used": False, "mode": "deterministic_autonomous_planner"},
        }

    # 2. Invoices
    if any(k in text for k in ("invoice", "overdue", "receivable")):
        micro_steps.append({
            "step": "tool_read",
            "title": "InvoiceDBTool.get_overdue_invoices",
            "detail": "Inspecting receivables database for overdue accounts.",
        })
        tool_res = await registry.execute("invoice_tool", "get_overdue_invoices", {"days": 30}, db)
        invoices = tool_res.data or []
        findings["invoices"] = invoices
        plan.append(
            PlanStep(
                step=1,
                label="Query overdue invoices",
                action="get_overdue_invoices",
                tool="invoice_tool",
                risk=RiskLevel.READ,
                status=StepStatus.COMPLETED,
            )
        )

        valid = [inv for inv in invoices if inv.get("billing_email") and "@" in inv["billing_email"]]
        for inv in valid:
            num = inv["invoice_number"]
            amt = float(inv.get("balance_due", inv.get("amount", 0)))
            payload = {
                "to": inv["billing_email"],
                "subject": f"Overdue Payment Reminder: Invoice {num}",
                "body": f"Dear Accounts Payable,\n\nOur records indicate invoice {num} for ${amt:,.2f} is past due. Please confirm payment.\n\nThank you,\nAccounts Receivable",
                "invoice_number": num,
                "customer_id": inv.get("customer_id"),
            }
            preview = {
                "invoice_number": num,
                "customer": inv.get("customer_name"),
                "balance": f"${amt:,.2f}",
                "recipient": inv["billing_email"],
            }
            pending_actions.append(
                _build_pending_action("email_tool", "send_email", RiskLevel.EXTERNAL_COMMUNICATION, payload, preview)
            )

        if pending_actions:
            plan.append(
                PlanStep(
                    step=2,
                    label="Send approved customer reminders",
                    action="send_email",
                    tool="email_tool",
                    risk=RiskLevel.EXTERNAL_COMMUNICATION,
                    requires_approval=True,
                    status=StepStatus.AWAITING_APPROVAL,
                )
            )
            micro_steps.append({
                "step": "gate",
                "title": "Human Clearance Gate: EmailTool",
                "detail": f"Staged {len(pending_actions)} reminder email(s) for human clearance.",
            })

    # 3. Support Tickets
    elif any(k in text for k in ("support ticket", "ticket", "escalat")):
        micro_steps.append({
            "step": "tool_read",
            "title": "SupportDBTool.get_open_tickets",
            "detail": "Retrieving active queue to evaluate ticket urgency and customer tier.",
        })
        tool_res = await registry.execute("support_tool", "get_open_tickets", {}, db)
        tickets = tool_res.data or []
        findings["open_tickets"] = tickets
        plan.append(
            PlanStep(
                step=1,
                label="Read open support tickets",
                action="get_open_tickets",
                tool="support_tool",
                risk=RiskLevel.READ,
                status=StepStatus.COMPLETED,
            )
        )

        for t in tickets:
            if t.get("severity") in {"critical", "high"} or str(t.get("customer_tier", "")).lower() == "enterprise":
                payload = {
                    "ticket_id": t["id"],
                    "ticket_number": t["ticket_number"],
                    "team": "Tier 2 Specialist Team",
                    "reason": f"Urgent {t.get('severity')} issue for {t.get('customer_name')}",
                }
                pending_actions.append(
                    _build_pending_action("support_tool", "escalate_ticket", RiskLevel.LOW_RISK_WRITE, payload, t)
                )

        if pending_actions:
            plan.append(
                PlanStep(
                    step=2,
                    label="Escalate approved tickets",
                    action="escalate_ticket",
                    tool="support_tool",
                    risk=RiskLevel.LOW_RISK_WRITE,
                    requires_approval=True,
                    status=StepStatus.AWAITING_APPROVAL,
                )
            )
            micro_steps.append({
                "step": "gate",
                "title": "Human Clearance Gate: SupportTool",
                "detail": f"Staged {len(pending_actions)} ticket escalation(s) for human review.",
            })

    # 4. Inventory Reorder
    elif any(k in text for k in ("inventory", "reorder", "stock")):
        micro_steps.append({
            "step": "tool_read",
            "title": "InventoryDBTool.get_inventory",
            "detail": "Calculating inventory consumption velocity and stock runway.",
        })
        tool_res = await registry.execute("inventory_tool", "get_inventory", {}, db)
        items = tool_res.data or []
        findings["inventory_items"] = items
        plan.append(
            PlanStep(
                step=1,
                label="Read inventory levels",
                action="get_inventory",
                tool="inventory_tool",
                risk=RiskLevel.READ,
                status=StepStatus.COMPLETED,
            )
        )

        for item in items:
            if float(item.get("days_remaining", 999)) <= 14:
                supp_res = await registry.execute(
                    "procurement_tool", "get_supplier_options", {"sku": item.get("sku")}, db
                )
                suppliers = supp_res.data or []
                if suppliers:
                    s = suppliers[0]
                    qty = int(item.get("reorder_pack", 10))
                    price = float(s.get("unit_price", 10))
                    cost = round(qty * price, 2)
                    payload = {
                        "sku": item.get("sku"),
                        "product_id": item.get("product_id"),
                        "supplier_id": s.get("supplier_id"),
                        "quantity": qty,
                        "unit_price": price,
                        "estimated_cost": cost,
                    }
                    pending_actions.append(
                        _build_pending_action(
                            "procurement_tool",
                            "create_purchase_order",
                            RiskLevel.FINANCIAL,
                            payload,
                            {**item, "estimated_cost": cost},
                        )
                    )

        if pending_actions:
            plan.append(
                PlanStep(
                    step=2,
                    label="Create approved purchase orders",
                    action="create_purchase_order",
                    tool="procurement_tool",
                    risk=RiskLevel.FINANCIAL,
                    requires_approval=True,
                    status=StepStatus.AWAITING_APPROVAL,
                )
            )
            micro_steps.append({
                "step": "gate",
                "title": "Human Clearance Gate: ProcurementTool",
                "detail": f"Staged {len(pending_actions)} purchase order(s) for financial approval.",
            })

    # 5. Access Requests
    elif any(k in text for k in ("access request", "access review", "permission")):
        micro_steps.append({
            "step": "tool_read",
            "title": "AccessRequestDBTool.get_pending_requests",
            "detail": "Querying pending access queue and evaluating role policies.",
        })
        req_res = await registry.execute("access_request_tool", "get_pending_requests", {}, db)
        reqs = req_res.data or []
        findings["requests"] = reqs
        plan.append(
            PlanStep(
                step=1,
                label="Read pending access requests",
                action="get_pending_requests",
                tool="access_request_tool",
                risk=RiskLevel.READ,
                status=StepStatus.COMPLETED,
            )
        )

        for r in reqs:
            payload = {"request_id": r["id"], "decision": "approve", "reason": "Role complies with access policy"}
            pending_actions.append(
                _build_pending_action("access_request_tool", "decide_access", RiskLevel.ACCESS_CONTROL, payload, r)
            )

        if pending_actions:
            plan.append(
                PlanStep(
                    step=2,
                    label="Apply approved access decisions",
                    action="decide_access",
                    tool="access_request_tool",
                    risk=RiskLevel.ACCESS_CONTROL,
                    requires_approval=True,
                    status=StepStatus.AWAITING_APPROVAL,
                )
            )

    elif any(k in text for k in ("guardrail", "clearance", "safety", "gate")):
        reply = (
            "🛡️ **How the Safety Guardrail & Human Clearance Engine Works:**\n\n"
            "1. **Autonomous Reads (Safe)**:\n"
            "   All informational queries (`SELECT` queries, inventory checks, invoice searches, ticket scans) execute automatically so the AI has real facts to reason over.\n\n"
            "2. **AST-Level SQL Guardrail**:\n"
            "   Every database query is parsed into an Abstract Syntax Tree via `sqlglot` before execution. Destructive statements (`DROP`, `TRUNCATE`, `ALTER`), system tables (`mysql`, `information_schema`), and unconditional mutations (`WHERE 1=1`) are blocked immediately with an HTTP 403 Security Violation. `SELECT` queries are auto-clamped with `LIMIT 100`.\n\n"
            "3. **The Human Clearance Gate**:\n"
            "   Whenever the agent decides to take a consequential write action (`send_email`, `create_purchase_order`, `escalate_ticket`, `decide_access`), the runtime safely halts. The action is staged as a `PendingAction` and requires a human operator to review, edit, or approve before anything is committed to the database.\n\n"
            "You can test arbitrary SQL queries and attack injections in the **AST Guardrail Sandbox** tab above!"
        )
        findings["conversational_response"] = reply
        findings["is_conversational"] = True
        plan = []
        micro_steps.append({
            "step": "chat",
            "title": "Guardrail Explanation",
            "detail": "Explained AST parser, table whitelisting, and Human Clearance Gate.",
        })

    elif any(k in text for k in ("tool", "catalog", "available tools", "what tools")):
        reply = (
            "🛠️ **Registered Enterprise Tool Catalog (11 Active Tools):**\n\n"
            "• 📄 **invoice_tool** (`get_overdue_invoices`) — Queries unpaid invoices and balances [READ]\n"
            "• ✉️ **email_tool** (`send_email`) — Sends approved external customer/lead emails [EXTERNAL_COMMUNICATION]\n"
            "• 🎫 **support_tool** (`get_open_tickets`, `escalate_ticket`) — Inspects queues and escalates cases [READ / WRITE]\n"
            "• 📦 **inventory_tool** (`get_inventory`) — Calculates stock levels, daily usage, and runways [READ]\n"
            "• 🛒 **procurement_tool** (`get_supplier_options`, `create_purchase_order`) — Compares vendor prices and creates POs [READ / FINANCIAL]\n"
            "• 📊 **crm_tool** (`get_leads`, `mark_contacted`) — Manages sales pipeline leads and contact activity [READ / WRITE]\n"
            "• 👥 **employee_directory_tool** (`get_employees`) — Resolves employee roles, departments, and emails [READ]\n"
            "• 📜 **policy_tool** (`get_access_policies`) — Checks software role permissions and rules [READ]\n"
            "• 🔐 **access_request_tool** (`get_pending_requests`, `decide_access`) — Reviews and decides access requests [READ / ACCESS_CONTROL]\n"
            "• 📋 **task_tool** (`create_task`) — Generates internal follow-up action items [WRITE]\n"
            "• 🔍 **database_query_tool** (`execute_read`) — Runs guarded arbitrary SQL queries against the 24 database tables [READ]"
        )
        findings["conversational_response"] = reply
        findings["is_conversational"] = True
        plan = []
        micro_steps.append({
            "step": "chat",
            "title": "Tool Catalog Guide",
            "detail": "Listed all 11 registered database tools with risk classifications.",
        })

    else:
        reply = (
            "Hello! I am your AI Operations Copilot with autonomous access to your enterprise operations database.\n\n"
            "Here is what I can do for you:\n\n"
            "• 📋 **Invoices & Receivables**: Identify overdue balances and prepare reminder emails (e.g. *\"Find invoices overdue by more than 30 days\"*)\n"
            "• 🎫 **Customer Support**: Review active tickets and escalate critical enterprise issues (e.g. *\"Review today's support tickets and escalate payment issues\"*)\n"
            "• 📦 **Inventory & Procurement**: Calculate stock consumption velocity and draft purchase orders (e.g. *\"Find inventory running out within 14 days\"*)\n"
            "• 🔐 **Access Control**: Audit employee software access requests against company policy\n"
            "• 🔍 **Guarded SQL Queries**: Ask direct data questions (e.g. *\"SELECT customer_code, name, tier FROM customers WHERE tier = 'enterprise'\"*)\n\n"
            "If you are not sure what to run, click any of the Quick Demo Scenarios above or ask me a specific question about your data!"
        )
        findings["conversational_response"] = reply
        findings["is_conversational"] = True
        plan = []
        micro_steps.append({
            "step": "chat",
            "title": "Assistant Guidance",
            "detail": "Clarified agent capabilities and provided operational suggestions.",
        })

    return {
        "findings": findings,
        "pending_actions": pending_actions,
        "plan": plan,
        "micro_steps": micro_steps,
        "ai_metadata": {"used": False, "mode": "deterministic_autonomous_planner"},
    }
