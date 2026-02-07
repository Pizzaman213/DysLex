import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Document, Folder } from '@/types/document';

interface DocumentState {
  documents: Document[];
  activeDocumentId: string | null;
  folders: Folder[];
  rootOrder: string[];
  folderOrders: Record<string, string[]>;

  createDocument: () => string;
  deleteDocument: (id: string) => void;
  switchDocument: (id: string) => void;
  updateDocumentTitle: (id: string, title: string) => void;
  updateDocumentContent: (id: string, content: string) => void;

  createFolder: (name?: string) => string;
  deleteFolder: (id: string) => void;
  renameFolder: (id: string, name: string) => void;
  toggleFolder: (id: string) => void;
  moveDocumentToFolder: (docId: string, folderId: string | null) => void;
  reorderRoot: (activeId: string, overId: string) => void;
  reorderInFolder: (folderId: string, activeId: string, overId: string) => void;
}

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

function arrayMove<T>(arr: T[], from: number, to: number): T[] {
  const result = [...arr];
  const [item] = result.splice(from, 1);
  result.splice(to, 0, item);
  return result;
}

export const useDocumentStore = create<DocumentState>()(
  persist(
    (set, get) => ({
      documents: [
        {
          id: 'default',
          title: 'Untitled Document',
          content: '',
          mode: 'draft' as const,
          createdAt: Date.now(),
          updatedAt: Date.now(),
          folderId: null,
        },
      ],
      activeDocumentId: 'default',
      folders: [],
      rootOrder: ['default'],
      folderOrders: {},

      createDocument: () => {
        const id = generateId();
        const doc: Document = {
          id,
          title: 'Untitled Document',
          content: '',
          mode: 'draft',
          createdAt: Date.now(),
          updatedAt: Date.now(),
          folderId: null,
        };
        set((state) => ({
          documents: [...state.documents, doc],
          activeDocumentId: id,
          rootOrder: [...state.rootOrder, id],
        }));
        return id;
      },

      deleteDocument: (id: string) => {
        const { documents, activeDocumentId, folderOrders } = get();
        if (documents.length <= 1) return;
        const doc = documents.find((d) => d.id === id);
        const filtered = documents.filter((d) => d.id !== id);

        const newFolderOrders = { ...folderOrders };
        if (doc?.folderId && newFolderOrders[doc.folderId]) {
          newFolderOrders[doc.folderId] = newFolderOrders[doc.folderId].filter(
            (did) => did !== id
          );
        }

        set((state) => ({
          documents: filtered,
          activeDocumentId:
            activeDocumentId === id ? filtered[0]?.id ?? null : activeDocumentId,
          rootOrder: state.rootOrder.filter((rid) => rid !== id),
          folderOrders: newFolderOrders,
        }));
      },

      switchDocument: (id: string) => {
        set({ activeDocumentId: id });
      },

      updateDocumentTitle: (id: string, title: string) => {
        set((state) => ({
          documents: state.documents.map((d) =>
            d.id === id ? { ...d, title, updatedAt: Date.now() } : d
          ),
        }));
      },

      updateDocumentContent: (id: string, content: string) => {
        set((state) => ({
          documents: state.documents.map((d) =>
            d.id === id ? { ...d, content, updatedAt: Date.now() } : d
          ),
        }));
      },

      createFolder: (name?: string) => {
        const id = 'folder-' + generateId();
        const folder: Folder = {
          id,
          name: name ?? 'New Folder',
          isExpanded: true,
          createdAt: Date.now(),
        };
        set((state) => ({
          folders: [...state.folders, folder],
          rootOrder: [...state.rootOrder, id],
          folderOrders: { ...state.folderOrders, [id]: [] },
        }));
        return id;
      },

      deleteFolder: (id: string) => {
        const { folderOrders, documents } = get();
        const docsInFolder = folderOrders[id] ?? [];

        const newFolderOrders = { ...folderOrders };
        delete newFolderOrders[id];

        set((state) => ({
          folders: state.folders.filter((f) => f.id !== id),
          rootOrder: [
            ...state.rootOrder.filter((rid) => rid !== id),
            ...docsInFolder,
          ],
          folderOrders: newFolderOrders,
          documents: documents.map((d) =>
            docsInFolder.includes(d.id) ? { ...d, folderId: null } : d
          ),
        }));
      },

      renameFolder: (id: string, name: string) => {
        set((state) => ({
          folders: state.folders.map((f) =>
            f.id === id ? { ...f, name } : f
          ),
        }));
      },

      toggleFolder: (id: string) => {
        set((state) => ({
          folders: state.folders.map((f) =>
            f.id === id ? { ...f, isExpanded: !f.isExpanded } : f
          ),
        }));
      },

      moveDocumentToFolder: (docId: string, folderId: string | null) => {
        const { documents, folderOrders, rootOrder } = get();
        const doc = documents.find((d) => d.id === docId);
        if (!doc) return;

        const oldFolderId = doc.folderId;
        if (oldFolderId === folderId) return;

        const newFolderOrders = { ...folderOrders };

        // Remove from old location
        if (oldFolderId && newFolderOrders[oldFolderId]) {
          newFolderOrders[oldFolderId] = newFolderOrders[oldFolderId].filter(
            (did) => did !== docId
          );
        }

        let newRootOrder = rootOrder.filter((rid) => rid !== docId);

        // Add to new location
        if (folderId) {
          if (!newFolderOrders[folderId]) {
            newFolderOrders[folderId] = [];
          }
          newFolderOrders[folderId] = [...newFolderOrders[folderId], docId];
        } else {
          newRootOrder = [...newRootOrder, docId];
        }

        set({
          documents: documents.map((d) =>
            d.id === docId ? { ...d, folderId } : d
          ),
          folderOrders: newFolderOrders,
          rootOrder: newRootOrder,
        });
      },

      reorderRoot: (activeId: string, overId: string) => {
        const { rootOrder } = get();
        const oldIndex = rootOrder.indexOf(activeId);
        const newIndex = rootOrder.indexOf(overId);
        if (oldIndex === -1 || newIndex === -1) return;
        set({ rootOrder: arrayMove(rootOrder, oldIndex, newIndex) });
      },

      reorderInFolder: (folderId: string, activeId: string, overId: string) => {
        const { folderOrders } = get();
        const order = folderOrders[folderId];
        if (!order) return;
        const oldIndex = order.indexOf(activeId);
        const newIndex = order.indexOf(overId);
        if (oldIndex === -1 || newIndex === -1) return;
        set({
          folderOrders: {
            ...folderOrders,
            [folderId]: arrayMove(order, oldIndex, newIndex),
          },
        });
      },
    }),
    {
      name: 'dyslex-documents',
      version: 2,
      migrate: (persisted: unknown, version: number) => {
        const state = persisted as Record<string, unknown>;

        if (version < 2) {
          // Migration from v1: add folder support
          const docs = (state.documents ?? []) as Document[];
          const migratedDocs = docs.map((d) => ({
            ...d,
            folderId: d.folderId ?? null,
          }));
          const rootOrder = migratedDocs.map((d) => d.id);

          return {
            ...state,
            documents: migratedDocs,
            folders: [],
            rootOrder,
            folderOrders: {},
          };
        }

        return state;
      },
    }
  )
);
