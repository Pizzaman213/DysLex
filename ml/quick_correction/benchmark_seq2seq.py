"""Comprehensive benchmark suite for the Seq2Seq Quick Correction Model.

Benchmarks the model across multiple dimensions:
- Latency: PyTorch (MPS/CPU) and ONNX inference timing with percentile statistics
- Throughput: Sentences per second at varying input lengths
- Accuracy: Per-error-type, per-source, no-change, and stratified test sets
- Memory: Model file sizes, peak memory during inference
- Comparison: PyTorch vs ONNX, quantized vs unquantized

Usage:
    python ml/quick_correction/benchmark_seq2seq.py
    python ml/quick_correction/benchmark_seq2seq.py --onnx-only --runs 200
    python ml/quick_correction/benchmark_seq2seq.py --output report.json
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

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PYTORCH_MODEL_DIR = PROJECT_ROOT / "ml" / "quick_correction" / "models" / "quick_correction_seq2seq_v1"
ONNX_MODEL_DIR = PROJECT_ROOT / "ml" / "models" / "quick_correction_seq2seq_v1"
TEST_DATA_DIR = PROJECT_ROOT / "ml" / "quick_correction" / "data"
MAX_LENGTH = 128

# Sentences at varying lengths for throughput benchmarks
THROUGHPUT_SENTENCES = {
    "short_5w": "teh cat sat on mat",
    "medium_15w": "I beleive that the studnets shold recieve there grades befor friday",
    "long_30w": (
        "The reserchers discovred that the enviroment was effecting the "
        "behavour of the animlas in there natural habittat much more then they had "
        "orginally anticpated during there studie"
    ),
    "very_long_60w": (
        "Wen the goverment anounced the new policie on educashun reform "
        "the teachers and there unions expresed consern about the potenshul impact "
        "on there abilitie to teach effectivley in the classrom enviornment becuse "
        "the propused changes wood signifcantly alter the curriculm and evalution "
        "methds that they had been useing for many yeers with there studants"
    ),
}


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def get_system_info() -> dict[str, str]:
    """Collect system information for the benchmark report."""
    info = {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "machine": platform.machine(),
    }
    try:
        import torch
        info["pytorch_version"] = torch.__version__
        info["mps_available"] = str(torch.backends.mps.is_available())
        info["cuda_available"] = str(torch.cuda.is_available())
    except ImportError:
        info["pytorch_version"] = "not installed"
    try:
        import onnxruntime as ort
        info["onnxruntime_version"] = ort.__version__
        info["onnx_available_providers"] = ", ".join(ort.get_available_providers())
    except ImportError:
        info["onnxruntime_version"] = "not installed"
    try:
        import transformers
        info["transformers_version"] = transformers.__version__
    except ImportError:
        info["transformers_version"] = "not installed"
    return info


def compute_percentiles(times: list[float]) -> dict[str, float]:
    """Compute latency statistics from a list of timings (ms)."""
    arr = np.array(times)
    return {
        "avg_ms": round(float(np.mean(arr)), 3),
        "p50_ms": round(float(np.percentile(arr, 50)), 3),
        "p95_ms": round(float(np.percentile(arr, 95)), 3),
        "p99_ms": round(float(np.percentile(arr, 99)), 3),
        "min_ms": round(float(np.min(arr)), 3),
        "max_ms": round(float(np.max(arr)), 3),
        "std_ms": round(float(np.std(arr)), 3),
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
        lines.append(f"\n  {title}")
        lines.append(f"  {'=' * len(title)}")
    lines.append(separator)
    lines.append(header_line)
    lines.append(separator)
    for row in rows:
        line = "| " + " | ".join(str(c).ljust(w) for c, w in zip(row, col_widths)) + " |"
        lines.append(line)
    lines.append(separator)
    return "\n".join(lines)


def _word_error_rate(hypothesis: list[str], reference: list[str]) -> float:
    """Compute word error rate via edit distance."""
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
                d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + 1)
    return d[len(hypothesis)][len(reference)] / len(reference)


def _char_error_rate(hypothesis: str, reference: str) -> float:
    """Compute character error rate."""
    if not reference:
        return 0.0 if not hypothesis else 1.0
    h, r = list(hypothesis), list(reference)
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
                d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + 1)
    return d[len(h)][len(r)] / len(r)


def _compute_metrics(predictions: list[str], targets: list[str]) -> dict[str, float]:
    """Compute exact match, WER, CER."""
    if not predictions:
        return {"exact_match": 0.0, "wer": 1.0, "cer": 1.0, "num_samples": 0}
    exact = sum(1 for p, t in zip(predictions, targets) if p.strip() == t.strip())
    wers = [_word_error_rate(p.strip().split(), t.strip().split()) for p, t in zip(predictions, targets)]
    cers = [_char_error_rate(p.strip(), t.strip()) for p, t in zip(predictions, targets)]
    return {
        "exact_match": round(exact / len(predictions), 4),
        "wer": round(float(np.mean(wers)), 4),
        "cer": round(float(np.mean(cers)), 4),
        "num_samples": len(predictions),
    }


def load_test_data(test_file: Path) -> list[dict[str, Any]]:
    """Load seq2seq test data from JSONL."""
    samples = []
    with open(test_file) as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


# ---------------------------------------------------------------------------
# PyTorch backend
# ---------------------------------------------------------------------------

class PyTorchBackend:
    """PyTorch seq2seq inference backend."""

    def __init__(self, model_dir: Path, device: str = "auto"):
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        self.model = AutoModelForSeq2SeqLM.from_pretrained(str(model_dir))
        self.model.eval()

        if device == "auto":
            if torch.cuda.is_available():
                self.device = torch.device("cuda")
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self.device = torch.device("mps")
            else:
                self.device = torch.device("cpu")
        else:
            self.device = torch.device(device)

        self.model = self.model.to(self.device)
        self.name = f"pytorch-{self.device.type}"

    def generate(self, text: str) -> str:
        import torch
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=MAX_LENGTH)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = self.model.generate(**inputs, max_length=MAX_LENGTH, num_beams=1)
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

    def generate_batch(self, texts: list[str], batch_size: int = 64) -> list[str]:
        import torch
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            inputs = self.tokenizer(batch, return_tensors="pt", truncation=True, max_length=MAX_LENGTH, padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            with torch.no_grad():
                outputs = self.model.generate(**inputs, max_length=MAX_LENGTH, num_beams=1)
            results.extend(self.tokenizer.batch_decode(outputs, skip_special_tokens=True))
        return results

    def to_cpu(self):
        """Move model to CPU for fair latency comparison."""
        import torch
        self.model = self.model.to(torch.device("cpu"))
        self.device = torch.device("cpu")
        self.name = "pytorch-cpu"

    def to_best(self):
        """Move model back to best device."""
        import torch
        if torch.cuda.is_available():
            dev = torch.device("cuda")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            dev = torch.device("mps")
        else:
            dev = torch.device("cpu")
        self.model = self.model.to(dev)
        self.device = dev
        self.name = f"pytorch-{dev.type}"


class ONNXBackend:
    """ONNX Runtime seq2seq inference backend via Optimum."""

    def __init__(self, model_dir: Path, provider: str = "CPUExecutionProvider"):
        from optimum.onnxruntime import ORTModelForSeq2SeqLM
        from transformers import AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        self.model = ORTModelForSeq2SeqLM.from_pretrained(
            str(model_dir),
            provider=provider,
        )
        # Short name for display: "CPUExecutionProvider" -> "cpu"
        short = provider.replace("ExecutionProvider", "").lower()
        self.name = f"onnx-{short}"
        self.provider = provider

    def generate(self, text: str) -> str:
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=MAX_LENGTH)
        outputs = self.model.generate(**inputs, max_length=MAX_LENGTH, num_beams=1)
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

    def generate_batch(self, texts: list[str], batch_size: int = 64) -> list[str]:
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            inputs = self.tokenizer(batch, return_tensors="pt", truncation=True, max_length=MAX_LENGTH, padding=True)
            outputs = self.model.generate(**inputs, max_length=MAX_LENGTH, num_beams=1)
            results.extend(self.tokenizer.batch_decode(outputs, skip_special_tokens=True))
        return results


# ---------------------------------------------------------------------------
# Benchmark: Latency
# ---------------------------------------------------------------------------

def benchmark_latency(
    backend: PyTorchBackend | ONNXBackend,
    num_runs: int = 100,
    warmup: int = 10,
) -> dict[str, Any]:
    """Benchmark single-sentence inference latency."""
    test_sentences = [
        "teh cat sat on teh mat",
        "I beleive the studnets shold recieve there homework",
        "He cleaned the intire house before the guests arrived fro dinner",
    ]

    # Warmup
    for _ in range(warmup):
        backend.generate(test_sentences[0])

    all_times: list[float] = []
    per_sentence: dict[str, list[float]] = {}

    for sent in test_sentences:
        times: list[float] = []
        for _ in range(num_runs):
            start = time.perf_counter()
            backend.generate(sent)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
            all_times.append(elapsed)
        word_count = len(sent.split())
        per_sentence[f"{word_count}w"] = times

    results: dict[str, Any] = {
        "overall": compute_percentiles(all_times),
        "per_length": {k: compute_percentiles(v) for k, v in per_sentence.items()},
    }
    return results


def print_latency_results(results: dict[str, Any], backend_name: str) -> None:
    """Print latency benchmark."""
    headers = ["Metric", "Avg", "P50", "P95", "P99", "Min", "Max", "Std"]
    overall = results["overall"]
    rows = [[
        "Overall",
        f"{overall['avg_ms']:.1f}",
        f"{overall['p50_ms']:.1f}",
        f"{overall['p95_ms']:.1f}",
        f"{overall['p99_ms']:.1f}",
        f"{overall['min_ms']:.1f}",
        f"{overall['max_ms']:.1f}",
        f"{overall['std_ms']:.1f}",
    ]]
    for length, stats in sorted(results["per_length"].items()):
        rows.append([
            length,
            f"{stats['avg_ms']:.1f}",
            f"{stats['p50_ms']:.1f}",
            f"{stats['p95_ms']:.1f}",
            f"{stats['p99_ms']:.1f}",
            f"{stats['min_ms']:.1f}",
            f"{stats['max_ms']:.1f}",
            f"{stats['std_ms']:.1f}",
        ])

    title = f"Latency (ms) — {backend_name} [{results['overall']['num_runs']} total runs]"
    logger.info(format_table(headers, rows, title))

    p95 = overall["p95_ms"]
    status = "PASS" if p95 < 200 else "FAIL"
    logger.info(f"  Target: P95 < 200ms | Actual P95: {p95:.1f}ms | {status}")


# ---------------------------------------------------------------------------
# Benchmark: Throughput
# ---------------------------------------------------------------------------

def benchmark_throughput(
    backend: PyTorchBackend | ONNXBackend,
    num_runs: int = 50,
    warmup: int = 5,
) -> dict[str, Any]:
    """Benchmark throughput at varying input lengths."""
    results: dict[str, Any] = {}

    for length_key, sentence in THROUGHPUT_SENTENCES.items():
        word_count = len(sentence.split()) - 1  # subtract "correct:"

        # Warmup
        for _ in range(warmup):
            backend.generate(sentence)

        times: list[float] = []
        for _ in range(num_runs):
            start = time.perf_counter()
            backend.generate(sentence)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_ms = float(np.mean(times))
        sps = 1000.0 / avg_ms if avg_ms > 0 else 0.0

        results[length_key] = {
            "word_count": word_count,
            "avg_ms": round(avg_ms, 2),
            "sentences_per_second": round(sps, 1),
            "stats": compute_percentiles(times),
        }

    return results


def print_throughput_results(results: dict[str, Any], backend_name: str) -> None:
    """Print throughput benchmark."""
    headers = ["Input", "Words", "Avg (ms)", "P95 (ms)", "Sent/s"]
    rows = []
    for key in ["short_5w", "medium_15w", "long_30w", "very_long_60w"]:
        if key not in results:
            continue
        r = results[key]
        rows.append([
            key, str(r["word_count"]),
            f"{r['avg_ms']:.1f}", f"{r['stats']['p95_ms']:.1f}",
            f"{r['sentences_per_second']:.1f}",
        ])
    logger.info(format_table(headers, rows, f"Throughput — {backend_name}"))


# ---------------------------------------------------------------------------
# Benchmark: Accuracy
# ---------------------------------------------------------------------------

def benchmark_accuracy(
    backend: PyTorchBackend | ONNXBackend,
    test_dir: Path,
) -> dict[str, Any]:
    """Benchmark accuracy across all available test sets."""
    results: dict[str, Any] = {}

    # Main test set with full breakdown
    main_file = test_dir / "test_seq2seq.jsonl"
    if not main_file.exists():
        logger.info("  No test data found, skipping accuracy benchmark")
        return results

    samples = load_test_data(main_file)
    # Strip legacy "correct: " prefix
    for s in samples:
        if s["input_text"].startswith("correct: "):
            s["input_text"] = s["input_text"][len("correct: "):]
    logger.info(f"  Running inference on {len(samples)} test samples...")

    input_texts = [s["input_text"] for s in samples]
    targets = [s["target_text"] for s in samples]
    predictions = backend.generate_batch(input_texts)

    # Overall
    results["overall"] = _compute_metrics(predictions, targets)

    # No-change accuracy
    no_change_preds, no_change_inputs = [], []
    for i, sample in enumerate(samples):
        raw = sample["input_text"].strip()
        if raw == sample["target_text"].strip():
            no_change_preds.append(predictions[i])
            no_change_inputs.append(raw)
    if no_change_preds:
        nc_correct = sum(1 for p, inp in zip(no_change_preds, no_change_inputs) if p.strip() == inp.strip())
        results["no_change_accuracy"] = round(nc_correct / len(no_change_preds), 4)
        results["no_change_samples"] = len(no_change_preds)
    else:
        results["no_change_accuracy"] = None

    # Per-source breakdown
    per_source: dict[str, dict[str, list[str]]] = {}
    per_error: dict[str, dict[str, list[str]]] = {}
    for i, sample in enumerate(samples):
        src = sample.get("source", "unknown")
        etype = sample.get("error_type", "unknown")
        per_source.setdefault(src, {"p": [], "t": []})
        per_source[src]["p"].append(predictions[i])
        per_source[src]["t"].append(targets[i])
        per_error.setdefault(etype, {"p": [], "t": []})
        per_error[etype]["p"].append(predictions[i])
        per_error[etype]["t"].append(targets[i])

    results["per_source"] = {k: _compute_metrics(v["p"], v["t"]) for k, v in sorted(per_source.items())}
    results["per_error_type"] = {k: _compute_metrics(v["p"], v["t"]) for k, v in sorted(per_error.items())}

    # Grammar vs spelling aggregates
    grammar_types = {"subject_verb", "article", "verb_tense", "function_word", "word_order", "run_on", "pronoun_case", "grammar"}
    grammar_p, grammar_t, spelling_p, spelling_t = [], [], [], []
    for etype, data in per_error.items():
        if etype in grammar_types:
            grammar_p.extend(data["p"])
            grammar_t.extend(data["t"])
        elif etype not in ("none", "unknown"):
            spelling_p.extend(data["p"])
            spelling_t.extend(data["t"])

    if grammar_p:
        results["grammar_aggregate"] = _compute_metrics(grammar_p, grammar_t)
    if spelling_p:
        results["spelling_aggregate"] = _compute_metrics(spelling_p, spelling_t)

    # Stratified test sets
    stratified_files = {
        "spelling": "test_seq2seq_spelling.jsonl",
        "grammar": "test_seq2seq_grammar.jsonl",
        "mixed": "test_seq2seq_mixed.jsonl",
        "hard": "test_seq2seq_hard.jsonl",
        "function_word": "test_seq2seq_function_word.jsonl",
        "verb_tense": "test_seq2seq_verb_tense.jsonl",
    }
    results["stratified"] = {}
    for name, filename in stratified_files.items():
        filepath = test_dir / filename
        if filepath.exists():
            s_samples = load_test_data(filepath)
            for s in s_samples:
                if s["input_text"].startswith("correct: "):
                    s["input_text"] = s["input_text"][len("correct: "):]
            s_inputs = [s["input_text"] for s in s_samples]
            s_targets = [s["target_text"] for s in s_samples]
            s_preds = backend.generate_batch(s_inputs)
            results["stratified"][name] = _compute_metrics(s_preds, s_targets)

    return results


def print_accuracy_results(results: dict[str, Any], backend_name: str) -> None:
    """Print accuracy benchmark."""
    if not results:
        return

    overall = results.get("overall", {})
    logger.info(format_table(
        ["Metric", "Value"],
        [
            ["Exact Match", f"{overall.get('exact_match', 0):.4f}"],
            ["WER", f"{overall.get('wer', 0):.4f}"],
            ["CER", f"{overall.get('cer', 0):.4f}"],
            ["Samples", str(overall.get("num_samples", 0))],
        ],
        f"Accuracy — {backend_name} (overall)",
    ))

    nc = results.get("no_change_accuracy")
    if nc is not None:
        status = "PASS" if nc >= 0.98 else "FAIL"
        logger.info(f"  No-change accuracy: {nc:.4f} ({results['no_change_samples']} samples) | Target >=0.98 | {status}")

    # Per-source
    if results.get("per_source"):
        headers = ["Source", "EM", "WER", "CER", "N"]
        rows = []
        for src, m in sorted(results["per_source"].items()):
            rows.append([src, f"{m['exact_match']:.4f}", f"{m['wer']:.4f}", f"{m['cer']:.4f}", str(m["num_samples"])])
        logger.info(format_table(headers, rows, f"Per-Source — {backend_name}"))

    # Per-error-type
    if results.get("per_error_type"):
        headers = ["Error Type", "EM", "WER", "CER", "N"]
        rows = []
        for etype, m in sorted(results["per_error_type"].items()):
            rows.append([etype, f"{m['exact_match']:.4f}", f"{m['wer']:.4f}", f"{m['cer']:.4f}", str(m["num_samples"])])
        logger.info(format_table(headers, rows, f"Per-Error-Type — {backend_name}"))

    # Grammar / spelling aggregates
    for key, label, target in [("grammar_aggregate", "Grammar", 0.85), ("spelling_aggregate", "Spelling", 0.95)]:
        agg = results.get(key)
        if agg:
            status = "PASS" if agg["exact_match"] >= target else "FAIL"
            logger.info(f"  {label} aggregate: EM={agg['exact_match']:.4f} ({agg['num_samples']} samples) | Target >={target} | {status}")

    # Stratified
    if results.get("stratified"):
        headers = ["Test Set", "EM", "WER", "CER", "N"]
        rows = []
        for name, m in sorted(results["stratified"].items()):
            rows.append([name, f"{m['exact_match']:.4f}", f"{m['wer']:.4f}", f"{m['cer']:.4f}", str(m["num_samples"])])
        logger.info(format_table(headers, rows, f"Stratified Test Sets — {backend_name}"))


# ---------------------------------------------------------------------------
# Benchmark: Memory
# ---------------------------------------------------------------------------

def benchmark_memory(
    backend: PyTorchBackend | ONNXBackend,
    model_dir: Path,
    num_runs: int = 20,
) -> dict[str, Any]:
    """Profile memory usage during inference."""
    test_text = "I beleive the studnets shold recieve there homework"

    # File sizes
    file_sizes: dict[str, float] = {}
    total_bytes = 0
    for f in sorted(model_dir.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            size = f.stat().st_size
            total_bytes += size
            size_mb = size / (1024 * 1024)
            if size_mb > 0.1:
                file_sizes[f.name] = round(size_mb, 2)
    file_sizes["TOTAL"] = round(total_bytes / (1024 * 1024), 2)

    # Quantized-only total
    quant_bytes = sum(
        f.stat().st_size for f in model_dir.iterdir()
        if f.is_file() and (
            f.suffix != ".onnx"
            or "quantized" in f.name
        ) and not f.name.startswith(".")
        and "quantized_quantized" not in f.name
    )
    file_sizes["quantized_subset"] = round(quant_bytes / (1024 * 1024), 2)

    # Memory profiling
    tracemalloc.start()
    for _ in range(num_runs):
        tracemalloc.reset_peak()
        backend.generate(test_text)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "file_sizes_mb": file_sizes,
        "peak_memory_mb": round(peak / (1024 * 1024), 2),
        "current_memory_mb": round(current / (1024 * 1024), 2),
    }


def print_memory_results(results: dict[str, Any], backend_name: str) -> None:
    """Print memory benchmark."""
    headers = ["File", "Size (MB)"]
    rows = [[name, str(size)] for name, size in sorted(results["file_sizes_mb"].items())]
    logger.info(format_table(headers, rows, f"Model Files — {backend_name}"))
    logger.info(f"  Peak memory (traced): {results['peak_memory_mb']:.2f} MB")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def _detect_onnx_providers(providers_arg: str | None) -> list[str]:
    """Return the list of ONNX providers to benchmark.

    If *providers_arg* is given (comma-separated), use that list.
    Otherwise auto-detect all available providers.
    """
    try:
        import onnxruntime as _ort
        available = set(_ort.get_available_providers())
    except ImportError:
        return []

    if providers_arg:
        requested = [p.strip() for p in providers_arg.split(",") if p.strip()]
        return [p for p in requested if p in available]

    # Default priority order
    priority = [
        "CoreMLExecutionProvider",
        "OpenVINOExecutionProvider",
        "QNNExecutionProvider",
        "VitisAIExecutionProvider",
        "DmlExecutionProvider",
        "CUDAExecutionProvider",
        "CPUExecutionProvider",
    ]
    return [p for p in priority if p in available]


def run_benchmarks(
    pytorch_dir: Path,
    onnx_dir: Path,
    test_dir: Path,
    onnx_only: bool = False,
    num_runs: int = 100,
    providers_arg: str | None = None,
) -> dict[str, Any]:
    """Run all benchmarks and return combined report."""
    report: dict[str, Any] = {
        "system_info": get_system_info(),
        "config": {
            "pytorch_model_dir": str(pytorch_dir),
            "onnx_model_dir": str(onnx_dir),
            "test_data_dir": str(test_dir),
            "onnx_only": onnx_only,
            "num_runs": num_runs,
            "max_length": MAX_LENGTH,
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    logger.info("=" * 72)
    logger.info("  Seq2Seq Quick Correction Model — Comprehensive Benchmark")
    logger.info("=" * 72)

    sys_info = report["system_info"]
    logger.info("\n  System")
    logger.info("  ------")
    for key, value in sys_info.items():
        logger.info(f"    {key}: {value}")

    # -------------------------------------------------------------------
    # PyTorch
    # -------------------------------------------------------------------
    pt_backend = None
    if not onnx_only and pytorch_dir.exists():
        try:
            logger.info(f"\n  Loading PyTorch model from {pytorch_dir}...")
            pt_backend = PyTorchBackend(pytorch_dir)
            logger.info(f"  Loaded on {pt_backend.device}")
        except Exception as e:
            logger.info(f"  Failed to load PyTorch model: {e}")

    if pt_backend is not None:
        # Accuracy (on best device for speed)
        logger.info(f"\n  [PyTorch] Accuracy benchmark...")
        pt_accuracy = benchmark_accuracy(pt_backend, test_dir)
        report["pytorch_accuracy"] = pt_accuracy
        print_accuracy_results(pt_accuracy, pt_backend.name)

        # Latency — on CPU for deployment-realistic numbers
        pt_backend.to_cpu()
        logger.info(f"\n  [PyTorch-CPU] Latency benchmark ({num_runs} runs/sentence)...")
        pt_latency = benchmark_latency(pt_backend, num_runs=num_runs)
        report["pytorch_latency"] = pt_latency
        print_latency_results(pt_latency, "pytorch-cpu")

        # Throughput — on CPU
        logger.info(f"\n  [PyTorch-CPU] Throughput benchmark...")
        pt_throughput = benchmark_throughput(pt_backend, num_runs=min(num_runs, 50))
        report["pytorch_throughput"] = pt_throughput
        print_throughput_results(pt_throughput, "pytorch-cpu")

        # Memory
        logger.info(f"\n  [PyTorch] Memory benchmark...")
        pt_memory = benchmark_memory(pt_backend, pytorch_dir)
        report["pytorch_memory"] = pt_memory
        print_memory_results(pt_memory, "pytorch")

        pt_backend.to_best()

    # -------------------------------------------------------------------
    # ONNX — benchmark each available provider
    # -------------------------------------------------------------------
    onnx_providers = _detect_onnx_providers(providers_arg) if onnx_dir.exists() else []
    if onnx_providers:
        logger.info(f"\n  ONNX providers to benchmark: {', '.join(onnx_providers)}")

    onnx_results: dict[str, dict[str, Any]] = {}

    for provider in onnx_providers:
        onnx_backend = None
        try:
            logger.info(f"\n  Loading ONNX model with {provider}...")
            onnx_backend = ONNXBackend(onnx_dir, provider=provider)
            logger.info(f"  Loaded ({onnx_backend.name})")
        except Exception as e:
            logger.info(f"  Failed to load ONNX model with {provider}: {e}")
            continue

        pkey = onnx_backend.name  # e.g. "onnx-cpu", "onnx-coreml"
        result: dict[str, Any] = {}

        # Smoke-test: run a single inference to catch runtime failures
        # (e.g. CoreML loads but crashes on unsupported T5 encoder ops)
        try:
            onnx_backend.generate("teh cat")
        except Exception as e:
            logger.info(f"  {pkey} failed at inference, skipping: {e}")
            continue

        # Accuracy
        logger.info(f"\n  [{pkey}] Accuracy benchmark...")
        acc = benchmark_accuracy(onnx_backend, test_dir)
        result["accuracy"] = acc
        report[f"{pkey}_accuracy"] = acc
        print_accuracy_results(acc, pkey)

        # Latency
        logger.info(f"\n  [{pkey}] Latency benchmark ({num_runs} runs/sentence)...")
        lat = benchmark_latency(onnx_backend, num_runs=num_runs)
        result["latency"] = lat
        report[f"{pkey}_latency"] = lat
        print_latency_results(lat, pkey)

        # Throughput
        logger.info(f"\n  [{pkey}] Throughput benchmark...")
        thr = benchmark_throughput(onnx_backend, num_runs=min(num_runs, 50))
        result["throughput"] = thr
        report[f"{pkey}_throughput"] = thr
        print_throughput_results(thr, pkey)

        # Memory
        logger.info(f"\n  [{pkey}] Memory benchmark...")
        mem = benchmark_memory(onnx_backend, onnx_dir)
        result["memory"] = mem
        report[f"{pkey}_memory"] = mem
        print_memory_results(mem, pkey)

        onnx_results[pkey] = result

    # Backward-compat keys for the default CPU provider
    if "onnx-cpu" in onnx_results:
        report["onnx_accuracy"] = onnx_results["onnx-cpu"].get("accuracy", {})
        report["onnx_latency"] = onnx_results["onnx-cpu"].get("latency", {})
        report["onnx_throughput"] = onnx_results["onnx-cpu"].get("throughput", {})
        report["onnx_memory"] = onnx_results["onnx-cpu"].get("memory", {})

    # -------------------------------------------------------------------
    # Comparison — PyTorch vs first ONNX provider
    # -------------------------------------------------------------------
    first_onnx = next(iter(onnx_results), None)
    if pt_backend is not None and first_onnx is not None:
        pt_lat = report["pytorch_latency"]["overall"]
        ox_lat = onnx_results[first_onnx]["latency"]["overall"]
        speedup_avg = pt_lat["avg_ms"] / ox_lat["avg_ms"] if ox_lat["avg_ms"] > 0 else 0
        speedup_p95 = pt_lat["p95_ms"] / ox_lat["p95_ms"] if ox_lat["p95_ms"] > 0 else 0

        headers = ["Metric", "PyTorch-CPU", first_onnx, "Speedup"]
        rows = [
            ["Avg latency (ms)", f"{pt_lat['avg_ms']:.1f}", f"{ox_lat['avg_ms']:.1f}", f"{speedup_avg:.2f}x"],
            ["P95 latency (ms)", f"{pt_lat['p95_ms']:.1f}", f"{ox_lat['p95_ms']:.1f}", f"{speedup_p95:.2f}x"],
        ]

        # Throughput comparison at medium length
        pt_thr = report.get("pytorch_throughput", {}).get("medium_15w")
        ox_thr = onnx_results[first_onnx].get("throughput", {}).get("medium_15w")
        if pt_thr and ox_thr:
            pt_sps = pt_thr["sentences_per_second"]
            ox_sps = ox_thr["sentences_per_second"]
            tp_ratio = ox_sps / pt_sps if pt_sps > 0 else 0
            rows.append(["Throughput 15w (sent/s)", f"{pt_sps:.1f}", f"{ox_sps:.1f}", f"{tp_ratio:.2f}x"])

        # Accuracy comparison
        pt_em = report.get("pytorch_accuracy", {}).get("overall", {}).get("exact_match", 0)
        ox_em = onnx_results[first_onnx].get("accuracy", {}).get("overall", {}).get("exact_match", 0)
        rows.append(["Exact Match", f"{pt_em:.4f}", f"{ox_em:.4f}", "—"])

        logger.info(format_table(headers, rows, f"PyTorch vs {first_onnx} Comparison"))

        report["comparison"] = {
            "latency_speedup_avg": round(speedup_avg, 2),
            "latency_speedup_p95": round(speedup_p95, 2),
        }

    # -------------------------------------------------------------------
    # Provider-vs-provider comparison (when multiple ONNX providers)
    # -------------------------------------------------------------------
    provider_keys = list(onnx_results.keys())
    if len(provider_keys) >= 2:
        base_key = provider_keys[0]
        base_lat = onnx_results[base_key]["latency"]["overall"]

        headers = ["Metric"] + provider_keys
        avg_row = ["Avg latency (ms)"]
        p95_row = ["P95 latency (ms)"]
        ratio_row = ["Ratio vs " + base_key]

        for pk in provider_keys:
            lat = onnx_results[pk]["latency"]["overall"]
            avg_row.append(f"{lat['avg_ms']:.1f}")
            p95_row.append(f"{lat['p95_ms']:.1f}")
            ratio = base_lat["avg_ms"] / lat["avg_ms"] if lat["avg_ms"] > 0 else 0
            ratio_row.append(f"{ratio:.2f}x")

        logger.info(format_table(headers, [avg_row, p95_row, ratio_row], "Provider Comparison"))

    # -------------------------------------------------------------------
    # Regression gate
    # -------------------------------------------------------------------
    gate_failures = []

    # Check ONNX accuracy (primary deployment target)
    acc_source = report.get("onnx_accuracy") or report.get("pytorch_accuracy", {})
    if acc_source:
        overall_em = acc_source.get("overall", {}).get("exact_match", 0)
        if overall_em < 0.85:
            gate_failures.append(f"Overall EM: {overall_em:.4f} < 0.85")

        sp = acc_source.get("stratified", {}).get("spelling", {})
        if sp and sp.get("exact_match", 0) < 0.95:
            gate_failures.append(f"Spelling EM: {sp['exact_match']:.4f} < 0.95")

        gr = acc_source.get("stratified", {}).get("grammar", {})
        if gr and gr.get("exact_match", 0) < 0.85:
            gate_failures.append(f"Grammar EM: {gr['exact_match']:.4f} < 0.85")

    # Check latency
    lat_source = report.get("onnx_latency") or report.get("pytorch_latency", {})
    if lat_source:
        p95 = lat_source.get("overall", {}).get("p95_ms", 0)
        if p95 > 200:
            gate_failures.append(f"P95 latency: {p95:.1f}ms > 200ms")

    report["gate_passed"] = len(gate_failures) == 0
    report["gate_failures"] = gate_failures

    logger.info(f"\n{'=' * 72}")
    if gate_failures:
        logger.info("  REGRESSION GATE: FAILED")
        for f in gate_failures:
            logger.info(f"    - {f}")
    else:
        logger.info("  REGRESSION GATE: PASSED")
    logger.info(f"{'=' * 72}")

    return report


def save_report(report: dict[str, Any], output_path: Path) -> None:
    """Save benchmark report to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

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

    with open(output_path, "w") as f:
        json.dump(make_serializable(report), f, indent=2, default=str)
    logger.info(f"\n  Report saved to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Comprehensive benchmark for the Seq2Seq Quick Correction Model",
    )
    parser.add_argument("--pytorch-dir", type=str, default=None, help="PyTorch model directory")
    parser.add_argument("--onnx-dir", type=str, default=None, help="ONNX model directory")
    parser.add_argument("--test-dir", type=str, default=None, help="Test data directory")
    parser.add_argument("--onnx-only", action="store_true", help="Skip PyTorch benchmarks")
    parser.add_argument("--runs", type=int, default=100, help="Timed runs per sentence (default: 100)")
    parser.add_argument("--output", type=str, default=None, help="Output JSON report path")
    parser.add_argument(
        "--providers",
        type=str,
        default=None,
        help="Comma-separated ONNX providers to benchmark (default: auto-detect all available)",
    )
    parser.add_argument("--beam", type=int, default=1, help="Number of beams for beam search (default: 1 = greedy)")
    parser.add_argument("--two-pass", action="store_true", help="Run two-pass inference: spelling first, then grammar")
    args = parser.parse_args()

    pytorch_dir = Path(args.pytorch_dir) if args.pytorch_dir else PYTORCH_MODEL_DIR
    onnx_dir = Path(args.onnx_dir) if args.onnx_dir else ONNX_MODEL_DIR
    test_dir = Path(args.test_dir) if args.test_dir else TEST_DATA_DIR

    report = run_benchmarks(
        pytorch_dir=pytorch_dir,
        onnx_dir=onnx_dir,
        test_dir=test_dir,
        onnx_only=args.onnx_only,
        num_runs=args.runs,
        providers_arg=args.providers,
    )

    output_path = Path(args.output) if args.output else onnx_dir / "benchmark_report.json"
    save_report(report, output_path)

    logger.info("\n  Benchmark complete.")


if __name__ == "__main__":
    main()
