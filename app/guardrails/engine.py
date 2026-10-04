import re
from datetime import datetime, date, timedelta, timezone
from typing import List, Optional, Set
from app.models.schemas import StrategyDecision, GuardrailResult
from app.store.json_store import JsonStore
from app.core.config import settings

class GuardrailsEngine:
    """Deterministic content guardrails with bounded retry and historical fallback."""

    def __init__(self, max_retries: int = settings.MAX_GUARDRAIL_RETRIES):
        self.max_retries = max_retries

    def _normalize_text(self, text: str) -> Set[str]:
        """Normalize text into lower-cased tokens without punctuation/common stop words."""
        stop_words = {"the", "a", "an", "in", "on", "of", "for", "to", "and", "or", "is", "are", "vs", "with", "how", "why", "what"}
        tokens = re.findall(r"\b\w+\b", text.lower())
        return {t for t in tokens if t not in stop_words and len(t) > 2}

    def check_topic_repetition(self, topic: str, recent_topics: List[str]) -> bool:
        """Returns True if topic is clean (no unacceptable overlap), False if repetitive."""
        topic_tokens = self._normalize_text(topic)
        if not topic_tokens:
            return True

        for recent in recent_topics:
            recent_tokens = self._normalize_text(recent)
            if not recent_tokens:
                continue
            intersection = topic_tokens.intersection(recent_tokens)
            # If 50% or more key tokens overlap, consider it repetitive
            overlap_ratio = len(intersection) / min(len(topic_tokens), len(recent_tokens))
            if overlap_ratio >= 0.5:
                return False
        return True

    def check_hook_rotation(self, hook_style: str, recent_hooks: List[str]) -> bool:
        """Returns True if hook passes rotation check.
        Fails if the proposed hook was used in both of the last 2 posts.
        """
        if len(recent_hooks) >= 2 and recent_hooks[0].lower() == hook_style.lower() and recent_hooks[1].lower() == hook_style.lower():
            return False
        return True

    def check_format_cooldown(self, format_style: str, recent_formats: List[str]) -> bool:
        """Returns True if format passes cooldown check.
        Fails if the format was used in 2 or more of the last 3 posts.
        """
        if len(recent_formats) >= 3:
            count = sum(1 for f in recent_formats[:3] if f.lower() == format_style.lower())
            if count >= 2:
                return False
        return True

    def validate_event_timestamp(self, event_date_str: str) -> bool:
        """Ensures the event date is valid and not older than 30 days."""
        try:
            event_dt = datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if (now - event_dt) > timedelta(days=30):
                return False
            return True
        except (ValueError, TypeError):
            return True  # If not parseable as date, don't fail hard

    def validate_segment_word_count(self, text: str, min_words: int = 15, max_words: int = 26) -> bool:
        """Validates that a script segment has roughly 18-23 words (tolerance 15-26)."""
        words = [w for w in text.split() if not (w.startswith("[") and w.endswith("]"))]
        return min_words <= len(words) <= max_words

    def rotate_hook_style(self, current_hook: str, recent_hooks: List[str]) -> str:
        """Deterministically selects a fresh hook style when repetition is detected."""
        all_hooks = ["question", "personal_story", "myth_bust", "shock_stat", "challenge"]
        exclude = {h.lower() for h in recent_hooks[:2]}
        exclude.add(current_hook.lower())
        for h in all_hooks:
            if h.lower() not in exclude:
                return h
        return "question" if current_hook.lower() != "question" else "personal_story"

    def run_all_checks(
        self,
        strategy: StrategyDecision,
        store: JsonStore,
        retry_count: int = 0,
        auto_rotate_hook: bool = False,
    ) -> GuardrailResult:
        """Runs all deterministic guardrail checks and records audit logs."""
        violations: List[str] = []
        hook_changed = False
        original_hook = strategy.hook_style
        rotated_hook: Optional[str] = None

        # 1. Fatigued topics check
        fatigued_topics = store.get_fatigued_topics()
        for fat in fatigued_topics:
            if fat.lower() in strategy.topic.lower() or strategy.topic.lower() in fat.lower():
                violations.append(f"TOPIC_FATIGUED: '{strategy.topic}' matches fatigued topic '{fat}'")

        # 2. Topic repetition check against recent posts (14 days)
        recent_topics = store.get_recent_topics(days=14)
        if not self.check_topic_repetition(strategy.topic, recent_topics):
            violations.append(f"TOPIC_REPETITION: '{strategy.topic}' overlaps heavily with recent posts")

        # 3. Hook rotation check
        recent_hooks = store.get_recent_hook_styles(count=3)
        if not self.check_hook_rotation(strategy.hook_style, recent_hooks):
            violations.append(f"HOOK_FATIGUE: '{strategy.hook_style}' has been used consecutively in recent posts")
            rotated_hook = self.rotate_hook_style(strategy.hook_style, recent_hooks)
            hook_changed = True
            if auto_rotate_hook:
                strategy.hook_style = rotated_hook
                violations = [v for v in violations if not v.startswith("HOOK_FATIGUE")]

        # 4. Format cooldown check
        recent_formats = store.get_recent_formats(count=3)
        if not self.check_format_cooldown(strategy.format, recent_formats):
            violations.append(f"FORMAT_OVERUSED: '{strategy.format}' has been used >=2 times in the last 3 posts")

        # Build Result
        if not violations:
            result = GuardrailResult(
                passed=True,
                violations=[],
                retry_count=retry_count,
                auto_picked=False,
                hook_changed=hook_changed,
                original_hook=original_hook,
                rotated_hook=rotated_hook,
            )
        elif retry_count >= self.max_retries:
            # BOUNDED FALLBACK
            best_combo = store.get_best_performing_combination(
                exclude_topics=fatigued_topics,
                exclude_hooks=store.get_recent_hook_styles(count=2),
                exclude_formats=store.get_recent_formats(count=2),
            )
            result = GuardrailResult(
                passed=True,
                violations=violations + [
                    f"FALLBACK_TRIGGERED: Strategy Agent failed guardrails {retry_count} times. "
                    "Auto-selected historical best-performing combination with needs_human_review=True."
                ],
                retry_count=retry_count,
                auto_picked=True,
                auto_picked_strategy=best_combo,
                hook_changed=hook_changed,
                original_hook=original_hook,
                rotated_hook=rotated_hook,
            )
        else:
            result = GuardrailResult(
                passed=False,
                violations=violations,
                retry_count=retry_count,
                auto_picked=False,
                hook_changed=hook_changed,
                original_hook=original_hook,
                rotated_hook=rotated_hook,
            )

        # Save audit log to memory
        store.log_guardrail_audit(
            strategy_topic=strategy.topic,
            hook_style=strategy.hook_style,
            passed=result.passed,
            violations=result.violations,
            reasoning=strategy.reasoning,
            confidence=strategy.confidence,
            hook_changed=result.hook_changed,
            original_hook=result.original_hook,
            rotated_hook=result.rotated_hook,
            auto_picked=result.auto_picked,
        )

        return result
