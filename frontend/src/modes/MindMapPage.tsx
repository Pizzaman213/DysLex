import { MindMapMode } from '@/components/WritingModes/MindMapMode';
import { Scaffold } from '@/components/WritingModes/MindMap/types';
import { useScaffoldStore } from '@/stores/scaffoldStore';
import { useMindMapStore } from '@/stores/mindMapStore';
import { useViewTransitionNavigate } from '@/hooks/useViewTransitionNavigate';

export function MindMapPage() {
  const navigate = useViewTransitionNavigate();
  const importFromMindMap = useScaffoldStore((s) => s.importFromMindMap);
  const setMindMapScaffold = useMindMapStore((s) => s.setScaffold);

  const handleNavigateToDraft = (scaffold: Scaffold) => {
    importFromMindMap(scaffold);
    setMindMapScaffold(null);
    navigate('/draft');
  };

  return <MindMapMode onNavigateToDraft={handleNavigateToDraft} />;
}
