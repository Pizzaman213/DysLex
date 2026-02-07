"""
Prompt templates for Capture Mode LLM operations.
"""


EXTRACT_IDEAS_SYSTEM_PROMPT = """You split text into separate ideas for a mind map. Output ONLY a JSON object.

STEP 1: Read the text and identify the CENTRAL TOPIC or THEME the user is talking about. Write a short 2-5 word label for it.
STEP 2: Find each separate idea, claim, or point.
STEP 3: For each idea, write an AI-generated "body" that EXPLAINS the idea in 1-2 clear sentences. Add useful context, background, or why it matters. Do NOT just copy the user's words — expand on them.
STEP 4: If one idea has 2+ specific details, list them as "sub_ideas" with AI-written bodies that explain each detail. Otherwise set "sub_ideas" to [].

OUTPUT FORMAT:
{"topic": "<central theme in 2-5 words>", "cards": [<array of idea objects>]}

RULES:
- "topic" = 2-5 word label for the overall central theme. This becomes the center of the mind map.
- "body" = 1-2 AI-written sentences that explain and expand on the idea. Add context the user didn't say. NOT a copy of the input.
- "title" = 3-8 word summary.
- Each topic must have a UNIQUE title. No duplicates.
- "sub_ideas" body: 1-2 AI-written sentences explaining the detail with context and significance.
- IDs: "topic-1", "topic-2", etc. Sub-idea IDs: "topic-1-sub-1", etc.
- Empty or gibberish text → return {"topic": "", "cards": []}.

Output ONLY valid JSON. No markdown, no explanation, no code fences."""


def build_extract_ideas_prompt(transcript: str) -> str:
    """
    Build the user prompt for idea extraction.

    Args:
        transcript: The voice transcript to analyze

    Returns:
        Formatted prompt string
    """
    return f"""EXAMPLE:

Input: "Nvidia makes gpus. Microsoft makes software. Google has data centers."

Output:
{{"topic":"Tech Industry Giants","cards":[{{"id":"topic-1","title":"Nvidia makes GPUs","body":"Nvidia is the leading manufacturer of graphics processing units, which are essential for gaming, AI training, and scientific computing.","sub_ideas":[]}},{{"id":"topic-2","title":"Microsoft makes software","body":"Microsoft develops widely-used software including the Windows operating system, Office productivity suite, and Azure cloud platform.","sub_ideas":[]}},{{"id":"topic-3","title":"Google operates data centers","body":"Google runs massive data centers worldwide that power its search engine, cloud services, and AI research infrastructure.","sub_ideas":[]}}]}}

Now split this text into separate ideas. Write each "body" as an AI-generated explanation — do NOT just copy the input words. Add context, background, and why it matters. Include the central "topic" label.

Input: "{transcript}"

Output:
"""
