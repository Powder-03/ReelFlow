import json
import re
from datetime import datetime, timezone
from typing import Dict, Any

from app.agents.state import AgentState
from app.core.llm import get_llm
from app.store.json_store import JsonStore

def _extract_json(text: str) -> Dict[str, Any]:
    """Helper to cleanly parse JSON from LLM markdown responses."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    # Try finding first { to last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1:
        return json.loads(text[first_brace : last_brace + 1])
    return json.loads(text)

INTELLIGENCE_PROMPT = """You are an Instagram Content Intelligence Analyst specializing in high-growth educational & creator accounts.

Given the account profile, recent post history, and events calendar, analyze:
1. upcoming_events: Upcoming events/festivals/milestones relevant to the account's niche with strategic content angles.
2. trending_topics: 3-5 current high-velocity trending topics in this niche right now.
3. account_analysis: An overview of account health, average engagement, and audience behavior patterns.
4. content_gaps: 3-5 high-value topics the audience desperately needs but haven't been covered in recent posts.

Account Profile:
{account_data}

Recent Posts (Last 10):
{recent_posts}

Events Calendar:
{events}

Today's Date: {today}
Optional User Content Request: {content_request}

Return ONLY valid JSON matching this structure:
{{
  "upcoming_events": [
    {{"event_name": "string", "date": "string", "angle": "string"}}
  ],
  "trending_topics": ["string"],
  "account_analysis": {{
    "avg_engagement": 4.2,
    "primary_audience_state": "string",
    "recent_strengths": ["string"],
    "fatigue_signals": ["string"]
  }},
  "content_gaps": ["string"]
}}
"""

async def intelligence_node(state: AgentState) -> Dict[str, Any]:
    """Intelligence Agent: Analyzes account performance, events calendar, and niche trends."""
    store = JsonStore()
    account_profile = store.load_account_profile()
    recent_posts = store.load_posts()[:10]
    events = store.load_events_calendar()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    llm = get_llm(temperature=0.5)
    prompt = INTELLIGENCE_PROMPT.format(
        account_data=account_profile.model_dump_json(indent=2),
        recent_posts=json.dumps([p.model_dump() for p in recent_posts], default=str, indent=2),
        events=json.dumps([e.model_dump() for e in events], indent=2),
        today=today,
        content_request=state.get("content_request") or "None specified",
    )

    response = await llm.ainvoke(prompt)
    try:
        data = _extract_json(response.content)
    except Exception:
        data = {
            "upcoming_events": [{"event_name": e.event_name, "date": e.date, "angle": e.relevance_to_niche} for e in events[:3]],
            "trending_topics": ["CSAT Cutoff Strategy", "Ethics GS4 Case Studies", "One Nation One Election"],
            "account_analysis": {"avg_engagement": account_profile.avg_engagement_rate, "primary_audience_state": "Exam revision stress"},
            "content_gaps": ["Answer writing for beginners", "Time management between Prelims and Mains"],
        }

    return {
        "upcoming_events": data.get("upcoming_events", []),
        "trending_topics": data.get("trending_topics", []),
        "account_analysis": data.get("account_analysis", {}),
        "content_gaps": data.get("content_gaps", []),
    }
