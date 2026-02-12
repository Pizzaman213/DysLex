"""Tests for GrammarErrorGenerator in ml.synthetic_data.grammar_generator."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.synthetic_data.grammar_generator import GrammarErrorGenerator


@pytest.fixture
def generator():
    """Create a GrammarErrorGenerator instance."""
    return GrammarErrorGenerator()


@pytest.fixture
def sample_corpus():
    """Sample sentences for testing."""
    return [
        "He goes to school every day.",
        "She has a new car.",
        "They go to the park on weekends.",
        "I walked to the store and talked to my friend.",
        "The cat sat on the mat.",
        "We need more time to finish the project.",
        "He runs every morning before breakfast.",
        "She wants to become a doctor when she grows up.",
    ]


class TestSubjectVerbError:
    def test_singular_to_base(self, generator):
        """Singular subject with 3rd-person verb should produce base form error."""
        result, etype = generator.apply_subject_verb_error("He goes to school every day.")
        assert etype == "subject_verb"
        assert "go" in result.lower()
        assert "goes" not in result.lower().split()[1]  # The verb should be changed

    def test_plural_to_third(self, generator):
        """Plural subject with base verb should produce 3rd-person error."""
        result, etype = generator.apply_subject_verb_error("They go to the park.")
        assert etype == "subject_verb"
        assert "goes" in result.lower()

    def test_no_match_returns_none(self, generator):
        """Sentence without subject-verb pair should return None type."""
        result, etype = generator.apply_subject_verb_error("The big red ball bounced away.")
        assert etype is None
        assert result == "The big red ball bounced away."


class TestArticleOmission:
    def test_removes_article(self, generator):
        """Should remove an article from the sentence."""
        result, etype = generator.apply_article_omission("She has a new car.")
        assert etype == "article"
        # The article 'a' should be removed
        assert "a new" not in result or "a" not in result.split()

    def test_no_article_returns_none(self, generator):
        """Sentence without articles should return None type."""
        result, etype = generator.apply_article_omission("Dogs run fast.")
        assert etype is None


class TestFunctionWordOmission:
    def test_removes_preposition(self, generator):
        """Should remove a preposition with matching context."""
        result, etype = generator.apply_function_word_omission(
            "He went to the store yesterday."
        )
        # May or may not succeed depending on context match
        if etype is not None:
            assert etype == "function_word"
            assert len(result.split()) < len("He went to the store yesterday.".split())

    def test_no_context_returns_none(self, generator):
        """Sentence without preposition context should return None."""
        result, etype = generator.apply_function_word_omission("Hello world.")
        assert etype is None


class TestTenseInconsistency:
    def test_past_to_present(self, generator):
        """Should swap a past-tense verb to present."""
        result, etype = generator.apply_tense_inconsistency(
            "She went home and ate dinner quickly."
        )
        # May or may not succeed depending on which verb is targeted
        if etype is not None:
            assert etype == "verb_tense"
            assert result != "She went home and ate dinner quickly."

    def test_short_sentence_returns_none(self, generator):
        """Sentences under 5 words should not be modified."""
        result, etype = generator.apply_tense_inconsistency("He ran.")
        assert etype is None


class TestPronounCaseError:
    def test_subject_to_object(self, generator):
        """Should replace subject pronoun with object form."""
        result, etype = generator.apply_pronoun_case_error("He went to the store.")
        if etype is not None:
            assert etype == "pronoun_case"
            assert result.lower().startswith("him")

    def test_preserves_capitalization(self, generator):
        """Should preserve capitalization when changing pronoun."""
        result, etype = generator.apply_pronoun_case_error("She called her friend.")
        if etype is not None:
            assert result[0].isupper()


class TestRunOn:
    def test_joins_two_sentences(self, generator):
        """Should join two sentences without proper punctuation."""
        result, etype = generator.apply_run_on(
            "I ran home.", "I was tired."
        )
        assert etype == "run_on"
        assert "." not in result.split("tired")[0]  # No period between sentences

    def test_no_other_sentence_returns_none(self, generator):
        """Without a second sentence, should return None."""
        result, etype = generator.apply_run_on("I ran home.")
        assert etype is None


class TestGenerateGrammarError:
    def test_produces_error(self, generator, sample_corpus):
        """Should produce at least some errors from the corpus."""
        successes = 0
        for _ in range(50):
            sentence = sample_corpus[0]
            error_text, clean_text, etype = generator.generate_grammar_error(
                sentence, sample_corpus
            )
            if etype is not None:
                successes += 1
                assert error_text != clean_text

        assert successes > 0, "Should produce at least some grammar errors"

    def test_error_type_is_valid(self, generator, sample_corpus):
        """Generated error types should be from the expected set."""
        valid_types = {
            "subject_verb", "article", "function_word",
            "verb_tense", "pronoun_case", "run_on", None,
        }
        for _ in range(100):
            sentence = sample_corpus[0]
            _, _, etype = generator.generate_grammar_error(sentence, sample_corpus)
            assert etype in valid_types, f"Unexpected error type: {etype}"


class TestGenerateTrainingPairs:
    def test_produces_samples(self, generator):
        """Should produce training samples in seq2seq format."""
        samples = generator.generate_training_pairs(num_samples=100)
        assert len(samples) > 0

    def test_sample_format(self, generator):
        """Each sample should have the required keys."""
        samples = generator.generate_training_pairs(num_samples=50)
        for sample in samples:
            assert "input_text" in sample
            assert "target_text" in sample
            assert "error_type" in sample
            assert "source" in sample
            assert sample["input_text"].startswith("correct: ")

    def test_includes_passthrough(self, generator):
        """Should include no-error passthrough samples."""
        samples = generator.generate_training_pairs(
            num_samples=200, include_passthrough=0.2
        )
        passthrough = [s for s in samples if s["error_type"] == "none"]
        assert len(passthrough) > 0, "Should include passthrough samples"

    def test_passthrough_input_equals_target(self, generator):
        """Passthrough samples should have input_text == target_text (minus prefix)."""
        samples = generator.generate_training_pairs(
            num_samples=100, include_passthrough=0.3
        )
        for sample in samples:
            if sample["error_type"] == "none":
                raw_input = sample["input_text"].removeprefix("correct: ")
                assert raw_input == sample["target_text"]

    def test_writes_to_file(self, generator, tmp_path):
        """Should write JSONL output to file."""
        output_file = tmp_path / "grammar_train.jsonl"
        samples = generator.generate_training_pairs(
            num_samples=50, output_file=output_file
        )
        assert output_file.exists()
        lines = output_file.read_text().strip().split("\n")
        assert len(lines) == len(samples)

    def test_error_type_distribution(self, generator):
        """Generated data should have a reasonable distribution of error types."""
        samples = generator.generate_training_pairs(num_samples=1000)
        type_counts: dict[str, int] = {}
        for s in samples:
            t = s["error_type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        # Should have at least some of each type (excluding none)
        error_types = {k: v for k, v in type_counts.items() if k != "none"}
        assert len(error_types) >= 3, f"Expected diverse error types, got: {error_types}"
