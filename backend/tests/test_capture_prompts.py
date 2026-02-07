"""Tests for Capture Mode prompt templates."""

from app.core.capture_prompts import (
    EXTRACT_IDEAS_SYSTEM_PROMPT,
    build_extract_ideas_prompt,
)


class TestExtractIdeasSystemPrompt:
    """Tests for the system prompt constant."""

    def test_is_non_empty_string(self):
        assert isinstance(EXTRACT_IDEAS_SYSTEM_PROMPT, str)
        assert len(EXTRACT_IDEAS_SYSTEM_PROMPT) > 0

    def test_contains_key_instructions(self):
        assert "JSON" in EXTRACT_IDEAS_SYSTEM_PROMPT
        assert "topic" in EXTRACT_IDEAS_SYSTEM_PROMPT
        assert "cards" in EXTRACT_IDEAS_SYSTEM_PROMPT
        assert "sub_ideas" in EXTRACT_IDEAS_SYSTEM_PROMPT


class TestBuildExtractIdeasPrompt:
    """Tests for build_extract_ideas_prompt."""

    def test_embeds_transcript(self):
        prompt = build_extract_ideas_prompt("Dogs are amazing animals")
        assert "Dogs are amazing animals" in prompt

    def test_empty_transcript(self):
        prompt = build_extract_ideas_prompt("")
        assert isinstance(prompt, str)
        assert 'Input: ""' in prompt

    def test_long_transcript(self):
        long_text = "word " * 500
        prompt = build_extract_ideas_prompt(long_text)
        assert long_text.strip() in prompt

    def test_returns_string(self):
        result = build_extract_ideas_prompt("test")
        assert isinstance(result, str)
