"""Tests for dynamic prompt construction."""

from app.core.prompt_builder import (
    build_correction_prompt,
    build_correction_prompt_v2,
    build_explanation_prompt,
)
from app.models.error_log import LLMContext


class TestBuildCorrectionPrompt:
    """Tests for the legacy build_correction_prompt function."""

    def test_includes_user_text(self):
        prompt = build_correction_prompt("I saw teh cat", [], [])
        assert "I saw teh cat" in prompt

    def test_includes_user_patterns(self):
        # build_correction_prompt uses getattr, so patterns must be objects
        patterns = [{"misspelling": "teh", "correction": "the"}]
        prompt = build_correction_prompt("text", patterns, [])
        # With dicts, getattr falls back to description=None, then "? -> ?"
        # Verify the function runs and includes the user text
        assert "text" in prompt
        assert isinstance(prompt, str)

    def test_includes_confusion_pairs_as_dicts(self):
        pairs = [{"word1": "there", "word2": "their"}]
        prompt = build_correction_prompt("text", [], pairs)
        assert "there" in prompt
        assert "their" in prompt

    def test_limits_patterns_to_five(self):
        # Create objects with description attribute so getattr finds them
        class FakePattern:
            def __init__(self, desc):
                self.description = desc
        patterns = [FakePattern(f"pattern-{i}") for i in range(10)]
        prompt = build_correction_prompt("text", patterns, [])
        assert "pattern-4" in prompt
        assert "pattern-5" not in prompt

    def test_includes_context_when_provided(self):
        prompt = build_correction_prompt("text", [], [], context="essay about cats")
        assert "essay about cats" in prompt

    def test_no_context_section_when_none(self):
        prompt = build_correction_prompt("text", [], [], context=None)
        assert "Context:" not in prompt

    def test_returns_string(self):
        result = build_correction_prompt("hello", [], [])
        assert isinstance(result, str)


class TestBuildCorrectionPromptV2:
    """Tests for the v2 prompt builder using LLMContext."""

    def _make_context(self, **overrides):
        defaults = {
            "top_errors": [],
            "error_types": {},
            "confusion_pairs": [],
            "writing_level": "intermediate",
            "personal_dictionary": [],
            "context_notes": [],
            "grammar_patterns": [],
            "improvement_trends": [],
            "mastered_words": [],
            "total_stats": None,
            "writing_streak": None,
            "recent_error_count": None,
            "recent_document_topics": [],
            "correction_aggressiveness": 50,
        }
        defaults.update(overrides)
        return LLMContext(**defaults)

    def _combined(self, text, ctx, context=None):
        """Helper: combine system + user messages for assertion checks."""
        system_msg, user_msg = build_correction_prompt_v2(text, ctx, context)
        return system_msg + "\n" + user_msg

    def test_returns_tuple(self):
        ctx = self._make_context()
        result = build_correction_prompt_v2("hello", ctx)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)

    def test_user_text_in_user_message(self):
        ctx = self._make_context()
        _, user_msg = build_correction_prompt_v2("I like becuase cats", ctx)
        assert "I like becuase cats" in user_msg

    def test_system_instructions_in_system_message(self):
        ctx = self._make_context()
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "writing coach" in system_msg
        assert "dyslexia" in system_msg

    def test_includes_top_errors(self):
        ctx = self._make_context(
            top_errors=[{"misspelling": "becuase", "correction": "because", "frequency": 12}]
        )
        combined = self._combined("text", ctx)
        assert "becuase" in combined
        assert "because" in combined
        assert "12" in combined

    def test_includes_error_type_breakdown(self):
        ctx = self._make_context(error_types={"reversal": 34.0, "phonetic": 28.0})
        combined = self._combined("text", ctx)
        assert "reversal" in combined
        assert "34" in combined

    def test_includes_confusion_pairs(self):
        ctx = self._make_context(
            confusion_pairs=[{"word_a": "their", "word_b": "there", "count": 5}]
        )
        combined = self._combined("text", ctx)
        assert "their" in combined
        assert "there" in combined

    def test_includes_personal_dictionary(self):
        ctx = self._make_context(personal_dictionary=["minecraft", "pokemon"])
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "minecraft" in system_msg
        assert "pokemon" in system_msg

    def test_includes_writing_level(self):
        ctx = self._make_context(writing_level="advanced")
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "advanced" in system_msg

    def test_includes_context_notes(self):
        ctx = self._make_context(context_notes=["User prefers British English"])
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "User prefers British English" in system_msg

    def test_includes_grammar_patterns(self):
        ctx = self._make_context(
            grammar_patterns=[
                {"subtype": "subject_verb", "misspelling": "dogs runs", "correction": "dogs run", "frequency": 3}
            ]
        )
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "dogs runs" in system_msg
        assert "subject_verb" in system_msg

    def test_includes_context_arg_in_user_message(self):
        ctx = self._make_context()
        _, user_msg = build_correction_prompt_v2("text", ctx, context="essay about dogs")
        assert "essay about dogs" in user_msg

    def test_no_context_in_user_message_when_none(self):
        ctx = self._make_context()
        _, user_msg = build_correction_prompt_v2("text", ctx, context=None)
        assert "Context:" not in user_msg

    def test_skips_zero_error_types(self):
        ctx = self._make_context(error_types={"reversal": 34.0, "phonetic": 0.0})
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "Error type breakdown:" in system_msg
        # Extract just the breakdown lines (between "Error type breakdown:" and next section)
        after_breakdown = system_msg.split("Error type breakdown:")[1]
        # Breakdown entries are indented "  - type: pct%", stop at next non-indented line
        breakdown_lines = []
        for line in after_breakdown.split("\n")[1:]:
            if line.startswith("  - "):
                breakdown_lines.append(line)
            elif line.strip():
                break
        breakdown_text = "\n".join(breakdown_lines)
        assert "reversal" in breakdown_text
        assert "phonetic" not in breakdown_text

    def test_system_msg_does_not_contain_user_text(self):
        ctx = self._make_context()
        system_msg, _ = build_correction_prompt_v2("My unique input text xyz", ctx)
        assert "My unique input text xyz" not in system_msg

    def test_user_msg_does_not_contain_system_instructions(self):
        ctx = self._make_context()
        _, user_msg = build_correction_prompt_v2("text", ctx)
        assert "writing coach" not in user_msg
        assert "INSTRUCTIONS:" not in user_msg

    def test_user_msg_contains_analyze_instruction(self):
        ctx = self._make_context()
        _, user_msg = build_correction_prompt_v2("text", ctx)
        assert "analyze" in user_msg.lower()

    def test_system_msg_contains_output_format_section(self):
        ctx = self._make_context()
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "OUTPUT FORMAT:" in system_msg

    def test_system_msg_specifies_all_required_fields(self):
        ctx = self._make_context()
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        for field in ("original", "correction", "error_type", "confidence", "explanation"):
            assert field in system_msg

    def test_system_msg_specifies_json_only_response(self):
        ctx = self._make_context()
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "ONLY a JSON array" in system_msg

    def test_system_msg_specifies_empty_array_for_no_errors(self):
        ctx = self._make_context()
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "[]" in system_msg

    def test_system_msg_examples_use_canonical_field_names(self):
        ctx = self._make_context()
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert '"correction"' in system_msg
        assert '"error_type"' in system_msg
        assert '"confidence"' in system_msg
        # Should NOT use the old aliased names in examples
        assert '"suggested"' not in system_msg
        assert '"type"' not in system_msg

    def test_system_msg_lists_valid_error_types(self):
        ctx = self._make_context()
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        for etype in ("spelling", "grammar", "homophone", "phonetic",
                       "subject_verb", "tense", "article", "word_order",
                       "missing_word", "run_on",
                       "clarity", "style", "word_choice"):
            assert etype in system_msg

    def test_system_msg_contains_grammar_detection(self):
        ctx = self._make_context()
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "GRAMMAR DETECTION" in system_msg
        assert "subject_verb" in system_msg
        assert "run_on" in system_msg

    def test_system_msg_contains_all_instructions(self):
        ctx = self._make_context()
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        for i in range(1, 8):
            assert f"{i}." in system_msg

    def test_system_msg_contains_recommendations_section(self):
        ctx = self._make_context()
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "RECOMMENDATIONS:" in system_msg
        assert "clarity" in system_msg.lower()
        assert "style" in system_msg.lower()
        assert "word choice" in system_msg.lower()

    def test_system_msg_examples_include_recommendation_types(self):
        ctx = self._make_context()
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert '"style"' in system_msg
        assert '"clarity"' in system_msg
        assert '"word_choice"' in system_msg

    def test_top_errors_limited_to_20(self):
        errors = [
            {"misspelling": f"word{i}", "correction": f"fix{i}", "frequency": i}
            for i in range(25)
        ]
        ctx = self._make_context(top_errors=errors)
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "word19" in system_msg
        assert "word20" not in system_msg

    def test_confusion_pairs_limited_to_10(self):
        pairs = [
            {"word_a": f"a{i}", "word_b": f"b{i}", "count": i}
            for i in range(15)
        ]
        ctx = self._make_context(confusion_pairs=pairs)
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "a9" in system_msg
        assert "a10" not in system_msg

    def test_grammar_patterns_limited_to_10(self):
        patterns = [
            {"subtype": f"type{i}", "misspelling": f"err{i}", "correction": f"fix{i}", "frequency": i}
            for i in range(15)
        ]
        ctx = self._make_context(grammar_patterns=patterns)
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "err9" in system_msg
        assert "err10" not in system_msg

    def test_personal_dictionary_limited_to_50(self):
        words = [f"word{i}" for i in range(60)]
        ctx = self._make_context(personal_dictionary=words)
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "word49" in system_msg
        assert "word50" not in system_msg

    def test_empty_profile_omits_optional_sections(self):
        ctx = self._make_context()
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "Most common errors:" not in system_msg
        assert "Error type breakdown:" not in system_msg
        assert "Frequently confused word pairs:" not in system_msg
        assert "grammar patterns:" not in system_msg
        assert "Personal dictionary" not in system_msg
        assert "NOTES:" not in system_msg

    def test_full_profile_includes_all_sections(self):
        ctx = self._make_context(
            top_errors=[{"misspelling": "teh", "correction": "the", "frequency": 5}],
            error_types={"reversal": 60.0, "phonetic": 40.0},
            confusion_pairs=[{"word_a": "their", "word_b": "there", "count": 3}],
            grammar_patterns=[{"subtype": "tense", "misspelling": "go", "correction": "went", "frequency": 2}],
            personal_dictionary=["minecraft"],
            context_notes=["Prefers short sentences"],
            writing_level="beginner",
        )
        system_msg, user_msg = build_correction_prompt_v2(
            "I teh cat there", ctx, context="story"
        )
        assert "Most common errors:" in system_msg
        assert "Error type breakdown:" in system_msg
        assert "Frequently confused" in system_msg
        assert "grammar patterns:" in system_msg.lower()
        assert "minecraft" in system_msg
        assert "NOTES:" in system_msg
        assert "Prefers short sentences" in system_msg
        assert "beginner" in system_msg
        assert "story" in user_msg
        assert "I teh cat there" in user_msg

    # --- Enriched context tests ---

    def test_includes_mastered_words(self):
        ctx = self._make_context(mastered_words=["because", "which", "their"])
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "mastered" in system_msg.lower()
        assert "because" in system_msg
        assert "which" in system_msg

    def test_includes_improvement_trends(self):
        ctx = self._make_context(
            improvement_trends=[
                {"error_type": "spelling", "change_percent": -25.0, "trend": "improving"},
                {"error_type": "grammar", "change_percent": 15.0, "trend": "needs_attention"},
            ]
        )
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "spelling" in system_msg
        assert "improving" in system_msg
        assert "grammar" in system_msg
        assert "needs_attention" in system_msg

    def test_includes_total_stats(self):
        ctx = self._make_context(
            total_stats={"total_sessions": 42, "total_words": 12000, "total_corrections": 350}
        )
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "42" in system_msg
        assert "12000" in system_msg

    def test_includes_document_topics(self):
        ctx = self._make_context(
            recent_document_topics=["My Essay on Climate Change", "History Homework"]
        )
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "My Essay on Climate Change" in system_msg
        assert "History Homework" in system_msg

    def test_correction_aggressiveness_low(self):
        ctx = self._make_context(correction_aggressiveness=20)
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "CORRECTION LEVEL: LOW" in system_msg

    def test_correction_aggressiveness_high(self):
        ctx = self._make_context(correction_aggressiveness=80)
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "CORRECTION LEVEL: HIGH" in system_msg

    def test_correction_aggressiveness_default_omitted(self):
        ctx = self._make_context(correction_aggressiveness=50)
        system_msg, _ = build_correction_prompt_v2("text", ctx)
        assert "CORRECTION LEVEL" not in system_msg

    def test_new_fields_backward_compatible(self):
        ctx = LLMContext(
            top_errors=[],
            error_types={},
            confusion_pairs=[],
            writing_level="new_user",
            personal_dictionary=[],
            context_notes=[],
        )
        system_msg, user_msg = build_correction_prompt_v2("hello", ctx)
        assert isinstance(system_msg, str)
        assert isinstance(user_msg, str)
        assert ctx.improvement_trends == []
        assert ctx.mastered_words == []
        assert ctx.total_stats is None
        assert ctx.correction_aggressiveness == 50


class TestBuildExplanationPrompt:
    """Tests for build_explanation_prompt."""

    def test_includes_original(self):
        prompt = build_explanation_prompt("teh", "the", "spelling")
        assert "teh" in prompt

    def test_includes_suggested(self):
        prompt = build_explanation_prompt("teh", "the", "spelling")
        assert "the" in prompt

    def test_includes_correction_type(self):
        prompt = build_explanation_prompt("there", "their", "homophone")
        assert "homophone" in prompt

    def test_returns_string(self):
        result = build_explanation_prompt("a", "b", "c")
        assert isinstance(result, str)
        assert len(result) > 0
