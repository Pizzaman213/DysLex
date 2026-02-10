"""
Prompt templates for Capture Mode LLM operations.
"""


EXTRACT_IDEAS_SYSTEM_PROMPT = """You are an idea extraction engine for a mind map tool. You read user text and output ONLY a single JSON object — no markdown, no explanation, no code fences.

TASK:
1. Identify or CREATE the CENTRAL TOPIC (2-5 word label for the overall theme). This becomes the MAIN IDEA at the center of the mind map. You MUST ALWAYS provide a central topic — even if the user's text is scattered or covers many things, find or invent the common thread that ties them together. NEVER return an empty topic.
2. Split the text into separate ideas, claims, or points (each becomes a "card"). These are the main branches that surround and connect to the central topic.
3. For each card, write an AI-generated "body" that EXPLAINS the idea in 1-2 clear sentences. Add useful context, background, or significance. Do NOT copy the user's words verbatim — expand on them.
4. EVERY card MUST have 2-4 "sub_ideas" — smaller, similar supporting ideas that surround their parent card like bubbles. These sub-ideas should be related details, examples, aspects, or angles of the parent card. NEVER leave sub_ideas empty. If the text doesn't explicitly mention supporting details, generate relevant ones that naturally support or expand on the parent idea.

MIND MAP STRUCTURE (everything surrounds and connects to the central idea):
- The "topic" is the ONE CENTRAL IDEA — the single bubble at the very center. Everything else is arranged AROUND it.
- Each "card" surrounds the central idea — they are placed around it and directly connected to it. Every card must clearly relate back to the central topic.
- Each "sub_idea" surrounds its parent card — smaller bubbles arranged around each card, all related to each other and to their parent.
- ALL ideas in the map are interconnected: the central idea is in the middle, cards surround it, and sub-ideas surround each card. Nothing floats alone.
- There is ONLY ONE central idea. Do NOT create multiple unrelated topics — find the single theme that ties everything together.
- You MUST ALWAYS generate a central topic. If the user's text seems random or covers unrelated things, find the broadest common theme (e.g. "Key Ideas", "Main Thoughts", "Brainstorm Topics"). NEVER leave the topic empty.

EXACT JSON SCHEMA — every card and sub_idea MUST match this structure:

{
  "topic": "<string: 2-5 word central theme — the MAIN IDEA>",
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
- "sub_ideas" MUST contain 2-4 items per card — NEVER an empty array

RULES:
- "topic": 2-5 word label that captures the ONE central theme connecting all the ideas. This is the single hub of the mind map — everything branches from it.
- "title": 3-8 word summary. Each card title must be UNIQUE — no duplicates. Every card must clearly relate back to the central topic.
- "body": 1-2 AI-written sentences that explain and expand on the idea with added context. NOT a copy of the input text.
- "sub_ideas": Each card MUST have 2-4 sub-ideas. These sub-ideas should be similar to each other and connected — they are a cohesive group of related supporting details, not random unrelated points. Generate relevant sub-ideas even if the user didn't explicitly mention them.
- Card IDs: "topic-1", "topic-2", "topic-3", etc.
- Sub-idea IDs: "topic-1-sub-1", "topic-1-sub-2", etc.
- If input is empty or gibberish, return: {"topic": "", "cards": []}
- For ALL other inputs, "topic" MUST be a non-empty string. Always find or create a central theme.

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

    return f"""{dedup_section}EXAMPLE 1 (every card has sub-idea bubbles):

Input: "Nvidia makes gpus. Microsoft makes software."

Output:
{{"topic":"Tech Industry Giants","cards":[{{"id":"topic-1","title":"Nvidia manufactures GPUs","body":"Nvidia is the leading manufacturer of graphics processing units, essential for gaming, AI training, and scientific computing.","sub_ideas":[{{"id":"topic-1-sub-1","title":"Gaming GPU dominance","body":"Nvidia's GeForce line powers the majority of PC gaming, setting the standard for real-time graphics performance."}},{{"id":"topic-1-sub-2","title":"AI and data center growth","body":"Nvidia's CUDA-enabled GPUs have become the backbone of modern AI training and cloud computing infrastructure."}},{{"id":"topic-1-sub-3","title":"Scientific computing applications","body":"Researchers use Nvidia GPUs for simulations, molecular modeling, and other computationally intensive scientific work."}}]}},{{"id":"topic-2","title":"Microsoft develops software","body":"Microsoft creates widely-used software including Windows, the Office suite, and the Azure cloud platform.","sub_ideas":[{{"id":"topic-2-sub-1","title":"Windows operating system","body":"Windows is the most widely used desktop OS worldwide, powering both personal and enterprise computing."}},{{"id":"topic-2-sub-2","title":"Office productivity suite","body":"Microsoft Office including Word, Excel, and PowerPoint remains the industry standard for business productivity."}},{{"id":"topic-2-sub-3","title":"Azure cloud platform","body":"Azure is Microsoft's cloud computing service competing with AWS, offering hosting, AI, and enterprise solutions."}}]}}]}}

EXAMPLE 2 (sub-idea bubbles branch off each main idea):

Input: "I want a pet for my apartment. Dogs are fun but loud. Cats are quiet and independent. Fish are easy but boring."

Output:
{{"topic":"Choosing an Apartment Pet","cards":[{{"id":"topic-1","title":"Desire for a companion animal","body":"The user wants a pet that fits well in an apartment setting, balancing companionship with practical living constraints.","sub_ideas":[{{"id":"topic-1-sub-1","title":"Companionship and emotional support","body":"Pets provide emotional comfort and reduce loneliness, which is a key motivation for apartment dwellers."}},{{"id":"topic-1-sub-2","title":"Apartment living constraints","body":"Limited space, noise rules, and landlord policies all factor into which pets are practical for apartment life."}}]}},{{"id":"topic-2","title":"Comparing pet options","body":"Several pet types are being weighed against apartment-friendly criteria like noise, independence, and maintenance.","sub_ideas":[{{"id":"topic-2-sub-1","title":"Dogs are fun but noisy","body":"Dogs offer high companionship and energy but may be too loud for apartment living with thin walls."}},{{"id":"topic-2-sub-2","title":"Cats are quiet and low-maintenance","body":"Cats suit apartments well due to their independence and quiet nature, requiring less active attention."}},{{"id":"topic-2-sub-3","title":"Fish are easy but lack interaction","body":"Fish require minimal care but offer little emotional bonding compared to dogs or cats."}}]}}]}}

Now extract ideas from this text. Write each "body" as an AI-generated explanation — do NOT copy the input words. Add context, background, and why it matters. Every card MUST have 2-4 sub-idea bubbles branching off it. Every card and sub_idea MUST include "id", "title", and "body".

Input: "{transcript}"

Output:
"""
