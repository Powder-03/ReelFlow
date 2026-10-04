import json
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.models.schemas import (
    Post,
    ReelScript,
    CriticEvaluation,
    AccountProfile,
    EventItem,
)

class JsonStore:
    """Thread-safe JSON file storage for performance memory and sample data."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        memory_dir: Optional[Path] = None,
    ):
        self.data_dir = data_dir or settings.DATA_DIR
        self.memory_dir = memory_dir or settings.MEMORY_DIR
        self._ensure_dirs()

    def _ensure_dirs(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure default memory files exist if not present
        approved_scripts_file = self.memory_dir / "approved_scripts.json"
        if not approved_scripts_file.exists():
            approved_scripts_file.write_text("[]", encoding="utf-8")

        performance_log_file = self.memory_dir / "performance_log.json"
        if not performance_log_file.exists():
            performance_log_file.write_text("[]", encoding="utf-8")

        fatigue_registry_file = self.memory_dir / "fatigue_registry.json"
        if not fatigue_registry_file.exists():
            fatigue_registry_file.write_text("[]", encoding="utf-8")

    def _read_json(self, file_path: Path, default: Any = None) -> Any:
        if not file_path.exists():
            return default if default is not None else []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default if default is not None else []

    def _write_json(self, file_path: Path, data: Any):
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    # --- Sample Data Loaders ---

    def load_account_profile(self) -> AccountProfile:
        path = self.data_dir / "sample_account.json"
        data = self._read_json(path, default={})
        if not data:
            return AccountProfile(
                handle="@upsc_insider",
                niche="UPSC Preparation & Current Affairs",
                followers=125000,
                avg_engagement_rate=4.2,
                content_language="Hinglish",
                top_buckets=["current_affairs", "motivation", "study_tips", "book_reviews", "strategy"],
            )
        return AccountProfile.model_validate(data)

    def load_posts(self) -> List[Post]:
        path = self.data_dir / "sample_posts.json"
        raw_posts = self._read_json(path, default=[])
        return [Post.model_validate(p) for p in raw_posts]

    def load_competitors(self) -> List[Dict[str, Any]]:
        path = self.data_dir / "sample_competitors.json"
        return self._read_json(path, default=[])

    def load_events_calendar(self) -> List[EventItem]:
        path = self.data_dir / "events_calendar.json"
        raw_events = self._read_json(path, default=[])
        return [EventItem.model_validate(e) for e in raw_events]

    # --- Memory Operations ---

    def save_approved_script(self, script: ReelScript, evaluation: CriticEvaluation):
        path = self.memory_dir / "approved_scripts.json"
        records = self._read_json(path, default=[])
        record = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "script": script.model_dump(),
            "evaluation": evaluation.model_dump(),
        }
        records.append(record)
        self._write_json(path, records)

    def get_recent_topics(self, days: int = 14) -> List[str]:
        posts = self.load_posts()
        # Sort by date descending
        posts = sorted(posts, key=lambda x: x.date, reverse=True)
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)
        recent = [
            p.topic for p in posts
            if (p.date.tzinfo is None and p.date >= cutoff.replace(tzinfo=None)) or
               (p.date.tzinfo is not None and p.date >= cutoff)
        ]
        if not recent and posts:
            recent = [p.topic for p in posts[:10]]

        # Also incorporate newly generated & approved scripts from runtime memory
        approved_path = self.memory_dir / "approved_scripts.json"
        approved = self._read_json(approved_path, default=[])
        for rec in reversed(approved):
            script_data = rec.get("script", {})
            topic = script_data.get("topic")
            saved_at_str = rec.get("saved_at")
            if topic:
                if saved_at_str:
                    try:
                        saved_dt = datetime.fromisoformat(saved_at_str)
                        if (saved_dt.tzinfo is None and saved_dt >= cutoff.replace(tzinfo=None)) or \
                           (saved_dt.tzinfo is not None and saved_dt >= cutoff):
                            if topic not in recent:
                                recent.insert(0, topic)
                    except Exception:
                        if topic not in recent:
                            recent.insert(0, topic)
                else:
                    if topic not in recent:
                        recent.insert(0, topic)
        return recent

    def get_recent_hook_styles(self, count: int = 5) -> List[str]:
        # Prepend hooks from newly approved scripts in runtime memory
        approved_path = self.memory_dir / "approved_scripts.json"
        approved = self._read_json(approved_path, default=[])
        runtime_hooks = [
            rec["script"]["hook_style"]
            for rec in reversed(approved)
            if "script" in rec and "hook_style" in rec["script"]
        ]
        posts = sorted(self.load_posts(), key=lambda x: x.date, reverse=True)
        post_hooks = [p.hook_style for p in posts]
        all_hooks = runtime_hooks + post_hooks
        return all_hooks[:count]

    def get_recent_formats(self, count: int = 5) -> List[str]:
        # Prepend formats from newly approved scripts in runtime memory
        approved_path = self.memory_dir / "approved_scripts.json"
        approved = self._read_json(approved_path, default=[])
        runtime_formats = [
            rec["script"]["format"]
            for rec in reversed(approved)
            if "script" in rec and "format" in rec["script"]
        ]
        posts = sorted(self.load_posts(), key=lambda x: x.date, reverse=True)
        post_formats = [p.format for p in posts]
        all_formats = runtime_formats + post_formats
        return all_formats[:count]

    def get_top_performing(self, metric: str = "engagement_rate", limit: int = 10) -> List[Post]:
        posts = self.load_posts()
        return sorted(posts, key=lambda x: getattr(x, metric, 0), reverse=True)[:limit]

    def get_underperforming(self, threshold: float = 3.0) -> List[Post]:
        posts = self.load_posts()
        return [p for p in posts if p.engagement_rate < threshold]

    def mark_fatigued(self, topic: str, reason: str):
        path = self.memory_dir / "fatigue_registry.json"
        registry = self._read_json(path, default=[])
        # Check if already registered
        for item in registry:
            if item.get("topic", "").lower() == topic.lower():
                item["reason"] = reason
                item["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._write_json(path, registry)
                return
        registry.append({
            "topic": topic,
            "reason": reason,
            "added_at": datetime.now(timezone.utc).isoformat(),
        })
        self._write_json(path, registry)

    def get_fatigued_topics(self) -> List[str]:
        path = self.memory_dir / "fatigue_registry.json"
        registry = self._read_json(path, default=[])
        return [item["topic"] for item in registry if "topic" in item]

    def detect_breakout_content(self, std_multiplier: float = 2.0) -> List[Post]:
        posts = self.load_posts()
        if len(posts) < 3:
            return []
        rates = [p.engagement_rate for p in posts]
        mean_rate = statistics.mean(rates)
        stdev_rate = statistics.stdev(rates) if len(rates) > 1 else 0
        threshold = mean_rate + (std_multiplier * stdev_rate)
        return [p for p in posts if p.engagement_rate >= threshold]

    def log_performance(self, script_id: str, metrics: Dict[str, Any]):
        path = self.memory_dir / "performance_log.json"
        logs = self._read_json(path, default=[])
        logs.append({
            "script_id": script_id,
            "logged_at": datetime.now(timezone.utc).isoformat(),
            **metrics,
        })
        self._write_json(path, logs)

    def get_best_performing_combination(
        self,
        exclude_topics: List[str],
        exclude_hooks: List[str],
        exclude_formats: List[str],
    ) -> Dict[str, Any]:
        """Find the highest-performing topic/bucket/hook/format combination
        from historical data, excluding fatigued/recently-used items.
        
        Used by guardrails fallback when Strategy Agent fails repeatedly.
        """
        posts = self.load_posts()
        if not posts:
            return {
                "topic": "Prelims CSAT Error Elimination Strategy",
                "content_bucket": "study_tips",
                "hook_style": "shock_stat",
                "format": "talking_head",
                "tone": "Empathetic, structured and authoritative",
                "source_post_id": "fallback_default",
                "engagement_rate": 5.0,
            }

        sorted_posts = sorted(posts, key=lambda x: x.engagement_rate, reverse=True)
        exclude_topics_lower = {t.lower() for t in exclude_topics}
        exclude_hooks_lower = {h.lower() for h in exclude_hooks}
        exclude_formats_lower = {f.lower() for f in exclude_formats}

        # 1. Try strict match: topic not in exclude_topics, hook not in exclude_hooks, format not in exclude_formats
        for p in sorted_posts:
            if (
                p.topic.lower() not in exclude_topics_lower
                and p.hook_style.lower() not in exclude_hooks_lower
                and p.format.lower() not in exclude_formats_lower
            ):
                return {
                    "topic": p.topic,
                    "content_bucket": p.content_bucket,
                    "hook_style": p.hook_style,
                    "format": p.format,
                    "tone": "High conviction and analytical",
                    "source_post_id": p.post_id,
                    "engagement_rate": p.engagement_rate,
                }

        # 2. Relax hook and format constraint, but strictly respect excluded fatigued topics
        for p in sorted_posts:
            if p.topic.lower() not in exclude_topics_lower:
                return {
                    "topic": p.topic,
                    "content_bucket": p.content_bucket,
                    "hook_style": p.hook_style,
                    "format": p.format,
                    "tone": "Authoritative and engaging",
                    "source_post_id": p.post_id,
                    "engagement_rate": p.engagement_rate,
                }

        # 3. If even that fails, pick the overall best performing post
        best = sorted_posts[0]
        return {
            "topic": f"{best.topic} (Fresh Angle)",
            "content_bucket": best.content_bucket,
            "hook_style": best.hook_style,
            "format": best.format,
            "tone": "Fresh perspective and sharp breakdown",
            "source_post_id": best.post_id,
            "engagement_rate": best.engagement_rate,
        }
