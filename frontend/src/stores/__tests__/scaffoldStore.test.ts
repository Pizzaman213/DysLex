import { describe, it, expect, beforeEach } from 'vitest';
import { useScaffoldStore, ScaffoldSection } from '../scaffoldStore';
import type { Scaffold } from '@/components/WritingModes/MindMap/types';

beforeEach(() => {
  useScaffoldStore.setState({ topic: '', sections: [], isLoading: false });
});

describe('scaffoldStore', () => {
  it('has correct default state: empty topic, empty sections, isLoading false', () => {
    const state = useScaffoldStore.getState();
    expect(state.topic).toBe('');
    expect(state.sections).toEqual([]);
    expect(state.isLoading).toBe(false);
  });

  it('setTopic updates the topic', () => {
    useScaffoldStore.getState().setTopic('Climate Change');
    expect(useScaffoldStore.getState().topic).toBe('Climate Change');
  });

  it('setSections adds status "empty" to each section', () => {
    const raw: Omit<ScaffoldSection, 'status'>[] = [
      { id: 's1', title: 'Introduction', type: 'intro', order: 0 },
      { id: 's2', title: 'Body', type: 'body', order: 1, suggested_topic_sentence: 'Start here.' },
      { id: 's3', title: 'Conclusion', type: 'conclusion', order: 2, hints: ['Summarize'] },
    ];

    useScaffoldStore.getState().setSections(raw);
    const sections = useScaffoldStore.getState().sections;

    expect(sections).toHaveLength(3);
    sections.forEach((s) => {
      expect(s.status).toBe('empty');
    });
    expect(sections[0].title).toBe('Introduction');
    expect(sections[1].suggested_topic_sentence).toBe('Start here.');
    expect(sections[2].hints).toEqual(['Summarize']);
  });

  it('updateSectionStatus changes status on the matching section', () => {
    const raw: Omit<ScaffoldSection, 'status'>[] = [
      { id: 's1', title: 'Introduction', type: 'intro', order: 0 },
      { id: 's2', title: 'Body', type: 'body', order: 1 },
    ];
    useScaffoldStore.getState().setSections(raw);

    useScaffoldStore.getState().updateSectionStatus('s1', 'in-progress');
    const sections = useScaffoldStore.getState().sections;
    expect(sections[0].status).toBe('in-progress');
    expect(sections[1].status).toBe('empty');

    useScaffoldStore.getState().updateSectionStatus('s1', 'complete');
    expect(useScaffoldStore.getState().sections[0].status).toBe('complete');
  });

  it('importFromMindMap sets topic and converts sections correctly', () => {
    const mindMapScaffold: Scaffold = {
      title: 'Essay on Dyslexia',
      sections: [
        { heading: 'What is Dyslexia?', hint: 'Define the condition', nodeIds: ['n1'], suggestedContent: 'Dyslexia is a learning difference.' },
        { heading: 'Strengths', hint: 'Talk about positives', nodeIds: ['n2'], suggestedContent: 'Big-picture thinking.' },
      ],
    };

    useScaffoldStore.getState().importFromMindMap(mindMapScaffold);
    const state = useScaffoldStore.getState();

    expect(state.topic).toBe('Essay on Dyslexia');
    expect(state.sections).toHaveLength(2);

    // heading -> title
    expect(state.sections[0].title).toBe('What is Dyslexia?');
    expect(state.sections[1].title).toBe('Strengths');

    // suggestedContent -> suggested_topic_sentence
    expect(state.sections[0].suggested_topic_sentence).toBe('Dyslexia is a learning difference.');
    expect(state.sections[1].suggested_topic_sentence).toBe('Big-picture thinking.');

    // hint -> hints as array
    expect(state.sections[0].hints).toEqual(['Define the condition']);
    expect(state.sections[1].hints).toEqual(['Talk about positives']);

    // All sections start with 'empty' status
    state.sections.forEach((s) => {
      expect(s.status).toBe('empty');
    });

    // type is set to 'body'
    state.sections.forEach((s) => {
      expect(s.type).toBe('body');
    });

    // order is set based on index
    expect(state.sections[0].order).toBe(0);
    expect(state.sections[1].order).toBe(1);
  });

  it('clearScaffold resets all state to defaults', () => {
    // First set some state
    useScaffoldStore.getState().setTopic('Some Topic');
    useScaffoldStore.getState().setSections([
      { id: 's1', title: 'Intro', type: 'intro', order: 0 },
    ]);
    useScaffoldStore.setState({ isLoading: true });

    // Now clear
    useScaffoldStore.getState().clearScaffold();
    const state = useScaffoldStore.getState();

    expect(state.topic).toBe('');
    expect(state.sections).toEqual([]);
    expect(state.isLoading).toBe(false);
  });
});
