"""End-to-end training pipeline for Quick Correction Model.

One command to run the full pipeline:
    python ml/quick_correction/train_pipeline.py --all

Or run individual stages:
    python ml/quick_correction/train_pipeline.py --download
    python ml/quick_correction/train_pipeline.py --process
    python ml/quick_correction/train_pipeline.py --combine
    python ml/quick_correction/train_pipeline.py --train
    python ml/quick_correction/train_pipeline.py --evaluate
    python ml/quick_correction/train_pipeline.py --export

Stages: download -> process -> combine -> train -> evaluate -> export
"""

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
ML_DIR = Path(__file__).parent.parent
DATASETS_DIR = ML_DIR / "datasets"
RAW_DIR = DATASETS_DIR / "raw"
PROCESSED_DIR = DATASETS_DIR / "processed"
DATA_DIR = Path(__file__).parent / "data"
MODEL_DIR = Path(__file__).parent / "models" / "quick_correction_base_v1"
ONNX_DIR = ML_DIR / "models" / "quick_correction_base_v1"

# Add project root to path for imports
sys.path.insert(0, str(PROJECT_ROOT))


def stage_download() -> bool:
    """Stage 1: Download real-world datasets."""
    logger.info("=" * 60)
    logger.info("STAGE 1: Download Datasets")
    logger.info("=" * 60)

    from ml.datasets.download_datasets import download_all

    results = download_all(output_dir=RAW_DIR)
    succeeded = sum(1 for v in results.values() if v)
    total = len(results)

    if succeeded == 0:
        logger.error("No datasets downloaded. Check network connectivity.")
        return False

    logger.info(f"Download stage complete: {succeeded}/{total} datasets")
    return True


def stage_process() -> bool:
    """Stage 2: Process downloaded datasets into training format."""
    logger.info("=" * 60)
    logger.info("STAGE 2: Process Datasets")
    logger.info("=" * 60)

    if not RAW_DIR.exists() or not list(RAW_DIR.iterdir()):
        logger.error(f"No raw data found in {RAW_DIR}. Run --download first.")
        return False

    from ml.datasets.process_datasets import process_all

    results = process_all(
        raw_dir=RAW_DIR,
        output_dir=PROCESSED_DIR,
    )
    total = sum(results.values())

    if total == 0:
        logger.error("No samples generated. Check raw data files.")
        return False

    logger.info(f"Processing stage complete: {total} total samples")
    return True


def stage_combine(target_total: int = 80000) -> bool:
    """Stage 3: Combine real and synthetic data into train/val/test splits.

    Args:
        target_total: Target total number of samples
    """
    logger.info("=" * 60)
    logger.info("STAGE 3: Combine Datasets")
    logger.info("=" * 60)

    from ml.datasets.combine_datasets import combine_and_split

    results = combine_and_split(
        processed_dir=PROCESSED_DIR,
        output_dir=DATA_DIR,
        target_total=target_total,
    )
    total = sum(results.values())

    if total == 0:
        logger.error("No combined data generated.")
        return False

    logger.info(f"Combine stage complete: {total} total samples")
    return True


def stage_train(
    model_name: str = "distilbert-base-uncased",
    epochs: int = 5,
    batch_size: int = 32,
    learning_rate: float = 2e-5,
    patience: int = 3,
) -> bool:
    """Stage 4: Fine-tune DistilBERT on the combined dataset.

    Args:
        model_name: HuggingFace model name
        epochs: Number of training epochs
        batch_size: Training batch size
        learning_rate: Learning rate
        patience: Early stopping patience
    """
    logger.info("=" * 60)
    logger.info("STAGE 4: Train Model")
    logger.info("=" * 60)

    train_file = DATA_DIR / "train.jsonl"
    val_file = DATA_DIR / "val.jsonl"

    if not train_file.exists():
        logger.error(f"Training data not found at {train_file}. Run --combine first.")
        return False

    from ml.quick_correction.train import train_model

    train_model(
        data_file=train_file,
        val_file=val_file if val_file.exists() else None,
        output_dir=MODEL_DIR,
        model_name=model_name,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        early_stopping_patience=patience,
    )

    logger.info("Training stage complete")
    return True


def stage_evaluate() -> bool:
    """Stage 5: Evaluate the trained model on held-out test data."""
    logger.info("=" * 60)
    logger.info("STAGE 5: Evaluate Model")
    logger.info("=" * 60)

    if not MODEL_DIR.exists():
        logger.error(f"Trained model not found at {MODEL_DIR}. Run --train first.")
        return False

    test_file = DATA_DIR / "test.jsonl"
    if not test_file.exists():
        logger.error(f"Test data not found at {test_file}. Run --combine first.")
        return False

    from ml.quick_correction.evaluate import evaluate_model

    results = evaluate_model(
        model_dir=MODEL_DIR,
        test_file=test_file,
        output_file=MODEL_DIR / "eval_report.json",
    )

    if not results:
        logger.error("Evaluation failed")
        return False

    logger.info("Evaluation stage complete")
    return True


def stage_export(quantize: bool = False) -> bool:
    """Stage 6: Export trained model to ONNX format.

    Args:
        quantize: Whether to apply INT8 quantization
    """
    logger.info("=" * 60)
    logger.info("STAGE 6: Export to ONNX")
    logger.info("=" * 60)

    if not MODEL_DIR.exists():
        logger.error(f"Trained model not found at {MODEL_DIR}. Run --train first.")
        return False

    from ml.quick_correction.export_onnx import export_to_onnx, test_onnx_inference

    export_to_onnx(
        model_path=MODEL_DIR,
        output_path=ONNX_DIR,
        optimize=True,
        quantize=quantize,
    )

    # Run inference test
    test_onnx_inference(ONNX_DIR)

    # Extract correction dictionary for frontend
    logger.info("Extracting correction dictionary...")
    try:
        from ml.quick_correction.extract_dictionary import extract_dictionary

        dict_path = ONNX_DIR / "correction_dict.json"
        correction_dict = extract_dictionary(raw_dir=RAW_DIR, output_path=dict_path)
        logger.info(f"Correction dictionary: {len(correction_dict)} entries -> {dict_path}")
    except Exception as e:
        logger.warning(f"Dictionary extraction failed (non-fatal): {e}")

    logger.info(f"ONNX model exported to {ONNX_DIR}")
    logger.info("Export stage complete")
    return True


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="End-to-end training pipeline for Quick Correction Model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run everything
  python ml/quick_correction/train_pipeline.py --all

  # Download and process only
  python ml/quick_correction/train_pipeline.py --download --process

  # Train with custom settings
  python ml/quick_correction/train_pipeline.py --train --epochs 10 --batch-size 16

  # Evaluate and export
  python ml/quick_correction/train_pipeline.py --evaluate --export
        """,
    )

    # Stage selection
    stages = parser.add_argument_group("stages")
    stages.add_argument("--all", action="store_true", help="Run all stages")
    stages.add_argument("--download", action="store_true", help="Download datasets")
    stages.add_argument("--process", action="store_true", help="Process datasets")
    stages.add_argument("--combine", action="store_true", help="Combine datasets")
    stages.add_argument("--train", action="store_true", help="Train model")
    stages.add_argument("--evaluate", action="store_true", help="Evaluate model")
    stages.add_argument("--export", action="store_true", help="Export to ONNX")

    # Training parameters
    training = parser.add_argument_group("training parameters")
    training.add_argument(
        "--model-name",
        type=str,
        default="distilbert-base-uncased",
        help="HuggingFace model name (default: distilbert-base-uncased)",
    )
    training.add_argument(
        "--epochs",
        type=int,
        default=5,
        help="Training epochs (default: 5)",
    )
    training.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size (default: 32)",
    )
    training.add_argument(
        "--lr",
        type=float,
        default=2e-5,
        help="Learning rate (default: 2e-5)",
    )
    training.add_argument(
        "--patience",
        type=int,
        default=3,
        help="Early stopping patience (default: 3)",
    )

    # Dataset parameters
    dataset = parser.add_argument_group("dataset parameters")
    dataset.add_argument(
        "--target-samples",
        type=int,
        default=80000,
        help="Target total samples (default: 80000)",
    )

    # Export parameters
    export = parser.add_argument_group("export parameters")
    export.add_argument(
        "--quantize",
        action="store_true",
        help="Apply INT8 quantization during export",
    )

    return parser.parse_args()


def main():
    """Run the training pipeline."""
    args = parse_args()

    # If no stages specified, show help
    stages = [args.download, args.process, args.combine, args.train, args.evaluate, args.export]
    if not args.all and not any(stages):
        logger.info("No stages specified. Use --all to run everything, or specify stages.")
        logger.info("Run with --help for usage information.")
        return

    if args.all:
        args.download = True
        args.process = True
        args.combine = True
        args.train = True
        args.evaluate = True
        args.export = True

    logger.info("Quick Correction Model Training Pipeline")
    logger.info(f"  Project root: {PROJECT_ROOT}")
    logger.info(f"  Raw data: {RAW_DIR}")
    logger.info(f"  Processed data: {PROCESSED_DIR}")
    logger.info(f"  Training data: {DATA_DIR}")
    logger.info(f"  Model output: {MODEL_DIR}")
    logger.info(f"  ONNX output: {ONNX_DIR}")

    # Run stages in order
    stage_results = {}

    if args.download:
        success = stage_download()
        stage_results["download"] = success
        if not success and args.all:
            logger.warning("Download had failures, continuing with available data...")

    if args.process:
        success = stage_process()
        stage_results["process"] = success
        if not success:
            logger.error("Processing failed. Cannot continue.")
            _print_summary(stage_results)
            return

    if args.combine:
        success = stage_combine(target_total=args.target_samples)
        stage_results["combine"] = success
        if not success:
            logger.error("Combination failed. Cannot continue.")
            _print_summary(stage_results)
            return

    if args.train:
        success = stage_train(
            model_name=args.model_name,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.lr,
            patience=args.patience,
        )
        stage_results["train"] = success
        if not success:
            logger.error("Training failed. Cannot continue.")
            _print_summary(stage_results)
            return

    if args.evaluate:
        success = stage_evaluate()
        stage_results["evaluate"] = success

    if args.export:
        success = stage_export(quantize=args.quantize)
        stage_results["export"] = success

    _print_summary(stage_results)


def _print_summary(results: dict[str, bool]) -> None:
    """Print a summary of pipeline stage results."""
    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE SUMMARY")
    logger.info("=" * 60)
    for stage, success in results.items():
        status = "PASS" if success else "FAIL"
        logger.info(f"  {stage:12s}: {status}")

    all_passed = all(results.values())
    logger.info("-" * 60)
    logger.info(f"  Overall: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
