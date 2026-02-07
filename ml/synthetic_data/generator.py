"""Synthetic training data generator for dyslexic error patterns.

Generates training data by applying realistic dyslexic error patterns to clean text.
Produces JSONL format with corrections for fine-tuning the Quick Correction Model.
"""

import json
import random
import re
from pathlib import Path
from typing import Any

# Sample corpus for training - in production, use larger corpus
SAMPLE_SENTENCES = [
    "The quick brown fox jumps over the lazy dog.",
    "She sells seashells by the seashore.",
    "Peter Piper picked a peck of pickled peppers.",
    "How much wood would a woodchuck chuck if a woodchuck could chuck wood?",
    "I scream, you scream, we all scream for ice cream.",
    "Betty Botter bought some butter but the butter was bitter.",
    "A proper copper coffee pot.",
    "Red lorry, yellow lorry.",
    "Unique New York.",
    "Toy boat.",
    "The big black bug bit the big black bear.",
    "Six thick thistle sticks.",
    "Eleven benevolent elephants.",
    "Two tried and true tridents.",
    "Five frantic frogs fled from fifty fierce fishes.",
]


class SyntheticDataGenerator:
    """Generates synthetic training data with dyslexic error patterns."""

    def __init__(self, patterns_dir: Path | None = None):
        """Initialize generator with error patterns.

        Args:
            patterns_dir: Directory containing error pattern JSON files
        """
        if patterns_dir is None:
            patterns_dir = Path(__file__).parent / "patterns"

        self.patterns_dir = patterns_dir
        self.reversals = self._load_pattern("reversals.json")
        self.phonetic = self._load_pattern("phonetic.json")
        self.transpositions = self._load_pattern("transpositions.json")
        self.omissions = self._load_pattern("omissions.json")

    def _load_pattern(self, filename: str) -> dict[str, Any]:
        """Load error pattern from JSON file."""
        filepath = self.patterns_dir / filename
        if not filepath.exists():
            return {"patterns": []}
        with open(filepath) as f:
            return json.load(f)

    def apply_letter_reversal(
        self, word: str, probability: float = 0.3
    ) -> tuple[str, bool]:
        """Apply letter reversal error (b→d, p→q, m→w).

        Args:
            word: Original word
            probability: Chance of applying reversal

        Returns:
            Tuple of (modified_word, was_changed)
        """
        if random.random() > probability:
            return word, False

        patterns = self.reversals.get("patterns", [])
        if not patterns:
            return word, False

        for i, char in enumerate(word):
            for pattern in patterns:
                if char.lower() == pattern["from"] and random.random() < pattern["frequency"]:
                    # Preserve case
                    replacement = pattern["to"].upper() if char.isupper() else pattern["to"]
                    return word[:i] + replacement + word[i + 1 :], True

        return word, False

    def apply_transposition(
        self, word: str, probability: float = 0.22
    ) -> tuple[str, bool]:
        """Apply letter transposition (teh→the, form→from).

        Args:
            word: Original word
            probability: Chance of applying transposition

        Returns:
            Tuple of (modified_word, was_changed)
        """
        if random.random() > probability or len(word) < 3:
            return word, False

        # Check common examples first
        examples = self.transpositions.get("common_examples", [])
        for example in examples:
            if word.lower() == example["correct"]:
                if random.random() < 0.8:  # High probability for known patterns
                    # Preserve case of first letter
                    error = example["error"]
                    if word[0].isupper():
                        error = error[0].upper() + error[1:]
                    return error, True

        # Random adjacent swap
        if len(word) > 2:
            idx = random.randint(0, len(word) - 2)
            chars = list(word)
            chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
            return "".join(chars), True

        return word, False

    def apply_omission(
        self, word: str, probability: float = 0.16
    ) -> tuple[str, bool]:
        """Apply letter omission (which→wich, probably→probly).

        Args:
            word: Original word
            probability: Chance of applying omission

        Returns:
            Tuple of (modified_word, was_changed)
        """
        if random.random() > probability or len(word) < 4:
            return word, False

        # Omit random letter (except first and last)
        idx = random.randint(1, len(word) - 2)
        return word[:idx] + word[idx + 1 :], True

    def apply_phonetic_substitution(
        self, word: str, probability: float = 0.28
    ) -> tuple[str, bool]:
        """Apply phonetic substitution (phone→fone, laugh→laf).

        Args:
            word: Original word
            probability: Chance of applying substitution

        Returns:
            Tuple of (modified_word, was_changed)
        """
        if random.random() > probability:
            return word, False

        patterns = self.phonetic.get("patterns", [])
        for pattern in patterns:
            if pattern["from"] in word.lower():
                # Simple replacement
                new_word = word.lower().replace(pattern["from"], pattern["to"])
                # Preserve case of first letter
                if word[0].isupper() and new_word:
                    new_word = new_word[0].upper() + new_word[1:]
                return new_word, True

        return word, False

    def apply_error_patterns(self, text: str) -> tuple[str, list[dict[str, Any]]]:
        """Apply multiple error patterns to text.

        Args:
            text: Clean input text

        Returns:
            Tuple of (error_text, corrections_list)
        """
        words = text.split()
        corrections = []
        modified_words = []
        current_pos = 0

        for word in words:
            # Remove punctuation for processing
            match = re.match(r"([^\w]*)(\w+)([^\w]*)", word)
            if not match:
                modified_words.append(word)
                current_pos += len(word) + 1
                continue

            prefix, core, suffix = match.groups()
            original_core = core
            error_type = None
            changed = False

            # Apply one random error type
            error_choice = random.random()
            if error_choice < 0.3:
                core, changed = self.apply_letter_reversal(core)
                error_type = "reversal"
            elif error_choice < 0.52:
                core, changed = self.apply_transposition(core)
                error_type = "transposition"
            elif error_choice < 0.8:
                core, changed = self.apply_phonetic_substitution(core)
                error_type = "phonetic"
            elif error_choice < 0.96:
                core, changed = self.apply_omission(core)
                error_type = "omission"

            if changed and core != original_core:
                # Calculate exact position in text
                start = current_pos + len(prefix)
                end = start + len(core)

                corrections.append(
                    {
                        "start": start,
                        "end": end,
                        "original": core,
                        "corrected": original_core,
                        "type": error_type,
                        "confidence": 1.0,
                    }
                )

            modified_word = prefix + core + suffix
            modified_words.append(modified_word)
            current_pos += len(modified_word) + 1

        return " ".join(modified_words), corrections

    def generate_training_pairs(
        self,
        corpus: list[str] | None = None,
        num_samples: int = 50000,
        output_file: Path | None = None,
    ) -> list[dict[str, Any]]:
        """Generate training pairs from corpus.

        Args:
            corpus: List of clean sentences (uses default if None)
            num_samples: Number of training samples to generate
            output_file: Optional path to save JSONL output

        Returns:
            List of training samples with corrections
        """
        if corpus is None:
            corpus = SAMPLE_SENTENCES

        samples = []

        for i in range(num_samples):
            # Select random sentence
            clean_text = random.choice(corpus)

            # Apply errors
            error_text, corrections = self.apply_error_patterns(clean_text)

            # Skip if no errors were applied
            if not corrections:
                continue

            sample = {
                "text": error_text,
                "clean_text": clean_text,
                "corrections": corrections,
            }
            samples.append(sample)

            # Progress indicator
            if (i + 1) % 5000 == 0:
                print(f"Generated {i + 1}/{num_samples} samples...")

        # Save to file if specified
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                for sample in samples:
                    f.write(json.dumps(sample) + "\n")
            print(f"Saved {len(samples)} samples to {output_file}")

        return samples


def main():
    """Generate training data for Quick Correction Model."""
    generator = SyntheticDataGenerator()

    # Generate 50K samples
    output_dir = Path(__file__).parent.parent / "quick_correction" / "data"
    output_file = output_dir / "train.jsonl"

    print("Generating synthetic training data...")
    samples = generator.generate_training_pairs(
        num_samples=50000, output_file=output_file
    )

    print(f"\nGeneration complete!")
    print(f"Total samples: {len(samples)}")
    print(f"Output: {output_file}")

    # Show sample
    if samples:
        print("\nSample training example:")
        sample = samples[0]
        print(f"Error text: {sample['text']}")
        print(f"Clean text: {sample['clean_text']}")
        print(f"Corrections: {sample['corrections']}")


if __name__ == "__main__":
    main()
