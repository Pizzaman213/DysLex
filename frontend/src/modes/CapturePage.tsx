import { useNavigate } from 'react-router-dom';
import { CaptureMode } from '@/components/WritingModes/CaptureMode';

export function CapturePage() {
  const navigate = useNavigate();

  return <CaptureMode onNavigateToMindMap={() => navigate('/mindmap')} />;
}
