import json
import re
from typing import Dict, Any, List
from langsmith import traceable

from app.agents.state import AgentState
from app.core.llm import get_llm
from app.models.schemas import StrategyDecision, StrategyHypothesis
from app.guardrails.engine import GuardrailsEngine
from app.store.json_store import JsonStore

def _extract_json(text: str) -> Any:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    first_bracket = text.find("[")
    last_bracket = text.rfind("]")
    if first_bracket != -1 and last_bracket != -1:
        return json.loads(text[first_bracket : last_bracket + 1])
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1:
        return json.loads(text[first_brace : last_brace + 1])
    return json.loads(text)

STRATEGY_TOT_PROMPT = """You are an Elite Instagram Content Strategist executing Tree of Thoughts (ToT) exploration.

Instead of outputting just one idea, you will BRANCH OUT AND EXPLORE 3 DIVERGENT STRATEGY HYPOTHESES:
- Branch 1: High-Utility Study Hack / Blueprint (content_bucket: study_tips or strategy)
- Branch 2: High-Emotion / Vulnerable Reality Check (content_bucket: motivation)
- Branch 3: High-Urgency Current Affairs Debate / Critical Milestone (content_bucket: current_affairs or strategy)

Intelligence Inputs:
- Upcoming Events: {upcoming_events}
- Trending Topics: {trending_topics}
- Content Gaps: {content_gaps}
- Account Analysis: {account_analysis}

Performance Memory:
- Top Historical Hooks: {successful_hooks}
- Top Formats: {successful_formats}
- Strictly Avoid (Fatigued / Repetitive Topics): {fatigued_topics}
- Competitor Insights: {competitor_insights}

User Content Request (if any): {content_request}
{guardrail_feedback}

For EACH of the 3 branches, output:
- hypothesis_id: 1, 2, or 3
- topic: Specific, compelling reel title
- content_bucket: One of ["study_tips", "motivation", "current_affairs", "strategy", "book_reviews"]
- hook_style: One of ["shock_stat", "question", "personal_story", "myth_bust", "challenge"]
- format: One of ["talking_head", "text_overlay", "voiceover_montage", "skit"]
- tone: Energy description
- rationale: Why this branch has viral retention potential
- confidence: Score between 0.0 and 1.0

Return ONLY valid JSON matching a list of 3 StrategyHypothesis objects:
[
  {{
    "hypothesis_id": 1,
    "topic": "string",
    "content_bucket": "study_tips",
    "hook_style": "shock_stat",
    "format": "talking_head",
    "tone": "Authoritative and urgent",
    "rationale": "string",
    "confidence": 0.92
  }},
  ...
]
"""

async def _generate_strategy_branches(state: AgentState, guardrail_feedback: str) -> List[StrategyHypothesis]:
    """Generates 3 divergent strategy hypotheses in parallel thought trees."""
    llm = get_llm(temperature=0.7)
    prompt = STRATEGY_TOT_PROMPT.format(
        upcoming_events=json.dumps(state.get("upcoming_events", []), indent=2),
        trending_topics=json.dumps(state.get("trending_topics", []), indent=2),
        content_gaps=json.dumps(state.get("content_gaps", []), indent=2),
        account_analysis=json.dumps(state.get("account_analysis", {}), indent=2),
        successful_hooks=json.dumps(state.get("successful_hooks", []), indent=2),
        successful_formats=json.dumps(state.get("successful_formats", []), indent=2),
        fatigued_topics=json.dumps(state.get("fatigued_topics") or JsonStore().get_fatigued_topics(), indent=2),
        competitor_insights=json.dumps(state.get("competitor_insights", []), indent=2),
        content_request=state.get("content_request") or "None",
        guardrail_feedback=guardrail_feedback,
    )

    response = await llm.ainvoke(prompt)
    try:
        raw_list = _extract_json(response.content)
        if isinstance(raw_list, dict) and "hypotheses" in raw_list:
            raw_list = raw_list["hypotheses"]
        hypotheses = [StrategyHypothesis.model_validate(item) for item in raw_list]
        if hypotheses:
            return hypotheses
    except Exception:
        pass

    # Fallback diverse branches
    return [
        StrategyHypothesis(
            hypothesis_id=1,
            topic="CSAT Error Elimination: The 3-Pass Rule to Guarantee 80+ Marks",
            content_bucket="study_tips",
            hook_style="shock_stat",
            format="talking_head",
            tone="Urgent and tactical",
            rationale="High search interest and consistent fear-driven engagement in Prelims prep.",
            confidence=0.91,
        ),
        StrategyHypothesis(
            hypothesis_id=2,
            topic="From 3 Prelims Failures to AIR 42: The 1 Mindset Shift",
            content_bucket="motivation",
            hook_style="personal_story",
            format="talking_head",
            tone="Empathetic, raw and inspiring",
            rationale="High save and share rate from aspirant emotional vulnerability.",
            confidence=0.88,
        ),
        StrategyHypothesis(
            hypothesis_id=3,
            topic="UPSC Mains GS4 Ethics: How Case Studies Decide Your Cadre",
            content_bucket="strategy",
            hook_style="myth_bust",
            format="text_overlay",
            tone="Strategic and high conviction",
            rationale="High marks leverage with low competition.",
            confidence=0.89,
        ),
    ]

def _prune_and_select_champion(
    hypotheses: List[StrategyHypothesis],
    store: JsonStore,
    engine: GuardrailsEngine,
    fatigued_topics: List[str],
) -> StrategyDecision:
    """Evaluates all candidate branches against guardrails, prunes violating branches, and selects the winner."""
    valid_candidates: List[tuple[StrategyHypothesis, float]] = []

    for hyp in hypotheses:
        decision_candidate = StrategyDecision(
            topic=hyp.topic,
            content_bucket=hyp.content_bucket,
            hook_style=hyp.hook_style,
            format=hyp.format,
            tone=hyp.tone,
            reasoning=hyp.rationale,
            confidence=hyp.confidence,
            avoid_topics=fatigued_topics,
            avoid_formats=[],
        )
        # Check against guardrails
        res = engine.run_all_checks(decision_candidate, store, retry_count=0)
        if res.passed and not res.violations:
            valid_candidates.append((hyp, hyp.confidence))

    # If any branches passed guardrails cleanly, pick the highest confidence
    if valid_candidates:
        valid_candidates.sort(key=lambda x: x[1], reverse=True)
        winner = valid_candidates[0][0]
        return StrategyDecision(
            topic=winner.topic,
            content_bucket=winner.content_bucket,
            hook_style=winner.hook_style,
            format=winner.format,
            tone=winner.tone,
            reasoning=f"[ToT Champion selected from {len(hypotheses)} branches]: {winner.rationale}",
            confidence=winner.confidence,
            avoid_topics=fatigued_topics,
            avoid_formats=[],
        )

    # If all 3 branches had minor rule overlap, pick the one with highest confidence
    hypotheses.sort(key=lambda x: x.confidence, reverse=True)
    fallback_winner = hypotheses[0]
    return StrategyDecision(
        topic=fallback_winner.topic,
        content_bucket=fallback_winner.content_bucket,
        hook_style=fallback_winner.hook_style,
        format=fallback_winner.format,
        tone=fallback_winner.tone,
        reasoning=f"[ToT Candidate]: {fallback_winner.rationale}",
        confidence=fallback_winner.confidence,
        avoid_topics=fatigued_topics,
        avoid_formats=[],
    )

@traceable(name="Strategy Agent (ToT)", run_type="chain")
async def strategy_node(state: AgentState) -> Dict[str, Any]:
    """Strategy Agent with Tree of Thoughts: Branches 3 hypotheses, prunes bad angles, and picks champion."""
    store = JsonStore()
    engine = GuardrailsEngine()
    guardrail_result = state.get("guardrail_result")
    retry_count = state.get("guardrail_retry_count", 0)

    guardrail_feedback = ""
    if guardrail_result and not guardrail_result.get("passed", True):
        violations = guardrail_result.get("violations", [])
        guardrail_feedback = (
            f"\nATTENTION - PREVIOUS PROPOSAL REJECTED BY GUARDRAILS (Attempt {retry_count}):\n"
            + "\n".join(f"- {v}" for v in violations)
            + "\nYou MUST explore DIVERGENT angles in all 3 branches that avoid these violations completely!\n"
        )

    # Level 1: Generate 3 diverse strategy branches
    hypotheses = await _generate_strategy_branches(state, guardrail_feedback)

    # Level 2: Deterministic guardrail pruning & champion selection
    fatigued_topics = state.get("fatigued_topics") or store.get_fatigued_topics()
    champion_strategy = _prune_and_select_champion(hypotheses, store, engine, fatigued_topics)

    return {
        "strategy": champion_strategy.model_dump(),
    }
