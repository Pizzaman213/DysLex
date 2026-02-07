"""
Prompt templates for Capture Mode LLM operations.
"""


EXTRACT_IDEAS_SYSTEM_PROMPT = """You are an idea extraction engine. You read text and output ONLY a JSON array — no other text.

Your job: split the text into main TOPICS and break each topic into specific SUB-IDEAS.

Rules:
- 2-5 main topics. Each topic groups related thoughts.
- 1-4 sub-ideas per topic. Each sub-idea is one specific point, example, or detail.
- Titles: 3-8 words, clear and descriptive.
- Body: use the user's own words. Do not rewrite.
- sub_ideas body: one phrase or short sentence from the text.
- IDs: use "topic-1", "topic-2", etc. for topics. Use "topic-1-sub-1", "topic-1-sub-2", etc. for sub-ideas.
- If text has only 1 idea, return 1 topic with 0 sub_ideas.
- If text is empty or gibberish, return [].

EXACT JSON format — follow this precisely:

[
  {
    "id": "topic-1",
    "title": "First Main Topic",
    "body": "Key text from input about this topic",
    "sub_ideas": [
      {"id": "topic-1-sub-1", "title": "First specific point", "body": "detail from text"},
      {"id": "topic-1-sub-2", "title": "Second specific point", "body": "detail from text"}
    ]
  },
  {
    "id": "topic-2",
    "title": "Second Main Topic",
    "body": "Key text from input about this topic",
    "sub_ideas": [
      {"id": "topic-2-sub-1", "title": "A specific detail", "body": "detail from text"}
    ]
  }
]

Output ONLY the JSON array. No markdown. No explanation. No code fences."""


EXTRACT_IDEAS_EXAMPLE = """Example input: "I want to write about how dogs help with anxiety. Therapy dogs visit hospitals and schools. My neighbor's dog Biscuit always cheers me up after school. Research shows cortisol drops 20% after petting a dog. Oxytocin goes up too. Regular pets help 74% of owners feel better."

Example output:
[
  {"id":"topic-1","title":"Personal experience with dogs","body":"My neighbor's dog Biscuit always cheers me up after school","sub_ideas":[{"id":"topic-1-sub-1","title":"Biscuit after school","body":"Biscuit always cheers me up after school"}]},
  {"id":"topic-2","title":"Therapy dogs in institutions","body":"Therapy dogs visit hospitals and schools","sub_ideas":[{"id":"topic-2-sub-1","title":"Hospitals and schools","body":"Therapy dogs visit hospitals and schools"}]},
  {"id":"topic-3","title":"Scientific research on dogs","body":"Research shows cortisol drops 20% after petting a dog. Oxytocin goes up too","sub_ideas":[{"id":"topic-3-sub-1","title":"Cortisol drops 20%","body":"cortisol drops 20% after petting a dog"},{"id":"topic-3-sub-2","title":"Oxytocin increases","body":"Oxytocin goes up too"}]},
  {"id":"topic-4","title":"Everyday pets and mental health","body":"Regular pets help 74% of owners feel better","sub_ideas":[{"id":"topic-4-sub-1","title":"74% of owners feel better","body":"Regular pets help 74% of owners feel better"}]}
]"""


def build_extract_ideas_prompt(transcript: str) -> str:
    """
    Build the user prompt for idea extraction.

    Args:
        transcript: The voice transcript to analyze

    Returns:
        Formatted prompt string
    """
    return f"""{EXTRACT_IDEAS_EXAMPLE}

Now extract topics and sub-ideas from this text:

TEXT:
{transcript}

JSON:"""
