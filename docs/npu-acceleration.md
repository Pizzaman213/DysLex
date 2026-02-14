# NPU Acceleration

DysLex AI's Quick Correction model runs through ONNX Runtime, which supports hardware accelerators beyond the CPU. Modern laptops increasingly include dedicated Neural Processing Units (NPUs) that can run inference faster and at lower power than the CPU. When available, DysLex AI uses these automatically.

## Why NPUs Matter

The Quick Correction model targets **< 50 ms** per correction so that fixes feel instant while writing. On CPU this is achievable, but NPU execution can cut latency further — especially on battery — and free CPU cycles for the editor and browser.

> **Tested on:** Apple Silicon (M-series) macOS only so far. Intel, Qualcomm, AMD, and DirectML providers are implemented but have not been tested on real hardware yet. Contributions and test reports from those platforms are welcome.

## Supported Hardware

| Vendor | Hardware | ONNX Provider | Install | Tested |
|--------|----------|---------------|---------|--------|
| Apple | M1/M2/M3/M4 (Neural Engine) | `CoreMLExecutionProvider` | Included in `onnxruntime` on macOS ARM64 | Yes |
| Intel | Core Ultra (Meteor Lake+) | `OpenVINOExecutionProvider` | `pip install onnxruntime-openvino>=1.21.0` | No |
| Qualcomm | Snapdragon X Elite / X Plus | `QNNExecutionProvider` | `pip install onnxruntime-qnn` (Qualcomm AI Hub) | No |
| AMD | Ryzen AI (XDNA NPU) | `VitisAIExecutionProvider` | Vitis AI toolkit — see [AMD docs](https://ryzenai.docs.amd.com) | No |
| Any (Windows) | DirectML-compatible GPU | `DmlExecutionProvider` | `pip install onnxruntime-directml>=1.21.0` | No |
| NVIDIA | CUDA GPU | `CUDAExecutionProvider` | `pip install onnxruntime-gpu>=1.21.0` | No |
| Any | CPU (always available) | `CPUExecutionProvider` | Included in base `onnxruntime` | Yes |

> **Important:** The accelerator-specific `onnxruntime-*` packages are **mutually exclusive** with the base `onnxruntime` package. Install only one variant. The base package should be uninstalled first if switching.

## Quick Setup

### Apple Silicon (macOS)

No extra steps — `CoreMLExecutionProvider` is bundled with the standard `onnxruntime` wheel on ARM64 macOS. DysLex AI will auto-detect it.

```bash
# Verify
python -c "import onnxruntime; print(onnxruntime.get_available_providers())"
# Should include 'CoreMLExecutionProvider'
```

### Intel NPU

```bash
pip uninstall onnxruntime -y
pip install onnxruntime-openvino>=1.21.0
```

### Qualcomm NPU

```bash
pip uninstall onnxruntime -y
pip install onnxruntime-qnn
```

### NVIDIA GPU

```bash
pip uninstall onnxruntime -y
pip install onnxruntime-gpu>=1.21.0
```

### Windows DirectML

```bash
pip uninstall onnxruntime -y
pip install onnxruntime-directml>=1.21.0
```

## Configuration

### Auto-Detection (default)

By default DysLex AI calls `onnxruntime.get_available_providers()` at startup and picks the highest-priority accelerator available. No configuration needed.

The priority order is:

```
CoreML → OpenVINO → QNN → VitisAI → DirectML → CUDA → CPU
```

### Manual Override

Set the `DYSLEX_ONNX_PROVIDERS` environment variable to a comma-separated list of providers to try, in order:

```bash
# Force CPU only
export DYSLEX_ONNX_PROVIDERS="CPUExecutionProvider"

# Prefer CoreML, fall back to CPU
export DYSLEX_ONNX_PROVIDERS="CoreMLExecutionProvider,CPUExecutionProvider"
```

Or set `onnx_providers` in the backend config (`.env` file):

```
ONNX_PROVIDERS=CoreMLExecutionProvider,CPUExecutionProvider
```

### How Fallback Works

1. DysLex AI reads the provider list (auto-detected or from config).
2. For each provider, it attempts to create an ONNX session.
3. If a provider fails (missing runtime, unsupported hardware, etc.), a warning is logged and the next provider is tried.
4. `CPUExecutionProvider` is always appended as the final fallback.
5. The active provider is logged at startup and reported in health checks.

## Benchmarking NPU Performance

Use the benchmark suite to compare providers on your hardware:

```bash
# Auto-detect and benchmark all available providers
python ml/quick_correction/benchmark_seq2seq.py --onnx-only --runs 50

# Benchmark specific providers
python ml/quick_correction/benchmark_seq2seq.py --onnx-only --runs 50 \
    --providers "CoreMLExecutionProvider,CPUExecutionProvider"

# The token-classification benchmark also supports multi-provider
python ml/quick_correction/benchmark.py --onnx-only --runs 50 \
    --providers "CoreMLExecutionProvider,CPUExecutionProvider"
```

The benchmark report includes per-provider latency, throughput, and accuracy results so you can compare NPU vs CPU performance on your specific hardware.

### Reading Benchmark Results

The benchmark outputs a comparison table like:

```
  Provider Comparison
  ===================
+-----------+-----------+-----------+---------+
| Metric    | onnx-cpu  | onnx-coreml | Ratio |
+-----------+-----------+-----------+---------+
| Avg (ms)  | 45.2      | 12.8        | 3.53x |
| P95 (ms)  | 52.1      | 15.3        | 3.40x |
+-----------+-----------+-----------+---------+
```

Look for the **Avg** and **P95** columns — lower is better. The **Ratio** column shows the speedup relative to the first (baseline) provider.

### Apple Silicon Benchmark Results (M3 Max, onnxruntime 1.22)

Token-classification model (DistilBERT, 253 MB) — `benchmark.py --onnx-only --runs 50`:

| Metric | CoreML | CPU | Winner |
|--------|--------|-----|--------|
| Avg latency (ms) | 17.95 | 4.54 | CPU (3.95x) |
| P95 latency (ms) | 20.57 | 5.81 | CPU (3.54x) |
| Throughput 20w (sent/s) | 46.7 | 91.3 | CPU (1.95x) |
| Accuracy (F1) | 0.9919 | 0.9919 | Identical |

On this model, **CPU is faster than CoreML**. CoreML only offloads 161 of 311 graph nodes (the embedding layer exceeds CoreML's 16K dimension limit), so the overhead of copying tensors between CPU and Neural Engine outweighs the acceleration. This is expected for smaller models — CoreML shines on larger models where more nodes can be offloaded.

The seq2seq model (T5-based, ~1.6 GB) does not currently work with `CoreMLExecutionProvider` through Optimum's `ORTModelForSeq2SeqLM` due to unsupported encoder operations. It runs on CPU only.

Both models pass the **< 50 ms P95** latency target on CPU.

## Troubleshooting

### Provider installed but not detected

```bash
# Check what providers are available
python -c "import onnxruntime; print(onnxruntime.get_available_providers())"
```

If your expected provider is missing:
- Ensure you installed the correct `onnxruntime-*` variant (not the base package).
- Check that the hardware driver / runtime is installed (e.g., Intel OpenVINO toolkit, CUDA toolkit).
- On macOS ARM64, `CoreMLExecutionProvider` requires macOS 12+.

### CoreML first-load compilation delay

The first time a model runs with `CoreMLExecutionProvider`, Core ML compiles the model to an optimised representation. This one-time compilation can take several seconds. Subsequent loads use the cached compilation and are fast.

### Package conflicts

The `onnxruntime-*` packages conflict with each other. If you see import errors, ensure only one variant is installed:

```bash
pip list | grep onnxruntime
# Should show exactly one: onnxruntime, onnxruntime-gpu, onnxruntime-openvino, etc.
```

### Session creation fails with warnings

If the log shows `Provider X failed, trying next`, the provider was detected but couldn't initialise a session for the model. Common causes:
- Model uses ops not supported by the provider.
- Provider requires a specific model format (e.g., FP16 for some NPUs).

In these cases the system falls back to the next provider automatically.

## Developer Notes

### Adding a New Provider

1. Add the provider name to `PROVIDER_PRIORITY` in `backend/app/core/npu_provider.py`.
2. Add provider-specific options to `_PROVIDER_OPTIONS` in the same file.
3. Update the supported hardware table in this document.
4. The benchmark suite will automatically pick up the new provider via auto-detection.
