"""Extract a correction dictionary from training data word pairs.

Builds a JSON mapping of misspelling -> correction from all parsed datasets.
This ships with the frontend as the base correction lookup for the ONNX model.
The user's personal error profile merges on top at runtime.

Output: ml/models/quick_correction_base_v1/correction_dict.json
"""

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "ml" / "datasets" / "raw"
ONNX_MODEL_DIR = PROJECT_ROOT / "ml" / "models" / "quick_correction_base_v1"


def extract_dictionary(
    raw_dir: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, str]:
    """Extract misspelling -> correction mapping from all dataset sources.

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

    # Import parsers
    from ml.datasets.process_datasets import (
        parse_aspell,
        parse_birkbeck,
        parse_github_typo,
        parse_wikipedia,
    )

    correction_dict: dict[str, str] = {}

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
        for misspelling, correct in pairs:
            misspelling = misspelling.lower().strip()
            correct = correct.lower().strip()

            # Skip if same, empty, or too short
            if not misspelling or not correct or misspelling == correct:
                continue
            if len(misspelling) < 2 or len(correct) < 2:
                continue

            # First occurrence wins (most reliable sources parsed first)
            if misspelling not in correction_dict:
                correction_dict[misspelling] = correct
                added += 1

        logger.info(f"  {source}: {added} new entries (from {len(pairs)} pairs)")

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
