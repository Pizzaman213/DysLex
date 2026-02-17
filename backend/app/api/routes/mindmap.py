"""Mind map endpoints — build scaffold from nodes/edges via LLM."""

import json
import logging
import uuid

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


class SuggestConnectionsRequest(BaseModel):
    nodes: list[MindMapNode]
    edges: list[MindMapEdge]


class ConnectionSuggestion(BaseModel):
    id: str
    type: str  # "connection", "gap", or "cluster"
    sourceNodeId: str | None = None  # noqa: N815
    targetNodeId: str | None = None  # noqa: N815
    description: str
    confidence: float | None = None


class SuggestConnectionsResponse(BaseModel):
    suggestions: list[ConnectionSuggestion]
    clusterNames: dict[str, str] | None = None  # noqa: N815


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
# LLM-powered connection suggester
# ---------------------------------------------------------------------------

SUGGEST_CONNECTIONS_SYSTEM_PROMPT = """\
You are a writing coach helping a dyslexic thinker discover connections between their ideas.

You will receive a list of idea nodes (each with an id, title, body, and cluster number) \
and any existing connections between them. Your job is to:

1. Suggest new connections between nodes that share themes, arguments, or evidence.
2. Identify gaps — areas where the writer might need more ideas.
3. Suggest meaningful names for each cluster of ideas.

Rules:
- Only suggest connections that are genuinely meaningful.
- Each suggestion needs a clear, short description of WHY these ideas connect.
- Confidence should be 0.0–1.0 (how confident you are in the connection).
- Do NOT repeat connections that already exist.
- Cluster names should be short (2-4 words) and capture the theme.

Respond with ONLY valid JSON (no markdown fences):
{
  "suggestions": [
    {
      "type": "connection",
      "sourceNodeId": "node-id-1",
      "targetNodeId": "node-id-2",
      "description": "Both discuss X",
      "confidence": 0.85
    },
    {
      "type": "gap",
      "description": "You might need more evidence for Y",
      "confidence": 0.7
    }
  ],
  "clusterNames": {
    "1": "Theme Name",
    "2": "Another Theme"
  }
}\
"""


def _build_suggest_connections_prompt(request: SuggestConnectionsRequest) -> str:
    """Build the user message for connection suggestion."""
    lines = ["Here are the idea nodes:\n"]
    for node in request.nodes:
        lines.append(
            f"- [{node.id}] (cluster {node.cluster}) \"{node.title}\": {node.body}"
        )

    if request.edges:
        lines.append("\nExisting connections:")
        for edge in request.edges:
            rel = f" ({edge.relationship})" if edge.relationship else ""
            lines.append(f"- {edge.source} → {edge.target}{rel}")
    else:
        lines.append("\nNo existing connections yet.")

    lines.append("\nSuggest new connections and name the clusters.")
    return "\n".join(lines)


async def _llm_suggest_connections(
    request: SuggestConnectionsRequest,
) -> SuggestConnectionsResponse | None:
    """Call the LLM to suggest connections between mind map nodes."""
    if not settings.nvidia_nim_api_key:
        logger.warning("NVIDIA_NIM_API_KEY not set — falling back to simple suggestions")
        return None

    url = f"{settings.nvidia_nim_llm_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.nvidia_nim_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.nvidia_nim_llm_model,
        "messages": [
            {"role": "system", "content": SUGGEST_CONNECTIONS_SYSTEM_PROMPT},
            {"role": "user", "content": _build_suggest_connections_prompt(request)},
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
        logger.info(f"Suggest-connections LLM response: {content[:300]}")

        # Strip markdown fences if present
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()

        parsed = json.loads(cleaned)
        valid_ids = {n.id for n in request.nodes}
        existing = {(e.source, e.target) for e in request.edges}

        suggestions = []
        for s in parsed.get("suggestions", []):
            src = s.get("sourceNodeId")
            tgt = s.get("targetNodeId")
            stype = s.get("type", "connection")

            # Skip if connection already exists
            if stype == "connection" and (src, tgt) in existing:
                continue
            # Skip if referencing invalid node IDs
            if src and src not in valid_ids:
                continue
            if tgt and tgt not in valid_ids:
                continue

            suggestions.append(
                ConnectionSuggestion(
                    id=str(uuid.uuid4()),
                    type=stype,
                    sourceNodeId=src,
                    targetNodeId=tgt,
                    description=s.get("description", "Related ideas"),
                    confidence=s.get("confidence"),
                )
            )

        return SuggestConnectionsResponse(
            suggestions=suggestions,
            clusterNames=parsed.get("clusterNames"),
        )

    except httpx.HTTPError as e:
        logger.error(f"Suggest-connections LLM API error: {e}")
        return None
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse suggest-connections LLM response: {e}")
        return None


def _simple_suggest_connections(
    request: SuggestConnectionsRequest,
) -> SuggestConnectionsResponse:
    """Suggest connections based on shared clusters (no LLM fallback)."""
    existing = {(e.source, e.target) for e in request.edges}
    existing |= {(e.target, e.source) for e in request.edges}

    suggestions: list[ConnectionSuggestion] = []
    cluster_groups: dict[int, list[MindMapNode]] = {}
    for node in request.nodes:
        cluster_groups.setdefault(node.cluster, []).append(node)

    # Suggest connections between nodes in the same cluster
    for nodes in cluster_groups.values():
        for i, a in enumerate(nodes):
            for b in nodes[i + 1 :]:
                if (a.id, b.id) not in existing:
                    suggestions.append(
                        ConnectionSuggestion(
                            id=str(uuid.uuid4()),
                            type="connection",
                            sourceNodeId=a.id,
                            targetNodeId=b.id,
                            description=f"Both in the same idea cluster",
                            confidence=0.5,
                        )
                    )

    # Generate simple cluster names
    cluster_names: dict[str, str] = {}
    for cid, nodes in cluster_groups.items():
        if nodes:
            cluster_names[str(cid)] = nodes[0].title[:30] if nodes[0].title else f"Group {cid}"

    return SuggestConnectionsResponse(
        suggestions=suggestions[:10],  # Limit to 10 suggestions
        clusterNames=cluster_names,
    )


@router.post("/suggest-connections", response_model=SuggestConnectionsResponse)
async def suggest_connections(
    request: SuggestConnectionsRequest,
) -> SuggestConnectionsResponse:
    """Suggest connections between mind map nodes.

    Uses the LLM to find thematic connections, identify gaps, and name
    clusters. Falls back to simple cluster-based suggestions if the LLM
    is unavailable.
    """
    if not request.nodes:
        return SuggestConnectionsResponse(suggestions=[], clusterNames={})

    # Try LLM first
    result = await _llm_suggest_connections(request)
    if result is not None:
        return result

    # Fallback
    logger.info("Using simple suggest-connections fallback")
    return _simple_suggest_connections(request)


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
