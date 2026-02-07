"""Tests for vision-based prompt templates."""

from app.core.vision_prompts import (
    VISION_EXTRACT_SYSTEM_PROMPT,
    build_vision_extract_prompt,
)


class TestVisionExtractSystemPrompt:
    """Tests for the vision system prompt constant."""

    def test_is_non_empty_string(self):
        assert isinstance(VISION_EXTRACT_SYSTEM_PROMPT, str)
        assert len(VISION_EXTRACT_SYSTEM_PROMPT) > 0

    def test_contains_key_instructions(self):
        assert "JSON" in VISION_EXTRACT_SYSTEM_PROMPT
        assert "topic" in VISION_EXTRACT_SYSTEM_PROMPT
        assert "cards" in VISION_EXTRACT_SYSTEM_PROMPT
        assert "image" in VISION_EXTRACT_SYSTEM_PROMPT.lower()


class TestBuildVisionExtractPrompt:
    """Tests for build_vision_extract_prompt."""

    def test_returns_base_prompt_without_hint(self):
        prompt = build_vision_extract_prompt()
        assert isinstance(prompt, str)
        assert "extract" in prompt.lower() or "Extract" in prompt

    def test_includes_user_hint_when_provided(self):
        prompt = build_vision_extract_prompt(user_hint="whiteboard from class")
        assert "whiteboard from class" in prompt

    def test_no_hint_section_when_none(self):
        prompt = build_vision_extract_prompt(user_hint=None)
        assert "User context:" not in prompt

    def test_hint_appended_to_base(self):
        base = build_vision_extract_prompt()
        with_hint = build_vision_extract_prompt(user_hint="my notes")
        assert len(with_hint) > len(base)
        assert "my notes" in with_hint
