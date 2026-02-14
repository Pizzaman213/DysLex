"""Mine hard examples from training data for oversampled retraining.

After an initial training run, evaluates the model on training data to find
samples it gets wrong, then creates an oversampled JSONL for the next round.

Usage:
    python ml/quick_correction/mine_hard_examples.py --verbose
"""

import argparse
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any

import torch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent / "models" / "quick_correction_seq2seq_v1"
DATA_DIR = Path(__file__).parent / "data"
TRAIN_FILE = DATA_DIR / "train_seq2seq.jsonl"
OUTPUT_FILE = DATA_DIR / "hard_examples_seq2seq.jsonl"
MAX_LENGTH = 128
DUPLICATE_COUNT = 3


def _get_best_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def mine_hard_examples(
    model_dir: Path = MODEL_DIR,
    train_file: Path = TRAIN_FILE,
    output_file: Path = OUTPUT_FILE,
    max_samples: int = 0,
    batch_size: int = 64,
    duplicate_count: int = DUPLICATE_COUNT,
    verbose: bool = False,
) -> dict[str, Any]:
    """Find samples the model gets wrong and write an oversampled JSONL.

    Args:
        model_dir: Path to trained model directory
        train_file: Path to training data JSONL
        output_file: Path to write hard examples JSONL
        max_samples: Max training samples to evaluate (0 = all)
        batch_size: Inference batch size
        duplicate_count: How many times to duplicate hard examples
        verbose: Log individual mismatches

    Returns:
        Stats dict with counts and breakdowns
    """
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    logger.info(f"Loading model from {model_dir}...")
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSeq2SeqLM.from_pretrained(str(model_dir))
    model.eval()

    device = _get_best_device()
    model = model.to(device)
    logger.info(f"Using device: {device}")

    # Load training data
    logger.info(f"Loading training data from {train_file}...")
    samples: list[dict[str, Any]] = []
    with open(train_file) as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))

    if max_samples > 0 and len(samples) > max_samples:
        import random
        random.seed(42)
        random.shuffle(samples)
        samples = samples[:max_samples]

    logger.info(f"Evaluating {len(samples)} training samples...")

    # Strip legacy prefix
    for s in samples:
        if s["input_text"].startswith("correct: "):
            s["input_text"] = s["input_text"][len("correct: "):]

    # Run batched inference
    hard_examples: list[dict[str, Any]] = []
    error_type_counts: Counter = Counter()
    source_counts: Counter = Counter()
    total_correct = 0

    for i in range(0, len(samples), batch_size):
        batch = samples[i : i + batch_size]
        batch_texts = [s["input_text"] for s in batch]

        inputs = tokenizer(
            batch_texts,
            return_tensors="pt",
            truncation=True,
            max_length=MAX_LENGTH,
            padding=True,
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(**inputs, max_length=MAX_LENGTH, num_beams=1)

        predictions = tokenizer.batch_decode(outputs, skip_special_tokens=True)

        for j, (sample, pred) in enumerate(zip(batch, predictions)):
            target = sample["target_text"]
            if pred.strip() != target.strip():
                hard_examples.append(sample)
                error_type_counts[sample.get("error_type", "unknown")] += 1
                source_counts[sample.get("source", "unknown")] += 1
                if verbose and len(hard_examples) <= 20:
                    logger.info(
                        f"  WRONG: '{sample['input_text'][:60]}' "
                        f"-> pred='{pred[:60]}' target='{target[:60]}'"
                    )
            else:
                total_correct += 1

        if (i // batch_size) % 10 == 0:
            logger.info(
                f"  Progress: {min(i + batch_size, len(samples))}/{len(samples)} "
                f"({len(hard_examples)} hard so far)"
            )

    total = len(samples)
    wrong = len(hard_examples)
    logger.info(f"\nResults: {total_correct}/{total} correct, {wrong}/{total} wrong "
                f"({wrong / total * 100:.1f}% error rate)")

    # Write oversampled hard examples
    oversampled: list[dict[str, Any]] = []
    for sample in hard_examples:
        for _ in range(duplicate_count):
            oversampled.append(sample)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        for sample in oversampled:
            f.write(json.dumps(sample) + "\n")

    logger.info(f"Wrote {len(oversampled)} oversampled hard examples "
                f"({wrong} unique x {duplicate_count}) to {output_file}")

    # Log breakdowns
    if error_type_counts:
        logger.info("\nHard examples by error type:")
        for etype, count in error_type_counts.most_common(15):
            logger.info(f"  {etype}: {count}")

    if source_counts:
        logger.info("\nHard examples by source:")
        for source, count in source_counts.most_common(10):
            logger.info(f"  {source}: {count}")

    stats = {
        "total_evaluated": total,
        "total_correct": total_correct,
        "total_wrong": wrong,
        "error_rate": wrong / total if total > 0 else 0.0,
        "oversampled_count": len(oversampled),
        "duplicate_count": duplicate_count,
        "by_error_type": dict(error_type_counts),
        "by_source": dict(source_counts),
        "output_file": str(output_file),
    }

    # Save stats alongside output
    stats_file = output_file.with_suffix(".stats.json")
    with open(stats_file, "w") as f:
        json.dump(stats, f, indent=2)
    logger.info(f"Stats saved to {stats_file}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Mine hard examples from training data for oversampled retraining"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help=f"Path to trained model directory (default: {MODEL_DIR})",
    )
    parser.add_argument(
        "--train-file",
        type=str,
        default=None,
        help=f"Path to training data JSONL (default: {TRAIN_FILE})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help=f"Output file for hard examples (default: {OUTPUT_FILE})",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=0,
        help="Max training samples to evaluate, 0 = all (default: 0)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Inference batch size (default: 64)",
    )
    parser.add_argument(
        "--duplicates",
        type=int,
        default=DUPLICATE_COUNT,
        help=f"Times to duplicate hard examples (default: {DUPLICATE_COUNT})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Log individual mismatches",
    )
    args = parser.parse_args()

    model_dir = Path(args.model) if args.model else MODEL_DIR
    train_file = Path(args.train_file) if args.train_file else TRAIN_FILE
    output_file = Path(args.output) if args.output else OUTPUT_FILE

    if not model_dir.exists():
        logger.error(f"Model not found at {model_dir}")
        logger.info("Train the model first:")
        logger.info("  python ml/quick_correction/train_pipeline.py --train --model-type seq2seq")
        return

    if not train_file.exists():
        logger.error(f"Training data not found at {train_file}")
        return

    mine_hard_examples(
        model_dir=model_dir,
        train_file=train_file,
        output_file=output_file,
        max_samples=args.max_samples,
        batch_size=args.batch_size,
        duplicate_count=args.duplicates,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
