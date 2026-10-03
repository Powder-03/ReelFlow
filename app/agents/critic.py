import json
import re
from typing import Dict, Any, List

from app.agents.state import AgentState
from app.core.llm import get_llm
from app.evaluation.scorer import evaluate_script

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

CRITIC_QUALITATIVE_PROMPT = """You are an Elite Instagram Content Director and Script Doctor.

A reel script was just rigorously evaluated using 5 G-Eval metrics (Hook Strength, Emotional Arc, Pacing, Originality, Strategic Alignment).
The script failed the 8.5/10 overall threshold. Your job is NOT to re-score. The scores are final.
Your job is to provide CONCRETE, ACTIONABLE rewrite coaching for the Writer Agent on the failing dimensions.

Script:
{script}

Strategy:
{strategy}

G-Eval Metric Breakdown:
- Hook Strength: {hook_score_10}/10 — {hook_reason}
- Emotional Arc: {arc_score_10}/10 — {arc_reason}
- Pacing: {pacing_score_10}/10 — {pacing_reason}
- Originality: {originality_score_10}/10 — {originality_reason}
- Strategic Alignment: {alignment_score_10}/10 — {alignment_reason}

Overall Score: {overall_score_10}/10 (Threshold: 8.5/10)
Rewrite Round: {rewrite_round}/3

For each metric scoring below 8.5, provide:
1. Exact weakness in the current script.
2. Concrete prescription (e.g. rewrite hook to start with a contrast statistic; trim segment 3 by 4 words).
3. Example spoken line showing how to fix it.

Return ONLY valid JSON:
{{
  "rewrite_suggestions": [
    "Hook Strength (7.5/10): Replace opening question with a counter-intuitive stat like '68% of 110+ GS scorers fail CSAT'.",
    "Pacing (8.0/10): Segment 3 currently has 28 words; cut filler adjectives to reach exactly 21 words."
  ],
  "qualitative_summary": "Good strategic alignment but hook lacks urgency and segment 3 drags."
}}
"""

async def critic_node(state: AgentState) -> Dict[str, Any]:
    """Critic Agent: Evaluates script using parallel G-Eval metrics and provides qualitative coaching."""
    current_script = state["current_script"]
    strategy = state["strategy"]
    rewrite_count = state.get("rewrite_count", 1)

    script_text = json.dumps(current_script, indent=2)
    strategy_text = f"Topic: {strategy.get('topic')}, Bucket: {strategy.get('content_bucket')}, Hook: {strategy.get('hook_style')}, Format: {strategy.get('format')}, Tone: {strategy.get('tone')}"

    # Step 1: Run calibrated G-Eval in parallel
    evaluation = await evaluate_script(
        script_text=script_text,
        strategy_context=strategy_text,
    )

    # Step 2: If score < 8.5/10, generate qualitative rewrite instructions
    if not evaluation.pass_threshold:
        llm = get_llm(temperature=0.3)
        prompt = CRITIC_QUALITATIVE_PROMPT.format(
            script=script_text,
            strategy=strategy_text,
            hook_score_10=evaluation.hook_strength.score_10,
            hook_reason=evaluation.hook_strength.reason,
            arc_score_10=evaluation.emotional_arc.score_10,
            arc_reason=evaluation.emotional_arc.reason,
            pacing_score_10=evaluation.pacing.score_10,
            pacing_reason=evaluation.pacing.reason,
            originality_score_10=evaluation.originality.score_10,
            originality_reason=evaluation.originality.reason,
            alignment_score_10=evaluation.strategic_alignment.score_10,
            alignment_reason=evaluation.strategic_alignment.reason,
            overall_score_10=evaluation.overall_score_10,
            rewrite_round=rewrite_count,
        )
        try:
            response = await llm.ainvoke(prompt)
            data = _extract_json(response.content)
            llm_suggestions = data.get("rewrite_suggestions", [])
            if llm_suggestions:
                evaluation.rewrite_suggestions = llm_suggestions
            if data.get("qualitative_summary"):
                evaluation.qualitative_feedback = f"{data['qualitative_summary']} | {evaluation.qualitative_feedback}"
        except Exception:
            pass  # Fall back to default rewrite suggestions already populated from G-Eval reasons

    # Step 3: Track best script and best score across rewrite rounds
    best_script = state.get("best_script")
    best_score = state.get("best_score", 0.0)

    if evaluation.overall_score > best_score or best_script is None:
        best_script = current_script
        best_score = evaluation.overall_score

    all_evals = list(state.get("all_evaluations", []))
    all_evals.append(evaluation.model_dump())

    return {
        "evaluation": evaluation.model_dump(),
        "all_evaluations": all_evals,
        "best_script": best_script,
        "best_score": best_score,
    }
