"""Training script for Seq2Seq Quick Correction Model.

Fine-tunes T5-small for text-to-text correction of dyslexic errors.
The model directly generates corrected text, eliminating the dictionary
lookup bottleneck of the BIO-tagging approach.

Input format (JSONL):
  {"input_text": "correct: I recieved teh letter", "target_text": "I received the letter"}
"""

import argparse
import json
import logging
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import torch
from datasets import Dataset
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    EarlyStoppingCallback,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    TrainerCallback,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration defaults
MODEL_NAME = "google/flan-t5-small"
MAX_INPUT_LENGTH = 128
MAX_TARGET_LENGTH = 128
BATCH_SIZE = 32
LEARNING_RATE = 1e-4  # Lower LR for larger dataset and better convergence
EPOCHS = 12  # More epochs with early stopping for grammar-augmented data
OUTPUT_DIR = Path(__file__).parent / "models" / "quick_correction_seq2seq_v1"


def load_seq2seq_data(data_file: Path) -> list[dict[str, str]]:
    """Load seq2seq training data from JSONL file.

    Args:
        data_file: Path to training data JSONL

    Returns:
        List of training samples with 'input_text' and 'target_text' keys
    """
    samples = []

    with open(data_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            sample = json.loads(line)

            if "input_text" in sample and "target_text" in sample:
                samples.append({
                    "input_text": sample["input_text"],
                    "target_text": sample["target_text"],
                })
            else:
                logger.warning("Skipping sample without 'input_text' or 'target_text' key")

    logger.info(f"Loaded {len(samples)} seq2seq training samples from {data_file}")
    return samples


def prepare_seq2seq_dataset(
    samples: list[dict[str, str]],
    tokenizer: Any,
    max_input_length: int = MAX_INPUT_LENGTH,
    max_target_length: int = MAX_TARGET_LENGTH,
) -> Dataset:
    """Prepare dataset for seq2seq training.

    Args:
        samples: List of training samples with 'input_text' and 'target_text'
        tokenizer: Tokenizer instance
        max_input_length: Maximum input token length
        max_target_length: Maximum target token length

    Returns:
        Prepared HuggingFace Dataset
    """
    examples = {
        "input_text": [s["input_text"] for s in samples],
        "target_text": [s["target_text"] for s in samples],
    }

    dataset = Dataset.from_dict(examples)

    def tokenize_fn(examples: dict[str, Any]) -> dict[str, Any]:
        model_inputs = tokenizer(
            examples["input_text"],
            max_length=max_input_length,
            truncation=True,
            padding=False,
        )

        labels = tokenizer(
            text_target=examples["target_text"],
            max_length=max_target_length,
            truncation=True,
            padding=False,
        )

        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    dataset = dataset.map(
        tokenize_fn,
        batched=True,
        remove_columns=dataset.column_names,
        num_proc=os.cpu_count(),
    )

    return dataset


def compute_metrics(eval_pred: tuple[np.ndarray, np.ndarray], tokenizer: Any) -> dict[str, float]:
    """Compute evaluation metrics for seq2seq.

    Args:
        eval_pred: Tuple of (predictions, labels)
        tokenizer: Tokenizer for decoding predictions

    Returns:
        Dictionary of metrics
    """
    predictions, labels = eval_pred

    # Replace any negative values in predictions with pad token id
    predictions = np.where(predictions >= 0, predictions, tokenizer.pad_token_id)

    # Decode predictions
    decoded_preds = tokenizer.batch_decode(predictions, skip_special_tokens=True)

    # Replace -100 in labels (padding) with pad token id for decoding
    labels = np.where(labels != -100, labels, tokenizer.pad_token_id)
    decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)

    # Exact match accuracy
    exact_matches = sum(
        1 for pred, label in zip(decoded_preds, decoded_labels)
        if pred.strip() == label.strip()
    )
    exact_match = exact_matches / len(decoded_preds) if decoded_preds else 0.0

    # Word Error Rate (WER)
    total_wer = 0.0
    for pred, label in zip(decoded_preds, decoded_labels):
        pred_words = pred.strip().split()
        label_words = label.strip().split()
        total_wer += _word_error_rate(pred_words, label_words)
    avg_wer = total_wer / len(decoded_preds) if decoded_preds else 0.0

    return {
        "exact_match": exact_match,
        "wer": avg_wer,
    }


def _word_error_rate(hypothesis: list[str], reference: list[str]) -> float:
    """Compute word error rate between two word sequences.

    Args:
        hypothesis: Predicted words
        reference: Reference words

    Returns:
        Word error rate (0.0 = perfect, 1.0+ = bad)
    """
    if not reference:
        return 0.0 if not hypothesis else 1.0

    # Levenshtein distance at word level
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
                    d[i - 1][j] + 1,      # deletion
                    d[i][j - 1] + 1,      # insertion
                    d[i - 1][j - 1] + 1,  # substitution
                )

    return d[len(hypothesis)][len(reference)] / len(reference)


class CurriculumCallback(TrainerCallback):
    """Swaps the training dataset at epoch boundaries for curriculum learning.

    Training phases of increasing difficulty:
    - Phase 1 (epochs 1-3): Spelling-only errors
    - Phase 2 (epochs 4-6): Spelling + grammar errors
    - Phase 3 (epochs 7-9): Spelling + grammar + mixed errors
    - Phase 4 (epochs 10+): Full dataset (all types including hard examples)
    """

    def __init__(
        self,
        phase_datasets: dict[int, Dataset],
        phase_boundaries: list[int] | None = None,
    ):
        """Initialize curriculum callback.

        Args:
            phase_datasets: Mapping of phase number (1-4) to prepared Dataset
            phase_boundaries: Epoch boundaries for phase transitions [phase1_end, phase2_end, phase3_end]
        """
        self.phase_datasets = phase_datasets
        self.boundaries = phase_boundaries or [3, 6, 9]
        self.current_phase = 1

    def _get_phase(self, epoch: int) -> int:
        """Determine which phase to use for a given epoch."""
        for i, boundary in enumerate(self.boundaries):
            if epoch < boundary:
                return i + 1
        return len(self.boundaries) + 1

    def on_epoch_begin(self, args, state, control, **kwargs):
        """Swap dataset at epoch boundaries."""
        new_phase = self._get_phase(int(state.epoch))
        if new_phase != self.current_phase and new_phase in self.phase_datasets:
            self.current_phase = new_phase
            trainer = kwargs.get("model", None)
            # The trainer is passed implicitly; we access it through the callback args
            logger.info(
                f"Curriculum: switching to phase {new_phase} "
                f"({len(self.phase_datasets[new_phase])} samples)"
            )


def _load_curriculum_datasets(
    data_dir: Path,
    tokenizer: Any,
    full_train_dataset: Dataset,
) -> dict[int, Dataset] | None:
    """Load curriculum phase datasets if they exist.

    Args:
        data_dir: Directory containing phase files
        tokenizer: Tokenizer for preparing datasets
        full_train_dataset: The full training dataset (used as phase 4)

    Returns:
        Dict mapping phase number to Dataset, or None if no phase files exist
    """
    phase_files = {
        1: data_dir / "train_seq2seq_phase1.jsonl",
        2: data_dir / "train_seq2seq_phase2.jsonl",
        3: data_dir / "train_seq2seq_phase3.jsonl",
    }

    # Check if any phase files exist
    if not any(f.exists() for f in phase_files.values()):
        return None

    phase_datasets: dict[int, Dataset] = {}
    for phase, filepath in phase_files.items():
        if filepath.exists():
            samples = load_seq2seq_data(filepath)
            if samples:
                dataset = prepare_seq2seq_dataset(samples, tokenizer)
                phase_datasets[phase] = dataset
                logger.info(f"Curriculum phase {phase}: {len(dataset)} samples from {filepath.name}")

    # Phase 4 is always the full dataset
    phase_datasets[4] = full_train_dataset
    logger.info(f"Curriculum phase 4 (full): {len(full_train_dataset)} samples")

    return phase_datasets if len(phase_datasets) > 1 else None


def train_seq2seq_model(
    data_dir: Path,
    output_dir: Path = OUTPUT_DIR,
    model_name: str = MODEL_NAME,
    epochs: int = EPOCHS,
    batch_size: int = BATCH_SIZE,
    learning_rate: float = LEARNING_RATE,
    patience: int = 15,
    max_eval_samples: int = 2000,
) -> None:
    """Train the Seq2Seq Quick Correction Model.

    Args:
        data_dir: Directory containing train_seq2seq.jsonl and val_seq2seq.jsonl
        output_dir: Where to save the trained model
        model_name: HuggingFace model name (default: t5-small)
        epochs: Number of training epochs
        batch_size: Training batch size
        learning_rate: Learning rate
        patience: Early stopping patience (in eval steps)
        max_eval_samples: Max eval samples during training (0 = no cap)
    """
    logger.info("Starting Seq2Seq Quick Correction Model training...")
    logger.info(f"  Model: {model_name}")
    logger.info(f"  Epochs: {epochs}")
    logger.info(f"  Batch size: {batch_size}")
    logger.info(f"  Learning rate: {learning_rate}")
    logger.info(f"  Early stopping patience: {patience}")

    # Load tokenizer and model
    logger.info(f"Loading {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    # Load training data
    train_file = data_dir / "train_seq2seq.jsonl"
    val_file = data_dir / "val_seq2seq.jsonl"

    if not train_file.exists():
        logger.error(f"Training data not found at {train_file}")
        return

    train_samples = load_seq2seq_data(train_file)

    # Load or split validation data
    if val_file.exists():
        eval_samples = load_seq2seq_data(val_file)
        logger.info(f"Using separate validation file: {val_file}")
    else:
        split_idx = int(len(train_samples) * 0.9)
        eval_samples = train_samples[split_idx:]
        train_samples = train_samples[:split_idx]

    logger.info(f"Preparing datasets ({len(train_samples)} train, {len(eval_samples)} eval)...")
    train_dataset = prepare_seq2seq_dataset(train_samples, tokenizer)
    eval_dataset = prepare_seq2seq_dataset(eval_samples, tokenizer)

    # Cap eval dataset to speed up training-time validation
    if max_eval_samples > 0 and len(eval_dataset) > max_eval_samples:
        logger.info(f"Capping eval dataset from {len(eval_dataset)} to {max_eval_samples} samples")
        eval_dataset = eval_dataset.shuffle(seed=42).select(range(max_eval_samples))

    # Calculate warmup steps (10% of total)
    steps_per_epoch = math.ceil(len(train_dataset) / batch_size)
    total_steps = steps_per_epoch * epochs
    warmup_steps = int(total_steps * 0.1)

    # Detect accelerator and fp16 support
    use_fp16 = False
    use_cuda = torch.cuda.is_available()
    use_torch_compile = False
    if use_cuda:
        use_fp16 = True
        use_torch_compile = True
        logger.info("CUDA detected, enabling fp16 mixed precision and torch.compile")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        logger.info("Apple MPS detected, enabling GPU acceleration (torch.compile disabled)")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Training arguments
    training_args = Seq2SeqTrainingArguments(
        output_dir=str(output_dir),
        eval_strategy="steps",
        eval_steps=500,
        save_strategy="steps",
        save_steps=500,
        learning_rate=learning_rate,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        num_train_epochs=epochs,
        weight_decay=0.03,
        warmup_steps=warmup_steps,
        lr_scheduler_type="cosine",
        fp16=use_fp16,
        label_smoothing_factor=0.1,
        logging_dir=str(output_dir / "logs"),
        logging_steps=100,
        load_best_model_at_end=True,
        metric_for_best_model="exact_match",
        greater_is_better=True,
        push_to_hub=False,
        save_total_limit=2,
        predict_with_generate=True,
        generation_max_length=96,
        gradient_accumulation_steps=2,
        dataloader_num_workers=4 if use_cuda else 0,
        dataloader_pin_memory=use_cuda,
        torch_compile=use_torch_compile,
    )

    # Data collator
    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
        padding=True,
        max_length=MAX_INPUT_LENGTH,
        label_pad_token_id=-100,
    )

    # Callbacks
    callbacks = [
        EarlyStoppingCallback(early_stopping_patience=patience),
    ]

    # Check for curriculum learning phase datasets
    curriculum_datasets = _load_curriculum_datasets(data_dir, tokenizer, train_dataset)
    if curriculum_datasets:
        logger.info("Curriculum learning ENABLED — training in phases of increasing difficulty")
        curriculum_cb = CurriculumCallback(
            phase_datasets=curriculum_datasets,
            phase_boundaries=[3, 6, 9],
        )
        callbacks.append(curriculum_cb)  # type: ignore[arg-type]
        # Start with phase 1 dataset (spelling-only)
        if 1 in curriculum_datasets:
            train_dataset = curriculum_datasets[1]
            logger.info(f"Starting with phase 1 ({len(train_dataset)} samples)")

    # Build compute_metrics with tokenizer closure
    def metrics_fn(eval_pred: tuple) -> dict[str, float]:
        return compute_metrics(eval_pred, tokenizer)

    # Trainer
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,  # type: ignore[arg-type]
        processing_class=tokenizer,
        data_collator=data_collator,
        compute_metrics=metrics_fn,  # type: ignore[arg-type]
        callbacks=callbacks,  # type: ignore[arg-type]
    )

    # Wire up curriculum dataset swapping through trainer
    if curriculum_datasets:
        original_train_loop = None  # Trainer handles via callback

        def _on_epoch_begin_swap(callback, args, state, control, **kwargs):
            """Swap trainer's train_dataset when curriculum phase changes."""
            new_phase = callback._get_phase(int(state.epoch))
            if new_phase != callback.current_phase and new_phase in callback.phase_datasets:
                callback.current_phase = new_phase
                trainer.train_dataset = callback.phase_datasets[new_phase]
                logger.info(
                    f"Curriculum: switched to phase {new_phase} "
                    f"({len(callback.phase_datasets[new_phase])} samples)"
                )

        # Monkey-patch the callback's on_epoch_begin to swap the dataset
        for cb in callbacks:
            if isinstance(cb, CurriculumCallback):
                cb.on_epoch_begin = lambda args, state, control, _cb=cb, **kw: _on_epoch_begin_swap(_cb, args, state, control, **kw)

    # Train
    logger.info(f"Starting training ({total_steps} total steps, {warmup_steps} warmup)...")
    trainer.train()

    # Evaluate
    logger.info("Evaluating model...")
    eval_results = trainer.evaluate()
    logger.info("Evaluation results:")
    for key, value in sorted(eval_results.items()):
        if isinstance(value, float):
            logger.info(f"  {key}: {value:.4f}")
        else:
            logger.info(f"  {key}: {value}")

    # Save
    logger.info(f"Saving model to {output_dir}...")
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    # Check model size
    model_size = sum(
        f.stat().st_size for f in output_dir.rglob("*") if f.is_file()
    )
    model_size_mb = model_size / (1024 * 1024)
    logger.info(f"Model size: {model_size_mb:.1f} MB")

    logger.info("Seq2Seq training complete!")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Train Seq2Seq Quick Correction Model (FLAN-T5-small)"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Directory containing train_seq2seq.jsonl and val_seq2seq.jsonl",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=MODEL_NAME,
        help=f"HuggingFace model name (default: {MODEL_NAME})",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=EPOCHS,
        help=f"Number of training epochs (default: {EPOCHS})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Training batch size (default: {BATCH_SIZE})",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=LEARNING_RATE,
        help=f"Learning rate (default: {LEARNING_RATE})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory for trained model",
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=15,
        help="Early stopping patience in eval steps (default: 15)",
    )
    parser.add_argument(
        "--max-eval-samples",
        type=int,
        default=2000,
        help="Max eval samples during training, 0 = no cap (default: 2000)",
    )
    return parser.parse_args()


def main():
    """Main training entry point."""
    args = parse_args()

    # Resolve data directory
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        data_dir = Path(__file__).parent / "data"

    train_file = data_dir / "train_seq2seq.jsonl"
    if not train_file.exists():
        logger.error(f"Training data not found at {train_file}")
        logger.info("Run the dataset pipeline first:")
        logger.info("  python ml/quick_correction/train_pipeline.py --all --model-type seq2seq")
        return

    # Resolve output directory
    output_dir = Path(args.output) if args.output else OUTPUT_DIR

    # Train model
    train_seq2seq_model(
        data_dir=data_dir,
        output_dir=output_dir,
        model_name=args.model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        patience=args.patience,
        max_eval_samples=args.max_eval_samples,
    )


if __name__ == "__main__":
    main()
