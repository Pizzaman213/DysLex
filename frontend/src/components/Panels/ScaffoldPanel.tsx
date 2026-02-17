import { useState } from 'react';
import { Editor } from '@tiptap/react';
import { useScaffoldStore } from '../../stores/scaffoldStore';
import { api } from '../../services/api';
import { Card } from '../Shared/Card';

interface ScaffoldPanelProps {
  editor: Editor | null;
}

export function ScaffoldPanel({ editor }: ScaffoldPanelProps) {
  const { topic, setTopic, sections, setSections } = useScaffoldStore();
  const [isLoading, setIsLoading] = useState(false);

  const handleGenerateScaffold = async () => {
    if (!topic.trim()) return;

    setIsLoading(true);
    try {
      const response = await api.generateScaffold({
        topic: topic.trim(),
      });

      setSections(response.sections);
    } catch (error) {
      console.error('Failed to generate scaffold:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSectionClick = (sectionId: string) => {
    if (!editor) return;

    // Find heading in editor that matches section title
    const section = sections.find((s) => s.id === sectionId);
    if (!section) return;

    // Search for heading with matching text
    const { doc } = editor.state;
    let targetPos: number | null = null;

    doc.descendants((node, pos) => {
      if (node.type.name.startsWith('heading') && node.textContent === section.title) {
        targetPos = pos;
        return false; // Stop searching
      }
    });

    if (targetPos !== null) {
      editor.chain().focus().setTextSelection(targetPos).scrollIntoView().run();
    }
  };

  const getStatusEmoji = (status: string) => {
    switch (status) {
      case 'complete':
        return '✓';
      case 'in-progress':
        return '◐';
      case 'empty':
      default:
        return '○';
    }
  };

  return (
    <div className="scaffold-panel">
      <div className="scaffold-panel__header">
        <h2 className="scaffold-panel__title">Outline</h2>

        <div className="scaffold-panel__input-group">
          <input
            type="text"
            className="scaffold-panel__input"
            placeholder="Enter your essay topic..."
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleGenerateScaffold();
              }
            }}
          />
          <button
            className="scaffold-panel__btn"
            onClick={handleGenerateScaffold}
            disabled={!topic.trim() || isLoading}
            type="button"
          >
            {isLoading ? 'Generating...' : 'Generate'}
          </button>
        </div>
      </div>

      <div className="scaffold-panel__sections">
        {sections.map((section) => (
          <Card
            key={section.id}
            className="scaffold-section"
            onClick={() => handleSectionClick(section.id)}
            tabIndex={0}
            role="button"
            aria-label={`Go to ${section.title}`}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleSectionClick(section.id);
              }
            }}
          >
            <div className="scaffold-section__header">
              <span className="scaffold-section__status" aria-label={`Status: ${section.status}`}>
                {getStatusEmoji(section.status)}
              </span>
              <h3 className="scaffold-section__title">{section.title}</h3>
            </div>

            {section.suggested_topic_sentence && (
              <p className="scaffold-section__topic-sentence">
                {section.suggested_topic_sentence}
              </p>
            )}

            {section.hints && section.hints.length > 0 && (
              <details className="scaffold-section__hints">
                <summary>Key points</summary>
                <ul>
                  {section.hints.map((hint, idx) => (
                    <li key={idx}>{hint}</li>
                  ))}
                </ul>
              </details>
            )}
          </Card>
        ))}

        {sections.length === 0 && !isLoading && (
          <div className="scaffold-panel__empty">
            <p>Enter a topic above to generate a writing scaffold.</p>
          </div>
        )}
      </div>
    </div>
  );
}
