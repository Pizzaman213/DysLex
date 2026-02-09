import { useState } from 'react';
import type { Editor } from '@tiptap/react';
import { useFormatStore, type FormatIssue } from '../../stores/formatStore';
import { useSettingsStore } from '../../stores/settingsStore';
import { PAPER_FORMATS } from '../../constants/paperFormats';
import { checkFormat } from '../../utils/formatChecker';
import { applyFormatFix } from '../../utils/applyFormat';
import { Card } from '../Shared/Card';
import { Badge } from '../Shared/Badge';

interface FormatPanelProps {
  editor: Editor | null;
}

export function FormatPanel(_props: FormatPanelProps) {
  const {
    activeFormat,
    issues,
    setIssues,
    dismissIssue,
    authorLastName,
    setAuthorLastName,
    shortenedTitle,
    setShortenedTitle,
    accessibilityOverride,
    setAccessibilityOverride,
  } = useFormatStore();
  const settings = useSettingsStore();
  const [headerOpen, setHeaderOpen] = useState(false);

  if (activeFormat === 'none') {
    return (
      <div className="format-panel" role="region" aria-label="Format panel">
        <h2 className="format-panel__title">Format</h2>
        <p className="format-panel__empty">
          Select a paper format from the toolbar to get started.
        </p>
      </div>
    );
  }

  const format = PAPER_FORMATS[activeFormat];

  const handleCheck = () => {
    const newIssues = checkFormat(
      format,
      {
        pageType: settings.pageType,
        font: settings.font,
        fontSize: settings.fontSize,
        lineSpacing: settings.lineSpacing,
        pageNumbers: settings.pageNumbers,
      },
      { authorLastName, shortenedTitle, accessibilityOverride }
    );
    setIssues(newIssues);
  };

  const handleFixAll = () => {
    const fixable = issues.filter((i) => i.canAutoFix);
    for (const issue of fixable) {
      applyFormatFix(issue, settings);
    }
    // Re-check after fixes
    setTimeout(handleCheck, 50);
  };

  const handleFix = (issue: FormatIssue) => {
    applyFormatFix(issue, settings);
    // Re-check after fix
    setTimeout(handleCheck, 50);
  };

  const errorCount = issues.filter((i) => i.severity === 'error').length;
  const warningCount = issues.filter((i) => i.severity === 'warning').length;
  const fixableCount = issues.filter((i) => i.canAutoFix).length;

  const showHeader = format.runningHeaderType === 'lastname-page' || format.runningHeaderType === 'shortened-title';

  return (
    <div className="format-panel" role="region" aria-label="Format panel">
      <div className="format-panel__header">
        <h2 className="format-panel__title">{format.name}</h2>
      </div>

      <div className="format-panel__actions">
        <button
          className="format-panel__check-btn"
          onClick={handleCheck}
          type="button"
        >
          Check Format
        </button>
        {fixableCount > 1 && (
          <button
            className="format-panel__fix-all-btn"
            onClick={handleFixAll}
            type="button"
          >
            Fix All ({fixableCount})
          </button>
        )}
      </div>

      {/* Header fields */}
      {showHeader && (
        <div className="format-panel__section">
          <button
            className="format-panel__section-toggle"
            onClick={() => setHeaderOpen(!headerOpen)}
            type="button"
            aria-expanded={headerOpen}
          >
            Running Header
            <span className="format-panel__chevron" aria-hidden="true">
              {headerOpen ? '\u25B4' : '\u25BE'}
            </span>
          </button>
          {headerOpen && (
            <div className="format-panel__section-body">
              {format.runningHeaderType === 'lastname-page' && (
                <label className="format-panel__field">
                  <span className="format-panel__field-label">Last Name</span>
                  <input
                    type="text"
                    className="format-panel__input"
                    value={authorLastName}
                    onChange={(e) => setAuthorLastName(e.target.value)}
                    placeholder="e.g. Smith"
                  />
                </label>
              )}
              {format.runningHeaderType === 'shortened-title' && (
                <label className="format-panel__field">
                  <span className="format-panel__field-label">Shortened Title</span>
                  <input
                    type="text"
                    className="format-panel__input"
                    value={shortenedTitle}
                    onChange={(e) => setShortenedTitle(e.target.value)}
                    placeholder="e.g. RUNNING HEAD"
                  />
                </label>
              )}
            </div>
          )}
        </div>
      )}

      {/* Accessibility override */}
      <div className="format-panel__section">
        <label className="format-panel__toggle-row">
          <input
            type="checkbox"
            checked={accessibilityOverride}
            onChange={(e) => setAccessibilityOverride(e.target.checked)}
          />
          <span className="format-panel__toggle-label">
            Keep dyslexic font in editor
          </span>
        </label>
        {accessibilityOverride && (
          <p className="format-panel__hint">
            Your comfortable font stays in the editor. Exports will use the format's required font.
          </p>
        )}
      </div>

      {/* Issues list */}
      {issues.length === 0 ? (
        <p className="format-panel__empty">
          Click "Check Format" to validate your document.
        </p>
      ) : errorCount === 0 && warningCount === 0 ? (
        <div className="format-panel__pass">
          All checks passed — your formatting looks great!
        </div>
      ) : (
        <div className="format-panel__list">
          {issues.map((issue) => (
            <Card
              key={issue.id}
              className="format-issue-card"
            >
              <div className="format-issue-card__header">
                <Badge variant={issue.severity as any}>
                  {getCategoryLabel(issue.category)}
                </Badge>
                {issue.severity === 'info' && (
                  <span className="format-issue-card__info-badge">Info</span>
                )}
              </div>

              <p className="format-issue-card__description">{issue.description}</p>

              <div className="format-issue-card__values">
                <span className="format-issue-card__current">
                  Current: {issue.currentValue}
                </span>
                <span className="format-issue-card__arrow" aria-hidden="true">
                  {'\u2192'}
                </span>
                <span className="format-issue-card__expected">
                  Expected: {issue.expectedValue}
                </span>
              </div>

              <div className="format-issue-card__actions">
                {issue.canAutoFix && (
                  <button
                    className="format-issue-card__btn format-issue-card__btn--fix"
                    onClick={() => handleFix(issue)}
                    type="button"
                  >
                    Fix
                  </button>
                )}
                <button
                  className="format-issue-card__btn format-issue-card__btn--dismiss"
                  onClick={() => dismissIssue(issue.id)}
                  type="button"
                >
                  Dismiss
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function getCategoryLabel(category: string): string {
  switch (category) {
    case 'margins': return 'Margins';
    case 'font': return 'Font';
    case 'spacing': return 'Spacing';
    case 'indentation': return 'Indent';
    case 'headings': return 'Headings';
    case 'pageNumbers': return 'Page #';
    case 'header': return 'Header';
    default: return category;
  }
}
