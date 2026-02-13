"""Mind map endpoints — build scaffold from nodes/edges via LLM."""

import json
import logging

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class MindMapNode(BaseModel):
    id: str
    title: str
    body: str
    cluster: int
    x: float
    y: float


class MindMapEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship: str | None = None


class BuildScaffoldRequest(BaseModel):
    nodes: list[MindMapNode]
    edges: list[MindMapEdge]
    writing_goal: str | None = None


class ScaffoldSection(BaseModel):
    heading: str
    hint: str
    nodeIds: list[str]  # noqa: N815
    suggestedContent: str | None = None  # noqa: N815


class BuildScaffoldResponse(BaseModel):
    title: str
    sections: list[ScaffoldSection]


# ---------------------------------------------------------------------------
# LLM-powered scaffold builder
# ---------------------------------------------------------------------------

SCAFFOLD_SYSTEM_PROMPT = """\
You are a writing coach helping a dyslexic thinker turn scattered ideas into a clear essay structure.

You will receive a list of idea nodes (each with an id, title, and body) and connections between them.
Your job is to organize these raw ideas into a logical essay scaffold that the writer can follow.

Rules:
- Preserve the writer's voice and ideas — do NOT rewrite their thoughts, just organize them.
- Every section must reference which node IDs it draws from (nodeIds).
- Write a short, encouraging hint for each section to guide the writer.
- Suggest opening content for each section that weaves the raw ideas together naturally.
- The suggestedContent should read like a rough first draft paragraph — conversational, not stiff.
- Keep headings simple and clear.
- Always include an Introduction and Conclusion.

Respond with ONLY valid JSON in this exact format (no markdown fences, no extra text):
{
  "title": "Essay title derived from the central idea",
  "sections": [
    {
      "heading": "Section heading",
      "hint": "Encouraging guidance for this section",
      "nodeIds": ["id1", "id2"],
      "suggestedContent": "A rough draft paragraph weaving the ideas together..."
    }
  ]
}\
"""


def _build_user_prompt(request: BuildScaffoldRequest) -> str:
    """Build the user message describing the mind map."""
    lines = ["Here are the idea nodes:\n"]
    for node in request.nodes:
        lines.append(f"- [{node.id}] \"{node.title}\": {node.body}")

    if request.edges:
        lines.append("\nConnections between ideas:")
        for edge in request.edges:
            rel = f" ({edge.relationship})" if edge.relationship else ""
            lines.append(f"- {edge.source} → {edge.target}{rel}")

    if request.writing_goal:
        lines.append(f"\nThe writer's goal: {request.writing_goal}")

    lines.append("\nOrganize these ideas into a clear essay scaffold.")
    return "\n".join(lines)


async def _llm_build_scaffold(request: BuildScaffoldRequest) -> BuildScaffoldResponse | None:
    """Call the LLM to organize mind map nodes into a scaffold."""
    if not settings.nvidia_nim_api_key:
        logger.warning("NVIDIA_NIM_API_KEY not set — falling back to simple scaffold")
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

        # Validate nodeIds reference actual node IDs
        valid_ids = {n.id for n in request.nodes}
        sections = []
        for s in parsed.get("sections", []):
            node_ids = [nid for nid in s.get("nodeIds", []) if nid in valid_ids]
            # If LLM hallucinated IDs, fall back to all node IDs for that section
            if not node_ids:
                node_ids = [n.id for n in request.nodes]
            sections.append(
                ScaffoldSection(
                    heading=s.get("heading", "Section"),
                    hint=s.get("hint", "Develop this section."),
                    nodeIds=node_ids,
                    suggestedContent=s.get("suggestedContent"),
                )
            )

        return BuildScaffoldResponse(
            title=parsed.get("title", request.nodes[0].title or "Untitled"),
            sections=sections,
        )

    except httpx.HTTPError as e:
        logger.error(f"Scaffold LLM API error: {e}")
        return None
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse scaffold LLM response: {e}")
        return None


# ---------------------------------------------------------------------------
# Simple fallback (no LLM)
# ---------------------------------------------------------------------------


def _simple_scaffold(request: BuildScaffoldRequest) -> BuildScaffoldResponse:
    """Build a basic scaffold by grouping nodes by cluster."""
    clusters: dict[int, list[MindMapNode]] = {}
    for node in request.nodes:
        clusters.setdefault(node.cluster, []).append(node)

    title = request.nodes[0].title or "Untitled"
    sections: list[ScaffoldSection] = [
        ScaffoldSection(
            heading="Introduction",
            hint="Introduce your topic and state your main idea.",
            nodeIds=[request.nodes[0].id],
        )
    ]

    for cluster_id in sorted(clusters.keys()):
        cluster_nodes = clusters[cluster_id]
        node_ids = [n.id for n in cluster_nodes]
        titles = [n.title for n in cluster_nodes if n.title]
        heading = titles[0] if titles else f"Section {cluster_id + 1}"
        hint = "Develop this section with supporting details."

        suggested = "\n\n".join(
            f"{n.title}: {n.body}" for n in cluster_nodes if n.body
        ) or None

        sections.append(
            ScaffoldSection(
                heading=heading,
                hint=hint,
                nodeIds=node_ids,
                suggestedContent=suggested,
            )
        )

    sections.append(
        ScaffoldSection(
            heading="Conclusion",
            hint="Summarize your key points and restate your main idea.",
            nodeIds=[n.id for n in request.nodes],
        )
    )

    return BuildScaffoldResponse(title=title, sections=sections)


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.post("/build-scaffold", response_model=BuildScaffoldResponse)
async def build_scaffold(request: BuildScaffoldRequest) -> BuildScaffoldResponse:
    """Build a writing scaffold from mind map nodes and edges.

    Uses the LLM to intelligently organize scattered ideas into a
    logical essay structure. Falls back to simple clustering if the
    LLM is unavailable.
    """
    if not request.nodes:
        return BuildScaffoldResponse(title="Untitled", sections=[])

    # Try LLM first
    result = await _llm_build_scaffold(request)
    if result is not None:
        return result

    # Fallback to simple clustering
    logger.info("Using simple scaffold fallback")
    return _simple_scaffold(request)
