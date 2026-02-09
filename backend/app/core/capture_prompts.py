"""
Prompt templates for Capture Mode LLM operations.
"""


EXTRACT_IDEAS_SYSTEM_PROMPT = """You are an idea extraction engine for a mind map tool. You read user text and output ONLY a single JSON object — no markdown, no explanation, no code fences.

TASK:
1. Identify the CENTRAL TOPIC (2-5 word label for the overall theme).
2. Split the text into separate ideas, claims, or points (each becomes a "card").
3. For each card, write an AI-generated "body" that EXPLAINS the idea in 1-2 clear sentences. Add useful context, background, or significance. Do NOT copy the user's words verbatim — expand on them.
4. If a card has 2+ specific supporting details, list them as "sub_ideas". Otherwise set "sub_ideas" to [].

EXACT JSON SCHEMA — every card and sub_idea MUST match this structure:

{
  "topic": "<string: 2-5 word central theme>",
  "cards": [
    {
      "id": "<string: 'topic-1', 'topic-2', etc.>",
      "title": "<string: 3-8 word summary of the idea>",
      "body": "<string: 1-2 AI-written sentences explaining the idea>",
      "sub_ideas": [
        {
          "id": "<string: 'topic-1-sub-1', 'topic-1-sub-2', etc.>",
          "title": "<string: 3-8 word summary of the detail>",
          "body": "<string: 1-2 AI-written sentences explaining the detail>"
        }
      ]
    }
  ]
}

REQUIRED FIELDS (never omit any):
- Every card MUST have: "id", "title", "body", "sub_ideas"
- Every sub_idea MUST have: "id", "title", "body"
- "sub_ideas" is an array — use [] when there are no sub-ideas

RULES:
- "topic": 2-5 word label for the central theme. This becomes the mind map center node.
- "title": 3-8 word summary. Each card title must be UNIQUE — no duplicates.
- "body": 1-2 AI-written sentences that explain and expand on the idea with added context. NOT a copy of the input text.
- Card IDs: "topic-1", "topic-2", "topic-3", etc.
- Sub-idea IDs: "topic-1-sub-1", "topic-1-sub-2", etc.
- If input is empty or gibberish, return: {"topic": "", "cards": []}

Output ONLY valid JSON. No markdown fences. No extra text."""



# Conservative character limit for the transcript portion.
# Rough estimate: 1 token ≈ 4 chars.  We budget ~3 000 tokens for the
# transcript so the full request (system + example + transcript + 2 048
# generation tokens) stays well within the model's context window.
_MAX_TRANSCRIPT_CHARS = 128_000


def build_extract_ideas_prompt(
    transcript: str,
    existing_titles: list[str] | None = None,
) -> str:
    """
    Build the user prompt for idea extraction.

    Args:
        transcript: The voice transcript to analyze
        existing_titles: Titles already extracted (for incremental dedup)

    Returns:
        Formatted prompt string
    """
    # Truncate long transcripts to avoid exceeding the model context window
    if len(transcript) > _MAX_TRANSCRIPT_CHARS:
        transcript = transcript[:_MAX_TRANSCRIPT_CHARS] + "…"

    dedup_section = ""
    if existing_titles:
        titles_str = ", ".join(f'"{t}"' for t in existing_titles)
        dedup_section = f"""
ALREADY EXTRACTED (do NOT regenerate these — only output NEW ideas):
{titles_str}

"""

    return f"""{dedup_section}EXAMPLE 1 (no sub_ideas):

Input: "Nvidia makes gpus. Microsoft makes software."

Output:
{{"topic":"Tech Industry Giants","cards":[{{"id":"topic-1","title":"Nvidia manufactures GPUs","body":"Nvidia is the leading manufacturer of graphics processing units, essential for gaming, AI training, and scientific computing.","sub_ideas":[]}},{{"id":"topic-2","title":"Microsoft develops software","body":"Microsoft creates widely-used software including Windows, the Office suite, and the Azure cloud platform.","sub_ideas":[]}}]}}

EXAMPLE 2 (with sub_ideas — note every sub_idea has "id", "title", AND "body"):

Input: "I want a pet for my apartment. Dogs are fun but loud. Cats are quiet and independent. Fish are easy but boring."

Output:
{{"topic":"Choosing an Apartment Pet","cards":[{{"id":"topic-1","title":"Desire for a companion animal","body":"The user wants a pet that fits well in an apartment setting, balancing companionship with practical living constraints.","sub_ideas":[]}},{{"id":"topic-2","title":"Comparing pet options","body":"Several pet types are being weighed against apartment-friendly criteria like noise, independence, and maintenance.","sub_ideas":[{{"id":"topic-2-sub-1","title":"Dogs are fun but noisy","body":"Dogs offer high companionship and energy but may be too loud for apartment living with thin walls."}},{{"id":"topic-2-sub-2","title":"Cats are quiet and low-maintenance","body":"Cats suit apartments well due to their independence and quiet nature, requiring less active attention."}},{{"id":"topic-2-sub-3","title":"Fish are easy but lack interaction","body":"Fish require minimal care but offer little emotional bonding compared to dogs or cats."}}]}}]}}

Now extract ideas from this text. Write each "body" as an AI-generated explanation — do NOT copy the input words. Add context, background, and why it matters. Every card and sub_idea MUST include "id", "title", and "body".

Input: "{transcript}"

Output:
"""
