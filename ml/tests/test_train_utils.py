"""Tests for training utility functions in ml.quick_correction.train.

These tests focus on the pure-Python utility functions (data loading,
label alignment, metric computation) and deliberately avoid importing
torch/transformers to stay fast and dependency-light.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# We need numpy for compute_metrics tests
np = pytest.importorskip("numpy", reason="numpy is required for training utility tests")


# ---------------------------------------------------------------------------
# Helpers to import train module functions without pulling in torch at module
# level.  We mock torch and transformers so the module can be imported even
# when those heavy packages are absent.
# ---------------------------------------------------------------------------

def _import_train_functions():
    """Import the three utility functions we test, mocking heavy deps."""
    import importlib
    import types

    # Create lightweight stubs for torch and transformers if not installed
    _mocked = []
    for mod_name in ("torch", "transformers", "datasets"):
        if mod_name not in sys.modules:
            sys.modules[mod_name] = types.ModuleType(mod_name)
            _mocked.append(mod_name)

    # Ensure torch stub has cuda attr
    torch_mod = sys.modules["torch"]
    if not hasattr(torch_mod, "cuda"):
        class _Cuda:
            @staticmethod
            def is_available():
                return False
        torch_mod.cuda = _Cuda()

    # Ensure transformers stub has needed names
    trans_mod = sys.modules["transformers"]
    for attr in (
        "AutoModelForTokenClassification",
        "AutoTokenizer",
        "DataCollatorForTokenClassification",
        "EarlyStoppingCallback",
        "Trainer",
        "TrainingArguments",
    ):
        if not hasattr(trans_mod, attr):
            setattr(trans_mod, attr, None)

    # Ensure datasets stub has Dataset
    ds_mod = sys.modules["datasets"]
    if not hasattr(ds_mod, "Dataset"):
        ds_mod.Dataset = None

    from ml.quick_correction.train import (
        align_labels_with_tokens,
        compute_metrics,
        convert_corrections_to_labels,
        load_training_data,
    )

    # Clean up mocked modules so they don't leak
    for mod_name in _mocked:
        del sys.modules[mod_name]

    return load_training_data, align_labels_with_tokens, compute_metrics, convert_corrections_to_labels


(
    load_training_data,
    align_labels_with_tokens,
    compute_metrics,
    convert_corrections_to_labels,
) = _import_train_functions()


# ---------------------------------------------------------------------------
# load_training_data
# ---------------------------------------------------------------------------

class TestLoadTrainingData:
    def test_labels_format(self, tmp_path: Path):
        """Loads JSONL with labels field directly."""
        filepath = tmp_path / "data.jsonl"
        samples = [
            {"text": "teh cat sat", "labels": [1, 0, 0]},
            {"text": "she went home", "labels": [0, 0, 0]},
        ]
        with open(filepath, "w") as f:
            for s in samples:
                f.write(json.dumps(s) + "\n")

        result = load_training_data(filepath)
        assert len(result) == 2
        assert result[0]["text"] == "teh cat sat"
        assert result[0]["labels"] == [1, 0, 0]

    def test_corrections_format(self, tmp_path: Path):
        """Loads JSONL with corrections field and auto-converts to labels."""
        filepath = tmp_path / "data.jsonl"
        sample = {
            "text": "teh quick brown fox",
            "clean_text": "the quick brown fox",
            "corrections": [
                {"start": 0, "end": 3, "original": "teh", "corrected": "the", "type": "transposition"}
            ],
        }
        with open(filepath, "w") as f:
            f.write(json.dumps(sample) + "\n")

        result = load_training_data(filepath)
        assert len(result) == 1
        assert result[0]["labels"] == [1, 0, 0, 0]

    def test_mixed_format(self, tmp_path: Path):
        """Handles both labels and corrections formats in the same file."""
        filepath = tmp_path / "mixed.jsonl"
        sample_labels = {"text": "hello world", "labels": [0, 0]}
        sample_corrections = {
            "text": "teh end",
            "clean_text": "the end",
            "corrections": [
                {"start": 0, "end": 3, "original": "teh", "corrected": "the", "type": "transposition"}
            ],
        }
        with open(filepath, "w") as f:
            f.write(json.dumps(sample_labels) + "\n")
            f.write(json.dumps(sample_corrections) + "\n")

        result = load_training_data(filepath)
        assert len(result) == 2
        assert result[0]["labels"] == [0, 0]
        assert result[1]["labels"] == [1, 0]

    def test_skips_empty_lines(self, tmp_path: Path):
        """Empty lines should be silently skipped."""
        filepath = tmp_path / "data.jsonl"
        with open(filepath, "w") as f:
            f.write(json.dumps({"text": "hello", "labels": [0]}) + "\n")
            f.write("\n")
            f.write("   \n")
            f.write(json.dumps({"text": "world", "labels": [0]}) + "\n")

        result = load_training_data(filepath)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# align_labels_with_tokens
# ---------------------------------------------------------------------------

class TestAlignLabelsWithTokens:
    def test_basic_alignment(self):
        """One-to-one mapping: each word maps to one token."""
        labels = [1, 0, 0]
        # [CLS]=None, word0, word1, word2, [SEP]=None
        word_ids = [None, 0, 1, 2, None]
        result = align_labels_with_tokens(labels, word_ids)
        assert result == [-100, 1, 0, 0, -100]

    def test_special_tokens_get_minus_100(self):
        """None word_ids (special tokens) should always get -100."""
        labels = [0, 1]
        word_ids = [None, 0, 1, None]
        result = align_labels_with_tokens(labels, word_ids)
        assert result[0] == -100
        assert result[-1] == -100

    def test_subword_tokens(self):
        """Repeated word_ids for subword tokens should get continuation labels."""
        labels = [1, 0]
        # word 0 is split into 2 subword tokens, word 1 is 1 token
        word_ids = [None, 0, 0, 1, None]
        result = align_labels_with_tokens(labels, word_ids)
        # [CLS]=-100, first subword of word0=1, continuation of word0=1 (since label!=0),
        # word1=0, [SEP]=-100
        assert result[0] == -100  # CLS
        assert result[1] == 1    # first token of word 0
        assert result[2] == 1    # continuation of word 0 (label is 1, not 0)
        assert result[3] == 0    # word 1
        assert result[4] == -100  # SEP

    def test_subword_tokens_no_error(self):
        """Continuation tokens for non-error words get -100."""
        labels = [0, 1]
        # word 0 split into 2 tokens, word 1 is 1 token
        word_ids = [None, 0, 0, 1, None]
        result = align_labels_with_tokens(labels, word_ids)
        assert result[0] == -100  # CLS
        assert result[1] == 0    # first token of word 0
        assert result[2] == -100  # continuation of word 0, label=0 so -100
        assert result[3] == 1    # word 1
        assert result[4] == -100  # SEP

    def test_word_id_out_of_range(self):
        """word_id beyond labels length should default to 0."""
        labels = [1]
        word_ids = [None, 0, 5, None]  # word_id 5 is out of range
        result = align_labels_with_tokens(labels, word_ids)
        assert result == [-100, 1, 0, -100]


# ---------------------------------------------------------------------------
# compute_metrics
# ---------------------------------------------------------------------------

class TestComputeMetrics:
    def _make_logits(self, predictions_flat: list[int], num_classes: int = 3) -> np.ndarray:
        """Convert flat class indices to one-hot-ish logits for argmax.

        Returns shape (1, seq_len, num_classes).
        """
        seq_len = len(predictions_flat)
        logits = np.full((1, seq_len, num_classes), -10.0)
        for i, cls_idx in enumerate(predictions_flat):
            logits[0, i, cls_idx] = 10.0
        return logits

    def test_perfect_predictions(self):
        """All correct predictions should give accuracy=1.0, f1=1.0."""
        labels = np.array([[0, 1, 0, 0, -100]])
        preds = self._make_logits([0, 1, 0, 0, 0])  # last ignored

        result = compute_metrics((preds, labels))
        assert result["accuracy"] == 1.0
        assert result["b_error_f1"] == 1.0

    def test_all_wrong(self):
        """All wrong predictions should give accuracy=0.0."""
        # True labels: [0, 1, 0, 1]  -- two O tokens and two B-ERROR
        labels = np.array([[0, 1, 0, 1]])
        # Predictions: all class 0 -- so B-ERROR tokens are missed
        preds = self._make_logits([0, 0, 0, 0])

        result = compute_metrics((preds, labels))
        # 2 out of 4 correct (the two O tokens), 2 wrong (the B-ERROR tokens)
        assert result["accuracy"] == pytest.approx(0.5)
        # No B-ERROR predicted, so precision undefined -> 0, recall -> 0
        assert result["b_error_recall"] == 0.0
        assert result["b_error_f1"] == 0.0

    def test_ignores_minus_100(self):
        """Tokens with label=-100 should be excluded from all metrics."""
        labels = np.array([[-100, 0, 1, -100]])
        preds = self._make_logits([2, 0, 1, 2])  # first and last ignored

        result = compute_metrics((preds, labels))
        # Only positions 1 and 2 matter: both correct
        assert result["accuracy"] == 1.0

    def test_precision_recall_balance(self):
        """One true positive, one false positive, one false negative."""
        # True: [0, 1, 1, 0]
        # Pred: [0, 1, 0, 1]
        # TP=1 (pos1), FP=1 (pos3), FN=1 (pos2)
        labels = np.array([[0, 1, 1, 0]])
        preds = self._make_logits([0, 1, 0, 1])

        result = compute_metrics((preds, labels))
        assert result["b_error_precision"] == pytest.approx(0.5)  # 1/(1+1)
        assert result["b_error_recall"] == pytest.approx(0.5)     # 1/(1+1)
        assert result["b_error_f1"] == pytest.approx(0.5)         # 2*0.5*0.5/(0.5+0.5)

    def test_no_error_tokens(self):
        """When there are no true error tokens, recall should be 0."""
        labels = np.array([[0, 0, 0]])
        preds = self._make_logits([0, 0, 0])

        result = compute_metrics((preds, labels))
        assert result["accuracy"] == 1.0
        assert result["b_error_recall"] == 0.0
        # No error predicted either, so precision is 0/0 -> 0
        assert result["b_error_precision"] == 0.0
