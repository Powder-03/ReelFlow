import json
import re
from typing import Dict, Any

from app.agents.state import AgentState
from app.core.llm import get_llm
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

MEMORY_PROMPT = """You are a Performance Memory & Audience Retention Analyst.

Analyze the account's historical winners, losers, breakout content, fatigue registry, and competitor benchmarks:
1. top_performers: Key factors that drove viral retention and saves in top posts.
2. successful_hooks: Hook styles and psychological triggers that stop the scroll consistently.
3. successful_formats: Which formats (talking head, text overlay, voiceover montage, skit) achieve maximum retention.
4. fatigued_topics: Exhausted topics from the fatigue registry and over-saturated angles to strictly avoid.
5. competitor_insights: Actionable insights from competitor wins and mistakes (ethical differentiation, no direct copying).

Historical Top 5 Posts:
{top_posts}

Breakout Content (High Standard Deviation):
{breakout_posts}

Fatigued Topics Registry:
{fatigued_registry}

Competitor Intelligence:
{competitors}

Return ONLY valid JSON matching this structure:
{{
  "top_performers": [
    {{"post_id": "string", "topic": "string", "why_it_worked": "string"}}
  ],
  "successful_hooks": ["string"],
  "successful_formats": ["string"],
  "fatigued_topics": ["string"],
  "competitor_insights": [
    {{"competitor": "string", "opportunity": "string", "avoid": "string"}}
  ]
}}
"""

async def memory_node(state: AgentState) -> Dict[str, Any]:
    """Memory Agent: Retrieves historical performance patterns and synthesizes memory insights."""
    store = JsonStore()
    top_posts = store.get_top_performing(limit=5)
    breakout_posts = store.detect_breakout_content()
    fatigued_registry = store.get_fatigued_topics()
    competitors = store.load_competitors()

    llm = get_llm(temperature=0.4)
    prompt = MEMORY_PROMPT.format(
        top_posts=json.dumps([p.model_dump() for p in top_posts], default=str, indent=2),
        breakout_posts=json.dumps([p.model_dump() for p in breakout_posts], default=str, indent=2),
        fatigued_registry=json.dumps(fatigued_registry, indent=2),
        competitors=json.dumps(competitors, indent=2),
    )

    response = await llm.ainvoke(prompt)
    try:
        data = _extract_json(response.content)
    except Exception:
        data = {
            "top_performers": [{"post_id": p.post_id, "topic": p.topic, "why_it_worked": "High curiosity and clear utility"} for p in top_posts[:3]],
            "successful_hooks": ["shock_stat", "personal_story", "question"],
            "successful_formats": ["talking_head", "text_overlay"],
            "fatigued_topics": fatigued_registry,
            "competitor_insights": [{"competitor": "@civilservices_mantra", "opportunity": "Make answers conversational instead of textbook dry", "avoid": "Sensational clickbait"}],
        }

    # Ensure fatigued topics include the registry
    combined_fatigued = list(set(data.get("fatigued_topics", []) + fatigued_registry))

    return {
        "top_performers": data.get("top_performers", []),
        "successful_hooks": data.get("successful_hooks", []),
        "successful_formats": data.get("successful_formats", []),
        "fatigued_topics": combined_fatigued,
        "competitor_insights": data.get("competitor_insights", []),
    }
