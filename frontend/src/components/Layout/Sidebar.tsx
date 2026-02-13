import { NavLink } from 'react-router-dom';
import { NavIcon } from '@/components/Shared/NavIcon';
import { useSettingsStore } from '@/stores/settingsStore';
import { useMediaQuery, MOBILE_QUERY } from '@/hooks/useMediaQuery';
import { DocumentList } from './DocumentList';

const THEMES = [
  { id: 'cream', label: 'Cream', className: 'tsw-cream' },
  { id: 'night', label: 'Night', className: 'tsw-night' },
  { id: 'blue-tint', label: 'Blue', className: 'tsw-blue' },
] as const;

export function Sidebar() {
  const {
    theme, setTheme, mindMapEnabled, draftModeEnabled, polishModeEnabled,
    sidebarCollapsed, toggleSidebar, mobileSidebarOpen,
  } = useSettingsStore();
  const isMobile = useMediaQuery(MOBILE_QUERY);

  const modeItems = [
    { to: '/capture', label: 'Capture', icon: 'mic' as const, enabled: true },
    { to: '/mindmap', label: 'Mind Map', icon: 'mindmap' as const, enabled: mindMapEnabled },
    { to: '/draft', label: 'Draft', icon: 'edit' as const, enabled: draftModeEnabled },
    { to: '/polish', label: 'Polish', icon: 'check' as const, enabled: polishModeEnabled },
  ];

  const visibleModes = modeItems.filter((item) => item.enabled);

  return (
    <aside
      className={[
        'sidebar',
        !isMobile && sidebarCollapsed ? 'collapsed' : '',
        isMobile ? 'mobile-drawer' : '',
        isMobile && mobileSidebarOpen ? 'open' : '',
      ].filter(Boolean).join(' ')}
      role="navigation"
      aria-label="Main navigation"
    >
      {/* Logo toggle */}
      <button
        className={`sidebar-logo-btn ${sidebarCollapsed ? 'flipped' : ''}`}
        onClick={toggleSidebar}
        aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        <svg className="sidebar-logo-svg" width="36" height="36" viewBox="0 0 28 28" fill="none" aria-hidden="true">
          <rect width="28" height="28" rx="8" fill="var(--accent)" />
          <path d="M8 8h4v12H8V8zm6 0h4c2.2 0 4 1.8 4 4s-1.8 4-4 4h-4V8z" fill="var(--text-inverse, #fff)" />
        </svg>
        <span className="sidebar-brand">DysLex AI</span>
      </button>

      {/* Writing Modes */}
      <div>
        <div className="sb-title">Writing Mode</div>
        <div className={`mode-selector ${sidebarCollapsed ? 'mode-selector-collapsed' : ''}`}>
          {visibleModes.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `mode-card ${isActive ? 'active' : ''}`
              }
              title={item.label}
            >
              <div className="mode-card-icon">
                <NavIcon name={item.icon} size={24} />
              </div>
              <span className="mode-card-label">{item.label}</span>
            </NavLink>
          ))}
        </div>
      </div>

      <div className="sb-sep" />

      {/* Documents */}
      <div className="sidebar-docs-wrap">
        <DocumentList />
      </div>

      {/* Theme Swatches */}
      <div className={`theme-row ${sidebarCollapsed ? 'theme-row-collapsed' : ''}`}>
        <span className="theme-row-label">Theme</span>
        {THEMES.map((t) => (
          <button
            key={t.id}
            className={`tsw ${t.className} ${theme === t.id ? 'active' : ''}`}
            onClick={() => setTheme(t.id)}
            aria-label={`Switch to ${t.label} theme`}
            title={t.label}
          />
        ))}
      </div>
    </aside>
  );
}
