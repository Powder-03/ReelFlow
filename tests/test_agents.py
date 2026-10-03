import pytest
from app.agents.graph import build_growth_brain_graph, route_after_guardrails, route_after_critic
from app.agents.state import AgentState

def test_graph_compilation():
    graph = build_growth_brain_graph()
    assert graph is not None

def test_route_after_guardrails_passed():
    state: AgentState = {
        "guardrail_result": {"passed": True, "violations": []}
    }
    assert route_after_guardrails(state) == "writer"

def test_route_after_guardrails_failed():
    state: AgentState = {
        "guardrail_result": {"passed": False, "violations": ["TOPIC_REPETITION"]}
    }
    assert route_after_guardrails(state) == "strategy"

def test_route_after_critic_passed():
    state: AgentState = {
        "evaluation": {"pass_threshold": True, "overall_score": 0.88},
        "rewrite_count": 1,
        "max_rewrites": 3,
    }
    assert route_after_critic(state) == "feedback"

def test_route_after_critic_failed_continue_rewrite():
    state: AgentState = {
        "evaluation": {"pass_threshold": False, "overall_score": 0.75},
        "rewrite_count": 1,
        "max_rewrites": 3,
    }
    assert route_after_critic(state) == "writer"

def test_route_after_critic_failed_max_rewrites_reached():
    state: AgentState = {
        "evaluation": {"pass_threshold": False, "overall_score": 0.81},
        "rewrite_count": 3,
        "max_rewrites": 3,
    }
    assert route_after_critic(state) == "feedback"
