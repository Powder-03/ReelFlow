from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, computed_field

class Post(BaseModel):
    post_id: str
    date: datetime
    content_bucket: str          # e.g., "motivation", "study_tips", "news_reaction"
    hook_style: str              # e.g., "question", "shock_stat", "personal_story"
    format: str                  # e.g., "talking_head", "text_overlay", "skit"
    topic: str
    engagement_rate: float
    views: int
    saves: int
    shares: int
    comments: int

class ScriptSegment(BaseModel):
    segment_id: int
    type: str                    # hook, build_up, core_value, emotional_peak, cta
    text: str                    # Aiming for ~18-23 words in Hinglish
    visual_cue: str              # [e.g. Camera zooms in, text overlay appears]
    estimated_seconds: float = 6.0

class ReelScript(BaseModel):
    title: str
    hook: str                    # Opening hook (~18-23 words)
    segments: List[ScriptSegment]
    cta: str                     # Call to action
    content_bucket: str
    hook_style: str
    format: str
    tone: str
    topic: str

# --- Tree of Thoughts (ToT) Schemas ---

class HookCandidate(BaseModel):
    """Candidate hook branch generated during ToT Level 1 exploration."""
    hook_id: int
    hook_style: str             # shock_stat, personal_story, myth_bust, challenge, question
    text: str                   # Spoken hook (~18-23 words)
    visual_cue: str             # [Visual cue description]
    word_count: int

class HookEvaluationResult(BaseModel):
    """Heuristic scoring of candidate hook in ToT Level 2."""
    hook_id: int
    curiosity_score: float      # 0.0 to 10.0
    scroll_stop_score: float    # 0.0 to 10.0
    word_count_valid: bool      # True if 15 <= word_count <= 25
    overall_hook_score: float   # 0.0 to 10.0
    critique: str

class StrategyHypothesis(BaseModel):
    """Candidate strategy branch in Strategy ToT."""
    hypothesis_id: int
    topic: str
    content_bucket: str
    hook_style: str
    format: str
    tone: str
    rationale: str
    confidence: float = 0.85

class GEvalScore(BaseModel):
    """Individual G-Eval metric result."""
    metric_name: str             # e.g., "hook_strength"
    score: float                 # 0.0-1.0 (normalized by DeepEval)
    score_10: float              # 0.0-10.0 (score * 10, for recruiter display)
    reason: str                  # CoT explanation from G-Eval
    evaluation_steps: List[str] = Field(default_factory=list)

class CriticEvaluation(BaseModel):
    """Aggregated evaluation from 5 G-Eval metrics."""
    hook_strength: GEvalScore
    emotional_arc: GEvalScore
    pacing: GEvalScore
    originality: GEvalScore
    strategic_alignment: GEvalScore
    overall_score: float         # Weighted average (0-1), used internally
    overall_score_10: float      # Weighted average (0-10), recruiter-facing
    qualitative_feedback: str    # LLM-generated summary of strengths/weaknesses
    pass_threshold: bool         # overall_score >= 0.85 (i.e. 8.5/10)
    rewrite_suggestions: List[str] = Field(default_factory=list)

class StrategyDecision(BaseModel):
    topic: str
    content_bucket: str
    hook_style: str
    format: str
    tone: str
    reasoning: str               # Why this idea was selected
    confidence: float            # 0.0 to 1.0
    avoid_topics: List[str] = Field(default_factory=list)
    avoid_formats: List[str] = Field(default_factory=list)
    needs_human_review: bool = False
    auto_pick_reason: str = ""

class GuardrailResult(BaseModel):
    passed: bool
    violations: List[str] = Field(default_factory=list)
    retry_count: int = 0
    auto_picked: bool = False
    auto_picked_strategy: Optional[Dict[str, Any]] = None
    hook_changed: bool = False
    original_hook: Optional[str] = None
    rotated_hook: Optional[str] = None

class AccountProfile(BaseModel):
    handle: str
    niche: str
    followers: int
    avg_engagement_rate: float
    content_language: str
    top_buckets: List[str] = Field(default_factory=list)

class EventItem(BaseModel):
    event_name: str
    date: str
    category: str
    relevance_to_niche: str

class GenerateRequest(BaseModel):
    account_handle: str = "@upsc_insider"
    content_request: Optional[str] = None

class GenerateResponse(BaseModel):
    status: str
    script: Optional[ReelScript] = None
    evaluation: Optional[CriticEvaluation] = None
    strategy: Optional[StrategyDecision] = None
    rewrites_done: int = 0
    needs_human_review: bool = False
    all_evaluations: List[CriticEvaluation] = Field(default_factory=list)
    error: Optional[str] = None

class FeedbackRequest(BaseModel):
    script_id: str
    engagement_rate: float
    views: int
    saves: int
    shares: int
    comments: int
