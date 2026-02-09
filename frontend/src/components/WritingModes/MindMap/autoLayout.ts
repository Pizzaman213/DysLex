import { MindMapFlowNode, MindMapFlowEdge } from './types';

// --- Radial layout constants ---
const DEPTH_1_RADIUS = 250;
const DEPTH_INCREMENT = 180;
const CLUSTER_GAP = Math.PI / 36; // 5 degrees between cluster sectors
const MIN_SECTOR_ANGLE = Math.PI / 6; // 30 degrees minimum sector width
const SUB_NODE_FAN_ANGLE = Math.PI / 8; // 22.5 degrees child fan spread
const MIN_ARC_SEPARATION = 90; // min px between sibling nodes on same arc

const OVERLAP_PADDING = 20; // extra px between node edges
const OVERLAP_RESOLVE_PASSES = 30;

// Estimated char width at 13px font-weight 700
const CHAR_WIDTH = 8;
const NODE_PAD_X = 36; // 18px padding each side
const NODE_HEIGHT = 40;
const ROOT_HEIGHT = 50;
const SUB_CHAR_WIDTH = 7;
const SUB_PAD_X = 24;
const SUB_HEIGHT = 30;

// Common stop words excluded from similarity comparison
const STOP_WORDS = new Set([
  'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
  'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'and', 'or', 'but',
  'not', 'no', 'it', 'its', 'this', 'that', 'i', 'my', 'me', 'we', 'our',
  'you', 'your', 'he', 'she', 'they', 'them', 'do', 'does', 'did', 'has',
  'have', 'had', 'so', 'if', 'as', 'up', 'out', 'about', 'from',
]);

interface Vec2 {
  x: number;
  y: number;
}

/**
 * Extract meaningful words from a node's title + body.
 * Lowercased, stripped of punctuation, stop words removed.
 */
function extractWords(node: MindMapFlowNode): Set<string> {
  const text = ((node.data.title || '') + ' ' + (node.data.body || '')).toLowerCase();
  const tokens = text.replace(/[^a-z0-9\s]/g, '').split(/\s+/).filter(Boolean);
  const words = new Set<string>();
  for (const t of tokens) {
    if (!STOP_WORDS.has(t) && t.length > 1) words.add(t);
  }
  return words;
}

/**
 * Jaccard similarity between two word sets (0 = nothing in common, 1 = identical).
 */
function wordSimilarity(a: Set<string>, b: Set<string>): number {
  if (a.size === 0 && b.size === 0) return 0;
  let intersection = 0;
  for (const w of a) {
    if (b.has(w)) intersection++;
  }
  const union = a.size + b.size - intersection;
  return union === 0 ? 0 : intersection / union;
}

/**
 * Greedy nearest-neighbor chain: given items and a similarity matrix,
 * return them reordered so each item is next to its most-similar neighbor.
 * Deterministic — ties broken by original index.
 */
function similarityChain<T>(items: T[], sim: (a: T, b: T) => number): T[] {
  if (items.length <= 2) return items;

  const remaining = new Set(items.map((_, i) => i));
  const order: number[] = [0];
  remaining.delete(0);

  while (remaining.size > 0) {
    const last = order[order.length - 1];
    let bestIdx = -1;
    let bestSim = -1;

    for (const idx of remaining) {
      const s = sim(items[last], items[idx]);
      if (s > bestSim || (s === bestSim && idx < bestIdx)) {
        bestSim = s;
        bestIdx = idx;
      }
    }

    order.push(bestIdx);
    remaining.delete(bestIdx);
  }

  return order.map((i) => items[i]);
}

function estimateNodeSize(node: MindMapFlowNode, isRoot: boolean, isSub: boolean): { w: number; h: number } {
  const title = node.data.title || '';
  if (isRoot) {
    return { w: Math.max(title.length * 10 + 48, 120), h: ROOT_HEIGHT };
  }
  if (isSub) {
    return { w: Math.max(title.length * SUB_CHAR_WIDTH + SUB_PAD_X, 70), h: SUB_HEIGHT };
  }
  return { w: Math.max(title.length * CHAR_WIDTH + NODE_PAD_X, 80), h: NODE_HEIGHT };
}

function nodesOverlap(
  posA: Vec2, sizeA: { w: number; h: number },
  posB: Vec2, sizeB: { w: number; h: number },
  padding: number
): { overlapX: number; overlapY: number } {
  const halfWA = sizeA.w / 2 + padding / 2;
  const halfHA = sizeA.h / 2 + padding / 2;
  const halfWB = sizeB.w / 2 + padding / 2;
  const halfHB = sizeB.h / 2 + padding / 2;

  const dx = Math.abs(posA.x - posB.x);
  const dy = Math.abs(posA.y - posB.y);

  const overlapX = (halfWA + halfWB) - dx;
  const overlapY = (halfHA + halfHB) - dy;

  return {
    overlapX: overlapX > 0 ? overlapX : 0,
    overlapY: overlapY > 0 ? overlapY : 0,
  };
}

/**
 * Push an overlapping node outward along its radial direction from center.
 * Deterministic: always pushes the deeper node outward.
 */
function pushOutward(
  pos: Vec2,
  center: Vec2,
  amount: number
): void {
  const dx = pos.x - center.x;
  const dy = pos.y - center.y;
  const dist = Math.sqrt(dx * dx + dy * dy);
  if (dist < 1) {
    // Node is at center; push right
    pos.x += amount;
    return;
  }
  pos.x += (dx / dist) * amount;
  pos.y += (dy / dist) * amount;
}

/**
 * Deterministic overlap resolution using radial push.
 * The deeper node (higher depth) gets pushed outward from center.
 * If same depth, the node with the larger ID string is pushed.
 */
function resolveOverlapsRadial(
  nodes: MindMapFlowNode[],
  positions: Map<string, Vec2>,
  sizes: Map<string, { w: number; h: number }>,
  depths: Map<string, number>,
  center: Vec2
): void {
  for (let pass = 0; pass < OVERLAP_RESOLVE_PASSES; pass++) {
    let hadOverlap = false;

    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i];
        const b = nodes[j];
        const posA = positions.get(a.id)!;
        const posB = positions.get(b.id)!;
        const sizeA = sizes.get(a.id)!;
        const sizeB = sizes.get(b.id)!;

        const { overlapX, overlapY } = nodesOverlap(posA, sizeA, posB, sizeB, OVERLAP_PADDING);

        if (overlapX > 0 && overlapY > 0) {
          hadOverlap = true;
          const pushAmount = Math.max(overlapX, overlapY) / 2 + 2;

          const depthA = depths.get(a.id) ?? Infinity;
          const depthB = depths.get(b.id) ?? Infinity;

          if (a.id === 'root') {
            pushOutward(posB, center, pushAmount * 2);
          } else if (b.id === 'root') {
            pushOutward(posA, center, pushAmount * 2);
          } else if (depthA > depthB) {
            pushOutward(posA, center, pushAmount);
          } else if (depthB > depthA) {
            pushOutward(posB, center, pushAmount);
          } else {
            // Same depth: push both slightly apart along the perpendicular
            const dx = posB.x - posA.x;
            const dy = posB.y - posA.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 1) {
              posB.x += pushAmount;
            } else {
              // Push along the tangential direction (perpendicular to radial)
              const nx = dx / dist;
              const ny = dy / dist;
              posA.x -= nx * pushAmount;
              posA.y -= ny * pushAmount;
              posB.x += nx * pushAmount;
              posB.y += ny * pushAmount;
            }
          }
        }
      }
    }

    if (!hadOverlap) break;
  }
}

export function computeAutoLayout(
  nodes: MindMapFlowNode[],
  edges: MindMapFlowEdge[]
): Map<string, Vec2> {
  if (nodes.length <= 1) {
    return new Map(nodes.map((n) => [n.id, { x: n.position.x, y: n.position.y }]));
  }

  // Find root node
  const rootNode = nodes.find((n) => n.id === 'root') ?? nodes[0];
  const center: Vec2 = { x: rootNode.position.x, y: rootNode.position.y };

  // Build adjacency list (undirected)
  const adj = new Map<string, Set<string>>();
  for (const node of nodes) {
    adj.set(node.id, new Set());
  }
  for (const e of edges) {
    if (adj.has(e.source) && adj.has(e.target)) {
      adj.get(e.source)!.add(e.target);
      adj.get(e.target)!.add(e.source);
    }
  }

  // --- Phase 1: BFS from root ---
  const depths = new Map<string, number>();
  const parent = new Map<string, string | null>();
  const children = new Map<string, string[]>();
  const visited = new Set<string>();

  depths.set(rootNode.id, 0);
  parent.set(rootNode.id, null);
  children.set(rootNode.id, []);
  visited.add(rootNode.id);

  const queue: string[] = [rootNode.id];

  while (queue.length > 0) {
    const curr = queue.shift()!;
    const neighbors = Array.from(adj.get(curr) ?? []);

    // Sort neighbors deterministically by (cluster, title) for consistent ordering
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    neighbors.sort((a, b) => {
      const na = nodeMap.get(a)!;
      const nb = nodeMap.get(b)!;
      if (na.data.cluster !== nb.data.cluster) return na.data.cluster - nb.data.cluster;
      return (na.data.title || '').localeCompare(nb.data.title || '');
    });

    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        visited.add(neighbor);
        depths.set(neighbor, (depths.get(curr) ?? 0) + 1);
        parent.set(neighbor, curr);
        if (!children.has(curr)) children.set(curr, []);
        children.get(curr)!.push(neighbor);
        if (!children.has(neighbor)) children.set(neighbor, []);
        queue.push(neighbor);
      }
    }
  }

  // Collect disconnected nodes (not reached by BFS)
  const disconnected: MindMapFlowNode[] = [];
  for (const node of nodes) {
    if (!visited.has(node.id)) {
      disconnected.push(node);
    }
  }

  // Compute sizes
  const sizes = new Map<string, { w: number; h: number }>();
  for (const node of nodes) {
    const isRoot = node.id === rootNode.id;
    const depth = depths.get(node.id);
    const isSub = !isRoot && (depth === undefined || depth >= 2);
    sizes.set(node.id, estimateNodeSize(node, isRoot, isSub));
  }

  const positions = new Map<string, Vec2>();
  positions.set(rootNode.id, { ...center });

  // Get depth-1 nodes (direct children of root)
  const depth1Nodes = children.get(rootNode.id) ?? [];

  // Handle edge case: no edges, place all non-root nodes in a circle
  if (edges.length === 0 || depth1Nodes.length === 0) {
    const nonRootConnected = nodes.filter((n) => n.id !== rootNode.id);
    const count = nonRootConnected.length;
    if (count > 0) {
      const angleStep = (2 * Math.PI) / count;
      // Sort by cluster first, then reorder by similarity so related ideas group
      nonRootConnected.sort((a, b) => {
        if (a.data.cluster !== b.data.cluster) return a.data.cluster - b.data.cluster;
        return (a.data.title || '').localeCompare(b.data.title || '');
      });
      const ws = new Map(nonRootConnected.map((n) => [n, extractWords(n)]));
      const reordered = similarityChain(nonRootConnected, (a, b) =>
        wordSimilarity(ws.get(a) ?? new Set(), ws.get(b) ?? new Set())
      );
      nonRootConnected.length = 0;
      nonRootConnected.push(...reordered);
      for (let i = 0; i < count; i++) {
        const angle = -Math.PI / 2 + i * angleStep; // Start from top
        positions.set(nonRootConnected[i].id, {
          x: center.x + Math.cos(angle) * DEPTH_1_RADIUS,
          y: center.y + Math.sin(angle) * DEPTH_1_RADIUS,
        });
        depths.set(nonRootConnected[i].id, 1);
      }
    }

    resolveOverlapsRadial(nodes, positions, sizes, depths, center);
    return positions;
  }

  // --- Phase 2: Assign angular sectors to clusters ---
  // Group depth-1 nodes by cluster
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const clusterDepth1 = new Map<number, string[]>();

  for (const nodeId of depth1Nodes) {
    const node = nodeMap.get(nodeId);
    if (!node) continue;
    const cluster = node.data.cluster;
    if (!clusterDepth1.has(cluster)) clusterDepth1.set(cluster, []);
    clusterDepth1.get(cluster)!.push(nodeId);
  }

  // Precompute word sets for every node (used for similarity ordering)
  const wordSets = new Map<string, Set<string>>();
  for (const node of nodes) {
    wordSets.set(node.id, extractWords(node));
  }

  // Build a merged word set per cluster (union of all its node words)
  const clusterWords = new Map<number, Set<string>>();
  for (const [cluster, nodeIds] of clusterDepth1) {
    const merged = new Set<string>();
    for (const id of nodeIds) {
      for (const w of wordSets.get(id) ?? []) merged.add(w);
    }
    clusterWords.set(cluster, merged);
  }

  // Count total descendants (depth-1 + their subtrees) per cluster for proportional sizing
  const countDescendants = (nodeId: string): number => {
    const kids = children.get(nodeId) ?? [];
    let count = 1;
    for (const kid of kids) count += countDescendants(kid);
    return count;
  };

  const clusterWeights = new Map<number, number>();
  let totalWeight = 0;
  for (const [cluster, nodeIds] of clusterDepth1) {
    let weight = 0;
    for (const id of nodeIds) weight += countDescendants(id);
    clusterWeights.set(cluster, weight);
    totalWeight += weight;
  }

  // Order clusters so similar ones are adjacent (greedy nearest-neighbor chain)
  const initialClusters = Array.from(clusterDepth1.keys()).sort((a, b) => a - b);
  const sortedClusters = similarityChain(initialClusters, (a, b) =>
    wordSimilarity(clusterWords.get(a) ?? new Set(), clusterWords.get(b) ?? new Set())
  );

  const numClusters = sortedClusters.length;
  const totalGapAngle = numClusters * CLUSTER_GAP;
  const availableAngle = 2 * Math.PI - totalGapAngle;

  // Assign each cluster its angular sector
  const clusterSectors = new Map<number, { start: number; end: number }>();
  let currentAngle = -Math.PI / 2; // Start from top (12 o'clock)

  for (const cluster of sortedClusters) {
    const weight = clusterWeights.get(cluster) ?? 1;
    let sectorAngle = (weight / totalWeight) * availableAngle;
    sectorAngle = Math.max(sectorAngle, MIN_SECTOR_ANGLE);

    clusterSectors.set(cluster, {
      start: currentAngle,
      end: currentAngle + sectorAngle,
    });
    currentAngle += sectorAngle + CLUSTER_GAP;
  }

  // --- Phase 3: Position depth-1 nodes ---
  // Each depth-1 node is placed within its cluster's sector
  const nodeAngles = new Map<string, number>(); // Track assigned angle per node

  for (const cluster of sortedClusters) {
    const sector = clusterSectors.get(cluster)!;
    const nodeIds = clusterDepth1.get(cluster)!;

    // Sort within cluster so similar ideas are adjacent
    nodeIds.sort((a, b) => {
      const na = nodeMap.get(a)!;
      const nb = nodeMap.get(b)!;
      return (na.data.title || '').localeCompare(nb.data.title || '');
    });
    const reordered = similarityChain(nodeIds, (a, b) =>
      wordSimilarity(wordSets.get(a) ?? new Set(), wordSets.get(b) ?? new Set())
    );
    nodeIds.length = 0;
    nodeIds.push(...reordered);

    const count = nodeIds.length;
    const sectorWidth = sector.end - sector.start;

    // Auto-expand radius if nodes are too dense
    const arcLength = DEPTH_1_RADIUS * sectorWidth;
    const neededArc = count * MIN_ARC_SEPARATION;
    const radius = neededArc > arcLength
      ? neededArc / sectorWidth
      : DEPTH_1_RADIUS;

    for (let i = 0; i < count; i++) {
      // Distribute evenly within sector with margins
      const t = count === 1 ? 0.5 : i / (count - 1);
      const margin = sectorWidth * 0.05; // 5% margin on each side
      const angle = sector.start + margin + t * (sectorWidth - 2 * margin);

      nodeAngles.set(nodeIds[i], angle);
      positions.set(nodeIds[i], {
        x: center.x + Math.cos(angle) * radius,
        y: center.y + Math.sin(angle) * radius,
      });
    }
  }

  // --- Phase 4: Position depth-2+ nodes ---
  // Fan children around their parent's angle, each depth level pushed outward
  const positionChildren = (parentId: string, parentAngle: number, parentRadius: number, depth: number) => {
    const kids = children.get(parentId) ?? [];
    if (kids.length === 0) return;

    // Sort children deterministically
    kids.sort((a, b) => {
      const na = nodeMap.get(a)!;
      const nb = nodeMap.get(b)!;
      if (na.data.cluster !== nb.data.cluster) return na.data.cluster - nb.data.cluster;
      return (na.data.title || '').localeCompare(nb.data.title || '');
    });

    const childRadius = parentRadius + DEPTH_INCREMENT;
    const fanAngle = SUB_NODE_FAN_ANGLE * Math.max(1, kids.length - 1);

    for (let i = 0; i < kids.length; i++) {
      const t = kids.length === 1 ? 0 : (i / (kids.length - 1)) - 0.5;
      const angle = parentAngle + t * fanAngle;

      nodeAngles.set(kids[i], angle);
      positions.set(kids[i], {
        x: center.x + Math.cos(angle) * childRadius,
        y: center.y + Math.sin(angle) * childRadius,
      });

      // Recurse for deeper children
      positionChildren(kids[i], angle, childRadius, depth + 1);
    }
  };

  // Start recursion from each depth-1 node
  for (const nodeId of depth1Nodes) {
    const angle = nodeAngles.get(nodeId)!;
    positionChildren(nodeId, angle, DEPTH_1_RADIUS, 2);
  }

  // --- Phase 5: Disconnected nodes ---
  // Place disconnected nodes in a row below the main layout
  if (disconnected.length > 0) {
    // Find lowest y position in the current layout
    let maxY = center.y;
    for (const pos of positions.values()) {
      if (pos.y > maxY) maxY = pos.y;
    }

    const rowY = maxY + 120; // 120px below the lowest node
    const startX = center.x - ((disconnected.length - 1) * 120) / 2;

    // Sort disconnected nodes deterministically
    disconnected.sort((a, b) => {
      if (a.data.cluster !== b.data.cluster) return a.data.cluster - b.data.cluster;
      return (a.data.title || '').localeCompare(b.data.title || '');
    });

    for (let i = 0; i < disconnected.length; i++) {
      positions.set(disconnected[i].id, {
        x: startX + i * 120,
        y: rowY,
      });
      depths.set(disconnected[i].id, Infinity);
    }
  }

  // --- Phase 6: Deterministic overlap resolution ---
  resolveOverlapsRadial(nodes, positions, sizes, depths, center);

  return positions;
}

/**
 * Resolve overlaps for a set of nodes in-place.
 * Call after adding nodes to push them apart from existing ones.
 * Returns a map of node IDs to adjusted positions.
 */
export function resolveOverlaps(
  nodes: MindMapFlowNode[],
  edges: MindMapFlowEdge[]
): Map<string, Vec2> | null {
  if (nodes.length <= 1) return null;

  const rootChildren = new Set<string>();
  for (const e of edges) {
    if (e.source === 'root') rootChildren.add(e.target);
    if (e.target === 'root') rootChildren.add(e.source);
  }

  const sizes = new Map<string, { w: number; h: number }>();
  for (const node of nodes) {
    const isRoot = node.id === 'root';
    const isSub = !isRoot && !rootChildren.has(node.id);
    sizes.set(node.id, estimateNodeSize(node, isRoot, isSub));
  }

  const positions = new Map<string, Vec2>();
  for (const node of nodes) {
    positions.set(node.id, { x: node.position.x, y: node.position.y });
  }

  let anyMoved = false;

  for (let pass = 0; pass < OVERLAP_RESOLVE_PASSES; pass++) {
    let hadOverlap = false;

    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i];
        const b = nodes[j];
        const posA = positions.get(a.id)!;
        const posB = positions.get(b.id)!;
        const sizeA = sizes.get(a.id)!;
        const sizeB = sizes.get(b.id)!;

        const { overlapX, overlapY } = nodesOverlap(posA, sizeA, posB, sizeB, OVERLAP_PADDING);

        if (overlapX > 0 && overlapY > 0) {
          hadOverlap = true;
          anyMoved = true;

          if (overlapX < overlapY) {
            const pushX = overlapX / 2 + 1;
            if (a.id === 'root') {
              posB.x += posB.x >= posA.x ? overlapX + 1 : -(overlapX + 1);
            } else if (b.id === 'root') {
              posA.x += posA.x >= posB.x ? overlapX + 1 : -(overlapX + 1);
            } else {
              if (posA.x <= posB.x) {
                posA.x -= pushX;
                posB.x += pushX;
              } else {
                posA.x += pushX;
                posB.x -= pushX;
              }
            }
          } else {
            const pushY = overlapY / 2 + 1;
            if (a.id === 'root') {
              posB.y += posB.y >= posA.y ? overlapY + 1 : -(overlapY + 1);
            } else if (b.id === 'root') {
              posA.y += posA.y >= posB.y ? overlapY + 1 : -(overlapY + 1);
            } else {
              if (posA.y <= posB.y) {
                posA.y -= pushY;
                posB.y += pushY;
              } else {
                posA.y += pushY;
                posB.y -= pushY;
              }
            }
          }
        }
      }
    }

    if (!hadOverlap) break;
  }

  return anyMoved ? positions : null;
}
