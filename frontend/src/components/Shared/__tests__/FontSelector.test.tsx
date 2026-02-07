import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FontSelector } from '../FontSelector';
import { useSettingsStore } from '@/stores/settingsStore';

describe('FontSelector', () => {
  beforeEach(() => {
    useSettingsStore.setState({ font: 'OpenDyslexic' });
  });

  it('renders a select with 4 options', () => {
    render(<FontSelector />);
    const select = screen.getByRole('combobox');
    const options = screen.getAllByRole('option');
    expect(select).toBeInTheDocument();
    expect(options).toHaveLength(4);
  });

  it('shows current font as selected', () => {
    render(<FontSelector />);
    const select = screen.getByRole('combobox') as HTMLSelectElement;
    expect(select.value).toBe('OpenDyslexic');
  });

  it('updates the store when a new font is selected', () => {
    render(<FontSelector />);
    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'AtkinsonHyperlegible' } });
    expect(useSettingsStore.getState().font).toBe('AtkinsonHyperlegible');
  });

  it('displays all expected font option labels', () => {
    render(<FontSelector />);
    expect(screen.getByText('OpenDyslexic')).toBeInTheDocument();
    expect(screen.getByText('Atkinson Hyperlegible')).toBeInTheDocument();
    expect(screen.getByText('Lexie Readable')).toBeInTheDocument();
    expect(screen.getByText('System Default')).toBeInTheDocument();
  });
});
