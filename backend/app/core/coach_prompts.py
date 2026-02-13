"""Prompt construction for the AI Coach chat feature."""

from app.models.error_log import LLMContext


def build_coach_system_prompt(
    llm_context: LLMContext | None = None,
    writing_context: str | None = None,
    session_stats: dict | None = None,
    corrections_context: dict | None = None,
    mind_map_context: dict | None = None,
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

    # Inject corrections context
    if corrections_context:
        focused = corrections_context.get("focused_correction")
        active = corrections_context.get("active_corrections", [])

        if focused:
            parts.append("THE USER IS ASKING ABOUT THIS SPECIFIC SUGGESTION:")
            parts.append(f'  "{focused["original"]}" → "{focused["suggested"]}" (type: {focused["type"]})')
            if focused.get("explanation"):
                parts.append(f"  Brief explanation shown: {focused['explanation']}")
            parts.append("")
            parts.append("When explaining this suggestion:")
            parts.append("- Explain the underlying pattern (why this mix-up happens)")
            parts.append("- Give a quick memory trick or mnemonic if possible")
            parts.append("- Keep it warm and encouraging — 3-5 sentences")
            parts.append("- Never say 'error' or 'mistake' — say 'mix-up' or 'pattern'")
            parts.append("")

        if active:
            parts.append(f"ACTIVE SUGGESTIONS IN DOCUMENT ({len(active)} total):")
            for c in active[:10]:
                parts.append(f'  - "{c["original"]}" → "{c["suggested"]}" ({c["type"]})')
            parts.append("")

    # Inject truncated document context
    if writing_context:
        truncated = writing_context[:1500]
        if len(writing_context) > 1500:
            truncated += "..."
        parts.append("CURRENT DOCUMENT (truncated):")
        parts.append(f'"""{truncated}"""')
        parts.append("")

    # Inject mind map context (brainstormed ideas)
    if mind_map_context:
        central = mind_map_context.get("central_idea")
        ideas: list[dict] = mind_map_context.get("ideas", [])
        connections: list[dict] = mind_map_context.get("connections", [])
        _themes: list[str] = mind_map_context.get("themes", [])

        if central or ideas:
            parts.append("MIND MAP (writer's brainstormed ideas):")

            if central:
                parts.append(f"  Central idea / thesis: {central}")

            # Group ideas by theme, limit to 20
            if ideas:
                by_theme: dict[str, list[dict]] = {}
                for idea in ideas[:20]:
                    theme = idea.get("theme") or "Ungrouped"
                    by_theme.setdefault(theme, []).append(idea)

                for theme, theme_ideas in by_theme.items():
                    parts.append(f"  [{theme}]")
                    for idea in theme_ideas:
                        body = idea.get("body")
                        if body:
                            parts.append(f"    - {idea['title']}: {body[:80]}")
                        else:
                            parts.append(f"    - {idea['title']}")

            # Show connections, limit to 15
            if connections:
                parts.append("  Connections:")
                for conn in connections[:15]:
                    rel = conn.get("relationship")
                    if rel:
                        parts.append(
                            f"    - {conn['from_idea']} --[{rel}]--> {conn['to_idea']}"
                        )
                    else:
                        parts.append(
                            f"    - {conn['from_idea']} --> {conn['to_idea']}"
                        )

            parts.append("")
            parts.append(
                "Reference the writer's own brainstormed ideas by name when relevant. "
                "If they seem stuck, suggest which idea from their mind map they could develop next."
            )
            parts.append("")

    return "\n".join(parts)
