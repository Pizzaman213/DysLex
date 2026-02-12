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
SOURCE_WEIGHTS = {
    "birkbeck": 0.18,
    "wikipedia": 0.12,
    "aspell": 0.08,
    "synthetic": 0.07,
    "github_typo": 0.05,
    "grammar_synthetic": 0.15,
    "mixed_synthetic": 0.30,
}


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

    Returns:
        Dict mapping split name to sample count
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Grammar error types for categorization
    grammar_types = {
        "subject_verb", "article", "verb_tense", "function_word",
        "word_order", "run_on", "pronoun_case", "grammar",
    }

    # Load all seq2seq data sources
    sources: dict[str, list[dict[str, Any]]] = {}
    for filepath in sorted(processed_dir.glob("*_seq2seq.jsonl")):
        source_name = filepath.stem.replace("_seq2seq", "")
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

    # Cap at target
    if len(all_samples) > target_total:
        random.shuffle(all_samples)
        all_samples = all_samples[:target_total]

    logger.info(f"Combined dataset: {len(all_samples)} samples")

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
        spelling_types = {"reversal", "transposition", "phonetic", "omission", "spelling"}
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
