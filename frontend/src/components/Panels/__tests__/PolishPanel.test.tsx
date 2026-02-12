import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PolishPanel } from '../PolishPanel';
import { usePolishStore } from '@/stores/polishStore';
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

vi.mock('@/services/api', () => ({
  api: {
    deepAnalysis: vi.fn(),
    logCorrection: vi.fn(),
    getSettings: vi.fn(),
    updateSettings: vi.fn(),
  },
}));

vi.mock('@/services/apiErrors', () => ({
  ApiError: class extends Error {
    constructor(m: string) {
      super(m);
    }
    getUserMessage() {
      return this.message;
    }
  },
}));

// Mock recharts to avoid SVG rendering issues in jsdom
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  RadarChart: () => <div data-testid="radar-chart" />,
  PolarGrid: () => null,
  PolarAngleAxis: () => null,
  PolarRadiusAxis: () => null,
  Radar: () => null,
}));

// Mock readabilityUtils to avoid complex calculations in tests
vi.mock('@/utils/readabilityUtils', () => ({
  analyzeText: vi.fn(() => ({
    grade: 8.5,
    readingEase: 60,
    wordCount: 100,
    sentenceCount: 10,
    avgSentenceLength: 10,
    level: 'medium',
  })),
}));

beforeEach(() => {
  usePolishStore.setState({
    suggestions: [],
    isAnalyzing: false,
    activeSuggestion: null,
  });
  useSessionStore.setState({
    correctionsApplied: 0,
    correctionsDismissed: 0,
  });
});

describe('PolishPanel', () => {
  it('"Run Deep Analysis" button renders', () => {
    render(<PolishPanel editor={null} />);
    const btn = screen.getByRole('button', { name: /run deep analysis/i });
    expect(btn).toBeInTheDocument();
  });

  it('button is disabled and shows "Analyzing..." when isAnalyzing is true', () => {
    usePolishStore.setState({ isAnalyzing: true });
    render(<PolishPanel editor={null} />);

    const btn = screen.getByRole('button', { name: /analyzing/i });
    expect(btn).toBeDisabled();
    expect(btn).toHaveTextContent('Analyzing...');
  });

  it('clicking "Readability" tab shows readability content', () => {
    render(<PolishPanel editor={null} />);

    const readabilityTab = screen.getByRole('button', { name: /^readability$/i });
    fireEvent.click(readabilityTab);

    // ReadabilityScore component renders its region with "Readability metrics" aria-label
    expect(screen.getByRole('region', { name: /readability metrics/i })).toBeInTheDocument();
  });

  it('clicking "Summary" tab shows session summary content', () => {
    render(<PolishPanel editor={null} />);

    const summaryTab = screen.getByRole('button', { name: /summary/i });
    fireEvent.click(summaryTab);

    // SessionSummary renders "Session Summary" heading
    expect(screen.getByText('Session Summary')).toBeInTheDocument();
  });

  it('empty suggestions state shows appropriate message', () => {
    render(<PolishPanel editor={null} />);

    // Default tab is "suggestions" and with no suggestions it shows the empty message
    expect(
      screen.getByText(/run deep analysis to get suggestions/i)
    ).toBeInTheDocument();
  });

  it('shows "Analyzing your document..." when isAnalyzing and no suggestions', () => {
    usePolishStore.setState({ isAnalyzing: true });
    render(<PolishPanel editor={null} />);

    expect(
      screen.getByText(/analyzing your document/i)
    ).toBeInTheDocument();
  });
});
