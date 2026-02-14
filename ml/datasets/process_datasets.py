"""Process raw misspelling datasets into training format.

Converts raw data files into JSONL with corrections embedded in sentences.

Output formats:
  - BIO (token classification): {"tokens": [...], "labels": [...]}
  - Seq2seq (text-to-text): {"input_text": "...", "target_text": "..."}
"""

import gzip
import json
import logging
import random
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

random.seed(42)


def _load_corpus_sentences(raw_dir: Path) -> list[str]:
    """Load corpus sentences for embedding misspellings into context.

    Args:
        raw_dir: Raw data directory (looks for corpus/sentences.txt sibling)

    Returns:
        List of clean sentences
    """
    corpus_file = raw_dir.parent / "corpus" / "sentences.txt"
    if corpus_file.exists():
        with open(corpus_file) as f:
            sentences = [line.strip() for line in f if line.strip()]
        logger.info(f"Loaded {len(sentences)} corpus sentences")
        return sentences

    # Fallback: generate basic sentences
    logger.warning("No corpus file found, using basic fallback sentences")
    return [
        "The student finished the assignment before the deadline.",
        "She walked to the store to buy groceries for dinner.",
        "He fixed the broken window in the living room yesterday.",
        "They decided to take the bus instead of driving to work.",
        "We need to complete the project by the end of the week.",
    ]


def _parse_birkbeck(filepath: Path) -> list[tuple[str, str]]:
    """Parse Birkbeck spelling error corpus.

    Format: $correct_word followed by misspelling lines until next $.

    Returns:
        List of (misspelling, correct) tuples
    """
    pairs = []
    current_correct = None

    with open(filepath, "rb") as f:
        for line in f:
            line = line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            if line.startswith("$"):
                current_correct = line[1:].strip().lower()
            elif current_correct:
                misspelling = line.strip().lower()
                # Clean underscores used as spaces in some entries
                misspelling = misspelling.replace("_", "")
                if misspelling and misspelling != current_correct:
                    pairs.append((misspelling, current_correct))

    logger.info(f"Parsed {len(pairs)} pairs from birkbeck")
    return pairs


def _parse_aspell(filepath: Path) -> list[tuple[str, str]]:
    """Parse Aspell test data.

    Same format as Birkbeck: $correct followed by misspellings.

    Returns:
        List of (misspelling, correct) tuples
    """
    pairs = []
    current_correct = None

    with open(filepath, "rb") as f:
        for line in f:
            line = line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            if line.startswith("$"):
                current_correct = line[1:].strip().lower()
            elif current_correct:
                misspelling = line.strip().lower()
                if misspelling and misspelling != current_correct:
                    pairs.append((misspelling, current_correct))

    logger.info(f"Parsed {len(pairs)} pairs from aspell")
    return pairs


def _parse_wikipedia(filepath: Path) -> list[tuple[str, str]]:
    """Parse Wikipedia common misspellings.

    Format: ` misspelling->correction` (space-prefixed, arrow-separated).
    Some entries have multiple corrections separated by commas.

    Returns:
        List of (misspelling, correct) tuples
    """
    pairs = []

    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if "->" not in line:
                continue
            # Skip wiki markup lines
            if line.startswith("<") or line.startswith("{") or line.startswith("["):
                continue
            if len(line) > 100:
                continue

            parts = line.split("->")
            if len(parts) != 2:
                continue

            misspelling = parts[0].strip().lower()
            corrections = parts[1].strip()

            # Take first correction if multiple
            correct = corrections.split(",")[0].strip().lower()

            if misspelling and correct and misspelling != correct:
                pairs.append((misspelling, correct))

    logger.info(f"Parsed {len(pairs)} pairs from wikipedia")
    return pairs


def _parse_github_typo(filepath: Path, max_pairs: int = 5000) -> list[tuple[str, str]]:
    """Parse GitHub Typo Corpus (gzipped JSONL).

    Returns:
        List of (misspelling, correct) tuples
    """
    pairs = []

    try:
        open_fn = gzip.open if filepath.suffix == ".gz" else open
        with open_fn(filepath, "rt", encoding="utf-8") as f:
            for line in f:
                if len(pairs) >= max_pairs:
                    break
                try:
                    entry = json.loads(line)
                    edits = entry.get("edits", [])
                    for edit in edits:
                        src = edit.get("src", {})
                        tgt = edit.get("tgt", {})
                        src_text = src.get("text", "").strip().lower()
                        tgt_text = tgt.get("text", "").strip().lower()
                        # Only single-word corrections
                        if (
                            src_text
                            and tgt_text
                            and " " not in src_text
                            and " " not in tgt_text
                            and src_text != tgt_text
                        ):
                            pairs.append((src_text, tgt_text))
                            if len(pairs) >= max_pairs:
                                break
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.warning(f"Error parsing github typo corpus: {e}")

    logger.info(f"Parsed {len(pairs)} pairs from github_typo")
    return pairs


def _classify_error(misspelling: str, correct: str) -> str:
    """Classify the type of spelling error."""
    if len(misspelling) == len(correct):
        # Check for transposition (adjacent swap)
        diffs = [i for i in range(len(misspelling)) if misspelling[i] != correct[i]]
        if len(diffs) == 2 and abs(diffs[0] - diffs[1]) == 1:
            if misspelling[diffs[0]] == correct[diffs[1]] and misspelling[diffs[1]] == correct[diffs[0]]:
                return "transposition"
        # Check for reversal (b/d, p/q, etc.)
        reversals = {"b": "d", "d": "b", "p": "q", "q": "p", "m": "w", "w": "m"}
        if len(diffs) == 1:
            char = misspelling[diffs[0]]
            if char in reversals and reversals[char] == correct[diffs[0]]:
                return "reversal"
        return "phonetic"
    elif len(misspelling) < len(correct):
        return "omission"
    else:
        return "addition"


def _embed_in_sentence(
    misspelling: str,
    correct: str,
    sentences: list[str],
) -> tuple[str, str] | None:
    """Embed a misspelling into a random sentence that contains the correct word.

    Returns:
        (sentence_with_error, correct_sentence) or None if no match found
    """
    # Find sentences containing the correct word
    matching = []
    pattern = re.compile(r"\b" + re.escape(correct) + r"\b", re.IGNORECASE)
    for sent in sentences:
        if pattern.search(sent):
            matching.append(sent)

    if not matching:
        # Create a simple sentence with the word
        templates = [
            f"The {correct} was very important to the whole project.",
            f"She noticed the {correct} right away and pointed it out.",
            f"They discussed the {correct} at the meeting yesterday.",
        ]
        sent = random.choice(templates)
        error_sent = sent.replace(correct, misspelling, 1)
        return error_sent, sent

    sent = random.choice(matching)
    # Replace one occurrence with the misspelling, preserving case
    match = pattern.search(sent)
    if not match:
        return None

    original_word = match.group()
    # Preserve capitalization
    if original_word[0].isupper():
        error_word = misspelling[0].upper() + misspelling[1:]
    else:
        error_word = misspelling
    error_sent = sent[:match.start()] + error_word + sent[match.end():]

    return error_sent, sent


def _pairs_to_seq2seq(
    pairs: list[tuple[str, str]],
    sentences: list[str],
    source: str,
    max_samples: int | None = None,
) -> list[dict[str, str]]:
    """Convert word pairs into sentence-level seq2seq training data.

    Args:
        pairs: List of (misspelling, correct) tuples
        sentences: Corpus sentences to embed errors into
        source: Source name for tracking
        max_samples: Maximum samples to generate

    Returns:
        List of seq2seq training samples
    """
    samples = []
    random.shuffle(pairs)

    for misspelling, correct in pairs:
        if max_samples and len(samples) >= max_samples:
            break

        result = _embed_in_sentence(misspelling, correct, sentences)
        if result is None:
            continue

        error_sent, clean_sent = result
        error_type = _classify_error(misspelling, correct)

        samples.append({
            "input_text": error_sent,
            "target_text": clean_sent,
            "source": source,
            "error_type": error_type,
        })

        # Also add no-change samples (correct text stays unchanged) ~20%
        if random.random() < 0.2:
            samples.append({
                "input_text": clean_sent,
                "target_text": clean_sent,
                "source": source,
                "error_type": "none",
            })

    logger.info(f"Generated {len(samples)} seq2seq samples from {source}")
    return samples


def _pairs_to_bio(
    pairs: list[tuple[str, str]],
    sentences: list[str],
    source: str,
    max_samples: int | None = None,
) -> list[dict[str, Any]]:
    """Convert word pairs into BIO token classification format."""
    samples = []
    random.shuffle(pairs)

    for misspelling, correct in pairs:
        if max_samples and len(samples) >= max_samples:
            break

        result = _embed_in_sentence(misspelling, correct, sentences)
        if result is None:
            continue

        error_sent, clean_sent = result
        tokens = error_sent.split()
        labels = ["O"] * len(tokens)

        # Find and label the error token
        for i, token in enumerate(tokens):
            clean_token = re.sub(r"[^\w]", "", token.lower())
            if clean_token == misspelling.lower() or clean_token == misspelling:
                labels[i] = "B-ERR"
                break

        samples.append({
            "tokens": tokens,
            "labels": labels,
            "correction": correct,
            "source": source,
        })

    logger.info(f"Generated {len(samples)} BIO samples from {source}")
    return samples


def process_all(raw_dir: Path, output_dir: Path) -> dict[str, int]:
    """Process all raw datasets into BIO token classification format.

    Args:
        raw_dir: Directory containing raw data files
        output_dir: Directory to write processed JSONL files

    Returns:
        Dict mapping source name to sample count
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    sentences = _load_corpus_sentences(raw_dir)
    results: dict[str, int] = {}

    parsers = {
        "birkbeck": ("birkbeck_missp.dat", _parse_birkbeck),
        "aspell": ("aspell.dat", _parse_aspell),
        "wikipedia": ("wikipedia_misspellings.txt", _parse_wikipedia),
        "github_typo": ("github_typo_corpus.jsonl.gz", _parse_github_typo),
    }

    for source, (filename, parser) in parsers.items():
        filepath = raw_dir / filename
        outpath = output_dir / f"{source}.jsonl"

        if outpath.exists() and outpath.stat().st_size > 0:
            # Count existing samples
            with open(outpath) as f:
                count = sum(1 for _ in f)
            logger.info(f"  {source}: already processed ({count} samples), skipping")
            results[source] = count
            continue

        if not filepath.exists():
            logger.warning(f"  {source}: raw file not found at {filepath}")
            results[source] = 0
            continue

        pairs = parser(filepath)
        samples = _pairs_to_bio(pairs, sentences, source)

        with open(outpath, "w") as f:
            for sample in samples:
                f.write(json.dumps(sample) + "\n")

        results[source] = len(samples)

    return results


def process_all_seq2seq(raw_dir: Path, output_dir: Path) -> dict[str, int]:
    """Process all raw datasets into seq2seq text-to-text format.

    Args:
        raw_dir: Directory containing raw data files
        output_dir: Directory to write processed JSONL files

    Returns:
        Dict mapping source name to sample count
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    sentences = _load_corpus_sentences(raw_dir)
    results: dict[str, int] = {}

    parsers = {
        "birkbeck": ("birkbeck_missp.dat", _parse_birkbeck),
        "aspell": ("aspell.dat", _parse_aspell),
        "wikipedia": ("wikipedia_misspellings.txt", _parse_wikipedia),
        "github_typo": ("github_typo_corpus.jsonl.gz", _parse_github_typo),
    }

    for source, (filename, parser) in parsers.items():
        filepath = raw_dir / filename
        outpath = output_dir / f"{source}_seq2seq.jsonl"

        if outpath.exists() and outpath.stat().st_size > 0:
            with open(outpath) as f:
                count = sum(1 for _ in f)
            logger.info(f"  {source}: already processed ({count} seq2seq samples), skipping")
            results[source] = count
            continue

        if not filepath.exists():
            logger.warning(f"  {source}: raw file not found at {filepath}")
            results[source] = 0
            continue

        pairs = parser(filepath)
        samples = _pairs_to_seq2seq(pairs, sentences, source)

        with open(outpath, "w") as f:
            for sample in samples:
                f.write(json.dumps(sample) + "\n")

        results[source] = len(samples)

    return results
