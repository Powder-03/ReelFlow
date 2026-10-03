import pytest
from app.models.schemas import HookCandidate, StrategyHypothesis, ReelScript, ScriptSegment
from app.agents.writer import _evaluate_and_prune_hooks, _validate_and_backtrack_pacing
from app.agents.strategy import _prune_and_select_champion
from app.guardrails.engine import GuardrailsEngine
from app.store.json_store import JsonStore

def test_tot_hook_evaluation_and_pruning():
    candidates = [
        HookCandidate(
            hook_id=1,
            hook_style="shock_stat",
            text="GS Paper 1 mein 110 marks laane waale 68 percent aspirants CSAT mein fail ho jaate hain.",
            visual_cue="[Camera zoom]",
            word_count=16,
        ),
        HookCandidate(
            hook_id=2,
            hook_style="personal_story",
            text="Jab mere teen attempts fail huye the tab maine realize kiya ki bina planning ke mehnat bekar hai.",
            visual_cue="[Serious eye contact]",
            word_count=18,
        ),
        HookCandidate(
            hook_id=3,
            hook_style="question",
            text="Kya aapko lagta hai?",
            visual_cue="[Camera pan]",
            word_count=4,  # Way too short
        ),
    ]

    champion, evals = _evaluate_and_prune_hooks(candidates)
    assert len(evals) == 3
    # Candidate 3 should fail word count check
    assert evals[2].word_count_valid is False
    # Candidate 2 or 1 should be champion (both valid word counts)
    assert champion.hook_id in [1, 2]
    assert evals[0].overall_hook_score > evals[2].overall_hook_score

def test_tot_segment_backtracking():
    long_text = "Yeh ek bohot hi zyada lamba segment hai jisme itne saare unnecessary words dale gaye hain jo kabhi bhi Instagram reel ke andar fit nahi baith sakte aur audience scroll kar degi."
    assert len(long_text.split()) > 25

    script = ReelScript(
        title="Test Reel",
        hook="Short hook text here.",
        segments=[
            ScriptSegment(segment_id=1, type="hook", text="Short hook text here.", visual_cue="[Zoom]"),
            ScriptSegment(segment_id=2, type="build_up", text=long_text, visual_cue="[Cut]"),
        ],
        cta="Comment CSAT below.",
        content_bucket="study_tips",
        hook_style="shock_stat",
        format="talking_head",
        tone="Urgent",
        topic="CSAT Strategy",
    )

    trimmed_script = _validate_and_backtrack_pacing(script)
    # Segment 2 should have been backtracked to <= 25 words
    assert len(trimmed_script.segments[1].text.split()) <= 23

def test_tot_strategy_pruning(tmp_path):
    data_dir = tmp_path / "data"
    memory_dir = tmp_path / "memory"
    data_dir.mkdir()
    memory_dir.mkdir()

    # Fatigued topic in store
    (memory_dir / "fatigue_registry.json").write_text('[{"topic": "Laxmikanth Notes", "reason": "Overused"}]', encoding="utf-8")
    (data_dir / "sample_posts.json").write_text('[]', encoding="utf-8")

    store = JsonStore(data_dir=data_dir, memory_dir=memory_dir)
    engine = GuardrailsEngine()

    hypotheses = [
        StrategyHypothesis(
            hypothesis_id=1,
            topic="Laxmikanth Notes Revision Hacks",  # Should be PRUNED (fatigued)
            content_bucket="study_tips",
            hook_style="shock_stat",
            format="talking_head",
            tone="Urgent",
            rationale="High search",
            confidence=0.95,
        ),
        StrategyHypothesis(
            hypothesis_id=2,
            topic="Mains Ethics GS4 Case Study Framework",  # CLEAN
            content_bucket="strategy",
            hook_style="personal_story",
            format="text_overlay",
            tone="Authoritative",
            rationale="Untapped high yield angle",
            confidence=0.88,
        ),
    ]

    champion = _prune_and_select_champion(hypotheses, store, engine, fatigued_topics=["Laxmikanth Notes Revision Hacks"])
    # The fatigued hypothesis MUST have been pruned, choosing the clean candidate
    assert "Ethics" in champion.topic
