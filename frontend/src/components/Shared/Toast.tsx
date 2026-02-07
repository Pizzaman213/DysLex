import { Toast as ToastType } from '../../hooks/useToast';

interface ToastProps {
  toast: ToastType;
  onDismiss: (id: string) => void;
}

export function Toast({ toast, onDismiss }: ToastProps) {
  const getEmoji = () => {
    switch (toast.type) {
      case 'success':
        return '✓';
      case 'coaching':
        return '💡';
      case 'info':
      default:
        return 'ℹ';
    }
  };

  return (
    <div className={`toast toast--${toast.type}`} role="status" aria-live="polite">
      <span className="toast__icon">{getEmoji()}</span>
      <span className="toast__message">{toast.message}</span>
      {toast.action && (
        <button
          className="toast__action"
          onClick={toast.action.onClick}
          type="button"
        >
          {toast.action.label}
        </button>
      )}
      <button
        className="toast__dismiss"
        onClick={() => onDismiss(toast.id)}
        aria-label="Dismiss notification"
        type="button"
      >
        ×
      </button>
    </div>
  );
}
