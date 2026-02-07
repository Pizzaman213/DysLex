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
        desc = getattr(pattern, 'description', None) or f"{getattr(pattern, 'misspelling', '?')} -> {getattr(pattern, 'correction', '?')}"
        prompt_parts.append(f"- {desc}")

    if confusion_pairs:
        prompt_parts.append("")
        prompt_parts.append("The user often confuses these word pairs:")
        for pair in confusion_pairs[:5]:
            w1 = getattr(pair, 'word_a', None) or (pair.get('word1', '?') if isinstance(pair, dict) else '?')
            w2 = getattr(pair, 'word_b', None) or (pair.get('word2', '?') if isinstance(pair, dict) else '?')
            prompt_parts.append(f"- {w1} / {w2}")

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
) -> tuple[str, str]:
    """Build a personalised correction prompt using the full LLMContext object.

    Returns (system_message, user_message) tuple for proper chat formatting.
    """
    # --- System message: instructions + user profile ---
    system_parts: list[str] = [
        "You are a warm, supportive writing coach helping a talented thinker who has dyslexia.",
        "Your job is to gently catch small slip-ups while celebrating what the writer does well.",
        "Preserve the user's voice and intent — they have great ideas, and your role is to help those ideas shine.",
        "Frame every suggestion as a small tweak, never as a correction of something 'wrong'.",
        "",
    ]

    # User error profile section
    system_parts.append("USER ERROR PROFILE:")

    if llm_context.top_errors:
        system_parts.append("Most common errors:")
        for err in llm_context.top_errors[:20]:
            system_parts.append(
                f'  - "{err["misspelling"]}" -> "{err["correction"]}" ({err["frequency"]}x)'
            )

    # Error type distribution
    non_zero_types = {k: v for k, v in llm_context.error_types.items() if v > 0}
    if non_zero_types:
        system_parts.append("Error type breakdown:")
        for etype, pct in sorted(non_zero_types.items(), key=lambda x: -x[1]):
            system_parts.append(f"  - {etype}: {pct}%")

    if llm_context.confusion_pairs:
        system_parts.append("Frequently confused word pairs:")
        for pair in llm_context.confusion_pairs[:10]:
            system_parts.append(f'  - {pair["word_a"]} / {pair["word_b"]} ({pair["count"]}x)')

    if llm_context.grammar_patterns:
        system_parts.append("User's frequent grammar patterns:")
        for gp in llm_context.grammar_patterns[:10]:
            system_parts.append(f'  - [{gp["subtype"]}] "{gp["misspelling"]}" -> "{gp["correction"]}" ({gp["frequency"]}x)')

    system_parts.append(f"Writing level: {llm_context.writing_level}")

    if llm_context.personal_dictionary:
        system_parts.append(
            "Personal dictionary (do NOT flag these words): "
            + ", ".join(llm_context.personal_dictionary[:50])
        )

    if llm_context.mastered_words:
        system_parts.append(
            "Words user recently mastered (lower priority): "
            + ", ".join(llm_context.mastered_words[:20])
        )
        system_parts.append(
            "  -> If you see these words used correctly, celebrate it! "
            "e.g. 'Nice — you nailed [word] this time!'"
        )

    if llm_context.improvement_trends:
        system_parts.append("Improvement trends by error type:")
        for trend in llm_context.improvement_trends[:8]:
            label = trend.get("trend", "stable")
            pct = trend.get("change_percent", 0)
            system_parts.append(f"  - {trend['error_type']}: {label} ({pct:+.0f}%)")
        system_parts.append(
            "  -> For improving areas, praise progress (e.g. 'You've been getting better at this!'). "
            "For areas needing attention, be extra gentle and encouraging."
        )

    if llm_context.total_stats:
        sessions = llm_context.total_stats.get("total_sessions", 0)
        words = llm_context.total_stats.get("total_words", 0)
        system_parts.append(f"User stats: {sessions} sessions, ~{words} words written")

    if llm_context.recent_document_topics:
        system_parts.append(
            "Recent document topics: " + ", ".join(llm_context.recent_document_topics[:5])
        )

    if llm_context.correction_aggressiveness < 30:
        system_parts.append(
            "CORRECTION LEVEL: LOW — Only flag clear, unambiguous errors. "
            "Skip stylistic suggestions and borderline issues."
        )
    elif llm_context.correction_aggressiveness > 70:
        system_parts.append(
            "CORRECTION LEVEL: HIGH — Flag everything including style, word choice, "
            "and minor grammar. Be thorough."
        )

    if llm_context.context_notes:
        system_parts.append("")
        system_parts.append("NOTES:")
        for note in llm_context.context_notes:
            system_parts.append(f"- {note}")

    system_parts.extend([
        "",
        "INSTRUCTIONS:",
        "1. Read the full text and understand the intended meaning",
        "2. Identify all errors, prioritizing the user's known patterns",
        "3. For each issue, provide: original, correction, error_type, confidence, explanation",
        "4. Flag any real-word errors (homophones in wrong context)",
        "5. Do NOT flag words in the personal dictionary",
        "6. Beyond corrections, also suggest improvements for clarity, word choice, and style",
        "7. If the text has no errors and no recommendations, return an empty array: []",
        "",
        "GRAMMAR DETECTION (Dyslexia-specific patterns):",
        "Pay special attention to these grammar issues common in dyslexic writing:",
        "- Subject-verb agreement: 'The dogs runs' -> 'The dogs run'",
        "- Tense consistency: Mixing past/present tense within a paragraph",
        "- Article usage: Missing 'a/an/the' or wrong choice ('a apple' -> 'an apple')",
        "- Word order: Scrambled syntax that obscures meaning",
        "- Missing function words: Dropped prepositions, articles, or conjunctions",
        "- Run-on sentences: Multiple independent clauses without proper punctuation",
        "",
        "RECOMMENDATIONS:",
        "In addition to error corrections, suggest improvements when you notice:",
        "- Clarity: Awkward phrasing that could be clearer or simpler",
        "- Word choice: A more precise or natural word exists",
        "- Style: Repetitive words, passive voice that weakens meaning, or wordy phrases",
        "- Sentence flow: Choppy sentences that could be combined, or long ones that should be split",
        "Keep recommendations encouraging — frame them as options, not requirements.",
        "Use lower confidence (0.5-0.8) for recommendations vs corrections (0.85-1.0).",
        "",
        "TONE GUIDELINES:",
        "- Start explanations with something positive when possible ('Nice sentence!', 'Good word choice!')",
        "- Use warm, friendly language: 'Almost there!', 'Just a small tweak', 'Easy fix'",
        "- NEVER use words like 'wrong', 'mistake', 'error', 'incorrect', or 'fault' in explanations",
        "- Instead use: 'try', 'swap', 'consider', 'tweak', 'small adjustment', 'just switch'",
        "- If the user has been improving at a pattern, note it: 'You've been getting better at this!'",
        "- Keep explanations brief and conversational — like a friend helping, not a teacher grading",
        "",
        "OUTPUT FORMAT:",
        "You MUST respond with ONLY a JSON array. No explanation, no markdown, no extra text.",
        "Each object in the array MUST have exactly these fields:",
        "",
        "  original     (string, required) — The exact text as it appears in the document",
        "  correction   (string, required) — The corrected or improved replacement text",
        '  error_type   (string, required) — One of:',
        '                Corrections: "spelling", "grammar", "homophone", "phonetic",',
        '                  "subject_verb", "tense", "article", "word_order",',
        '                  "missing_word", "run_on"',
        '                Recommendations: "clarity", "style", "word_choice"',
        "  confidence   (number, required) — 0.0 to 1.0 (higher for errors, lower for suggestions)",
        "  explanation  (string, required) — One-sentence friendly explanation",
        "",
        "EXAMPLE OUTPUT:",
        "[",
        '  {"original": "becuase", "correction": "because", "error_type": "spelling", "confidence": 0.99, "explanation": "Almost there! Just swap the u and a — easy fix."},',
        '  {"original": "there house", "correction": "their house", "error_type": "homophone", "confidence": 0.95, "explanation": "Nice sentence! Use \'their\' here since you\'re showing ownership."},',
        '  {"original": "The dogs runs", "correction": "The dogs run", "error_type": "subject_verb", "confidence": 0.97, "explanation": "Good thought — just drop the s from runs to match the plural dogs."},',
        '  {"original": "a apple", "correction": "an apple", "error_type": "article", "confidence": 0.98, "explanation": "Small tweak — swap to \'an\' before vowel sounds."},',
        '  {"original": "I went to the store I bought milk", "correction": "I went to the store. I bought milk.", "error_type": "run_on", "confidence": 0.85, "explanation": "Two great thoughts here — try a period between them so each one lands."},',
        '  {"original": "very very important", "correction": "extremely important", "error_type": "style", "confidence": 0.65, "explanation": "Your point is strong! Try \'extremely\' to punch it up even more."},',
        '  {"original": "The thing that happened was bad", "correction": "The incident was unfortunate", "error_type": "clarity", "confidence": 0.6, "explanation": "Good idea — more specific wording makes your point even clearer."},',
        '  {"original": "used", "correction": "utilized", "error_type": "word_choice", "confidence": 0.5, "explanation": "Nice word! You could also consider \'utilized\' to add a bit more precision."}',
        "]",
        "",
        "If there are no errors and no recommendations, respond with exactly: []",
    ])

    system_msg = "\n".join(system_parts)

    # --- User message: just the text to analyze ---
    user_parts: list[str] = []
    if context:
        user_parts.append(f"Context: {context}")
        user_parts.append("")
    user_parts.append("Please analyze this text and return corrections as a JSON array:")
    user_parts.append(f'"{text}"')

    user_msg = "\n".join(user_parts)

    return system_msg, user_msg


def build_explanation_prompt(
    original: str,
    suggested: str,
    correction_type: str,
) -> str:
    """Build a prompt to generate a user-friendly explanation."""
    return f"""You're a warm, supportive writing coach. Explain why "{original}" could be swapped to "{suggested}".
This is a {correction_type} suggestion.
Start with something positive or encouraging.
Keep it brief (1-2 sentences) and friendly — like a helpful friend, not a teacher.
Never use words like "wrong", "mistake", "error", or "incorrect".
Use words like "try", "swap", "tweak", or "consider" instead."""
