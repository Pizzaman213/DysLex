"""Combine processed datasets into train/val/test splits.

Merges multiple data sources (real misspelling datasets + synthetic data)
into balanced train/val/test splits for model training.

Split ratios: 87.5% train, 9.7% val, 2.8% test (adjustable)
"""

import json
import logging
import random
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

random.seed(42)

# Default sampling weights by source (higher = more samples selected)
# Rebalanced to prioritize dyslexia-specific spelling data over grammar
# github_typo excluded — code/XML/markdown noise hurts dyslexic writing correction
SOURCE_WEIGHTS = {
    "birkbeck": 0.40,
    "wikipedia": 0.15,
    "aspell": 0.10,
    "synthetic": 0.20,
    "pedler": 0.10,
    "grammar_synthetic": 0.03,
    "mixed_synthetic": 0.02,
}

# Sources to exclude entirely (not relevant to dyslexic writing)
EXCLUDED_SOURCES = {"github_typo"}

# Error types that represent core dyslexic patterns — oversampled 2x
DYSLEXIA_CORE_ERROR_TYPES = {
    "phonetic", "reversal", "vowel_confusion", "homophone", "visual_similarity",
}

# Error types that are severely underrepresented and need aggressive oversampling
UNDERSAMPLE_TARGETS = {
    "reversal": 3000,
    "transposition": 3000,
    "visual_similarity": 2000,
    "vowel_confusion": 2000,
}

# Pattern files for augmentation (multi-error injection)
PATTERNS_DIR = Path(__file__).parent.parent / "synthetic_data" / "patterns"


def _load_jsonl(filepath: Path) -> list[dict[str, Any]]:
    """Load samples from a JSONL file."""
    samples = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


def _write_jsonl(samples: list[dict[str, Any]], filepath: Path) -> None:
    """Write samples to a JSONL file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        for sample in samples:
            f.write(json.dumps(sample) + "\n")


def _load_error_pairs() -> list[tuple[str, str]]:
    """Load (correct, error) pairs from pattern files for augmentation."""
    pairs: list[tuple[str, str]] = []
    pattern_files = ["transpositions.json", "vowel_confusion.json", "visual_similarity.json", "omissions.json"]

    for filename in pattern_files:
        filepath = PATTERNS_DIR / filename
        if not filepath.exists():
            continue
        with open(filepath) as f:
            data = json.load(f)
        examples_key = "common_examples" if "common_examples" in data else "examples"
        for ex in data.get(examples_key, []):
            correct = ex.get("correct", "")
            error = ex.get("error", "")
            if correct and error and correct.lower() != error.lower():
                pairs.append((correct.lower(), error.lower()))

    return pairs


def augment_training_data(
    samples: list[dict[str, Any]],
    multi_error_ratio: float = 0.15,
    position_shuffle_ratio: float = 0.10,
) -> list[dict[str, Any]]:
    """Augment training data with multi-error and position-varied samples.

    Two strategies:
    1. Multi-error injection: For a fraction of samples, inject a second random
       error into a different word in the sentence.
    2. Error position shuffling: Create variants with the same error word
       at different positions in the sentence.

    Args:
        samples: Original training samples
        multi_error_ratio: Fraction of samples to create multi-error variants for
        position_shuffle_ratio: Fraction of samples to create position variants for

    Returns:
        Augmented samples (original + new variants)
    """
    error_pairs = _load_error_pairs()
    if not error_pairs:
        logger.warning("No error pairs loaded for augmentation, skipping")
        return samples

    # Build a lookup from correct word -> list of error variants
    correct_to_errors: dict[str, list[str]] = {}
    for correct, error in error_pairs:
        correct_to_errors.setdefault(correct, []).append(error)

    augmented: list[dict[str, Any]] = []
    multi_error_count = 0
    position_count = 0

    # Strategy 1: Multi-error injection
    n_multi = int(len(samples) * multi_error_ratio)
    multi_candidates = random.sample(range(len(samples)), min(n_multi, len(samples)))

    for idx in multi_candidates:
        sample = samples[idx]
        input_text = sample.get("input_text", "")
        target_text = sample.get("target_text", "")

        # Find a word in the target that has a known error variant
        target_words = target_text.split()
        injectable = [
            (i, w) for i, w in enumerate(target_words)
            if w.lower() in correct_to_errors
        ]

        if not injectable:
            continue

        # Pick a random word to inject an error into
        word_idx, word = random.choice(injectable)
        error_variant = random.choice(correct_to_errors[word.lower()])

        # Apply the error to both input and keep target clean
        input_words = input_text.split()
        # Only inject if this word position exists and matches in input
        if word_idx < len(input_words) and input_words[word_idx].lower() == word.lower():
            new_input_words = list(input_words)
            # Preserve original casing pattern
            if word[0].isupper():
                error_variant = error_variant.capitalize()
            new_input_words[word_idx] = error_variant

            new_sample = dict(sample)
            new_sample["input_text"] = " ".join(new_input_words)
            new_sample["error_type"] = sample.get("error_type", "unknown") + "+augmented"
            new_sample["source"] = sample.get("source", "unknown")
            augmented.append(new_sample)
            multi_error_count += 1

    # Strategy 2: Error position shuffling
    # For samples where error word is near start/end, create a variant with it in middle
    n_position = int(len(samples) * position_shuffle_ratio)
    position_candidates = random.sample(range(len(samples)), min(n_position, len(samples)))

    for idx in position_candidates:
        sample = samples[idx]
        input_text = sample.get("input_text", "")
        target_text = sample.get("target_text", "")
        input_words = input_text.split()
        target_words = target_text.split()

        min_len = min(len(input_words), len(target_words))
        if min_len < 4:
            continue

        # Find differing words (the error)
        diffs = [
            i for i, (iw, tw) in enumerate(zip(input_words, target_words))
            if iw.lower() != tw.lower()
        ]
        if not diffs or len(diffs) > 2:
            continue

        error_pos = diffs[0]

        # Only shuffle if error is in first or last quarter
        if min_len // 4 < error_pos < min_len * 3 // 4:
            continue

        # Swap the error word position with a word in the middle
        mid = min_len // 2
        if mid == error_pos:
            continue

        new_input = list(input_words)
        new_target = list(target_words)
        new_input[error_pos], new_input[mid] = new_input[mid], new_input[error_pos]
        new_target[error_pos], new_target[mid] = new_target[mid], new_target[error_pos]

        new_sample = dict(sample)
        new_sample["input_text"] = " ".join(new_input)
        new_sample["target_text"] = " ".join(new_target)
        new_sample["error_type"] = sample.get("error_type", "unknown") + "+shuffled"
        new_sample["source"] = sample.get("source", "unknown")
        augmented.append(new_sample)
        position_count += 1

    logger.info(
        f"Augmentation: +{multi_error_count} multi-error, "
        f"+{position_count} position-shuffled "
        f"({len(augmented)} total new samples)"
    )

    return samples + augmented


def combine_and_split(
    processed_dir: Path,
    output_dir: Path,
    target_total: int = 80000,
    train_ratio: float = 0.875,
    val_ratio: float = 0.097,
) -> dict[str, int]:
    """Combine BIO format datasets into train/val/test splits.

    Args:
        processed_dir: Directory with processed JSONL files
        output_dir: Directory to write combined splits
        target_total: Target total number of samples
        train_ratio: Fraction for training set
        val_ratio: Fraction for validation set

    Returns:
        Dict mapping split name to sample count
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load all BIO data sources
    all_samples: list[dict[str, Any]] = []
    for filepath in sorted(processed_dir.glob("*.jsonl")):
        if "_seq2seq" in filepath.name:
            continue  # Skip seq2seq files
        samples = _load_jsonl(filepath)
        source = filepath.stem
        logger.info(f"  Loaded {len(samples)} BIO samples from {source}")
        all_samples.extend(samples)

    if not all_samples:
        logger.error("No BIO data found to combine")
        return {"train": 0, "val": 0, "test": 0}

    # Subsample if we have more than target
    if len(all_samples) > target_total:
        random.shuffle(all_samples)
        all_samples = all_samples[:target_total]

    # Split
    random.shuffle(all_samples)
    n_train = int(len(all_samples) * train_ratio)
    n_val = int(len(all_samples) * val_ratio)

    train = all_samples[:n_train]
    val = all_samples[n_train : n_train + n_val]
    test = all_samples[n_train + n_val :]

    _write_jsonl(train, output_dir / "train.jsonl")
    _write_jsonl(val, output_dir / "val.jsonl")
    _write_jsonl(test, output_dir / "test.jsonl")

    results = {"train": len(train), "val": len(val), "test": len(test)}
    logger.info(f"BIO splits: train={len(train)}, val={len(val)}, test={len(test)}")
    return results


def combine_and_split_seq2seq(
    processed_dir: Path,
    output_dir: Path,
    target_total: int = 80000,
    train_ratio: float = 0.875,
    val_ratio: float = 0.097,
    augment: bool = False,
) -> dict[str, int]:
    """Combine seq2seq format datasets into train/val/test splits.

    Intelligently samples from multiple sources to create a balanced dataset.
    When grammar data is present, creates separate spelling/grammar test files
    for regression tracking.

    Args:
        processed_dir: Directory with processed JSONL files
        output_dir: Directory to write combined splits
        target_total: Target total number of samples
        train_ratio: Fraction for training set
        val_ratio: Fraction for validation set
        augment: If True, apply data augmentation (multi-error + position shuffle)

    Returns:
        Dict mapping split name to sample count
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Grammar error types for categorization
    grammar_types = {
        "subject_verb", "article", "verb_tense", "function_word",
        "word_order", "run_on", "pronoun_case", "grammar",
    }

    # Load all seq2seq data sources (excluding noisy sources)
    sources: dict[str, list[dict[str, Any]]] = {}
    for filepath in sorted(processed_dir.glob("*_seq2seq.jsonl")):
        source_name = filepath.stem.replace("_seq2seq", "")
        if source_name in EXCLUDED_SOURCES:
            logger.info(f"  SKIPPING {source_name} (in EXCLUDED_SOURCES)")
            continue
        samples = _load_jsonl(filepath)
        if samples:
            sources[source_name] = samples
            logger.info(f"  Loaded {len(samples)} seq2seq samples from {source_name}")

    if not sources:
        logger.error("No seq2seq data found to combine")
        return {"train": 0, "val": 0, "test": 0}

    total_available = sum(len(s) for s in sources.values())
    logger.info(f"Total available: {total_available} samples from {len(sources)} sources")

    # Determine samples per source based on weights
    all_samples: list[dict[str, Any]] = []
    has_grammar = any(
        name in ("grammar_synthetic", "mixed_synthetic") for name in sources
    )

    for source_name, samples in sources.items():
        weight = SOURCE_WEIGHTS.get(source_name, 0.05)
        target_for_source = int(target_total * weight)

        # Don't undersample if source is small
        if len(samples) <= target_for_source:
            selected = samples
        else:
            random.shuffle(samples)
            selected = samples[:target_for_source]

        all_samples.extend(selected)
        logger.info(
            f"  {source_name}: selected {len(selected)}/{len(samples)} "
            f"(weight={weight:.2f}, target={target_for_source})"
        )

    # If we're still under target, add more from the largest source
    if len(all_samples) < target_total:
        deficit = target_total - len(all_samples)
        # Find sources with remaining samples
        used_counts: dict[str, int] = {}
        for sample in all_samples:
            src = sample.get("source", "unknown")
            used_counts[src] = used_counts.get(src, 0) + 1

        for source_name in sorted(sources.keys(), key=lambda k: len(sources[k]), reverse=True):
            if deficit <= 0:
                break
            used = used_counts.get(source_name, 0)
            remaining = [s for i, s in enumerate(sources[source_name]) if i >= used]
            if remaining:
                take = min(len(remaining), deficit)
                random.shuffle(remaining)
                all_samples.extend(remaining[:take])
                deficit -= take
                logger.info(f"  {source_name}: added {take} more to fill target")

    # Oversample core dyslexic error types 2x (phonetic, reversal, vowel, homophone, visual)
    core_samples = [
        s for s in all_samples
        if s.get("error_type", "unknown") in DYSLEXIA_CORE_ERROR_TYPES
    ]
    if core_samples:
        all_samples.extend(core_samples)  # duplicate = 2x total
        logger.info(f"  Oversampled {len(core_samples)} core dyslexic error samples (2x)")

    # Aggressively oversample severely underrepresented error types
    for error_type, target_count in UNDERSAMPLE_TARGETS.items():
        type_samples = [
            s for s in all_samples
            if s.get("error_type", "unknown") == error_type
        ]
        current_count = len(type_samples)
        if 0 < current_count < target_count:
            copies_needed = target_count - current_count
            oversampled = []
            while len(oversampled) < copies_needed:
                oversampled.extend(type_samples)
            oversampled = oversampled[:copies_needed]
            all_samples.extend(oversampled)
            logger.info(
                f"  Oversampled '{error_type}': {current_count} -> {current_count + copies_needed} "
                f"(target: {target_count})"
            )

    # Data augmentation (before cap, after oversampling)
    if augment:
        logger.info("Applying data augmentation...")
        all_samples = augment_training_data(all_samples)

    # Cap at target
    if len(all_samples) > target_total:
        random.shuffle(all_samples)
        all_samples = all_samples[:target_total]

    logger.info(f"Combined dataset: {len(all_samples)} samples")

    # Merge hard examples if they exist
    hard_examples_file = output_dir / "hard_examples_seq2seq.jsonl"
    if hard_examples_file.exists():
        hard_samples = _load_jsonl(hard_examples_file)
        if hard_samples:
            all_samples.extend(hard_samples)
            logger.info(f"  Added {len(hard_samples)} hard examples from previous mining")

    # Split into train/val/test
    random.shuffle(all_samples)
    n_train = int(len(all_samples) * train_ratio)
    n_val = int(len(all_samples) * val_ratio)

    train = all_samples[:n_train]
    val = all_samples[n_train : n_train + n_val]
    test = all_samples[n_train + n_val :]

    _write_jsonl(train, output_dir / "train_seq2seq.jsonl")
    _write_jsonl(val, output_dir / "val_seq2seq.jsonl")
    _write_jsonl(test, output_dir / "test_seq2seq.jsonl")

    results = {"train": len(train), "val": len(val), "test": len(test)}
    logger.info(f"Seq2seq splits: train={len(train)}, val={len(val)}, test={len(test)}")

    # Create curriculum phase splits for curriculum learning
    if has_grammar:
        spelling_types = {
            "reversal", "transposition", "phonetic", "omission", "spelling",
            "vowel_confusion", "homophone", "visual_similarity",
        }
        grammar_types_set = grammar_types
        mixed_types = {"mixed_multi_2", "mixed_multi_3", "mixed_multi_4", "mixed_single_long"}

        # Phase datasets only for training set
        phase1_spelling = [
            s for s in train
            if s.get("error_type", "unknown") in spelling_types
            or s.get("source", "") in ("birkbeck_seq2seq", "wikipedia_seq2seq", "aspell_seq2seq", "synthetic_seq2seq")
        ]
        phase2_grammar = phase1_spelling + [
            s for s in train
            if s.get("error_type", "unknown") in grammar_types_set
            or s.get("source", "") == "grammar_synthetic"
        ]
        phase3_mixed = phase2_grammar + [
            s for s in train
            if s.get("error_type", "unknown").startswith("mixed_")
            or s.get("source", "") == "synthetic_mixed"
        ]

        if phase1_spelling:
            _write_jsonl(phase1_spelling, output_dir / "train_seq2seq_phase1.jsonl")
            logger.info(f"  Curriculum phase 1 (spelling): {len(phase1_spelling)} samples")
        if phase2_grammar:
            _write_jsonl(phase2_grammar, output_dir / "train_seq2seq_phase2.jsonl")
            logger.info(f"  Curriculum phase 2 (+grammar): {len(phase2_grammar)} samples")
        if phase3_mixed:
            _write_jsonl(phase3_mixed, output_dir / "train_seq2seq_phase3.jsonl")
            logger.info(f"  Curriculum phase 3 (+mixed): {len(phase3_mixed)} samples")

    # Create separate spelling/grammar test files for regression tracking
    if has_grammar:
        spelling_test = [
            s for s in test
            if s.get("error_type", "unknown") not in grammar_types
            and s.get("error_type") != "none"
        ]
        grammar_test = [
            s for s in test
            if s.get("error_type", "unknown") in grammar_types
        ]

        if spelling_test:
            _write_jsonl(spelling_test, output_dir / "test_seq2seq_spelling.jsonl")
            logger.info(f"  Spelling test subset: {len(spelling_test)} samples")
            results["test_spelling"] = len(spelling_test)

        if grammar_test:
            _write_jsonl(grammar_test, output_dir / "test_seq2seq_grammar.jsonl")
            logger.info(f"  Grammar test subset: {len(grammar_test)} samples")
            results["test_grammar"] = len(grammar_test)

    # Create per-error-type stratified test sets
    mixed_types = {"mixed_multi_2", "mixed_multi_3", "mixed_multi_4", "mixed_single_long"}
    mixed_prefixes = ("mixed_",)

    mixed_test = [
        s for s in test
        if s.get("error_type", "unknown").startswith("mixed_")
        or s.get("error_type", "unknown") in mixed_types
    ]
    if mixed_test:
        _write_jsonl(mixed_test, output_dir / "test_seq2seq_mixed.jsonl")
        logger.info(f"  Mixed test subset: {len(mixed_test)} samples")
        results["test_mixed"] = len(mixed_test)

    # Per-grammar-subtype test sets (function_word, verb_tense)
    for subtype in ["function_word", "verb_tense"]:
        subtype_test = [
            s for s in test
            if s.get("error_type", "unknown") == subtype
        ]
        if subtype_test:
            _write_jsonl(subtype_test, output_dir / f"test_seq2seq_{subtype}.jsonl")
            logger.info(f"  {subtype} test subset: {len(subtype_test)} samples")
            results[f"test_{subtype}"] = len(subtype_test)

    # Create a "hard" test set: multi-error and long sentences
    hard_test = [
        s for s in test
        if s.get("error_type", "unknown") in mixed_types
        or (s.get("error_type", "unknown").startswith("mixed_multi_")
            and s.get("error_type", "unknown")[-1] in ("3", "4"))
    ]
    if hard_test:
        _write_jsonl(hard_test, output_dir / "test_seq2seq_hard.jsonl")
        logger.info(f"  Hard test subset: {len(hard_test)} samples")
        results["test_hard"] = len(hard_test)

    return results
