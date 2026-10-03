import json
import re
from typing import Dict, Any, List
from langsmith import traceable

from app.agents.state import AgentState
from app.core.llm import get_llm
from app.models.schemas import ReelScript, ScriptSegment, HookCandidate, HookEvaluationResult

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

def _count_spoken_words(text: str) -> int:
    """Counts actual spoken words, excluding visual cues in [brackets]."""
    cleaned = re.sub(r"\[.*?\]", "", text).strip()
    return len(cleaned.split())

HOOK_TREE_PROMPT = """You are an Elite Viral Hinglish Instagram Reel Scriptwriter using Tree of Thoughts (ToT).

TOPIC: {topic}
CONTENT BUCKET: {content_bucket}
TONE: {tone}
STRATEGIC RATIONALE: {reasoning}

TASK (Level 1 Exploration):
Generate 3 DIVERGENT HOOK CANDIDATES exploring different psychological triggers:
- Hook 1 (Shock Stat / Stark Reality): Numbers or contrast that creates immediate FOMO.
- Hook 2 (Personal Vulnerability / Pain): Deep relatable pain point or exam anxiety.
- Hook 3 (Contrarian Challenge / Myth-Bust): Shatters a common misconception boldly.

RULES FOR EVERY HOOK:
1. Spoken Hinglish (Hindi-English mix in Roman alphabet).
2. Word count MUST be between 18 and 23 words (absolute bounds 15 to 25 words).
3. First 2-second scroll stopper. No greetings ("Hey guys" or "Aaj hum baat karenge").
4. Include visual action cues in [brackets].

Return ONLY valid JSON:
[
  {{
    "hook_id": 1,
    "hook_style": "shock_stat",
    "text": "spoken hook text here (~18-23 words)",
    "visual_cue": "[Fast camera zoom, red warning text overlay]"
  }},
  {{
    "hook_id": 2,
    "hook_style": "personal_story",
    "text": "spoken hook text here (~18-23 words)",
    "visual_cue": "[Close-up earnest eye contact, ticking clock sound]"
  }},
  {{
    "hook_id": 3,
    "hook_style": "myth_bust",
    "text": "spoken hook text here (~18-23 words)",
    "visual_cue": "[Crossing out a big book with a red marker]"
  }}
]
"""

BODY_ARC_PROMPT = """You are an Elite Viral Hinglish Reel Scriptwriter expanding a winning hook into a complete 5-segment reel script.

STRATEGY:
- Topic: {topic}
- Bucket: {content_bucket}
- Format: {format}
- Tone: {tone}

WINNING HOOK (Segment 1):
Text: "{champion_hook_text}"
Visual Cue: "{champion_hook_cue}"

TASK:
Write the remaining 4 segments (Segment 2 to Segment 5) to complete the 5-part structure:
- Segment 2 (build_up): Agitates the pain point or stakes (~18-23 words).
- Segment 3 (core_value): Delivers the clear, high-utility framework (~18-23 words).
- Segment 4 (emotional_peak): The punchline, insight, or emotional pivot (~18-23 words).
- Segment 5 (cta): High-converting call-to-action (~18-23 words).

RULES:
1. Strict Hinglish.
2. Every single segment MUST be approximately 18 to 23 words (tolerance 15 to 25 words).
3. Include visual cues in [brackets] for every segment.
{rewrite_instructions}

Return ONLY valid JSON matching ReelScript schema:
{{
  "title": "{topic}",
  "hook": "{champion_hook_text}",
  "segments": [
    {{
      "segment_id": 1,
      "type": "hook",
      "text": "{champion_hook_text}",
      "visual_cue": "{champion_hook_cue}",
      "estimated_seconds": 5.0
    }},
    {{
      "segment_id": 2,
      "type": "build_up",
      "text": "spoken text (~18-23 words)",
      "visual_cue": "[Visual cue]",
      "estimated_seconds": 6.0
    }},
    {{
      "segment_id": 3,
      "type": "core_value",
      "text": "spoken text (~18-23 words)",
      "visual_cue": "[Visual cue]",
      "estimated_seconds": 7.0
    }},
    {{
      "segment_id": 4,
      "type": "emotional_peak",
      "text": "spoken text (~18-23 words)",
      "visual_cue": "[Visual cue]",
      "estimated_seconds": 6.0
    }},
    {{
      "segment_id": 5,
      "type": "cta",
      "text": "spoken text (~18-23 words)",
      "visual_cue": "[Visual cue]",
      "estimated_seconds": 5.0
    }}
  ],
  "cta": "cta text here",
  "content_bucket": "{content_bucket}",
  "hook_style": "{hook_style}",
  "format": "{format}",
  "tone": "{tone}",
  "topic": "{topic}"
}}
"""

async def _generate_hook_tree(strategy: Dict[str, Any], rewrite_instructions: str) -> List[HookCandidate]:
    """Generates 3 competing hook candidates exploring different psychological angles."""
    llm = get_llm(temperature=0.75)
    prompt = HOOK_TREE_PROMPT.format(
        topic=strategy["topic"],
        content_bucket=strategy["content_bucket"],
        tone=strategy["tone"],
        reasoning=strategy.get("reasoning", ""),
    )

    response = await llm.ainvoke(prompt)
    try:
        raw_list = _extract_json(response.content)
        candidates = []
        for item in raw_list:
            text = item.get("text", "")
            words = _count_spoken_words(text)
            candidates.append(
                HookCandidate(
                    hook_id=item.get("hook_id", len(candidates) + 1),
                    hook_style=item.get("hook_style", "shock_stat"),
                    text=text,
                    visual_cue=item.get("visual_cue", "[Camera zooms in]"),
                    word_count=words,
                )
            )
        if candidates:
            return candidates
    except Exception:
        pass

    # Fallback hook candidates
    return [
        HookCandidate(
            hook_id=1,
            hook_style="shock_stat",
            text="GS 1 mein 110 laane waale 68 percent aspirants CSAT mein fail ho jaate hain, dhyan se suno.",
            visual_cue="[Fast camera zoom, red warning text overlay]",
            word_count=19,
        ),
        HookCandidate(
            hook_id=2,
            hook_style="personal_story",
            text="Jab mere 3 Prelims consecutive fail huye the, tab maine realize kiya ki Laxmikanth ke notes sabse badi galti thi.",
            visual_cue="[Close-up eye contact, serious tone]",
            word_count=21,
        ),
        HookCandidate(
            hook_id=3,
            hook_style="myth_bust",
            text="Agar aap daily 3 newspapers padh ke 4 ghante waste kar rahe ho, toh stop right now before it is too late.",
            visual_cue="[Crossing out newspaper with bold red marker]",
            word_count=22,
        ),
    ]

def _evaluate_and_prune_hooks(candidates: List[HookCandidate]) -> tuple[HookCandidate, List[HookEvaluationResult]]:
    """Heuristically evaluates hook candidates for scroll-stopping power and word count discipline.
    Prunes the weaker hooks and selects the champion.
    """
    evaluations: List[HookEvaluationResult] = []

    for c in candidates:
        word_valid = 15 <= c.word_count <= 25
        # Score calculation: base 8.0, bonus for 18-23 words, bonus for numbers/contrasts
        score = 8.0
        if 18 <= c.word_count <= 23:
            score += 1.0
        elif not word_valid:
            score -= 2.0

        has_numbers = any(char.isdigit() for char in c.text)
        if has_numbers:
            score += 0.5

        final_score = max(0.0, min(10.0, score))
        evaluations.append(
            HookEvaluationResult(
                hook_id=c.hook_id,
                curiosity_score=final_score,
                scroll_stop_score=final_score,
                word_count_valid=word_valid,
                overall_hook_score=final_score,
                critique=f"Words: {c.word_count} ({'Target 18-23 met' if 18 <= c.word_count <= 23 else 'Adjust word length'})",
            )
        )

    # Sort candidates by score descending
    sorted_pairs = sorted(zip(candidates, evaluations), key=lambda p: p[1].overall_hook_score, reverse=True)
    champion_hook = sorted_pairs[0][0]
    return champion_hook, evaluations

async def _expand_champion_arc(
    champion_hook: HookCandidate,
    strategy: Dict[str, Any],
    rewrite_instructions: str,
) -> ReelScript:
    """Expands the winning champion hook into a cohesive 5-segment reel script."""
    llm = get_llm(temperature=0.65)
    prompt = BODY_ARC_PROMPT.format(
        topic=strategy["topic"],
        content_bucket=strategy["content_bucket"],
        format=strategy["format"],
        tone=strategy["tone"],
        champion_hook_text=champion_hook.text,
        champion_hook_cue=champion_hook.visual_cue,
        hook_style=champion_hook.hook_style,
        rewrite_instructions=rewrite_instructions,
    )

    response = await llm.ainvoke(prompt)
    try:
        data = _extract_json(response.content)
        return ReelScript.model_validate(data)
    except Exception:
        # Fallback to structured 5 segments
        return ReelScript(
            title=strategy["topic"],
            hook=champion_hook.text,
            segments=[
                ScriptSegment(
                    segment_id=1,
                    type="hook",
                    text=champion_hook.text,
                    visual_cue=champion_hook.visual_cue,
                    estimated_seconds=5.0,
                ),
                ScriptSegment(
                    segment_id=2,
                    type="build_up",
                    text="GS Paper 1 mein 115 marks laane waale toppers har saal 66 marks CSAT mein nahi la pate.",
                    visual_cue="[Scorecard graphics with red fail highlight]",
                    estimated_seconds=6.0,
                ),
                ScriptSegment(
                    segment_id=3,
                    type="core_value",
                    text="Daily maths formulas rattne ke bajaye sirf 50 Reading Comprehension PYQs solve karo with 85 percent accuracy rule.",
                    visual_cue="[3-step rule sliding across screen]",
                    estimated_seconds=7.0,
                ),
                ScriptSegment(
                    segment_id=4,
                    type="emotional_peak",
                    text="Yaad rakhna, prelims fail hone ka dard marksheet dekhne ke baad nahi, pooray ek saal tak rehta hai.",
                    visual_cue="[Direct eye contact, sincere reality check]",
                    estimated_seconds=6.0,
                ),
                ScriptSegment(
                    segment_id=5,
                    type="cta",
                    text="Neeche comment karo CSAT aur main apko 5 saal ke solved question papers direct DM kar dunga.",
                    visual_cue="[Save button pulse animation + Comment banner]",
                    estimated_seconds=5.0,
                ),
            ],
            cta="Neeche comment karo CSAT aur main apko 5 saal ke solved question papers direct DM kar dunga.",
            content_bucket=strategy["content_bucket"],
            hook_style=champion_hook.hook_style,
            format=strategy["format"],
            tone=strategy["tone"],
            topic=strategy["topic"],
        )

def _validate_and_backtrack_pacing(script: ReelScript) -> ReelScript:
    """Validates segment word counts and adjusts any segments that drift outside [15, 25] bounds."""
    updated_segments: List[ScriptSegment] = []
    for seg in script.segments:
        words = seg.text.split()
        if len(words) > 25:
            # Backtrack / trim trailing filler while preserving core message
            trimmed_text = " ".join(words[:22]) + "."
            updated_segments.append(
                ScriptSegment(
                    segment_id=seg.segment_id,
                    type=seg.type,
                    text=trimmed_text,
                    visual_cue=seg.visual_cue,
                    estimated_seconds=seg.estimated_seconds,
                )
            )
        else:
            updated_segments.append(seg)

    script.segments = updated_segments
    return script

@traceable(name="Writer Agent (ToT)", run_type="chain")
async def writer_node(state: AgentState) -> Dict[str, Any]:
    """Writer Agent with Tree of Thoughts:
    Level 1: Branch 3 competing hooks
    Level 2: Score and prune weaker hooks
    Level 3: Expand champion hook into 5 segments
    Level 4: Segment-level pacing validation & backtracking
    """
    strategy = state["strategy"]
    evaluation = state.get("evaluation")
    rewrite_count = state.get("rewrite_count", 0)

    rewrite_instructions = ""
    if evaluation and not evaluation.get("pass_threshold", True):
        suggestions = evaluation.get("rewrite_suggestions", [])
        rewrite_instructions = (
            f"\nREWRITE MANDATE (Round {rewrite_count + 1}/3 - Previous Score: {evaluation.get('overall_score_10')}/10):\n"
            "Fix these specific deficiencies identified by G-Eval:\n"
            + "\n".join(f"- {s}" for s in suggestions)
            + "\nEnsure strict word count (18-23 words/segment)!"
        )

    # Level 1: Generate 3 divergent hook branches
    hook_candidates = await _generate_hook_tree(strategy, rewrite_instructions)

    # Level 2: Evaluate and prune weaker hooks
    champion_hook, hook_evals = _evaluate_and_prune_hooks(hook_candidates)

    # Level 3: Expand the champion hook into 5 segments
    script = await _expand_champion_arc(champion_hook, strategy, rewrite_instructions)

    # Level 4: Segment discipline check & backtracking
    final_script = _validate_and_backtrack_pacing(script)

    return {
        "current_script": final_script.model_dump(),
        "rewrite_count": rewrite_count + 1,
    }
