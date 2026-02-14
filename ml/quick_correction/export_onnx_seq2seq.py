"""Export trained Seq2Seq model to ONNX format.

Exports the T5-based Quick Correction Model to ONNX with INT8 quantization
for browser inference via @xenova/transformers. Produces:
  - encoder_model.onnx (or encoder_model_quantized.onnx)
  - decoder_model_merged.onnx (or decoder_model_merged_quantized.onnx)
  - tokenizer files (tokenizer.json, spiece.model, etc.)
  - config.json, generation_config.json

Target: <100MB total (INT8), <200ms inference per sentence.
"""

import logging
from pathlib import Path

from transformers import AutoTokenizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def export_seq2seq_to_onnx(
    model_path: Path | str,
    output_path: Path | str,
    quantize: bool = True,
) -> None:
    """Export PyTorch seq2seq model to ONNX format.

    Uses Optimum's ORTModelForSeq2SeqLM for export, which handles the
    encoder/decoder split and KV-cache merging automatically.

    Args:
        model_path: Path to trained PyTorch model
        output_path: Where to save ONNX model
        quantize: Whether to apply INT8 quantization (default: True)
    """
    from optimum.onnxruntime import ORTModelForSeq2SeqLM

    model_path = Path(model_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Exporting seq2seq model from {model_path} to {output_path}...")

    # Load tokenizer
    logger.info("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(str(model_path))

    # Export to ONNX using Optimum
    logger.info("Converting to ONNX format (this may take a minute)...")
    ort_model = ORTModelForSeq2SeqLM.from_pretrained(
        str(model_path),
        export=True,
        provider="CPUExecutionProvider",
    )

    # Save ONNX model
    logger.info("Saving ONNX model...")
    ort_model.save_pretrained(str(output_path))
    tokenizer.save_pretrained(str(output_path))

    # Apply quantization using Optimum's ORTQuantizer (transformer-aware)
    if quantize:
        logger.info("Applying quantization via Optimum ORTQuantizer...")
        try:
            from optimum.onnxruntime import ORTQuantizer
            from optimum.onnxruntime.configuration import AutoQuantizationConfig

            # Optimum quantizes each component (encoder, decoder, decoder_with_past)
            # using avx512_vnni config for best CPU compatibility
            quantization_config = AutoQuantizationConfig.avx2(
                is_static=False,
                per_channel=False,
            )

            onnx_files = [
                f for f in sorted(output_path.glob("*.onnx"))
                if "quantized" not in f.stem
            ]

            for onnx_file in onnx_files:
                logger.info(f"  Quantizing {onnx_file.name}...")
                original_size = onnx_file.stat().st_size / (1024 * 1024)

                quantizer = ORTQuantizer.from_pretrained(
                    str(output_path),
                    file_name=onnx_file.name,
                )
                quantizer.quantize(
                    save_dir=str(output_path),
                    quantization_config=quantization_config,
                )

                # Optimum saves as <stem>_quantized.onnx
                quantized_file = output_path / (onnx_file.stem + "_quantized.onnx")
                if quantized_file.exists():
                    quantized_size = quantized_file.stat().st_size / (1024 * 1024)
                    reduction = (1 - quantized_size / original_size) * 100 if original_size > 0 else 0
                    logger.info(
                        f"    {onnx_file.name}: {original_size:.1f} MB -> "
                        f"{quantized_file.name}: {quantized_size:.1f} MB "
                        f"({reduction:.1f}% reduction)"
                    )
                    # Remove FP32, rename quantized to original name
                    onnx_file.unlink()
                    quantized_file.rename(onnx_file)
                    logger.info(f"    Replaced {onnx_file.name} with quantized version")
                else:
                    logger.warning(f"    Quantized file not found for {onnx_file.name}")

        except Exception as e:
            logger.error(f"Quantization failed: {e}")
            logger.info("Continuing with FP32 model files.")

    # Report final model sizes
    logger.info("\nFinal model files:")
    total_size = 0
    for f in sorted(output_path.iterdir()):
        if f.is_file():
            size_mb = f.stat().st_size / (1024 * 1024)
            total_size += size_mb
            if size_mb > 0.1:  # Only show files > 100KB
                logger.info(f"  {f.name}: {size_mb:.1f} MB")

    logger.info(f"\nTotal size: {total_size:.1f} MB")
    if total_size > 100:
        logger.warning(f"Total model size ({total_size:.1f} MB) exceeds 100 MB target")
    else:
        logger.info("Total size within 100 MB target")

    logger.info("Seq2seq ONNX export complete!")


def test_onnx_seq2seq_inference(
    model_path: Path | str,
    test_text: str = "teh cat sat on teh mat",
) -> None:
    """Test ONNX seq2seq model inference.

    Args:
        model_path: Path to ONNX model directory
        test_text: Test text to correct
    """
    import time

    import numpy as np
    from optimum.onnxruntime import ORTModelForSeq2SeqLM

    model_path = Path(model_path)
    logger.info(f"Testing ONNX seq2seq model from {model_path}...")

    # Load tokenizer and ONNX model
    tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    model = ORTModelForSeq2SeqLM.from_pretrained(str(model_path))

    # Tokenize input
    inputs = tokenizer(
        test_text,
        return_tensors="pt",
        truncation=True,
        max_length=128,
    )

    # Run inference and measure time
    logger.info(f"Running inference on: '{test_text}'")

    times = []
    result = None
    for i in range(10):
        start = time.perf_counter()
        outputs = model.generate(**inputs, max_length=128, num_beams=1)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        if result is None:
            result = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Statistics
    times_arr = np.array(times)
    avg_time = float(np.mean(times_arr))
    p95_time = float(np.percentile(times_arr, 95))

    logger.info(f"Generated: '{result}'")
    logger.info(f"Inference times (10 runs):")
    logger.info(f"  Average: {avg_time:.2f} ms")
    logger.info(f"  P95: {p95_time:.2f} ms")

    if p95_time > 200:
        logger.warning(f"P95 latency ({p95_time:.2f} ms) exceeds 200 ms target")
    else:
        logger.info("Latency within target (<200ms)")


def main():
    """Main export entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Export seq2seq model to ONNX")
    parser.add_argument(
        "--model",
        type=str,
        default="ml/quick_correction/models/quick_correction_seq2seq_v1",
        help="Path to trained PyTorch seq2seq model",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="ml/models",
        help="Output directory for ONNX model",
    )
    parser.add_argument(
        "--no-quantize",
        action="store_true",
        help="Skip INT8 quantization (keep FP32)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test ONNX inference after export",
    )

    args = parser.parse_args()

    model_path = Path(args.model)
    output_path = Path(args.output) / "quick_correction_seq2seq_v1"

    if not model_path.exists():
        logger.error(f"Model not found at {model_path}")
        logger.info("Please train the seq2seq model first:")
        logger.info("  python ml/quick_correction/train_pipeline.py --all --model-type seq2seq")
        return

    # Export
    export_seq2seq_to_onnx(
        model_path=model_path,
        output_path=output_path,
        quantize=not args.no_quantize,
    )

    # Test if requested
    if args.test:
        test_onnx_seq2seq_inference(output_path)


if __name__ == "__main__":
    main()
