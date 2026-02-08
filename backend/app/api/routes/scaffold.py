"""Essay scaffold generation endpoint — powered by Nemotron LLM."""

import json
import logging

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class ScaffoldSection(BaseModel):
    """A single section in the scaffold."""

    id: str
    title: str
    type: str
    suggested_topic_sentence: str | None = None
    hints: list[str] | None = None
    order: int


class GenerateScaffoldRequest(BaseModel):
    """Request model for scaffold generation."""

    topic: str
    essay_type: str | None = None
    existing_ideas: list[str] | None = None


class GenerateScaffoldResponse(BaseModel):
    """Response model for scaffold generation."""

    sections: list[ScaffoldSection]
    transitions: list[str] | None = None


# ---------------------------------------------------------------------------
# LLM prompt
# ---------------------------------------------------------------------------

SCAFFOLD_SYSTEM_PROMPT = """\
You are a writing coach helping a dyslexic thinker plan an essay. \
Your job is to create a clear, encouraging scaffold they can follow.

Rules:
- Create sections tailored to the specific topic — NOT generic "First Main Point" placeholders.
- Each section needs a concrete, topic-specific title and suggested opening sentence.
- Write hints that are specific and actionable, not vague.
- Keep language warm and encouraging.
- Suggest useful transition words.

Respond with ONLY valid JSON (no markdown fences, no extra text):
{
  "sections": [
    {
      "id": "unique-id",
      "title": "Section title",
      "type": "intro" | "body" | "conclusion",
      "suggested_topic_sentence": "A concrete opening sentence for this section...",
      "hints": ["Specific, actionable hint 1", "Hint 2"],
      "order": 0
    }
  ],
  "transitions": ["Furthermore,", "However,", "As a result,"]
}\
"""


def _build_user_prompt(request: GenerateScaffoldRequest) -> str:
    """Build the user message for scaffold generation."""
    lines = [f"Topic: {request.topic}"]

    if request.essay_type:
        lines.append(f"Essay type: {request.essay_type}")

    if request.existing_ideas:
        lines.append("\nIdeas the writer already has:")
        for idea in request.existing_ideas:
            lines.append(f"- {idea}")

    lines.append("\nCreate a writing scaffold for this essay.")
    return "\n".join(lines)


async def _llm_generate_scaffold(
    request: GenerateScaffoldRequest,
) -> GenerateScaffoldResponse | None:
    """Call Nemotron to generate a topic-aware scaffold."""
    if not settings.nvidia_nim_api_key:
        logger.warning("NVIDIA_NIM_API_KEY not set — falling back to static scaffold")
        return None

    url = f"{settings.nvidia_nim_llm_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.nvidia_nim_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.nvidia_nim_llm_model,
        "messages": [
            {"role": "system", "content": SCAFFOLD_SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(request)},
        ],
        "temperature": 0.5,
        "max_tokens": 4096,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

        result = response.json()
        content = result["choices"][0]["message"]["content"]
        logger.info(f"Scaffold LLM response: {content[:300]}")

        # Strip markdown fences if present
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()

        parsed = json.loads(cleaned)

        sections = []
        for i, s in enumerate(parsed.get("sections", [])):
            sections.append(
                ScaffoldSection(
                    id=s.get("id", f"section-{i}"),
                    title=s.get("title", f"Section {i + 1}"),
                    type=s.get("type", "body"),
                    suggested_topic_sentence=s.get("suggested_topic_sentence"),
                    hints=s.get("hints"),
                    order=s.get("order", i),
                )
            )

        transitions = parsed.get("transitions")

        return GenerateScaffoldResponse(
            sections=sections,
            transitions=transitions,
        )

    except httpx.HTTPError as e:
        logger.error(f"Scaffold LLM API error: {e}")
        return None
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse scaffold LLM response: {e}")
        return None


# ---------------------------------------------------------------------------
# Static fallback
# ---------------------------------------------------------------------------


def _static_scaffold(topic: str) -> GenerateScaffoldResponse:
    """Hardcoded 5-paragraph fallback when Nemotron is unavailable."""
    sections = [
        ScaffoldSection(
            id="intro", title="Introduction", type="intro",
            suggested_topic_sentence=f"This essay will explore {topic}.",
            hints=["Hook the reader with an interesting fact or question",
                   "Provide background on the topic",
                   "State your thesis clearly"],
            order=0,
        ),
        ScaffoldSection(
            id="body1", title="First Main Point", type="body",
            suggested_topic_sentence=f"One key aspect of {topic} is...",
            hints=["Start with a clear topic sentence",
                   "Provide evidence or examples",
                   "Explain how this supports your thesis"],
            order=1,
        ),
        ScaffoldSection(
            id="body2", title="Second Main Point", type="body",
            suggested_topic_sentence=f"Another important consideration regarding {topic} is...",
            hints=["Connect to your previous point",
                   "Introduce new evidence",
                   "Analyze and explain"],
            order=2,
        ),
        ScaffoldSection(
            id="body3", title="Third Main Point", type="body",
            suggested_topic_sentence=f"Finally, when considering {topic}, we must examine...",
            hints=["Introduce your strongest or final point",
                   "Provide compelling evidence",
                   "Tie back to your thesis"],
            order=3,
        ),
        ScaffoldSection(
            id="conclusion", title="Conclusion", type="conclusion",
            suggested_topic_sentence=f"In conclusion, {topic} demonstrates...",
            hints=["Restate your thesis in new words",
                   "Summarize main points briefly",
                   "End with a memorable closing thought"],
            order=4,
        ),
    ]
    transitions = ["Furthermore,", "In addition,", "Moreover,", "However,",
                   "On the other hand,", "As a result,", "Therefore,", "In conclusion,"]
    return GenerateScaffoldResponse(sections=sections, transitions=transitions)


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.post("", response_model=GenerateScaffoldResponse)
async def generate_scaffold(
    request: GenerateScaffoldRequest,
) -> GenerateScaffoldResponse:
    """Generate a writing scaffold for the given topic using Nemotron.

    Falls back to a static template only if the LLM is unavailable.
    """
    result = await _llm_generate_scaffold(request)
    if result is not None:
        return result

    logger.info("Using static scaffold fallback")
    return _static_scaffold(request.topic)
