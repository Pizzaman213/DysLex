import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallbackRoute?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * React error boundary — catches render errors and shows an encouraging
 * fallback instead of a blank screen. Styled with CSS variables so it
 * works across all themes (cream / night / blue-tint).
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  private handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  private handleNavigate = () => {
    // Navigate to capture mode (safe landing page) via full reload to
    // guarantee a clean React tree.
    window.location.href = this.props.fallbackRoute ?? '/capture';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary-fallback" role="alert">
          <h2>Something unexpected happened</h2>
          <p>
            Don&apos;t worry — your work is safe. You can try again or switch to
            another mode.
          </p>
          <div className="error-boundary-actions">
            <button onClick={this.handleRetry} className="error-boundary-btn primary">
              Try Again
            </button>
            <button onClick={this.handleNavigate} className="error-boundary-btn secondary">
              Go to Capture
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
