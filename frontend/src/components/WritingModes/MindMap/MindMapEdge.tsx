import { memo, useState } from 'react';
import { BaseEdge, EdgeLabelRenderer, EdgeProps, getBezierPath } from '@xyflow/react';
import { EdgeRelationship, MindMapEdgeData } from './types';

const RELATIONSHIP_COLORS: Record<EdgeRelationship, string> = {
  supports: 'var(--green)',
  contradicts: 'var(--error, #c44)',
  leads_to: 'var(--blue)',
  example_of: 'var(--yellow)',
  related_to: 'var(--border2, rgba(45,42,36,.15))',
};

const RELATIONSHIP_LABELS: Record<EdgeRelationship, string> = {
  supports: 'supports',
  contradicts: 'contradicts',
  leads_to: 'leads to',
  example_of: 'example of',
  related_to: 'related to',
};

export const MindMapEdge = memo((props: EdgeProps) => {
  const [hovered, setHovered] = useState(false);

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    sourcePosition: props.sourcePosition,
    targetX: props.targetX,
    targetY: props.targetY,
    targetPosition: props.targetPosition,
  });

  const edgeData = props.data as MindMapEdgeData | undefined;
  const relationship = edgeData?.relationship as EdgeRelationship | null | undefined;
  const isFromRoot = props.source === 'root';
  const hasRelationship = relationship != null;

  // Determine stroke color
  let strokeColor: string;
  if (hasRelationship) {
    strokeColor = RELATIONSHIP_COLORS[relationship];
  } else if (isFromRoot) {
    strokeColor = 'var(--accent)';
  } else {
    strokeColor = 'var(--border2, rgba(45,42,36,.15))';
  }

  // Determine dash pattern
  const strokeDasharray = hasRelationship || isFromRoot ? 'none' : '6 4';

  // Determine opacity
  let baseOpacity: number;
  if (hasRelationship) {
    baseOpacity = 0.7;
  } else if (isFromRoot) {
    baseOpacity = 0.35;
  } else {
    baseOpacity = 0.6;
  }

  return (
    <>
      {/* Invisible wider path for easier hover/click targeting */}
      <path
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={20}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{ cursor: 'pointer' }}
      />
      <BaseEdge
        path={edgePath}
        markerEnd={props.markerEnd}
        style={{
          stroke: strokeColor,
          strokeWidth: isFromRoot ? 2.5 : 2,
          strokeDasharray,
          opacity: hovered ? 1 : baseOpacity,
          transition: 'opacity 0.2s',
          pointerEvents: 'none',
        }}
      />
      {hasRelationship && (
        <EdgeLabelRenderer>
          <div
            className={`edge-label${hovered ? ' edge-label-visible' : ''}`}
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'none',
              color: strokeColor,
            }}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
          >
            {RELATIONSHIP_LABELS[relationship]}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
});

MindMapEdge.displayName = 'MindMapEdge';
