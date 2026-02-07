"""Essay scaffold generation endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.dependencies import CurrentUserId, DbSession

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


@router.post("", response_model=GenerateScaffoldResponse)
async def generate_scaffold(
    request: GenerateScaffoldRequest,
    user_id: CurrentUserId,
    db: DbSession,
) -> GenerateScaffoldResponse:
    """Generate a writing scaffold for the given topic.

    This creates a structured outline with sections, topic sentences,
    and helpful hints to guide the writing process.
    """
    # TODO: Implement LLM-based scaffold generation
    # For now, return a basic 5-paragraph essay structure

    essay_type = request.essay_type or "argumentative"

    # Default 5-paragraph essay structure
    sections = [
        ScaffoldSection(
            id="intro",
            title="Introduction",
            type="intro",
            suggested_topic_sentence=f"This essay will explore {request.topic}.",
            hints=[
                "Hook the reader with an interesting fact or question",
                "Provide background on the topic",
                "State your thesis clearly",
            ],
            order=0,
        ),
        ScaffoldSection(
            id="body1",
            title="First Main Point",
            type="body",
            suggested_topic_sentence=f"One key aspect of {request.topic} is...",
            hints=[
                "Start with a clear topic sentence",
                "Provide evidence or examples",
                "Explain how this supports your thesis",
            ],
            order=1,
        ),
        ScaffoldSection(
            id="body2",
            title="Second Main Point",
            type="body",
            suggested_topic_sentence=f"Another important consideration regarding {request.topic} is...",
            hints=[
                "Connect to your previous point",
                "Introduce new evidence",
                "Analyze and explain",
            ],
            order=2,
        ),
        ScaffoldSection(
            id="body3",
            title="Third Main Point",
            type="body",
            suggested_topic_sentence=f"Finally, when considering {request.topic}, we must examine...",
            hints=[
                "Introduce your strongest or final point",
                "Provide compelling evidence",
                "Tie back to your thesis",
            ],
            order=3,
        ),
        ScaffoldSection(
            id="conclusion",
            title="Conclusion",
            type="conclusion",
            suggested_topic_sentence=f"In conclusion, {request.topic} demonstrates...",
            hints=[
                "Restate your thesis in new words",
                "Summarize main points briefly",
                "End with a memorable closing thought",
            ],
            order=4,
        ),
    ]

    transitions = [
        "Furthermore,",
        "In addition,",
        "Moreover,",
        "However,",
        "On the other hand,",
        "As a result,",
        "Therefore,",
        "In conclusion,",
    ]

    return GenerateScaffoldResponse(
        sections=sections,
        transitions=transitions,
    )
