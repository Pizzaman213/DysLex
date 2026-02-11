"""Comprehensive benchmark suite for the Quick Correction Model.

Benchmarks the model across multiple dimensions:
- Latency: PyTorch and ONNX inference timing with percentile statistics
- Throughput: Sentences per second at varying input lengths
- Accuracy: Per-error-type accuracy, false positive/negative rates, confusion matrix
- Memory: Model size on disk, peak memory during inference

Usage:
    python ml/quick_correction/benchmark.py
    python ml/quick_correction/benchmark.py --onnx-only --runs 200
    python ml/quick_correction/benchmark.py --model-dir path/to/model --test-data path/to/test.jsonl
"""

import argparse
import json
import logging
import platform
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Default paths (relative to project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MODEL_DIR = PROJECT_ROOT / "ml" / "quick_correction" / "models" / "quick_correction_base_v1"
DEFAULT_ONNX_DIR = PROJECT_ROOT / "ml" / "models" / "quick_correction_base_v1"
DEFAULT_TEST_DATA = PROJECT_ROOT / "ml" / "quick_correction" / "data" / "test.jsonl"

MAX_SEQ_LENGTH = 128

LABEL_NAMES = {0: "O", 1: "B-ERROR", 2: "I-ERROR"}
NUM_LABELS = 3

# Synthetic sentences at different lengths for throughput benchmarks
THROUGHPUT_SENTENCES = {
    "short_5w": "The cat sat on mat.",
    "medium_20w": (
        "The quick brown fox jumped over the lazy dog while the sun was "
        "setting behind the distant mountain range slowly."
    ),
    "long_50w": (
        "The experienced software engineer carefully reviewed the complex "
        "codebase looking for potential performance bottlenecks and security "
        "vulnerabilities that could affect the production deployment of the "
        "new feature release scheduled for next quarter while also considering "
        "backward compatibility with existing client integrations and third "
        "party service dependencies throughout the entire system."
    ),
    "very_long_100w": (
        "The comprehensive research study conducted by the international team "
        "of scientists from multiple prestigious universities across several "
        "continents examined the long term effects of environmental pollution "
        "on marine ecosystems and biodiversity in tropical coastal regions "
        "where coral reef degradation has accelerated significantly over the "
        "past two decades due to rising ocean temperatures and increased "
        "acidification levels caused by excessive carbon dioxide emissions "
        "from industrial activities and transportation networks that continue "
        "to expand rapidly in developing nations despite growing awareness of "
        "climate change impacts on fragile natural habitats and endangered "
        "species populations that depend on healthy ocean environments for "
        "survival and reproduction throughout their complex life cycles and "
        "migration patterns across vast oceanic distances each year."
    ),
}


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def get_system_info() -> dict[str, str]:
    """Collect system information for the benchmark report."""
    info = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "machine": platform.machine(),
        "os": platform.system(),
        "os_version": platform.version(),
    }

    try:
        import torch
        info["pytorch_version"] = torch.__version__
        info["cuda_available"] = str(torch.cuda.is_available())
    except ImportError:
        info["pytorch_version"] = "not installed"

    try:
        import onnxruntime as ort
        info["onnxruntime_version"] = ort.__version__
    except ImportError:
        info["onnxruntime_version"] = "not installed"

    try:
        import transformers
        info["transformers_version"] = transformers.__version__
    except ImportError:
        info["transformers_version"] = "not installed"

    return info


def compute_percentiles(times: list[float]) -> dict[str, float]:
    """Compute latency statistics from a list of timings (in ms)."""
    arr = np.array(times)
    return {
        "avg_ms": float(np.mean(arr)),
        "p50_ms": float(np.percentile(arr, 50)),
        "p95_ms": float(np.percentile(arr, 95)),
        "p99_ms": float(np.percentile(arr, 99)),
        "min_ms": float(np.min(arr)),
        "max_ms": float(np.max(arr)),
        "std_ms": float(np.std(arr)),
        "num_runs": len(times),
    }


def format_table(headers: list[str], rows: list[list[str]], title: str = "") -> str:
    """Format data as an aligned text table."""
    all_rows = [headers] + rows
    col_widths = [max(len(str(cell)) for cell in col) for col in zip(*all_rows)]

    separator = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    header_line = "| " + " | ".join(str(h).ljust(w) for h, w in zip(headers, col_widths)) + " |"

    lines = []
    if title:
        lines.append("")
        lines.append(f"  {title}")
        lines.append(f"  {'=' * len(title)}")
    lines.append(separator)
    lines.append(header_line)
    lines.append(separator)
    for row in rows:
        line = "| " + " | ".join(str(c).ljust(w) for c, w in zip(row, col_widths)) + " |"
        lines.append(line)
    lines.append(separator)
    return "\n".join(lines)


def load_test_data(test_file: Path) -> list[dict[str, Any]]:
    """Load test data from JSONL file."""
    samples: list[dict[str, Any]] = []
    with open(test_file) as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


# ---------------------------------------------------------------------------
# PyTorch inference helpers
# ---------------------------------------------------------------------------

def load_pytorch_model(model_dir: Path) -> tuple[Any, Any]:
    """Load PyTorch model and tokenizer. Returns (tokenizer, model) or raises ImportError."""
    from transformers import AutoModelForTokenClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForTokenClassification.from_pretrained(str(model_dir))
    model.eval()
    return tokenizer, model


def pytorch_tokenize(text: str, tokenizer: Any) -> Any:
    """Tokenize text for PyTorch model."""
    import torch
    return tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=MAX_SEQ_LENGTH,
    )


def pytorch_inference(inputs: dict[str, Any], model: Any) -> np.ndarray:
    """Run PyTorch inference and return predicted label indices per token."""
    import torch
    with torch.no_grad():
        outputs = model(**inputs)
    return torch.argmax(outputs.logits, dim=2)[0].cpu().numpy()


def pytorch_predict_sample(text: str, tokenizer: Any, model: Any) -> list[int]:
    """Run full PyTorch inference pipeline on a single sample, returning word-level preds."""
    inputs = pytorch_tokenize(text, tokenizer)

    import torch
    with torch.no_grad():
        outputs = model(**inputs)

    predictions = torch.argmax(outputs.logits, dim=2)[0].cpu().numpy()
    word_ids = inputs.word_ids(batch_index=0)

    words = text.split()
    word_preds = [0] * len(words)
    seen = set()
    for token_idx, word_id in enumerate(word_ids):
        if word_id is not None and word_id not in seen:
            if word_id < len(word_preds):
                word_preds[word_id] = int(predictions[token_idx])
            seen.add(word_id)
    return word_preds


# ---------------------------------------------------------------------------
# ONNX inference helpers
# ---------------------------------------------------------------------------

def load_onnx_model(onnx_dir: Path) -> tuple[Any, Any]:
    """Load ONNX session and tokenizer. Returns (tokenizer, session)."""
    import onnxruntime as ort
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(onnx_dir))
    onnx_file = onnx_dir / "model.onnx"
    if not onnx_file.exists():
        raise FileNotFoundError(f"ONNX model not found at {onnx_file}")

    session = ort.InferenceSession(
        str(onnx_file),
        providers=["CPUExecutionProvider"],
    )
    return tokenizer, session


def onnx_tokenize(text: str, tokenizer: Any) -> dict[str, np.ndarray]:
    """Tokenize text for ONNX model, returning numpy arrays."""
    inputs = tokenizer(
        text,
        return_tensors="np",
        truncation=True,
        padding=True,
        max_length=MAX_SEQ_LENGTH,
    )
    return {
        "input_ids": inputs["input_ids"].astype(np.int64),
        "attention_mask": inputs["attention_mask"].astype(np.int64),
    }


def onnx_inference(inputs: dict[str, np.ndarray], session: Any) -> np.ndarray:
    """Run ONNX inference and return raw logits."""
    outputs = session.run(None, inputs)
    return outputs[0]


def onnx_predict_sample(text: str, tokenizer: Any, session: Any) -> list[int]:
    """Run full ONNX inference pipeline on a single sample, returning word-level preds."""
    tok_inputs = tokenizer(
        text,
        return_tensors="np",
        truncation=True,
        padding=True,
        max_length=MAX_SEQ_LENGTH,
    )

    feed = {
        "input_ids": tok_inputs["input_ids"].astype(np.int64),
        "attention_mask": tok_inputs["attention_mask"].astype(np.int64),
    }
    outputs = session.run(None, feed)
    predictions = np.argmax(outputs[0], axis=-1)[0]
    word_ids = tok_inputs.word_ids(batch_index=0)

    words = text.split()
    word_preds = [0] * len(words)
    seen = set()
    for token_idx, word_id in enumerate(word_ids):
        if word_id is not None and word_id not in seen:
            if word_id < len(word_preds):
                word_preds[word_id] = int(predictions[token_idx])
            seen.add(word_id)
    return word_preds


# ---------------------------------------------------------------------------
# Benchmark: Latency
# ---------------------------------------------------------------------------

def benchmark_latency(
    tokenizer: Any,
    model_or_session: Any,
    backend: str,
    num_runs: int = 100,
    warmup_runs: int = 10,
) -> dict[str, Any]:
    """Benchmark inference latency for a given backend (pytorch or onnx).

    Measures total inference, tokenization-only, and model-only latency
    separately. Warmup runs are excluded from statistics.

    Args:
        tokenizer: Tokenizer instance
        model_or_session: PyTorch model or ONNX session
        backend: "pytorch" or "onnx"
        num_runs: Number of timed runs
        warmup_runs: Number of warmup runs to exclude

    Returns:
        Dictionary of latency statistics
    """
    test_text = "He cleaned the intire house before the guests arrived fro dinner."

    # Warmup
    for _ in range(warmup_runs):
        if backend == "pytorch":
            inputs = pytorch_tokenize(test_text, tokenizer)
            pytorch_inference(inputs, model_or_session)
        else:
            inputs = onnx_tokenize(test_text, tokenizer)
            onnx_inference(inputs, model_or_session)

    # Timed runs: total (tokenize + inference)
    total_times: list[float] = []
    tokenize_times: list[float] = []
    inference_times: list[float] = []

    for _ in range(num_runs):
        # Tokenization timing
        t0 = time.perf_counter()
        if backend == "pytorch":
            inputs = pytorch_tokenize(test_text, tokenizer)
        else:
            inputs = onnx_tokenize(test_text, tokenizer)
        t1 = time.perf_counter()
        tokenize_times.append((t1 - t0) * 1000)

        # Inference timing
        t2 = time.perf_counter()
        if backend == "pytorch":
            pytorch_inference(inputs, model_or_session)
        else:
            onnx_inference(inputs, model_or_session)
        t3 = time.perf_counter()
        inference_times.append((t3 - t2) * 1000)

        total_times.append((t3 - t0) * 1000)

    return {
        "total": compute_percentiles(total_times),
        "tokenization": compute_percentiles(tokenize_times),
        "inference_only": compute_percentiles(inference_times),
    }


def print_latency_results(results: dict[str, dict[str, Any]], backend: str) -> None:
    """Print latency benchmark results as a formatted table."""
    headers = ["Phase", "Avg (ms)", "P50 (ms)", "P95 (ms)", "P99 (ms)", "Min (ms)", "Max (ms)", "Std (ms)"]
    rows = []
    for phase in ["total", "tokenization", "inference_only"]:
        stats = results[phase]
        rows.append([
            phase.replace("_", " ").title(),
            f"{stats['avg_ms']:.3f}",
            f"{stats['p50_ms']:.3f}",
            f"{stats['p95_ms']:.3f}",
            f"{stats['p99_ms']:.3f}",
            f"{stats['min_ms']:.3f}",
            f"{stats['max_ms']:.3f}",
            f"{stats['std_ms']:.3f}",
        ])

    title = f"Latency Benchmark ({backend.upper()}, {results['total']['num_runs']} runs)"
    logger.info(format_table(headers, rows, title))

    target = 50.0
    p95 = results["total"]["p95_ms"]
    status = "PASS" if p95 < target else "FAIL"
    logger.info(f"  Target: P95 < {target:.0f}ms | Actual P95: {p95:.3f}ms | {status}")


# ---------------------------------------------------------------------------
# Benchmark: Throughput
# ---------------------------------------------------------------------------

def benchmark_throughput(
    tokenizer: Any,
    model_or_session: Any,
    backend: str,
    num_runs: int = 50,
    warmup_runs: int = 5,
) -> dict[str, Any]:
    """Benchmark throughput at various sentence lengths.

    Args:
        tokenizer: Tokenizer instance
        model_or_session: PyTorch model or ONNX session
        backend: "pytorch" or "onnx"
        num_runs: Number of runs per sentence length
        warmup_runs: Number of warmup runs

    Returns:
        Dictionary mapping sentence-length key to throughput stats
    """
    results: dict[str, Any] = {}

    for length_key, sentence in THROUGHPUT_SENTENCES.items():
        word_count = len(sentence.split())

        # Warmup
        for _ in range(warmup_runs):
            if backend == "pytorch":
                inputs = pytorch_tokenize(sentence, tokenizer)
                pytorch_inference(inputs, model_or_session)
            else:
                inputs = onnx_tokenize(sentence, tokenizer)
                onnx_inference(inputs, model_or_session)

        # Timed runs
        times: list[float] = []
        for _ in range(num_runs):
            t0 = time.perf_counter()
            if backend == "pytorch":
                inputs = pytorch_tokenize(sentence, tokenizer)
                pytorch_inference(inputs, model_or_session)
            else:
                inputs = onnx_tokenize(sentence, tokenizer)
                onnx_inference(inputs, model_or_session)
            elapsed = (time.perf_counter() - t0) * 1000
            times.append(elapsed)

        avg_ms = float(np.mean(times))
        sentences_per_sec = 1000.0 / avg_ms if avg_ms > 0 else 0.0

        results[length_key] = {
            "word_count": word_count,
            "avg_ms": avg_ms,
            "sentences_per_second": sentences_per_sec,
            "latency_stats": compute_percentiles(times),
        }

    return results


def print_throughput_results(results: dict[str, Any], backend: str) -> None:
    """Print throughput benchmark results."""
    headers = ["Length", "Words", "Avg (ms)", "Sent/s", "P95 (ms)"]
    rows = []
    for length_key in ["short_5w", "medium_20w", "long_50w", "very_long_100w"]:
        if length_key not in results:
            continue
        r = results[length_key]
        rows.append([
            length_key,
            str(r["word_count"]),
            f"{r['avg_ms']:.3f}",
            f"{r['sentences_per_second']:.1f}",
            f"{r['latency_stats']['p95_ms']:.3f}",
        ])

    title = f"Throughput Benchmark ({backend.upper()})"
    logger.info(format_table(headers, rows, title))


# ---------------------------------------------------------------------------
# Benchmark: Accuracy
# ---------------------------------------------------------------------------

def benchmark_accuracy(
    test_data: list[dict[str, Any]],
    tokenizer: Any,
    model_or_session: Any,
    backend: str,
) -> dict[str, Any]:
    """Benchmark accuracy across multiple dimensions.

    Computes:
    - Overall accuracy, precision, recall, F1
    - Per-error-type accuracy and false negative rate
    - False positive rate on clean text (error_type == "none")
    - Confusion matrix for O / B-ERROR / I-ERROR labels

    Args:
        test_data: List of test samples
        tokenizer: Tokenizer instance
        model_or_session: PyTorch model or ONNX session
        backend: "pytorch" or "onnx"

    Returns:
        Accuracy benchmark results dictionary
    """
    all_true: list[int] = []
    all_pred: list[int] = []
    per_error_type: dict[str, dict[str, list[int]]] = {}

    for sample in test_data:
        text = sample["text"]
        true_labels = sample["labels"]
        error_type = sample.get("error_type", "unknown")

        if backend == "pytorch":
            pred_labels = pytorch_predict_sample(text, tokenizer, model_or_session)
        else:
            pred_labels = onnx_predict_sample(text, tokenizer, model_or_session)

        # Align lengths
        min_len = min(len(true_labels), len(pred_labels))
        true_labels = true_labels[:min_len]
        pred_labels = pred_labels[:min_len]

        all_true.extend(true_labels)
        all_pred.extend(pred_labels)

        if error_type not in per_error_type:
            per_error_type[error_type] = {"true": [], "pred": []}
        per_error_type[error_type]["true"].extend(true_labels)
        per_error_type[error_type]["pred"].extend(pred_labels)

    true_arr = np.array(all_true)
    pred_arr = np.array(all_pred)

    # Overall metrics
    overall = _compute_classification_metrics(true_arr, pred_arr)

    # Confusion matrix (3x3: O, B-ERROR, I-ERROR)
    confusion = _compute_confusion_matrix(true_arr, pred_arr, NUM_LABELS)

    # Per-error-type metrics
    per_type_results: dict[str, Any] = {}
    for etype, data in sorted(per_error_type.items()):
        t = np.array(data["true"])
        p = np.array(data["pred"])
        metrics = _compute_classification_metrics(t, p)

        # False negative rate: errors missed (true error, predicted O)
        error_mask = t != 0
        if error_mask.sum() > 0:
            fn_rate = float(((t != 0) & (p == 0)).sum() / error_mask.sum())
        else:
            fn_rate = 0.0

        # False positive rate: clean tokens wrongly flagged
        clean_mask = t == 0
        if clean_mask.sum() > 0:
            fp_rate = float(((t == 0) & (p != 0)).sum() / clean_mask.sum())
        else:
            fp_rate = 0.0

        metrics["false_negative_rate"] = fn_rate
        metrics["false_positive_rate"] = fp_rate
        metrics["num_samples_tokens"] = int(len(t))
        per_type_results[etype] = metrics

    # Global false positive rate on clean text only
    clean_data = per_error_type.get("none", {"true": [], "pred": []})
    if clean_data["true"]:
        clean_true = np.array(clean_data["true"])
        clean_pred = np.array(clean_data["pred"])
        clean_total = len(clean_true)
        false_positives_on_clean = int((clean_pred != 0).sum())
        fp_rate_clean = float(false_positives_on_clean / clean_total) if clean_total > 0 else 0.0
    else:
        clean_total = 0
        false_positives_on_clean = 0
        fp_rate_clean = 0.0

    return {
        "overall": overall,
        "confusion_matrix": confusion,
        "per_error_type": per_type_results,
        "false_positive_analysis": {
            "clean_text_tokens": clean_total,
            "false_positives_on_clean": false_positives_on_clean,
            "fp_rate_on_clean_text": fp_rate_clean,
        },
    }


def _compute_classification_metrics(true: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    """Compute overall classification metrics."""
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


def _compute_confusion_matrix(true: np.ndarray, pred: np.ndarray, num_labels: int) -> dict[str, Any]:
    """Compute a confusion matrix and return as a structured dict."""
    matrix = np.zeros((num_labels, num_labels), dtype=int)
    for t, p in zip(true, pred):
        if 0 <= t < num_labels and 0 <= p < num_labels:
            matrix[t][p] += 1

    # Convert to serializable format
    result: dict[str, Any] = {
        "labels": [LABEL_NAMES[i] for i in range(num_labels)],
        "matrix": matrix.tolist(),
    }

    # Per-class stats
    per_class: dict[str, dict[str, float]] = {}
    for i in range(num_labels):
        label = LABEL_NAMES[i]
        tp = int(matrix[i][i])
        fp = int(matrix[:, i].sum() - tp)
        fn = int(matrix[i, :].sum() - tp)
        support = int(matrix[i, :].sum())

        class_precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        class_recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        class_f1 = (
            2 * class_precision * class_recall / (class_precision + class_recall)
            if (class_precision + class_recall) > 0 else 0.0
        )

        per_class[label] = {
            "precision": class_precision,
            "recall": class_recall,
            "f1": class_f1,
            "support": support,
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
        }

    result["per_class"] = per_class
    return result


def print_accuracy_results(results: dict[str, Any], backend: str) -> None:
    """Print accuracy benchmark results."""
    overall = results["overall"]

    # Overall metrics table
    headers = ["Metric", "Value"]
    rows = [
        ["Accuracy", f"{overall['accuracy']:.6f}"],
        ["Precision (error detect)", f"{overall['precision']:.6f}"],
        ["Recall (error detect)", f"{overall['recall']:.6f}"],
        ["F1 (error detect)", f"{overall['f1']:.6f}"],
        ["B-ERROR Precision", f"{overall['b_error_precision']:.6f}"],
        ["B-ERROR Recall", f"{overall['b_error_recall']:.6f}"],
        ["B-ERROR F1", f"{overall['b_error_f1']:.6f}"],
        ["Total tokens", str(overall["total_tokens"])],
        ["Error tokens", str(overall["error_tokens"])],
    ]
    logger.info(format_table(headers, rows, f"Accuracy Benchmark ({backend.upper()}) - Overall"))

    # Confusion matrix
    cm = results["confusion_matrix"]
    labels = cm["labels"]
    matrix = cm["matrix"]

    cm_headers = ["True \\ Pred"] + labels
    cm_rows = []
    for i, label in enumerate(labels):
        cm_rows.append([label] + [str(v) for v in matrix[i]])
    logger.info(format_table(cm_headers, cm_rows, "Confusion Matrix"))

    # Per-class metrics from confusion matrix
    per_class = cm["per_class"]
    pc_headers = ["Label", "Precision", "Recall", "F1", "Support", "TP", "FP", "FN"]
    pc_rows = []
    for label in labels:
        c = per_class[label]
        pc_rows.append([
            label,
            f"{c['precision']:.6f}",
            f"{c['recall']:.6f}",
            f"{c['f1']:.6f}",
            str(c["support"]),
            str(c["true_positive"]),
            str(c["false_positive"]),
            str(c["false_negative"]),
        ])
    logger.info(format_table(pc_headers, pc_rows, "Per-Label Metrics"))

    # Per error type
    pet = results["per_error_type"]
    pet_headers = ["Error Type", "Accuracy", "Precision", "Recall", "F1", "FP Rate", "FN Rate", "Tokens"]
    pet_rows = []
    for etype in sorted(pet.keys()):
        m = pet[etype]
        pet_rows.append([
            etype,
            f"{m['accuracy']:.6f}",
            f"{m['precision']:.6f}" if m["precision"] > 0 else "N/A",
            f"{m['recall']:.6f}" if m["recall"] > 0 else "N/A",
            f"{m['f1']:.6f}" if m["f1"] > 0 else "N/A",
            f"{m['false_positive_rate']:.6f}",
            f"{m['false_negative_rate']:.6f}",
            str(m["num_samples_tokens"]),
        ])
    logger.info(format_table(pet_headers, pet_rows, "Per Error Type Breakdown"))

    # False positive analysis on clean text
    fpa = results["false_positive_analysis"]
    logger.info("")
    logger.info("  False Positive Analysis (clean text, error_type='none')")
    logger.info(f"    Clean text tokens:         {fpa['clean_text_tokens']}")
    logger.info(f"    False positives on clean:   {fpa['false_positives_on_clean']}")
    logger.info(f"    FP rate on clean text:      {fpa['fp_rate_on_clean_text']:.6f}")


# ---------------------------------------------------------------------------
# Benchmark: Memory
# ---------------------------------------------------------------------------

def benchmark_memory(
    model_dir: Path,
    onnx_dir: Path,
    tokenizer: Any,
    model_or_session: Any,
    backend: str,
    num_runs: int = 20,
) -> dict[str, Any]:
    """Benchmark memory usage.

    Measures:
    - Model file sizes on disk
    - Peak memory during inference (tracemalloc)
    - Average memory per inference call

    Args:
        model_dir: Path to PyTorch model directory
        onnx_dir: Path to ONNX model directory
        tokenizer: Tokenizer instance
        model_or_session: PyTorch model or ONNX session
        backend: "pytorch" or "onnx"
        num_runs: Number of inference runs for memory profiling

    Returns:
        Memory benchmark results dictionary
    """
    test_text = "He cleaned the intire house before the guests arrived fro dinner."

    # File sizes
    file_sizes: dict[str, float] = {}
    for check_dir, label_prefix in [(model_dir, "pytorch"), (onnx_dir, "onnx")]:
        if check_dir.exists():
            total_bytes = 0
            for f in check_dir.rglob("*"):
                if f.is_file() and not f.name.startswith("."):
                    size = f.stat().st_size
                    total_bytes += size
                    ext = f.suffix.lower()
                    if ext in (".onnx", ".safetensors", ".bin", ".pt"):
                        file_sizes[f"{label_prefix}/{f.name}"] = size / (1024 * 1024)
            file_sizes[f"{label_prefix}/total_dir"] = total_bytes / (1024 * 1024)

    # Memory profiling with tracemalloc
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    per_call_peaks: list[float] = []
    for _ in range(num_runs):
        tracemalloc.reset_peak()
        if backend == "pytorch":
            inputs = pytorch_tokenize(test_text, tokenizer)
            pytorch_inference(inputs, model_or_session)
        else:
            inputs = onnx_tokenize(test_text, tokenizer)
            onnx_inference(inputs, model_or_session)
        _, peak = tracemalloc.get_traced_memory()
        per_call_peaks.append(peak / (1024 * 1024))  # Convert to MB

    current, peak_overall = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "file_sizes_mb": file_sizes,
        "peak_memory_mb": peak_overall / (1024 * 1024),
        "current_memory_mb": current / (1024 * 1024),
        "per_call_peak_avg_mb": float(np.mean(per_call_peaks)),
        "per_call_peak_max_mb": float(np.max(per_call_peaks)),
        "per_call_peak_min_mb": float(np.min(per_call_peaks)),
        "num_profiling_runs": num_runs,
    }


def print_memory_results(results: dict[str, Any]) -> None:
    """Print memory benchmark results."""
    # File sizes
    headers = ["File / Directory", "Size (MB)"]
    rows = []
    for name, size in sorted(results["file_sizes_mb"].items()):
        rows.append([name, f"{size:.2f}"])
    logger.info(format_table(headers, rows, "Model File Sizes"))

    # Memory usage
    headers2 = ["Metric", "Value"]
    rows2 = [
        ["Peak memory (traced)", f"{results['peak_memory_mb']:.2f} MB"],
        ["Current memory (traced)", f"{results['current_memory_mb']:.2f} MB"],
        ["Avg peak per inference call", f"{results['per_call_peak_avg_mb']:.4f} MB"],
        ["Max peak per inference call", f"{results['per_call_peak_max_mb']:.4f} MB"],
        ["Min peak per inference call", f"{results['per_call_peak_min_mb']:.4f} MB"],
        ["Profiling runs", str(results["num_profiling_runs"])],
    ]
    logger.info(format_table(headers2, rows2, "Memory Usage (tracemalloc)"))


# ---------------------------------------------------------------------------
# Main benchmark runner
# ---------------------------------------------------------------------------

def run_benchmarks(
    model_dir: Path,
    onnx_dir: Path,
    test_data_path: Path,
    onnx_only: bool = False,
    num_runs: int = 100,
) -> dict[str, Any]:
    """Run all benchmarks and return a combined report.

    Args:
        model_dir: Path to PyTorch model directory
        onnx_dir: Path to ONNX model directory
        test_data_path: Path to test data JSONL
        onnx_only: If True, skip PyTorch benchmarks
        num_runs: Number of timed runs for latency benchmarks

    Returns:
        Full benchmark report dictionary
    """
    report: dict[str, Any] = {
        "system_info": get_system_info(),
        "config": {
            "model_dir": str(model_dir),
            "onnx_dir": str(onnx_dir),
            "test_data": str(test_data_path),
            "onnx_only": onnx_only,
            "num_runs": num_runs,
            "max_seq_length": MAX_SEQ_LENGTH,
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

    logger.info("=" * 72)
    logger.info("  Quick Correction Model - Comprehensive Benchmark")
    logger.info("=" * 72)

    # Print system info
    sys_info = report["system_info"]
    logger.info("")
    logger.info("  System Information")
    logger.info("  ------------------")
    for key, value in sys_info.items():
        label = key.replace("_", " ").title()
        logger.info(f"    {label}: {value}")
    logger.info("")

    # Load test data
    test_data: list[dict[str, Any]] = []
    if test_data_path.exists():
        test_data = load_test_data(test_data_path)
        logger.info(f"  Loaded {len(test_data)} test samples from {test_data_path}")
    else:
        logger.info(f"  WARNING: Test data not found at {test_data_path}")
        logger.info(f"  Accuracy benchmarks will be skipped.")

    # -----------------------------------------------------------------------
    # PyTorch benchmarks
    # -----------------------------------------------------------------------
    pytorch_available = False
    pt_tokenizer: Any = None
    pt_model: Any = None
    if not onnx_only:
        try:
            if not model_dir.exists():
                logger.info(f"\n  PyTorch model not found at {model_dir} -- skipping PyTorch benchmarks")
            else:
                logger.info(f"\n  Loading PyTorch model from {model_dir}...")
                pt_tokenizer, pt_model = load_pytorch_model(model_dir)
                pytorch_available = True
                logger.info("  PyTorch model loaded successfully.")
        except ImportError as e:
            logger.info(f"\n  PyTorch/transformers not available ({e}) -- skipping PyTorch benchmarks")
        except Exception as e:
            logger.info(f"\n  Failed to load PyTorch model: {e} -- skipping PyTorch benchmarks")

    if pytorch_available:
        # Latency
        logger.info(f"\n  Running PyTorch latency benchmark ({num_runs} runs)...")
        pt_latency = benchmark_latency(pt_tokenizer, pt_model, "pytorch", num_runs=num_runs)  # type: ignore[possibly-undefined]
        report["pytorch_latency"] = pt_latency
        print_latency_results(pt_latency, "pytorch")

        # Throughput
        logger.info(f"\n  Running PyTorch throughput benchmark...")
        pt_throughput = benchmark_throughput(pt_tokenizer, pt_model, "pytorch", num_runs=min(num_runs, 50))  # type: ignore[possibly-undefined]
        report["pytorch_throughput"] = pt_throughput
        print_throughput_results(pt_throughput, "pytorch")

        # Accuracy
        if test_data:
            logger.info(f"\n  Running PyTorch accuracy benchmark ({len(test_data)} samples)...")
            pt_accuracy = benchmark_accuracy(test_data, pt_tokenizer, pt_model, "pytorch")  # type: ignore[possibly-undefined]
            report["pytorch_accuracy"] = pt_accuracy
            print_accuracy_results(pt_accuracy, "pytorch")

        # Memory
        logger.info(f"\n  Running PyTorch memory benchmark...")
        pt_memory = benchmark_memory(model_dir, onnx_dir, pt_tokenizer, pt_model, "pytorch")  # type: ignore[possibly-undefined]
        report["pytorch_memory"] = pt_memory
        print_memory_results(pt_memory)

    # -----------------------------------------------------------------------
    # ONNX benchmarks
    # -----------------------------------------------------------------------
    onnx_available = False
    onnx_tokenizer: Any = None
    onnx_session: Any = None
    try:
        if not onnx_dir.exists():
            logger.info(f"\n  ONNX model not found at {onnx_dir} -- skipping ONNX benchmarks")
        else:
            onnx_model_file = onnx_dir / "model.onnx"
            if not onnx_model_file.exists():
                logger.info(f"\n  ONNX file not found at {onnx_model_file} -- skipping ONNX benchmarks")
            else:
                logger.info(f"\n  Loading ONNX model from {onnx_dir}...")
                onnx_tokenizer, onnx_session = load_onnx_model(onnx_dir)
                onnx_available = True
                logger.info("  ONNX model loaded successfully.")
    except ImportError as e:
        logger.info(f"\n  onnxruntime not available ({e}) -- skipping ONNX benchmarks")
    except Exception as e:
        logger.info(f"\n  Failed to load ONNX model: {e} -- skipping ONNX benchmarks")

    if onnx_available:
        # Latency
        logger.info(f"\n  Running ONNX latency benchmark ({num_runs} runs)...")
        onnx_latency = benchmark_latency(onnx_tokenizer, onnx_session, "onnx", num_runs=num_runs)  # type: ignore[possibly-undefined]
        report["onnx_latency"] = onnx_latency
        print_latency_results(onnx_latency, "onnx")

        # Throughput
        logger.info(f"\n  Running ONNX throughput benchmark...")
        onnx_throughput = benchmark_throughput(onnx_tokenizer, onnx_session, "onnx", num_runs=min(num_runs, 50))  # type: ignore[possibly-undefined]
        report["onnx_throughput"] = onnx_throughput
        print_throughput_results(onnx_throughput, "onnx")

        # Accuracy
        if test_data:
            logger.info(f"\n  Running ONNX accuracy benchmark ({len(test_data)} samples)...")
            onnx_accuracy = benchmark_accuracy(test_data, onnx_tokenizer, onnx_session, "onnx")  # type: ignore[possibly-undefined]
            report["onnx_accuracy"] = onnx_accuracy
            print_accuracy_results(onnx_accuracy, "onnx")

        # Memory
        logger.info(f"\n  Running ONNX memory benchmark...")
        onnx_memory = benchmark_memory(model_dir, onnx_dir, onnx_tokenizer, onnx_session, "onnx")  # type: ignore[possibly-undefined]
        report["onnx_memory"] = onnx_memory
        print_memory_results(onnx_memory)

    # -----------------------------------------------------------------------
    # Comparison table (if both backends available)
    # -----------------------------------------------------------------------
    if pytorch_available and onnx_available:
        logger.info("")
        headers = ["Metric", "PyTorch", "ONNX", "Speedup"]
        rows = []

        pt_avg = report["pytorch_latency"]["total"]["avg_ms"]
        ox_avg = report["onnx_latency"]["total"]["avg_ms"]
        speedup = pt_avg / ox_avg if ox_avg > 0 else 0
        rows.append(["Avg latency (ms)", f"{pt_avg:.3f}", f"{ox_avg:.3f}", f"{speedup:.2f}x"])

        pt_p95 = report["pytorch_latency"]["total"]["p95_ms"]
        ox_p95 = report["onnx_latency"]["total"]["p95_ms"]
        speedup_p95 = pt_p95 / ox_p95 if ox_p95 > 0 else 0
        rows.append(["P95 latency (ms)", f"{pt_p95:.3f}", f"{ox_p95:.3f}", f"{speedup_p95:.2f}x"])

        # Medium sentence throughput
        if "medium_20w" in report.get("pytorch_throughput", {}) and "medium_20w" in report.get("onnx_throughput", {}):
            pt_sps = report["pytorch_throughput"]["medium_20w"]["sentences_per_second"]
            ox_sps = report["onnx_throughput"]["medium_20w"]["sentences_per_second"]
            tp_ratio = ox_sps / pt_sps if pt_sps > 0 else 0
            rows.append(["Throughput 20w (sent/s)", f"{pt_sps:.1f}", f"{ox_sps:.1f}", f"{tp_ratio:.2f}x"])

        # Accuracy comparison
        if "pytorch_accuracy" in report and "onnx_accuracy" in report:
            pt_f1 = report["pytorch_accuracy"]["overall"]["f1"]
            ox_f1 = report["onnx_accuracy"]["overall"]["f1"]
            rows.append(["F1 score", f"{pt_f1:.6f}", f"{ox_f1:.6f}", "N/A"])

        logger.info(format_table(headers, rows, "PyTorch vs ONNX Comparison"))

    # -----------------------------------------------------------------------
    # Warnings and summary
    # -----------------------------------------------------------------------
    if not pytorch_available and not onnx_available:
        logger.info("\n  ERROR: Neither PyTorch nor ONNX model could be loaded.")
        logger.info("  No benchmarks were run.")

    return report


def save_report(report: dict[str, Any], output_path: Path) -> None:
    """Save the benchmark report to a JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure all values are JSON-serializable
    def make_serializable(obj: Any) -> Any:
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [make_serializable(item) for item in obj]
        return obj

    serializable_report = make_serializable(report)

    with open(output_path, "w") as f:
        json.dump(serializable_report, f, indent=2, default=str)
    logger.info(f"\n  Report saved to {output_path}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Comprehensive benchmark suite for the Quick Correction Model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python ml/quick_correction/benchmark.py\n"
            "  python ml/quick_correction/benchmark.py --onnx-only --runs 200\n"
            "  python ml/quick_correction/benchmark.py --model-dir path/to/model\n"
        ),
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default=None,
        help=(
            "Path to PyTorch model directory "
            f"(default: {DEFAULT_MODEL_DIR.relative_to(PROJECT_ROOT)})"
        ),
    )
    parser.add_argument(
        "--onnx-dir",
        type=str,
        default=None,
        help=(
            "Path to ONNX model directory "
            f"(default: {DEFAULT_ONNX_DIR.relative_to(PROJECT_ROOT)})"
        ),
    )
    parser.add_argument(
        "--test-data",
        type=str,
        default=None,
        help=(
            "Path to test data JSONL file "
            f"(default: {DEFAULT_TEST_DATA.relative_to(PROJECT_ROOT)})"
        ),
    )
    parser.add_argument(
        "--onnx-only",
        action="store_true",
        help="Skip PyTorch benchmarks and only run ONNX benchmarks",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=100,
        help="Number of timed runs for latency benchmarks (default: 100)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help=(
            "Path to save JSON report "
            "(default: <model-dir>/benchmark_report.json)"
        ),
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    model_dir = Path(args.model_dir) if args.model_dir else DEFAULT_MODEL_DIR
    onnx_dir = Path(args.onnx_dir) if args.onnx_dir else DEFAULT_ONNX_DIR
    test_data_path = Path(args.test_data) if args.test_data else DEFAULT_TEST_DATA

    report = run_benchmarks(
        model_dir=model_dir,
        onnx_dir=onnx_dir,
        test_data_path=test_data_path,
        onnx_only=args.onnx_only,
        num_runs=args.runs,
    )

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = model_dir / "benchmark_report.json"

    save_report(report, output_path)

    logger.info("")
    logger.info("=" * 72)
    logger.info("  Benchmark complete.")
    logger.info("=" * 72)


if __name__ == "__main__":
    main()
