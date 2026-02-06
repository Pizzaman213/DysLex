import { Editor } from '../Editor/Editor';

interface DraftModeProps {
  initialContent?: string;
}

export function DraftMode({ initialContent }: DraftModeProps) {
  return (
    <div className="draft-mode">
      <div className="draft-scaffold">
        <div className="scaffold-section">
          <h3>Introduction</h3>
          <p className="scaffold-hint">What are you writing about?</p>
        </div>
        <div className="scaffold-section">
          <h3>Main Points</h3>
          <p className="scaffold-hint">What are your key ideas?</p>
        </div>
        <div className="scaffold-section">
          <h3>Conclusion</h3>
          <p className="scaffold-hint">How will you wrap up?</p>
        </div>
      </div>
      <Editor mode="draft" />
    </div>
  );
}
