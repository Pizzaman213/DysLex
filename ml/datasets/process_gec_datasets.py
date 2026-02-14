"""Download and process Grammar Error Correction (GEC) datasets.

Converts GEC datasets to seq2seq JSONL format compatible with the
Quick Correction Model training pipeline.

Supported datasets:
  - JFLEG: ~1,500 fluency-corrected sentences (freely available)
  - W&I+LOCNESS (BEA-2019): filtered for native-writer subset

Output format (same as existing seq2seq data):
  {"input_text": "<erroneous>", "target_text": "<corrected>", "source": "jfleg", "error_type": "grammar"}
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def classify_grammar_error(source: str, target: str) -> str:
    """Classify the type of grammar error by comparing source and target.

    Args:
        source: Original (erroneous) text
        target: Corrected text

    Returns:
        Error type string
    """
    src_words = source.lower().split()
    tgt_words = target.lower().split()

    # Word count change suggests insertion/deletion
    if len(tgt_words) > len(src_words):
        # Check for article insertion
        diff_words = set(tgt_words) - set(src_words)
        if diff_words & {"a", "an", "the"}:
            return "article"
        # Check for function word insertion
        preps = {"to", "in", "on", "at", "for", "with", "of", "from", "by", "about"}
        if diff_words & preps:
            return "function_word"
        return "grammar"

    if len(tgt_words) < len(src_words):
        return "run_on"

    # Same word count — check for verb/pronoun changes
    changes = []
    for s, t in zip(src_words, tgt_words):
        s_clean = re.sub(r'[^\w]', '', s)
        t_clean = re.sub(r'[^\w]', '', t)
        if s_clean != t_clean:
            changes.append((s_clean, t_clean))

    if not changes:
        # Punctuation-only changes
        return "run_on"

    # Check for verb form changes (subject-verb agreement)
    verb_endings = {("s", ""), ("es", ""), ("", "s"), ("", "es")}
    for src_w, tgt_w in changes:
        for end_s, end_t in verb_endings:
            if src_w.endswith(end_s) and tgt_w.endswith(end_t):
                base_s = src_w[:len(src_w) - len(end_s)] if end_s else src_w
                base_t = tgt_w[:len(tgt_w) - len(end_t)] if end_t else tgt_w
                if base_s == base_t:
                    return "subject_verb"

    # Check for tense changes
    for src_w, tgt_w in changes:
        if src_w.endswith("ed") and not tgt_w.endswith("ed"):
            return "verb_tense"
        if not src_w.endswith("ed") and tgt_w.endswith("ed"):
            return "verb_tense"

    # Check for pronoun case changes
    pronoun_forms = {
        "i": "me", "me": "i", "he": "him", "him": "he",
        "she": "her", "her": "she", "we": "us", "us": "we",
        "they": "them", "them": "they",
    }
    for src_w, tgt_w in changes:
        if pronoun_forms.get(src_w) == tgt_w:
            return "pronoun_case"

    return "grammar"


def parse_jfleg(data_dir: Path) -> list[dict[str, str]]:
    """Parse JFLEG dataset into seq2seq training pairs.

    JFLEG format: paired files with source sentences and 4 reference corrections.
    We use all available references as separate training pairs.

    Args:
        data_dir: Directory containing JFLEG data files

    Returns:
        List of seq2seq training pairs
    """
    pairs: list[dict[str, str]] = []

    # JFLEG has test and dev splits, each with source + 4 reference files
    for split in ["test", "dev"]:
        src_file = data_dir / f"{split}" / f"{split}.src"
        if not src_file.exists():
            # Try flat layout
            src_file = data_dir / f"{split}.src"
        if not src_file.exists():
            continue

        sources = src_file.read_text().strip().split("\n")

        # Try up to 4 references
        for ref_idx in range(4):
            ref_file = data_dir / f"{split}" / f"{split}.ref{ref_idx}"
            if not ref_file.exists():
                ref_file = data_dir / f"{split}.ref{ref_idx}"
            if not ref_file.exists():
                continue

            references = ref_file.read_text().strip().split("\n")

            for src, ref in zip(sources, references):
                src = src.strip()
                ref = ref.strip()
                if not src or not ref:
                    continue
                if src == ref:
                    continue

                error_type = classify_grammar_error(src, ref)
                pairs.append({
                    "input_text": src,
                    "target_text": ref,
                    "source": "jfleg",
                    "error_type": error_type,
                })

    logger.info(f"Parsed {len(pairs)} JFLEG pairs")
    return pairs


def parse_wi_locness(data_dir: Path) -> list[dict[str, str]]:
    """Parse W&I+LOCNESS (BEA-2019) dataset.

    Format: M2 annotation files with source sentences and edits.
    We extract source-target pairs from the annotations.

    Args:
        data_dir: Directory containing W&I+LOCNESS data

    Returns:
        List of seq2seq training pairs
    """
    pairs: list[dict[str, str]] = []

    # Look for M2 files or pre-processed TSV/JSONL
    for m2_file in sorted(data_dir.glob("*.m2")):
        pairs.extend(_parse_m2_file(m2_file, source_name="wi_locness"))

    # Also check for pre-processed JSONL
    for jsonl_file in sorted(data_dir.glob("*.jsonl")):
        with open(jsonl_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                sample = json.loads(line)
                src = sample.get("source", sample.get("input", "")).strip()
                tgt = sample.get("target", sample.get("output", "")).strip()
                if src and tgt and src != tgt:
                    error_type = classify_grammar_error(src, tgt)
                    pairs.append({
                        "input_text": src,
                        "target_text": tgt,
                        "source": "wi_locness",
                        "error_type": error_type,
                    })

    logger.info(f"Parsed {len(pairs)} W&I+LOCNESS pairs")
    return pairs


def _parse_m2_file(filepath: Path, source_name: str = "gec") -> list[dict[str, str]]:
    """Parse an M2-format file into source-target pairs.

    M2 format:
        S <source sentence>
        A <start> <end>|||<type>|||<correction>|||...
        (blank line separates sentences)

    Args:
        filepath: Path to M2 file
        source_name: Source name for tracking

    Returns:
        List of seq2seq training pairs
    """
    pairs: list[dict[str, str]] = []

    with open(filepath) as f:
        content = f.read()

    blocks = content.strip().split("\n\n")

    for block in blocks:
        lines = block.strip().split("\n")
        if not lines:
            continue

        source_line = ""
        edits: list[tuple[int, int, str]] = []

        for line in lines:
            if line.startswith("S "):
                source_line = line[2:].strip()
            elif line.startswith("A "):
                parts = line[2:].split("|||")
                if len(parts) >= 3:
                    span = parts[0].strip().split()
                    if len(span) >= 2:
                        try:
                            start = int(span[0])
                            end = int(span[1])
                            correction = parts[2].strip()
                            if correction != "-NONE-":
                                edits.append((start, end, correction))
                        except ValueError:
                            continue

        if not source_line or not edits:
            continue

        # Apply edits to reconstruct target
        words = source_line.split()
        target_words = list(words)

        # Apply edits in reverse order to preserve indices
        for start, end, correction in sorted(edits, key=lambda x: -x[0]):
            if start <= len(target_words):
                actual_end = min(end, len(target_words))
                if correction:
                    target_words[start:actual_end] = correction.split()
                else:
                    target_words[start:actual_end] = []

        target_line = " ".join(target_words)

        if source_line != target_line:
            error_type = classify_grammar_error(source_line, target_line)
            pairs.append({
                "input_text": source_line,
                "target_text": target_line,
                "source": source_name,
                "error_type": error_type,
            })

    return pairs


def parse_tsv_pairs(filepath: Path, source_name: str = "gec") -> list[dict[str, str]]:
    """Parse a simple TSV file with source\\ttarget pairs.

    Args:
        filepath: Path to TSV file
        source_name: Source name for tracking

    Returns:
        List of seq2seq training pairs
    """
    pairs: list[dict[str, str]] = []

    with open(filepath) as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                src, tgt = parts[0].strip(), parts[1].strip()
                if src and tgt and src != tgt:
                    error_type = classify_grammar_error(src, tgt)
                    pairs.append({
                        "input_text": src,
                        "target_text": tgt,
                        "source": source_name,
                        "error_type": error_type,
                    })

    logger.info(f"Parsed {len(pairs)} pairs from {filepath.name}")
    return pairs


def process_gec_data(
    raw_dir: Path,
    output_dir: Path,
) -> dict[str, int]:
    """Process all available GEC datasets into seq2seq JSONL.

    Looks for JFLEG and W&I+LOCNESS data in raw_dir subdirectories.

    Args:
        raw_dir: Directory containing raw GEC dataset subdirectories
        output_dir: Directory to write processed JSONL files

    Returns:
        Dictionary mapping source names to sample counts
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, int] = {}

    # Process JFLEG
    jfleg_dir = raw_dir / "jfleg"
    if jfleg_dir.exists():
        jfleg_pairs = parse_jfleg(jfleg_dir)
        if jfleg_pairs:
            outfile = output_dir / "jfleg_seq2seq.jsonl"
            with open(outfile, "w") as f:
                for pair in jfleg_pairs:
                    f.write(json.dumps(pair) + "\n")
            results["jfleg"] = len(jfleg_pairs)
            logger.info(f"Wrote {len(jfleg_pairs)} JFLEG samples to {outfile}")

    # Process W&I+LOCNESS
    wi_dir = raw_dir / "wi_locness"
    if not wi_dir.exists():
        wi_dir = raw_dir / "bea2019"
    if wi_dir.exists():
        wi_pairs = parse_wi_locness(wi_dir)
        if wi_pairs:
            outfile = output_dir / "wi_locness_seq2seq.jsonl"
            with open(outfile, "w") as f:
                for pair in wi_pairs:
                    f.write(json.dumps(pair) + "\n")
            results["wi_locness"] = len(wi_pairs)
            logger.info(f"Wrote {len(wi_pairs)} W&I+LOCNESS samples to {outfile}")

    # Process any TSV pair files in a gec/ subdirectory
    gec_dir = raw_dir / "gec"
    if gec_dir.exists():
        for tsv_file in sorted(gec_dir.glob("*.tsv")):
            pairs = parse_tsv_pairs(tsv_file, source_name=tsv_file.stem)
            if pairs:
                outfile = output_dir / f"{tsv_file.stem}_seq2seq.jsonl"
                with open(outfile, "w") as f:
                    for pair in pairs:
                        f.write(json.dumps(pair) + "\n")
                results[tsv_file.stem] = len(pairs)

    total = sum(results.values())
    logger.info(f"GEC processing complete: {total} total samples from {len(results)} sources")
    return results


def main():
    """Process GEC datasets from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Process GEC datasets for grammar training")
    parser.add_argument(
        "--raw-dir",
        type=str,
        default=None,
        help="Directory containing raw GEC data (default: ml/datasets/raw)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory for processed output (default: ml/datasets/processed)",
    )
    args = parser.parse_args()

    ml_dir = Path(__file__).parent.parent
    raw_dir = Path(args.raw_dir) if args.raw_dir else ml_dir / "datasets" / "raw"
    output_dir = Path(args.output_dir) if args.output_dir else ml_dir / "datasets" / "processed"

    process_gec_data(raw_dir, output_dir)


if __name__ == "__main__":
    main()
