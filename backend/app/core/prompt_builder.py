"""Dynamic prompt construction for LLM calls."""


def build_correction_prompt(
    text: str,
    user_patterns: list[dict],
    confusion_pairs: list[dict],
    context: str | None = None,
) -> str:
    """Build a personalized correction prompt based on user's error profile."""
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
