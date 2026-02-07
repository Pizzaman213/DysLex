import { type KeyboardEvent } from 'react';

export interface Tab {
  id: string;
  label: string;
  visible?: boolean;
}

interface TabNavProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

export function TabNav({ tabs, activeTab, onTabChange }: TabNavProps) {
  const visibleTabs = tabs.filter((tab) => tab.visible !== false);

  const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement>, _tabId: string, index: number) => {
    if (e.key === 'ArrowRight') {
      e.preventDefault();
      const nextIndex = (index + 1) % visibleTabs.length;
      const nextTab = visibleTabs[nextIndex];
      onTabChange(nextTab.id);
      // Focus the next tab button
      const buttons = e.currentTarget.parentElement?.querySelectorAll('button');
      if (buttons) (buttons[nextIndex] as HTMLButtonElement).focus();
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      const prevIndex = (index - 1 + visibleTabs.length) % visibleTabs.length;
      const prevTab = visibleTabs[prevIndex];
      onTabChange(prevTab.id);
      // Focus the previous tab button
      const buttons = e.currentTarget.parentElement?.querySelectorAll('button');
      if (buttons) (buttons[prevIndex] as HTMLButtonElement).focus();
    } else if (e.key === 'Home') {
      e.preventDefault();
      const firstTab = visibleTabs[0];
      onTabChange(firstTab.id);
      const buttons = e.currentTarget.parentElement?.querySelectorAll('button');
      if (buttons) (buttons[0] as HTMLButtonElement).focus();
    } else if (e.key === 'End') {
      e.preventDefault();
      const lastTab = visibleTabs[visibleTabs.length - 1];
      onTabChange(lastTab.id);
      const buttons = e.currentTarget.parentElement?.querySelectorAll('button');
      if (buttons) (buttons[visibleTabs.length - 1] as HTMLButtonElement).focus();
    }
  };

  return (
    <div className="tab-nav" role="tablist" aria-label="Settings navigation">
      {visibleTabs.map((tab, index) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={activeTab === tab.id}
          aria-controls={`${tab.id}-panel`}
          id={`${tab.id}-tab`}
          tabIndex={activeTab === tab.id ? 0 : -1}
          className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
          onClick={() => onTabChange(tab.id)}
          onKeyDown={(e) => handleKeyDown(e, tab.id, index)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
