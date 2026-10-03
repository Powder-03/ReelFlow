import pytest
from pathlib import Path
from datetime import datetime, timezone
from app.store.json_store import JsonStore
from app.models.schemas import Post, ReelScript, ScriptSegment, CriticEvaluation, GEvalScore

@pytest.fixture
def temp_store(tmp_path: Path):
    data_dir = tmp_path / "data"
    memory_dir = tmp_path / "memory"
    data_dir.mkdir()
    memory_dir.mkdir()

    # Create dummy sample account
    (data_dir / "sample_account.json").write_text("""{
        "handle": "@test_account",
        "niche": "UPSC Prep",
        "followers": 50000,
        "avg_engagement_rate": 4.5,
        "content_language": "Hinglish",
        "top_buckets": ["study_tips", "motivation"]
    }""", encoding="utf-8")

    # Create dummy sample posts
    (data_dir / "sample_posts.json").write_text("""[
        {
            "post_id": "p1",
            "date": "2026-09-20T10:00:00Z",
            "content_bucket": "study_tips",
            "hook_style": "shock_stat",
            "format": "talking_head",
            "topic": "CSAT Cutoff Strategy",
            "engagement_rate": 8.5,
            "views": 200000,
            "saves": 15000,
            "shares": 8000,
            "comments": 1200
        },
        {
            "post_id": "p2",
            "date": "2026-09-18T10:00:00Z",
            "content_bucket": "motivation",
            "hook_style": "personal_story",
            "format": "text_overlay",
            "topic": "Why failure is your teacher",
            "engagement_rate": 3.0,
            "views": 50000,
            "saves": 2000,
            "shares": 1000,
            "comments": 200
        },
        {
            "post_id": "p3",
            "date": "2026-09-15T10:00:00Z",
            "content_bucket": "current_affairs",
            "hook_style": "question",
            "format": "talking_head",
            "topic": "One Nation One Election Bill",
            "engagement_rate": 6.0,
            "views": 120000,
            "saves": 8000,
            "shares": 4000,
            "comments": 600
        }
    ]""", encoding="utf-8")

    # Create dummy events
    (data_dir / "events_calendar.json").write_text("""[
        {
            "event_name": "Gandhi Jayanti",
            "date": "2026-10-02",
            "category": "national_day",
            "relevance_to_niche": "Ethics GS4 relevance"
        }
    ]""", encoding="utf-8")

    return JsonStore(data_dir=data_dir, memory_dir=memory_dir)

def test_load_account_profile(temp_store: JsonStore):
    profile = temp_store.load_account_profile()
    assert profile.handle == "@test_account"
    assert profile.followers == 50000

def test_load_posts(temp_store: JsonStore):
    posts = temp_store.load_posts()
    assert len(posts) == 3
    assert posts[0].post_id == "p1"
    assert posts[0].engagement_rate == 8.5

def test_get_top_performing(temp_store: JsonStore):
    top = temp_store.get_top_performing(limit=2)
    assert len(top) == 2
    assert top[0].post_id == "p1"
    assert top[1].post_id == "p3"

def test_get_underperforming(temp_store: JsonStore):
    under = temp_store.get_underperforming(threshold=4.0)
    assert len(under) == 1
    assert under[0].post_id == "p2"

def test_fatigue_registry(temp_store: JsonStore):
    temp_store.mark_fatigued("Laxmikanth Notes", "Too many videos in last month")
    fatigued = temp_store.get_fatigued_topics()
    assert "Laxmikanth Notes" in fatigued

def test_save_approved_script(temp_store: JsonStore):
    script = ReelScript(
        title="Test Reel",
        hook="Yeh 3 mistakes apke 2 attempts barbaad kar sakti hain.",
        segments=[
            ScriptSegment(segment_id=1, type="hook", text="Yeh 3 mistakes apke 2 attempts barbaad kar sakti hain.", visual_cue="[Camera zoom]"),
            ScriptSegment(segment_id=2, type="cta", text="Comment karo 'CSAT' for full PDF guide.", visual_cue="[Text pop-up]"),
        ],
        cta="Comment karo 'CSAT' for full PDF guide.",
        content_bucket="study_tips",
        hook_style="shock_stat",
        format="talking_head",
        tone="Urgent and strategic",
        topic="CSAT Mistakes",
    )
    score_item = GEvalScore(
        metric_name="hook_strength",
        score=0.9,
        score_10=9.0,
        reason="Strong curiosity gap",
    )
    evaluation = CriticEvaluation(
        hook_strength=score_item,
        emotional_arc=score_item,
        pacing=score_item,
        originality=score_item,
        strategic_alignment=score_item,
        overall_score=0.9,
        overall_score_10=9.0,
        qualitative_feedback="hook_strength=9.0/10",
        pass_threshold=True,
        rewrite_suggestions=[],
    )
    temp_store.save_approved_script(script, evaluation)
    
    approved_file = temp_store.memory_dir / "approved_scripts.json"
    import json
    data = json.loads(approved_file.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["script"]["title"] == "Test Reel"

def test_get_best_performing_combination(temp_store: JsonStore):
    # Exclude p1's topic and hook
    combo = temp_store.get_best_performing_combination(
        exclude_topics=["CSAT Cutoff Strategy"],
        exclude_hooks=["shock_stat"],
        exclude_formats=["text_overlay"],
    )
    # Should select p3
    assert combo["topic"] == "One Nation One Election Bill"
    assert combo["hook_style"] == "question"
    assert combo["format"] == "talking_head"
