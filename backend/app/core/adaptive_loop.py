"""Passive learning loop - learns from user behavior without explicit feedback."""

import difflib
import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class TextSnapshot:
    """A snapshot of user's text at a point in time."""

    text: str
    timestamp: datetime
    word_count: int


@dataclass
class UserCorrection:
    """A correction detected from user behavior."""

    original: str
    corrected: str
    position: int
    correction_type: str
    confidence: float


async def process_snapshot_pair(
    before: TextSnapshot,
    after: TextSnapshot,
    user_id: str,
    db: AsyncSession,
) -> list[UserCorrection]:
    """Process a pair of snapshots to detect user corrections.

    Uses Longest Common Subsequence (LCS) algorithm to detect word-level changes.
    Identifies substitutions, insertions, and deletions, then filters for likely
    self-corrections based on edit distance and word validity.
    """
    corrections = []

    # Tokenize text into words
    before_words = _tokenize(before.text)
    after_words = _tokenize(after.text)

    # Detect changes using difflib SequenceMatcher (O(n) avg vs O(n*m) LCS)
    changes = _compute_word_changes(before_words, after_words)

    # Filter for self-corrections (substitutions that look like error fixes)
    for change in changes:
        if change["type"] == "replace":
            original = change["old_value"]
            corrected = change["new_value"]

            # Calculate similarity to determine if it's likely a correction
            similarity = _calculate_similarity(original, corrected)

            # Likely a self-correction if:
            # - Words are similar (0.3 < similarity < 0.95)
            # - Not too different (suggests intentional rewrite vs typo fix)
            if 0.3 < similarity < 0.95:
                confidence = similarity
                correction_type = _classify_error_type(original, corrected)

                corrections.append(
                    UserCorrection(
                        original=original,
                        corrected=corrected,
                        position=change["position"],
                        correction_type=correction_type,
                        confidence=confidence,
                    )
                )

    # Update error profile with detected corrections
    if corrections:
        await update_error_profile_from_corrections(user_id, corrections, db)

    return corrections


def _tokenize(text: str) -> list[str]:
    """Split text into words, filtering empty strings."""
    return [w for w in text.split() if w]


def _compute_word_changes(old_words: list[str], new_words: list[str]) -> list[dict]:
    """Detect word-level changes using difflib.SequenceMatcher.

    Returns list of change dicts with type: add|remove|replace.
    Much faster than the custom O(n*m) LCS approach for typical inputs.
    """
    changes: list[dict] = []
    sm = difflib.SequenceMatcher(None, old_words, new_words, autojunk=False)

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        elif tag == "replace":
            # Pair up old/new words one-to-one; extras become add/remove
            old_span = old_words[i1:i2]
            new_span = new_words[j1:j2]
            for k in range(max(len(old_span), len(new_span))):
                if k < len(old_span) and k < len(new_span):
                    changes.append({
                        "type": "replace",
                        "old_value": old_span[k],
                        "new_value": new_span[k],
                        "position": i1 + k,
                    })
                elif k < len(old_span):
                    changes.append({
                        "type": "remove",
                        "old_value": old_span[k],
                        "position": i1 + k,
                    })
                else:
                    changes.append({
                        "type": "add",
                        "new_value": new_span[k],
                        "position": j1 + k,
                    })
        elif tag == "delete":
            for k in range(i1, i2):
                changes.append({
                    "type": "remove",
                    "old_value": old_words[k],
                    "position": k,
                })
        elif tag == "insert":
            for k in range(j1, j2):
                changes.append({
                    "type": "add",
                    "new_value": new_words[k],
                    "position": k,
                })

    return changes


def _calculate_similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings using Levenshtein distance.

    Returns value between 0.0 (completely different) and 1.0 (identical).
    """
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 1.0

    distance = _levenshtein_distance(a.lower(), b.lower())
    return 1.0 - (distance / max_len)


def _levenshtein_distance(a: str, b: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    # Create matrix
    matrix = [[0] * (len(a) + 1) for _ in range(len(b) + 1)]

    # Initialize first row and column
    for i in range(len(b) + 1):
        matrix[i][0] = i
    for j in range(len(a) + 1):
        matrix[0][j] = j

    # Fill matrix
    for i in range(1, len(b) + 1):
        for j in range(1, len(a) + 1):
            if b[i - 1] == a[j - 1]:
                matrix[i][j] = matrix[i - 1][j - 1]
            else:
                matrix[i][j] = min(
                    matrix[i - 1][j - 1] + 1,  # substitution
                    matrix[i][j - 1] + 1,      # insertion
                    matrix[i - 1][j] + 1,      # deletion
                )

    return matrix[len(b)][len(a)]


def _classify_error_type(original: str, corrected: str) -> str:
    """Classify the type of error based on original and corrected words.

    Returns error type string for use in error profile.
    """
    orig_lower = original.lower()
    corr_lower = corrected.lower()

    # Check for common dyslexic error patterns

    # Reversed letters (e.g., "teh" -> "the")
    if _has_letter_reversal(orig_lower, corr_lower):
        return "letter_reversal"

    # Phonetic substitution (sounds similar)
    if _is_phonetically_similar(orig_lower, corr_lower):
        return "phonetic"

    # Homophone confusion (different words, same sound)
    if _are_homophones(orig_lower, corr_lower):
        return "homophone"

    # Letter omission/addition
    if _is_omission_or_addition(orig_lower, corr_lower):
        return "omission"

    # Default to spelling error
    return "spelling"


def _has_letter_reversal(a: str, b: str) -> bool:
    """Check if strings differ by a simple letter reversal."""
    if abs(len(a) - len(b)) > 0:
        return False

    # Check each adjacent pair
    for i in range(len(a) - 1):
        # Try swapping position i and i+1
        chars = list(a)
        chars[i], chars[i + 1] = chars[i + 1], chars[i]
        if "".join(chars) == b:
            return True

    return False


def _is_phonetically_similar(a: str, b: str) -> bool:
    """Rough phonetic similarity check.

    True if words share most consonants in similar positions.
    """
    def get_consonants(word: str) -> str:
        return "".join(c for c in word if c not in "aeiou")

    cons_a = get_consonants(a)
    cons_b = get_consonants(b)

    if not cons_a or not cons_b:
        return False

    # Check if consonant patterns are similar
    similarity = _calculate_similarity(cons_a, cons_b)
    return similarity > 0.6


def _are_homophones(a: str, b: str) -> bool:
    """Check if words are common homophones.

    Simple check - in production would use comprehensive homophone dictionary.
    """
    common_pairs = {
        ("there", "their"), ("their", "they're"), ("there", "they're"),
        ("to", "too"), ("to", "two"), ("too", "two"),
        ("your", "you're"),
        ("its", "it's"),
        ("affect", "effect"),
        ("accept", "except"),
    }

    pair = tuple(sorted([a, b]))
    return pair in common_pairs or tuple(reversed(pair)) in common_pairs


def _is_omission_or_addition(a: str, b: str) -> bool:
    """Check if one word is the other with a letter added or removed."""
    if abs(len(a) - len(b)) != 1:
        return False

    shorter, longer = (a, b) if len(a) < len(b) else (b, a)

    # Try removing each character from longer word
    for i in range(len(longer)):
        if longer[:i] + longer[i + 1:] == shorter:
            return True

    return False


async def update_error_profile_from_corrections(
    user_id: str,
    corrections: list[UserCorrection],
    db: AsyncSession,
) -> None:
    """Update user's error profile based on detected corrections."""
    from app.core.error_profile import error_profile_service

    for correction in corrections:
        try:
            await error_profile_service.log_error(
                user_id=user_id,
                db=db,
                original=correction.original,
                corrected=correction.corrected,
                error_type=correction.correction_type,
                confidence=correction.confidence,
                source="self_corrected",
            )
        except Exception:
            logger.warning(
                "Failed to log self-correction for user %s", user_id, exc_info=True
            )


async def compute_learning_signal(
    user_id: str,
    window_hours: int = 24,
    db: AsyncSession = None,
) -> dict:
    """Compute learning signals from recent user activity."""
    if db is not None:
        from app.core.error_profile import error_profile_service

        try:
            result = await error_profile_service.detect_improvement(user_id, db)
            return {
                "patterns_reinforced": [],
                "patterns_weakened": [],
                "new_confusion_pairs": [],
                "overall_trend": result.get("trend", "improving"),
            }
        except Exception:
            logger.warning("Failed to compute learning signal", exc_info=True)

    return {
        "patterns_reinforced": [],
        "patterns_weakened": [],
        "new_confusion_pairs": [],
        "overall_trend": "improving",
    }
