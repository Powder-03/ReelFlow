import asyncio
from typing import Dict, Tuple
from deepeval.test_case import LLMTestCase
from app.evaluation.metrics import (
    create_hook_strength_metric,
    create_emotional_arc_metric,
    create_pacing_metric,
    create_originality_metric,
    create_strategic_alignment_metric,
)
from app.models.schemas import CriticEvaluation, GEvalScore
from app.core.config import settings

# Deterministic metric weights
METRIC_WEIGHTS: Dict[str, float] = {
    "hook_strength": 0.25,        # Hook is critical for reels scroll-stopping
    "emotional_arc": 0.20,
    "pacing": 0.20,
    "originality": 0.15,
    "strategic_alignment": 0.20,
}

PASS_THRESHOLD: float = settings.PASS_THRESHOLD  # 0.85 (8.5/10)

async def _measure_metric(name: str, metric, test_case: LLMTestCase) -> Tuple[str, GEvalScore]:
    """Run a single G-Eval metric asynchronously."""
    await metric.a_measure(test_case)
    score_val = float(metric.score if metric.score is not None else 0.0)
    # Ensure score is clamped to [0.0, 1.0]
    score_val = max(0.0, min(1.0, score_val))
    return name, GEvalScore(
        metric_name=metric.name,
        score=round(score_val, 4),
        score_10=round(score_val * 10, 2),
        reason=str(metric.reason or ""),
        evaluation_steps=list(metric.evaluation_steps or []),
    )

async def evaluate_script(
    script_text: str,
    strategy_context: str,
) -> CriticEvaluation:
    """Run all 5 G-Eval metrics in PARALLEL via asyncio.gather and aggregate.
    
    Parallel execution reduces evaluation latency from ~15s (sequential) to ~3-4s.
    """
    metrics = {
        "hook_strength": create_hook_strength_metric(),
        "emotional_arc": create_emotional_arc_metric(),
        "pacing": create_pacing_metric(),
        "originality": create_originality_metric(),
        "strategic_alignment": create_strategic_alignment_metric(strategy_context),
    }

    test_case = LLMTestCase(
        input=f"Generate a high-quality Hinglish Instagram reel script aligned with strategy: {strategy_context}",
        actual_output=script_text,
    )

    # Concurrently evaluate all 5 metrics
    scored = await asyncio.gather(
        *[_measure_metric(name, metric, test_case) for name, metric in metrics.items()]
    )
    results = dict(scored)

    # Weighted score calculation
    overall = sum(
        results[name].score * weight
        for name, weight in METRIC_WEIGHTS.items()
    )
    overall_clamped = max(0.0, min(1.0, overall))

    # Identify rewrite suggestions from failing dimensions (< 0.85)
    rewrite_suggestions = [
        f"{results[name].metric_name} ({results[name].score_10}/10): {results[name].reason}"
        for name in METRIC_WEIGHTS
        if results[name].score < PASS_THRESHOLD
    ]

    qualitative_feedback = " | ".join(
        f"{r.metric_name}: {r.score_10}/10" for r in results.values()
    )

    return CriticEvaluation(
        hook_strength=results["hook_strength"],
        emotional_arc=results["emotional_arc"],
        pacing=results["pacing"],
        originality=results["originality"],
        strategic_alignment=results["strategic_alignment"],
        overall_score=round(overall_clamped, 4),
        overall_score_10=round(overall_clamped * 10, 2),
        qualitative_feedback=qualitative_feedback,
        pass_threshold=overall_clamped >= PASS_THRESHOLD,
        rewrite_suggestions=rewrite_suggestions,
    )
