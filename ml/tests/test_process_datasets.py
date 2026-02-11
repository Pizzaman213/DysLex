"""Tests for parsing and injection functions in ml.datasets.process_datasets."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.datasets.process_datasets import (  # type: ignore[import-not-found]
    inject_errors_into_sentences,
    load_clean_sentences,
    parse_aspell,
    parse_birkbeck,
    parse_wikipedia,
)


# ---------------------------------------------------------------------------
# parse_birkbeck
# ---------------------------------------------------------------------------

class TestParseBirkbeck:
    def test_parse_birkbeck(self, birkbeck_file: Path):
        """Parse known Birkbeck content and verify (misspelling, correct) pairs."""
        pairs = parse_birkbeck(birkbeck_file)
        assert len(pairs) > 0
        # Expect specific pairs based on fixture content
        assert ("teh", "the") in pairs
        assert ("form", "from") in pairs
        assert ("becuase", "because") in pairs
        assert ("wich", "which") in pairs
        assert ("whn", "when") in pairs
        assert ("fone", "phone") in pairs

    def test_parse_birkbeck_missing_file(self, tmp_path: Path):
        """Missing file should return an empty list, not raise."""
        result = parse_birkbeck(tmp_path / "nonexistent.dat")
        assert result == []

    def test_parse_birkbeck_empty_file(self, tmp_raw_dir: Path):
        """An empty file should return an empty list."""
        filepath = tmp_raw_dir / "empty.dat"
        filepath.write_text("")
        assert parse_birkbeck(filepath) == []

    def test_parse_birkbeck_skips_same_word(self, tmp_raw_dir: Path):
        """Misspelling identical to correct word should be skipped."""
        filepath = tmp_raw_dir / "dup.dat"
        filepath.write_text("$the\nthe\n")
        pairs = parse_birkbeck(filepath)
        assert len(pairs) == 0


# ---------------------------------------------------------------------------
# parse_aspell (same format as Birkbeck)
# ---------------------------------------------------------------------------

class TestParseAspell:
    def test_parse_aspell(self, tmp_raw_dir: Path):
        """Aspell uses the same $ format as Birkbeck."""
        filepath = tmp_raw_dir / "aspell.dat"
        content = "$receive\nrecieve\nreceve\n$separate\nseperate\n"
        filepath.write_text(content)
        pairs = parse_aspell(filepath)
        assert ("recieve", "receive") in pairs
        assert ("receve", "receive") in pairs
        assert ("seperate", "separate") in pairs

    def test_parse_aspell_missing_file(self, tmp_path: Path):
        result = parse_aspell(tmp_path / "no_such_file.dat")
        assert result == []


# ---------------------------------------------------------------------------
# parse_wikipedia
# ---------------------------------------------------------------------------

class TestParseWikipedia:
    def test_parse_wikipedia_raw_format(self, wikipedia_file: Path):
        """Parse 'misspelling->correct' lines from the fixture file."""
        pairs = parse_wikipedia(wikipedia_file)
        assert len(pairs) > 0
        assert ("accomodate", "accommodate") in pairs
        assert ("adress", "address") in pairs
        assert ("seperate", "separate") in pairs

    def test_parse_wikipedia_missing_file(self, tmp_path: Path):
        result = parse_wikipedia(tmp_path / "nonexistent.txt")
        assert result == []

    def test_parse_wikipedia_multiword_skip(self, tmp_raw_dir: Path):
        """Corrections containing spaces should be skipped."""
        filepath = tmp_raw_dir / "wiki_multi.txt"
        content = " alot->a lot\n misspel->misspell\n"
        filepath.write_text(content)
        pairs = parse_wikipedia(filepath)
        # "a lot" contains a space, so it should be excluded
        assert all(" " not in p[1] for p in pairs)
        assert ("misspel", "misspell") in pairs


# ---------------------------------------------------------------------------
# inject_errors_into_sentences
# ---------------------------------------------------------------------------

class TestInjectErrors:
    def test_inject_errors_basic(self, sample_sentences: list[str]):
        """Inject known pairs into sentences, verify labels match word positions."""
        pairs = [("teh", "the"), ("wich", "which")]
        samples = inject_errors_into_sentences(
            word_pairs=pairs,
            clean_sentences=sample_sentences,
            source="test",
        )
        for sample in samples:
            words = sample["text"].split()
            labels = sample["labels"]
            assert len(labels) == len(words), (
                f"Label count ({len(labels)}) must match word count ({len(words)})"
            )
            # At least one label should be 1 (error)
            assert any(lbl == 1 for lbl in labels)

    def test_inject_errors_preserves_punctuation(self):
        """Words with trailing punctuation should keep the punctuation."""
        pairs = [("teh", "the")]
        sentences = ["The dog sat on the mat."]
        samples = inject_errors_into_sentences(
            word_pairs=pairs,
            clean_sentences=sentences,
            source="test",
        )
        for sample in samples:
            words = sample["text"].split()
            # The last word should still end with a period
            assert words[-1].endswith("."), (
                f"Punctuation lost: last word is '{words[-1]}'"
            )

    def test_inject_errors_preserves_capitalization(self):
        """Capitalized words should produce capitalized misspellings."""
        pairs = [("teh", "the")]
        sentences = ["The dog sat on the mat."]
        samples = inject_errors_into_sentences(
            word_pairs=pairs,
            clean_sentences=sentences,
            source="test",
        )
        for sample in samples:
            words = sample["text"].split()
            labels = sample["labels"]
            for i, (word, label) in enumerate(zip(words, labels)):
                if label == 1 and i == 0:
                    # First word was "The" -> should become "Teh" (capital T)
                    clean = word.rstrip(".,!?;:")
                    assert clean[0].isupper(), (
                        f"Expected capitalized misspelling, got '{word}'"
                    )

    def test_inject_errors_empty_pairs(self, sample_sentences: list[str]):
        """Empty pairs should produce no samples."""
        result = inject_errors_into_sentences(
            word_pairs=[],
            clean_sentences=sample_sentences,
            source="test",
        )
        assert result == []

    def test_inject_errors_empty_sentences(self, sample_word_pairs: list[tuple[str, str]]):
        """Empty sentences should produce no samples."""
        result = inject_errors_into_sentences(
            word_pairs=sample_word_pairs,
            clean_sentences=[],
            source="test",
        )
        assert result == []

    def test_inject_errors_label_count_matches_words(self, sample_sentences: list[str]):
        """len(labels) must always equal len(text.split()) for every sample."""
        pairs = [("teh", "the"), ("form", "from"), ("wich", "which")]
        samples = inject_errors_into_sentences(
            word_pairs=pairs,
            clean_sentences=sample_sentences,
            source="test",
            target_samples=20,
        )
        for sample in samples:
            words = sample["text"].split()
            assert len(sample["labels"]) == len(words)

    def test_inject_errors_source_tag(self, sample_sentences: list[str]):
        """Source field should match the provided source name."""
        pairs = [("teh", "the")]
        samples = inject_errors_into_sentences(
            word_pairs=pairs,
            clean_sentences=sample_sentences,
            source="my_source",
        )
        for sample in samples:
            assert sample["source"] == "my_source"


# ---------------------------------------------------------------------------
# load_clean_sentences
# ---------------------------------------------------------------------------

class TestLoadCleanSentences:
    def test_load_clean_sentences(self, tmp_path: Path):
        """Load sentences from a fixture file."""
        filepath = tmp_path / "sentences.txt"
        lines = [
            "The cat sat on the mat.",
            "She sells seashells by the seashore.",
            "How much wood would a woodchuck chuck.",
        ]
        filepath.write_text("\n".join(lines) + "\n")
        result = load_clean_sentences(filepath)
        assert len(result) == 3
        assert result[0] == "The cat sat on the mat."

    def test_load_clean_sentences_missing_file(self, tmp_path: Path):
        """Missing corpus file should return an empty list."""
        result = load_clean_sentences(tmp_path / "no_such_file.txt")
        assert result == []

    def test_load_clean_sentences_skips_empty_lines(self, tmp_path: Path):
        """Blank lines should be skipped."""
        filepath = tmp_path / "sentences.txt"
        filepath.write_text("Hello world.\n\n\nGoodbye world.\n\n")
        result = load_clean_sentences(filepath)
        assert len(result) == 2
