from deepeval.metrics import GEval
from deepeval.test_case import SingleTurnParams
from app.core.llm import get_eval_model

def create_hook_strength_metric() -> GEval:
    """Evaluates whether the hook stops the scroll in 2 seconds."""
    return GEval(
        name="Hook Strength",
        model=get_eval_model(),
        evaluation_steps=[
            "Read only the 'hook' field of the script",
            "Check if it creates immediate curiosity, shock, or emotional pull",
            "Assess whether a viewer would stop scrolling within 2 seconds",
            "Penalize generic openings like 'Aaj hum baat karenge...' or 'Hey guys'",
            "Reward specific numbers, bold claims, counter-intuitive statements, or direct questions",
            "A perfect hook makes the viewer feel they'll miss out if they scroll past",
        ],
        evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT],
        threshold=0.85,
    )

def create_emotional_arc_metric() -> GEval:
    """Evaluates the emotional journey across the script."""
    return GEval(
        name="Emotional Arc",
        model=get_eval_model(),
        evaluation_steps=[
            "Read all segments of the script in order",
            "Identify the emotional starting point (hook emotion)",
            "Track how emotion shifts across segments: does it build, dip, then peak?",
            "Check for at least one emotional pivot (surprise, realization, or empathy moment)",
            "Penalize flat emotional trajectories where every segment has the same energy",
            "Reward scripts that end on a higher emotional note than they started",
        ],
        evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT],
        threshold=0.85,
    )

def create_pacing_metric() -> GEval:
    """Evaluates segment length discipline and energy flow."""
    return GEval(
        name="Pacing",
        model=get_eval_model(),
        evaluation_steps=[
            "Count words in each segment — each should be approximately 18-23 words",
            "Segments significantly outside 15-25 words should be penalized",
            "Check that information density is even — no segment is overloaded while others are filler",
            "Verify the script doesn't rush the setup or drag the middle",
            "The CTA should feel earned, not abrupt",
            "Reward rhythmic consistency that would sound natural when spoken aloud",
        ],
        evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT],
        threshold=0.85,
    )

def create_originality_metric() -> GEval:
    """Evaluates freshness and standout potential."""
    return GEval(
        name="Originality",
        model=get_eval_model(),
        evaluation_steps=[
            "Assess whether the angle or perspective is fresh — not a common take on this topic",
            "Check if the hook offers a unique framing that differentiates from typical content",
            "Penalize cliché phrases, overused Instagram tropes, and predictable structures",
            "Reward unexpected analogies, novel comparisons, or unconventional storytelling",
            "Consider: would this script make a viewer share it because they haven't seen this take before?",
        ],
        evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT],
        threshold=0.85,
    )

def create_strategic_alignment_metric(strategy_context: str) -> GEval:
    """Evaluates alignment with the chosen strategy.
    
    Takes the strategy as context via evaluation_steps so the judge knows what to align against.
    """
    return GEval(
        name="Strategic Alignment",
        model=get_eval_model(),
        evaluation_steps=[
            f"The chosen strategy is: {strategy_context}",
            "Verify the script matches the specified content bucket and topic",
            "Check that the hook style matches the strategy's hook_style choice",
            "Verify the tone matches — if strategy says 'high energy', the script shouldn't be mellow",
            "Check the format cues align (e.g., if talking_head, there should be direct-to-camera cues)",
            "Penalize scripts that drift into a different content bucket mid-way",
        ],
        evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT],
        threshold=0.85,
    )
