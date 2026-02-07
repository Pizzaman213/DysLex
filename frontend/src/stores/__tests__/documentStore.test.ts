import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useDocumentStore } from '../documentStore';

vi.mock('@/services/documentSync', () => ({
  syncCreateDocument: vi.fn(),
  syncDeleteDocument: vi.fn(),
  syncUpdateDocumentTitle: vi.fn(),
  syncUpdateDocumentContent: vi.fn(),
  syncCreateFolder: vi.fn(),
  syncDeleteFolder: vi.fn(),
  syncRenameFolder: vi.fn(),
  syncMoveDocument: vi.fn(),
  initializeFromServer: vi.fn(),
}));

const DEFAULT_DOC_ID = '00000000-0000-4000-8000-000000000001';

function makeDefaultState() {
  return {
    documents: [
      {
        id: DEFAULT_DOC_ID,
        title: 'Untitled Document',
        content: '',
        mode: 'draft' as const,
        createdAt: Date.now(),
        updatedAt: Date.now(),
        folderId: null,
      },
    ],
    activeDocumentId: DEFAULT_DOC_ID,
    folders: [],
    rootOrder: [DEFAULT_DOC_ID],
    folderOrders: {},
  };
}

describe('documentStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useDocumentStore.setState(makeDefaultState());
  });

  it('has correct default state with 1 document', () => {
    const state = useDocumentStore.getState();
    expect(state.documents).toHaveLength(1);
    expect(state.documents[0].id).toBe(DEFAULT_DOC_ID);
    expect(state.documents[0].title).toBe('Untitled Document');
    expect(state.activeDocumentId).toBe(DEFAULT_DOC_ID);
    expect(state.rootOrder).toContain(DEFAULT_DOC_ID);
    expect(state.folders).toEqual([]);
    expect(state.folderOrders).toEqual({});
  });

  it('createDocument adds new doc, sets active, appends to rootOrder', () => {
    const newId = useDocumentStore.getState().createDocument();
    const state = useDocumentStore.getState();

    expect(state.documents).toHaveLength(2);
    expect(state.activeDocumentId).toBe(newId);
    expect(state.rootOrder).toContain(newId);
    expect(state.rootOrder.indexOf(newId)).toBe(state.rootOrder.length - 1);
  });

  it('deleteDocument removes doc and keeps at least one doc', () => {
    const newId = useDocumentStore.getState().createDocument();
    expect(useDocumentStore.getState().documents).toHaveLength(2);

    useDocumentStore.getState().deleteDocument(newId);
    const state = useDocumentStore.getState();
    expect(state.documents).toHaveLength(1);
    expect(state.documents[0].id).toBe(DEFAULT_DOC_ID);
    expect(state.rootOrder).not.toContain(newId);
  });

  it('deleteDocument prevents deleting last doc (no-op)', () => {
    useDocumentStore.getState().deleteDocument(DEFAULT_DOC_ID);
    const state = useDocumentStore.getState();
    expect(state.documents).toHaveLength(1);
    expect(state.documents[0].id).toBe(DEFAULT_DOC_ID);
  });

  it('deleteDocument switches activeDocumentId if deleted doc was active', () => {
    const newId = useDocumentStore.getState().createDocument();
    // newId is now active
    expect(useDocumentStore.getState().activeDocumentId).toBe(newId);

    useDocumentStore.getState().deleteDocument(newId);
    const state = useDocumentStore.getState();
    expect(state.activeDocumentId).toBe(DEFAULT_DOC_ID);
  });

  it('switchDocument sets activeDocumentId', () => {
    const newId = useDocumentStore.getState().createDocument();
    useDocumentStore.getState().switchDocument(DEFAULT_DOC_ID);
    expect(useDocumentStore.getState().activeDocumentId).toBe(DEFAULT_DOC_ID);
    useDocumentStore.getState().switchDocument(newId);
    expect(useDocumentStore.getState().activeDocumentId).toBe(newId);
  });

  it('updateDocumentTitle updates title on correct doc', () => {
    useDocumentStore.getState().updateDocumentTitle(DEFAULT_DOC_ID, 'My Essay');
    const doc = useDocumentStore.getState().documents.find((d) => d.id === DEFAULT_DOC_ID);
    expect(doc?.title).toBe('My Essay');
  });

  it('updateDocumentContent updates content on correct doc', () => {
    useDocumentStore.getState().updateDocumentContent(DEFAULT_DOC_ID, 'Some content here');
    const doc = useDocumentStore.getState().documents.find((d) => d.id === DEFAULT_DOC_ID);
    expect(doc?.content).toBe('Some content here');
  });

  it('createFolder adds folder, appends to rootOrder, creates empty folderOrders entry', () => {
    const folderId = useDocumentStore.getState().createFolder('Test Folder');
    const state = useDocumentStore.getState();

    expect(state.folders).toHaveLength(1);
    expect(state.folders[0].name).toBe('Test Folder');
    expect(state.folders[0].id).toBe(folderId);
    expect(state.rootOrder).toContain(folderId);
    expect(state.folderOrders[folderId]).toEqual([]);
  });

  it('deleteFolder removes folder and moves docs to root', () => {
    const folderId = useDocumentStore.getState().createFolder('Folder');
    const docId = useDocumentStore.getState().createDocument();

    // Move doc into folder
    useDocumentStore.getState().moveDocumentToFolder(docId, folderId);
    expect(useDocumentStore.getState().folderOrders[folderId]).toContain(docId);

    // Delete folder
    useDocumentStore.getState().deleteFolder(folderId);
    const state = useDocumentStore.getState();

    expect(state.folders).toHaveLength(0);
    expect(state.rootOrder).not.toContain(folderId);
    // Doc should be moved back to root
    expect(state.rootOrder).toContain(docId);
    const doc = state.documents.find((d) => d.id === docId);
    expect(doc?.folderId).toBeNull();
    expect(state.folderOrders[folderId]).toBeUndefined();
  });

  it('renameFolder updates folder name', () => {
    const folderId = useDocumentStore.getState().createFolder('Old Name');
    useDocumentStore.getState().renameFolder(folderId, 'New Name');

    const folder = useDocumentStore.getState().folders.find((f) => f.id === folderId);
    expect(folder?.name).toBe('New Name');
  });

  it('toggleFolder flips isExpanded', () => {
    const folderId = useDocumentStore.getState().createFolder('Folder');
    expect(useDocumentStore.getState().folders[0].isExpanded).toBe(true);

    useDocumentStore.getState().toggleFolder(folderId);
    expect(useDocumentStore.getState().folders.find((f) => f.id === folderId)?.isExpanded).toBe(false);

    useDocumentStore.getState().toggleFolder(folderId);
    expect(useDocumentStore.getState().folders.find((f) => f.id === folderId)?.isExpanded).toBe(true);
  });

  it('moveDocumentToFolder moves from root to folder', () => {
    const folderId = useDocumentStore.getState().createFolder('Folder');
    useDocumentStore.getState().moveDocumentToFolder(DEFAULT_DOC_ID, folderId);

    const state = useDocumentStore.getState();
    expect(state.rootOrder).not.toContain(DEFAULT_DOC_ID);
    expect(state.folderOrders[folderId]).toContain(DEFAULT_DOC_ID);
    expect(state.documents.find((d) => d.id === DEFAULT_DOC_ID)?.folderId).toBe(folderId);
  });

  it('moveDocumentToFolder moves from folder to root', () => {
    const folderId = useDocumentStore.getState().createFolder('Folder');
    useDocumentStore.getState().moveDocumentToFolder(DEFAULT_DOC_ID, folderId);

    // Now move back to root
    useDocumentStore.getState().moveDocumentToFolder(DEFAULT_DOC_ID, null);
    const state = useDocumentStore.getState();

    expect(state.rootOrder).toContain(DEFAULT_DOC_ID);
    expect(state.folderOrders[folderId]).not.toContain(DEFAULT_DOC_ID);
    expect(state.documents.find((d) => d.id === DEFAULT_DOC_ID)?.folderId).toBeNull();
  });

  it('moveDocumentToFolder is no-op when same folder', () => {
    const folderId = useDocumentStore.getState().createFolder('Folder');
    useDocumentStore.getState().moveDocumentToFolder(DEFAULT_DOC_ID, folderId);

    const stateBefore = useDocumentStore.getState();
    useDocumentStore.getState().moveDocumentToFolder(DEFAULT_DOC_ID, folderId);
    const stateAfter = useDocumentStore.getState();

    // folderOrders for the folder should be unchanged
    expect(stateAfter.folderOrders[folderId]).toEqual(stateBefore.folderOrders[folderId]);
  });

  it('reorderRoot swaps positions of two items', () => {
    const docId2 = useDocumentStore.getState().createDocument();
    const rootBefore = useDocumentStore.getState().rootOrder;
    const idx0 = rootBefore.indexOf(DEFAULT_DOC_ID);
    const idx1 = rootBefore.indexOf(docId2);

    useDocumentStore.getState().reorderRoot(DEFAULT_DOC_ID, docId2);
    const rootAfter = useDocumentStore.getState().rootOrder;

    // The positions should have swapped
    expect(rootAfter.indexOf(DEFAULT_DOC_ID)).toBe(idx1);
    expect(rootAfter.indexOf(docId2)).toBe(idx0);
  });

  it('reorderRoot is no-op for missing IDs', () => {
    const rootBefore = [...useDocumentStore.getState().rootOrder];
    useDocumentStore.getState().reorderRoot('missing-id', DEFAULT_DOC_ID);
    expect(useDocumentStore.getState().rootOrder).toEqual(rootBefore);
  });

  it('reorderInFolder swaps positions within a folder', () => {
    const folderId = useDocumentStore.getState().createFolder('Folder');
    const docId2 = useDocumentStore.getState().createDocument();

    useDocumentStore.getState().moveDocumentToFolder(DEFAULT_DOC_ID, folderId);
    useDocumentStore.getState().moveDocumentToFolder(docId2, folderId);

    const orderBefore = useDocumentStore.getState().folderOrders[folderId];
    expect(orderBefore).toEqual([DEFAULT_DOC_ID, docId2]);

    useDocumentStore.getState().reorderInFolder(folderId, DEFAULT_DOC_ID, docId2);

    const orderAfter = useDocumentStore.getState().folderOrders[folderId];
    expect(orderAfter).toEqual([docId2, DEFAULT_DOC_ID]);
  });
});
