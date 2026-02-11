# Passkey Authentication (WebAuthn)

## Purpose

Passwordless biometric authentication using WebAuthn/FIDO2. Users can register and login with fingerprint, Face ID, or security keys — no passwords to type (especially helpful for dyslexic users).

## Endpoints

`backend/app/api/routes/passkey.py`:

| Endpoint | Purpose |
|----------|---------|
| `POST /passkey/register/options` | Generate WebAuthn registration challenge |
| `POST /passkey/register/complete` | Verify attestation, create user + passkey |
| `POST /passkey/login/options` | Generate authentication challenge |
| `POST /passkey/login/complete` | Verify assertion, return JWT |

### Registration Flow

1. Frontend calls `/register/options` with user's name
2. Backend generates challenge using `py_webauthn`, stores in Redis (5-min TTL)
3. Frontend calls `navigator.credentials.create()` with options
4. Frontend sends attestation to `/register/complete`
5. Backend verifies attestation, creates `User` + `PasskeyCredential` records
6. Returns JWT token

### Login Flow

1. Frontend calls `/login/options`
2. Backend generates challenge, stores in Redis
3. Frontend calls `navigator.credentials.get()`
4. Frontend sends assertion to `/login/complete`
5. Backend verifies assertion against stored credential
6. Returns JWT token

## Implementation Details

- Uses `py_webauthn` library for challenge generation and verification
- Challenges stored in Redis with 5-minute TTL
- Supports discoverable credentials (passkey auto-fill)
- Rate-limited: 10 requests/minute
- `PasskeyCredential` model stores credential_id, public_key, sign_count

### Configuration

`backend/app/config.py`:
```python
webauthn_rp_id: str = "localhost"
webauthn_rp_name: str = "DysLex AI"
webauthn_origin: str = "http://localhost:3000"
```

## Traditional Auth (Fallback)

`backend/app/api/routes/auth.py` also provides password-based auth:
- `POST /auth/register` — Password validation (8+ chars, letter, digit)
- `POST /auth/login` — bcrypt verification, returns JWT
- `POST /auth/refresh` — Token refresh

## Key Files

| File | Role |
|------|------|
| `backend/app/api/routes/passkey.py` | WebAuthn endpoints |
| `backend/app/api/routes/auth.py` | Password-based auth |
| `backend/app/db/models.py` | `PasskeyCredential` model |
| `backend/app/config.py` | WebAuthn RP configuration |
| `backend/app/services/redis_client.py` | Challenge storage |

## Integration Points

- [Redis](redis-caching-layer.md): Challenge storage with TTL
- [Database](database-schema.md): `passkey_credentials` table (migration 006)
- [User-Scoped Storage](../frontend/user-scoped-storage.md): Login triggers scope switch

## Status

- [x] WebAuthn registration + login flows
- [x] py_webauthn integration
- [x] Redis challenge storage with TTL
- [x] Traditional password auth fallback
- [x] Rate limiting
- [x] Alembic migration (006)
