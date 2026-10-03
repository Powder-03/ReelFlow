from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.intelligence import intelligence_node
from app.agents.memory import memory_node
from app.agents.strategy import strategy_node
from app.agents.guardrails_node import guardrails_node
from app.agents.writer import writer_node
from app.agents.critic import critic_node
from app.agents.feedback import feedback_node

def route_after_guardrails(state: AgentState) -> str:
    """Route after guardrails check.
    - PASS (normal or historical auto-pick fallback) -> 'writer'
    - FAIL (retry_count < 2) -> 'strategy' (re-prompt LLM)
    """
    guardrail_result = state.get("guardrail_result", {})
    if guardrail_result.get("passed", False):
        return "writer"
    return "strategy"

def route_after_critic(state: AgentState) -> str:
    """Route after critic evaluation.
    - Score >= 8.5/10 (pass_threshold=True) -> 'feedback'
    - Score < 8.5/10 and rewrites < 3 -> 'writer' (rewrite loop)
    - Score < 8.5/10 and rewrites >= 3 -> 'feedback' (finish with best_script)
    """
    eval_data = state.get("evaluation", {})
    if eval_data.get("pass_threshold", False):
        return "feedback"
    
    rewrite_count = state.get("rewrite_count", 0)
    max_rewrites = state.get("max_rewrites", 3)
    if rewrite_count < max_rewrites:
        return "writer"
    
    return "feedback"

def build_growth_brain_graph() -> StateGraph:
    """Compiles the LangGraph Multi-Agent Instagram Growth Brain workflow."""
    workflow = StateGraph(AgentState)

    # Register all agent and deterministic nodes
    workflow.add_node("intelligence", intelligence_node)
    workflow.add_node("memory", memory_node)
    workflow.add_node("strategy", strategy_node)
    workflow.add_node("guardrails", guardrails_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("feedback", feedback_node)

    # Define entry and sequential transitions
    workflow.set_entry_point("intelligence")
    workflow.add_edge("intelligence", "memory")
    workflow.add_edge("memory", "strategy")
    workflow.add_edge("strategy", "guardrails")

    # Conditional routing after guardrails: bounded retry
    workflow.add_conditional_edges(
        "guardrails",
        route_after_guardrails,
        {
            "writer": "writer",
            "strategy": "strategy",
        }
    )

    workflow.add_edge("writer", "critic")

    # Conditional routing after critic: rewrite loop or finish
    workflow.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "writer": "writer",
            "feedback": "feedback",
        }
    )

    workflow.add_edge("feedback", END)

    return workflow.compile()
