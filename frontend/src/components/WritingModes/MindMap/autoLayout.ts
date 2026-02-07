import { MindMapFlowNode, MindMapFlowEdge } from './types';

const REPULSION = 12000;
const ATTRACTION = 0.004;
const CLUSTER_PULL = 0.008;
const DAMPING = 0.85;
const ITERATIONS = 200;
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

interface Vec2 {
  x: number;
  y: number;
}

interface NodeRect {
  id: string;
  w: number;
  h: number;
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

export function computeAutoLayout(
  nodes: MindMapFlowNode[],
  edges: MindMapFlowEdge[]
): Map<string, Vec2> {
  if (nodes.length <= 1) {
    return new Map(nodes.map((n) => [n.id, { x: n.position.x, y: n.position.y }]));
  }

  // Precompute which nodes connect to root
  const rootChildren = new Set<string>();
  for (const e of edges) {
    if (e.source === 'root') rootChildren.add(e.target);
    if (e.target === 'root') rootChildren.add(e.source);
  }

  // Compute sizes
  const sizes = new Map<string, NodeRect>();
  for (const node of nodes) {
    const isRoot = node.id === 'root';
    const isSub = !isRoot && !rootChildren.has(node.id);
    const size = estimateNodeSize(node, isRoot, isSub);
    sizes.set(node.id, { id: node.id, ...size });
  }

  // Initialize positions with small random jitter to break symmetry
  const positions = new Map<string, Vec2>();
  const velocities = new Map<string, Vec2>();

  for (const node of nodes) {
    positions.set(node.id, {
      x: node.position.x + (Math.random() - 0.5) * 4,
      y: node.position.y + (Math.random() - 0.5) * 4,
    });
    velocities.set(node.id, { x: 0, y: 0 });
  }

  const edgeList = edges.map((e) => ({ source: e.source, target: e.target }));

  const computeClusterCentroids = () => {
    const clusterSums = new Map<number, { x: number; y: number; count: number }>();
    for (const node of nodes) {
      if (node.id === 'root') continue;
      const cluster = node.data.cluster;
      const pos = positions.get(node.id)!;
      const existing = clusterSums.get(cluster);
      if (existing) {
        existing.x += pos.x;
        existing.y += pos.y;
        existing.count++;
      } else {
        clusterSums.set(cluster, { x: pos.x, y: pos.y, count: 1 });
      }
    }
    const centroids = new Map<number, Vec2>();
    for (const [cluster, sum] of clusterSums) {
      centroids.set(cluster, { x: sum.x / sum.count, y: sum.y / sum.count });
    }
    return centroids;
  };

  const rootPos = positions.get('root');
  const pinCenter = rootPos ? { x: rootPos.x, y: rootPos.y } : { x: 400, y: 200 };

  // --- Force simulation ---
  for (let iter = 0; iter < ITERATIONS; iter++) {
    const cooling = 1 - iter / ITERATIONS;
    const clusterCentroids = computeClusterCentroids();

    for (const node of nodes) {
      velocities.set(node.id, { x: 0, y: 0 });
    }

    // Rectangle-aware repulsion (all pairs)
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i];
        const b = nodes[j];
        const posA = positions.get(a.id)!;
        const posB = positions.get(b.id)!;
        const sizeA = sizes.get(a.id)!;
        const sizeB = sizes.get(b.id)!;

        let dx = posA.x - posB.x;
        let dy = posA.y - posB.y;
        let dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 1) {
          dx = (Math.random() - 0.5) * 4;
          dy = (Math.random() - 0.5) * 4;
          dist = Math.sqrt(dx * dx + dy * dy);
        }

        // Effective minimum distance based on node sizes
        const minDistX = (sizeA.w + sizeB.w) / 2 + OVERLAP_PADDING;
        const minDistY = (sizeA.h + sizeB.h) / 2 + OVERLAP_PADDING;
        const effectiveMinDist = Math.sqrt(minDistX * minDistX + minDistY * minDistY) * 0.5;

        // Stronger repulsion when nodes are close relative to their sizes
        const clampedDist = Math.max(dist, effectiveMinDist * 0.3);
        let force = REPULSION / (clampedDist * clampedDist);

        // Boost force when actually overlapping
        const { overlapX, overlapY } = nodesOverlap(posA, sizeA, posB, sizeB, OVERLAP_PADDING);
        if (overlapX > 0 && overlapY > 0) {
          force += (overlapX + overlapY) * 2;
        }

        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        const velA = velocities.get(a.id)!;
        const velB = velocities.get(b.id)!;
        velA.x += fx;
        velA.y += fy;
        velB.x -= fx;
        velB.y -= fy;
      }
    }

    // Edge attraction
    for (const edge of edgeList) {
      const posA = positions.get(edge.source);
      const posB = positions.get(edge.target);
      if (!posA || !posB) continue;

      const dx = posB.x - posA.x;
      const dy = posB.y - posA.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 1) continue;

      const force = ATTRACTION * dist;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;

      const velA = velocities.get(edge.source)!;
      const velB = velocities.get(edge.target)!;
      velA.x += fx;
      velA.y += fy;
      velB.x -= fx;
      velB.y -= fy;
    }

    // Cluster cohesion
    for (const node of nodes) {
      if (node.id === 'root') continue;
      const centroid = clusterCentroids.get(node.data.cluster);
      if (!centroid) continue;

      const pos = positions.get(node.id)!;
      const dx = centroid.x - pos.x;
      const dy = centroid.y - pos.y;

      const vel = velocities.get(node.id)!;
      vel.x += dx * CLUSTER_PULL;
      vel.y += dy * CLUSTER_PULL;
    }

    // Apply velocities
    for (const node of nodes) {
      if (node.id === 'root') continue;

      const pos = positions.get(node.id)!;
      const vel = velocities.get(node.id)!;

      pos.x += vel.x * DAMPING * cooling;
      pos.y += vel.y * DAMPING * cooling;
    }

    positions.set('root', { ...pinCenter });
  }

  // --- Final overlap resolution pass ---
  // Iteratively push apart any remaining overlapping node pairs
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

          // Push apart along the axis of least overlap
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
