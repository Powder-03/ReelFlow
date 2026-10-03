import pytest
from app.evaluation.scorer import METRIC_WEIGHTS, PASS_THRESHOLD
from app.evaluation.metrics import (
    create_hook_strength_metric,
    create_emotional_arc_metric,
    create_pacing_metric,
    create_originality_metric,
    create_strategic_alignment_metric,
)
from app.models.schemas import GEvalScore, CriticEvaluation

def test_metric_weights_sum_to_one():
    total_weight = sum(METRIC_WEIGHTS.values())
    assert pytest.approx(total_weight, 0.001) == 1.0

def test_dual_scale_mapping():
    score = 0.865
    score_10 = round(score * 10, 2)
    assert score_10 == 8.65
    assert score >= PASS_THRESHOLD

def test_threshold_boundary():
    # 8.5/10 passes
    assert 0.85 >= PASS_THRESHOLD
    # 8.4/10 fails
    assert 0.84 < PASS_THRESHOLD

def test_metrics_instantiation():
    hook_m = create_hook_strength_metric()
    assert hook_m.name == "Hook Strength"
    assert len(hook_m.evaluation_steps) > 3
    assert hook_m.threshold == 0.85

    arc_m = create_emotional_arc_metric()
    assert arc_m.name == "Emotional Arc"

    pacing_m = create_pacing_metric()
    assert pacing_m.name == "Pacing"

    orig_m = create_originality_metric()
    assert orig_m.name == "Originality"

    strat_m = create_strategic_alignment_metric("Content Bucket: study_tips, Hook: shock_stat")
    assert strat_m.name == "Strategic Alignment"
    assert "study_tips" in strat_m.evaluation_steps[0]

def test_critic_evaluation_schema_contract():
    s = GEvalScore(
        metric_name="Hook Strength",
        score=0.9,
        score_10=9.0,
        reason="Captivating first 2 seconds",
        evaluation_steps=["step 1", "step 2"],
    )
    eval_result = CriticEvaluation(
        hook_strength=s,
        emotional_arc=s,
        pacing=s,
        originality=s,
        strategic_alignment=s,
        overall_score=0.9,
        overall_score_10=9.0,
        qualitative_feedback="All metrics passed",
        pass_threshold=True,
        rewrite_suggestions=[],
    )
    assert eval_result.overall_score_10 == 9.0
    assert eval_result.pass_threshold is True
