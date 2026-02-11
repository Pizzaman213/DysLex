"""Extract a correction dictionary from training data word pairs.

Builds a JSON mapping of misspelling -> correction from all parsed datasets.
This ships with the frontend as the base correction lookup for the ONNX model.
The user's personal error profile merges on top at runtime.

Output: ml/models/quick_correction_base_v1/correction_dict.json
"""

import json
import logging
from collections import Counter
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "ml" / "datasets" / "raw"
ONNX_MODEL_DIR = PROJECT_ROOT / "ml" / "models" / "quick_correction_base_v1"


def _load_valid_words() -> set[str]:
    """Load a set of valid English words to filter out false corrections.

    Loads from the comprehensive merged dictionary (379K words) first,
    then falls back to the system dictionary and built-in word list.
    """
    valid: set[str] = set()

    # Try comprehensive dictionary first (merged Webster's + system + frequency)
    full_dict = ONNX_MODEL_DIR / "frequency_dictionary_en_full.txt"
    if full_dict.exists():
        for line in full_dict.read_text().splitlines():
            parts = line.strip().split()
            if parts:
                word = parts[0].lower()
                if len(word) >= 2:
                    valid.add(word)
        logger.info(f"  Loaded {len(valid)} valid words from full dictionary")
    else:
        # Fall back to system dictionary
        system_dict = Path("/usr/share/dict/words")
        if system_dict.exists():
            for line in system_dict.read_text().splitlines():
                word = line.strip().lower()
                if len(word) >= 2:
                    valid.add(word)
            logger.info(f"  Loaded {len(valid)} valid words from system dictionary")
        else:
            logger.warning("  No dictionary found, using built-in word list only")

    # Always add the most critical common English words
    # (ensures coverage even if system dict is missing or incomplete)
    _COMMON = {
        "a", "i", "am", "an", "as", "at", "be", "by", "do", "go", "he",
        "if", "in", "is", "it", "me", "my", "no", "of", "on", "or", "so",
        "to", "up", "us", "we", "ad", "ah", "ha", "hi", "oh", "ok",
        "the", "and", "for", "are", "but", "not", "you", "all", "can",
        "had", "her", "was", "one", "our", "out", "day", "get", "has",
        "him", "his", "how", "its", "let", "may", "new", "now", "old",
        "see", "way", "who", "did", "got", "say", "she", "too", "use",
        "man", "big", "set", "try", "ask", "own", "put", "run", "few",
        "end", "top", "red", "far", "lot", "ago", "add", "act", "age",
        "air", "arm", "art", "bad", "bag", "bar", "bed", "bit", "box",
        "boy", "bus", "buy", "car", "cup", "cut", "dog", "ear", "eat",
        "egg", "eye", "fit", "fly", "fun", "god", "gun", "hat", "hit",
        "hot", "ice", "job", "key", "kid", "lay", "led", "leg", "lie",
        "lip", "low", "map", "mix", "nor", "oil", "pay", "per", "pig",
        "pin", "pop", "ran", "raw", "row", "sat", "sea", "sir", "sit",
        "six", "son", "sun", "tea", "ten", "tie", "tip", "war", "win",
        "won", "yes", "yet",
        "that", "with", "have", "this", "will", "your", "from", "they",
        "been", "said", "each", "make", "like", "long", "look", "many",
        "some", "them", "than", "come", "made", "find", "here", "know",
        "take", "want", "give", "most", "only", "tell", "very", "when",
        "what", "were", "much", "then", "also", "back", "into", "year",
        "just", "over", "such", "good", "well", "time", "down", "even",
        "hand", "high", "keep", "last", "must", "name", "part", "work",
        "went", "call", "need", "home", "life", "left", "head", "read",
        "door", "sure", "open", "done", "turn", "move", "live", "real",
        "face", "hold", "best", "stop", "help", "show", "hear", "seem",
        "came", "seen", "used", "line", "side", "late", "hard", "form",
        "full", "half", "city", "once", "plan", "area", "care", "free",
        "kind", "land", "lost", "love", "play", "word", "ever", "next",
        "near", "feel", "fact", "else", "talk", "girl", "food", "four",
        "body", "mind", "city", "wide", "tree", "rest", "idea", "case",
        "store", "about", "other", "which", "their", "there", "would",
        "could", "after", "where", "think", "going", "being", "those",
        "still", "every", "never", "might", "under", "while", "first",
        "found", "great", "thing", "right", "world", "house", "place",
        "small", "again", "point", "start", "young", "water", "until",
        "three", "state", "woman", "night", "since", "shall", "along",
        "close", "stood", "group", "given", "often", "taken", "bring",
        "began", "whole", "above", "below", "power", "money", "early",
        "light", "human", "heart", "story", "child",
        "should", "people", "before", "little", "follow", "friend",
        "around", "family", "school", "always", "really", "answer",
        "mother", "father", "number", "become", "better", "enough",
        "change", "simple", "system", "social", "return", "public",
        "government", "something", "important", "different", "children",
        "between", "because", "through", "another", "without", "against",
        "receive", "believe", "whether", "nothing", "already", "thought",
        "company", "country", "problem", "program", "several", "student",
        "general", "however", "morning", "example",
    }
    valid.update(_COMMON)
    return valid


def _damerau_levenshtein_distance(a: str, b: str) -> int:
    """Compute optimal string alignment distance (Damerau-Levenshtein).

    Like Levenshtein but also counts adjacent transpositions as a single edit.
    This is critical for dyslexic writing where letter swaps (e.g. "teh" -> "the")
    are extremely common.
    """
    len_a, len_b = len(a), len(b)
    matrix = [[0] * (len_a + 1) for _ in range(len_b + 1)]
    for i in range(len_b + 1):
        matrix[i][0] = i
    for j in range(len_a + 1):
        matrix[0][j] = j
    for i in range(1, len_b + 1):
        for j in range(1, len_a + 1):
            cost = 0 if b[i - 1] == a[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j - 1] + cost,  # substitution
                matrix[i][j - 1] + 1,          # insertion
                matrix[i - 1][j] + 1,          # deletion
            )
            # Transposition of adjacent characters
            if i > 1 and j > 1 and b[i - 1] == a[j - 2] and b[i - 2] == a[j - 1]:
                matrix[i][j] = min(matrix[i][j], matrix[i - 2][j - 2] + cost)
    return matrix[len_b][len_a]


def _validate_entry(misspelling: str, correction: str) -> bool:
    """Validate that a misspelling-correction pair is plausible.

    Filters out spurious entries where the misspelling and correction are too
    dissimilar to represent a real typo or dyslexic error.

    Three checks:
    - Edit distance ratio: Levenshtein distance <= 50% of longer word length
    - Character overlap: At least 50% of characters shared (by frequency)
    - Length ratio: Correction between 0.5x and 2.0x misspelling length
    """
    max_len = max(len(misspelling), len(correction))
    min_len = min(len(misspelling), len(correction))

    # Length ratio check
    if min_len == 0:
        return False
    if min_len / max_len < 0.5:
        return False

    # Edit distance ratio check (uses Damerau-Levenshtein to count transpositions as 1 edit)
    distance = _damerau_levenshtein_distance(misspelling, correction)
    if distance / max_len > 0.5:
        return False

    # Character overlap check (by frequency via Counter)
    counter_m = Counter(misspelling)
    counter_c = Counter(correction)
    overlap = sum((counter_m & counter_c).values())
    if overlap / max_len < 0.5:
        return False

    return True


def extract_dictionary(
    raw_dir: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, str]:
    """Extract misspelling -> correction mapping from all dataset sources.

    Only includes entries where the misspelling is NOT a valid English word.
    This prevents the dictionary from "correcting" real words like
    "went" -> "want" or "he" -> "her".

    Args:
        raw_dir: Directory containing raw dataset files
        output_path: Where to save the JSON dictionary

    Returns:
        Dict mapping misspelling to correction
    """
    if raw_dir is None:
        raw_dir = RAW_DIR
    if output_path is None:
        output_path = ONNX_MODEL_DIR / "correction_dict.json"

    # Load valid English words to filter false corrections
    valid_words = _load_valid_words()
    logger.info(f"  Valid word filter: {len(valid_words)} words loaded")

    # Import parsers
    from ml.datasets.process_datasets import (  # type: ignore[import-not-found]
        parse_aspell,
        parse_birkbeck,
        parse_github_typo,
        parse_wikipedia,
    )

    correction_dict: dict[str, str] = {}
    rejected_entries: list[dict[str, str]] = []
    skipped_valid = 0
    skipped_validation = 0

    # Parse all sources
    parsers = {
        "birkbeck": (parse_birkbeck, raw_dir / "birkbeck_missp.dat"),
        "aspell": (parse_aspell, raw_dir / "aspell.dat"),
        "wikipedia": (parse_wikipedia, raw_dir / "wikipedia_misspellings.txt"),
        "github_typo": (parse_github_typo, raw_dir / "github_typo_corpus.jsonl.gz"),
    }

    for source, (parser_fn, filepath) in parsers.items():
        pairs = parser_fn(filepath)
        added = 0
        source_skipped = 0
        source_rejected = 0
        for misspelling, correct in pairs:
            misspelling = misspelling.lower().strip()
            correct = correct.lower().strip()

            # Skip if same, empty, or too short
            if not misspelling or not correct or misspelling == correct:
                continue
            if len(misspelling) < 2 or len(correct) < 2:
                continue

            # CRITICAL: Skip if the "misspelling" is a valid English word.
            # The raw datasets contain pairs where real words are listed as
            # misspellings of other words (e.g. "he" -> "her", "went" -> "want").
            # These would cause the corrector to mangle correct text.
            if misspelling in valid_words:
                source_skipped += 1
                skipped_valid += 1
                continue

            # Validate that the pair is plausible (edit distance, char overlap, length ratio)
            if not _validate_entry(misspelling, correct):
                rejected_entries.append({"misspelling": misspelling, "correction": correct, "source": source})
                source_rejected += 1
                skipped_validation += 1
                continue

            # First occurrence wins (most reliable sources parsed first)
            if misspelling not in correction_dict:
                correction_dict[misspelling] = correct
                added += 1

        logger.info(f"  {source}: {added} new entries, {source_skipped} skipped (valid words), {source_rejected} rejected (validation) (from {len(pairs)} pairs)")

    logger.info(f"  Total skipped (valid English words): {skipped_valid}")
    logger.info(f"  Total rejected (validation filters): {skipped_validation}")

    # Save rejected entries for manual review
    rejected_path = ONNX_MODEL_DIR / "rejected_entries_review.json"
    with open(rejected_path, "w") as f:
        json.dump(rejected_entries, f, indent=2)
    logger.info(f"  Rejected entries saved to {rejected_path} ({len(rejected_entries)} entries)")

    # Add common dyslexic patterns that may not be in datasets
    common_extras = {
        "teh": "the", "taht": "that", "siad": "said", "thier": "their",
        "recieve": "receive", "freind": "friend", "becuase": "because",
        "wich": "which", "thsi": "this", "adn": "and", "hte": "the",
        "waht": "what", "ahve": "have", "wiht": "with", "form": "from",
        "jsut": "just", "konw": "know", "woudl": "would", "dont": "don't",
        "didnt": "didn't", "doesnt": "doesn't", "cant": "can't",
        "wont": "won't", "isnt": "isn't", "wasnt": "wasn't",
        "havent": "haven't", "hasnt": "hasn't", "wouldnt": "wouldn't",
        "couldnt": "couldn't", "shouldnt": "shouldn't",
        "yuo": "you", "hwo": "how", "whn": "when", "thn": "then",
        "beacuse": "because", "beleive": "believe", "definately": "definitely",
        "seperate": "separate", "occured": "occurred", "untill": "until",
        "tommorrow": "tomorrow", "goverment": "government",
        "enviroment": "environment", "necesary": "necessary",
        "accomodate": "accommodate", "occurence": "occurrence",
    }
    for misspelling, correct in common_extras.items():
        if misspelling not in correction_dict:
            correction_dict[misspelling] = correct

    logger.info(f"\nTotal dictionary entries: {len(correction_dict)}")

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(correction_dict, f, sort_keys=True)

    size_kb = output_path.stat().st_size / 1024
    logger.info(f"Saved to {output_path} ({size_kb:.1f} KB)")

    return correction_dict


def main():
    """Extract correction dictionary."""
    import argparse

    parser = argparse.ArgumentParser(description="Extract correction dictionary")
    parser.add_argument("--raw-dir", type=str, default=None, help="Raw dataset directory")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir) if args.raw_dir else None
    output_path = Path(args.output) if args.output else None

    dictionary = extract_dictionary(raw_dir=raw_dir, output_path=output_path)
    logger.info(f"Extracted {len(dictionary)} correction entries")


if __name__ == "__main__":
    main()
