"""Prompt construction for the AI Coach chat feature."""

from app.models.error_log import LLMContext


def build_coach_system_prompt(
    llm_context: LLMContext | None = None,
    writing_context: str | None = None,
    session_stats: dict | None = None,
) -> str:
    """Build the system prompt for the AI writing coach.

    The coach is warm, encouraging, and concise. It knows the user's
    writing profile and current document context, but never writes for them.
    """
    parts: list[str] = [
        "You are a warm, encouraging writing coach helping a talented writer who has dyslexia.",
        "You genuinely believe in this person's ideas and ability.",
        "",
        "RULES:",
        "- Keep replies concise: 2-4 sentences max unless they ask for more detail",
        "- Never write their essay or paragraphs for them — guide, don't ghost-write",
        "- Be positive and specific — praise what's working before suggesting changes",
        "- Use simple, friendly language — like a supportive friend, not a professor",
        "- Never use words like 'wrong', 'mistake', 'error', or 'incorrect'",
        "- If they seem frustrated, acknowledge it and encourage them",
        "- If they ask about spelling or grammar, explain gently without technical jargon",
        "",
    ]

    # Inject user profile context
    if llm_context is not None:
        parts.append("WRITER PROFILE:")

        if llm_context.mastered_words:
            parts.append(
                "  Words they've recently mastered: "
                + ", ".join(llm_context.mastered_words[:10])
            )

        if llm_context.confusion_pairs:
            pairs = [
                f"{p['word_a']}/{p['word_b']}"
                for p in llm_context.confusion_pairs[:5]
            ]
            parts.append("  Sound-alikes they sometimes mix up: " + ", ".join(pairs))

        if llm_context.improvement_trends:
            improving = [
                t["error_type"]
                for t in llm_context.improvement_trends
                if t.get("trend") == "improving"
            ]
            if improving:
                parts.append(
                    "  Areas they're improving in: " + ", ".join(improving[:5])
                )

        parts.append(f"  Writing level: {llm_context.writing_level}")

        if llm_context.total_stats:
            words = llm_context.total_stats.get("total_words", 0)
            sessions = llm_context.total_stats.get("total_sessions", 0)
            if words > 0:
                parts.append(f"  Total words written: ~{words} across {sessions} sessions")

        parts.append("")

    # Inject current session stats
    if session_stats:
        words = session_stats.get("totalWordsWritten", 0)
        minutes = session_stats.get("timeSpent", 0)
        corrections = session_stats.get("correctionsApplied", 0)
        stats_parts = []
        if words > 0:
            stats_parts.append(f"{words} words written")
        if minutes > 0:
            stats_parts.append(f"{minutes} min spent")
        if corrections > 0:
            stats_parts.append(f"{corrections} suggestions applied")
        if stats_parts:
            parts.append("THIS SESSION: " + ", ".join(stats_parts))
            parts.append("")

    # Inject truncated document context
    if writing_context:
        truncated = writing_context[:1500]
        if len(writing_context) > 1500:
            truncated += "..."
        parts.append("CURRENT DOCUMENT (truncated):")
        parts.append(f'"""{truncated}"""')
        parts.append("")

    return "\n".join(parts)
