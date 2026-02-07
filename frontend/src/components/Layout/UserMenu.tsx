import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUserStore } from '@/stores/userStore';

export function UserMenu() {
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(0);
  const menuRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useUserStore();

  const menuItems = [
    { label: 'Settings', action: 'settings' },
    { label: 'separator', action: 'separator' },
    { label: 'Log Out', action: 'logout' },
  ];

  // Close menu on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isOpen]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) return;

    const actionableItems = menuItems.filter((item) => item.action !== 'separator');

    switch (e.key) {
      case 'Escape':
        e.preventDefault();
        setIsOpen(false);
        buttonRef.current?.focus();
        break;
      case 'ArrowDown':
        e.preventDefault();
        setFocusedIndex((prev) => {
          let next = prev + 1;
          if (menuItems[next]?.action === 'separator') next++;
          return next >= menuItems.length ? 0 : next;
        });
        break;
      case 'ArrowUp':
        e.preventDefault();
        setFocusedIndex((prev) => {
          let next = prev - 1;
          if (menuItems[next]?.action === 'separator') next--;
          return next < 0 ? actionableItems.length - 1 : next;
        });
        break;
      case 'Enter':
      case ' ':
        e.preventDefault();
        {
          const item = menuItems[focusedIndex];
          if (item && item.action !== 'separator') {
            handleMenuAction(item.action);
          }
        }
        break;
    }
  };

  const handleMenuAction = (action: string) => {
    switch (action) {
      case 'settings':
        navigate('/settings');
        break;
      case 'logout':
        logout();
        break;
    }
    setIsOpen(false);
  };

  const toggleMenu = () => {
    setIsOpen(!isOpen);
    setFocusedIndex(0);
  };

  const userInitial = user?.name?.charAt(0).toUpperCase();

  return (
    <div className="user-menu" onKeyDown={handleKeyDown}>
      <button
        ref={buttonRef}
        type="button"
        className="topbar-avatar"
        onClick={toggleMenu}
        aria-label="User menu"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        {isAuthenticated && userInitial ? (
          <span className="user-menu__initial">{userInitial}</span>
        ) : (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <circle cx="8" cy="5" r="3" />
            <path d="M2 14c0-3.3 2.7-6 6-6s6 2.7 6 6" />
          </svg>
        )}
      </button>

      {isOpen && (
        <div ref={menuRef} className="user-menu__dropdown" role="menu">
          {isAuthenticated && user && (
            <div className="user-menu__header">
              <div className="user-menu__name">{user.name}</div>
              <div className="user-menu__email">{user.email}</div>
            </div>
          )}
          {menuItems.map((item, index) => {
            if (item.action === 'separator') {
              return <div key={index} className="user-menu__separator" role="separator" />;
            }

            const isDanger = item.action === 'logout';

            return (
              <button
                key={item.action}
                type="button"
                className={`user-menu__item ${isDanger ? 'user-menu__item--danger' : ''} ${focusedIndex === index ? 'user-menu__item--focused' : ''}`}
                onClick={() => handleMenuAction(item.action)}
                onMouseEnter={() => setFocusedIndex(index)}
                role="menuitem"
                tabIndex={focusedIndex === index ? 0 : -1}
              >
                {item.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
