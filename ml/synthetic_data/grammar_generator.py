"""Synthetic grammar error generator for training the Quick Correction Model.

Generates training data by applying realistic grammar errors to clean text.
Produces JSONL format with input/target pairs for fine-tuning T5 (seq2seq).

Grammar error types covered:
  - Subject-verb agreement ("he go" -> "he goes")
  - Article omission ("I have cat" -> "I have a cat")
  - Function word omission ("went the store" -> "went to the store")
  - Tense inconsistency ("I walked and talk" -> "I walked and talked")
  - Pronoun case errors ("him went" -> "he went")
  - Run-on sentences ("I ran home I was tired" -> "I ran home. I was tired.")
"""

import json
import random
import re
from pathlib import Path
from typing import Any


class GrammarErrorGenerator:
    """Generates synthetic grammar errors for training data."""

    def __init__(self, patterns_dir: Path | None = None):
        """Initialize generator with grammar patterns.

        Args:
            patterns_dir: Directory containing grammar pattern JSON files
        """
        if patterns_dir is None:
            patterns_dir = Path(__file__).parent / "patterns"

        self.patterns_dir = patterns_dir
        self.subject_verb = self._load_pattern("grammar_subject_verb.json")
        self.articles = self._load_pattern("grammar_articles.json")
        self.function_words = self._load_pattern("grammar_function_words.json")
        self.pronouns = self._load_pattern("grammar_pronouns.json")
        self.verb_tenses = self._load_pattern("grammar_verb_tenses.json")

        # Build reverse lookup tables
        self._build_verb_tables()
        self._build_pronoun_tables()

    def _load_pattern(self, filename: str) -> dict[str, Any]:
        """Load grammar pattern from JSON file."""
        filepath = self.patterns_dir / filename
        if not filepath.exists():
            return {}
        with open(filepath) as f:
            return json.load(f)

    def _build_verb_tables(self) -> None:
        """Build verb conjugation lookup tables."""
        pairs = self.subject_verb.get("third_person_singular", {}).get("pairs", {})
        # base -> 3rd person: "go" -> "goes"
        self.base_to_3rd: dict[str, str] = dict(pairs)
        # 3rd person -> base: "goes" -> "go"
        self.third_to_base: dict[str, str] = {v: k for k, v in pairs.items()}

        # Irregular past tense pairs
        irr = self.verb_tenses.get("irregular_verbs", {}).get("pairs", {})
        self.present_to_past: dict[str, str] = dict(irr)
        self.past_to_present: dict[str, str] = {v: k for k, v in irr.items()}

        # Regular verbs
        self.regular_verbs: list[str] = self.verb_tenses.get("regular_verbs", {}).get("verbs", [])

    def _build_pronoun_tables(self) -> None:
        """Build pronoun case lookup tables."""
        case_forms = self.pronouns.get("case_forms", {}).get("pairs", [])
        self.subject_to_object: dict[str, str] = {}
        self.object_to_subject: dict[str, str] = {}
        for pair in case_forms:
            s = pair["subject"].lower()
            o = pair["object"].lower()
            self.subject_to_object[s] = o
            self.object_to_subject[o] = s

    def _regularize_past(self, verb: str) -> str:
        """Convert a regular verb to past tense."""
        if verb.endswith("e"):
            return verb + "d"
        if verb.endswith("y") and len(verb) > 2 and verb[-2] not in "aeiou":
            return verb[:-1] + "ied"
        if (
            len(verb) >= 3
            and verb[-1] not in "aeiouwxy"
            and verb[-2] in "aeiou"
            and verb[-3] not in "aeiou"
        ):
            return verb + verb[-1] + "ed"
        return verb + "ed"

    def apply_subject_verb_error(self, text: str) -> tuple[str, str | None]:
        """Toggle verb agreement: correct -> incorrect.

        Examples:
            "he goes to school" -> "he go to school"
            "they go to school" -> "they goes to school"

        Returns:
            Tuple of (modified_text, error_type or None if no change)
        """
        words = text.split()
        singular = {"he", "she", "it"}
        plural = {"they", "we", "i", "you"}

        for i in range(len(words) - 1):
            word_lower = words[i].lower()
            verb_lower = words[i + 1].lower().rstrip(".,!?;:")
            punct = words[i + 1][len(verb_lower):]

            if word_lower in singular and verb_lower in self.third_to_base:
                # "he goes" -> "he go"
                wrong = self.third_to_base[verb_lower]
                words[i + 1] = wrong + punct
                return " ".join(words), "subject_verb"

            if word_lower in plural and verb_lower in self.base_to_3rd:
                # "they go" -> "they goes"
                wrong = self.base_to_3rd[verb_lower]
                words[i + 1] = wrong + punct
                return " ".join(words), "subject_verb"

        return text, None

    def apply_article_omission(self, text: str) -> tuple[str, str | None]:
        """Drop an article ('a', 'an', 'the') from the sentence.

        Example: "I have a cat" -> "I have cat"

        Returns:
            Tuple of (modified_text, error_type or None)
        """
        pattern = re.compile(r'\b(a|an|the)\s+', re.IGNORECASE)
        matches = list(pattern.finditer(text))
        if not matches:
            return text, None

        match = random.choice(matches)
        # Remove the article and the space after it
        modified = text[:match.start()] + text[match.end():]
        return modified, "article"

    def apply_function_word_omission(self, text: str) -> tuple[str, str | None]:
        """Drop a preposition from the sentence.

        Example: "went to the store" -> "went the store"

        Returns:
            Tuple of (modified_text, error_type or None)
        """
        preps = self.function_words.get("prepositions", {}).get("patterns", [])
        if not preps:
            return text, None

        words = text.split()
        candidates: list[int] = []

        for i, w in enumerate(words):
            w_lower = w.lower().rstrip(".,!?;:")
            for prep_info in preps:
                if w_lower == prep_info["word"]:
                    # Check context: verb before or determiner after
                    has_context = False
                    if i > 0:
                        prev = words[i - 1].lower().rstrip(".,!?;:")
                        if prev in prep_info.get("context_before", []):
                            has_context = True
                    if i < len(words) - 1:
                        nxt = words[i + 1].lower().rstrip(".,!?;:")
                        if nxt in prep_info.get("context_after", []):
                            has_context = True
                    if has_context:
                        candidates.append(i)

        if not candidates:
            return text, None

        idx = random.choice(candidates)
        words.pop(idx)
        return " ".join(words), "function_word"

    def apply_tense_inconsistency(self, text: str) -> tuple[str, str | None]:
        """Mix tenses within a sentence.

        Example: "I walked to the store and talk to my friend"
                 (should be "talked" to match past tense)

        Returns:
            Tuple of (modified_text, error_type or None)
        """
        words = text.split()
        if len(words) < 5:
            return text, None

        # Find verbs that could be swapped
        past_indices: list[int] = []
        present_indices: list[int] = []

        for i, w in enumerate(words):
            w_lower = w.lower().rstrip(".,!?;:")
            if w_lower in self.past_to_present:
                past_indices.append(i)
            elif w_lower in self.present_to_past:
                present_indices.append(i)
            elif w_lower.endswith("ed") and len(w_lower) > 3:
                past_indices.append(i)

        # If we have past-tense verbs, swap one to present
        if past_indices and random.random() < 0.6:
            idx = random.choice(past_indices)
            w_lower = words[idx].lower().rstrip(".,!?;:")
            punct = words[idx][len(w_lower):]
            if w_lower in self.past_to_present:
                words[idx] = self.past_to_present[w_lower] + punct
                return " ".join(words), "verb_tense"

        # If we have present-tense verbs, swap one to past
        if present_indices:
            idx = random.choice(present_indices)
            w_lower = words[idx].lower().rstrip(".,!?;:")
            punct = words[idx][len(w_lower):]
            if w_lower in self.present_to_past:
                words[idx] = self.present_to_past[w_lower] + punct
                return " ".join(words), "verb_tense"
            elif w_lower in self.regular_verbs:
                words[idx] = self._regularize_past(w_lower) + punct
                return " ".join(words), "verb_tense"

        return text, None

    def apply_pronoun_case_error(self, text: str) -> tuple[str, str | None]:
        """Use wrong pronoun case form.

        Example: "him went to the store" -> should be "he went"

        Returns:
            Tuple of (modified_text, error_type or None)
        """
        words = text.split()
        verbs_after = set(self.pronouns.get("subject_position_cues", {}).get("verbs_after", []))

        for i in range(len(words) - 1):
            w_lower = words[i].lower().rstrip(".,!?;:")
            next_lower = words[i + 1].lower().rstrip(".,!?;:")

            # Subject position: pronoun before verb -> use object form (wrong)
            if w_lower in self.subject_to_object and next_lower in verbs_after:
                wrong = self.subject_to_object[w_lower]
                # Preserve capitalization
                if words[i][0].isupper():
                    wrong = wrong[0].upper() + wrong[1:]
                punct = words[i][len(w_lower):]
                words[i] = wrong + punct
                return " ".join(words), "pronoun_case"

        return text, None

    def apply_run_on(self, text: str, other_sentence: str | None = None) -> tuple[str, str | None]:
        """Join two sentences without punctuation, creating a run-on.

        Example: "I ran home. I was tired." -> "I ran home I was tired"

        Args:
            text: Primary sentence
            other_sentence: Optional second sentence to join with

        Returns:
            Tuple of (modified_text, error_type or None)
        """
        if other_sentence is None:
            return text, None

        # Strip trailing punctuation from first sentence
        clean_first = text.rstrip(" .")
        # Strip leading capital? No — keep it to make the run-on realistic
        # but lowercase the first letter of the second sentence
        clean_second = other_sentence.strip()
        if clean_second and clean_second[0].isupper():
            clean_second = clean_second[0].lower() + clean_second[1:]

        # Remove trailing period from second sentence too (the correct version has it)
        run_on = clean_first + " " + clean_second
        return run_on, "run_on"

    def generate_grammar_error(
        self, sentence: str, corpus: list[str] | None = None
    ) -> tuple[str, str, str | None]:
        """Apply one random grammar error to a sentence.

        Args:
            sentence: Clean input sentence
            corpus: Optional corpus for run-on sentence partner

        Returns:
            Tuple of (error_text, clean_text, error_type)
        """
        # Weight the error types by frequency
        error_funcs = [
            (0.25, "subject_verb"),
            (0.25, "article"),
            (0.20, "function_word"),
            (0.10, "verb_tense"),
            (0.10, "run_on"),
            (0.10, "pronoun_case"),
        ]

        # Shuffle weighted
        r = random.random()
        cumulative = 0.0
        chosen_type = "subject_verb"
        for weight, etype in error_funcs:
            cumulative += weight
            if r < cumulative:
                chosen_type = etype
                break

        if chosen_type == "subject_verb":
            result, etype = self.apply_subject_verb_error(sentence)
        elif chosen_type == "article":
            result, etype = self.apply_article_omission(sentence)
        elif chosen_type == "function_word":
            result, etype = self.apply_function_word_omission(sentence)
        elif chosen_type == "verb_tense":
            result, etype = self.apply_tense_inconsistency(sentence)
        elif chosen_type == "pronoun_case":
            result, etype = self.apply_pronoun_case_error(sentence)
        elif chosen_type == "run_on":
            other = random.choice(corpus) if corpus else None
            result, etype = self.apply_run_on(sentence, other)
            if etype:
                # The clean_text for a run-on is both sentences properly punctuated
                clean = sentence.rstrip() + " " + (other or "").strip()
                return result, clean, etype
        else:
            return sentence, sentence, None

        if etype is None:
            # Failed to apply chosen error, try another
            for _, fallback_type in error_funcs:
                if fallback_type == chosen_type or fallback_type == "run_on":
                    continue
                if fallback_type == "subject_verb":
                    result, etype = self.apply_subject_verb_error(sentence)
                elif fallback_type == "article":
                    result, etype = self.apply_article_omission(sentence)
                elif fallback_type == "function_word":
                    result, etype = self.apply_function_word_omission(sentence)
                elif fallback_type == "verb_tense":
                    result, etype = self.apply_tense_inconsistency(sentence)
                elif fallback_type == "pronoun_case":
                    result, etype = self.apply_pronoun_case_error(sentence)
                if etype is not None:
                    break

        return result, sentence, etype

    def generate_training_pairs(
        self,
        corpus: list[str] | None = None,
        num_samples: int = 30000,
        include_passthrough: float = 0.15,
        output_file: Path | None = None,
    ) -> list[dict[str, str]]:
        """Produce JSONL training pairs in seq2seq format.

        Args:
            corpus: List of clean sentences
            num_samples: Number of training samples to generate
            include_passthrough: Fraction of "no error" samples (prevents false positives)
            output_file: Optional path to save JSONL output

        Returns:
            List of training samples with input_text, target_text, error_type, source
        """
        if corpus is None:
            # Load default corpus
            corpus_file = Path(__file__).parent.parent / "datasets" / "corpus" / "sentences.txt"
            if corpus_file.exists():
                with open(corpus_file) as f:
                    corpus = [line.strip() for line in f if line.strip()]
            else:
                corpus = [
                    "The student submitted the assignment before the deadline.",
                    "She walked to the store to buy some groceries for dinner.",
                    "He decided to take the bus instead of driving his car today.",
                ]

        samples: list[dict[str, str]] = []
        passthrough_count = int(num_samples * include_passthrough)
        error_count = num_samples - passthrough_count

        # Generate error samples
        for i in range(error_count):
            sentence = random.choice(corpus)
            error_text, clean_text, error_type = self.generate_grammar_error(
                sentence, corpus
            )

            if error_type is None or error_text == clean_text:
                continue

            samples.append({
                "input_text": f"correct: {error_text}",
                "target_text": clean_text,
                "error_type": error_type,
                "source": "synthetic_grammar",
            })

            if (i + 1) % 5000 == 0:
                print(f"Generated {i + 1}/{error_count} grammar error samples...")

        # Generate passthrough (no-error) samples
        for i in range(passthrough_count):
            sentence = random.choice(corpus)
            samples.append({
                "input_text": f"correct: {sentence}",
                "target_text": sentence,
                "error_type": "none",
                "source": "synthetic_grammar_passthrough",
            })

        random.shuffle(samples)

        # Save to file
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                for sample in samples:
                    f.write(json.dumps(sample) + "\n")
            print(f"Saved {len(samples)} grammar samples to {output_file}")

        return samples


def main():
    """Generate grammar training data for Quick Correction Model."""
    generator = GrammarErrorGenerator()

    output_dir = Path(__file__).parent.parent / "quick_correction" / "data"
    output_file = output_dir / "train_grammar.jsonl"

    print("Generating synthetic grammar training data...")
    samples = generator.generate_training_pairs(
        num_samples=30000, output_file=output_file
    )

    print(f"\nGeneration complete!")
    print(f"Total samples: {len(samples)}")
    print(f"Output: {output_file}")

    # Show distribution
    type_counts: dict[str, int] = {}
    for s in samples:
        t = s.get("error_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    print("\nError type distribution:")
    for etype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        pct = count / len(samples) * 100
        print(f"  {etype:20s}: {count:6d} ({pct:.1f}%)")

    # Show sample
    if samples:
        print("\nSample training examples:")
        for sample in samples[:3]:
            print(f"  Input:  {sample['input_text']}")
            print(f"  Target: {sample['target_text']}")
            print(f"  Type:   {sample['error_type']}")
            print()


if __name__ == "__main__":
    main()
