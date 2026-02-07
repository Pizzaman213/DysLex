"""Export trained PyTorch model to ONNX format.

Exports the Quick Correction Model to ONNX with optimizations for
browser and server-side inference. Target: <150MB, <50ms inference.
"""

import logging
from pathlib import Path

import torch
from optimum.onnxruntime import ORTModelForTokenClassification
from transformers import AutoTokenizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def export_to_onnx(
    model_path: Path | str,
    output_path: Path | str,
    optimize: bool = True,
    quantize: bool = False,
) -> None:
    """Export PyTorch model to ONNX format.

    Args:
        model_path: Path to trained PyTorch model
        output_path: Where to save ONNX model
        optimize: Whether to apply graph optimizations
        quantize: Whether to apply INT8 quantization (smaller but less accurate)
    """
    model_path = Path(model_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Exporting model from {model_path} to {output_path}...")

    # Load tokenizer
    logger.info("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(str(model_path))

    # Export to ONNX using Optimum
    logger.info("Converting to ONNX format...")
    ort_model = ORTModelForTokenClassification.from_pretrained(
        str(model_path),
        export=True,
        provider="CPUExecutionProvider",
    )

    # Save ONNX model
    logger.info("Saving ONNX model...")
    ort_model.save_pretrained(str(output_path))
    tokenizer.save_pretrained(str(output_path))

    # Apply quantization if requested
    if quantize:
        logger.info("Applying INT8 quantization...")
        try:
            from onnxruntime.quantization import QuantType, quantize_dynamic

            model_file = output_path / "model.onnx"
            quantized_file = output_path / "model_int8.onnx"

            quantize_dynamic(
                model_input=str(model_file),
                model_output=str(quantized_file),
                weight_type=QuantType.QUInt8,
                optimize_model=optimize,
            )

            logger.info(f"Quantized model saved to {quantized_file}")

            # Compare sizes
            original_size = model_file.stat().st_size / (1024 * 1024)
            quantized_size = quantized_file.stat().st_size / (1024 * 1024)
            logger.info(f"Original: {original_size:.1f} MB")
            logger.info(f"Quantized: {quantized_size:.1f} MB")
            logger.info(f"Reduction: {(1 - quantized_size/original_size)*100:.1f}%")

        except Exception as e:
            logger.error(f"Quantization failed: {e}")

    # Check final model size
    model_files = list(output_path.glob("*.onnx"))
    for model_file in model_files:
        size_mb = model_file.stat().st_size / (1024 * 1024)
        logger.info(f"Model file: {model_file.name} ({size_mb:.1f} MB)")

        if size_mb > 150:
            logger.warning(f"Model size ({size_mb:.1f} MB) exceeds 150 MB target")

    logger.info("Export complete!")


def test_onnx_inference(model_path: Path | str, test_text: str = "teh cat sat on teh mat") -> None:
    """Test ONNX model inference.

    Args:
        model_path: Path to ONNX model directory
        test_text: Test text with errors
    """
    import time

    import numpy as np
    import onnxruntime as ort

    model_path = Path(model_path)
    logger.info(f"Testing ONNX model from {model_path}...")

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(model_path))

    # Load ONNX session
    onnx_file = model_path / "model.onnx"
    if not onnx_file.exists():
        logger.error(f"ONNX file not found: {onnx_file}")
        return

    session = ort.InferenceSession(
        str(onnx_file),
        providers=["CPUExecutionProvider"],
    )

    # Tokenize input
    inputs = tokenizer(
        test_text,
        return_tensors="np",
        padding=True,
        truncation=True,
        max_length=128,
    )

    # Run inference and measure time
    logger.info(f"Running inference on: '{test_text}'")

    times = []
    for i in range(10):
        start = time.perf_counter()
        outputs = session.run(
            None,
            {
                "input_ids": inputs["input_ids"].astype(np.int64),
                "attention_mask": inputs["attention_mask"].astype(np.int64),
            },
        )
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    # Statistics
    avg_time = np.mean(times)
    p95_time = np.percentile(times, 95)

    logger.info(f"Inference times (10 runs):")
    logger.info(f"  Average: {avg_time:.2f} ms")
    logger.info(f"  P95: {p95_time:.2f} ms")

    if p95_time > 50:
        logger.warning(f"P95 latency ({p95_time:.2f} ms) exceeds 50 ms target")
    else:
        logger.info(f"✓ Latency within target (<50ms)")

    # Show predictions
    predictions = outputs[0]
    predicted_labels = np.argmax(predictions, axis=-1)[0]

    tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
    logger.info("\nPredictions:")
    for token, label in zip(tokens, predicted_labels):
        if label != 0:  # Not O (no error)
            logger.info(f"  {token}: label={label}")


def main():
    """Main export entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Export model to ONNX")
    parser.add_argument(
        "--model",
        type=str,
        default="ml/quick_correction/models/quick_correction_base_v1",
        help="Path to trained PyTorch model",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="ml/models",
        help="Output directory for ONNX model",
    )
    parser.add_argument(
        "--quantize",
        action="store_true",
        help="Apply INT8 quantization",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test ONNX inference after export",
    )

    args = parser.parse_args()

    model_path = Path(args.model)
    output_path = Path(args.output) / "quick_correction_base_v1"

    if not model_path.exists():
        logger.error(f"Model not found at {model_path}")
        logger.info("Please train the model first using train.py")
        return

    # Export
    export_to_onnx(
        model_path=model_path,
        output_path=output_path,
        optimize=True,
        quantize=args.quantize,
    )

    # Test if requested
    if args.test:
        test_onnx_inference(output_path)


if __name__ == "__main__":
    main()
