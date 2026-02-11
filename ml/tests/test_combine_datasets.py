"""Tests for combination and conversion functions in ml.datasets.combine_datasets."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.datasets.combine_datasets import (  # type: ignore[import-not-found]
    convert_corrections_to_labels,
    load_processed_real_data,
)


# ---------------------------------------------------------------------------
# convert_corrections_to_labels
# ---------------------------------------------------------------------------

class TestConvertCorrectionsToLabels:
    def test_single_error(self):
        """Single correction should produce exactly one label=1."""
        sample = {
            "text": "teh quick brown fox",
            "clean_text": "the quick brown fox",
            "corrections": [
                {
                    "start": 0,
                    "end": 3,
                    "original": "teh",
                    "corrected": "the",
                    "type": "transposition",
                    "confidence": 1.0,
                }
            ],
        }
        result = convert_corrections_to_labels(sample)
        assert result["text"] == "teh quick brown fox"
        assert result["labels"] == [1, 0, 0, 0]
        assert result["source"] == "synthetic"
        assert result["error_type"] == "transposition"

    def test_no_errors(self):
        """Clean text with no corrections should produce all-zero labels."""
        sample = {
            "text": "the quick brown fox",
            "clean_text": "the quick brown fox",
            "corrections": [],
        }
        result = convert_corrections_to_labels(sample)
        assert result["labels"] == [0, 0, 0, 0]
        assert result["error_type"] == "none"

    def test_multiple_errors(self):
        """Multiple corrections should produce multiple label=1 entries."""
        sample = {
            "text": "teh bog ran fast",
            "clean_text": "the dog ran fast",
            "corrections": [
                {
                    "start": 0,
                    "end": 3,
                    "original": "teh",
                    "corrected": "the",
                    "type": "transposition",
                    "confidence": 1.0,
                },
                {
                    "start": 4,
                    "end": 7,
                    "original": "bog",
                    "corrected": "dog",
                    "type": "reversal",
                    "confidence": 1.0,
                },
            ],
        }
        result = convert_corrections_to_labels(sample)
        assert result["labels"] == [1, 1, 0, 0]

    def test_middle_word_error(self):
        """Error in the middle of a sentence should flag the correct word index."""
        sample = {
            "text": "she went to teh store",
            "clean_text": "she went to the store",
            "corrections": [
                {
                    "start": 12,
                    "end": 15,
                    "original": "teh",
                    "corrected": "the",
                    "type": "transposition",
                    "confidence": 1.0,
                }
            ],
        }
        result = convert_corrections_to_labels(sample)
        assert result["labels"] == [0, 0, 0, 1, 0]

    def test_label_count_matches_word_count(self, sample_synthetic_data: list[dict]):
        """Converted labels list length must match word count for all fixtures."""
        for sample in sample_synthetic_data:
            result = convert_corrections_to_labels(sample)
            word_count = len(result["text"].split())
            assert len(result["labels"]) == word_count


# ---------------------------------------------------------------------------
# load_processed_real_data
# ---------------------------------------------------------------------------

class TestLoadProcessedRealData:
    def test_load_processed_real_data(self, tmp_processed_dir: Path):
        """Load JSONL files from a directory."""
        data = [
            {"text": "teh cat sat", "labels": [1, 0, 0], "source": "birkbeck", "error_type": "transposition"},
            {"text": "she went home", "labels": [0, 0, 0], "source": "birkbeck", "error_type": "none"},
        ]
        filepath = tmp_processed_dir / "birkbeck.jsonl"
        with open(filepath, "w") as f:
            for d in data:
                f.write(json.dumps(d) + "\n")

        result = load_processed_real_data(tmp_processed_dir)
        assert len(result) == 2
        assert result[0]["text"] == "teh cat sat"
        assert result[1]["labels"] == [0, 0, 0]

    def test_load_processed_multiple_files(self, tmp_processed_dir: Path):
        """Should load and combine samples from multiple JSONL files."""
        for name in ("source_a.jsonl", "source_b.jsonl"):
            filepath = tmp_processed_dir / name
            with open(filepath, "w") as f:
                f.write(json.dumps({"text": f"hello from {name}", "labels": [0, 0, 0], "source": name}) + "\n")

        result = load_processed_real_data(tmp_processed_dir)
        assert len(result) == 2

    def test_load_processed_missing_dir(self, tmp_path: Path):
        """Missing directory should return an empty list."""
        result = load_processed_real_data(tmp_path / "nonexistent")
        assert result == []

    def test_load_processed_empty_dir(self, tmp_processed_dir: Path):
        """Directory with no JSONL files should return an empty list."""
        result = load_processed_real_data(tmp_processed_dir)
        assert result == []


# ---------------------------------------------------------------------------
# combine_and_split (integration-level, but no heavy deps)
# ---------------------------------------------------------------------------

class TestCombineAndSplit:
    """Test combine_and_split ratios and determinism.

    These tests mock generate_synthetic_data to avoid importing the
    SyntheticDataGenerator (which may have optional dependencies).
    """

    def _write_real_data(self, processed_dir: Path, count: int) -> None:
        """Helper to write N real-data samples to a JSONL file."""
        filepath = processed_dir / "real.jsonl"
        with open(filepath, "w") as f:
            for i in range(count):
                sample = {
                    "text": f"sample number {i} words here",
                    "labels": [0, 0, 0, 0, 0],
                    "source": "test",
                    "error_type": "none",
                }
                f.write(json.dumps(sample) + "\n")

    def test_combine_and_split_ratios(self, tmp_processed_dir: Path, tmp_output_dir: Path, monkeypatch):
        """Verify train/val/test split ratios approximately match targets."""
        from ml.datasets import combine_datasets  # type: ignore[import-not-found]

        # Write 200 real samples
        self._write_real_data(tmp_processed_dir, 200)

        # Mock generate_synthetic_data to return deterministic data
        def mock_generate(target_count: int) -> list[dict]:
            return [
                {
                    "text": f"synthetic sample {i} data",
                    "labels": [0, 0, 0, 0],
                    "source": "synthetic",
                    "error_type": "none",
                }
                for i in range(target_count)
            ]

        monkeypatch.setattr(combine_datasets, "generate_synthetic_data", mock_generate)

        results = combine_datasets.combine_and_split(
            processed_dir=tmp_processed_dir,
            output_dir=tmp_output_dir,
            target_total=400,
            real_ratio=0.5,
            test_ratio=0.05,
            val_ratio=0.1,
            seed=42,
        )

        total = sum(results.values())
        assert total > 0

        # Test set should be roughly 5% of real data
        assert results["test"] > 0

        # Val set should be roughly 10% of combined (train+val)
        train_val = results["train"] + results["val"]
        if train_val > 0:
            val_ratio_actual = results["val"] / train_val
            assert 0.05 < val_ratio_actual < 0.20, (
                f"Val ratio {val_ratio_actual:.2f} outside expected range"
            )

        # Verify output files exist
        assert (tmp_output_dir / "train.jsonl").exists()
        assert (tmp_output_dir / "val.jsonl").exists()
        assert (tmp_output_dir / "test.jsonl").exists()

    def test_combine_and_split_deterministic(self, tmp_processed_dir: Path, tmp_output_dir: Path, monkeypatch):
        """Same seed should produce the same split."""
        from ml.datasets import combine_datasets  # type: ignore[import-not-found]

        self._write_real_data(tmp_processed_dir, 100)

        def mock_generate(target_count: int) -> list[dict]:
            return [
                {
                    "text": f"synthetic sample {i} data",
                    "labels": [0, 0, 0, 0],
                    "source": "synthetic",
                    "error_type": "none",
                }
                for i in range(target_count)
            ]

        monkeypatch.setattr(combine_datasets, "generate_synthetic_data", mock_generate)

        # First run
        out1 = tmp_output_dir / "run1"
        out1.mkdir()
        results1 = combine_datasets.combine_and_split(
            processed_dir=tmp_processed_dir,
            output_dir=out1,
            target_total=200,
            seed=123,
        )

        # Second run with same seed
        out2 = tmp_output_dir / "run2"
        out2.mkdir()
        results2 = combine_datasets.combine_and_split(
            processed_dir=tmp_processed_dir,
            output_dir=out2,
            target_total=200,
            seed=123,
        )

        assert results1 == results2

        # Verify file contents are identical
        for split in ("train", "val", "test"):
            content1 = (out1 / f"{split}.jsonl").read_text()
            content2 = (out2 / f"{split}.jsonl").read_text()
            assert content1 == content2, f"{split} split differs between runs with same seed"
