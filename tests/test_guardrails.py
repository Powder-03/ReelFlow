import pytest
from pathlib import Path
from app.guardrails.engine import GuardrailsEngine
from app.models.schemas import StrategyDecision
from app.store.json_store import JsonStore

@pytest.fixture
def store_and_engine(tmp_path: Path):
    data_dir = tmp_path / "data"
    memory_dir = tmp_path / "memory"
    data_dir.mkdir()
    memory_dir.mkdir()

    (data_dir / "sample_posts.json").write_text("""[
        {
            "post_id": "p1",
            "date": "2026-09-28T10:00:00Z",
            "content_bucket": "study_tips",
            "hook_style": "shock_stat",
            "format": "talking_head",
            "topic": "CSAT Cutoff Trap and Mistakes",
            "engagement_rate": 8.5,
            "views": 200000,
            "saves": 15000,
            "shares": 8000,
            "comments": 1200
        },
        {
            "post_id": "p2",
            "date": "2026-09-25T10:00:00Z",
            "content_bucket": "study_tips",
            "hook_style": "shock_stat",
            "format": "talking_head",
            "topic": "Prelims GS Paper 1 Time Strategy",
            "engagement_rate": 7.0,
            "views": 150000,
            "saves": 10000,
            "shares": 5000,
            "comments": 800
        },
        {
            "post_id": "p3",
            "date": "2026-09-20T10:00:00Z",
            "content_bucket": "current_affairs",
            "hook_style": "question",
            "format": "text_overlay",
            "topic": "Semiconductor Mission India",
            "engagement_rate": 6.0,
            "views": 110000,
            "saves": 7000,
            "shares": 3500,
            "comments": 400
        }
    ]""", encoding="utf-8")

    store = JsonStore(data_dir=data_dir, memory_dir=memory_dir)
    engine = GuardrailsEngine(max_retries=2)
    return store, engine

def test_topic_repetition():
    engine = GuardrailsEngine()
    recent = ["CSAT Cutoff Trap and Mistakes", "Prelims GS Paper 1 Time Strategy"]
    # Repetitive topic
    assert not engine.check_topic_repetition("CSAT Cutoff Trap Strategy", recent)
    # Fresh topic
    assert engine.check_topic_repetition("Mains GS4 Ethics Case Studies Framework", recent)

def test_hook_rotation():
    engine = GuardrailsEngine()
    # If recent 2 posts used shock_stat, proposing shock_stat should fail
    recent_hooks = ["shock_stat", "shock_stat", "question"]
    assert not engine.check_hook_rotation("shock_stat", recent_hooks)
    assert engine.check_hook_rotation("personal_story", recent_hooks)

def test_format_cooldown():
    engine = GuardrailsEngine()
    # talking_head used 2 of last 3
    recent_formats = ["talking_head", "talking_head", "text_overlay"]
    assert not engine.check_format_cooldown("talking_head", recent_formats)
    assert engine.check_format_cooldown("skit", recent_formats)

def test_segment_word_count():
    engine = GuardrailsEngine()
    # 20 words (within 18-23 range)
    valid_text = "Agar aap CSAT ko lightly le rahe ho to yeh reel aapke poore do saal bacha sakti hai dhyan se suno."
    assert engine.validate_segment_word_count(valid_text)

    # Way too short (4 words)
    short_text = "Yeh video dekho abhi."
    assert not engine.validate_segment_word_count(short_text)

def test_guardrails_pass(store_and_engine):
    store, engine = store_and_engine
    strategy = StrategyDecision(
        topic="Mains Ethics Case Study Framework",
        content_bucket="strategy",
        hook_style="personal_story",
        format="skit",
        tone="Strategic and engaging",
        reasoning="Fresh angle for ethics paper",
        confidence=0.9,
    )
    result = engine.run_all_checks(strategy, store, retry_count=0)
    assert result.passed
    assert not result.auto_picked
    assert len(result.violations) == 0

def test_guardrails_fail_under_max_retries(store_and_engine):
    store, engine = store_and_engine
    # Violates hook rotation (shock_stat used twice recently) and topic repetition
    bad_strategy = StrategyDecision(
        topic="CSAT Cutoff Trap and Mistakes",
        content_bucket="study_tips",
        hook_style="shock_stat",
        format="talking_head",
        tone="Urgent",
        reasoning="High past engagement",
        confidence=0.7,
    )
    result = engine.run_all_checks(bad_strategy, store, retry_count=1)
    assert not result.passed
    assert not result.auto_picked
    assert len(result.violations) > 0

def test_guardrails_bounded_fallback_at_max_retries(store_and_engine):
    store, engine = store_and_engine
    # Violates checks, but retry_count is 2 (equal to MAX_GUARDRAIL_RETRIES)
    bad_strategy = StrategyDecision(
        topic="CSAT Cutoff Trap and Mistakes",
        content_bucket="study_tips",
        hook_style="shock_stat",
        format="talking_head",
        tone="Urgent",
        reasoning="Testing fallback trigger",
        confidence=0.5,
    )
    result = engine.run_all_checks(bad_strategy, store, retry_count=2)
    # Bounded fallback: must pass with auto_picked=True to prevent infinite loops
    assert result.passed
    assert result.auto_picked
    assert result.auto_picked_strategy is not None
    assert "FALLBACK_TRIGGERED" in result.violations[-1]

def test_hook_rotation_and_audit_logging(store_and_engine):
    """Verifies that consecutive hook fatigue triggers hook rotation,
    logs the change, and persists reasoning and confidence in audit trail.
    """
    store, engine = store_and_engine
    # Recent 2 posts used 'shock_stat'
    consecutive_hook_strategy = StrategyDecision(
        topic="Mains Essay Scoring Framework",
        content_bucket="strategy",
        hook_style="shock_stat",  # Overused
        format="skit",
        tone="Strategic and engaging",
        reasoning="Shock statistics on essay mark differences create high urgency for aspirants.",
        confidence=0.92,
    )

    result = engine.run_all_checks(consecutive_hook_strategy, store, retry_count=0)

    # Assert violation caught
    assert not result.passed
    assert result.hook_changed
    assert result.original_hook == "shock_stat"
    assert result.rotated_hook in ["question", "personal_story", "myth_bust", "challenge"]
    assert any("HOOK_FATIGUE" in v for v in result.violations)

    # Verify audit log in persistent memory
    audit_logs = store.get_guardrail_audit_logs(limit=10)
    assert len(audit_logs) > 0
    latest_log = audit_logs[-1]

    # Verify reasoning and confidence are recorded
    assert latest_log["strategy_topic"] == "Mains Essay Scoring Framework"
    assert latest_log["reasoning"] == "Shock statistics on essay mark differences create high urgency for aspirants."
    assert latest_log["confidence"] == 0.92
    assert latest_log["hook_changed"] is True
    assert latest_log["original_hook"] == "shock_stat"
    assert latest_log["rotated_hook"] == result.rotated_hook

def test_auto_rotate_hook_resolution(store_and_engine):
    """Verifies that auto_rotate_hook switches to fresh hook and clears hook violation."""
    store, engine = store_and_engine
    strategy = StrategyDecision(
        topic="Mains Ethics Case Study Framework",
        content_bucket="strategy",
        hook_style="shock_stat",  # Overused
        format="skit",
        tone="Strategic and engaging",
        reasoning="High conviction ethical framework.",
        confidence=0.88,
    )

    result = engine.run_all_checks(strategy, store, retry_count=0, auto_rotate_hook=True)
    assert result.passed
    assert result.hook_changed
    assert strategy.hook_style != "shock_stat"
    assert len(result.violations) == 0
