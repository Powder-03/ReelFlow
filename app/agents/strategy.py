import json
import re
from typing import Dict, Any
from langsmith import traceable

from app.agents.state import AgentState
from app.core.llm import get_llm
from app.models.schemas import StrategyDecision

def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1:
        return json.loads(text[first_brace : last_brace + 1])
    return json.loads(text)

STRATEGY_PROMPT = """You are an Elite Instagram Content Strategist.

Your goal is to select the single best content strategy for the next viral Instagram reel.

Intelligence Insights:
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

DECISION REQUIREMENTS:
1. topic: A specific, captivating reel topic (MUST NOT be in the avoid/fatigued list).
2. content_bucket: One of ["study_tips", "motivation", "current_affairs", "strategy", "book_reviews"].
3. hook_style: One of ["shock_stat", "question", "personal_story", "myth_bust", "challenge"].
4. format: One of ["talking_head", "text_overlay", "voiceover_montage", "skit"].
5. tone: Specific energy (e.g. "High conviction and empathetic", "Urgent reality check").
6. reasoning: Detailed strategic rationale explaining why this specific combination will outperform current benchmarks.
7. confidence: Numerical confidence score between 0.0 and 1.0.
8. avoid_topics: List of topics currently fatigued or oversaturated.
9. avoid_formats: List of formats currently on cooldown.

Return ONLY valid JSON matching StrategyDecision schema:
{{
  "topic": "string",
  "content_bucket": "string",
  "hook_style": "string",
  "format": "string",
  "tone": "string",
  "reasoning": "string",
  "confidence": 0.9,
  "avoid_topics": ["string"],
  "avoid_formats": ["string"]
}}
"""

@traceable(name="Strategy Agent", run_type="chain")
async def strategy_node(state: AgentState) -> Dict[str, Any]:
    """Strategy Agent: Formulates the next content move based on Intelligence and Memory."""
    guardrail_result = state.get("guardrail_result")
    retry_count = state.get("guardrail_retry_count", 0)

    guardrail_feedback = ""
    if guardrail_result and not guardrail_result.get("passed", True):
        violations = guardrail_result.get("violations", [])
        guardrail_feedback = (
            f"\nATTENTION - PREVIOUS PROPOSAL REJECTED BY GUARDRAILS (Attempt {retry_count}):\n"
            + "\n".join(f"- {v}" for v in violations)
            + "\nYou MUST choose a DIFFERENT topic, hook style, or format that avoids these violations completely!\n"
        )

    llm = get_llm(temperature=0.6)
    prompt = STRATEGY_PROMPT.format(
        upcoming_events=json.dumps(state.get("upcoming_events", []), indent=2),
        trending_topics=json.dumps(state.get("trending_topics", []), indent=2),
        content_gaps=json.dumps(state.get("content_gaps", []), indent=2),
        account_analysis=json.dumps(state.get("account_analysis", {}), indent=2),
        successful_hooks=json.dumps(state.get("successful_hooks", []), indent=2),
        successful_formats=json.dumps(state.get("successful_formats", []), indent=2),
        fatigued_topics=json.dumps(state.get("fatigued_topics", []), indent=2),
        competitor_insights=json.dumps(state.get("competitor_insights", []), indent=2),
        content_request=state.get("content_request") or "None",
        guardrail_feedback=guardrail_feedback,
    )

    response = await llm.ainvoke(prompt)
    try:
        data = _extract_json(response.content)
        strategy = StrategyDecision.model_validate(data)
    except Exception:
        # Fallback to a clean strategic decision
        strategy = StrategyDecision(
            topic="Ethics GS4 Case Study Framework: 3 Golden Rules for 20+ Marks Jump",
            content_bucket="strategy",
            hook_style="shock_stat",
            format="talking_head",
            tone="Urgent, highly actionable and authoritative",
            reasoning="Ethics offers maximum marks leverage in Mains with minimal competition.",
            confidence=0.92,
            avoid_topics=state.get("fatigued_topics", []),
            avoid_formats=["voiceover_montage"],
        )

    return {
        "strategy": strategy.model_dump(),
    }
