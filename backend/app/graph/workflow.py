from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph_observe import observe_graph

from app.agents.request_analyzer import analyze_request
from app.core.config import get_settings
from app.core.tracing import trace_span
from app.db.guardrails import RiskLevel
from app.graph.state import OperationsState
from app.models.schemas import PlanStep, StepStatus
from app.services.agent_loop import (
    SYSTEM_INSTRUCTION,
    _build_pending_action,
    _run_deterministic_agent_simulation,
)
from app.services.llm_service import llm_service
from app.tools.registry import registry


async def analyze_node(state: OperationsState, config: RunnableConfig) -> dict[str, Any]:
    async with trace_span("langgraph.node.analyze", "langgraph", {"node": "analyze", "graph": "operations_graph"}) as s:
        is_cont = state.get("is_continuation", False)
        if is_cont:
            pending_actions = list(state.get("pending_actions", []))
            plan = list(state.get("plan", []))
            findings = dict(state.get("findings", {}))
            micro = list(state.get("micro_steps", []))
            micro.append({
                "step": "continuation",
                "title": "Human Operator Instruction",
                "detail": f"Received operator instruction: '{state['user_request']}'. Processing against {len(pending_actions)} staged action(s).",
            })

            staged_lines = []
            for i, act in enumerate(pending_actions, start=1):
                staged_lines.append(
                    f"Action #{i} [ID: {act.get('id')}]: {act.get('tool_name')}.{act.get('action_type')} - Payload: {json.dumps(act.get('payload', {}), default=str)}"
                )
            staged_str = "\n".join(staged_lines) if staged_lines else "None currently staged."

            operator_prompt = (
                f"OPERATOR FOLLOW-UP INSTRUCTION:\n{state['user_request']}\n\n"
                f"CURRENT STAGED ACTIONS AT HUMAN CLEARANCE GATE:\n{staged_str}\n\n"
                f"INSTRUCTIONS:\n"
                f"- If the operator wants to modify/edit a staged action, call `update_staged_action` with `action_id` (the ID or index like '1') and `updates` dict.\n"
                f"- If the operator wants to remove/cancel an action, call `remove_staged_action` with `action_id` and `reason`.\n"
                f"- If the operator wants to add new actions (e.g. another email, ticket, invoice, or purchase order), call the appropriate tool.\n"
                f"- If the operator says to send, dispatch, or approve everything (e.g. 'send them out', 'looks good send'), call `approve_and_dispatch_all`.\n"
                f"- Call read tools if you need more data from the system first."
            )

            existing_messages = list(state.get("messages", []))
            if not existing_messages:
                existing_messages = [SystemMessage(content=SYSTEM_INSTRUCTION)]
            existing_messages.append(HumanMessage(content=operator_prompt))

            return {
                "micro_steps": micro,
                "messages": existing_messages,
                "retry_count": 0,
                "tool_turns": 0,
                "validation_errors": [],
                "pending_actions": pending_actions,
                "plan": plan,
                "findings": findings,
                "dispatch_all_requested": False,
            }

        analysis, metadata = await analyze_request(state["user_request"], config=config)
        s["metadata"]["workflow_type"] = analysis.workflow_type.value
        s["metadata"]["parameters"] = analysis.parameters
        micro = list(state.get("micro_steps", []))
        micro.append({
            "step": "analyze",
            "title": "Intent Analysis",
            "detail": f"Request analyzed: '{analysis.workflow_type.value}'. Handing off to Autonomous Agent Loop.",
        })

        initial_messages = [
            SystemMessage(content=SYSTEM_INSTRUCTION),
            HumanMessage(content=f"OPERATIONAL REQUEST:\n{state['user_request']}"),
        ]

        return {
            "analysis": analysis,
            "ai_metadata": metadata,
            "errors": [],
            "micro_steps": micro,
            "messages": initial_messages,
            "retry_count": 0,
            "tool_turns": 0,
            "validation_errors": [],
            "pending_actions": [],
            "plan": [],
            "findings": {},
            "dispatch_all_requested": False,
        }


async def agent_reasoning_node(state: OperationsState, config: RunnableConfig) -> dict[str, Any]:
    async with trace_span("langgraph.node.agent", "langgraph", {"node": "agent", "graph": "operations_graph"}) as s:
        settings = get_settings()
        micro = list(state.get("micro_steps", []))
        tool_turns = state.get("tool_turns", 0)

        # 1. Fallback if LLM is not configured (e.g. offline testing)
        if not llm_service.configured:
            if state.get("is_continuation"):
                user_req = state.get("user_request", "").lower()
                pending_actions = list(state.get("pending_actions", []))
                dispatch = False
                import re

                if any(w in user_req for w in ["send", "dispatch", "approve"]):
                    dispatch = True
                    resp_text = f"Simulated dispatch of {len(pending_actions)} staged action(s) as instructed."
                elif any(w in user_req for w in ["remove", "cancel", "delete"]):
                    if pending_actions:
                        pending_actions.pop()
                    resp_text = f"Simulated removal of staged action. {len(pending_actions)} action(s) remain."
                elif any(w in user_req for w in ["update", "change", "edit", "discount", "recipient", "to:"]):
                    if pending_actions:
                        email_m = re.search(r"[\w\.-]+@[\w\.-]+", state.get("user_request", ""))
                        if email_m:
                            pending_actions[0].setdefault("payload", {})["to"] = email_m.group(0)
                        num_m = re.search(r"\$?(\d+(?:\.\d+)?)", state.get("user_request", ""))
                        if num_m and "discount" in user_req:
                            pending_actions[0].setdefault("payload", {})["discount"] = float(num_m.group(1))
                    resp_text = "Simulated update of staged action payload."
                else:
                    resp_text = f"Simulated response to operator instruction: {state.get('user_request')}"

                return {
                    "pending_actions": pending_actions,
                    "dispatch_all_requested": dispatch,
                    "messages": [AIMessage(content=resp_text)],
                    "findings": {
                        **state.get("findings", {}),
                        "ai_synthesis": resp_text,
                    },
                }

            sim_res = await _run_deterministic_agent_simulation(
                user_request=state["user_request"],
                db=state["db"],
                micro_steps=micro,
            )
            findings = sim_res.get("findings", {})
            summary = findings.get("ai_synthesis") or findings.get("conversational_response") or "Analysis complete."
            return {
                "findings": findings,
                "pending_actions": sim_res.get("pending_actions", []),
                "plan": sim_res.get("plan", []),
                "micro_steps": sim_res.get("micro_steps", micro),
                "ai_metadata": sim_res.get("ai_metadata", {"used": False}),
                "messages": [AIMessage(content=summary)],
            }

        # 2. Hard iteration limit check inside the agent loop
        MAX_TOOL_TURNS = 8
        if tool_turns >= MAX_TOOL_TURNS:
            summary_msg = AIMessage(
                content="Maximum reasoning turns reached. Consolidating findings and proceeding to validation."
            )
            return {
                "messages": [summary_msg],
                "findings": {
                    **state.get("findings", {}),
                    "ai_synthesis": summary_msg.content,
                },
            }

        # 3. Standard Chat Model invocation
        chat_model = llm_service.get_chat_model()
        tools = registry.to_openai_tools()
        llm_with_tools = chat_model.bind_tools(tools) if tools else chat_model

        async with trace_span("openai_chat_completion", "llm", {"turn": tool_turns + 1, "model": settings.openai_model}) as llm_span:
            ai_msg: AIMessage = await llm_with_tools.ainvoke(state.get("messages", []), config=config)
            if hasattr(ai_msg, "usage_metadata") and ai_msg.usage_metadata:
                llm_span["metadata"]["prompt_tokens"] = ai_msg.usage_metadata.get("input_tokens", 0)
                llm_span["metadata"]["completion_tokens"] = ai_msg.usage_metadata.get("output_tokens", 0)
                llm_span["metadata"]["total_tokens"] = ai_msg.usage_metadata.get("total_tokens", 0)

        summary_text = ""
        if ai_msg.content:
            summary_text = str(ai_msg.content).strip()

        findings = dict(state.get("findings", {}))
        tool_calls = getattr(ai_msg, "tool_calls", []) or []

        if not tool_calls:
            # Reasoning concluded
            if not state.get("plan") and summary_text:
                findings["conversational_response"] = summary_text
                findings["is_conversational"] = True
                micro.append({
                    "step": "chat",
                    "title": "Assistant Response",
                    "detail": "Generated direct conversational answer / clarification.",
                })
            findings["ai_synthesis"] = summary_text or "Agent investigation complete."
        else:
            micro.append({
                "step": "agent_reason",
                "title": "Agent Reasoning",
                "detail": f"Agent selected {len(tool_calls)} tool action(s) to dispatch.",
            })

        return {
            "messages": [ai_msg],
            "findings": findings,
            "micro_steps": micro,
            "ai_metadata": {
                "used": True,
                "provider": "openai",
                "model": settings.openai_model,
                "turns": tool_turns + 1,
            },
        }


async def tool_dispatcher_node(state: OperationsState, config: RunnableConfig) -> dict[str, Any]:
    async with trace_span("langgraph.node.tools", "langgraph", {"node": "tools", "graph": "operations_graph"}) as s:
        messages = state.get("messages", [])
        last_msg = messages[-1] if messages else None
        tool_calls = getattr(last_msg, "tool_calls", []) or []

        pending_actions = list(state.get("pending_actions", []))
        plan = list(state.get("plan", []))
        findings = dict(state.get("findings", {}))
        micro = list(state.get("micro_steps", []))
        tool_messages = []
        dispatch_all_requested = state.get("dispatch_all_requested", False)

        for tc in tool_calls:
            action_name = tc.get("name")
            args = tc.get("args") or {}
            tc_id = tc.get("id") or str(uuid4().hex)

            if action_name == "update_staged_action":
                target_id = str(args.get("action_id", "")).strip()
                updates = args.get("updates", {})
                updated_action = None

                for act in pending_actions:
                    if (
                        str(act.get("id")) == target_id
                        or (target_id.isdigit() and pending_actions.index(act) == int(target_id) - 1)
                        or (target_id.startswith("#") and target_id[1:].isdigit() and pending_actions.index(act) == int(target_id[1:]) - 1)
                        or target_id.lower() in str(act.get("id")).lower()
                    ):
                        act.setdefault("payload", {})
                        act["payload"].update(updates)
                        act.setdefault("preview", {})
                        act["preview"].update(updates)
                        updated_action = act
                        break

                if not updated_action and pending_actions:
                    for act in pending_actions:
                        if target_id.lower() in act.get("action_type", "").lower():
                            act["payload"].update(updates)
                            act["preview"].update(updates)
                            updated_action = act
                            break
                    if not updated_action:
                        pending_actions[0]["payload"].update(updates)
                        pending_actions[0]["preview"].update(updates)
                        updated_action = pending_actions[0]

                micro.append({
                    "step": "tool_staging",
                    "title": f"Staged Action Mutated: {target_id}",
                    "detail": f"Updated staged action parameters: {updates}",
                })
                tool_messages.append(
                    ToolMessage(
                        tool_call_id=tc_id,
                        content=json.dumps({
                            "status": "UPDATED" if updated_action else "NOT_FOUND",
                            "action_id": target_id,
                            "updated_action": updated_action,
                        }, default=str),
                    )
                )
                continue

            elif action_name == "remove_staged_action":
                target_id = str(args.get("action_id", "")).strip()
                reason = args.get("reason", "Removed by operator")
                removed = None
                for idx, act in enumerate(pending_actions):
                    if (
                        str(act.get("id")) == target_id
                        or (target_id.isdigit() and idx == int(target_id) - 1)
                        or (target_id.startswith("#") and target_id[1:].isdigit() and idx == int(target_id[1:]) - 1)
                        or target_id.lower() in act.get("action_type", "").lower()
                    ):
                        removed = pending_actions.pop(idx)
                        break

                micro.append({
                    "step": "tool_staging",
                    "title": f"Staged Action Removed: {target_id}",
                    "detail": f"Removed action from clearance gate: {reason}",
                })
                tool_messages.append(
                    ToolMessage(
                        tool_call_id=tc_id,
                        content=json.dumps({
                            "status": "REMOVED" if removed else "NOT_FOUND",
                            "action_id": target_id,
                            "reason": reason,
                        }),
                    )
                )
                continue

            elif action_name == "approve_and_dispatch_all":
                dispatch_all_requested = True
                reason = args.get("reason", "Operator requested dispatch")
                micro.append({
                    "step": "dispatch_requested",
                    "title": "Dispatch Authorized",
                    "detail": f"Operator authorized dispatch of all staged actions: {reason}",
                })
                tool_messages.append(
                    ToolMessage(
                        tool_call_id=tc_id,
                        content=json.dumps({
                            "status": "DISPATCH_AUTHORIZED",
                            "count": len(pending_actions),
                            "reason": reason,
                        }),
                    )
                )
                continue

            tool, action_spec = registry.get_action(action_name)
            is_read = action_spec.risk == RiskLevel.READ

            if is_read:
                # 1. READ ACTION: Execute immediately
                micro.append({
                    "step": "tool_read",
                    "title": f"Autonomous Tool Read: {tool.name}.{action_name}",
                    "detail": f"Agent invoked {action_name} with parameters: {args}",
                })
                async with trace_span(f"{tool.name}.{action_name}", "tool", {"tool": tool.name, "action": action_name, "args": args}) as t_span:
                    res = await tool.execute(action_name, args, state["db"])
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

                tool_messages.append(
                    ToolMessage(
                        tool_call_id=tc_id,
                        content=json.dumps(result_data, default=str),
                    )
                )
            else:
                # 2. WRITE ACTION: Intercept and stage at clearance gate
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
                micro.append({
                    "step": "gate",
                    "title": f"Human Clearance Gate: {tool.name}.{action_name}",
                    "detail": f"Intercepted consequential {action_spec.risk.value} action. Paused for human approval.",
                })

                async with trace_span(f"gate_intercept.{action_name}", "clearance_gate", {"tool": tool.name, "action": action_name, "risk": action_spec.risk.value}):
                    pass

                tool_messages.append(
                    ToolMessage(
                        tool_call_id=tc_id,
                        content=json.dumps({
                            "status": "AWAITING_APPROVAL",
                            "action_id": pending_act["id"],
                            "message": "Consequential action successfully intercepted and staged for human clearance.",
                        }),
                    )
                )

        new_tool_turns = state.get("tool_turns", 0) + 1
        s["metadata"]["dispatched_tool_calls"] = len(tool_calls)
        s["metadata"]["turn"] = new_tool_turns

        return {
            "messages": tool_messages,
            "pending_actions": pending_actions,
            "plan": plan,
            "findings": findings,
            "micro_steps": micro,
            "tool_turns": new_tool_turns,
            "dispatch_all_requested": dispatch_all_requested,
        }


async def policy_validator_node(state: OperationsState, config: RunnableConfig) -> dict[str, Any]:
    async with trace_span("langgraph.node.validate", "langgraph", {"node": "validate", "graph": "operations_graph"}) as s:
        pending_actions = state.get("pending_actions", [])
        validation_errors: list[str] = []
        validation_results: list[dict[str, Any]] = []

        # Validate staged pending actions against deterministic guardrail rules
        for act in pending_actions:
            action_type = act.get("action_type")
            payload = act.get("payload", {})
            act_id = act.get("id")

            # Rule 1: Email recipient deliverability check
            if action_type == "send_email":
                to_addr = str(payload.get("to", "")).strip()
                if not to_addr or "@" not in to_addr or "." not in to_addr.split("@")[-1]:
                    err = f"Invalid email recipient '{to_addr}'. Email address must contain '@' and a valid domain."
                    validation_errors.append(err)
                    validation_results.append({"action_id": act_id, "valid": False, "reason": err})
                    continue

            # Rule 2: Single-order PO spend threshold limit ($10,000)
            if action_type == "create_purchase_order":
                cost = float(payload.get("estimated_cost", 0) or (payload.get("quantity", 0) * payload.get("unit_price", 0)))
                MAX_SINGLE_PO_LIMIT = 10000.0
                if cost > MAX_SINGLE_PO_LIMIT:
                    err = (
                        f"Purchase Order for SKU '{payload.get('sku')}' (${cost:,.2f}) exceeds the single-order "
                        f"approval policy limit (${MAX_SINGLE_PO_LIMIT:,.2f}). Please re-evaluate supplier pricing or split quantities."
                    )
                    validation_errors.append(err)
                    validation_results.append({"action_id": act_id, "valid": False, "reason": err})
                    continue

            # Action passed validation
            validation_results.append({"action_id": act_id, "valid": True})

        micro = list(state.get("micro_steps", []))
        if validation_errors:
            micro.append({
                "step": "validate",
                "title": "Policy & Guardrail Validator",
                "detail": f"Policy violations detected ({len(validation_errors)} error(s)). Triggering reflection cycle.",
            })
        else:
            micro.append({
                "step": "validate",
                "title": "Policy & Guardrail Validator",
                "detail": "All staged actions passed deterministic policy and guardrail checks.",
            })

        s["metadata"]["validation_passed"] = len(validation_errors) == 0
        s["metadata"]["validation_errors_count"] = len(validation_errors)

        return {
            "validation_errors": validation_errors,
            "validation_results": validation_results,
            "micro_steps": micro,
        }


async def format_reflection_feedback_node(state: OperationsState, config: RunnableConfig) -> dict[str, Any]:
    async with trace_span("langgraph.node.self_correct", "langgraph", {"node": "self_correct", "graph": "operations_graph"}) as s:
        retry_count = state.get("retry_count", 0) + 1
        errors = state.get("validation_errors", [])
        err_bullets = "\n".join(f"- {e}" for e in errors)

        feedback_content = (
            f"POLICY & GUARDRAIL VALIDATION FAILURE (Attempt {retry_count} of 2):\n"
            f"The following actions failed deterministic policy compliance rules and were rejected:\n"
            f"{err_bullets}\n\n"
            f"CORRECTIVE INSTRUCTION: Please review the tool observations or call alternative tools "
            f"to correct the parameters, split purchase orders, or eliminate invalid actions so that all staged operations comply."
        )

        micro = list(state.get("micro_steps", []))
        micro.append({
            "step": "reflection",
            "title": "Reflection & Self-Correction",
            "detail": f"Injected corrective feedback into agent message history (Retry {retry_count}/2).",
        })

        # Filter out actions that failed validation so the agent can regenerate compliant ones
        invalid_ids = {r["action_id"] for r in state.get("validation_results", []) if not r.get("valid")}
        cleaned_pending = [a for a in state.get("pending_actions", []) if a.get("id") not in invalid_ids]
        cleaned_plan = [
            p for p in state.get("plan", [])
            if p.action not in {a.get("action_type") for a in state.get("pending_actions", []) if a.get("id") in invalid_ids}
        ]

        s["metadata"]["retry_attempt"] = retry_count
        s["metadata"]["errors_injected"] = len(errors)

        return {
            "messages": [HumanMessage(content=feedback_content)],
            "retry_count": retry_count,
            "validation_errors": [],
            "pending_actions": cleaned_pending,
            "plan": cleaned_plan,
            "micro_steps": micro,
        }


async def finalize_node(state: OperationsState, config: RunnableConfig) -> dict[str, Any]:
    async with trace_span("langgraph.node.finalize", "langgraph", {"node": "finalize", "graph": "operations_graph"}) as s:
        count = len(state.get("pending_actions", []))
        micro = list(state.get("micro_steps", []))
        findings = dict(state.get("findings", {}))
        s["metadata"]["pending_actions"] = count

        if state.get("dispatch_all_requested"):
            summary = f"Operator instruction executed. Authorized dispatch of {count} staged action(s)."
            s["metadata"]["mode"] = "dispatch_authorized"
            return {
                "final_result": {
                    "summary": summary,
                    "is_conversational": False,
                    "pending_count": count,
                    "dispatch_all_requested": True,
                },
                "micro_steps": micro,
                "dispatch_all_requested": True,
            }

        if findings.get("conversational_response"):
            summary = findings["conversational_response"]
            s["metadata"]["mode"] = "conversational_direct"
            return {
                "final_result": {"summary": summary, "is_conversational": True, "pending_count": 0},
                "micro_steps": micro,
            }

        if count:
            summary = f"Autonomous analysis complete. {count} consequential action(s) staged at Human Clearance Gate."
            s["metadata"]["mode"] = "approval_gate_paused"
            micro.append({
                "step": "gate",
                "title": "Human Clearance Gate",
                "detail": f"System paused. Awaiting human operator review for {count} action(s).",
            })
        else:
            summary = (
                findings.get("message")
                or findings.get("ai_synthesis")
                or "Operation completed with zero pending actions."
            )
            s["metadata"]["mode"] = "completed_autonomous"
            micro.append({
                "step": "finalize",
                "title": "Operation Complete",
                "detail": summary,
            })
        return {
            "final_result": {"summary": summary, "is_conversational": False, "pending_count": count},
            "micro_steps": micro,
        }


# 1. Routing functions
def route_agent_output(state: OperationsState) -> str:
    """Decide whether to execute tools or proceed to validation."""
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else None

    if last_msg and getattr(last_msg, "tool_calls", None):
        return "tools"
    return "validate"


def route_validation_output(state: OperationsState) -> str:
    """Loop back to agent if recoverable policy errors exist, else finalize."""
    errors = state.get("validation_errors", [])
    retry_count = state.get("retry_count", 0)

    # 🔁 Self-correction loop: max 2 retries
    if errors and retry_count < 2:
        return "self_correct"
    return "finalize"


# 2. Build the state graph with cycles
builder = StateGraph(OperationsState)

# Nodes
builder.add_node("analyze", analyze_node)
builder.add_node("agent", agent_reasoning_node)
builder.add_node("tools", tool_dispatcher_node)
builder.add_node("validate", policy_validator_node)
builder.add_node("self_correct", format_reflection_feedback_node)
builder.add_node("finalize", finalize_node)

# Edges & Loops
builder.add_edge(START, "analyze")
builder.add_edge("analyze", "agent")

# 🔁 Loop 1: ReAct Tool Calling Cycle
builder.add_conditional_edges(
    "agent",
    route_agent_output,
    {
        "tools": "tools",
        "validate": "validate",
    },
)
builder.add_edge("tools", "agent")  # Back to agent with observations!

# 🔁 Loop 2: Policy Validation & Self-Correction Cycle
builder.add_conditional_edges(
    "validate",
    route_validation_output,
    {
        "self_correct": "self_correct",
        "finalize": "finalize",
    },
)
builder.add_edge("self_correct", "agent")  # Back to agent with error feedback!

builder.add_edge("finalize", END)

# Wrap compiled LangGraph workflow with langgraph-observe universal tracing
_settings = get_settings()
operations_graph = observe_graph(
    builder.compile(),
    name="AIOperationsWorkflow",
    project=_settings.observe_project,
    environment=_settings.observe_environment,
)


