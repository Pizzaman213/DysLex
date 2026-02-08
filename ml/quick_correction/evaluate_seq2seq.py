"""Evaluate trained Seq2Seq Quick Correction Model on held-out test data.

Reports:
- Exact match accuracy (% of sentences where output == target exactly)
- Word Error Rate (WER): edit distance at word level
- Character Error Rate (CER): edit distance at character level
- Per-error-type breakdown (reversal/transposition/phonetic/omission/spelling)
- Per-source breakdown (birkbeck, wikipedia, github_typo, aspell, synthetic)
- Latency benchmark (100 samples, greedy decode)
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent / "models" / "quick_correction_seq2seq_v1"
TEST_FILE = Path(__file__).parent / "data" / "test_seq2seq.jsonl"
MAX_LENGTH = 128


def load_test_data(test_file: Path) -> list[dict[str, Any]]:
    """Load seq2seq test data from JSONL file.

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
    logger.info(f"Loaded {len(samples)} seq2seq test samples")
    return samples


def generate_prediction(
    input_text: str,
    tokenizer: Any,
    model: Any,
    max_length: int = MAX_LENGTH,
) -> str:
    """Run seq2seq inference on a single input and return generated text.

    Args:
        input_text: Input text (with "correct: " prefix)
        tokenizer: Tokenizer instance
        model: Model instance
        max_length: Maximum generation length

    Returns:
        Generated corrected text
    """
    inputs = tokenizer(
        input_text,
        return_tensors="pt",
        truncation=True,
        max_length=max_length,
    )

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_length=max_length,
            num_beams=1,  # Greedy decode for speed
        )

    return tokenizer.decode(outputs[0], skip_special_tokens=True)


def _word_error_rate(hypothesis: list[str], reference: list[str]) -> float:
    """Compute word error rate."""
    if not reference:
        return 0.0 if not hypothesis else 1.0

    d = [[0] * (len(reference) + 1) for _ in range(len(hypothesis) + 1)]
    for i in range(len(hypothesis) + 1):
        d[i][0] = i
    for j in range(len(reference) + 1):
        d[0][j] = j

    for i in range(1, len(hypothesis) + 1):
        for j in range(1, len(reference) + 1):
            if hypothesis[i - 1] == reference[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = min(
                    d[i - 1][j] + 1,
                    d[i][j - 1] + 1,
                    d[i - 1][j - 1] + 1,
                )

    return d[len(hypothesis)][len(reference)] / len(reference)


def _char_error_rate(hypothesis: str, reference: str) -> float:
    """Compute character error rate."""
    if not reference:
        return 0.0 if not hypothesis else 1.0

    h = list(hypothesis)
    r = list(reference)

    d = [[0] * (len(r) + 1) for _ in range(len(h) + 1)]
    for i in range(len(h) + 1):
        d[i][0] = i
    for j in range(len(r) + 1):
        d[0][j] = j

    for i in range(1, len(h) + 1):
        for j in range(1, len(r) + 1):
            if h[i - 1] == r[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = min(
                    d[i - 1][j] + 1,
                    d[i][j - 1] + 1,
                    d[i - 1][j - 1] + 1,
                )

    return d[len(h)][len(r)] / len(r)


def _compute_metrics(
    predictions: list[str], targets: list[str]
) -> dict[str, float]:
    """Compute seq2seq evaluation metrics.

    Args:
        predictions: List of predicted texts
        targets: List of target texts

    Returns:
        Dict of metrics
    """
    if not predictions:
        return {
            "exact_match": 0.0,
            "wer": 1.0,
            "cer": 1.0,
            "num_samples": 0,
        }

    exact_matches = sum(
        1 for pred, target in zip(predictions, targets)
        if pred.strip() == target.strip()
    )
    exact_match = exact_matches / len(predictions)

    wer_scores = []
    cer_scores = []
    for pred, target in zip(predictions, targets):
        pred_words = pred.strip().split()
        target_words = target.strip().split()
        wer_scores.append(_word_error_rate(pred_words, target_words))
        cer_scores.append(_char_error_rate(pred.strip(), target.strip()))

    return {
        "exact_match": exact_match,
        "wer": float(np.mean(wer_scores)),
        "cer": float(np.mean(cer_scores)),
        "num_samples": len(predictions),
    }


def evaluate_seq2seq_model(
    model_dir: Path | None = None,
    test_file: Path | None = None,
    output_file: Path | None = None,
    latency_samples: int = 100,
) -> dict[str, Any]:
    """Evaluate the trained seq2seq model on test data.

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
    logger.info(f"Loading seq2seq model from {model_dir}...")
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSeq2SeqLM.from_pretrained(str(model_dir))
    model.eval()

    # Load test data
    samples = load_test_data(test_file)
    if not samples:
        logger.error("No test samples found")
        return {}

    # Generate predictions for all samples
    all_predictions = []
    all_targets = []
    per_source: dict[str, dict[str, list[str]]] = {}
    per_error_type: dict[str, dict[str, list[str]]] = {}

    logger.info(f"Running inference on {len(samples)} test samples...")
    for i, sample in enumerate(samples):
        input_text = sample["input_text"]
        target_text = sample["target_text"]
        source = sample.get("source", "unknown")
        error_type = sample.get("error_type", "unknown")

        prediction = generate_prediction(input_text, tokenizer, model)

        all_predictions.append(prediction)
        all_targets.append(target_text)

        # Per-source tracking
        if source not in per_source:
            per_source[source] = {"predictions": [], "targets": []}
        per_source[source]["predictions"].append(prediction)
        per_source[source]["targets"].append(target_text)

        # Per-error-type tracking
        if error_type not in per_error_type:
            per_error_type[error_type] = {"predictions": [], "targets": []}
        per_error_type[error_type]["predictions"].append(prediction)
        per_error_type[error_type]["targets"].append(target_text)

        if (i + 1) % 500 == 0:
            logger.info(f"  Processed {i + 1}/{len(samples)} samples...")

    # Overall metrics
    results: dict[str, Any] = {
        "overall": _compute_metrics(all_predictions, all_targets),
        "per_source": {},
        "per_error_type": {},
        "latency": {},
    }

    logger.info("\n--- Overall Metrics ---")
    _print_metrics(results["overall"])

    # Per-source breakdown
    logger.info("\n--- Per-Source Breakdown ---")
    for source, data in sorted(per_source.items()):
        metrics = _compute_metrics(data["predictions"], data["targets"])
        results["per_source"][source] = metrics
        logger.info(f"\n  {source} ({metrics['num_samples']} samples):")
        _print_metrics(metrics, indent=4)

    # Per-error-type breakdown
    logger.info("\n--- Per-Error-Type Breakdown ---")
    for error_type, data in sorted(per_error_type.items()):
        metrics = _compute_metrics(data["predictions"], data["targets"])
        results["per_error_type"][error_type] = metrics
        logger.info(f"\n  {error_type} ({metrics['num_samples']} samples):")
        _print_metrics(metrics, indent=4)

    # Latency benchmark
    logger.info(f"\n--- Latency Benchmark ({latency_samples} samples, CPU, greedy decode) ---")
    latency_results = _benchmark_latency(
        samples[:latency_samples], tokenizer, model
    )
    results["latency"] = latency_results
    logger.info(f"  Average: {latency_results['avg_ms']:.2f} ms")
    logger.info(f"  P50:     {latency_results['p50_ms']:.2f} ms")
    logger.info(f"  P95:     {latency_results['p95_ms']:.2f} ms")
    logger.info(f"  P99:     {latency_results['p99_ms']:.2f} ms")

    target_met = latency_results["p95_ms"] < 200
    logger.info(f"  Target (<200ms P95): {'MET' if target_met else 'NOT MET'}")

    # Save JSON report
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=float)
        logger.info(f"\nReport saved to {output_file}")

    return results


def _print_metrics(metrics: dict[str, float], indent: int = 2) -> None:
    """Print metrics in a formatted way."""
    pad = " " * indent
    logger.info(f"{pad}Exact Match: {metrics['exact_match']:.4f}")
    logger.info(f"{pad}WER:         {metrics['wer']:.4f}")
    logger.info(f"{pad}CER:         {metrics['cer']:.4f}")


def _benchmark_latency(
    samples: list[dict[str, Any]],
    tokenizer: Any,
    model: Any,
) -> dict[str, float]:
    """Benchmark inference latency on CPU with greedy decode.

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
            generate_prediction(samples[0]["input_text"], tokenizer, model)

    times = []
    for sample in samples:
        start = time.perf_counter()
        generate_prediction(sample["input_text"], tokenizer, model)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    times_arr = np.array(times)
    return {
        "avg_ms": float(np.mean(times_arr)),
        "p50_ms": float(np.percentile(times_arr, 50)),
        "p95_ms": float(np.percentile(times_arr, 95)),
        "p99_ms": float(np.percentile(times_arr, 99)),
        "min_ms": float(np.min(times_arr)),
        "max_ms": float(np.max(times_arr)),
        "num_samples": len(times_arr),
    }


def main():
    """Evaluate the seq2seq model."""
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate Seq2Seq Quick Correction Model")
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
        logger.info("Train the model first:")
        logger.info("  python ml/quick_correction/train_pipeline.py --all --model-type seq2seq")
        return

    if not test_file.exists():
        logger.error(f"Test data not found at {test_file}")
        logger.info("Run the dataset pipeline first:")
        logger.info("  python ml/quick_correction/train_pipeline.py --download --process --combine --model-type seq2seq")
        return

    evaluate_seq2seq_model(
        model_dir=model_dir,
        test_file=test_file,
        output_file=output_file,
        latency_samples=args.latency_samples,
    )


if __name__ == "__main__":
    main()
