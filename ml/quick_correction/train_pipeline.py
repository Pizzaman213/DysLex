"""End-to-end training pipeline for Quick Correction Model.

One command to run the full pipeline:
    python ml/quick_correction/train_pipeline.py --all

Or run individual stages:
    python ml/quick_correction/train_pipeline.py --download
    python ml/quick_correction/train_pipeline.py --process
    python ml/quick_correction/train_pipeline.py --combine
    python ml/quick_correction/train_pipeline.py --build-tokens
    python ml/quick_correction/train_pipeline.py --train
    python ml/quick_correction/train_pipeline.py --evaluate
    python ml/quick_correction/train_pipeline.py --mine-hard
    python ml/quick_correction/train_pipeline.py --export

Model types:
    --model-type bio       BIO token classification (DistilBERT, default)
    --model-type seq2seq   Seq2seq text correction (T5-small)

Grammar support:
    --grammar              Include grammar error data (seq2seq only)

Accuracy improvements:
    --build-tokens         Build custom dyslexic tokens for tokenizer
    --augment              Enable data augmentation (multi-error + position shuffle)
    --mine-hard            Mine hard examples after training for oversampled retraining

Stages: download -> process -> [grammar] -> combine -> build-tokens -> train -> evaluate -> [mine-hard] -> export
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
SEQ2SEQ_MODEL_DIR = Path(__file__).parent / "models" / "quick_correction_seq2seq_v1"
SEQ2SEQ_ONNX_DIR = ML_DIR / "models" / "quick_correction_seq2seq_v1"

# Add project root to path for imports
sys.path.insert(0, str(PROJECT_ROOT))


def stage_download() -> bool:
    """Stage 1: Download real-world datasets."""
    logger.info("=" * 60)
    logger.info("STAGE 1: Download Datasets")
    logger.info("=" * 60)

    from ml.datasets.download_datasets import download_all  # type: ignore[import-not-found]

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

    from ml.datasets.process_datasets import process_all  # type: ignore[import-not-found]

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

    from ml.datasets.combine_datasets import combine_and_split  # type: ignore[import-not-found]

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
    patience: int = 10,
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


def stage_expand_corpus() -> bool:
    """Stage: Expand the sentence corpus with Tatoeba and Simple Wikipedia."""
    logger.info("=" * 60)
    logger.info("STAGE: Expand Sentence Corpus")
    logger.info("=" * 60)

    from ml.datasets.download_sentences import build_expanded_corpus

    corpus = build_expanded_corpus(target_total=30000)

    if len(corpus) < 5000:
        logger.warning(f"Corpus expansion produced only {len(corpus)} sentences (expected 20K+)")
        logger.info("Will continue with existing corpus.")
        return True  # Non-fatal

    logger.info(f"Corpus expansion complete: {len(corpus)} sentences")
    return True


def stage_generate_grammar(target_samples: int = 50000) -> bool:
    """Stage: Generate synthetic grammar error training data."""
    logger.info("=" * 60)
    logger.info("STAGE: Generate Grammar Training Data")
    logger.info("=" * 60)

    from ml.synthetic_data.grammar_generator import GrammarErrorGenerator

    generator = GrammarErrorGenerator()
    output_file = PROCESSED_DIR / "grammar_synthetic_seq2seq.jsonl"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    samples = generator.generate_training_pairs(
        num_samples=target_samples,
        output_file=output_file,
    )

    if not samples:
        logger.error("No grammar samples generated.")
        return False

    logger.info(f"Grammar generation complete: {len(samples)} samples -> {output_file}")
    return True


def stage_generate_mixed(target_samples: int = 75000) -> bool:
    """Stage: Generate mixed spelling+grammar error training data.

    Generates two types:
    - Simple mixed (1 spelling + 1 grammar error): 25K samples
    - Multi-error (2-4 errors, including long-sentence samples): 50K samples
    """
    logger.info("=" * 60)
    logger.info("STAGE: Generate Mixed (Spelling+Grammar) Training Data")
    logger.info("=" * 60)

    from ml.synthetic_data.generator import SyntheticDataGenerator

    generator = SyntheticDataGenerator()
    output_file = PROCESSED_DIR / "mixed_synthetic_seq2seq.jsonl"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Simple mixed: 1/3 of target
    simple_count = target_samples // 3
    samples = generator.generate_mixed_training_pairs(
        num_samples=simple_count,
        output_file=None,  # Don't write yet
    )
    logger.info(f"Simple mixed: {len(samples)} samples")

    # Multi-error: 2/3 of target
    multi_count = target_samples - simple_count
    multi_samples = generator.generate_multi_error_training_pairs(
        num_samples=multi_count,
        output_file=None,  # Don't write yet
    )
    logger.info(f"Multi-error mixed: {len(multi_samples)} samples")

    # Combine and write
    import json
    import random
    all_samples = samples + multi_samples
    random.shuffle(all_samples)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        for sample in all_samples:
            f.write(json.dumps(sample) + "\n")

    logger.info(f"Mixed generation complete: {len(all_samples)} samples -> {output_file}")
    return bool(all_samples)


def stage_process_gec() -> bool:
    """Stage: Process GEC datasets (JFLEG, W&I+LOCNESS) into seq2seq format."""
    logger.info("=" * 60)
    logger.info("STAGE: Process GEC Datasets")
    logger.info("=" * 60)

    from ml.datasets.process_gec_datasets import process_gec_data

    results = process_gec_data(
        raw_dir=RAW_DIR,
        output_dir=PROCESSED_DIR,
    )
    total = sum(results.values())

    if total == 0:
        logger.warning("No GEC datasets found. This is expected if JFLEG/W&I data hasn't been downloaded.")
        logger.info("Grammar training will use synthetic data only.")
        return True  # Not a failure — GEC data is optional

    logger.info(f"GEC processing complete: {total} samples from {len(results)} sources")
    return True


def stage_process_seq2seq() -> bool:
    """Stage 2 (seq2seq): Process downloaded datasets into seq2seq training format."""
    logger.info("=" * 60)
    logger.info("STAGE 2: Process Datasets (seq2seq)")
    logger.info("=" * 60)

    if not RAW_DIR.exists() or not list(RAW_DIR.iterdir()):
        logger.error(f"No raw data found in {RAW_DIR}. Run --download first.")
        return False

    from ml.datasets.process_datasets import process_all_seq2seq  # type: ignore[import-not-found]

    results = process_all_seq2seq(
        raw_dir=RAW_DIR,
        output_dir=PROCESSED_DIR,
    )
    total = sum(results.values())

    if total == 0:
        logger.error("No seq2seq samples generated. Check raw data files.")
        return False

    logger.info(f"Seq2seq processing stage complete: {total} total samples")
    return True


def stage_combine_seq2seq(
    target_total: int = 80000,
    include_grammar: bool = False,
    augment: bool = False,
) -> bool:
    """Stage 3 (seq2seq): Combine real and synthetic data into seq2seq train/val/test splits.

    Args:
        target_total: Target total number of samples
        include_grammar: Whether to include grammar data in the mix
        augment: Whether to apply data augmentation
    """
    logger.info("=" * 60)
    logger.info("STAGE 3: Combine Datasets (seq2seq)")
    if include_grammar:
        logger.info("  (Including grammar data)")
    if augment:
        logger.info("  (Data augmentation: ENABLED)")
    logger.info("=" * 60)

    from ml.datasets.combine_datasets import combine_and_split_seq2seq  # type: ignore[import-not-found]

    results = combine_and_split_seq2seq(
        processed_dir=PROCESSED_DIR,
        output_dir=DATA_DIR,
        target_total=target_total,
        augment=augment,
    )
    total = sum(results.values())

    if total == 0:
        logger.error("No combined seq2seq data generated.")
        return False

    logger.info(f"Seq2seq combine stage complete: {total} total samples")
    return True


def stage_train_seq2seq(
    model_name: str = "google/flan-t5-base",
    epochs: int = 20,
    batch_size: int = 16,
    learning_rate: float = 5e-5,
    patience: int = 25,
    max_eval_samples: int = 0,
) -> bool:
    """Stage 4 (seq2seq): Fine-tune FLAN-T5-base on the combined seq2seq dataset."""
    logger.info("=" * 60)
    logger.info("STAGE 4: Train Seq2Seq Model")
    logger.info("=" * 60)

    train_file = DATA_DIR / "train_seq2seq.jsonl"
    if not train_file.exists():
        logger.error(f"Seq2seq training data not found at {train_file}. Run --combine first.")
        return False

    from ml.quick_correction.train_seq2seq import train_seq2seq_model

    train_seq2seq_model(
        data_dir=DATA_DIR,
        output_dir=SEQ2SEQ_MODEL_DIR,
        model_name=model_name,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        patience=patience,
        max_eval_samples=max_eval_samples,
    )

    logger.info("Seq2seq training stage complete")
    return True


def stage_evaluate_seq2seq(gate: bool = False) -> bool:
    """Stage 5 (seq2seq): Evaluate the trained seq2seq model on held-out test data.

    Args:
        gate: If True, fail pipeline if quality thresholds are not met
    """
    logger.info("=" * 60)
    logger.info("STAGE 5: Evaluate Seq2Seq Model")
    if gate:
        logger.info("  (Regression gate: ENABLED)")
    logger.info("=" * 60)

    if not SEQ2SEQ_MODEL_DIR.exists():
        logger.error(f"Trained seq2seq model not found at {SEQ2SEQ_MODEL_DIR}. Run --train first.")
        return False

    test_file = DATA_DIR / "test_seq2seq.jsonl"
    if not test_file.exists():
        logger.error(f"Seq2seq test data not found at {test_file}. Run --combine first.")
        return False

    # Check for grammar/spelling-specific test files
    spelling_test = DATA_DIR / "test_seq2seq_spelling.jsonl"
    grammar_test = DATA_DIR / "test_seq2seq_grammar.jsonl"

    from ml.quick_correction.evaluate_seq2seq import evaluate_seq2seq_model

    results = evaluate_seq2seq_model(
        model_dir=SEQ2SEQ_MODEL_DIR,
        test_file=test_file,
        output_file=SEQ2SEQ_MODEL_DIR / "eval_report.json",
        spelling_test_file=spelling_test if spelling_test.exists() else None,
        grammar_test_file=grammar_test if grammar_test.exists() else None,
        gate=gate,
    )

    if not results:
        logger.error("Seq2seq evaluation failed")
        return False

    if gate and not results.get("gate_passed", True):
        logger.error("Seq2seq evaluation: REGRESSION GATE FAILED")
        return False

    logger.info("Seq2seq evaluation stage complete")
    return True


def stage_export_seq2seq(quantize: bool = True) -> bool:
    """Stage 6 (seq2seq): Export trained seq2seq model to ONNX format.

    Args:
        quantize: Whether to apply INT8 quantization (default: True)
    """
    logger.info("=" * 60)
    logger.info("STAGE 6: Export Seq2Seq to ONNX")
    logger.info("=" * 60)

    if not SEQ2SEQ_MODEL_DIR.exists():
        logger.error(f"Trained seq2seq model not found at {SEQ2SEQ_MODEL_DIR}. Run --train first.")
        return False

    from ml.quick_correction.export_onnx_seq2seq import (
        export_seq2seq_to_onnx,
        test_onnx_seq2seq_inference,
    )

    export_seq2seq_to_onnx(
        model_path=SEQ2SEQ_MODEL_DIR,
        output_path=SEQ2SEQ_ONNX_DIR,
        quantize=quantize,
    )

    # Run inference test
    test_onnx_seq2seq_inference(SEQ2SEQ_ONNX_DIR)

    logger.info(f"Seq2seq ONNX model exported to {SEQ2SEQ_ONNX_DIR}")
    logger.info("Seq2seq export stage complete")
    return True


def stage_build_custom_tokens() -> bool:
    """Stage: Build custom dyslexic token list for tokenizer expansion."""
    logger.info("=" * 60)
    logger.info("STAGE: Build Custom Dyslexic Tokens")
    logger.info("=" * 60)

    from ml.quick_correction.build_custom_tokens import build_custom_tokens

    result = build_custom_tokens(verbose=True)

    if not result:
        logger.error("Failed to build custom token list")
        return False

    logger.info(f"Custom tokens: {result.get('token_count', 0)} tokens ready")
    return True


def stage_mine_hard_examples(max_samples: int = 0) -> bool:
    """Stage: Mine hard examples from training data for oversampled retraining.

    Args:
        max_samples: Max training samples to evaluate (0 = all)
    """
    logger.info("=" * 60)
    logger.info("STAGE: Mine Hard Examples")
    logger.info("=" * 60)

    if not SEQ2SEQ_MODEL_DIR.exists():
        logger.error(f"Trained model not found at {SEQ2SEQ_MODEL_DIR}. Run --train first.")
        return False

    train_file = DATA_DIR / "train_seq2seq.jsonl"
    if not train_file.exists():
        logger.error(f"Training data not found at {train_file}. Run --combine first.")
        return False

    from ml.quick_correction.mine_hard_examples import mine_hard_examples

    stats = mine_hard_examples(
        model_dir=SEQ2SEQ_MODEL_DIR,
        train_file=train_file,
        output_file=DATA_DIR / "hard_examples_seq2seq.jsonl",
        max_samples=max_samples,
        verbose=True,
    )

    if not stats:
        logger.error("Hard example mining failed")
        return False

    logger.info(
        f"Mined {stats.get('total_wrong', 0)} hard examples "
        f"(oversampled to {stats.get('oversampled_count', 0)})"
    )
    return True


def stage_download_dyslexia() -> bool:
    """Stage: Download dyslexia-specific datasets (Pedler, DysList).

    Downloads and processes:
    - Pedler confused word sets (real-word confusion from dyslexic writing)
    - DysList error taxonomy patterns (Rello & Baeza-Yates 2014)
    """
    logger.info("=" * 60)
    logger.info("STAGE: Download Dyslexia-Specific Datasets")
    logger.info("=" * 60)

    from ml.datasets.download_dyslexia_datasets import download_all

    results = download_all(output_dir=RAW_DIR)
    succeeded = sum(1 for v in results.values() if v)
    total = len(results)

    if succeeded == 0:
        logger.error("No dyslexia datasets downloaded/generated.")
        return False

    logger.info(f"Dyslexia dataset stage complete: {succeeded}/{total} succeeded")
    return True


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="End-to-end training pipeline for Quick Correction Model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run everything (BIO model, default)
  python ml/quick_correction/train_pipeline.py --all

  # Run everything (seq2seq T5 model)
  python ml/quick_correction/train_pipeline.py --all --model-type seq2seq

  # Run everything with grammar support (seq2seq + grammar errors)
  python ml/quick_correction/train_pipeline.py --all --model-type seq2seq --grammar

  # Download and process only
  python ml/quick_correction/train_pipeline.py --download --process

  # Train with custom settings
  python ml/quick_correction/train_pipeline.py --train --epochs 10 --batch-size 16

  # Evaluate and export
  python ml/quick_correction/train_pipeline.py --evaluate --export
        """,
    )

    # Model type selection
    parser.add_argument(
        "--model-type",
        type=str,
        choices=["bio", "seq2seq"],
        default="bio",
        help="Model architecture: 'bio' (DistilBERT token classifier, default) or 'seq2seq' (T5 text-to-text)",
    )

    # Stage selection
    stages = parser.add_argument_group("stages")
    stages.add_argument("--all", action="store_true", help="Run all stages")
    stages.add_argument("--download", action="store_true", help="Download datasets")
    stages.add_argument("--download-dyslexia", action="store_true", help="Download dyslexia-specific datasets (Pedler, DysList)")
    stages.add_argument("--process", action="store_true", help="Process datasets")
    stages.add_argument("--combine", action="store_true", help="Combine datasets")
    stages.add_argument("--train", action="store_true", help="Train model")
    stages.add_argument("--evaluate", action="store_true", help="Evaluate model")
    stages.add_argument("--export", action="store_true", help="Export to ONNX")
    stages.add_argument("--build-tokens", action="store_true", help="Build custom dyslexic token list for tokenizer")
    stages.add_argument("--mine-hard", action="store_true", help="Mine hard examples after training for oversampled retraining")

    # Grammar support
    grammar = parser.add_argument_group("grammar")
    grammar.add_argument(
        "--grammar",
        action="store_true",
        help="Include grammar error data in training (seq2seq only). "
             "Generates synthetic grammar errors, processes GEC datasets, "
             "and mixes them with spelling data.",
    )

    # Data augmentation
    augmentation = parser.add_argument_group("data augmentation")
    augmentation.add_argument(
        "--augment",
        action="store_true",
        help="Enable data augmentation during combine (multi-error injection + position shuffling)",
    )

    # Quality gates
    quality = parser.add_argument_group("quality gates")
    quality.add_argument(
        "--gate",
        action="store_true",
        help="Enable regression gate: fail pipeline if spelling < 95%%, "
             "grammar < 85%%, or P95 latency > 200ms",
    )

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
        default=25,
        help="Early stopping patience in eval steps (default: 25)",
    )

    # Dataset parameters
    dataset = parser.add_argument_group("dataset parameters")
    dataset.add_argument(
        "--target-samples",
        type=int,
        default=80000,
        help="Target total samples (default: 80000)",
    )
    dataset.add_argument(
        "--max-eval-samples",
        type=int,
        default=0,
        help="Max eval samples during training, 0 = no cap (default: 0)",
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
    download_dyslexia = getattr(args, "download_dyslexia", False)
    build_tokens = getattr(args, "build_tokens", False)
    mine_hard = getattr(args, "mine_hard", False)
    stages = [
        args.download, download_dyslexia, args.process, args.combine,
        args.train, args.evaluate, args.export, build_tokens, mine_hard,
    ]
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
        download_dyslexia = True  # Always include dyslexia datasets in --all
        build_tokens = True  # Build custom tokens in --all flow

    is_seq2seq = args.model_type == "seq2seq"
    include_grammar = args.grammar
    model_type_label = "Seq2Seq (T5)" if is_seq2seq else "BIO (DistilBERT)"

    if include_grammar and not is_seq2seq:
        logger.warning("--grammar flag requires --model-type seq2seq. Ignoring grammar flag.")
        include_grammar = False

    logger.info(f"Quick Correction Model Training Pipeline [{model_type_label}]")
    if include_grammar:
        logger.info("  Grammar support: ENABLED")
    logger.info(f"  Project root: {PROJECT_ROOT}")
    logger.info(f"  Raw data: {RAW_DIR}")
    logger.info(f"  Processed data: {PROCESSED_DIR}")
    logger.info(f"  Training data: {DATA_DIR}")
    if is_seq2seq:
        logger.info(f"  Model output: {SEQ2SEQ_MODEL_DIR}")
        logger.info(f"  ONNX output: {SEQ2SEQ_ONNX_DIR}")
    else:
        logger.info(f"  Model output: {MODEL_DIR}")
        logger.info(f"  ONNX output: {ONNX_DIR}")

    # Run stages in order
    stage_results = {}

    if args.download:
        success = stage_download()
        stage_results["download"] = success
        if not success and args.all:
            logger.warning("Download had failures, continuing with available data...")

    if download_dyslexia:
        success = stage_download_dyslexia()
        stage_results["download_dyslexia"] = success
        if not success:
            logger.warning("Dyslexia dataset download had failures, continuing...")

    if args.process:
        if is_seq2seq:
            success = stage_process_seq2seq()
        else:
            success = stage_process()
        stage_results["process"] = success
        if not success:
            logger.error("Processing failed. Cannot continue.")
            _print_summary(stage_results)
            return

    # Grammar-specific stages (run after process, before combine)
    if include_grammar and (args.process or args.all):
        # Expand sentence corpus before generating synthetic data
        success = stage_expand_corpus()
        stage_results["expand_corpus"] = success

        # Generate synthetic grammar errors
        success = stage_generate_grammar(target_samples=50000)
        stage_results["generate_grammar"] = success

        # Generate mixed spelling+grammar errors (now 75K)
        success = stage_generate_mixed(target_samples=75000)
        stage_results["generate_mixed"] = success

        # Process real GEC datasets if available
        success = stage_process_gec()
        stage_results["process_gec"] = success

    if args.combine:
        if is_seq2seq:
            target = args.target_samples
            if include_grammar and target == 80000:
                target = 180000  # Larger target to accommodate expanded mixed data
            success = stage_combine_seq2seq(
                target_total=target,
                include_grammar=include_grammar,
                augment=args.augment,
            )
        else:
            success = stage_combine(target_total=args.target_samples)
        stage_results["combine"] = success
        if not success:
            logger.error("Combination failed. Cannot continue.")
            _print_summary(stage_results)
            return

    # Build custom tokens (after combine, before train)
    if build_tokens and is_seq2seq:
        success = stage_build_custom_tokens()
        stage_results["build_tokens"] = success
        if not success:
            logger.warning("Custom token building failed, continuing without custom tokens...")

    if args.train:
        if is_seq2seq:
            # Use seq2seq defaults if user didn't override
            model_name = args.model_name if args.model_name != "distilbert-base-uncased" else "google/flan-t5-base"
            # Use lower LR for flan-t5-base
            default_lr = 5e-5
            lr = args.lr if args.lr != 2e-5 else default_lr
            # More epochs with early stopping
            epochs = args.epochs if args.epochs != 5 else 20
            success = stage_train_seq2seq(
                model_name=model_name,
                epochs=epochs,
                batch_size=args.batch_size,
                learning_rate=lr,
                patience=args.patience,
                max_eval_samples=args.max_eval_samples,
            )
        else:
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
        if is_seq2seq:
            success = stage_evaluate_seq2seq(gate=args.gate)
        else:
            success = stage_evaluate()
        stage_results["evaluate"] = success

    # Mine hard examples (after evaluate, before optional retrain)
    if mine_hard and is_seq2seq:
        success = stage_mine_hard_examples()
        stage_results["mine_hard"] = success
        if not success:
            logger.warning("Hard example mining failed, continuing...")

    if args.export:
        if is_seq2seq:
            # Seq2seq uses INT8 quantization by default; --quantize flag is
            # shared with BIO but for seq2seq it's always on
            success = stage_export_seq2seq(quantize=True)
        else:
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
