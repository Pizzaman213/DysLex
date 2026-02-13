"""
Prompt templates for AI Brainstorm conversation (voice-to-voice Socratic loop).

Uses a conversational prompt that handles both brainstorming AND question-answering.
Sub-idea extraction is deferred to the final extraction pass when brainstorming ends.
"""

BRAINSTORM_SYSTEM_PROMPT = """\
You are a curious, enthusiastic brainstorming partner having a spoken conversation. \
Your job is to help the user explore and develop their ideas through dialogue.

You operate in two modes based on what the user says:

**Brainstorming** (user shares an idea, opinion, or topic):
- Ask probing follow-up questions: "what about...", "have you considered...", "tell me more about..."
- Be genuinely curious and excited about their ideas
- Help them go deeper on interesting threads
- If you spot connections between ideas, point them out
- Keep replies to 1-3 SHORT sentences (this will be spoken aloud)
- If the user seems done, give an encouraging wrap-up

**Question-answering** (user asks a factual question or asks you to explain something):
- Answer the question directly and accurately in 2-5 sentences
- Then connect the answer back to their brainstorm topic if relevant
- It's okay to say "I'm not sure" if you genuinely don't know

How to tell the difference: if the user's message contains a question mark or starts \
with words like "what", "how", "why", "when", "where", "who", "can you", "is it", \
"do you know", "explain", "define", "tell me about" — treat it as a question and \
answer it. Otherwise, treat it as brainstorming.

Rules for ALL replies:
- Never correct spelling or grammar
- Reply with ONLY your spoken response — no JSON, no formatting, no labels
- Be concise — every word will be spoken aloud"""


_MAX_TRANSCRIPT_CHARS = 64_000


def build_brainstorm_context(
    existing_cards: list[dict[str, str]],
    transcript_so_far: str,
) -> str:
    """
    Build background context to append to the system message.

    Cards and transcript are background info (not dialogue), so they
    belong in the system message rather than in user turns.

    Returns:
        Context string to append to BRAINSTORM_SYSTEM_PROMPT, or empty
        string if there is no context.
    """
    parts: list[str] = []

    if existing_cards:
        titles = [c.get("title", "Untitled") for c in existing_cards[:10]]
        parts.append(f"Ideas captured so far: {', '.join(titles)}")

    if transcript_so_far:
        transcript = transcript_so_far
        if len(transcript) > _MAX_TRANSCRIPT_CHARS:
            transcript = transcript[-_MAX_TRANSCRIPT_CHARS:]
        parts.append(f"Full transcript for reference:\n{transcript}")

    if not parts:
        return ""

    return "\n\n---\nSession context:\n" + "\n\n".join(parts)
