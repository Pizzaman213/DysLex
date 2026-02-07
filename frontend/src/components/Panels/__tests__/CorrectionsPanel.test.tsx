import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CorrectionsPanel } from '../CorrectionsPanel';
import { useEditorStore, Correction } from '@/stores/editorStore';
import { useSessionStore } from '@/stores/sessionStore';

// Mock documentSync to prevent errors from session store persist middleware
vi.mock('@/services/documentSync', () => ({
  syncCreateDocument: vi.fn(),
  syncDeleteDocument: vi.fn(),
  syncUpdateDocumentTitle: vi.fn(),
  syncUpdateDocumentContent: vi.fn(),
  syncCreateFolder: vi.fn(),
  syncDeleteFolder: vi.fn(),
  syncRenameFolder: vi.fn(),
  syncMoveDocument: vi.fn(),
  initializeFromServer: vi.fn(),
}));

const sampleCorrections: Correction[] = [
  {
    id: 'c1',
    original: 'teh',
    suggested: 'the',
    type: 'spelling',
    start: 0,
    end: 3,
    explanation: 'Common swap',
  },
  {
    id: 'c2',
    original: 'there',
    suggested: 'their',
    type: 'confusion',
    start: 10,
    end: 15,
    explanation: 'Possessive needed here',
  },
];

beforeEach(() => {
  useEditorStore.setState({ corrections: [], activeCorrection: null });
  useSessionStore.setState({ correctionsApplied: 0, correctionsDismissed: 0 });
});

describe('CorrectionsPanel', () => {
  it('has role="region" and aria-label="Corrections panel"', () => {
    render(<CorrectionsPanel editor={null} />);
    const panel = screen.getByRole('region', { name: 'Corrections panel' });
    expect(panel).toBeInTheDocument();
  });

  it('shows "No suggestions right now" when there are no corrections', () => {
    render(<CorrectionsPanel editor={null} />);
    expect(screen.getByText(/no suggestions right now/i)).toBeInTheDocument();
  });

  it('renders correction cards showing original and suggested text', () => {
    useEditorStore.setState({ corrections: sampleCorrections });
    render(<CorrectionsPanel editor={null} />);

    expect(screen.getByText('teh')).toBeInTheDocument();
    expect(screen.getByText('the')).toBeInTheDocument();
    expect(screen.getByText('there')).toBeInTheDocument();
    expect(screen.getByText('their')).toBeInTheDocument();
  });

  it('renders the type badge with human-readable label', () => {
    useEditorStore.setState({ corrections: sampleCorrections });
    render(<CorrectionsPanel editor={null} />);

    // "spelling" maps to "Spelling", "confusion" maps to "Word Choice"
    expect(screen.getByText('Spelling')).toBeInTheDocument();
    expect(screen.getByText('Word Choice')).toBeInTheDocument();
  });

  it('shows explanation text when provided on a correction', () => {
    useEditorStore.setState({ corrections: sampleCorrections });
    render(<CorrectionsPanel editor={null} />);

    expect(screen.getByText('Common swap')).toBeInTheDocument();
    expect(screen.getByText('Possessive needed here')).toBeInTheDocument();
  });

  it('dismiss button calls dismissCorrection and recordCorrectionDismissed', () => {
    useEditorStore.setState({ corrections: sampleCorrections });
    render(<CorrectionsPanel editor={null} />);

    const dismissButtons = screen.getAllByRole('button', { name: /dismiss/i });
    fireEvent.click(dismissButtons[0]);

    // The correction should now be marked as dismissed in the store
    const state = useEditorStore.getState();
    const dismissed = state.corrections.find((c) => c.id === 'c1');
    expect(dismissed?.isDismissed).toBe(true);

    // Session store should have recorded the dismissal
    expect(useSessionStore.getState().correctionsDismissed).toBe(1);
  });

  it('"Apply All" button is visible when more than 1 active correction', () => {
    useEditorStore.setState({ corrections: sampleCorrections });
    render(<CorrectionsPanel editor={null} />);

    const applyAllBtn = screen.getByRole('button', { name: /apply all/i });
    expect(applyAllBtn).toBeInTheDocument();
  });

  it('"Apply All" button is not visible when 0 or 1 active correction', () => {
    // 0 corrections
    render(<CorrectionsPanel editor={null} />);
    expect(screen.queryByRole('button', { name: /apply all/i })).not.toBeInTheDocument();

    // 1 correction
    useEditorStore.setState({ corrections: [sampleCorrections[0]] });
    const { unmount } = render(<CorrectionsPanel editor={null} />);
    expect(screen.queryByRole('button', { name: /apply all/i })).not.toBeInTheDocument();
    unmount();
  });

  it('filters out applied and dismissed corrections from the rendered list', () => {
    const mixedCorrections: Correction[] = [
      { ...sampleCorrections[0], isApplied: true },
      { ...sampleCorrections[1], isDismissed: true },
      {
        id: 'c3',
        original: 'becuase',
        suggested: 'because',
        type: 'spelling',
        start: 20,
        end: 27,
        explanation: 'Transposed letters',
      },
    ];
    useEditorStore.setState({ corrections: mixedCorrections });
    render(<CorrectionsPanel editor={null} />);

    // Only the third correction should render
    expect(screen.queryByText('teh')).not.toBeInTheDocument();
    expect(screen.queryByText('there')).not.toBeInTheDocument();
    expect(screen.getByText('becuase')).toBeInTheDocument();
    expect(screen.getByText('because')).toBeInTheDocument();
  });
});
