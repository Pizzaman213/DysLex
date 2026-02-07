import { useCallback, useEffect, useState } from 'react';
import { useCaptureStore } from '../../stores/captureStore';
import { useMindMapStore } from '../../stores/mindMapStore';
import { api } from '../../services/api';
import { MindMapCanvas } from './MindMap/MindMapCanvas';
import { AISuggestionsPanel } from './MindMap/AISuggestionsPanel';
import { StatusBar } from '../Shared/StatusBar';
import { Scaffold } from './MindMap/types';
import './MindMap/mindmap.css';

interface MindMapModeProps {
  onNavigateToDraft: (scaffold: Scaffold) => void;
}

export function MindMapMode({ onNavigateToDraft }: MindMapModeProps) {
  const [isScaffoldLoading, setIsScaffoldLoading] = useState(false);

  const captureCards = useCaptureStore((s) => s.cards);
  const resetCapture = useCaptureStore((s) => s.reset);

  const {
    nodes,
    edges,
    addNode,
    setScaffold,
    setSuggestions,
    setIsSuggestionsLoading,
  } = useMindMapStore();

  // Import cards from Capture Mode on mount
  useEffect(() => {
    if (captureCards.length > 0) {
      const rootNode = nodes.find((n) => n.id === 'root');
      const rootX = rootNode?.position.x || 400;
      const rootY = rootNode?.position.y || 200;

      const angleStep = (2 * Math.PI) / captureCards.length;
      const radius = 250;

      captureCards.forEach((card, index) => {
        const angle = index * angleStep;
        const x = rootX + Math.cos(angle) * radius;
        const y = rootY + Math.sin(angle) * radius;

        addNode('root', { x, y }, {
          title: card.title,
          body: card.body || '',
          cluster: ((index % 5) + 1) as 1 | 2 | 3 | 4 | 5,
        });
      });

      resetCapture();
    }
  }, [captureCards, resetCapture, nodes, addNode]);

  const handleSuggest = useCallback(async () => {
    setIsSuggestionsLoading(true);

    try {
      const apiNodes = nodes.map((node) => ({
        id: node.id,
        title: node.data.title,
        body: node.data.body,
        cluster: node.data.cluster,
        x: node.position.x,
        y: node.position.y,
      }));

      const apiEdges = edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
      }));

      const response = await api.suggestConnections(apiNodes, apiEdges);
      setSuggestions(response.suggestions);
    } catch (error) {
      console.error('Failed to get suggestions:', error);
      setSuggestions([]);
    } finally {
      setIsSuggestionsLoading(false);
    }
  }, [nodes, edges, setSuggestions, setIsSuggestionsLoading]);

  const handleExtractFromText = useCallback(async (text: string) => {
    try {
      const response = await api.extractIdeas(text);
      const cards = response.cards;
      if (cards.length === 0) return;

      // Position topic nodes in a circle around the root
      const rootNode = nodes.find((n) => n.id === 'root');
      const rootX = rootNode?.position.x || 400;
      const rootY = rootNode?.position.y || 200;

      const topicAngleStep = (2 * Math.PI) / cards.length;
      const topicRadius = 280;

      cards.forEach((card, topicIndex) => {
        const cluster = ((topicIndex % 5) + 1) as 1 | 2 | 3 | 4 | 5;
        const topicAngle = topicIndex * topicAngleStep - Math.PI / 2;
        const topicX = rootX + Math.cos(topicAngle) * topicRadius;
        const topicY = rootY + Math.sin(topicAngle) * topicRadius;

        // Create the topic node connected to root
        addNode('root', { x: topicX, y: topicY }, {
          title: card.title,
          body: card.body || '',
          cluster,
        });

        // Get the ID of the node we just created
        const currentNodes = useMindMapStore.getState().nodes;
        const topicNode = currentNodes[currentNodes.length - 1];

        // Create sub-nodes connected to the topic node
        const subs = card.sub_ideas || [];
        if (subs.length > 0) {
          const subAngleStep = (Math.PI * 0.8) / Math.max(subs.length - 1, 1);
          const subRadius = 160;
          const subStartAngle = topicAngle - (Math.PI * 0.4);

          subs.forEach((sub, subIndex) => {
            const subAngle = subs.length === 1
              ? topicAngle
              : subStartAngle + subIndex * subAngleStep;
            const subX = topicX + Math.cos(subAngle) * subRadius;
            const subY = topicY + Math.sin(subAngle) * subRadius;

            addNode(topicNode.id, { x: subX, y: subY }, {
              title: sub.title,
              body: sub.body || '',
              cluster,
            });
          });
        }
      });
    } catch (error) {
      console.error('Failed to extract ideas:', error);
    }
  }, [nodes, addNode]);

  const handleBuildScaffold = useCallback(async () => {
    setIsScaffoldLoading(true);

    try {
      const apiNodes = nodes.map((node) => ({
        id: node.id,
        title: node.data.title,
        body: node.data.body,
        cluster: node.data.cluster,
        x: node.position.x,
        y: node.position.y,
      }));

      const apiEdges = edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
      }));

      const response = await api.buildScaffold(apiNodes, apiEdges);
      setScaffold(response);
      onNavigateToDraft(response);
    } catch (error) {
      console.error('Failed to build scaffold:', error);
      alert('Failed to build scaffold. Please try again.');
    } finally {
      setIsScaffoldLoading(false);
    }
  }, [nodes, edges, setScaffold, onNavigateToDraft]);

  return (
    <div className="mindmap-mode">
      <div className="mindmap-canvas-container">
        <MindMapCanvas onBuildScaffold={handleBuildScaffold} isScaffoldLoading={isScaffoldLoading} onExtractFromText={handleExtractFromText} />
        <StatusBar />
      </div>
      <AISuggestionsPanel onSuggest={handleSuggest} onBuildScaffold={handleBuildScaffold} isScaffoldLoading={isScaffoldLoading} />
    </div>
  );
}
