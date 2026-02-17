import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { api, setAuthToken } from '@/services/api';
import { useUserStore } from '@/stores/userStore';
import {
  isWebAuthnSupported,
  prepareAuthenticationOptions,
  serializeAuthenticationCredential,
} from '@/utils/webauthn';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { setUser } = useUserStore();

  const from = (location.state as { from?: string })?.from || '/capture';
  const webauthnOk = isWebAuthnSupported();

  async function handlePasskeyLogin(emailHint?: string) {
    setError('');
    setLoading(true);
    try {
      const optionsRes = await api.passkeyLoginStart(emailHint || undefined);
      if (!optionsRes.data || optionsRes.status === 'error') {
        const msg = (optionsRes as any).errors?.[0]?.message || 'Could not start login — please try again.';
        setError(msg);
        setLoading(false);
        return;
      }
      const serverOptions = optionsRes.data;
      const sessionId = serverOptions.sessionId as string;

      const publicKey = prepareAuthenticationOptions(serverOptions);
      const credential = (await navigator.credentials.get({ publicKey })) as PublicKeyCredential | null;

      if (!credential) {
        setError('Authentication was cancelled.');
        setLoading(false);
        return;
      }

      const serialized = serializeAuthenticationCredential(credential);
      const result = await api.passkeyLoginComplete(sessionId, serialized);

      if (!result.data || result.status === 'error') {
        const msg = (result as any).errors?.[0]?.message || 'Login failed — please try again.';
        setError(msg);
        setLoading(false);
        return;
      }

      setAuthToken(result.data.access_token);
      setUser({
        id: result.data.user_id,
        name: result.data.user_name,
        email: result.data.user_email,
      });
      navigate(from, { replace: true });
    } catch (err: any) {
      if (err?.name === 'NotAllowedError') {
        setError('Authentication was cancelled.');
      } else {
        const apiMsg = err?.data?.errors?.[0]?.message;
        setError(apiMsg || err?.message || 'Login failed — please try again.');
      }
    } finally {
      setLoading(false);
    }
  }

  function handleEmailSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    handlePasskeyLogin(email.trim());
  }

  return (
    <div className="auth-page">
      <Link to="/" className="auth-home-btn">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M19 12H5" />
          <path d="M12 19l-7-7 7-7" />
        </svg>
        Back to home
      </Link>
      <div className="auth-container">
        <div className="auth-card">
          <Link to="/" className="auth-logo" aria-label="Back to home">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true">
              <rect width="40" height="40" rx="10" fill="var(--accent)" />
              <text x="50%" y="54%" dominantBaseline="middle" textAnchor="middle" fill="white" fontSize="20" fontWeight="700">D</text>
            </svg>
          </Link>

          <h1 className="auth-title anim anim-d1">Welcome back</h1>
          <p className="auth-subtitle anim anim-d2">Sign in to continue writing</p>

          {!webauthnOk && (
            <div className="auth-error auth-error--visible">
              Your browser doesn't support passkeys. Please use a modern browser like Chrome, Safari, or Edge.
            </div>
          )}

          <div
            className={`auth-error ${error ? 'auth-error--visible' : 'auth-error--hidden'}`}
            aria-live="polite"
          >
            {error || '\u00A0'}
          </div>

          <button
            type="button"
            className="auth-passkey-btn anim anim-d3"
            onClick={() => handlePasskeyLogin()}
            disabled={loading || !webauthnOk}
          >
            {loading ? (
              <>
                <span className="auth-btn-spinner" aria-hidden="true" />
                Authenticating...
              </>
            ) : (
              <>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                Sign in with passkey
              </>
            )}
          </button>

          <div className="auth-divider anim anim-d4">
            <span>or sign in with email</span>
          </div>

          <form onSubmit={handleEmailSubmit} className="anim anim-d5">
            <div className="auth-field">
              <label className="auth-label" htmlFor="login-email">Email</label>
              <input
                id="login-email"
                className="auth-input"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email webauthn"
                disabled={loading}
              />
            </div>

            <button
              type="submit"
              className="auth-passkey-btn auth-passkey-btn--secondary"
              disabled={loading || !webauthnOk || !email.trim()}
            >
              Continue with email
            </button>
          </form>

          <p className="auth-footer anim anim-d6">
            Don't have an account? <Link to="/signup">Create one</Link>
          </p>

        </div>
      </div>
    </div>
  );
}
