export interface Document {
  id: string;
  title: string;
  content: string;
  mode: 'capture' | 'mindmap' | 'draft' | 'polish';
  createdAt: number;
  updatedAt: number;
  folderId: string | null;
}

export interface Folder {
  id: string;
  name: string;
  isExpanded: boolean;
  createdAt: number;
}
