import { Node, Edge } from '@xyflow/react';

export interface MindMapNodeData extends Record<string, unknown> {
  title: string;
  body: string;
  cluster: 1 | 2 | 3 | 4 | 5;
}

export type MindMapFlowNode = Node<MindMapNodeData>;

export type EdgeRelationship =
  | 'supports'
  | 'contradicts'
  | 'leads_to'
  | 'example_of'
  | 'related_to';

export interface MindMapEdgeData extends Record<string, unknown> {
  relationship?: EdgeRelationship | null;
}

export type MindMapFlowEdge = Edge<MindMapEdgeData>;

export type AISuggestionType = 'connection' | 'gap' | 'cluster';

export interface AISuggestion {
  id: string;
  type: AISuggestionType;
  sourceNodeId?: string;
  targetNodeId?: string;
  description: string;
  confidence?: number;
  suggestedRelationship?: EdgeRelationship;
}

export interface ScaffoldSection {
  heading: string;
  hint: string;
  nodeIds: string[];
  suggestedContent?: string;
}

export interface Scaffold {
  title: string;
  sections: ScaffoldSection[];
}
