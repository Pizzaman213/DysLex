import { NavLink } from 'react-router-dom';
import { NavIcon } from '@/components/Shared/NavIcon';
import { useSettingsStore } from '@/stores/settingsStore';
import { DocumentList } from './DocumentList';

const MODE_ITEMS = [
  { to: '/capture', label: 'Capture', icon: 'mic' as const },
  { to: '/mindmap', label: 'Mind Map', icon: 'mindmap' as const },
  { to: '/draft', label: 'Draft', icon: 'edit' as const },
  { to: '/polish', label: 'Polish', icon: 'check' as const },
];

const THEMES = [
  { id: 'cream', label: 'Cream', className: 'tsw-cream' },
  { id: 'night', label: 'Night', className: 'tsw-night' },
  { id: 'blue-tint', label: 'Blue', className: 'tsw-blue' },
] as const;

export function Sidebar() {
  const { theme, setTheme } = useSettingsStore();

  return (
    <aside className="sidebar" role="navigation" aria-label="Main navigation">
      {/* Writing Modes */}
      <div>
        <div className="sb-title">Writing Mode</div>
        <div className="mode-selector">
          {MODE_ITEMS.map((item) => (
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
      <DocumentList />

      {/* Theme Swatches */}
      <div className="theme-row">
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
