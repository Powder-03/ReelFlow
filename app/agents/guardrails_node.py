from typing import Dict, Any
from langsmith import traceable
from app.agents.state import AgentState
from app.guardrails.engine import GuardrailsEngine
from app.models.schemas import StrategyDecision
from app.store.json_store import JsonStore

@traceable(name="Guardrails Node", run_type="tool")
async def guardrails_node(state: AgentState) -> Dict[str, Any]:
    """Guardrails node: Validates strategy against repetition, fatigue, and cooldowns.
    
    If validation fails >= 2 times, gracefully falls back to the historical
    best-performing combination and sets needs_human_review=True (preventing infinite loops).
    """
    store = JsonStore()
    engine = GuardrailsEngine()
    current_retry = state.get("guardrail_retry_count", 0)
    strategy_dict = state["strategy"]
    strategy = StrategyDecision.model_validate(strategy_dict)

    result = engine.run_all_checks(strategy, store, retry_count=current_retry)

    if result.auto_picked and result.auto_picked_strategy:
        fallback = result.auto_picked_strategy
        strategy = StrategyDecision(
            topic=fallback["topic"],
            content_bucket=fallback["content_bucket"],
            hook_style=fallback["hook_style"],
            format=fallback["format"],
            tone=fallback.get("tone", "High conviction and analytical"),
            reasoning=f"Auto-selected historical winner (ID: {fallback.get('source_post_id', 'N/A')}, ER: {fallback.get('engagement_rate', 0.0)}%) after Strategy Agent failed guardrails {current_retry} times.",
            confidence=0.85,
            needs_human_review=True,
            auto_pick_reason=f"Strategy Agent failed guardrail rules {current_retry} times. Auto-picked historical top performer to maintain pipeline flow without unbounded loops.",
        )
        return {
            "guardrail_result": result.model_dump(),
            "guardrail_retry_count": current_retry + 1,
            "strategy": strategy.model_dump(),
            "needs_human_review": True,
        }

    return {
        "guardrail_result": result.model_dump(),
        "guardrail_retry_count": current_retry + 1 if not result.passed else current_retry,
        "strategy": strategy.model_dump(),
    }
