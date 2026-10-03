from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langgraph.graph.message import add_messages

class AgentState(TypedDict, total=False):
    # Input
    account_handle: str
    content_request: Optional[str]

    # Intelligence output
    upcoming_events: List[Dict[str, Any]]
    trending_topics: List[str]
    account_analysis: Dict[str, Any]
    content_gaps: List[str]

    # Memory output
    top_performers: List[Dict[str, Any]]
    successful_hooks: List[str]
    successful_formats: List[str]
    fatigued_topics: List[str]
    competitor_insights: List[Dict[str, Any]]

    # Strategy output
    strategy: Dict[str, Any]
    guardrail_result: Dict[str, Any]
    guardrail_retry_count: int

    # Writer & Critic loop
    current_script: Dict[str, Any]
    evaluation: Dict[str, Any]
    all_evaluations: List[Dict[str, Any]]
    rewrite_count: int
    max_rewrites: int

    # Final outputs
    approved_script: Optional[Dict[str, Any]]
    best_script: Optional[Dict[str, Any]]
    best_score: float
    needs_human_review: bool
    messages: Annotated[list, add_messages]
