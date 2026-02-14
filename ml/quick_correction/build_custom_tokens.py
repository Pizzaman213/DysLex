"""Build custom token list from dyslexic misspelling patterns and training data.

Analyzes pattern files AND actual training data to find misspellings that
fragment under flan-t5-base's SentencePiece tokenizer. These words are added
as single tokens during training to improve accuracy and speed.

Two sources:
1. Pattern files (transpositions, vowel_confusion, etc.) — curated misspellings
2. Training data (birkbeck, wikipedia, etc.) — high-frequency real misspellings

Usage:
    python ml/quick_correction/build_custom_tokens.py --verbose
    python ml/quick_correction/build_custom_tokens.py --min-freq 100 --verbose
"""

import argparse
import json
import logging
from collections import Counter
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PATTERNS_DIR = Path(__file__).parent.parent / "synthetic_data" / "patterns"
PROCESSED_DIR = Path(__file__).parent.parent / "datasets" / "processed"
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "custom_dyslexic_tokens.json"
BASE_MODEL = "google/flan-t5-base"

# Pattern files containing misspellings (not real words)
MISSPELLING_PATTERN_FILES = [
    "transpositions.json",
    "vowel_confusion.json",
    "visual_similarity.json",
    "omissions.json",
]

# Training data files to mine for high-frequency misspellings
TRAINING_DATA_FILES = [
    "birkbeck_seq2seq.jsonl",
    "wikipedia_seq2seq.jsonl",
    "aspell_seq2seq.jsonl",
    "github_typo_seq2seq.jsonl",
]

# Default minimum frequency for training data misspellings
DEFAULT_MIN_FREQ = 50


def load_misspellings_from_patterns(patterns_dir: Path, verbose: bool = False) -> dict[str, str]:
    """Extract misspelled words from pattern files.

    Args:
        patterns_dir: Directory containing pattern JSON files
        verbose: Log details about each file

    Returns:
        Dict mapping misspelling -> correct word
    """
    misspellings: dict[str, str] = {}

    for filename in MISSPELLING_PATTERN_FILES:
        filepath = patterns_dir / filename
        if not filepath.exists():
            logger.warning(f"Pattern file not found: {filepath}")
            continue

        with open(filepath) as f:
            data = json.load(f)

        # Extract from common_examples (transpositions, vowel_confusion, visual_similarity)
        examples_key = "common_examples" if "common_examples" in data else "examples"
        examples = data.get(examples_key, [])

        count = 0
        for ex in examples:
            error = ex.get("error", "")
            correct = ex.get("correct", "")
            if error and correct and error.lower() != correct.lower():
                misspellings[error.lower()] = correct.lower()
                count += 1

        if verbose:
            logger.info(f"  {filename}: {count} misspellings extracted")

    return misspellings


def load_misspellings_from_training_data(
    processed_dir: Path,
    min_freq: int = DEFAULT_MIN_FREQ,
    verbose: bool = False,
) -> dict[str, int]:
    """Extract high-frequency misspellings from training data JSONL files.

    Compares input_text vs target_text word-by-word to find misspelled words,
    then returns those occurring at least min_freq times.

    Args:
        processed_dir: Directory containing processed *_seq2seq.jsonl files
        min_freq: Minimum frequency to include a misspelling
        verbose: Log details

    Returns:
        Dict mapping misspelling -> frequency count
    """
    all_misspellings: Counter = Counter()

    for filename in TRAINING_DATA_FILES:
        filepath = processed_dir / filename
        if not filepath.exists():
            if verbose:
                logger.info(f"  {filename}: not found, skipping")
            continue

        file_count = 0
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                sample = json.loads(line)
                inp = sample.get("input_text", "").replace("correct: ", "")
                tgt = sample.get("target_text", "")
                inp_words = inp.lower().split()
                tgt_words = tgt.lower().split()
                for iw, tw in zip(inp_words, tgt_words):
                    if iw != tw and len(iw) > 2:
                        all_misspellings[iw] += 1
                        file_count += 1

        if verbose:
            logger.info(f"  {filename}: {file_count} misspelling occurrences")

    # Filter by minimum frequency
    frequent = {word: count for word, count in all_misspellings.items() if count >= min_freq}

    logger.info(
        f"Training data: {len(all_misspellings)} unique misspellings, "
        f"{len(frequent)} with freq >= {min_freq}"
    )

    return frequent


def filter_fragmented_tokens(
    words: list[str],
    model_name: str = BASE_MODEL,
    verbose: bool = False,
) -> tuple[list[str], int]:
    """Filter to only words that fragment into 2+ subword tokens.

    Args:
        words: List of words to check
        model_name: HuggingFace model name for tokenizer
        verbose: Log tokenization details

    Returns:
        Tuple of (fragmented words list, base vocab size)
    """
    from transformers import AutoTokenizer

    logger.info(f"Loading tokenizer from {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    base_vocab_size = len(tokenizer)
    logger.info(f"Base vocabulary size: {base_vocab_size}")

    fragmented: list[str] = []
    already_single = 0

    for word in sorted(words):
        tokens = tokenizer.tokenize(word)
        if len(tokens) >= 2:
            fragmented.append(word)
            if verbose and len(fragmented) <= 30:
                logger.info(f"  ADD: '{word}' -> {tokens} ({len(tokens)} tokens)")
        else:
            already_single += 1

    logger.info(f"Fragmented (will add): {len(fragmented)}")
    logger.info(f"Already single token (skip): {already_single}")

    return fragmented, base_vocab_size


def build_custom_tokens(
    patterns_dir: Path = PATTERNS_DIR,
    processed_dir: Path = PROCESSED_DIR,
    output_file: Path = OUTPUT_FILE,
    model_name: str = BASE_MODEL,
    min_freq: int = DEFAULT_MIN_FREQ,
    verbose: bool = False,
) -> dict:
    """Build and save the custom token list from patterns + training data.

    Args:
        patterns_dir: Directory containing pattern JSON files
        processed_dir: Directory containing processed training JSONL files
        output_file: Path to write the output JSON
        model_name: HuggingFace model name for tokenizer
        min_freq: Minimum frequency for training data misspellings
        verbose: Enable verbose logging

    Returns:
        The output data dict
    """
    logger.info("Building custom dyslexic token list...")
    logger.info(f"  Pattern directory: {patterns_dir}")
    logger.info(f"  Training data directory: {processed_dir}")
    logger.info(f"  Base model: {model_name}")
    logger.info(f"  Min frequency for training data: {min_freq}")

    # Step 1: Load misspellings from pattern files
    logger.info("\n--- Source 1: Pattern Files ---")
    pattern_misspellings = load_misspellings_from_patterns(patterns_dir, verbose=verbose)
    logger.info(f"Pattern files: {len(pattern_misspellings)} misspellings")

    # Step 2: Load misspellings from training data
    logger.info("\n--- Source 2: Training Data (freq >= {}) ---".format(min_freq))
    training_misspellings = load_misspellings_from_training_data(
        processed_dir, min_freq=min_freq, verbose=verbose,
    )

    # Step 3: Merge and deduplicate
    all_words = set(pattern_misspellings.keys()) | set(training_misspellings.keys())
    logger.info(f"\nTotal unique misspellings (merged): {len(all_words)}")
    logger.info(f"  From patterns only: {len(set(pattern_misspellings.keys()) - set(training_misspellings.keys()))}")
    logger.info(f"  From training only: {len(set(training_misspellings.keys()) - set(pattern_misspellings.keys()))}")
    logger.info(f"  Overlap: {len(set(pattern_misspellings.keys()) & set(training_misspellings.keys()))}")

    if not all_words:
        logger.error("No misspellings found")
        return {}

    # Step 4: Filter to only those that fragment
    logger.info("\n--- Filtering for fragmentation ---")
    fragmented, base_vocab_size = filter_fragmented_tokens(
        list(all_words), model_name, verbose=verbose,
    )

    if not fragmented:
        logger.warning("No fragmented tokens found")
        return {}

    # Step 5: Build output with source tracking
    output = {
        "description": "Dyslexic misspellings that fragment under flan-t5-base SentencePiece",
        "base_model": model_name,
        "base_vocab_size": base_vocab_size,
        "tokens": sorted(fragmented),
        "token_count": len(fragmented),
        "min_freq": min_freq,
        "sources": {
            "pattern_files": MISSPELLING_PATTERN_FILES,
            "training_data": TRAINING_DATA_FILES,
        },
        "stats": {
            "from_patterns": len(pattern_misspellings),
            "from_training_data": len(training_misspellings),
            "merged_unique": len(all_words),
            "fragmented": len(fragmented),
        },
    }

    # Step 6: Write to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    logger.info(f"\nWrote {len(fragmented)} custom tokens to {output_file}")
    size_kb = len(fragmented) * 768 * 4 / 1024
    logger.info(f"Estimated model size increase: ~{size_kb:.0f} KB ({size_kb / 1024:.1f} MB)")
    return output


def main():
    parser = argparse.ArgumentParser(
        description="Build custom token list from dyslexic misspelling patterns and training data"
    )
    parser.add_argument(
        "--patterns-dir",
        type=str,
        default=None,
        help=f"Pattern directory (default: {PATTERNS_DIR})",
    )
    parser.add_argument(
        "--processed-dir",
        type=str,
        default=None,
        help=f"Processed training data directory (default: {PROCESSED_DIR})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help=f"Output file (default: {OUTPUT_FILE})",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=BASE_MODEL,
        help=f"Base model for tokenizer (default: {BASE_MODEL})",
    )
    parser.add_argument(
        "--min-freq",
        type=int,
        default=DEFAULT_MIN_FREQ,
        help=f"Minimum frequency for training data misspellings (default: {DEFAULT_MIN_FREQ})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show per-token details",
    )
    args = parser.parse_args()

    patterns_dir = Path(args.patterns_dir) if args.patterns_dir else PATTERNS_DIR
    processed_dir = Path(args.processed_dir) if args.processed_dir else PROCESSED_DIR
    output_file = Path(args.output) if args.output else OUTPUT_FILE

    result = build_custom_tokens(
        patterns_dir=patterns_dir,
        processed_dir=processed_dir,
        output_file=output_file,
        model_name=args.model,
        min_freq=args.min_freq,
        verbose=args.verbose,
    )

    if result:
        logger.info(f"\nSummary: {result['token_count']} tokens ready for training")
    else:
        logger.error("Failed to build custom token list")


if __name__ == "__main__":
    main()
