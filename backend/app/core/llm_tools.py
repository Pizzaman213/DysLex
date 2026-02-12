"""LLM tool definitions and executor for tool-calling support.

Provides tools the LLM can invoke mid-inference to look up words,
check confusion pairs, and query user history.
"""

import json
import logging
import re
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static resources (loaded once at startup)
# ---------------------------------------------------------------------------

_frequency_dict: set[str] | None = None
_confusion_pairs: list[dict] | None = None

_FREQ_DICT_PATH = Path(__file__).resolve().parents[3] / "ml" / "models" / "quick_correction_base_v1" / "frequency_dictionary_en_full.txt"
_CONFUSION_PAIRS_PATH = Path(__file__).resolve().parents[3] / "ml" / "confusion_pairs" / "en.json"


def _load_frequency_dict() -> set[str]:
    """Load frequency dictionary into a set for O(1) word lookup."""
    global _frequency_dict
    if _frequency_dict is not None:
        return _frequency_dict

    words: set[str] = set()
    try:
        with open(_FREQ_DICT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if parts:
                    words.add(parts[0].lower())
        logger.info("Loaded frequency dictionary: %d words", len(words))
    except FileNotFoundError:
        logger.warning("Frequency dictionary not found at %s", _FREQ_DICT_PATH)
    except Exception:
        logger.error("Failed to load frequency dictionary", exc_info=True)

    _frequency_dict = words
    return _frequency_dict


def _load_confusion_pairs() -> list[dict]:
    """Load confusion pairs from JSON."""
    global _confusion_pairs
    if _confusion_pairs is not None:
        return _confusion_pairs

    pairs: list[dict] = []
    try:
        with open(_CONFUSION_PAIRS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            pairs = data.get("pairs", [])
        logger.info("Loaded confusion pairs: %d entries", len(pairs))
    except FileNotFoundError:
        logger.warning("Confusion pairs not found at %s", _CONFUSION_PAIRS_PATH)
    except Exception:
        logger.error("Failed to load confusion pairs", exc_info=True)

    _confusion_pairs = pairs
    return _confusion_pairs


def preload_static_resources() -> None:
    """Pre-load static resources at startup to avoid first-request latency."""
    _load_frequency_dict()
    _load_confusion_pairs()


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def lookup_word(word: str) -> dict:
    """Check if a word is valid English by looking it up in the frequency dictionary."""
    freq_dict = _load_frequency_dict()
    found = word.lower().strip() in freq_dict
    return {"word": word, "is_valid": found}


def check_confusion_pair(word_a: str, word_b: str) -> dict:
    """Check if two words form a known confusion pair."""
    pairs = _load_confusion_pairs()
    a_lower = word_a.lower().strip()
    b_lower = word_b.lower().strip()

    for entry in pairs:
        words = [w.lower() for w in entry.get("words", [])]
        if a_lower in words and b_lower in words:
            return {
                "word_a": word_a,
                "word_b": word_b,
                "is_confusion_pair": True,
                "category": entry.get("category", "unknown"),
                "frequency": entry.get("frequency", "unknown"),
            }

    return {"word_a": word_a, "word_b": word_b, "is_confusion_pair": False}


async def get_user_error_history(
    misspelling: str, user_id: str, db: AsyncSession
) -> dict:
    """Check if the user has a history with a specific misspelling."""
    from app.db.repositories import user_error_pattern_repo

    try:
        patterns = await user_error_pattern_repo.get_top_patterns(db, user_id, limit=100)
        for p in patterns:
            if p.misspelling.lower() == misspelling.lower().strip():
                return {
                    "misspelling": misspelling,
                    "found": True,
                    "correction": p.correction,
                    "frequency": p.frequency,
                    "improving": p.improving,
                }
        return {"misspelling": misspelling, "found": False}
    except Exception:
        logger.warning("Failed to check user error history for %s", misspelling, exc_info=True)
        return {"misspelling": misspelling, "found": False, "error": "lookup failed"}


async def check_personal_dictionary(
    word: str, user_id: str, db: AsyncSession
) -> dict:
    """Check if a word is in the user's personal dictionary."""
    from app.db.repositories import personal_dictionary_repo

    try:
        found = await personal_dictionary_repo.check_word(db, user_id, word)
        return {"word": word, "in_dictionary": found}
    except Exception:
        logger.warning("Failed to check personal dictionary for %s", word, exc_info=True)
        return {"word": word, "in_dictionary": False, "error": "lookup failed"}


# ---------------------------------------------------------------------------
# Pre-resolution of static lookups (Phase 2.2 optimization)
# ---------------------------------------------------------------------------


def pre_resolve_static_lookups(text: str) -> dict:
    """Run dictionary and confusion-pair lookups locally for all words in text.

    Returns a dict with:
      - unknown_words: list of words not found in the frequency dictionary
      - relevant_confusion_pairs: list of confusion pair dicts where at least
        one word appears in the text

    These results are injected directly into the system prompt so the LLM
    does not need to call lookup_word or check_confusion_pair as tools.
    """
    words = set(re.findall(r"[a-zA-Z']+", text.lower()))

    # Dictionary check — find words NOT in the dictionary
    freq_dict = _load_frequency_dict()
    # Skip very short words (1-2 chars) to reduce noise
    unknown_words = sorted(w for w in words if len(w) > 2 and w not in freq_dict)

    # Confusion pair check — find pairs where any word appears in the text
    pairs = _load_confusion_pairs()
    relevant_pairs: list[dict] = []
    for entry in pairs:
        pair_words = [w.lower() for w in entry.get("words", [])]
        if any(pw in words for pw in pair_words):
            relevant_pairs.append({
                "word_a": entry.get("words", ["?", "?"])[0],
                "word_b": entry.get("words", ["?", "?"])[1] if len(entry.get("words", [])) > 1 else "?",
                "category": entry.get("category", "unknown"),
            })

    return {
        "unknown_words": unknown_words,
        "relevant_confusion_pairs": relevant_pairs,
    }


# ---------------------------------------------------------------------------
# Tool definitions (OpenAI-compatible format)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict] = [
    # NOTE: lookup_word and check_confusion_pair have been removed from tool
    # definitions — they are now pre-resolved locally before the LLM call
    # and injected directly into the system prompt (Phase 2.2 optimization).
    {
        "type": "function",
        "function": {
            "name": "get_user_error_history",
            "description": "Check if this user has a history of making a specific error. Use when you want to know if a misspelling is a recurring pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "misspelling": {
                        "type": "string",
                        "description": "The misspelled word to look up in the user's history",
                    },
                },
                "required": ["misspelling"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_personal_dictionary",
            "description": "Check if a word is in the user's personal dictionary (words that should never be flagged). Use when unsure if an unusual word is intentional.",
            "parameters": {
                "type": "object",
                "properties": {
                    "word": {
                        "type": "string",
                        "description": "The word to check",
                    },
                },
                "required": ["word"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool executor (dispatcher)
# ---------------------------------------------------------------------------


async def execute_tool(
    tool_name: str,
    arguments: dict,
    user_id: str | None = None,
    db: AsyncSession | None = None,
) -> str:
    """Execute a tool by name and return the result as a JSON string."""
    try:
        if tool_name == "lookup_word":
            result = lookup_word(arguments["word"])
        elif tool_name == "check_confusion_pair":
            result = check_confusion_pair(arguments["word_a"], arguments["word_b"])
        elif tool_name == "get_user_error_history":
            if user_id is None or db is None:
                result = {"error": "user_id and db required for this tool"}
            else:
                result = await get_user_error_history(arguments["misspelling"], user_id, db)
        elif tool_name == "check_personal_dictionary":
            if user_id is None or db is None:
                result = {"error": "user_id and db required for this tool"}
            else:
                result = await check_personal_dictionary(arguments["word"], user_id, db)
        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        return json.dumps(result)
    except Exception as e:
        logger.error("Tool execution failed: %s(%s) — %s", tool_name, arguments, e)
        return json.dumps({"error": f"Tool execution failed: {e}"})
