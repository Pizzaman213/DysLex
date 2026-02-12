"""Training script for Quick Correction Model.

Fine-tunes DistilBERT for token classification to detect and correct
dyslexic errors. Target: >85% accuracy, <150MB model size, <50ms inference.

Supports both labels format (from dataset pipeline) and corrections format
(from synthetic generator). Use CLI args to customize training.
"""

import argparse
import json
import logging
import math
import os
import re
from pathlib import Path
from typing import Any

import numpy as np
import torch
from datasets import Dataset
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration defaults
MODEL_NAME = "distilbert-base-uncased"
MAX_SEQ_LENGTH = 128
BATCH_SIZE = 32
LEARNING_RATE = 2e-5
EPOCHS = 5
OUTPUT_DIR = Path(__file__).parent / "models" / "quick_correction_base_v1"

# Label mapping
LABEL_MAP = {
    "O": 0,  # No error
    "B-ERROR": 1,  # Beginning of error
    "I-ERROR": 2,  # Inside error
}
ID_TO_LABEL = {v: k for k, v in LABEL_MAP.items()}


def convert_corrections_to_labels(sample: dict[str, Any]) -> dict[str, Any]:
    """Convert corrections format to labels format.

    The synthetic generator produces:
      {"text": "...", "clean_text": "...", "corrections": [{"start": ..., "end": ..., ...}]}

    Training expects:
      {"text": "...", "labels": [0, 1, 0, ...]}

    Args:
        sample: Sample in corrections format

    Returns:
        Sample in labels format
    """
    text = sample["text"]
    corrections = sample.get("corrections", [])
    words = text.split()

    labels = [0] * len(words)

    # Map character positions to word indices
    word_starts = []
    pos = 0
    for word in words:
        word_starts.append(pos)
        pos += len(word) + 1

    for correction in corrections:
        start = correction["start"]
        end = correction["end"]

        for i, word_start in enumerate(word_starts):
            word_end = word_start + len(words[i])
            if start < word_end and end > word_start:
                labels[i] = 1  # B-ERROR

    return {
        "text": text,
        "labels": labels,
    }


def load_training_data(data_file: Path) -> list[dict[str, Any]]:
    """Load training data from JSONL file.

    Auto-detects format: if samples have 'labels', use directly.
    If samples have 'corrections', convert to labels format.

    Args:
        data_file: Path to training data JSONL

    Returns:
        List of training samples with 'text' and 'labels' keys
    """
    samples = []
    corrections_count = 0
    labels_count = 0

    with open(data_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            sample = json.loads(line)

            if "labels" in sample:
                samples.append({"text": sample["text"], "labels": sample["labels"]})
                labels_count += 1
            elif "corrections" in sample:
                converted = convert_corrections_to_labels(sample)
                samples.append(converted)
                corrections_count += 1
            else:
                logger.warning(f"Skipping sample without 'labels' or 'corrections' key")

    logger.info(
        f"Loaded {len(samples)} training samples "
        f"({labels_count} labels format, {corrections_count} corrections format)"
    )
    return samples


def align_labels_with_tokens(
    labels: list[int], word_ids: list[int | None]
) -> list[int]:
    """Align labels with tokenized words.

    Args:
        labels: Word-level labels
        word_ids: Word IDs for each token

    Returns:
        Token-level labels
    """
    aligned_labels = []
    previous_word_id = None

    for word_id in word_ids:
        if word_id is None:
            # Special tokens get -100 (ignored in loss)
            aligned_labels.append(-100)
        elif word_id != previous_word_id:
            # First token of word gets the label
            if word_id < len(labels):
                aligned_labels.append(labels[word_id])
            else:
                aligned_labels.append(0)
        else:
            # Continuation tokens get I-ERROR or O
            if word_id < len(labels):
                aligned_labels.append(labels[word_id] if labels[word_id] != 0 else -100)
            else:
                aligned_labels.append(-100)

        previous_word_id = word_id

    return aligned_labels


def prepare_dataset(samples: list[dict[str, Any]], tokenizer: Any) -> Dataset:
    """Prepare dataset for training.

    Args:
        samples: List of training samples with 'text' and 'labels' keys
        tokenizer: Tokenizer instance

    Returns:
        Prepared HuggingFace Dataset
    """
    examples = {"text": [], "labels": []}

    for sample in samples:
        examples["text"].append(sample["text"])
        examples["labels"].append(sample["labels"])

    dataset = Dataset.from_dict(examples)

    def tokenize_and_align(examples: dict[str, Any]) -> dict[str, Any]:
        tokenized = tokenizer(
            examples["text"],
            truncation=True,
            padding=False,
            max_length=MAX_SEQ_LENGTH,
            is_split_into_words=False,
        )

        aligned_labels = []
        for i, labels in enumerate(examples["labels"]):
            word_ids = tokenized.word_ids(batch_index=i)
            aligned_labels.append(align_labels_with_tokens(labels, word_ids))

        tokenized["labels"] = aligned_labels
        return tokenized

    dataset = dataset.map(
        tokenize_and_align,
        batched=True,
        remove_columns=dataset.column_names,
        num_proc=os.cpu_count(),
    )

    return dataset


def compute_metrics(eval_pred: tuple[np.ndarray, np.ndarray]) -> dict[str, float]:
    """Compute evaluation metrics including per-class precision/recall.

    Args:
        eval_pred: Tuple of (predictions, labels)

    Returns:
        Dictionary of metrics
    """
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=2)

    # Remove ignored tokens (-100)
    true_predictions = []
    true_labels = []

    for prediction, label in zip(predictions, labels):
        for pred, lbl in zip(prediction, label):
            if lbl != -100:
                true_predictions.append(pred)
                true_labels.append(lbl)

    true_predictions = np.array(true_predictions)
    true_labels = np.array(true_labels)

    # Overall accuracy
    total = len(true_predictions)
    accuracy = (true_predictions == true_labels).sum() / total if total > 0 else 0

    # B-ERROR (class 1) metrics
    b_error_true = (true_labels == 1).sum()
    b_error_pred = (true_predictions == 1).sum()
    b_error_correct = ((true_predictions == 1) & (true_labels == 1)).sum()

    b_precision = b_error_correct / b_error_pred if b_error_pred > 0 else 0
    b_recall = b_error_correct / b_error_true if b_error_true > 0 else 0
    b_f1 = 2 * b_precision * b_recall / (b_precision + b_recall) if (b_precision + b_recall) > 0 else 0

    # Any-error metrics (B-ERROR or I-ERROR)
    error_true = (true_labels != 0).sum()
    error_pred = (true_predictions != 0).sum()
    error_correct = ((true_predictions != 0) & (true_labels != 0)).sum()

    precision = error_correct / error_pred if error_pred > 0 else 0
    recall = error_correct / error_true if error_true > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "b_error_precision": float(b_precision),
        "b_error_recall": float(b_recall),
        "b_error_f1": float(b_f1),
    }


def train_model(
    data_file: Path,
    val_file: Path | None = None,
    output_dir: Path = OUTPUT_DIR,
    model_name: str = MODEL_NAME,
    epochs: int = EPOCHS,
    batch_size: int = BATCH_SIZE,
    learning_rate: float = LEARNING_RATE,
    early_stopping_patience: int = 10,
) -> None:
    """Train the Quick Correction Model.

    Args:
        data_file: Path to training data JSONL
        val_file: Path to validation data JSONL (if None, splits from train)
        output_dir: Where to save the trained model
        model_name: HuggingFace model name
        epochs: Number of training epochs
        batch_size: Training batch size
        learning_rate: Learning rate
        early_stopping_patience: Stop after N eval steps without improvement
    """
    logger.info("Starting Quick Correction Model training...")
    logger.info(f"  Model: {model_name}")
    logger.info(f"  Epochs: {epochs}")
    logger.info(f"  Batch size: {batch_size}")
    logger.info(f"  Learning rate: {learning_rate}")
    logger.info(f"  Early stopping patience: {early_stopping_patience}")

    # Load tokenizer and model
    logger.info(f"Loading {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForTokenClassification.from_pretrained(
        model_name,
        num_labels=len(LABEL_MAP),
        id2label=ID_TO_LABEL,
        label2id=LABEL_MAP,
    )

    # Load training data
    train_samples = load_training_data(data_file)

    # Load or split validation data
    if val_file and val_file.exists():
        eval_samples = load_training_data(val_file)
        logger.info(f"Using separate validation file: {val_file}")
    else:
        split_idx = int(len(train_samples) * 0.9)
        eval_samples = train_samples[split_idx:]
        train_samples = train_samples[:split_idx]

    logger.info(f"Preparing datasets ({len(train_samples)} train, {len(eval_samples)} eval)...")
    train_dataset = prepare_dataset(train_samples, tokenizer)
    eval_dataset = prepare_dataset(eval_samples, tokenizer)

    # Calculate warmup steps (10% of total)
    steps_per_epoch = math.ceil(len(train_dataset) / batch_size)
    total_steps = steps_per_epoch * epochs
    warmup_steps = int(total_steps * 0.1)

    # Detect accelerator and fp16 support
    use_fp16 = False
    use_cuda = torch.cuda.is_available()
    if use_cuda:
        use_fp16 = True
        logger.info("CUDA detected, enabling fp16 mixed precision")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        logger.info("Apple MPS detected, enabling GPU acceleration")

    # Training arguments
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        eval_strategy="steps",
        eval_steps=500,
        save_strategy="steps",
        save_steps=500,
        learning_rate=learning_rate,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        num_train_epochs=epochs,
        weight_decay=0.01,
        warmup_steps=warmup_steps,
        lr_scheduler_type="cosine",
        fp16=use_fp16,
        logging_dir=str(output_dir / "logs"),
        logging_steps=100,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        push_to_hub=False,
        save_total_limit=2,
        gradient_accumulation_steps=2,
        dataloader_num_workers=4 if use_cuda else 0,
        dataloader_pin_memory=use_cuda,
        torch_compile=True,
    )

    # Data collator
    data_collator = DataCollatorForTokenClassification(
        tokenizer=tokenizer,
        padding=True,
        max_length=MAX_SEQ_LENGTH,
    )

    # Callbacks
    callbacks = [
        EarlyStoppingCallback(early_stopping_patience=early_stopping_patience),
    ]

    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,  # type: ignore[arg-type]
        callbacks=callbacks,  # type: ignore[arg-type]
    )

    # Train
    logger.info(f"Starting training ({total_steps} total steps, {warmup_steps} warmup)...")
    trainer.train()

    # Evaluate
    logger.info("Evaluating model...")
    eval_results = trainer.evaluate()
    logger.info(f"Evaluation results:")
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

    if model_size_mb > 150:
        logger.warning(f"Model size ({model_size_mb:.1f} MB) exceeds target of 150 MB")

    logger.info("Training complete!")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Train Quick Correction Model (DistilBERT for token classification)"
    )
    parser.add_argument(
        "--data",
        type=str,
        default=None,
        help="Path to training data JSONL (default: ml/quick_correction/data/train.jsonl)",
    )
    parser.add_argument(
        "--val",
        type=str,
        default=None,
        help="Path to validation data JSONL (if not provided, splits from train)",
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
        default=10,
        help="Early stopping patience in eval steps (default: 10)",
    )
    return parser.parse_args()


def main():
    """Main training entry point."""
    args = parse_args()

    # Resolve data file
    if args.data:
        data_file = Path(args.data)
    else:
        data_file = Path(__file__).parent / "data" / "train.jsonl"

    if not data_file.exists():
        logger.error(f"Training data not found at {data_file}")
        logger.info("Run the dataset pipeline first:")
        logger.info("  python ml/quick_correction/train_pipeline.py --download --process --combine")
        logger.info("Or generate synthetic data:")
        logger.info("  python ml/synthetic_data/generator.py")
        return

    # Resolve validation file
    val_file = Path(args.val) if args.val else None
    if val_file is None:
        # Check for val.jsonl alongside train.jsonl
        default_val = data_file.parent / "val.jsonl"
        if default_val.exists():
            val_file = default_val

    # Resolve output directory
    output_dir = Path(args.output) if args.output else OUTPUT_DIR

    # Train model
    train_model(
        data_file=data_file,
        val_file=val_file,
        output_dir=output_dir,
        model_name=args.model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        early_stopping_patience=args.patience,
    )


if __name__ == "__main__":
    main()
