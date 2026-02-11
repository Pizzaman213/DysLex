"""Error Profile Service — the adaptive brain of DysLex AI.

Replaces hardcoded stubs with a real service that reads from normalized
PostgreSQL tables and builds personalised LLM context for every prompt.
"""

import asyncio
import logging
from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import (
    error_log_repo,
    personal_dictionary_repo,
    progress_snapshot_repo,
    user_confusion_pair_repo,
    user_error_pattern_repo,
)
from app.db.repositories import progress_repo, settings_repo, document_repo
from app.services.redis_client import cache_delete, cache_get, cache_set
from app.models.error_log import (
    ErrorProfile,
    ErrorProfileUpdate,
    ErrorTypeBreakdown,
    FullErrorProfile,
    LLMContext,
    PersonalDictionaryEntry,
    UserConfusionPairResponse,
    UserErrorPatternResponse,
)
from app.models.progress import ProgressSnapshotResponse

logger = logging.getLogger(__name__)

# Error types that indicate homophone confusion
_HOMOPHONE_TYPES = {"homophone", "confusion", "real-word"}


class ErrorProfileService:
    """Central service for all error-profile operations."""

    # ------------------------------------------------------------------
    # Core profile access
    # ------------------------------------------------------------------

    async def get_full_profile(
        self, user_id: str, db: AsyncSession
    ) -> FullErrorProfile:
        """Assemble a complete error profile from all normalized tables.

        Uses get_profile_data() to fetch all patterns in 1 query instead of 6.
        Total queries: 1 (patterns) + 1 (confusion pairs) + 1 (dictionary) = 3.
        Results are cached in Redis for 10 minutes.
        """
        cache_key = f"profile:{user_id}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return FullErrorProfile(**cached)

        profile_data = await user_error_pattern_repo.get_profile_data(db, user_id)
        pairs = await user_confusion_pair_repo.get_pairs_for_user(db, user_id, limit=50)
        dictionary = await personal_dictionary_repo.get_dictionary(db, user_id)

        top_patterns = profile_data["top_patterns"]
        mastered = profile_data["mastered_patterns"]
        total = profile_data["total_count"]
        type_counts = profile_data["type_counts"]

        # Build breakdown from type_counts
        breakdown = self._build_breakdown(type_counts)

        # Compute a simple overall score: ratio of mastered to total patterns
        overall_score = 50  # default for new users
        if total > 0:
            overall_score = min(100, int((len(mastered) / total) * 100))

        result = FullErrorProfile(
            user_id=user_id,
            top_errors=[UserErrorPatternResponse.model_validate(p) for p in top_patterns],
            error_type_breakdown=breakdown,
            confusion_pairs=[UserConfusionPairResponse.model_validate(p) for p in pairs],
            personal_dictionary=[PersonalDictionaryEntry.model_validate(d) for d in dictionary],
            patterns_mastered=len(mastered),
            total_patterns=total,
            overall_score=overall_score,
        )
        await cache_set(cache_key, result.model_dump(), ttl_seconds=600)
        return result

    async def get_top_errors(
        self, user_id: str, db: AsyncSession, limit: int = 20
    ) -> list[UserErrorPatternResponse]:
        patterns = await user_error_pattern_repo.get_top_patterns(db, user_id, limit)
        return [UserErrorPatternResponse.model_validate(p) for p in patterns]

    async def get_confusion_pairs(
        self, user_id: str, db: AsyncSession
    ) -> list[UserConfusionPairResponse]:
        pairs = await user_confusion_pair_repo.get_pairs_for_user(db, user_id)
        return [UserConfusionPairResponse.model_validate(p) for p in pairs]

    def _build_breakdown(self, type_counts: list[tuple[str, int]]) -> ErrorTypeBreakdown:
        """Build ErrorTypeBreakdown from pre-computed type counts."""
        total = sum(c for _, c in type_counts) or 1
        breakdown: dict[str, float] = {}
        for error_type, count in type_counts:
            key = _normalize_error_type(error_type)
            breakdown[key] = breakdown.get(key, 0.0) + round(count / total * 100, 1)
        return ErrorTypeBreakdown(**breakdown)

    async def get_error_type_breakdown(
        self, user_id: str, db: AsyncSession
    ) -> ErrorTypeBreakdown:
        counts = await user_error_pattern_repo.get_error_type_counts(db, user_id)
        return self._build_breakdown(counts)

    # ------------------------------------------------------------------
    # build_llm_context — the critical method
    # ------------------------------------------------------------------

    async def build_llm_context(
        self, user_id: str, db: AsyncSession
    ) -> LLMContext:
        """Build the context blob injected into every Nemotron prompt.

        Uses get_profile_data() to reduce queries: 1 (patterns) + 1 (pairs) + 1 (dict) = 3.
        Then fetches enrichment data (trends, stats, streak, settings, documents) in parallel.
        Results are cached in Redis for 10 minutes.
        """
        cache_key = f"llm_context:{user_id}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return LLMContext(**cached)

        profile_data = await user_error_pattern_repo.get_profile_data(db, user_id)
        pairs = await user_confusion_pair_repo.get_pairs_for_user(db, user_id, limit=10)
        dictionary = await personal_dictionary_repo.get_dictionary(db, user_id)

        top_patterns = profile_data["top_patterns"]
        total = profile_data["total_count"]
        type_counts = profile_data["type_counts"]

        breakdown = self._build_breakdown(type_counts)

        # Fetch enrichment data in parallel — all gracefully degradable
        results = await asyncio.gather(
            progress_repo.get_improvement_by_error_type(db, user_id),
            progress_repo.get_mastered_words(db, user_id),
            progress_repo.get_total_stats(db, user_id),
            progress_repo.get_writing_streak(db, user_id),
            progress_repo.get_top_errors(db, user_id),
            settings_repo.get_settings_by_user_id(db, user_id),
            document_repo.get_documents_by_user(db, user_id),
            return_exceptions=True,
        )

        trends_result = results[0]
        mastered_result = results[1]
        stats_result = results[2]
        streak_result = results[3]
        top_errors_result = results[4]
        user_settings_result = results[5]
        docs_result = results[6]

        improvement_trends: list[dict] = []
        if not isinstance(trends_result, BaseException):
            improvement_trends = trends_result  # type: ignore[assignment]

        mastered_words: list[str] = []
        if not isinstance(mastered_result, BaseException):
            mastered_words = [m["word"] for m in mastered_result]  # type: ignore[union-attr]

        total_stats: dict | None = None
        if not isinstance(stats_result, BaseException):
            total_stats = stats_result  # type: ignore[assignment]

        writing_streak: dict | None = None
        if not isinstance(streak_result, BaseException):
            writing_streak = streak_result  # type: ignore[assignment]

        recent_error_count: int | None = None
        if not isinstance(top_errors_result, BaseException):
            recent_error_count = len(top_errors_result)  # type: ignore[arg-type]

        correction_aggressiveness = 50
        if not isinstance(user_settings_result, BaseException) and user_settings_result is not None:
            correction_aggressiveness = user_settings_result.correction_aggressiveness  # type: ignore[union-attr]

        recent_document_topics: list[str] = []
        if not isinstance(docs_result, BaseException):
            recent_document_topics = [
                d.title for d in docs_result[:10]  # type: ignore[union-attr]
                if d.title and d.title != "Untitled Document"  # type: ignore[union-attr]
            ]

        # Derive a rough writing level from total pattern count
        if total == 0:
            writing_level = "new_user"
        elif total < 20:
            writing_level = "developing"
        elif total < 50:
            writing_level = "intermediate"
        else:
            writing_level = "advanced"

        # Context notes — adaptive tips for the LLM
        context_notes: list[str] = []
        if breakdown.homophone > 30:
            context_notes.append("User frequently confuses homophones — pay extra attention to word context.")
        if breakdown.reversal > 30:
            context_notes.append("User has frequent letter reversals (b/d, p/q) — check carefully.")
        if breakdown.phonetic > 30:
            context_notes.append("User often writes phonetically — infer intended words from pronunciation.")
        if breakdown.grammar > 20:
            context_notes.append(
                "User frequently makes grammar errors — check subject-verb agreement, "
                "tense consistency, articles, and missing function words."
            )

        # Enriched context notes
        if correction_aggressiveness < 30:
            context_notes.append(
                "User prefers minimal corrections — only flag clear, unambiguous errors. "
                "Skip stylistic suggestions and borderline issues."
            )
        elif correction_aggressiveness > 70:
            context_notes.append(
                "User wants thorough correction — flag everything including stylistic issues, "
                "word choice, and minor grammar imperfections."
            )

        if mastered_words:
            context_notes.append(
                f"User recently mastered these words (lower priority to flag): {', '.join(mastered_words[:10])}"
            )

        for trend in improvement_trends:
            if trend.get("trend") == "needs_attention":
                context_notes.append(
                    f"Error type '{trend['error_type']}' is trending up ({trend['change_percent']:+.0f}%) — needs extra attention."
                )
            elif trend.get("trend") == "improving":
                context_notes.append(
                    f"Error type '{trend['error_type']}' is improving ({trend['change_percent']:+.0f}%) — positive reinforcement."
                )

        if writing_streak and writing_streak.get("current_streak", 0) >= 3:
            context_notes.append(
                f"User has a {writing_streak['current_streak']}-day writing streak — they're engaged and practicing."
            )

        # Extract grammar-specific patterns for prompt injection
        grammar_subtypes = {"grammar", "subject_verb", "tense", "article", "word_order", "missing_word", "run_on"}
        grammar_patterns = [
            {"misspelling": p.misspelling, "correction": p.correction, "subtype": p.error_type, "frequency": p.frequency}
            for p in top_patterns if p.error_type in grammar_subtypes
        ][:10]

        result = LLMContext(
            top_errors=[
                {"misspelling": p.misspelling, "correction": p.correction, "frequency": p.frequency}
                for p in top_patterns
            ],
            error_types=breakdown.model_dump(),
            confusion_pairs=[
                {"word_a": p.word_a, "word_b": p.word_b, "count": p.confusion_count}
                for p in pairs
            ],
            writing_level=writing_level,
            personal_dictionary=[e.word for e in dictionary],
            context_notes=context_notes,
            grammar_patterns=grammar_patterns,
            improvement_trends=improvement_trends,
            mastered_words=mastered_words,
            total_stats=total_stats,
            writing_streak=writing_streak,
            recent_error_count=recent_error_count,
            recent_document_topics=recent_document_topics,
            correction_aggressiveness=correction_aggressiveness,
        )
        await cache_set(cache_key, result.model_dump(), ttl_seconds=600)
        return result

    # ------------------------------------------------------------------
    # Error logging
    # ------------------------------------------------------------------

    async def log_error(
        self,
        user_id: str,
        db: AsyncSession,
        original: str,
        corrected: str,
        error_type: str,
        context: str | None = None,
        confidence: float = 0.0,
        source: str = "passive",
    ) -> None:
        """Log a raw error + update the aggregated pattern table."""
        # 1. Raw log
        await error_log_repo.create_error_log(
            db=db,
            user_id=user_id,
            original_text=original,
            corrected_text=corrected,
            error_type=error_type,
            context=context,
            confidence=confidence,
            source=source,
        )

        # 2. Upsert aggregated pattern
        await self.update_pattern(user_id, db, original, corrected, error_type)

        # 3. Auto-detect confusion pairs for homophone-type errors
        if error_type in _HOMOPHONE_TYPES:
            await self.add_confusion_pair(user_id, db, original, corrected)

        # 4. Invalidate caches so next read picks up new data
        await cache_delete(f"profile:{user_id}")
        await cache_delete(f"llm_context:{user_id}")

    async def update_pattern(
        self,
        user_id: str,
        db: AsyncSession,
        misspelling: str,
        correction: str,
        error_type: str,
    ) -> None:
        """Upsert a user error pattern (increment frequency)."""
        await user_error_pattern_repo.upsert_pattern(
            db, user_id, misspelling, correction, error_type
        )

    async def add_confusion_pair(
        self, user_id: str, db: AsyncSession, word_a: str, word_b: str
    ) -> None:
        """Upsert a confusion pair count."""
        await user_confusion_pair_repo.upsert_confusion_pair(db, user_id, word_a, word_b)

    # ------------------------------------------------------------------
    # Personal dictionary
    # ------------------------------------------------------------------

    async def check_personal_dictionary(
        self, user_id: str, db: AsyncSession, word: str
    ) -> bool:
        return await personal_dictionary_repo.check_word(db, user_id, word)

    async def add_to_dictionary(
        self, user_id: str, db: AsyncSession, word: str, source: str = "manual"
    ) -> PersonalDictionaryEntry:
        entry = await personal_dictionary_repo.add_word(db, user_id, word, source)
        return PersonalDictionaryEntry.model_validate(entry)

    async def get_personal_dictionary(
        self, user_id: str, db: AsyncSession
    ) -> list[PersonalDictionaryEntry]:
        entries = await personal_dictionary_repo.get_dictionary(db, user_id)
        return [PersonalDictionaryEntry.model_validate(e) for e in entries]

    async def remove_from_dictionary(
        self, user_id: str, db: AsyncSession, word: str
    ) -> bool:
        return await personal_dictionary_repo.remove_word(db, user_id, word)

    # ------------------------------------------------------------------
    # Progress & improvement
    # ------------------------------------------------------------------

    async def generate_weekly_snapshot(
        self, user_id: str, db: AsyncSession
    ) -> ProgressSnapshotResponse:
        """Aggregate the current week's data into a snapshot."""
        today = date.today()
        # ISO week start = Monday
        week_start = today - timedelta(days=today.weekday())

        error_count = await error_log_repo.get_error_count_by_period(db, user_id, days=7)
        breakdown = await self.get_error_type_breakdown(user_id, db)
        mastered = await user_error_pattern_repo.get_mastered_patterns(db, user_id)
        top = await user_error_pattern_repo.get_top_patterns(db, user_id, limit=5)

        # Accuracy: rough heuristic — fewer recent errors = higher accuracy
        accuracy = max(0.0, min(100.0, 100.0 - error_count * 2.0))

        snapshot = await progress_snapshot_repo.upsert_snapshot(
            db=db,
            user_id=user_id,
            week_start=week_start,
            total_corrections=error_count,
            accuracy_score=accuracy,
            error_type_breakdown=breakdown.model_dump(),
            top_errors=[
                {"misspelling": p.misspelling, "correction": p.correction, "frequency": p.frequency}
                for p in top
            ],
            patterns_mastered=len(mastered),
        )
        return ProgressSnapshotResponse.model_validate(snapshot)

    async def get_progress(
        self, user_id: str, db: AsyncSession, weeks: int = 12
    ) -> list[ProgressSnapshotResponse]:
        snapshots = await progress_snapshot_repo.get_snapshots(db, user_id, weeks)
        return [ProgressSnapshotResponse.model_validate(s) for s in snapshots]

    async def detect_improvement(
        self, user_id: str, db: AsyncSession
    ) -> dict:
        """Compare last 14 days vs prior 14 days to detect improvement."""
        recent_count = await error_log_repo.get_error_count_by_period(db, user_id, days=14)
        older_count = await error_log_repo.get_error_count_by_period(db, user_id, days=28)
        # older_count includes recent_count, so isolate prior period
        prior_count = older_count - recent_count

        if prior_count == 0:
            trend = "new_user"
        elif recent_count < prior_count:
            trend = "improving"
        elif recent_count == prior_count:
            trend = "stable"
        else:
            trend = "needs_practice"

        # Bulk update improving patterns
        patterns = await user_error_pattern_repo.get_top_patterns(db, user_id, limit=100)
        cutoff = datetime.utcnow() - timedelta(days=14)
        set_improving_ids = []
        clear_improving_ids = []
        for p in patterns:
            is_improving = p.last_seen < cutoff
            if is_improving and not p.improving:
                set_improving_ids.append(p.id)
            elif not is_improving and p.improving:
                clear_improving_ids.append(p.id)
        improving_count = len(set_improving_ids)

        if set_improving_ids:
            await user_error_pattern_repo.bulk_mark_improving(db, set_improving_ids, True)
        if clear_improving_ids:
            await user_error_pattern_repo.bulk_mark_improving(db, clear_improving_ids, False)

        return {
            "trend": trend,
            "recent_errors": recent_count,
            "prior_errors": prior_count,
            "patterns_improving": improving_count,
        }

    async def get_mastered_words(
        self, user_id: str, db: AsyncSession
    ) -> list[UserErrorPatternResponse]:
        patterns = await user_error_pattern_repo.get_mastered_patterns(db, user_id)
        return [UserErrorPatternResponse.model_validate(p) for p in patterns]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
error_profile_service = ErrorProfileService()


# ---------------------------------------------------------------------------
# Backward-compatible wrappers for existing callers
# ---------------------------------------------------------------------------

async def get_user_profile(user_id: str, db: AsyncSession) -> FullErrorProfile:
    """Backward-compatible wrapper used by llm_orchestrator and routes."""
    return await error_profile_service.get_full_profile(user_id, db)


async def update_user_profile(
    user_id: str,
    update: ErrorProfileUpdate,
    db: AsyncSession,
) -> FullErrorProfile:
    """Backward-compatible wrapper."""
    # Process incoming updates through the service
    if update.patterns_to_update:
        for p in update.patterns_to_update:
            await error_profile_service.update_pattern(
                user_id, db,
                p.get("misspelling", ""),
                p.get("correction", ""),
                p.get("error_type", "other"),
            )
    if update.confusion_pairs_to_add:
        for cp in update.confusion_pairs_to_add:
            await error_profile_service.add_confusion_pair(
                user_id, db, cp.get("word1", ""), cp.get("word2", "")
            )
    return await error_profile_service.get_full_profile(user_id, db)


async def record_correction(
    user_id: str,
    original: str,
    corrected: str,
    correction_type: str,
    db: AsyncSession,
) -> None:
    """Backward-compatible wrapper."""
    await error_profile_service.log_error(
        user_id, db, original, corrected, correction_type
    )


async def analyze_patterns(user_id: str, db: AsyncSession) -> list[dict]:
    """Backward-compatible wrapper."""
    result = await error_profile_service.detect_improvement(user_id, db)
    return [result]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_error_type(error_type: str) -> str:
    """Map raw error_type strings to ErrorTypeBreakdown field names."""
    mapping = {
        "reversal": "reversal",
        "letter_reversal": "reversal",
        "b/d": "reversal",
        "phonetic": "phonetic",
        "phonetic_substitution": "phonetic",
        "homophone": "homophone",
        "confusion": "homophone",
        "real-word": "homophone",
        "omission": "omission",
        "transposition": "transposition",
        "spelling": "other",
        "grammar": "grammar",
        "subject_verb": "grammar",
        "tense": "grammar",
        "article": "grammar",
        "word_order": "grammar",
        "missing_word": "grammar",
        "run_on": "grammar",
        "self-correction": "other",
    }
    return mapping.get(error_type.lower(), "other")
