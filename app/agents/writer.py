import json
import re
from typing import Dict, Any

from app.agents.state import AgentState
from app.core.llm import get_llm
from app.models.schemas import ReelScript, ScriptSegment

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

WRITER_PROMPT = """You are an Elite Viral Hinglish Instagram Reel Scriptwriter.

You create high-retention, authentic, scroll-stopping reel scripts that educate and motivate aspirants.

STRATEGY TO EXECUTE:
- Topic: {topic}
- Content Bucket: {content_bucket}
- Hook Style: {hook_style}
- Format: {format}
- Tone: {tone}
- Strategic Reasoning: {reasoning}

CRITICAL SCRIPTING RULES:
1. Language: Authentic spoken Hinglish (casual Hindi in Roman script mixed naturally with English).
2. Segment Length Discipline: Each segment MUST be approximately 18 to 23 words (absolute bounds 15-25 words).
3. 5-Part Segment Structure:
   - Segment 1 (type='hook'): Scroll-stopping hook in the first 2 seconds. No greetings like 'Hey guys' or 'Aaj hum baat karenge'.
   - Segment 2 (type='build_up'): Agitate the pain point or tension.
   - Segment 3 (type='core_value'): Provide the practical, high-value framework or solution.
   - Segment 4 (type='emotional_peak'): The memorable insight, reality check, or empathy pivot.
   - Segment 5 (type='cta'): Clear call-to-action (e.g. comment a keyword for notes, share with study partner).
4. Visual Cues: Include direct camera/screen cues in [brackets] for every segment.

{rewrite_instructions}

Return ONLY valid JSON matching ReelScript schema:
{{
  "title": "string",
  "hook": "string (the exact spoken hook text, ~18-23 words)",
  "segments": [
    {{
      "segment_id": 1,
      "type": "hook",
      "text": "spoken text here (~18-23 words)",
      "visual_cue": "[Fast zoom-in to camera, bold red text overlay: WARNING]",
      "estimated_seconds": 5.0
    }},
    {{
      "segment_id": 2,
      "type": "build_up",
      "text": "spoken text here (~18-23 words)",
      "visual_cue": "[Cut to paper highlights and clock ticking sound effect]",
      "estimated_seconds": 6.0
    }},
    {{
      "segment_id": 3,
      "type": "core_value",
      "text": "spoken text here (~18-23 words)",
      "visual_cue": "[3-step framework cards sliding in from left to right]",
      "estimated_seconds": 7.0
    }},
    {{
      "segment_id": 4,
      "type": "emotional_peak",
      "text": "spoken text here (~18-23 words)",
      "visual_cue": "[Camera slowly pulls back, serious and sincere direct eye contact]",
      "estimated_seconds": 6.0
    }},
    {{
      "segment_id": 5,
      "type": "cta",
      "text": "spoken text here (~18-23 words)",
      "visual_cue": "[Save icon pulse animation + text: Comment 'NOTES' below]",
      "estimated_seconds": 5.0
    }}
  ],
  "cta": "string",
  "content_bucket": "{content_bucket}",
  "hook_style": "{hook_style}",
  "format": "{format}",
  "tone": "{tone}",
  "topic": "{topic}"
}}
"""

async def writer_node(state: AgentState) -> Dict[str, Any]:
    """Writer Agent: Generates viral Hinglish reel scripts following the strategy."""
    strategy = state["strategy"]
    evaluation = state.get("evaluation")
    rewrite_count = state.get("rewrite_count", 0)

    rewrite_instructions = ""
    if evaluation and not evaluation.get("pass_threshold", True):
        suggestions = evaluation.get("rewrite_suggestions", [])
        rewrite_instructions = (
            f"\nREWRITE MANDATE (Round {rewrite_count + 1}/3 - Previous Score: {evaluation.get('overall_score_10')}/10):\n"
            "The previous draft failed G-Eval quality benchmarks. You MUST fix these specific deficiencies:\n"
            + "\n".join(f"- {s}" for s in suggestions)
            + "\nEnsure strict word count (18-23 words/segment) and intensify the hook!"
        )

    llm = get_llm(temperature=0.7)
    prompt = WRITER_PROMPT.format(
        topic=strategy["topic"],
        content_bucket=strategy["content_bucket"],
        hook_style=strategy["hook_style"],
        format=strategy["format"],
        tone=strategy["tone"],
        reasoning=strategy.get("reasoning", ""),
        rewrite_instructions=rewrite_instructions,
    )

    response = await llm.ainvoke(prompt)
    try:
        data = _extract_json(response.content)
        script = ReelScript.model_validate(data)
    except Exception:
        # Fallback script adhering strictly to rules
        segments = [
            ScriptSegment(
                segment_id=1,
                type="hook",
                text="Agar aap CSAT ko lightweight subject samajh rahe ho to yeh reel aapke poore do saal bacha sakti hai.",
                visual_cue="[Camera zooms in, text overlay: CSAT REALITY CHECK]",
                estimated_seconds=5.0,
            ),
            ScriptSegment(
                segment_id=2,
                type="build_up",
                text="GS Paper 1 mein 115 marks laane waale toppers har saal 66 marks CSAT mein nahi la pate.",
                visual_cue="[Cut to scorecard graphics with red fail highlight]",
                estimated_seconds=6.0,
            ),
            ScriptSegment(
                segment_id=3,
                type="core_value",
                text="Daily maths formulas rattne ke bajaye sirf 50 Reading Comprehension PYQs solve karo with 85 percent accuracy rule.",
                visual_cue="[Rule breakdown on whiteboard graphic]",
                estimated_seconds=7.0,
            ),
            ScriptSegment(
                segment_id=4,
                type="emotional_peak",
                text="Yaad rakhna, prelims fail hone ka dard marksheet dekhne ke baad nahi, pooray ek saal tak rehta hai.",
                visual_cue="[Direct eye contact, earnest tone]",
                estimated_seconds=6.0,
            ),
            ScriptSegment(
                segment_id=5,
                type="cta",
                text="Neeche comment karo CSAT aur main apko 5 saal ke solved question papers direct DM kar dunga.",
                visual_cue="[Comment icon animation + save button pointer]",
                estimated_seconds=5.0,
            ),
        ]
        script = ReelScript(
            title=strategy["topic"],
            hook=segments[0].text,
            segments=segments,
            cta=segments[-1].text,
            content_bucket=strategy["content_bucket"],
            hook_style=strategy["hook_style"],
            format=strategy["format"],
            tone=strategy["tone"],
            topic=strategy["topic"],
        )

    return {
        "current_script": script.model_dump(),
        "rewrite_count": rewrite_count + 1,
    }
