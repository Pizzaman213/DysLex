import { useState, useEffect } from 'react';
import { useSettingsStore } from '@/stores/settingsStore';
import { TabNav } from '@/components/Shared/TabNav';
import { GeneralTab } from '@/components/Panels/Settings/GeneralTab';
import { AppearanceTab } from '@/components/Panels/Settings/AppearanceTab';
import { AccessibilityTab } from '@/components/Panels/Settings/AccessibilityTab';
import { PrivacyTab } from '@/components/Panels/Settings/PrivacyTab';
import type { SettingsTab } from '@/types';

export function SettingsPanel() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('general');
  const { developerMode, loadFromBackend, isLoading } = useSettingsStore();

  useEffect(() => {
    loadFromBackend();
  }, [loadFromBackend]);

  const tabs = [
    { id: 'general', label: 'General' },
    { id: 'appearance', label: 'Appearance' },
    { id: 'accessibility', label: 'Accessibility' },
    { id: 'privacy', label: 'Privacy' },
    { id: 'docs', label: 'Developer Docs', visible: developerMode },
  ];

  return (
    <div className="settings-panel" role="region" aria-label="Settings">
      <h1 className="panel-title">Settings</h1>

      {isLoading ? (
        <div className="loading-state">
          <p>Loading settings...</p>
        </div>
      ) : (
        <>
          <TabNav
            tabs={tabs}
            activeTab={activeTab}
            onTabChange={(tabId) => setActiveTab(tabId as SettingsTab)}
          />

          <div className="tab-content-container">
            {activeTab === 'general' && <GeneralTab />}
            {activeTab === 'appearance' && <AppearanceTab />}
            {activeTab === 'accessibility' && <AccessibilityTab />}
            {activeTab === 'privacy' && <PrivacyTab />}
            {activeTab === 'docs' && developerMode && (
              <div className="settings-tab-content">
                <h2>Developer Documentation</h2>
                <p>Documentation tab will be available in the next phase.</p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
