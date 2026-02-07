import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { VoiceBar } from '../VoiceBar';

const defaultProps = {
  isRecording: false,
  isTranscribing: false,
  onStartRecording: vi.fn(),
  onStopRecording: vi.fn(),
};

function renderVoiceBar(overrides: Partial<Parameters<typeof VoiceBar>[0]> = {}) {
  return render(<VoiceBar {...defaultProps} {...overrides} />);
}

describe('VoiceBar', () => {
  it('renders the mic toggle button', () => {
    renderVoiceBar();
    const btn = screen.getByRole('button', { name: /start recording/i });
    expect(btn).toBeInTheDocument();
  });

  it('calls onStartRecording when clicked while not recording', () => {
    const onStart = vi.fn();
    renderVoiceBar({ onStartRecording: onStart });
    fireEvent.click(screen.getByRole('button', { name: /start recording/i }));
    expect(onStart).toHaveBeenCalledOnce();
  });

  it('calls onStopRecording when clicked while recording', () => {
    const onStop = vi.fn();
    renderVoiceBar({ isRecording: true, onStopRecording: onStop });
    fireEvent.click(screen.getByRole('button', { name: /stop recording/i }));
    expect(onStop).toHaveBeenCalledOnce();
  });

  it('disables the toggle button when transcribing', () => {
    renderVoiceBar({ isTranscribing: true });
    const btn = screen.getByRole('button', { name: /start recording/i });
    expect(btn).toBeDisabled();
  });

  it('sets aria-pressed matching isRecording', () => {
    const { rerender } = render(<VoiceBar {...defaultProps} isRecording={false} />);
    const btn = screen.getByRole('button', { name: /start recording/i });
    expect(btn).toHaveAttribute('aria-pressed', 'false');

    rerender(<VoiceBar {...defaultProps} isRecording={true} />);
    const activeBtn = screen.getByRole('button', { name: /stop recording/i });
    expect(activeBtn).toHaveAttribute('aria-pressed', 'true');
  });

  it('adds voice-bar-compact class when compact is true', () => {
    const { container } = renderVoiceBar({ compact: true });
    const bar = container.querySelector('.voice-bar');
    expect(bar).toHaveClass('voice-bar-compact');
  });

  it('shows "Listening..." text when recording', () => {
    renderVoiceBar({ isRecording: true });
    expect(screen.getByText('Listening...')).toBeInTheDocument();
  });

  it('renders read-aloud button only when onReadAloud is provided', () => {
    const { rerender } = render(<VoiceBar {...defaultProps} />);
    expect(screen.queryByRole('button', { name: /read aloud/i })).not.toBeInTheDocument();

    rerender(<VoiceBar {...defaultProps} onReadAloud={vi.fn()} />);
    expect(screen.getByRole('button', { name: /read aloud/i })).toBeInTheDocument();
  });
});
