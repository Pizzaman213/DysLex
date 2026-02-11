import { describe, it, expect, beforeEach } from 'vitest';
import { useCoachStore } from '../coachStore';

describe('coachStore', () => {
  beforeEach(() => {
    useCoachStore.setState({
      messages: [],
      isLoading: false,
      _documentSessions: {},
      _activeDocumentId: null,
    });
    useCoachStore.getState().setActiveDocument('test-doc');
  });

  it('has correct default state', () => {
    const state = useCoachStore.getState();
    expect(state.messages).toEqual([]);
    expect(state.isLoading).toBe(false);
  });

  it('addMessage appends a message', () => {
    useCoachStore.getState().addMessage('user', 'Hello');
    useCoachStore.getState().addMessage('coach', 'Hi there!');

    const msgs = useCoachStore.getState().messages;
    expect(msgs).toHaveLength(2);
    expect(msgs[0].role).toBe('user');
    expect(msgs[0].content).toBe('Hello');
    expect(msgs[1].role).toBe('coach');
    expect(msgs[1].content).toBe('Hi there!');
  });

  it('setLoading updates isLoading', () => {
    useCoachStore.getState().setLoading(true);
    expect(useCoachStore.getState().isLoading).toBe(true);
    useCoachStore.getState().setLoading(false);
    expect(useCoachStore.getState().isLoading).toBe(false);
  });

  it('clearMessages resets messages and loading', () => {
    useCoachStore.getState().addMessage('user', 'Test');
    useCoachStore.getState().setLoading(true);

    useCoachStore.getState().clearMessages();

    expect(useCoachStore.getState().messages).toEqual([]);
    expect(useCoachStore.getState().isLoading).toBe(false);
  });

  it('clearMessages removes persisted session for active document', () => {
    useCoachStore.getState().addMessage('user', 'Hello');

    // Switch away to save
    useCoachStore.getState().setActiveDocument('other');
    expect(useCoachStore.getState()._documentSessions['test-doc']).toBeDefined();

    // Switch back and clear
    useCoachStore.getState().setActiveDocument('test-doc');
    useCoachStore.getState().clearMessages();

    expect(useCoachStore.getState()._documentSessions['test-doc']).toBeUndefined();
  });

  // ---------- Per-Document Coach Sessions ----------

  describe('Per-Document Coach Sessions', () => {
    it('switching documents saves and loads messages', () => {
      // Add messages to doc A
      useCoachStore.getState().addMessage('user', 'Doc A question');
      useCoachStore.getState().addMessage('coach', 'Doc A answer');
      expect(useCoachStore.getState().messages).toHaveLength(2);

      // Switch to doc B — should be empty
      useCoachStore.getState().setActiveDocument('doc-b');
      expect(useCoachStore.getState().messages).toEqual([]);

      // Add messages to doc B
      useCoachStore.getState().addMessage('user', 'Doc B question');
      expect(useCoachStore.getState().messages).toHaveLength(1);

      // Switch back to doc A
      useCoachStore.getState().setActiveDocument('test-doc');
      expect(useCoachStore.getState().messages).toHaveLength(2);
      expect(useCoachStore.getState().messages[0].content).toBe('Doc A question');

      // Switch back to doc B
      useCoachStore.getState().setActiveDocument('doc-b');
      expect(useCoachStore.getState().messages).toHaveLength(1);
      expect(useCoachStore.getState().messages[0].content).toBe('Doc B question');
    });

    it('new document gets empty coach session', () => {
      useCoachStore.getState().addMessage('user', 'existing');

      useCoachStore.getState().setActiveDocument('brand-new');

      expect(useCoachStore.getState().messages).toEqual([]);
      expect(useCoachStore.getState().isLoading).toBe(false);
    });

    it('setActiveDocument is a no-op for the same document', () => {
      useCoachStore.getState().addMessage('user', 'test');
      const msgsBefore = useCoachStore.getState().messages;

      useCoachStore.getState().setActiveDocument('test-doc');

      expect(useCoachStore.getState().messages).toBe(msgsBefore);
    });

    it('deleteDocumentSession removes session data', () => {
      useCoachStore.getState().addMessage('user', 'test');

      // Switch to save
      useCoachStore.getState().setActiveDocument('doc-b');
      expect(useCoachStore.getState()._documentSessions['test-doc']).toBeDefined();

      useCoachStore.getState().deleteDocumentSession('test-doc');
      expect(useCoachStore.getState()._documentSessions['test-doc']).toBeUndefined();
    });

    it('isLoading is preserved per document', () => {
      useCoachStore.getState().setLoading(true);

      useCoachStore.getState().setActiveDocument('doc-b');
      expect(useCoachStore.getState().isLoading).toBe(false);

      useCoachStore.getState().setActiveDocument('test-doc');
      expect(useCoachStore.getState().isLoading).toBe(true);
    });
  });
});
