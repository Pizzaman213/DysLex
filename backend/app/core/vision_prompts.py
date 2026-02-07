"""
Prompt templates for vision-based idea extraction using Cosmos Reason2 8B.
"""


VISION_EXTRACT_SYSTEM_PROMPT = """You analyze images of whiteboards, handwritten notes, diagrams, and other visual content to extract ideas for a mind map. Output ONLY a JSON object.

STEP 1: Examine the image carefully. Identify all text, diagrams, arrows, groupings, and visual relationships.
STEP 2: Determine the CENTRAL TOPIC or THEME. Write a short 2-5 word label for it.
STEP 3: Extract each separate idea, concept, or point visible in the image.
STEP 4: For each idea, write an AI-generated "body" that EXPLAINS the idea in 1-2 clear sentences. Add useful context. Do NOT just transcribe the text verbatim — expand on it.
STEP 5: If one idea has 2+ specific details or sub-points visible, list them as "sub_ideas" with AI-written bodies. Otherwise set "sub_ideas" to [].

OUTPUT FORMAT:
{"topic": "<central theme in 2-5 words>", "cards": [<array of idea objects>]}

RULES:
- "topic" = 2-5 word label for the overall central theme.
- "body" = 1-2 AI-written sentences that explain and expand on the idea. NOT a verbatim copy of text in the image.
- "title" = 3-8 word summary.
- Each topic must have a UNIQUE title. No duplicates.
- "sub_ideas" body: 1-2 AI-written sentences explaining the detail.
- IDs: "topic-1", "topic-2", etc. Sub-idea IDs: "topic-1-sub-1", etc.
- If the image is blank, unreadable, or contains no meaningful content, return {"topic": "", "cards": []}.

Output ONLY valid JSON. No markdown, no explanation, no code fences."""


def build_vision_extract_prompt(user_hint: str | None = None) -> str:
    """
    Build the user prompt for vision-based idea extraction.

    Args:
        user_hint: Optional hint from the user about what the image contains

    Returns:
        Formatted prompt string
    """
    base = "Look at this image and extract all ideas, concepts, and points into structured mind map nodes. Write each \"body\" as an AI-generated explanation with context — do NOT just copy text from the image. Include the central \"topic\" label."

    if user_hint:
        base += f"\n\nUser context: {user_hint}"

    return base
