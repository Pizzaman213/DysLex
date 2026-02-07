import { useNavigate } from 'react-router-dom';
import { MindMapMode } from '@/components/WritingModes/MindMapMode';
import { Scaffold } from '@/components/WritingModes/MindMap/types';

export function MindMapPage() {
  const navigate = useNavigate();

  const handleNavigateToDraft = (_scaffold: Scaffold) => {
    navigate('/draft');
  };

  return <MindMapMode onNavigateToDraft={handleNavigateToDraft} />;
}
