"""Evaluate trained Quick Correction Model on held-out test data.

Reports:
- Overall accuracy, precision, recall, F1
- Per-source breakdown (Birkbeck vs Wikipedia vs GitHub vs Aspell vs synthetic)
- Per-error-type breakdown (reversal/transposition/phonetic/omission/spelling)
- CPU latency benchmark (avg/p95 over 100 samples)
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent / "models" / "quick_correction_base_v1"
TEST_FILE = Path(__file__).parent / "data" / "test.jsonl"
MAX_SEQ_LENGTH = 128


def load_test_data(test_file: Path) -> list[dict[str, Any]]:
    """Load test data from JSONL file.

    Args:
        test_file: Path to test data JSONL

    Returns:
        List of test samples
    """
    samples = []
    with open(test_file) as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    logger.info(f"Loaded {len(samples)} test samples")
    return samples


def predict_sample(
    text: str,
    tokenizer: Any,
    model: Any,
) -> list[int]:
    """Run inference on a single sample and return word-level predictions.

    Args:
        text: Input text
        tokenizer: Tokenizer instance
        model: Model instance

    Returns:
        Word-level predicted labels
    """
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=MAX_SEQ_LENGTH,
    )

    with torch.no_grad():
        outputs = model(**inputs)

    predictions = torch.argmax(outputs.logits, dim=2)[0].cpu().numpy()
    word_ids = inputs.word_ids(batch_index=0)

    # Convert token-level predictions back to word-level
    words = text.split()
    word_preds = [0] * len(words)
    seen_word_ids = set()

    for token_idx, word_id in enumerate(word_ids):
        if word_id is not None and word_id not in seen_word_ids:
            if word_id < len(word_preds):
                word_preds[word_id] = int(predictions[token_idx])
            seen_word_ids.add(word_id)

    return word_preds


def evaluate_model(
    model_dir: Path | None = None,
    test_file: Path | None = None,
    output_file: Path | None = None,
    latency_samples: int = 100,
) -> dict[str, Any]:
    """Evaluate the trained model on test data.

    Args:
        model_dir: Path to trained model directory
        test_file: Path to test data JSONL
        output_file: Optional path to save JSON report
        latency_samples: Number of samples for latency benchmark

    Returns:
        Evaluation results dictionary
    """
    if model_dir is None:
        model_dir = MODEL_DIR
    if test_file is None:
        test_file = TEST_FILE

    # Load model
    logger.info(f"Loading model from {model_dir}...")
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForTokenClassification.from_pretrained(str(model_dir))
    model.eval()

    # Load test data
    samples = load_test_data(test_file)
    if not samples:
        logger.error("No test samples found")
        return {}

    # Evaluate each sample
    all_true = []
    all_pred = []
    per_source: dict[str, dict[str, list]] = {}
    per_error_type: dict[str, dict[str, list]] = {}

    for sample in samples:
        text = sample["text"]
        true_labels = sample["labels"]
        source = sample.get("source", "unknown")
        error_type = sample.get("error_type", "unknown")

        pred_labels = predict_sample(text, tokenizer, model)

        # Align lengths (truncate to shorter)
        min_len = min(len(true_labels), len(pred_labels))
        true_labels = true_labels[:min_len]
        pred_labels = pred_labels[:min_len]

        all_true.extend(true_labels)
        all_pred.extend(pred_labels)

        # Per-source tracking
        if source not in per_source:
            per_source[source] = {"true": [], "pred": []}
        per_source[source]["true"].extend(true_labels)
        per_source[source]["pred"].extend(pred_labels)

        # Per-error-type tracking
        if error_type not in per_error_type:
            per_error_type[error_type] = {"true": [], "pred": []}
        per_error_type[error_type]["true"].extend(true_labels)
        per_error_type[error_type]["pred"].extend(pred_labels)

    # Overall metrics
    all_true = np.array(all_true)
    all_pred = np.array(all_pred)

    results: dict[str, Any] = {
        "overall": _compute_metrics(all_true, all_pred),
        "per_source": {},
        "per_error_type": {},
        "latency": {},
    }

    # Per-source breakdown
    logger.info("\n--- Overall Metrics ---")
    _print_metrics(results["overall"])

    logger.info("\n--- Per-Source Breakdown ---")
    for source, data in sorted(per_source.items()):
        true = np.array(data["true"])
        pred = np.array(data["pred"])
        metrics = _compute_metrics(true, pred)
        results["per_source"][source] = metrics
        logger.info(f"\n  {source} ({len(true)} tokens):")
        _print_metrics(metrics, indent=4)

    logger.info("\n--- Per-Error-Type Breakdown ---")
    for error_type, data in sorted(per_error_type.items()):
        true = np.array(data["true"])
        pred = np.array(data["pred"])
        metrics = _compute_metrics(true, pred)
        results["per_error_type"][error_type] = metrics
        logger.info(f"\n  {error_type} ({len(true)} tokens):")
        _print_metrics(metrics, indent=4)

    # Latency benchmark
    logger.info(f"\n--- Latency Benchmark ({latency_samples} samples, CPU) ---")
    latency_results = _benchmark_latency(
        samples[:latency_samples], tokenizer, model
    )
    results["latency"] = latency_results
    logger.info(f"  Average: {latency_results['avg_ms']:.2f} ms")
    logger.info(f"  P50:     {latency_results['p50_ms']:.2f} ms")
    logger.info(f"  P95:     {latency_results['p95_ms']:.2f} ms")
    logger.info(f"  P99:     {latency_results['p99_ms']:.2f} ms")

    target_met = latency_results["p95_ms"] < 50
    logger.info(f"  Target (<50ms P95): {'MET' if target_met else 'NOT MET'}")

    # Save JSON report
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=float)
        logger.info(f"\nReport saved to {output_file}")

    return results


def _compute_metrics(true: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    """Compute classification metrics.

    Args:
        true: True labels
        pred: Predicted labels

    Returns:
        Dict of metrics
    """
    total = len(true)
    accuracy = float((true == pred).sum() / total) if total > 0 else 0.0

    # Error detection (any non-zero label)
    error_true = (true != 0).sum()
    error_pred = (pred != 0).sum()
    error_correct = ((true != 0) & (pred != 0)).sum()

    precision = float(error_correct / error_pred) if error_pred > 0 else 0.0
    recall = float(error_correct / error_true) if error_true > 0 else 0.0
    f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    # B-ERROR specific
    b_true = (true == 1).sum()
    b_pred = (pred == 1).sum()
    b_correct = ((true == 1) & (pred == 1)).sum()

    b_precision = float(b_correct / b_pred) if b_pred > 0 else 0.0
    b_recall = float(b_correct / b_true) if b_true > 0 else 0.0
    b_f1 = float(2 * b_precision * b_recall / (b_precision + b_recall)) if (b_precision + b_recall) > 0 else 0.0

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "b_error_precision": b_precision,
        "b_error_recall": b_recall,
        "b_error_f1": b_f1,
        "total_tokens": int(total),
        "error_tokens": int(error_true),
    }


def _print_metrics(metrics: dict[str, float], indent: int = 2) -> None:
    """Print metrics in a formatted way."""
    pad = " " * indent
    logger.info(f"{pad}Accuracy:          {metrics['accuracy']:.4f}")
    logger.info(f"{pad}Precision:         {metrics['precision']:.4f}")
    logger.info(f"{pad}Recall:            {metrics['recall']:.4f}")
    logger.info(f"{pad}F1:                {metrics['f1']:.4f}")
    logger.info(f"{pad}B-ERROR Precision: {metrics['b_error_precision']:.4f}")
    logger.info(f"{pad}B-ERROR Recall:    {metrics['b_error_recall']:.4f}")
    logger.info(f"{pad}B-ERROR F1:        {metrics['b_error_f1']:.4f}")


def _benchmark_latency(
    samples: list[dict[str, Any]],
    tokenizer: Any,
    model: Any,
) -> dict[str, float]:
    """Benchmark inference latency on CPU.

    Args:
        samples: Test samples to benchmark
        tokenizer: Tokenizer instance
        model: Model instance

    Returns:
        Latency statistics in milliseconds
    """
    # Warmup
    if samples:
        for _ in range(5):
            predict_sample(samples[0]["text"], tokenizer, model)

    times = []
    for sample in samples:
        start = time.perf_counter()
        predict_sample(sample["text"], tokenizer, model)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    times = np.array(times)
    return {
        "avg_ms": float(np.mean(times)),
        "p50_ms": float(np.percentile(times, 50)),
        "p95_ms": float(np.percentile(times, 95)),
        "p99_ms": float(np.percentile(times, 99)),
        "min_ms": float(np.min(times)),
        "max_ms": float(np.max(times)),
        "num_samples": len(times),
    }


def main():
    """Evaluate the model."""
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate Quick Correction Model")
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Path to trained model directory",
    )
    parser.add_argument(
        "--test",
        type=str,
        default=None,
        help="Path to test data JSONL",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save JSON report",
    )
    parser.add_argument(
        "--latency-samples",
        type=int,
        default=100,
        help="Number of samples for latency benchmark (default: 100)",
    )
    args = parser.parse_args()

    model_dir = Path(args.model) if args.model else MODEL_DIR
    test_file = Path(args.test) if args.test else TEST_FILE
    output_file = Path(args.output) if args.output else model_dir / "eval_report.json"

    if not model_dir.exists():
        logger.error(f"Model not found at {model_dir}")
        logger.info("Train the model first: python ml/quick_correction/train.py")
        return

    if not test_file.exists():
        logger.error(f"Test data not found at {test_file}")
        logger.info("Run the dataset pipeline first:")
        logger.info("  python ml/quick_correction/train_pipeline.py --download --process --combine")
        return

    evaluate_model(
        model_dir=model_dir,
        test_file=test_file,
        output_file=output_file,
        latency_samples=args.latency_samples,
    )


if __name__ == "__main__":
    main()
