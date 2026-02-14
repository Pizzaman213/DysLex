"""Evaluate trained Seq2Seq Quick Correction Model on held-out test data.

Reports:
- Exact match accuracy (% of sentences where output == target exactly)
- Word Error Rate (WER): edit distance at word level
- Character Error Rate (CER): edit distance at character level
- Per-error-type breakdown (reversal/transposition/phonetic/omission/spelling + grammar types)
- Per-source breakdown (birkbeck, wikipedia, github_typo, aspell, synthetic, grammar)
- No-change accuracy (correct text must not be modified)
- Spelling regression check (when grammar test data is available)
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


def _get_best_device() -> torch.device:
    """Detect the best available device: cuda > mps > cpu."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def generate_prediction(
    input_text: str,
    tokenizer: Any,
    model: Any,
    max_length: int = MAX_LENGTH,
    num_beams: int = 1,
    confidence_threshold: float = 0.0,
) -> str:
    """Run seq2seq inference on a single input and return generated text.

    Args:
        input_text: Input text
        tokenizer: Tokenizer instance
        model: Model instance
        max_length: Maximum generation length
        num_beams: Number of beams for beam search (1 = greedy)
        confidence_threshold: Min confidence to apply correction (0.0 = disabled)

    Returns:
        Generated corrected text (or original if below confidence threshold)
    """
    inputs = tokenizer(
        input_text,
        return_tensors="pt",
        truncation=True,
        max_length=max_length,
    )
    inputs = {k: v.to(model.device) for k, v in inputs.items()}

    use_confidence = confidence_threshold > 0.0

    with torch.no_grad():
        if use_confidence:
            outputs = model.generate(
                **inputs,
                max_length=max_length,
                num_beams=num_beams,
                output_scores=True,
                return_dict_in_generate=True,
            )
            sequences = outputs.sequences
            scores = outputs.scores  # tuple of (vocab_size,) tensors per step

            # Compute sequence-level confidence
            log_probs = []
            for step_idx, step_scores in enumerate(scores):
                token_id = sequences[0, step_idx + 1]  # +1 for decoder_start_token
                step_log_probs = torch.nn.functional.log_softmax(step_scores[0], dim=-1)
                log_probs.append(step_log_probs[token_id].item())

            if log_probs:
                avg_log_prob = sum(log_probs) / len(log_probs)
                confidence = np.exp(avg_log_prob)
            else:
                confidence = 0.0

            if confidence < confidence_threshold:
                return input_text  # Safe passthrough

            return tokenizer.decode(sequences[0], skip_special_tokens=True)
        else:
            outputs = model.generate(
                **inputs,
                max_length=max_length,
                num_beams=num_beams,
            )
            return tokenizer.decode(outputs[0], skip_special_tokens=True)


def generate_predictions_batched(
    input_texts: list[str],
    tokenizer: Any,
    model: Any,
    max_length: int = MAX_LENGTH,
    batch_size: int = 64,
    num_beams: int = 1,
    confidence_threshold: float = 0.0,
) -> list[str]:
    """Run batched seq2seq inference and return generated texts.

    Args:
        input_texts: List of input texts
        tokenizer: Tokenizer instance
        model: Model instance
        max_length: Maximum generation length
        batch_size: Number of samples per batch
        num_beams: Number of beams for beam search (1 = greedy)
        confidence_threshold: Min confidence to apply correction (0.0 = disabled)

    Returns:
        List of generated corrected texts
    """
    all_predictions: list[str] = []
    use_confidence = confidence_threshold > 0.0

    for i in range(0, len(input_texts), batch_size):
        batch_texts = input_texts[i : i + batch_size]
        inputs = tokenizer(
            batch_texts,
            return_tensors="pt",
            truncation=True,
            max_length=max_length,
            padding=True,
        )
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        with torch.no_grad():
            if use_confidence:
                outputs = model.generate(
                    **inputs,
                    max_length=max_length,
                    num_beams=num_beams,
                    output_scores=True,
                    return_dict_in_generate=True,
                )
                sequences = outputs.sequences
                scores = outputs.scores

                decoded = tokenizer.batch_decode(sequences, skip_special_tokens=True)

                # Compute per-sequence confidence
                for seq_idx in range(len(batch_texts)):
                    log_probs = []
                    for step_idx, step_scores in enumerate(scores):
                        if step_idx + 1 >= sequences.shape[1]:
                            break
                        token_id = sequences[seq_idx, step_idx + 1]
                        step_log_probs = torch.nn.functional.log_softmax(
                            step_scores[seq_idx], dim=-1
                        )
                        log_probs.append(step_log_probs[token_id].item())

                    if log_probs:
                        avg_log_prob = sum(log_probs) / len(log_probs)
                        confidence = np.exp(avg_log_prob)
                    else:
                        confidence = 0.0

                    if confidence < confidence_threshold:
                        all_predictions.append(batch_texts[seq_idx])
                    else:
                        all_predictions.append(decoded[seq_idx])
            else:
                outputs = model.generate(
                    **inputs,
                    max_length=max_length,
                    num_beams=num_beams,
                )
                decoded = tokenizer.batch_decode(outputs, skip_special_tokens=True)
                all_predictions.extend(decoded)

    return all_predictions


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


def _compute_no_change_accuracy(
    predictions: list[str], inputs: list[str]
) -> float:
    """Compute no-change accuracy: correct text must not be modified.

    Args:
        predictions: Model outputs
        inputs: Original input texts (without "correct: " prefix)

    Returns:
        Fraction of inputs that were correctly left unchanged
    """
    if not predictions:
        return 0.0

    correct = sum(
        1 for pred, inp in zip(predictions, inputs)
        if pred.strip() == inp.strip()
    )
    return correct / len(predictions)


def evaluate_seq2seq_model(
    model_dir: Path | None = None,
    test_file: Path | None = None,
    output_file: Path | None = None,
    latency_samples: int = 100,
    spelling_test_file: Path | None = None,
    grammar_test_file: Path | None = None,
    gate: bool = False,
    confidence_threshold: float = 0.0,
) -> dict[str, Any]:
    """Evaluate the trained seq2seq model on test data.

    Args:
        model_dir: Path to trained model directory
        test_file: Path to test data JSONL
        output_file: Optional path to save JSON report
        latency_samples: Number of samples for latency benchmark
        spelling_test_file: Optional spelling-only test file for regression check
        grammar_test_file: Optional grammar-only test file
        gate: If True, fail if quality thresholds are not met
        confidence_threshold: Min confidence to apply correction (0.0 = disabled)

    Returns:
        Evaluation results dictionary
    """
    if model_dir is None:
        model_dir = MODEL_DIR
    if test_file is None:
        test_file = TEST_FILE

    # Auto-detect grammar/spelling test files
    data_dir = test_file.parent
    if spelling_test_file is None:
        candidate = data_dir / "test_seq2seq_spelling.jsonl"
        if candidate.exists():
            spelling_test_file = candidate
    if grammar_test_file is None:
        candidate = data_dir / "test_seq2seq_grammar.jsonl"
        if candidate.exists():
            grammar_test_file = candidate

    # Load model
    logger.info(f"Loading seq2seq model from {model_dir}...")
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSeq2SeqLM.from_pretrained(str(model_dir))
    model.eval()

    # Move model to best available device for faster inference
    device = _get_best_device()
    model = model.to(device)
    logger.info(f"Using device: {device}")

    # Load test data
    samples = load_test_data(test_file)
    if not samples:
        logger.error("No test samples found")
        return {}

    # Generate predictions for all samples
    all_predictions = []
    all_targets = []
    no_change_predictions: list[str] = []
    no_change_inputs: list[str] = []
    per_source: dict[str, dict[str, list[str]]] = {}
    per_error_type: dict[str, dict[str, list[str]]] = {}

    # Grammar error types for separate reporting
    grammar_types = {
        "subject_verb", "article", "verb_tense", "function_word",
        "word_order", "run_on", "pronoun_case", "grammar",
    }

    # Strip legacy "correct: " prefix from input texts
    for s in samples:
        if s["input_text"].startswith("correct: "):
            s["input_text"] = s["input_text"][len("correct: "):]

    if confidence_threshold > 0.0:
        logger.info(f"Confidence threshold: {confidence_threshold}")

    logger.info(f"Running batched inference on {len(samples)} test samples...")
    all_input_texts = [s["input_text"] for s in samples]
    all_predictions = generate_predictions_batched(
        all_input_texts, tokenizer, model,
        confidence_threshold=confidence_threshold,
    )
    all_targets = [s["target_text"] for s in samples]

    # Build metadata tracking from predictions
    for i, sample in enumerate(samples):
        input_text = sample["input_text"]
        target_text = sample["target_text"]
        prediction = all_predictions[i]
        source = sample.get("source", "unknown")
        error_type = sample.get("error_type", "unknown")

        # Track no-change (passthrough) accuracy
        raw_input = input_text.strip()
        if raw_input == target_text.strip():
            no_change_predictions.append(prediction)
            no_change_inputs.append(raw_input)

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

    # Overall metrics
    results: dict[str, Any] = {
        "overall": _compute_metrics(all_predictions, all_targets),
        "per_source": {},
        "per_error_type": {},
        "latency": {},
        "no_change_accuracy": 0.0,
        "grammar_summary": {},
        "spelling_regression": {},
    }

    logger.info("\n--- Overall Metrics ---")
    _print_metrics(results["overall"])

    # No-change accuracy
    if no_change_predictions:
        no_change_acc = _compute_no_change_accuracy(no_change_predictions, no_change_inputs)
        results["no_change_accuracy"] = no_change_acc
        logger.info(f"\n--- No-Change Accuracy (correct text stays unchanged) ---")
        logger.info(f"  Accuracy: {no_change_acc:.4f} ({len(no_change_predictions)} samples)")
        target_met = no_change_acc >= 0.98
        logger.info(f"  Target (>=98%): {'MET' if target_met else 'NOT MET'}")

    # Per-source breakdown
    logger.info("\n--- Per-Source Breakdown ---")
    for source, data in sorted(per_source.items()):
        metrics = _compute_metrics(data["predictions"], data["targets"])
        results["per_source"][source] = metrics
        logger.info(f"\n  {source} ({metrics['num_samples']} samples):")
        _print_metrics(metrics, indent=4)

    # Per-error-type breakdown
    logger.info("\n--- Per-Error-Type Breakdown ---")
    grammar_preds: list[str] = []
    grammar_targets: list[str] = []
    spelling_preds: list[str] = []
    spelling_targets: list[str] = []

    for error_type, data in sorted(per_error_type.items()):
        metrics = _compute_metrics(data["predictions"], data["targets"])
        results["per_error_type"][error_type] = metrics
        logger.info(f"\n  {error_type} ({metrics['num_samples']} samples):")
        _print_metrics(metrics, indent=4)

        # Aggregate into grammar vs spelling
        if error_type in grammar_types:
            grammar_preds.extend(data["predictions"])
            grammar_targets.extend(data["targets"])
        elif error_type not in ("none", "unknown"):
            spelling_preds.extend(data["predictions"])
            spelling_targets.extend(data["targets"])

    # Grammar summary
    if grammar_preds:
        grammar_metrics = _compute_metrics(grammar_preds, grammar_targets)
        results["grammar_summary"] = grammar_metrics
        logger.info(f"\n--- Grammar Summary ({grammar_metrics['num_samples']} samples) ---")
        _print_metrics(grammar_metrics)
        target_met = grammar_metrics["exact_match"] >= 0.85
        logger.info(f"  Target (>=85% exact match): {'MET' if target_met else 'NOT MET'}")

    # Spelling summary (for regression tracking)
    if spelling_preds:
        spelling_metrics = _compute_metrics(spelling_preds, spelling_targets)
        logger.info(f"\n--- Spelling Summary ({spelling_metrics['num_samples']} samples) ---")
        _print_metrics(spelling_metrics)

    # Spelling regression check on dedicated spelling-only test file
    if spelling_test_file and spelling_test_file.exists():
        logger.info(f"\n--- Spelling Regression Check ({spelling_test_file.name}) ---")
        spelling_samples = load_test_data(spelling_test_file)
        for s in spelling_samples:
            if s["input_text"].startswith("correct: "):
                s["input_text"] = s["input_text"][len("correct: "):]
        sp_input_texts = [s["input_text"] for s in spelling_samples]
        sp_preds = generate_predictions_batched(
            sp_input_texts, tokenizer, model,
            confidence_threshold=confidence_threshold,
        )
        sp_tgts = [s["target_text"] for s in spelling_samples]
        sp_metrics = _compute_metrics(sp_preds, sp_tgts)
        results["spelling_regression"] = sp_metrics
        _print_metrics(sp_metrics)
        # Spelling must stay >= 95%
        target_met = sp_metrics["exact_match"] >= 0.95
        logger.info(f"  Target (>=95% exact match): {'MET' if target_met else 'NOT MET'}")

    # Grammar-only test file evaluation
    if grammar_test_file and grammar_test_file.exists():
        logger.info(f"\n--- Grammar-Only Evaluation ({grammar_test_file.name}) ---")
        grammar_samples = load_test_data(grammar_test_file)
        for s in grammar_samples:
            if s["input_text"].startswith("correct: "):
                s["input_text"] = s["input_text"][len("correct: "):]
        gr_input_texts = [s["input_text"] for s in grammar_samples]
        gr_preds = generate_predictions_batched(
            gr_input_texts, tokenizer, model,
            confidence_threshold=confidence_threshold,
        )
        gr_tgts = [s["target_text"] for s in grammar_samples]
        gr_per_type: dict[str, dict[str, list[str]]] = {}
        for i, sample in enumerate(grammar_samples):
            etype = sample.get("error_type", "grammar")
            if etype not in gr_per_type:
                gr_per_type[etype] = {"predictions": [], "targets": []}
            gr_per_type[etype]["predictions"].append(gr_preds[i])
            gr_per_type[etype]["targets"].append(sample["target_text"])

        gr_metrics = _compute_metrics(gr_preds, gr_tgts)
        results["grammar_only"] = gr_metrics
        _print_metrics(gr_metrics)
        target_met = gr_metrics["exact_match"] >= 0.85
        logger.info(f"  Target (>=85% exact match): {'MET' if target_met else 'NOT MET'}")

        # Per-grammar-type breakdown
        results["grammar_per_type"] = {}
        for etype, data in sorted(gr_per_type.items()):
            metrics = _compute_metrics(data["predictions"], data["targets"])
            results["grammar_per_type"][etype] = metrics
            logger.info(f"    {etype} ({metrics['num_samples']}): EM={metrics['exact_match']:.4f}")

    # Latency benchmark — must run on CPU for deployment-realistic numbers
    model = model.to(torch.device("cpu"))
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

    # Move back to best device for remaining evaluations
    model = model.to(device)

    # Evaluate additional stratified test sets if available
    stratified_types = ["function_word", "verb_tense", "mixed", "hard"]
    results["stratified"] = {}
    for stype in stratified_types:
        sfile = data_dir / f"test_seq2seq_{stype}.jsonl"
        if sfile.exists():
            logger.info(f"\n--- Stratified: {stype} ({sfile.name}) ---")
            s_samples = load_test_data(sfile)
            for s in s_samples:
                if s["input_text"].startswith("correct: "):
                    s["input_text"] = s["input_text"][len("correct: "):]
            s_input_texts = [s["input_text"] for s in s_samples]
            s_preds = generate_predictions_batched(
                s_input_texts, tokenizer, model,
                confidence_threshold=confidence_threshold,
            )
            s_tgts = [s["target_text"] for s in s_samples]
            s_metrics = _compute_metrics(s_preds, s_tgts)
            results["stratified"][stype] = s_metrics
            _print_metrics(s_metrics)

    # Regression gate check
    results["gate_passed"] = True
    if gate:
        logger.info("\n--- REGRESSION GATE CHECK ---")
        gate_failures = []

        # Spelling must stay >= 95%
        sp_em = results.get("spelling_regression", {}).get("exact_match", 0.0)
        if sp_em > 0 and sp_em < 0.95:
            gate_failures.append(f"Spelling regression: {sp_em:.4f} < 0.95")

        # Grammar must be >= 85%
        gr_em = results.get("grammar_only", {}).get("exact_match", 0.0)
        if gr_em > 0 and gr_em < 0.85:
            gate_failures.append(f"Grammar accuracy: {gr_em:.4f} < 0.85")

        # Latency P95 must be < 200ms
        p95 = results.get("latency", {}).get("p95_ms", 0.0)
        if p95 > 200:
            gate_failures.append(f"Latency P95: {p95:.2f}ms > 200ms")

        # Overall exact match should not drop below 85%
        overall_em = results.get("overall", {}).get("exact_match", 0.0)
        if overall_em < 0.85:
            gate_failures.append(f"Overall exact match: {overall_em:.4f} < 0.85")

        if gate_failures:
            results["gate_passed"] = False
            results["gate_failures"] = gate_failures
            logger.error("GATE FAILED:")
            for failure in gate_failures:
                logger.error(f"  - {failure}")
        else:
            logger.info("GATE PASSED: All quality thresholds met.")

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
    parser.add_argument(
        "--spelling-test",
        type=str,
        default=None,
        help="Path to spelling-only test JSONL (for regression check)",
    )
    parser.add_argument(
        "--grammar-test",
        type=str,
        default=None,
        help="Path to grammar-only test JSONL",
    )
    parser.add_argument(
        "--gate",
        action="store_true",
        help="Enable regression gate: fail if spelling < 95%%, grammar < 85%%, or P95 > 200ms",
    )
    parser.add_argument(
        "--beam",
        type=int,
        default=1,
        help="Number of beams for beam search (default: 1 = greedy)",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.0,
        help="Min confidence to apply correction; below threshold returns input unchanged "
             "(default: 0.0 = disabled, suggested: 0.7-0.85)",
    )
    args = parser.parse_args()

    model_dir = Path(args.model) if args.model else MODEL_DIR
    test_file = Path(args.test) if args.test else TEST_FILE
    output_file = Path(args.output) if args.output else model_dir / "eval_report.json"
    spelling_test = Path(args.spelling_test) if args.spelling_test else None
    grammar_test = Path(args.grammar_test) if args.grammar_test else None

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

    results = evaluate_seq2seq_model(
        model_dir=model_dir,
        test_file=test_file,
        output_file=output_file,
        latency_samples=args.latency_samples,
        spelling_test_file=spelling_test,
        grammar_test_file=grammar_test,
        gate=args.gate,
        confidence_threshold=args.confidence_threshold,
    )

    # Exit with non-zero code if gate fails
    if args.gate and not results.get("gate_passed", True):
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
