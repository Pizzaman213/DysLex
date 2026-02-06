import { useState, useEffect } from 'react';

interface DocsViewerProps {
  docPath: string;
}

export function DocsViewer({ docPath }: DocsViewerProps) {
  const [content, setContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDoc = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(`/docs/${docPath}`);
        if (!response.ok) {
          throw new Error('Document not found');
        }
        const text = await response.text();
        setContent(text);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load document');
      } finally {
        setIsLoading(false);
      }
    };

    fetchDoc();
  }, [docPath]);

  if (isLoading) {
    return (
      <div className="docs-viewer docs-loading" role="status">
        <p>Loading documentation...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="docs-viewer docs-error" role="alert">
        <p>Error: {error}</p>
      </div>
    );
  }

  return (
    <article className="docs-viewer" aria-label={`Documentation: ${docPath}`}>
      <div className="docs-content" dangerouslySetInnerHTML={{ __html: content }} />
    </article>
  );
}
