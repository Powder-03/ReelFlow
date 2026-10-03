import uuid
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from langsmith import traceable

from app.models.schemas import (
    GenerateRequest,
    GenerateResponse,
    FeedbackRequest,
    Post,
    ReelScript,
    CriticEvaluation,
    StrategyDecision,
)
from app.agents.graph import build_growth_brain_graph
from app.agents.state import AgentState
from app.agents.intelligence import intelligence_node
from app.agents.memory import memory_node
from app.agents.strategy import strategy_node
from app.agents.guardrails_node import guardrails_node
from app.store.json_store import JsonStore
from app.core.config import settings

router = APIRouter()
store = JsonStore()
graph = build_growth_brain_graph()

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model": settings.GEMINI_MODEL,
        "gcp_project": settings.GOOGLE_CLOUD_PROJECT,
        "gcp_location": settings.GOOGLE_CLOUD_LOCATION,
        "pass_threshold_10": settings.PASS_THRESHOLD * 10,
        "max_rewrites": settings.MAX_REWRITES,
    }

@router.post("/generate", response_model=GenerateResponse)
@traceable(
    name="Generate Reel Pipeline",
    run_type="chain",
    tags=["reel-flow", "upsc"],
    metadata={"service": "growth-brain", "model": settings.GEMINI_MODEL}
)
async def generate_reel_pipeline(request: GenerateRequest):
    """Run full Multi-Agent Instagram Growth Brain workflow."""
    try:
        initial_state: AgentState = {
            "account_handle": request.account_handle,
            "content_request": request.content_request,
            "guardrail_retry_count": 0,
            "rewrite_count": 0,
            "max_rewrites": settings.MAX_REWRITES,
            "needs_human_review": False,
            "all_evaluations": [],
        }

        thread_id = f"reel-{uuid.uuid4().hex[:12]}"
        config = {
            "configurable": {"thread_id": thread_id},
            "run_name": f"ReelFlow Pipeline: {request.account_handle}",
            "tags": ["reel-flow", request.account_handle],
        }

        final_state = await graph.ainvoke(initial_state, config=config)

        approved_script_dict = final_state.get("approved_script") or final_state.get("best_script")
        evaluation_dict = final_state.get("evaluation")
        strategy_dict = final_state.get("strategy")

        script = ReelScript.model_validate(approved_script_dict) if approved_script_dict else None
        evaluation = CriticEvaluation.model_validate(evaluation_dict) if evaluation_dict else None
        strategy = StrategyDecision.model_validate(strategy_dict) if strategy_dict else None

        all_evals = [
            CriticEvaluation.model_validate(e)
            for e in final_state.get("all_evaluations", [])
        ]

        return GenerateResponse(
            status="success",
            script=script,
            evaluation=evaluation,
            strategy=strategy,
            rewrites_done=final_state.get("rewrite_count", 1) - 1,
            needs_human_review=final_state.get("needs_human_review", False),
            all_evaluations=all_evals,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate/strategy-only", response_model=StrategyDecision)
@traceable(
    name="Strategy Formulation Flow",
    run_type="chain",
    tags=["strategy-only", "upsc"],
    metadata={"service": "growth-brain", "model": settings.GEMINI_MODEL}
)
async def generate_strategy_only(request: GenerateRequest):
    """Run Intelligence + Memory + Strategy + Guardrails only."""
    try:
        state: AgentState = {
            "account_handle": request.account_handle,
            "content_request": request.content_request,
            "guardrail_retry_count": 0,
            "needs_human_review": False,
        }

        intel_out = await intelligence_node(state)
        state.update(intel_out)

        mem_out = await memory_node(state)
        state.update(mem_out)

        strat_out = await strategy_node(state)
        state.update(strat_out)

        guard_out = await guardrails_node(state)
        state.update(guard_out)

        return StrategyDecision.model_validate(state["strategy"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/memory/top-posts", response_model=List[Post])
async def get_top_posts(limit: int = 10):
    """Retrieve historically top performing posts."""
    return store.get_top_performing(limit=limit)

@router.get("/memory/fatigued", response_model=List[str])
async def get_fatigued():
    """Retrieve list of currently fatigued topics."""
    return store.get_fatigued_topics()

@router.post("/memory/fatigue")
async def mark_topic_fatigued(topic: str, reason: str):
    """Manually register a topic as fatigued."""
    store.mark_fatigued(topic, reason)
    return {"status": "success", "message": f"Topic '{topic}' marked as fatigued"}

@router.post("/feedback")
async def submit_performance_feedback(feedback: FeedbackRequest):
    """Log performance metrics for a published reel script."""
    store.log_performance(
        script_id=feedback.script_id,
        metrics={
            "engagement_rate": feedback.engagement_rate,
            "views": feedback.views,
            "saves": feedback.saves,
            "shares": feedback.shares,
            "comments": feedback.comments,
        },
    )
    return {"status": "success", "message": f"Metrics logged for script {feedback.script_id}"}
