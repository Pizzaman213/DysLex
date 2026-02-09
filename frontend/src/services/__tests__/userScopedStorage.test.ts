import { describe, it, expect, beforeEach } from 'vitest';
import {
  setStorageUserId,
  getStorageUserId,
  createUserScopedStorage,
  registerScopedStore,
  rehydrateAllStores,
  migrateGlobalToScoped,
} from '../userScopedStorage';

// Reset module state between tests by clearing localStorage and resetting scope
beforeEach(() => {
  localStorage.clear();
  setStorageUserId(null); // reset to '__anonymous__'
});

describe('setStorageUserId / getStorageUserId', () => {
  it('defaults to __anonymous__', () => {
    expect(getStorageUserId()).toBe('__anonymous__');
  });

  it('sets and gets a user ID', () => {
    setStorageUserId('user-abc-123');
    expect(getStorageUserId()).toBe('user-abc-123');
  });

  it('resets to __anonymous__ when set to null', () => {
    setStorageUserId('user-abc-123');
    setStorageUserId(null);
    expect(getStorageUserId()).toBe('__anonymous__');
  });
});

describe('createUserScopedStorage', () => {
  it('returns a PersistStorage object', () => {
    const storage = createUserScopedStorage();
    expect(storage).toBeDefined();
    expect(storage!.getItem).toBeInstanceOf(Function);
    expect(storage!.setItem).toBeInstanceOf(Function);
    expect(storage!.removeItem).toBeInstanceOf(Function);
  });

  it('writes to scoped keys based on current userId', () => {
    setStorageUserId('user-1');
    const storage = createUserScopedStorage<{ count: number }>();

    storage!.setItem('my-store', { state: { count: 42 }, version: 1 });

    // Should be stored under scoped key
    const raw = localStorage.getItem('my-store::user-1');
    expect(raw).toBeTruthy();
    const parsed = JSON.parse(raw!);
    expect(parsed.state.count).toBe(42);

    // Global key should NOT exist
    expect(localStorage.getItem('my-store')).toBeNull();
  });

  it('reads from scoped keys based on current userId', async () => {
    localStorage.setItem(
      'my-store::user-2',
      JSON.stringify({ state: { name: 'Alice' }, version: 1 })
    );

    setStorageUserId('user-2');
    const storage = createUserScopedStorage<{ name: string }>();

    const result = await storage!.getItem('my-store');
    expect(result).toEqual({ state: { name: 'Alice' }, version: 1 });
  });

  it('isolates data between users', () => {
    const storage = createUserScopedStorage<{ value: string }>();

    setStorageUserId('user-A');
    storage!.setItem('data', { state: { value: 'A-data' }, version: 0 });

    setStorageUserId('user-B');
    storage!.setItem('data', { state: { value: 'B-data' }, version: 0 });

    // Check raw localStorage keys
    expect(JSON.parse(localStorage.getItem('data::user-A')!).state.value).toBe('A-data');
    expect(JSON.parse(localStorage.getItem('data::user-B')!).state.value).toBe('B-data');
  });

  it('returns null for missing scoped keys', async () => {
    setStorageUserId('user-X');
    const storage = createUserScopedStorage<{ data: string }>();
    const result = await storage!.getItem('nonexistent');
    expect(result).toBeNull();
  });

  it('removes scoped key only', () => {
    setStorageUserId('user-1');
    const storage = createUserScopedStorage<{ v: number }>();

    storage!.setItem('test', { state: { v: 1 }, version: 0 });
    expect(localStorage.getItem('test::user-1')).toBeTruthy();

    storage!.removeItem('test');
    expect(localStorage.getItem('test::user-1')).toBeNull();
  });
});

describe('registerScopedStore / rehydrateAllStores', () => {
  it('calls all registered rehydrate functions', async () => {
    let callCount = 0;
    // Note: registerScopedStore appends to a module-level array, so these
    // registrations persist across tests. We test that the newly registered
    // ones are called.
    const before = callCount;
    registerScopedStore(() => { callCount++; });
    registerScopedStore(() => { callCount++; });

    await rehydrateAllStores();
    expect(callCount - before).toBe(2);
  });
});

describe('migrateGlobalToScoped', () => {
  it('copies global keys to scoped keys', () => {
    localStorage.setItem('dyslex-documents', '{"state":{"docs":[]}}');
    localStorage.setItem('dyslex-settings', '{"state":{"theme":"cream"}}');

    migrateGlobalToScoped('user-123');

    // Scoped keys should have the data
    expect(localStorage.getItem('dyslex-documents::user-123')).toBe('{"state":{"docs":[]}}');
    expect(localStorage.getItem('dyslex-settings::user-123')).toBe('{"state":{"theme":"cream"}}');

    // Global keys should be removed
    expect(localStorage.getItem('dyslex-documents')).toBeNull();
    expect(localStorage.getItem('dyslex-settings')).toBeNull();
  });

  it('sets migration flag', () => {
    migrateGlobalToScoped('user-456');
    expect(localStorage.getItem('dyslex-storage-migrated::user-456')).toBe('1');
  });

  it('is idempotent — skips if already migrated', () => {
    localStorage.setItem('dyslex-documents', '{"state":{"docs":["original"]}}');
    migrateGlobalToScoped('user-789');

    // Put new global data (simulating another write after migration)
    localStorage.setItem('dyslex-documents', '{"state":{"docs":["new"]}}');

    // Second migration should be a no-op
    migrateGlobalToScoped('user-789');

    // Scoped data should still be the original
    const scoped = JSON.parse(localStorage.getItem('dyslex-documents::user-789')!);
    expect(scoped.state.docs[0]).toBe('original');
  });

  it('does not overwrite existing scoped data', () => {
    // Pre-existing scoped data
    localStorage.setItem('dyslex-documents::user-AAA', '{"state":{"docs":["existing"]}}');
    // Global data
    localStorage.setItem('dyslex-documents', '{"state":{"docs":["global"]}}');

    migrateGlobalToScoped('user-AAA');

    // Scoped data should NOT be overwritten
    const scoped = JSON.parse(localStorage.getItem('dyslex-documents::user-AAA')!);
    expect(scoped.state.docs[0]).toBe('existing');
  });

  it('migrates all 6 store keys', () => {
    const keys = [
      'dyslex-documents',
      'dyslex-settings',
      'dyslex-session',
      'dyslex-capture-session',
      'dyslex-mindmap',
      'dyslex-format',
    ];

    for (const key of keys) {
      localStorage.setItem(key, `{"state":"${key}"}`);
    }

    migrateGlobalToScoped('user-all');

    for (const key of keys) {
      expect(localStorage.getItem(`${key}::user-all`)).toBe(`{"state":"${key}"}`);
      expect(localStorage.getItem(key)).toBeNull();
    }
  });

  it('handles missing global keys gracefully', () => {
    // No global keys set — migration should not throw
    expect(() => migrateGlobalToScoped('user-empty')).not.toThrow();
    expect(localStorage.getItem('dyslex-storage-migrated::user-empty')).toBe('1');
  });
});
