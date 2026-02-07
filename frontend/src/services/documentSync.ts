/**
 * Document sync service — bridges the Zustand document store with the backend API.
 *
 * All sync calls are fire-and-forget: they run asynchronously but never block
 * the UI. If the backend is unreachable the app degrades gracefully to
 * localStorage-only mode.
 */

import { api } from './api';
import type { Document, Folder } from '@/types/document';

let syncEnabled = false;

// ---------------------------------------------------------------------------
// Content debounce (avoids flooding on every keystroke)
// ---------------------------------------------------------------------------

const CONTENT_DEBOUNCE_MS = 2000;
const contentTimers = new Map<string, ReturnType<typeof setTimeout>>();

function debouncedContentSync(docId: string, content: string): void {
  const existing = contentTimers.get(docId);
  if (existing) clearTimeout(existing);

  contentTimers.set(
    docId,
    setTimeout(() => {
      contentTimers.delete(docId);
      syncUpdateDocument(docId, { content });
    }, CONTENT_DEBOUNCE_MS),
  );
}

// ---------------------------------------------------------------------------
// Fire-and-forget wrappers
// ---------------------------------------------------------------------------

function safeFire(fn: () => Promise<unknown>): void {
  if (!syncEnabled) return;
  fn().catch((err) => {
    console.warn('[documentSync] sync failed (non-blocking):', err);
  });
}

// ---------------------------------------------------------------------------
// Public sync helpers — called by the document store after mutations
// ---------------------------------------------------------------------------

export function syncCreateDocument(doc: Document): void {
  safeFire(() =>
    api.createDocument({
      id: doc.id,
      title: doc.title,
      content: doc.content,
      mode: doc.mode,
      folder_id: doc.folderId,
      sort_order: 0,
    }),
  );
}

export function syncDeleteDocument(docId: string): void {
  safeFire(() => api.deleteDocument(docId));
}

export function syncUpdateDocumentTitle(docId: string, title: string): void {
  safeFire(() => api.updateDocument(docId, { title }));
}

export function syncUpdateDocumentContent(docId: string, content: string): void {
  if (!syncEnabled) return;
  debouncedContentSync(docId, content);
}

export function syncMoveDocument(docId: string, folderId: string | null): void {
  safeFire(() => api.updateDocument(docId, { folder_id: folderId }));
}

export function syncCreateFolder(folder: Folder): void {
  safeFire(() =>
    api.createFolder({
      id: folder.id,
      name: folder.name,
      sort_order: 0,
    }),
  );
}

export function syncDeleteFolder(folderId: string): void {
  safeFire(() => api.deleteFolder(folderId));
}

export function syncRenameFolder(folderId: string, name: string): void {
  safeFire(() => api.updateFolder(folderId, { name }));
}

// ---------------------------------------------------------------------------
// Initialisation — called once on app mount from AppLayout
// ---------------------------------------------------------------------------

export async function initializeFromServer(
  getState: () => {
    documents: Document[];
    folders: Folder[];
  },
  setState: (patch: {
    documents?: Document[];
    folders?: Folder[];
    rootOrder?: string[];
    folderOrders?: Record<string, string[]>;
    activeDocumentId?: string;
  }) => void,
): Promise<void> {
  try {
    const response = await api.listDocuments();
    const serverDocs = response.data.documents;
    const serverFolders = response.data.folders;

    if (serverDocs.length > 0 || serverFolders.length > 0) {
      // Server has data — hydrate local state from server
      const documents: Document[] = serverDocs.map((d) => ({
        id: d.id,
        title: d.title,
        content: d.content,
        mode: d.mode as Document['mode'],
        createdAt: d.created_at ? new Date(d.created_at).getTime() : Date.now(),
        updatedAt: d.updated_at ? new Date(d.updated_at).getTime() : Date.now(),
        folderId: d.folder_id,
      }));

      const folders: Folder[] = serverFolders.map((f) => ({
        id: f.id,
        name: f.name,
        isExpanded: true,
        createdAt: f.created_at ? new Date(f.created_at).getTime() : Date.now(),
      }));

      // Rebuild ordering arrays
      const folderIds = new Set(folders.map((f) => f.id));
      const folderOrders: Record<string, string[]> = {};
      for (const f of folders) {
        folderOrders[f.id] = [];
      }
      const rootOrder: string[] = [];

      for (const f of folders) {
        rootOrder.push(f.id);
      }
      for (const d of documents) {
        if (d.folderId && folderIds.has(d.folderId)) {
          folderOrders[d.folderId].push(d.id);
        } else {
          rootOrder.push(d.id);
        }
      }

      setState({
        documents,
        folders,
        rootOrder,
        folderOrders,
        activeDocumentId: documents[0]?.id ?? null,
      });
    } else {
      // Server is empty — push local state up
      const { documents, folders } = getState();
      await pushLocalToServer(documents, folders);
    }

    syncEnabled = true;
    console.log('[documentSync] sync initialised');
  } catch (err) {
    // Backend unreachable — stay in local-only mode
    syncEnabled = false;
    console.warn('[documentSync] backend unreachable, running in local-only mode:', err);
  }
}

// ---------------------------------------------------------------------------
// Push full local state to server (used when server is empty)
// ---------------------------------------------------------------------------

async function pushLocalToServer(documents: Document[], folders: Folder[]): Promise<void> {
  try {
    await api.syncDocuments({
      documents: documents.map((d, i) => ({
        id: d.id,
        title: d.title,
        content: d.content,
        mode: d.mode,
        folder_id: d.folderId,
        sort_order: i,
      })),
      folders: folders.map((f, i) => ({
        id: f.id,
        name: f.name,
        sort_order: i,
      })),
    });
  } catch (err) {
    console.warn('[documentSync] failed to push local state to server:', err);
  }
}
