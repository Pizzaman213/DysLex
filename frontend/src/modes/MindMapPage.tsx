import { MindMapMode } from '@/components/WritingModes/MindMapMode';
import { Scaffold } from '@/components/WritingModes/MindMap/types';
import { useScaffoldStore } from '@/stores/scaffoldStore';
import { useMindMapStore } from '@/stores/mindMapStore';
import { useViewTransitionNavigate } from '@/hooks/useViewTransitionNavigate';
import { api } from '@/services/api';

export function MindMapPage() {
  const navigate = useViewTransitionNavigate();
  const { setTopic, setSections, importFromMindMap } = useScaffoldStore();
  const setMindMapScaffold = useMindMapStore((s) => s.setScaffold);

  const handleNavigateToDraft = async (scaffold: Scaffold) => {
    // Collect the ideas from the mind map scaffold to feed into Nemotron
    const existingIdeas = scaffold.sections
      .map((s) => `${s.heading}: ${s.suggestedContent ?? s.hint}`)
      .filter(Boolean);

    const topic = scaffold.title || 'Untitled';

    // Navigate immediately so the user sees Draft mode loading
    setTopic(topic);
    setMindMapScaffold(null);
    navigate('/draft');

    // Call the scaffold API with the mind map ideas so Nemotron
    // generates a proper draft scaffold from them
    try {
      const response = await api.generateScaffold({
        topic,
        existingIdeas,
      });
      setSections(response.sections);
    } catch {
      // Fallback: use the basic mind map conversion if the API fails
      importFromMindMap(scaffold);
    }
  };

  return <MindMapMode onNavigateToDraft={handleNavigateToDraft} />;
}
