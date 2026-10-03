import json
import re
from typing import Dict, Any

from app.agents.state import AgentState
from app.core.llm import get_llm
from app.models.schemas import ReelScript, CriticEvaluation
from app.store.json_store import JsonStore

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

FEEDBACK_PROMPT = """You are a Continuous Learning & Content Feedback Agent.

Analyze the approved reel script, its evaluation scores, and projected audience response:
1. learning_points: What core patterns made this script succeed (or what limits were reached)?
2. fatigue_recommendation: Should this topic or angle now be put on cooldown/fatigued list? Why?
3. format_verdict: Should this format remain in rotation or enter a cooldown period?
4. future_guidance: Specific tactical recommendation for the next content cycle.

Final Script:
{script}

Critic Evaluation (G-Eval):
{evaluation}

Return ONLY valid JSON:
{{
  "learning_points": ["string"],
  "mark_as_fatigued": false,
  "fatigue_reason": "",
  "format_verdict": "string",
  "future_guidance": "string"
}}
"""

async def feedback_node(state: AgentState) -> Dict[str, Any]:
    """Feedback Agent: Learns from approved content and updates performance memory."""
    store = JsonStore()
    
    # Pick the best script obtained during the generation cycles
    final_script_dict = state.get("best_script") or state.get("current_script")
    evaluation_dict = state.get("evaluation")

    final_script = ReelScript.model_validate(final_script_dict)
    evaluation = CriticEvaluation.model_validate(evaluation_dict)

    # Persist the approved script to memory
    store.save_approved_script(final_script, evaluation)

    llm = get_llm(temperature=0.3)
    prompt = FEEDBACK_PROMPT.format(
        script=final_script.model_dump_json(indent=2),
        evaluation=evaluation.model_dump_json(indent=2),
    )

    try:
        response = await llm.ainvoke(prompt)
        feedback_data = _extract_json(response.content)
        if feedback_data.get("mark_as_fatigued"):
            store.mark_fatigued(
                topic=final_script.topic,
                reason=feedback_data.get("fatigue_reason") or "Topic reached saturation threshold after publication",
            )
    except Exception:
        pass

    return {
        "approved_script": final_script.model_dump(),
    }
