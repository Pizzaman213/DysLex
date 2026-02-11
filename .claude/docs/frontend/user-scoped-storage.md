# User-Scoped Storage

## Purpose

Per-user localStorage namespace adapter for Zustand persistence. Ensures multi-account isolation — switching users loads different data without conflicts.

## Implementation

`frontend/src/services/userScopedStorage.ts`:

### Key Exports

| Export | Purpose |
|--------|---------|
| `createUserScopedStorage<S>()` | Returns a `PersistStorage` for Zustand `persist()` |
| `setStorageUserId(id)` | Set current user scope (called on login) |
| `getStorageUserId()` | Get current user ID |
| `registerScopedStore(rehydrate)` | Register store for bulk rehydration |
| `rehydrateAllStores()` | Rehydrate all registered stores (called on login) |
| `migrateGlobalToScoped(userId)` | One-time migration from legacy global keys |

### How It Works

Keys are rewritten as `${storeName}::${userId}` in localStorage. When a user logs in:

1. `setStorageUserId(userId)` sets the scope
2. `rehydrateAllStores()` triggers all registered stores to load their user-specific data
3. If global (unscoped) data exists, `migrateGlobalToScoped()` migrates it once

### Consumers

- `captureStore.ts` — Per-user capture sessions
- `mindMapStore.ts` — Per-user mind maps

Both use `createUserScopedStorage()` in their Zustand `persist()` config.

## Key Files

| File | Role |
|------|------|
| `frontend/src/services/userScopedStorage.ts` | Storage adapter |
| `frontend/src/stores/captureStore.ts` | Consumer (persisted) |
| `frontend/src/stores/mindMapStore.ts` | Consumer (persisted) |

## Status

- [x] User-scoped localStorage adapter
- [x] Bulk rehydration on login
- [x] Legacy global-to-scoped migration
- [x] Integrated with captureStore and mindMapStore
