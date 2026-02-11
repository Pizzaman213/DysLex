import { describe, it, expect, beforeEach } from 'vitest';
import { useCaptureStore } from '../captureStore';
import type { ThoughtCard, CapturePhase } from '../captureStore';

describe('captureStore', () => {
  beforeEach(() => {
    useCaptureStore.setState({
      phase: 'idle',
      transcript: '',
      cards: [],
      error: null,
      takes: 0,
      audioBlobs: [],
      audioUrls: [],
      lastExtractedOffset: 0,
      isIncrementalExtracting: false,
      brainstormActive: false,
      brainstormAutoProbe: true,
      sessions: {},
      _transientSession: {},
      _activeDocumentId: null,
    });
    useCaptureStore.getState().setActiveDocument('test-doc');
  });

  it('has correct default state', () => {
    const state = useCaptureStore.getState();
    expect(state.phase).toBe('idle');
    expect(state.transcript).toBe('');
    expect(state.cards).toEqual([]);
    expect(state.error).toBeNull();
    expect(state.takes).toBe(0);
    expect(state.audioBlobs).toEqual([]);
    expect(state.audioUrls).toEqual([]);
    expect(state.lastExtractedOffset).toBe(0);
    expect(state.isIncrementalExtracting).toBe(false);
    expect(state.brainstormActive).toBe(false);
    expect(state.brainstormAutoProbe).toBe(true);
  });

  it('setPhase updates phase to each valid value', () => {
    const phases: CapturePhase[] = [
      'idle', 'recording', 'recorded', 'transcribing',
      'extracting', 'review', 'brainstorming',
    ];
    for (const phase of phases) {
      useCaptureStore.getState().setPhase(phase);
      expect(useCaptureStore.getState().phase).toBe(phase);
    }
  });

  it('setTranscript updates transcript', () => {
    useCaptureStore.getState().setTranscript('Hello world');
    expect(useCaptureStore.getState().transcript).toBe('Hello world');
  });

  it('appendTranscript appends text to existing transcript', () => {
    useCaptureStore.getState().setTranscript('Hello');
    useCaptureStore.getState().appendTranscript('world');
    expect(useCaptureStore.getState().transcript).toBe('Hello world');
  });

  it('appendTranscript sets text when transcript is empty', () => {
    useCaptureStore.getState().appendTranscript('first words');
    expect(useCaptureStore.getState().transcript).toBe('first words');
  });

  it('setCards sets cards array', () => {
    const cards: ThoughtCard[] = [
      { id: '1', title: 'Idea A', body: 'Body A', sub_ideas: [] },
      { id: '2', title: 'Idea B', body: 'Body B', sub_ideas: [] },
    ];
    useCaptureStore.getState().setCards(cards);
    expect(useCaptureStore.getState().cards).toEqual(cards);
  });

  it('appendCards adds cards with deduplication', () => {
    const existing: ThoughtCard[] = [
      { id: '1', title: 'Idea A', body: 'Body A', sub_ideas: [] },
    ];
    useCaptureStore.getState().setCards(existing);

    const newCards: ThoughtCard[] = [
      { id: '2', title: 'Idea A', body: 'Duplicate', sub_ideas: [] }, // duplicate title
      { id: '3', title: 'Idea B', body: 'Body B', sub_ideas: [] },   // unique
    ];
    useCaptureStore.getState().appendCards(newCards);

    const cards = useCaptureStore.getState().cards;
    expect(cards).toHaveLength(2);
    expect(cards[0].id).toBe('1');
    expect(cards[1].id).toBe('3');
  });

  it('setError sets error string', () => {
    useCaptureStore.getState().setError('Something went wrong');
    expect(useCaptureStore.getState().error).toBe('Something went wrong');
  });

  it('setError(null) clears error', () => {
    useCaptureStore.getState().setError('An error');
    useCaptureStore.getState().setError(null);
    expect(useCaptureStore.getState().error).toBeNull();
  });

  it('updateCard updates matching card by id, leaves others unchanged', () => {
    const cards: ThoughtCard[] = [
      { id: '1', title: 'Original A', body: 'Body A', sub_ideas: [] },
      { id: '2', title: 'Original B', body: 'Body B', sub_ideas: [] },
    ];
    useCaptureStore.getState().setCards(cards);
    useCaptureStore.getState().updateCard('1', { title: 'Updated A' });

    const updated = useCaptureStore.getState().cards;
    expect(updated[0]).toEqual({ id: '1', title: 'Updated A', body: 'Body A', sub_ideas: [] });
    expect(updated[1]).toEqual({ id: '2', title: 'Original B', body: 'Body B', sub_ideas: [] });
  });

  it('removeCard filters out card by id', () => {
    const cards: ThoughtCard[] = [
      { id: '1', title: 'A', body: 'Body A', sub_ideas: [] },
      { id: '2', title: 'B', body: 'Body B', sub_ideas: [] },
      { id: '3', title: 'C', body: 'Body C', sub_ideas: [] },
    ];
    useCaptureStore.getState().setCards(cards);
    useCaptureStore.getState().removeCard('2');

    const remaining = useCaptureStore.getState().cards;
    expect(remaining).toHaveLength(2);
    expect(remaining.map((c) => c.id)).toEqual(['1', '3']);
  });

  it('reorderCards moves card from oldIndex to newIndex', () => {
    const cards: ThoughtCard[] = [
      { id: 'A', title: 'A', body: '', sub_ideas: [] },
      { id: 'B', title: 'B', body: '', sub_ideas: [] },
      { id: 'C', title: 'C', body: '', sub_ideas: [] },
    ];
    useCaptureStore.getState().setCards(cards);
    // Move index 0 to index 2: [A,B,C] -> [B,C,A]
    useCaptureStore.getState().reorderCards(0, 2);

    const reordered = useCaptureStore.getState().cards;
    expect(reordered.map((c) => c.id)).toEqual(['B', 'C', 'A']);
  });

  it('incrementTakes increments takes counter', () => {
    expect(useCaptureStore.getState().takes).toBe(0);
    useCaptureStore.getState().incrementTakes();
    expect(useCaptureStore.getState().takes).toBe(1);
    useCaptureStore.getState().incrementTakes();
    expect(useCaptureStore.getState().takes).toBe(2);
  });

  it('setLastExtractedOffset updates offset', () => {
    useCaptureStore.getState().setLastExtractedOffset(42);
    expect(useCaptureStore.getState().lastExtractedOffset).toBe(42);
  });

  it('setIncrementalExtracting updates flag', () => {
    useCaptureStore.getState().setIncrementalExtracting(true);
    expect(useCaptureStore.getState().isIncrementalExtracting).toBe(true);
    useCaptureStore.getState().setIncrementalExtracting(false);
    expect(useCaptureStore.getState().isIncrementalExtracting).toBe(false);
  });

  // Sub-idea actions
  it('addSubIdea adds a sub-idea to the specified card', () => {
    const cards: ThoughtCard[] = [
      { id: '1', title: 'Main', body: '', sub_ideas: [] },
    ];
    useCaptureStore.getState().setCards(cards);
    useCaptureStore.getState().addSubIdea('1');

    const updated = useCaptureStore.getState().cards[0];
    expect(updated.sub_ideas).toHaveLength(1);
    expect(updated.sub_ideas[0].id).toBe('1-sub-1');
    expect(updated.sub_ideas[0].title).toBe('');
    expect(updated.sub_ideas[0].body).toBe('');
  });

  it('updateSubIdea updates a specific sub-idea', () => {
    const cards: ThoughtCard[] = [
      {
        id: '1', title: 'Main', body: '',
        sub_ideas: [{ id: 'sub-1', title: 'Old', body: 'Old body' }],
      },
    ];
    useCaptureStore.getState().setCards(cards);
    useCaptureStore.getState().updateSubIdea('1', 'sub-1', { title: 'New' });

    const sub = useCaptureStore.getState().cards[0].sub_ideas[0];
    expect(sub.title).toBe('New');
    expect(sub.body).toBe('Old body'); // unchanged
  });

  it('removeSubIdea removes a specific sub-idea', () => {
    const cards: ThoughtCard[] = [
      {
        id: '1', title: 'Main', body: '',
        sub_ideas: [
          { id: 'sub-1', title: 'A', body: '' },
          { id: 'sub-2', title: 'B', body: '' },
        ],
      },
    ];
    useCaptureStore.getState().setCards(cards);
    useCaptureStore.getState().removeSubIdea('1', 'sub-1');

    const subs = useCaptureStore.getState().cards[0].sub_ideas;
    expect(subs).toHaveLength(1);
    expect(subs[0].id).toBe('sub-2');
  });

  // Brainstorm actions
  it('setBrainstormActive updates brainstorm state', () => {
    useCaptureStore.getState().setBrainstormActive(true);
    expect(useCaptureStore.getState().brainstormActive).toBe(true);
    useCaptureStore.getState().setBrainstormActive(false);
    expect(useCaptureStore.getState().brainstormActive).toBe(false);
  });

  it('setBrainstormAutoProbe updates auto-probe setting', () => {
    useCaptureStore.getState().setBrainstormAutoProbe(false);
    expect(useCaptureStore.getState().brainstormAutoProbe).toBe(false);
    useCaptureStore.getState().setBrainstormAutoProbe(true);
    expect(useCaptureStore.getState().brainstormAutoProbe).toBe(true);
  });

  it('reset returns to initial state including new fields', () => {
    useCaptureStore.getState().setPhase('recording');
    useCaptureStore.getState().setTranscript('Some text');
    useCaptureStore.getState().setCards([{ id: '1', title: 'T', body: 'B', sub_ideas: [] }]);
    useCaptureStore.getState().setError('err');
    useCaptureStore.getState().incrementTakes();
    useCaptureStore.getState().setLastExtractedOffset(100);
    useCaptureStore.getState().setIncrementalExtracting(true);
    useCaptureStore.getState().setBrainstormActive(true);
    useCaptureStore.getState().setBrainstormAutoProbe(false);

    useCaptureStore.getState().reset();

    const state = useCaptureStore.getState();
    expect(state.phase).toBe('idle');
    expect(state.transcript).toBe('');
    expect(state.cards).toEqual([]);
    expect(state.error).toBeNull();
    expect(state.takes).toBe(0);
    expect(state.audioBlobs).toEqual([]);
    expect(state.audioUrls).toEqual([]);
    expect(state.lastExtractedOffset).toBe(0);
    expect(state.isIncrementalExtracting).toBe(false);
    expect(state.brainstormActive).toBe(false);
    expect(state.brainstormAutoProbe).toBe(true);
  });

  it('reset clears persisted session for active document', () => {
    useCaptureStore.getState().setTranscript('Doc A text');
    useCaptureStore.getState().setCards([{ id: '1', title: 'Card', body: '', sub_ideas: [] }]);

    // Save by switching away
    useCaptureStore.getState().setActiveDocument('other-doc');
    expect(useCaptureStore.getState().sessions['test-doc']).toBeDefined();

    // Switch back and reset
    useCaptureStore.getState().setActiveDocument('test-doc');
    useCaptureStore.getState().reset();

    expect(useCaptureStore.getState().sessions['test-doc']).toBeUndefined();
  });

  // ---------- Per-Document Capture Sessions ----------

  describe('Per-Document Capture Sessions', () => {
    it('switching documents saves and loads capture data', () => {
      // Set data for doc A (test-doc)
      useCaptureStore.getState().setTranscript('Doc A transcript');
      useCaptureStore.getState().setCards([{ id: '1', title: 'Idea A', body: 'A', sub_ideas: [] }]);
      useCaptureStore.getState().setPhase('review');

      // Switch to doc B — should be empty
      useCaptureStore.getState().setActiveDocument('doc-b');
      expect(useCaptureStore.getState().transcript).toBe('');
      expect(useCaptureStore.getState().cards).toEqual([]);
      expect(useCaptureStore.getState().phase).toBe('idle');

      // Set data for doc B
      useCaptureStore.getState().setTranscript('Doc B transcript');
      useCaptureStore.getState().setPhase('recorded');

      // Switch back to doc A
      useCaptureStore.getState().setActiveDocument('test-doc');
      expect(useCaptureStore.getState().transcript).toBe('Doc A transcript');
      expect(useCaptureStore.getState().cards).toHaveLength(1);
      expect(useCaptureStore.getState().cards[0].title).toBe('Idea A');
      expect(useCaptureStore.getState().phase).toBe('review');

      // Switch back to doc B
      useCaptureStore.getState().setActiveDocument('doc-b');
      expect(useCaptureStore.getState().transcript).toBe('Doc B transcript');
      expect(useCaptureStore.getState().phase).toBe('recorded');
    });

    it('new document gets empty capture session', () => {
      useCaptureStore.getState().setTranscript('existing text');
      useCaptureStore.getState().setCards([{ id: '1', title: 'T', body: '', sub_ideas: [] }]);

      useCaptureStore.getState().setActiveDocument('brand-new');

      const state = useCaptureStore.getState();
      expect(state.transcript).toBe('');
      expect(state.cards).toEqual([]);
      expect(state.takes).toBe(0);
      expect(state.phase).toBe('idle');
      expect(state.error).toBeNull();
    });

    it('setActiveDocument is a no-op for the same document', () => {
      useCaptureStore.getState().setTranscript('some text');
      const transcriptBefore = useCaptureStore.getState().transcript;

      useCaptureStore.getState().setActiveDocument('test-doc');

      expect(useCaptureStore.getState().transcript).toBe(transcriptBefore);
    });

    it('deleteDocumentSession removes persisted data', () => {
      useCaptureStore.getState().setTranscript('text');

      // Switch to save test-doc's data
      useCaptureStore.getState().setActiveDocument('doc-b');
      expect(useCaptureStore.getState().sessions['test-doc']).toBeDefined();

      useCaptureStore.getState().deleteDocumentSession('test-doc');
      expect(useCaptureStore.getState().sessions['test-doc']).toBeUndefined();
    });

    it('transient data (phase, error) is preserved per document', () => {
      useCaptureStore.getState().setPhase('recording');
      useCaptureStore.getState().setError('mic error');

      // Switch to doc B
      useCaptureStore.getState().setActiveDocument('doc-b');
      expect(useCaptureStore.getState().phase).toBe('idle');
      expect(useCaptureStore.getState().error).toBeNull();

      // Switch back to doc A
      useCaptureStore.getState().setActiveDocument('test-doc');
      expect(useCaptureStore.getState().phase).toBe('recording');
      expect(useCaptureStore.getState().error).toBe('mic error');
    });

    it('derives phase from persisted data for new transient sessions', () => {
      // Set up doc with transcript but no cards
      useCaptureStore.getState().setTranscript('some text');
      useCaptureStore.getState().setPhase('recorded');

      // Switch away and back — transient is saved, so phase is restored
      useCaptureStore.getState().setActiveDocument('doc-b');
      useCaptureStore.getState().setActiveDocument('test-doc');
      expect(useCaptureStore.getState().phase).toBe('recorded');
    });

    it('brainstormAutoProbe is saved per document', () => {
      useCaptureStore.getState().setBrainstormAutoProbe(false);

      useCaptureStore.getState().setActiveDocument('doc-b');
      expect(useCaptureStore.getState().brainstormAutoProbe).toBe(true); // default

      useCaptureStore.getState().setActiveDocument('test-doc');
      expect(useCaptureStore.getState().brainstormAutoProbe).toBe(false);
    });
  });

  // ---------- Migration ----------

  describe('Migration v0 → v1', () => {
    it('wraps top-level capture data into sessions with default doc ID', () => {
      const DEFAULT_DOC_ID = '00000000-0000-4000-8000-000000000001';
      const v0State = {
        transcript: 'hello world',
        cards: [{ id: '1', title: 'Idea', body: 'text', sub_ideas: [] }],
        takes: 2,
        brainstormAutoProbe: false,
      };

      const { migrate } = (useCaptureStore as any).persist.getOptions();
      const migrated = migrate(structuredClone(v0State), 0);

      expect(migrated.sessions).toBeDefined();
      expect(migrated.sessions[DEFAULT_DOC_ID]).toBeDefined();
      expect(migrated.sessions[DEFAULT_DOC_ID].transcript).toBe('hello world');
      expect(migrated.sessions[DEFAULT_DOC_ID].cards).toHaveLength(1);
      expect(migrated.sessions[DEFAULT_DOC_ID].takes).toBe(2);
      expect(migrated.sessions[DEFAULT_DOC_ID].brainstormAutoProbe).toBe(false);
      expect(migrated._activeDocumentId).toBe(DEFAULT_DOC_ID);

      // Old top-level fields removed
      expect(migrated.transcript).toBeUndefined();
      expect(migrated.cards).toBeUndefined();
      expect(migrated.takes).toBeUndefined();
      expect(migrated.brainstormAutoProbe).toBeUndefined();
    });
  });
});
