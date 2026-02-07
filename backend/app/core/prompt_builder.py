"""Dynamic prompt construction for LLM calls."""

from app.models.error_log import LLMContext


def build_correction_prompt(
    text: str,
    user_patterns: list[dict],
    confusion_pairs: list[dict],
    context: str | None = None,
) -> str:
    """Build a personalized correction prompt based on user's error profile (legacy)."""
    prompt_parts = [
        "You are a writing assistant specialized in helping dyslexic users.",
        "Analyze the following text for spelling and grammar errors.",
        "",
        "The user commonly makes these types of errors:",
    ]

    for pattern in user_patterns[:5]:
        prompt_parts.append(f"- {pattern['description']}")

    if confusion_pairs:
        prompt_parts.append("")
        prompt_parts.append("The user often confuses these word pairs:")
        for pair in confusion_pairs[:5]:
            prompt_parts.append(f"- {pair['word1']} / {pair['word2']}")

    prompt_parts.extend([
        "",
        "Text to analyze:",
        f'"{text}"',
        "",
        "Return corrections in JSON format:",
        '[{"original": "word", "suggested": "word", "type": "spelling|grammar|confusion", "explanation": "brief explanation"}]',
    ])

    if context:
        prompt_parts.insert(-1, f"Context: {context}")

    return "\n".join(prompt_parts)


def build_correction_prompt_v2(
    text: str,
    llm_context: LLMContext,
    context: str | None = None,
) -> str:
    """Build a personalised correction prompt using the full LLMContext object."""
    parts: list[str] = [
        "You are a writing assistant for a person with dyslexia.",
        "Your job is to identify and correct errors while preserving the user's voice and intent.",
        "Be encouraging, never condescending.",
        "",
    ]

    # User error profile section
    parts.append("USER ERROR PROFILE:")

    if llm_context.top_errors:
        parts.append("Most common errors:")
        for err in llm_context.top_errors[:20]:
            parts.append(
                f'  - "{err["misspelling"]}" -> "{err["correction"]}" ({err["frequency"]}x)'
            )

    # Error type distribution
    non_zero_types = {k: v for k, v in llm_context.error_types.items() if v > 0}
    if non_zero_types:
        parts.append("Error type breakdown:")
        for etype, pct in sorted(non_zero_types.items(), key=lambda x: -x[1]):
            parts.append(f"  - {etype}: {pct}%")

    if llm_context.confusion_pairs:
        parts.append("Frequently confused word pairs:")
        for pair in llm_context.confusion_pairs[:10]:
            parts.append(f'  - {pair["word_a"]} / {pair["word_b"]} ({pair["count"]}x)')

    parts.append(f"Writing level: {llm_context.writing_level}")

    if llm_context.personal_dictionary:
        parts.append(
            "Personal dictionary (do NOT flag these words): "
            + ", ".join(llm_context.personal_dictionary[:50])
        )

    if llm_context.context_notes:
        parts.append("")
        parts.append("NOTES:")
        for note in llm_context.context_notes:
            parts.append(f"- {note}")

    parts.extend([
        "",
        "INSTRUCTIONS:",
        "1. Read the full text and understand the intended meaning",
        "2. Identify all errors, prioritizing the user's known patterns",
        "3. For each error, provide: original, correction, error type, brief friendly explanation",
        "4. Flag any real-word errors (homophones in wrong context)",
        "5. Do NOT flag words in the personal dictionary",
        "6. Return structured JSON for frontend display",
        "",
    ])

    if context:
        parts.append(f"Context: {context}")
        parts.append("")

    parts.extend([
        "USER TEXT:",
        f'"{text}"',
        "",
        "Return corrections in JSON format:",
        '[{"original": "word", "suggested": "word", "type": "spelling|grammar|confusion|homophone", "explanation": "brief friendly explanation"}]',
    ])

    return "\n".join(parts)


def build_explanation_prompt(
    original: str,
    suggested: str,
    correction_type: str,
) -> str:
    """Build a prompt to generate a user-friendly explanation."""
    return f"""Explain why "{original}" should be "{suggested}" in simple terms.
This is a {correction_type} issue.
Keep the explanation brief (1-2 sentences) and encouraging.
Do not use technical grammar terms."""
