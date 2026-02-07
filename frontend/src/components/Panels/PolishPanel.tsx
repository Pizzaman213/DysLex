import { useState } from 'react';
import { Editor } from '@tiptap/react';
import { Node as PMNode } from '@tiptap/pm/model';
import { usePolishStore, TrackedChange } from '../../stores/polishStore';
import { useSessionStore } from '../../stores/sessionStore';
import { SuggestionCard } from './SuggestionCard';
import { ReadabilityScore } from './ReadabilityScore';
import { SessionSummary } from './SessionSummary';
import { analyzeText } from '../../utils/readabilityUtils';
import { api } from '../../services/api';
import { ApiError } from '../../services/apiErrors';

interface PolishPanelProps {
  editor: Editor | null;
}

/**
 * Search for `text` inside a ProseMirror document and return the PM positions.
 * `searchFrom` advances the cursor so duplicate words get distinct matches.
 */
function findInDocument(
  doc: PMNode,
  text: string,
  searchFrom: number = 0,
): { from: number; to: number } | null {
  if (!text) return null;
  let found: { from: number; to: number } | null = null;

  doc.descendants((node, pos) => {
    if (found) return false;
    if (!node.isText || !node.text) return;
    // Skip nodes entirely before our search cursor
    if (pos + node.text.length <= searchFrom) return;

    const startInNode = Math.max(0, searchFrom - pos);
    const idx = node.text.indexOf(text, startInNode);
    if (idx !== -1) {
      found = { from: pos + idx, to: pos + idx + text.length };
      return false;
    }
  });

  return found;
}

export function PolishPanel({ editor }: PolishPanelProps) {
  const {
    suggestions,
    isAnalyzing,
    activeSuggestion,
    setSuggestions,
    applySuggestion,
    dismissSuggestion,
    setActiveSuggestion,
    setIsAnalyzing
  } = usePolishStore();

  const { recordCorrectionApplied, recordCorrectionDismissed } = useSessionStore();

  const [activeTab, setActiveTab] = useState<'suggestions' | 'readability' | 'summary'>('suggestions');
  const [readabilityMetrics, setReadabilityMetrics] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const activeSuggestions = suggestions.filter(
    s => !s.isApplied && !s.isDismissed
  );

  const handleDeepAnalysis = async () => {
    if (!editor) {
      setError('Editor is still loading. Please try again in a moment.');
      return;
    }
    if (isAnalyzing) return;

    try {
      setError(null);
      setIsAnalyzing(true);

      const text = editor.getText();

      if (!text.trim()) {
        setError('Please write some text before running analysis');
        setIsAnalyzing(false);
        return;
      }

      const results = await api.deepAnalysis(text);

      // Recompute positions using ProseMirror document so decorations
      // and apply/dismiss target the correct ranges.
      const doc = editor.state.doc;
      let searchFrom = 0;
      const positioned: TrackedChange[] = [];

      for (const result of results) {
        const found = findInDocument(doc, result.original ?? '', searchFrom);
        if (found) {
          positioned.push({ ...result, start: found.from, end: found.to });
          searchFrom = found.to;
        } else {
          // Retry from start (LLM may return out of document order)
          const retry = findInDocument(doc, result.original ?? '', 0);
          if (retry) {
            positioned.push({ ...result, start: retry.from, end: retry.to });
          }
        }
      }

      setSuggestions(positioned);

      if ((editor.commands as any).setTrackedChanges) {
        (editor.commands as any).setTrackedChanges(positioned);
      }

      const metrics = analyzeText(text);
      setReadabilityMetrics(metrics);

      if (positioned.length === 0 && results.length === 0) {
        setError('No issues found — your writing looks great!');
      }

    } catch (err) {
      console.error('Deep analysis failed:', err);
      if (err instanceof ApiError) {
        setError(err.getUserMessage());
      } else if (err instanceof TypeError && (err as any).message?.includes('fetch')) {
        setError('Cannot reach the server. Please check that the backend is running.');
      } else {
        setError('Unable to analyze document. Please try again.');
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleApply = (id: string) => {
    const suggestion = suggestions.find(s => s.id === id);
    if (!suggestion || !editor) return;

    try {
      if (suggestion.type === 'insert' || suggestion.type === 'replace') {
        editor
          .chain()
          .focus()
          .insertContentAt(
            { from: suggestion.start, to: suggestion.end },
            suggestion.text
          )
          .run();
      } else if (suggestion.type === 'delete') {
        editor
          .chain()
          .focus()
          .deleteRange({ from: suggestion.start, to: suggestion.end })
          .run();
      }

      applySuggestion(id);
      recordCorrectionApplied();

      const updatedSuggestions = suggestions.map(s =>
        s.id === id ? { ...s, isApplied: true } : s
      );
      if ((editor.commands as any).setTrackedChanges) {
        (editor.commands as any).setTrackedChanges(updatedSuggestions);
      }
    } catch (err) {
      console.error('Failed to apply suggestion:', err);
    }
  };

  const handleDismiss = async (id: string) => {
    const suggestion = suggestions.find(s => s.id === id);
    if (!suggestion) return;

    try {
      await api.logCorrection({
        originalText: suggestion.original || suggestion.text,
        correctedText: suggestion.text,
        errorType: suggestion.category,
      });

      dismissSuggestion(id);
      recordCorrectionDismissed();

      const updatedSuggestions = suggestions.map(s =>
        s.id === id ? { ...s, isDismissed: true } : s
      );
      if ((editor?.commands as any)?.setTrackedChanges) {
        (editor!.commands as any).setTrackedChanges(updatedSuggestions);
      }
    } catch (err) {
      console.error('Failed to log dismissal:', err);
    }
  };

  const handleSuggestionClick = (id: string) => {
    const suggestion = suggestions.find(s => s.id === id);
    if (!suggestion || !editor) return;

    setActiveSuggestion(id);
    editor.commands.setTextSelection({
      from: suggestion.start,
      to: suggestion.end
    });
  };

  return (
    <div className="polish-panel" role="region" aria-label="Polish mode suggestions">
      {/* Deep Analysis Button */}
      <div className="polish-panel-section">
        <button
          className="btn btn-primary button-full-width"
          onClick={handleDeepAnalysis}
          disabled={isAnalyzing}
          aria-busy={isAnalyzing}
        >
          {isAnalyzing ? (
            <>
              <span className="spinner" aria-hidden="true" />
              Analyzing...
            </>
          ) : (
            'Run Deep Analysis'
          )}
        </button>
        {error && (
          <p className="polish-panel-error" role="alert">{error}</p>
        )}
      </div>

      {/* Tabs */}
      <div className="pp-tabs">
        <button
          className={`pp-tab ${activeTab === 'suggestions' ? 'active' : ''}`}
          onClick={() => setActiveTab('suggestions')}
        >
          Suggestions
        </button>
        <button
          className={`pp-tab ${activeTab === 'readability' ? 'active' : ''}`}
          onClick={() => setActiveTab('readability')}
        >
          Readability
        </button>
        <button
          className={`pp-tab ${activeTab === 'summary' ? 'active' : ''}`}
          onClick={() => setActiveTab('summary')}
        >
          Summary
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'suggestions' && (
        <div className="polish-panel-section">
          {activeSuggestions.length === 0 ? (
            <p className="polish-panel-empty">
              {isAnalyzing
                ? 'Analyzing your document...'
                : 'Run deep analysis to get suggestions'}
            </p>
          ) : (
            <div className="polish-panel-suggestions">
              {activeSuggestions.map((suggestion) => (
                <SuggestionCard
                  key={suggestion.id}
                  suggestion={suggestion}
                  onApply={() => handleApply(suggestion.id)}
                  onDismiss={() => handleDismiss(suggestion.id)}
                  onClick={() => handleSuggestionClick(suggestion.id)}
                  isActive={activeSuggestion === suggestion.id}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'readability' && (
        <div className="polish-panel-section">
          <ReadabilityScore metrics={readabilityMetrics} />
        </div>
      )}

      {activeTab === 'summary' && (
        <div className="polish-panel-section">
          <SessionSummary />
        </div>
      )}
    </div>
  );
}
