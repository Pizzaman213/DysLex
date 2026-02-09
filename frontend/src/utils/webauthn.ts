/**
 * WebAuthn browser helpers — base64url conversion and credential serialization.
 */

/** Convert a base64url string to an ArrayBuffer. */
export function base64urlToBuffer(base64url: string): ArrayBuffer {
  const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
  const pad = base64.length % 4;
  const padded = pad ? base64 + '='.repeat(4 - pad) : base64;
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

/** Convert an ArrayBuffer to a base64url string. */
export function bufferToBase64url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

/** Check if the browser supports WebAuthn. */
export function isWebAuthnSupported(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof window.PublicKeyCredential !== 'undefined' &&
    typeof navigator.credentials !== 'undefined'
  );
}

/**
 * Convert server registration options into the format
 * `navigator.credentials.create()` expects.
 */
export function prepareRegistrationOptions(
  serverOptions: Record<string, unknown>,
): PublicKeyCredentialCreationOptions {
  const opts = serverOptions as Record<string, any>;

  return {
    rp: opts.rp,
    user: {
      ...opts.user,
      id: base64urlToBuffer(opts.user.id as string),
    },
    challenge: base64urlToBuffer(opts.challenge as string),
    pubKeyCredParams: opts.pubKeyCredParams,
    timeout: opts.timeout,
    attestation: opts.attestation,
    authenticatorSelection: opts.authenticatorSelection,
    excludeCredentials: (opts.excludeCredentials ?? []).map(
      (c: Record<string, any>) => ({
        ...c,
        id: base64urlToBuffer(c.id as string),
      }),
    ),
  };
}

/**
 * Convert server authentication options into the format
 * `navigator.credentials.get()` expects.
 */
export function prepareAuthenticationOptions(
  serverOptions: Record<string, unknown>,
): PublicKeyCredentialRequestOptions {
  const opts = serverOptions as Record<string, any>;

  const publicKey: PublicKeyCredentialRequestOptions = {
    ...opts,
    challenge: base64urlToBuffer(opts.challenge as string),
    allowCredentials: (opts.allowCredentials ?? []).map(
      (c: Record<string, any>) => ({
        ...c,
        id: base64urlToBuffer(c.id as string),
      }),
    ),
  };

  return publicKey;
}

/** Serialize a registration credential for POSTing to the server. */
export function serializeRegistrationCredential(
  credential: PublicKeyCredential,
  sessionId: string,
): Record<string, unknown> {
  const response = credential.response as AuthenticatorAttestationResponse;
  return {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    type: credential.type,
    sessionId,
    response: {
      attestationObject: bufferToBase64url(response.attestationObject),
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
      transports: response.getTransports?.() ?? [],
    },
  };
}

/** Serialize an authentication credential for POSTing to the server. */
export function serializeAuthenticationCredential(
  credential: PublicKeyCredential,
): Record<string, unknown> {
  const response = credential.response as AuthenticatorAssertionResponse;
  return {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    type: credential.type,
    response: {
      authenticatorData: bufferToBase64url(response.authenticatorData),
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
      signature: bufferToBase64url(response.signature),
      userHandle: response.userHandle
        ? bufferToBase64url(response.userHandle)
        : null,
    },
  };
}
