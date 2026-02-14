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
        self.vowel_confusion = self._load_pattern("vowel_confusion.json")
        self.visual_similarity = self._load_pattern("visual_similarity.json")
        self.homophones = self._load_pattern("homophones.json")

        # Load confusion pairs from the main database
        self.confusion_pairs = self._load_confusion_pairs()

    def _load_pattern(self, filename: str) -> dict[str, Any]:
        """Load error pattern from JSON file."""
        filepath = self.patterns_dir / filename
        if not filepath.exists():
            return {"patterns": []}
        with open(filepath) as f:
            return json.load(f)

    def _load_confusion_pairs(self) -> dict[str, list[str]]:
        """Load confusion pairs from en.json and homophones pattern file.

        Returns:
            Dict mapping each word to its possible confusions.
        """
        pairs: dict[str, list[str]] = {}

        # Load from ml/confusion_pairs/en.json
        en_path = Path(__file__).parent.parent / "confusion_pairs" / "en.json"
        if en_path.exists():
            with open(en_path) as f:
                data = json.load(f)
            for entry in data.get("pairs", []):
                words = entry.get("words", [])
                for i, word in enumerate(words):
                    others = [w for j, w in enumerate(words) if j != i]
                    if word in pairs:
                        pairs[word].extend(o for o in others if o not in pairs[word])
                    else:
                        pairs[word] = others

        # Load from homophones pattern file
        for sub in self.homophones.get("high_frequency_substitutions", []):
            correct = sub["correct"]
            errors = sub.get("errors", [])
            if correct in pairs:
                pairs[correct].extend(e for e in errors if e not in pairs[correct])
            else:
                pairs[correct] = list(errors)

        for sub in self.homophones.get("pedler_confused_words", []):
            correct = sub["correct"]
            errors = sub.get("errors", [])
            if correct in pairs:
                pairs[correct].extend(e for e in errors if e not in pairs[correct])
            else:
                pairs[correct] = list(errors)

        return pairs

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

    def apply_vowel_confusion(
        self, word: str, probability: float = 0.25
    ) -> tuple[str, bool]:
        """Apply vowel confusion error (separate→seperate, definite→definate).

        Args:
            word: Original word
            probability: Chance of applying vowel confusion

        Returns:
            Tuple of (modified_word, was_changed)
        """
        if random.random() > probability or len(word) < 3:
            return word, False

        # Check common examples first
        examples = self.vowel_confusion.get("common_examples", [])
        for example in examples:
            if word.lower() == example["correct"]:
                if random.random() < 0.8:
                    error = example["error"]
                    if word[0].isupper():
                        error = error[0].upper() + error[1:]
                    return error, True

        # Apply pattern-based vowel substitution
        patterns = self.vowel_confusion.get("patterns", [])
        for pattern in patterns:
            from_str = pattern["from"]
            to_str = pattern["to"]
            if from_str in word.lower() and random.random() < pattern.get("frequency", 0.15):
                new_word = word.lower().replace(from_str, to_str, 1)
                if word[0].isupper() and new_word:
                    new_word = new_word[0].upper() + new_word[1:]
                if new_word != word.lower():
                    return new_word, True

        return word, False

    def apply_homophone_substitution(
        self, word: str, probability: float = 0.20
    ) -> tuple[str, bool]:
        """Apply homophone substitution (their→there, your→you're).

        Uses the confusion pairs database loaded from en.json.

        Args:
            word: Original word
            probability: Chance of applying substitution

        Returns:
            Tuple of (modified_word, was_changed)
        """
        if random.random() > probability:
            return word, False

        word_lower = word.lower().rstrip(".,!?;:'\"")
        if word_lower in self.confusion_pairs:
            alternatives = self.confusion_pairs[word_lower]
            if alternatives:
                replacement = random.choice(alternatives)
                # Preserve case
                if word[0].isupper():
                    replacement = replacement[0].upper() + replacement[1:]
                return replacement, True

        return word, False

    def apply_visual_similarity(
        self, word: str, probability: float = 0.15
    ) -> tuple[str, bool]:
        """Apply visual similarity error (burn→bum, corner→comer).

        Letters and letter combinations that look alike in common fonts.

        Args:
            word: Original word
            probability: Chance of applying visual similarity error

        Returns:
            Tuple of (modified_word, was_changed)
        """
        if random.random() > probability or len(word) < 3:
            return word, False

        # Check common examples first
        examples = self.visual_similarity.get("common_examples", [])
        for example in examples:
            if word.lower() == example["correct"]:
                if random.random() < 0.7:
                    error = example["error"]
                    if word[0].isupper():
                        error = error[0].upper() + error[1:]
                    return error, True

        # Apply pattern-based substitution
        patterns = self.visual_similarity.get("patterns", [])
        for pattern in patterns:
            from_str = pattern["from"]
            to_str = pattern["to"]
            if from_str in word.lower() and random.random() < pattern.get("frequency", 0.10):
                new_word = word.lower().replace(from_str, to_str, 1)
                if word[0].isupper() and new_word:
                    new_word = new_word[0].upper() + new_word[1:]
                if new_word != word.lower():
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

            # Apply one random error type with updated distribution
            error_choice = random.random()
            if error_choice < 0.15:
                core, changed = self.apply_letter_reversal(core)
                error_type = "reversal"
            elif error_choice < 0.35:
                core, changed = self.apply_transposition(core)
                error_type = "transposition"
            elif error_choice < 0.55:
                core, changed = self.apply_phonetic_substitution(core)
                error_type = "phonetic"
            elif error_choice < 0.65:
                core, changed = self.apply_omission(core)
                error_type = "omission"
            elif error_choice < 0.80:
                core, changed = self.apply_vowel_confusion(core)
                error_type = "vowel_confusion"
            elif error_choice < 0.90:
                core, changed = self.apply_homophone_substitution(core)
                error_type = "homophone"
            elif error_choice < 1.0:
                core, changed = self.apply_visual_similarity(core)
                error_type = "visual_similarity"

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


    def generate_mixed_training_pairs(
        self,
        corpus: list[str] | None = None,
        num_samples: int = 5000,
        output_file: Path | None = None,
    ) -> list[dict[str, str]]:
        """Generate samples with both spelling AND grammar errors in the same sentence.

        Applies a spelling error from this generator and a grammar error from
        GrammarErrorGenerator to the same sentence (~5% of combined training data).

        Args:
            corpus: List of clean sentences
            num_samples: Number of combined-error samples
            output_file: Optional path to save JSONL output

        Returns:
            List of training samples in seq2seq format
        """
        from ml.synthetic_data.grammar_generator import GrammarErrorGenerator

        grammar_gen = GrammarErrorGenerator(self.patterns_dir)

        if corpus is None:
            corpus_file = Path(__file__).parent.parent / "datasets" / "corpus" / "sentences.txt"
            if corpus_file.exists():
                with open(corpus_file) as f:
                    corpus = [line.strip() for line in f if line.strip()]
            else:
                corpus = SAMPLE_SENTENCES

        samples: list[dict[str, str]] = []

        for i in range(num_samples):
            sentence = random.choice(corpus)

            # Apply grammar error first
            error_text, clean_text, grammar_type = grammar_gen.generate_grammar_error(
                sentence, corpus
            )
            if grammar_type is None:
                continue

            # Apply spelling error on top of the grammar-errored text
            spelling_error_text, corrections = self.apply_error_patterns(error_text)
            if not corrections:
                continue

            samples.append({
                "input_text": spelling_error_text,
                "target_text": clean_text,
                "error_type": f"mixed_{grammar_type}",
                "source": "synthetic_mixed",
            })

            if (i + 1) % 1000 == 0:
                print(f"Generated {i + 1}/{num_samples} mixed samples...")

        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                for sample in samples:
                    f.write(json.dumps(sample) + "\n")
            print(f"Saved {len(samples)} mixed samples to {output_file}")

        return samples


    def generate_multi_error_training_pairs(
        self,
        corpus: list[str] | None = None,
        num_samples: int = 50000,
        output_file: Path | None = None,
    ) -> list[dict[str, str]]:
        """Generate samples with 2-4 errors (spelling and/or grammar) per sentence.

        Also includes single-error-in-long-sentence samples to teach the model
        to leave most text unchanged.

        Args:
            corpus: List of clean sentences
            num_samples: Number of samples to generate
            output_file: Optional path to save JSONL output

        Returns:
            List of training samples in seq2seq format
        """
        from ml.synthetic_data.grammar_generator import GrammarErrorGenerator

        grammar_gen = GrammarErrorGenerator(self.patterns_dir)

        if corpus is None:
            corpus_file = Path(__file__).parent.parent / "datasets" / "corpus" / "sentences.txt"
            if corpus_file.exists():
                with open(corpus_file) as f:
                    corpus = [line.strip() for line in f if line.strip()]
            else:
                corpus = SAMPLE_SENTENCES

        samples: list[dict[str, str]] = []

        # 70% multi-error samples, 30% single-error-in-long-sentence
        multi_count = int(num_samples * 0.7)
        single_long_count = num_samples - multi_count

        # Generate multi-error samples (2-4 errors per sentence)
        for i in range(multi_count):
            sentence = random.choice(corpus)
            num_errors = random.randint(2, 4)
            error_text = sentence
            error_types: list[str] = []

            for _ in range(num_errors):
                # Alternate between spelling and grammar errors
                if random.random() < 0.5:
                    # Spelling error
                    modified, corrections = self.apply_error_patterns(error_text)
                    if corrections:
                        error_text = modified
                        error_types.append("spelling")
                else:
                    # Grammar error
                    modified, _, etype = grammar_gen.generate_grammar_error(
                        error_text, corpus
                    )
                    if etype is not None and modified != error_text:
                        error_text = modified
                        error_types.append(etype)

            if error_types and error_text != sentence:
                samples.append({
                    "input_text": error_text,
                    "target_text": sentence,
                    "error_type": f"mixed_multi_{len(error_types)}",
                    "source": "synthetic_mixed",
                })

            if (i + 1) % 5000 == 0:
                print(f"Generated {i + 1}/{multi_count} multi-error samples...")

        # Generate single-error-in-long-sentence samples
        # Concatenate 2-3 sentences, apply only one error
        for i in range(single_long_count):
            n_sentences = random.randint(2, 3)
            chosen = random.sample(corpus, min(n_sentences, len(corpus)))
            long_sentence = " ".join(chosen)

            # Apply a single error (spelling or grammar)
            if random.random() < 0.5:
                modified, corrections = self.apply_error_patterns(long_sentence)
                if corrections:
                    samples.append({
                        "input_text": modified,
                        "target_text": long_sentence,
                        "error_type": "mixed_single_long",
                        "source": "synthetic_mixed",
                    })
            else:
                modified, _, etype = grammar_gen.generate_grammar_error(
                    long_sentence, corpus
                )
                if etype is not None and modified != long_sentence:
                    samples.append({
                        "input_text": modified,
                        "target_text": long_sentence,
                        "error_type": "mixed_single_long",
                        "source": "synthetic_mixed",
                    })

            if (i + 1) % 5000 == 0:
                print(f"Generated {i + 1}/{single_long_count} single-error-long samples...")

        random.shuffle(samples)

        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                for sample in samples:
                    f.write(json.dumps(sample) + "\n")
            print(f"Saved {len(samples)} multi-error mixed samples to {output_file}")

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
