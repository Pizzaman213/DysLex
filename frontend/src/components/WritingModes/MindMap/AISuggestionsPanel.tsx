import { useCallback, useMemo } from 'react';
import { useMindMapStore } from '../../../stores/mindMapStore';
import { AISuggestion } from './types';

interface SuggestionCardProps {
  suggestion: AISuggestion;
  onAccept: () => void;
  onDismiss: () => void;
}

function SuggestionCard({ suggestion, onAccept, onDismiss }: SuggestionCardProps) {
  const nodes = useMindMapStore((state) => state.nodes);

  const getNodeTitle = (nodeId?: string) => {
    if (!nodeId) return '';
    const node = nodes.find((n) => n.id === nodeId);
    return node?.data.title || '';
  };

  const renderDescription = () => {
    if (suggestion.type === 'connection' && suggestion.sourceNodeId && suggestion.targetNodeId) {
      return (
        <>
          <strong>Connect:</strong> "{getNodeTitle(suggestion.sourceNodeId)}" with "
          {getNodeTitle(suggestion.targetNodeId)}"
          <div className="mm-suggestion-reason">{suggestion.description}</div>
        </>
      );
    }

    return <div>{suggestion.description}</div>;
  };

  const getSuggestionIcon = () => {
    switch (suggestion.type) {
      case 'connection':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
          </svg>
        );
      case 'gap':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <line x1="12" y1="2" x2="12" y2="6" />
            <line x1="12" y1="18" x2="12" y2="22" />
            <line x1="4.93" y1="4.93" x2="7.76" y2="7.76" />
            <line x1="16.24" y1="16.24" x2="19.07" y2="19.07" />
            <line x1="2" y1="12" x2="6" y2="12" />
            <line x1="18" y1="12" x2="22" y2="12" />
            <line x1="4.93" y1="19.07" x2="7.76" y2="16.24" />
            <line x1="16.24" y1="7.76" x2="19.07" y2="4.93" />
          </svg>
        );
      case 'cluster':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <circle cx="12" cy="12" r="3" />
            <circle cx="19" cy="5" r="2" />
            <circle cx="5" cy="5" r="2" />
            <circle cx="19" cy="19" r="2" />
            <circle cx="5" cy="19" r="2" />
          </svg>
        );
      default:
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
          </svg>
        );
    }
  };

  const getTypeLabel = () => {
    switch (suggestion.type) {
      case 'connection': return 'Connection';
      case 'gap': return 'Missing Idea';
      case 'cluster': return 'Grouping';
      default: return 'Suggestion';
    }
  };

  return (
    <div className="mm-suggestion" role="article">
      <div className="mm-suggestion-head">
        <span className="mm-suggestion-icon">{getSuggestionIcon()}</span>
        <span className="mm-suggestion-label">{getTypeLabel()}</span>
      </div>
      <div className="mm-suggestion-desc">{renderDescription()}</div>
      <div className="mm-suggestion-actions">
        <button
          type="button"
          onClick={onAccept}
          className="btn-accept"
          aria-label="Accept suggestion"
        >
          Accept
        </button>
        <button
          type="button"
          onClick={onDismiss}
          className="btn-dismiss"
          aria-label="Dismiss suggestion"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}

const CLUSTER_COLORS = ['var(--accent)', 'var(--green)', 'var(--blue)', 'var(--yellow)', 'var(--purple)'];
const CLUSTER_NAMES = ['Cluster 1', 'Cluster 2', 'Cluster 3', 'Cluster 4', 'Cluster 5'];

interface AISuggestionsPanelProps {
  onSuggest: () => void;
  onBuildScaffold?: () => void;
  isScaffoldLoading?: boolean;
}

export function AISuggestionsPanel({ onSuggest, onBuildScaffold, isScaffoldLoading }: AISuggestionsPanelProps) {
  const { suggestions, isSuggestionsLoading, acceptSuggestion, dismissSuggestion, nodes } =
    useMindMapStore();

  const handleAccept = useCallback(
    (id: string) => {
      acceptSuggestion(id);
    },
    [acceptSuggestion]
  );

  const handleDismiss = useCallback(
    (id: string) => {
      dismissSuggestion(id);
    },
    [dismissSuggestion]
  );

  // Build cluster summary from nodes
  const clusters = useMemo(() => {
    const clusterMap = new Map<number, { count: number; title: string }>();
    nodes.forEach((node) => {
      if (node.id === 'root') return;
      const c = node.data.cluster;
      const existing = clusterMap.get(c);
      if (existing) {
        existing.count++;
      } else {
        clusterMap.set(c, { count: 1, title: node.data.title });
      }
    });
    return Array.from(clusterMap.entries())
      .sort(([a], [b]) => a - b)
      .map(([cluster, info]) => ({
        cluster,
        color: CLUSTER_COLORS[cluster - 1] || CLUSTER_COLORS[0],
        name: info.count === 1 ? info.title : CLUSTER_NAMES[cluster - 1],
        count: info.count,
      }));
  }, [nodes]);

  const nonRootCount = nodes.filter((n) => n.id !== 'root').length;

  return (
    <aside
      className="ai-suggestions-panel"
      role="region"
      aria-label="AI suggestions"
      aria-live="polite"
    >
      <div className="suggestions-header">
        <h2 className="mm-panel-title">AI Suggestions</h2>
        <button
          type="button"
          onClick={onSuggest}
          className="btn-suggest"
          disabled={isSuggestionsLoading}
          aria-label="Get AI suggestions"
        >
          {isSuggestionsLoading ? 'Thinking...' : 'Suggest'}
        </button>
      </div>

      <div className="suggestions-content">
        {isSuggestionsLoading && (
          <div className="suggestions-loading" aria-busy="true">
            <div className="loading-spinner" aria-hidden="true" />
            <p>Analyzing your ideas...</p>
          </div>
        )}

        {!isSuggestionsLoading && suggestions.length === 0 && (
          <div className="suggestions-empty">
            <p>Add some ideas, then tap <strong>Suggest</strong> to get AI-powered connections and insights.</p>
          </div>
        )}

        {!isSuggestionsLoading && suggestions.length > 0 && (
          <div className="suggestions-list">
            {suggestions.map((suggestion) => (
              <SuggestionCard
                key={suggestion.id}
                suggestion={suggestion}
                onAccept={() => handleAccept(suggestion.id)}
                onDismiss={() => handleDismiss(suggestion.id)}
              />
            ))}
          </div>
        )}

        {/* Cluster list */}
        {clusters.length > 0 && (
          <div className="cluster-list">
            <div className="cluster-list-title">
              Clusters ({clusters.length})
            </div>
            {clusters.map(({ cluster, color, name, count }) => (
              <div key={cluster} className="cluster-item">
                <div className="cluster-item-dot" style={{ background: color }} />
                <span>{name}</span>
                <span className="cluster-item-count">
                  {count} {count === 1 ? 'idea' : 'ideas'}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Build scaffold button */}
        {onBuildScaffold && (
          <button
            type="button"
            className="panel-action-btn"
            onClick={onBuildScaffold}
            disabled={nonRootCount < 2 || isScaffoldLoading}
          >
            {isScaffoldLoading ? 'Building...' : 'Build scaffold from map →'}
          </button>
        )}
      </div>
    </aside>
  );
}
