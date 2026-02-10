import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, setAuthToken } from '@/services/api';
import { useUserStore } from '@/stores/userStore';
import {
  isWebAuthnSupported,
  prepareRegistrationOptions,
  serializeRegistrationCredential,
} from '@/utils/webauthn';

export function SignupPage() {
  const [step, setStep] = useState<'info' | 'passkey'>('info');
  const [stepDirection, setStepDirection] = useState<'forward' | 'back'>('forward');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { setUser } = useUserStore();

  const webauthnOk = isWebAuthnSupported();

  function handleInfoSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !email.trim()) return;
    setError('');
    setStepDirection('forward');
    setStep('passkey');
  }

  async function handleCreatePasskey() {
    setError('');
    setLoading(true);
    try {
      const optionsRes = await api.passkeyRegisterStart(email.trim(), name.trim());
      if (!optionsRes.data || optionsRes.status === 'error') {
        const msg = (optionsRes as any).errors?.[0]?.message || 'Could not start registration — please try again.';
        setError(msg);
        setLoading(false);
        return;
      }
      const serverOptions = optionsRes.data;
      const sessionId = serverOptions.sessionId as string;

      const publicKey = prepareRegistrationOptions(serverOptions);
      const credential = (await navigator.credentials.create({ publicKey })) as PublicKeyCredential | null;

      if (!credential) {
        setError('Passkey creation was cancelled.');
        setLoading(false);
        return;
      }

      const serialized = serializeRegistrationCredential(credential, sessionId);
      const result = await api.passkeyRegisterComplete(email.trim(), serialized);

      if (!result.data || result.status === 'error') {
        const msg = (result as any).errors?.[0]?.message || 'Registration failed — please try again.';
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
      navigate('/capture', { replace: true });
    } catch (err: any) {
      if (err?.name === 'NotAllowedError') {
        setError('Passkey creation was cancelled.');
      } else {
        const apiMsg = err?.data?.errors?.[0]?.message;
        setError(apiMsg || err?.message || 'Registration failed — please try again.');
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-logo">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true">
              <rect width="40" height="40" rx="10" fill="var(--accent)" />
              <text x="50%" y="54%" dominantBaseline="middle" textAnchor="middle" fill="white" fontSize="20" fontWeight="700">D</text>
            </svg>
          </div>

          <h1 className="auth-title anim anim-d1">Create your account</h1>
          <p className="auth-subtitle anim anim-d2">
            {step === 'info'
              ? 'Enter your name and email to get started'
              : 'Set up a passkey for secure, password-free sign in'}
          </p>

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

          {step === 'info' && (
            <form
              key="step-info"
              onSubmit={handleInfoSubmit}
              className={`anim anim-d3 ${stepDirection === 'back' ? 'auth-step-back' : ''}`}
            >
              <div className="auth-field">
                <label className="auth-label" htmlFor="signup-name">Name</label>
                <input
                  id="signup-name"
                  className="auth-input"
                  type="text"
                  placeholder="Your name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  autoComplete="name"
                  required
                />
              </div>

              <div className="auth-field">
                <label className="auth-label" htmlFor="signup-email">Email</label>
                <input
                  id="signup-email"
                  className="auth-input"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  required
                />
              </div>

              <button
                type="submit"
                className="auth-passkey-btn"
                disabled={!name.trim() || !email.trim()}
              >
                Continue
              </button>
            </form>
          )}

          {step === 'passkey' && (
            <div
              key="step-passkey"
              className={`auth-passkey-prompt ${stepDirection === 'forward' ? 'auth-step-forward' : 'auth-step-back'}`}
            >
              <div className="auth-passkey-icon" aria-hidden="true">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 11c0-1.1.9-2 2-2s2 .9 2 2-.9 2-2 2-2-.9-2-2z" />
                  <path d="M14 13.5V17l-1.5 1.5" />
                  <path d="M14 17l1.5 1.5" />
                  <circle cx="10" cy="10" r="8" />
                </svg>
              </div>

              <p className="auth-passkey-description">
                A passkey lets you sign in with your fingerprint, face, or screen lock —
                no password needed. It's stored securely on your device.
              </p>

              <button
                type="button"
                className="auth-passkey-btn"
                onClick={handleCreatePasskey}
                disabled={loading || !webauthnOk}
              >
                {loading ? (
                  <>
                    <span className="auth-btn-spinner" aria-hidden="true" />
                    Creating passkey...
                  </>
                ) : (
                  <>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                    Create passkey
                  </>
                )}
              </button>

              <button
                type="button"
                className="auth-back-btn"
                onClick={() => { setStepDirection('back'); setStep('info'); setError(''); }}
                disabled={loading}
              >
                Back
              </button>
            </div>
          )}

          <p className="auth-footer anim anim-d5">
            Already have an account? <Link to="/login">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
