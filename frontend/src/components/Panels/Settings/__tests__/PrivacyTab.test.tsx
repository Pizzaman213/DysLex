import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PrivacyTab } from '../PrivacyTab';
import { useSettingsStore } from '@/stores/settingsStore';
import { api } from '@/services/api';

vi.mock('@/services/api', () => ({
  api: {
    getSettings: vi.fn(),
    updateSettings: vi.fn(),
    exportUserData: vi.fn(),
    deleteUserData: vi.fn(),
  },
}));

beforeEach(() => {
  vi.clearAllMocks();
  useSettingsStore.setState({
    anonymizedDataCollection: false,
    cloudSync: false,
  });
});

describe('PrivacyTab', () => {
  it('download data button exists', () => {
    render(<PrivacyTab />);
    expect(screen.getByRole('button', { name: /download/i })).toBeInTheDocument();
  });

  it('download data button calls api.exportUserData when clicked', async () => {
    const mockBlob = new Blob(['{}'], { type: 'application/json' });
    vi.mocked(api.exportUserData).mockResolvedValue(mockBlob);

    // Stub URL.createObjectURL and URL.revokeObjectURL for jsdom
    const createObjectURLSpy = vi.fn(() => 'blob:http://localhost/fake');
    const revokeObjectURLSpy = vi.fn();
    global.URL.createObjectURL = createObjectURLSpy;
    global.URL.revokeObjectURL = revokeObjectURLSpy;

    render(<PrivacyTab />);
    const downloadBtn = screen.getByRole('button', { name: /download/i });
    fireEvent.click(downloadBtn);

    await waitFor(() => {
      expect(api.exportUserData).toHaveBeenCalledWith('00000000-0000-0000-0000-000000000000');
    });
  });

  it('delete button opens confirmation dialog', () => {
    render(<PrivacyTab />);
    const deleteBtn = screen.getByRole('button', { name: /^delete$/i });
    fireEvent.click(deleteBtn);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/confirm deletion/i)).toBeInTheDocument();
  });

  it('delete confirmation requires typing "DELETE" before the action button is enabled', () => {
    render(<PrivacyTab />);
    // Open the confirmation dialog
    const deleteBtn = screen.getByRole('button', { name: /^delete$/i });
    fireEvent.click(deleteBtn);

    const confirmBtn = screen.getByRole('button', { name: /delete everything/i });
    expect(confirmBtn).toBeDisabled();

    const input = screen.getByPlaceholderText(/type delete/i);
    fireEvent.change(input, { target: { value: 'DELETE' } });

    expect(confirmBtn).not.toBeDisabled();
  });
});
