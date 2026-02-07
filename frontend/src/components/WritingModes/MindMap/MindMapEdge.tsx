import { memo } from 'react';
import { BaseEdge, EdgeProps, getBezierPath } from '@xyflow/react';

export const MindMapEdge = memo((props: EdgeProps) => {
  const [edgePath] = getBezierPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    sourcePosition: props.sourcePosition,
    targetX: props.targetX,
    targetY: props.targetY,
    targetPosition: props.targetPosition,
  });

  const isFromRoot = props.source === 'root';

  return (
    <BaseEdge
      path={edgePath}
      markerEnd={props.markerEnd}
      style={{
        stroke: isFromRoot ? 'var(--accent)' : 'var(--border2, rgba(45,42,36,.15))',
        strokeWidth: isFromRoot ? 2.5 : 2,
        strokeDasharray: isFromRoot ? 'none' : '6 4',
        opacity: isFromRoot ? 0.35 : 0.6,
      }}
    />
  );
});

MindMapEdge.displayName = 'MindMapEdge';
