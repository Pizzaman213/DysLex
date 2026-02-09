/**
 * Per-user scoped localStorage adapter for Zustand persist middleware.
 *
 * Namespaces all persisted store keys by the current user ID so that:
 *  - Multiple accounts on the same browser are isolated
 *  - Logout switches scope to '__anonymous__' (previous user's data stays safe)
 *  - Login rehydrates from the user's scoped keys
 *
 * @author Connor Secrist
 * @since  Feb 9, 2026
 */

import { createJSONStorage } from 'zustand/middleware';
import type { PersistStorage, StateStorage } from 'zustand/middleware';

// ---------------------------------------------------------------------------
// Module-level scope (no store imports — avoids circular dependencies)
// ---------------------------------------------------------------------------

let currentUserId: string = '__anonymous__';

export function setStorageUserId(id: string | null): void {
  currentUserId = id ?? '__anonymous__';
}

export function getStorageUserId(): string {
  return currentUserId;
}

// ---------------------------------------------------------------------------
// Scoped StateStorage: rewrites keys as `<name>::<userId>`
// ---------------------------------------------------------------------------

function createScopedStateStorage(): StateStorage {
  return {
    getItem(name: string): string | null {
      const scopedKey = `${name}::${currentUserId}`;
      return localStorage.getItem(scopedKey);
    },
    setItem(name: string, value: string): void {
      const scopedKey = `${name}::${currentUserId}`;
      localStorage.setItem(scopedKey, value);
    },
    removeItem(name: string): void {
      const scopedKey = `${name}::${currentUserId}`;
      localStorage.removeItem(scopedKey);
    },
  };
}

// ---------------------------------------------------------------------------
// Factory: returns a PersistStorage that reads/writes to scoped keys
// ---------------------------------------------------------------------------

export function createUserScopedStorage<S>(): PersistStorage<S> | undefined {
  return createJSONStorage<S>(createScopedStateStorage);
}

// ---------------------------------------------------------------------------
// Store registry: bulk rehydration on scope changes
// ---------------------------------------------------------------------------

type RehydrateFn = () => Promise<void> | void;

const scopedStores: RehydrateFn[] = [];

export function registerScopedStore(rehydrate: RehydrateFn): void {
  scopedStores.push(rehydrate);
}

export async function rehydrateAllStores(): Promise<void> {
  await Promise.all(scopedStores.map((fn) => fn()));
}

// ---------------------------------------------------------------------------
// One-time migration: global keys → scoped keys
// ---------------------------------------------------------------------------

const SCOPED_STORE_KEYS = [
  'dyslex-documents',
  'dyslex-settings',
  'dyslex-session',
  'dyslex-capture-session',
  'dyslex-mindmap',
  'dyslex-format',
];

export function migrateGlobalToScoped(userId: string): void {
  const flag = `dyslex-storage-migrated::${userId}`;
  if (localStorage.getItem(flag)) return; // already migrated

  for (const key of SCOPED_STORE_KEYS) {
    const globalData = localStorage.getItem(key);
    if (!globalData) continue;

    const scopedKey = `${key}::${userId}`;

    // Don't overwrite existing scoped data
    if (localStorage.getItem(scopedKey)) continue;

    localStorage.setItem(scopedKey, globalData);
    localStorage.removeItem(key);
  }

  localStorage.setItem(flag, '1');
}
