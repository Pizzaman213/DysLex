import { CaptureMode } from '@/components/WritingModes/CaptureMode';
import { useViewTransitionNavigate } from '@/hooks/useViewTransitionNavigate';

export function CapturePage() {
  const navigate = useViewTransitionNavigate();

  return <CaptureMode onNavigateToMindMap={() => navigate('/mindmap')} />;
}
