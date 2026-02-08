import { useCallback, useEffect, useRef, useState } from 'react';
import { useCaptureStore } from '../../stores/captureStore';
import { useMindMapStore } from '../../stores/mindMapStore';
import { api } from '../../services/api';
import { MindMapCanvas } from './MindMap/MindMapCanvas';
import { AISuggestionsPanel } from './MindMap/AISuggestionsPanel';
import { StatusBar } from '../Shared/StatusBar';
import { VoiceBar } from '../Shared/VoiceBar';
import { useCaptureVoice } from '../../hooks/useCaptureVoice';
import { Scaffold } from './MindMap/types';
import './MindMap/mindmap.css';

const QUICK_ADD_MAX_WORDS = 25;
const QUICK_ADD_MAX_SENTENCES = 1;
const DEFAULT_ROOT_TITLE = 'Main Idea';

function isQuickAddTranscript(text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed) return false;

  const wordCount = trimmed.split(/\s+/).length;
  if (wordCount > QUICK_ADD_MAX_WORDS) return false;

  // Count sentences by splitting on sentence-ending punctuation
  const sentences = trimmed.split(/[.!?]+/).filter((s) => s.trim().length > 0);
  if (sentences.length > QUICK_ADD_MAX_SENTENCES) return false;

  return true;
}

/** Returns true if the root node still has the default placeholder title */
function rootIsDefault(): boolean {
  const root = useMindMapStore.getState().nodes.find((n) => n.id === 'root');
  return !root || root.data.title === DEFAULT_ROOT_TITLE;
}

/** Set the root node title if it's still the default placeholder */
function setRootTitleIfDefault(title: string) {
  if (!title.trim()) return;
  if (!rootIsDefault()) return;
  useMindMapStore.getState().updateNodeData('root', { title: title.trim() });
}

/** Derive a short central theme from a set of card titles (fallback when API doesn't provide one) */
function deriveTopicFromCards(titles: string[]): string {
  if (titles.length === 0) return '';
  if (titles.length === 1) return titles[0];
  // Use the shortest title as a rough proxy for the most general one
  const sorted = [...titles].sort((a, b) => a.length - b.length);
  return sorted[0];
}

interface MindMapModeProps {
  onNavigateToDraft: (scaffold: Scaffold) => void;
}

export function MindMapMode({ onNavigateToDraft }: MindMapModeProps) {
  const [isScaffoldLoading, setIsScaffoldLoading] = useState(false);
  const { isRecording, analyserNode, isTranscribing, micDenied, start: startVoice, stop: stopVoice } = useCaptureVoice();

  const captureCards = useCaptureStore((s) => s.cards);
  const resetCapture = useCaptureStore((s) => s.reset);

  const {
    nodes,
    edges,
    setScaffold,
    setSuggestions,
    setIsSuggestionsLoading,
    setClusterName,
    quickAddNode,
  } = useMindMapStore();

  // Ref for getting viewport center from canvas
  const viewportCenterRef = useRef<() => { x: number; y: number }>(() => ({ x: 400, y: 200 }));

  // Guard against re-importing the same capture cards
  const importedRef = useRef(false);

  // Import cards from Capture Mode on mount
  useEffect(() => {
    if (captureCards.length > 0 && !importedRef.current) {
      importedRef.current = true;
      const { nodes: currentNodes, addNode, batchUpdate } = useMindMapStore.getState();
      const rootNode = currentNodes.find((n) => n.id === 'root');
      const rootX = rootNode?.position.x || 400;
      const rootY = rootNode?.position.y || 200;

      const angleStep = (2 * Math.PI) / captureCards.length;
      const radius = Math.max(300, captureCards.length * 80);

      batchUpdate(() => {
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
      });

      // Set root title from capture card titles
      const topic = deriveTopicFromCards(captureCards.map((c) => c.title));
      setRootTitleIfDefault(topic);

      resetCapture();
    }
  }, [captureCards, resetCapture]);

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
        relationship: edge.data?.relationship ?? null,
      }));

      const response = await api.suggestConnections(apiNodes, apiEdges);
      setSuggestions(response.suggestions);

      // Apply AI-generated cluster names
      if (response.clusterNames) {
        for (const [key, name] of Object.entries(response.clusterNames)) {
          const cluster = parseInt(key) as 1 | 2 | 3 | 4 | 5;
          if (cluster >= 1 && cluster <= 5 && name) {
            setClusterName(cluster, name);
          }
        }
      }
    } catch (error) {
      console.error('Failed to get suggestions:', error);
      setSuggestions([]);
    } finally {
      setIsSuggestionsLoading(false);
    }
  }, [nodes, edges, setSuggestions, setIsSuggestionsLoading, setClusterName]);

  const processExtractedCards = useCallback((response: {
    cards: Array<{ id: string; title: string; body: string; sub_ideas?: Array<{ id: string; title: string; body: string }> }>;
    topic?: string;
    clusterNames?: Record<string, string>;
  }) => {
    const cards = response.cards;
    if (cards.length === 0) return;

    // Apply AI-generated cluster names
    if (response.clusterNames) {
      for (const [key, name] of Object.entries(response.clusterNames)) {
        const cluster = parseInt(key) as 1 | 2 | 3 | 4 | 5;
        if (cluster >= 1 && cluster <= 5 && name) {
          setClusterName(cluster, name);
        }
      }
    }

    // Update root title from API-provided topic
    if (response.topic) {
      setRootTitleIfDefault(response.topic);
    } else {
      setRootTitleIfDefault(deriveTopicFromCards(cards.map((c) => c.title)));
    }

    // Get existing node titles to avoid duplicates
    const { nodes: currentNodes, addNode, batchUpdate } = useMindMapStore.getState();
    const existingTitles = new Set(
      currentNodes.map((n) => n.data.title.trim().toLowerCase())
    );

    const newCards = cards.filter(
      (card) => !existingTitles.has(card.title.trim().toLowerCase())
    );
    if (newCards.length === 0) return;

    // Position topic nodes in a circle around the root
    const rootNode = currentNodes.find((n) => n.id === 'root');
    const rootX = rootNode?.position.x || 400;
    const rootY = rootNode?.position.y || 200;

    const existingCount = currentNodes.length - 1;
    const angleOffset = existingCount * 0.5;

    const topicAngleStep = (2 * Math.PI) / newCards.length;
    const topicRadius = Math.max(350, newCards.length * 90);

    batchUpdate(() => {
      newCards.forEach((card, topicIndex) => {
        const cluster = (((existingCount + topicIndex) % 5) + 1) as 1 | 2 | 3 | 4 | 5;
        const topicAngle = topicIndex * topicAngleStep - Math.PI / 2 + angleOffset;
        const topicX = rootX + Math.cos(topicAngle) * topicRadius;
        const topicY = rootY + Math.sin(topicAngle) * topicRadius;

        addNode('root', { x: topicX, y: topicY }, {
          title: card.title,
          body: card.body || '',
          cluster,
        });

        const latestNodes = useMindMapStore.getState().nodes;
        const topicNode = latestNodes[latestNodes.length - 1];

        const topicBody = (card.body || '').trim().toLowerCase();
        const subs = (card.sub_ideas || []).filter((s) => {
          const subBody = s.body.trim().toLowerCase();
          return subBody !== topicBody && !topicBody.startsWith(subBody) && !subBody.startsWith(topicBody);
        });
        if (subs.length > 0) {
          const subAngleStep = (Math.PI * 0.8) / Math.max(subs.length - 1, 1);
          const subRadius = 220;
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
    });
  }, [setClusterName]);

  const handleExtractFromText = useCallback(async (text: string) => {
    try {
      const response = await api.extractIdeas(text);
      processExtractedCards(response);
    } catch (error) {
      console.error('Failed to extract ideas:', error);
    }
  }, [processExtractedCards]);

  const handleExtractFromImage = useCallback(async (base64: string, mimeType: string) => {
    try {
      const response = await api.extractIdeasFromImage(base64, mimeType);
      processExtractedCards(response);
    } catch (error) {
      console.error('Failed to extract ideas from image:', error);
    }
  }, [processExtractedCards]);

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
        relationship: edge.data?.relationship ?? null,
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

  const handleVoiceStop = useCallback(async () => {
    const text = await stopVoice();
    if (!text) return;

    if (isQuickAddTranscript(text)) {
      // If this is the first idea and root is still default, use it as the root title
      const state = useMindMapStore.getState();
      const isFirstIdea = state.nodes.length === 1; // only root
      if (isFirstIdea && rootIsDefault()) {
        // First voice input becomes the central theme
        const capitalized = text.charAt(0).toUpperCase() + text.slice(1);
        const title = capitalized.length > 40 ? capitalized.substring(0, 37) + '...' : capitalized;
        state.updateNodeData('root', { title });
      } else {
        const center = viewportCenterRef.current();
        quickAddNode(text, center);
      }
    } else {
      handleExtractFromText(text);
    }
  }, [stopVoice, quickAddNode, handleExtractFromText]);

  return (
    <div className="mindmap-mode">
      <div className="mindmap-canvas-container">
        <MindMapCanvas
          onBuildScaffold={handleBuildScaffold}
          isScaffoldLoading={isScaffoldLoading}
          onExtractFromText={handleExtractFromText}
          onExtractFromImage={handleExtractFromImage}
          viewportCenterRef={viewportCenterRef}
        />
        <VoiceBar
          isRecording={isRecording}
          isTranscribing={isTranscribing}
          analyserNode={analyserNode}
          onStartRecording={startVoice}
          onStopRecording={handleVoiceStop}
          micDenied={micDenied}
          compact
        />
        <StatusBar />
      </div>
      <AISuggestionsPanel onSuggest={handleSuggest} onBuildScaffold={handleBuildScaffold} isScaffoldLoading={isScaffoldLoading} />
    </div>
  );
}
