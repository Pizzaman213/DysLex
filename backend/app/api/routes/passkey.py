"""WebAuthn passkey endpoints — register and authenticate with biometrics."""

import json
import logging
import uuid

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import bytes_to_base64url, base64url_to_bytes
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.api.dependencies import DbSession, create_access_token
from app.config import settings
from app.db.models import PasskeyCredential, User as UserORM
from app.db.repositories.passkey_repo import (
    create_passkey_credential,
    get_credential_by_credential_id,
    get_credentials_by_user_id,
    update_credential_sign_count,
)
from app.db.repositories.user_repo import create_user, get_user_by_email
from app.middleware.rate_limiter import limiter
from app.models.envelope import ApiError, error_response, success_response
from app.services.redis_client import get_redis

logger = logging.getLogger(__name__)

router = APIRouter()

CHALLENGE_TTL = 300  # 5 minutes


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class RegisterOptionsRequest(BaseModel):
    email: EmailStr
    name: str


class RegisterCompleteRequest(BaseModel):
    email: EmailStr
    credential: dict


class LoginOptionsRequest(BaseModel):
    email: str | None = None


class LoginCompleteRequest(BaseModel):
    session_id: str
    credential: dict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _store_challenge(session_id: str, data: dict) -> None:
    """Store a WebAuthn challenge in Redis with TTL."""
    redis = await get_redis()
    await redis.setex(
        f"webauthn:challenge:{session_id}",
        CHALLENGE_TTL,
        json.dumps(data),
    )


async def _get_challenge(session_id: str) -> dict | None:
    """Retrieve and delete a WebAuthn challenge from Redis."""
    redis = await get_redis()
    key = f"webauthn:challenge:{session_id}"
    raw = await redis.get(key)
    if raw is None:
        return None
    await redis.delete(key)
    return json.loads(raw)


def _serialize_options(options: object) -> dict:
    """Convert a py_webauthn options object to a JSON-safe dict.

    py_webauthn >=2.0 returns dataclass objects. We use the built-in
    json helper to serialize, then parse back to a dict so FastAPI can
    encode it in the response envelope.
    """
    from webauthn.helpers import options_to_json
    return json.loads(options_to_json(options))


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


@router.post("/register/options")
@limiter.limit("10/minute")
async def register_options(request: Request, body: RegisterOptionsRequest, db: DbSession) -> dict:
    """Generate WebAuthn registration options for a new user."""
    existing = await get_user_by_email(db, body.email)
    if existing:
        return error_response(
            [ApiError(code="EMAIL_EXISTS", message="An account with this email already exists — please sign in instead")],
            status_code=409,
        )

    user_id = str(uuid.uuid4()).encode()
    exclude: list[PublicKeyCredentialDescriptor] = []

    options = generate_registration_options(
        rp_id=settings.webauthn_rp_id,
        rp_name=settings.webauthn_rp_name,
        user_id=user_id,
        user_name=body.email,
        user_display_name=body.name,
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=exclude,
    )

    session_id = str(uuid.uuid4())
    await _store_challenge(session_id, {
        "challenge": bytes_to_base64url(options.challenge),
        "email": body.email,
        "name": body.name,
        "user_id": user_id.decode(),
    })

    serialized = _serialize_options(options)
    serialized["sessionId"] = session_id
    return success_response(serialized)


@router.post("/register/complete", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register_complete(request: Request, body: RegisterCompleteRequest, db: DbSession) -> dict:
    """Verify the attestation response and create the user + credential."""
    session_id = body.credential.get("sessionId")
    if not session_id:
        return error_response(
            [ApiError(code="MISSING_SESSION", message="Missing session ID")],
            status_code=400,
        )

    challenge_data = await _get_challenge(session_id)
    if not challenge_data:
        return error_response(
            [ApiError(code="CHALLENGE_EXPIRED", message="Registration session expired — please try again")],
            status_code=400,
        )

    expected_challenge = base64url_to_bytes(challenge_data["challenge"])

    try:
        verification = verify_registration_response(
            credential=body.credential,
            expected_challenge=expected_challenge,
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_origins,
        )
    except Exception as exc:
        logger.warning("Passkey registration verification failed: %s", exc)
        return error_response(
            [ApiError(code="VERIFICATION_FAILED", message="Passkey verification failed — please try again")],
            status_code=400,
        )

    # Create user (reject if email was taken between options and complete)
    user = await get_user_by_email(db, challenge_data["email"])
    if user:
        return error_response(
            [ApiError(code="EMAIL_EXISTS", message="An account with this email already exists — please sign in instead")],
            status_code=409,
        )

    user = UserORM(
        id=challenge_data["user_id"],
        email=challenge_data["email"],
        name=challenge_data["name"],
        password_hash=None,
    )
    user = await create_user(db, user)

    # Store credential
    transports = body.credential.get("response", {}).get("transports")
    cred = PasskeyCredential(
        id=str(uuid.uuid4()),
        user_id=user.id,
        credential_id=verification.credential_id,
        public_key=verification.credential_public_key,
        sign_count=verification.sign_count,
        transports=json.dumps(transports) if transports else None,
    )
    await create_passkey_credential(db, cred)

    token = create_access_token(user.id, user.email)
    return success_response({
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "user_name": user.name,
        "user_email": user.email,
    })


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


@router.post("/login/options")
@limiter.limit("10/minute")
async def login_options(request: Request, body: LoginOptionsRequest, db: DbSession) -> dict:
    """Generate WebAuthn authentication options.

    If email is provided, returns allowCredentials for that user.
    If email is omitted, returns empty allowCredentials for discoverable
    credential (passkey) flow.
    """
    allow_credentials: list[PublicKeyCredentialDescriptor] = []

    if body.email:
        user = await get_user_by_email(db, body.email)
        if user:
            creds = await get_credentials_by_user_id(db, user.id)
            allow_credentials = [
                PublicKeyCredentialDescriptor(
                    id=c.credential_id,
                    transports=json.loads(c.transports) if c.transports else None,
                )
                for c in creds
            ]

    options = generate_authentication_options(
        rp_id=settings.webauthn_rp_id,
        allow_credentials=allow_credentials or None,
        user_verification=UserVerificationRequirement.REQUIRED,
    )

    session_id = str(uuid.uuid4())
    await _store_challenge(session_id, {
        "challenge": bytes_to_base64url(options.challenge),
        "email": body.email,
    })

    serialized = _serialize_options(options)
    serialized["sessionId"] = session_id
    return success_response(serialized)


@router.post("/login/complete")
@limiter.limit("10/minute")
async def login_complete(request: Request, body: LoginCompleteRequest, db: DbSession) -> dict:
    """Verify the authentication assertion and return a JWT."""
    challenge_data = await _get_challenge(body.session_id)
    if not challenge_data:
        return error_response(
            [ApiError(code="CHALLENGE_EXPIRED", message="Login session expired — please try again")],
            status_code=400,
        )

    expected_challenge = base64url_to_bytes(challenge_data["challenge"])

    # Look up the credential
    raw_id = body.credential.get("rawId") or body.credential.get("id", "")
    try:
        credential_id_bytes = base64url_to_bytes(raw_id)
    except Exception:
        return error_response(
            [ApiError(code="INVALID_CREDENTIAL", message="Invalid credential format")],
            status_code=400,
        )

    stored_cred = await get_credential_by_credential_id(db, credential_id_bytes)
    if not stored_cred:
        return error_response(
            [ApiError(code="CREDENTIAL_NOT_FOUND", message="Passkey not recognized — have you registered?")],
            status_code=400,
        )

    try:
        verification = verify_authentication_response(
            credential=body.credential,
            expected_challenge=expected_challenge,
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_origins,
            credential_public_key=stored_cred.public_key,
            credential_current_sign_count=stored_cred.sign_count,
        )
    except Exception as exc:
        logger.warning("Passkey login verification failed: %s", exc)
        return error_response(
            [ApiError(code="VERIFICATION_FAILED", message="Authentication failed — please try again")],
            status_code=400,
        )

    # Update sign count
    await update_credential_sign_count(db, credential_id_bytes, verification.new_sign_count)

    # Load the user
    from app.db.repositories.user_repo import get_user_by_id
    user = await get_user_by_id(db, stored_cred.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    token = create_access_token(user.id, user.email)
    return success_response({
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "user_name": user.name,
        "user_email": user.email,
    })
