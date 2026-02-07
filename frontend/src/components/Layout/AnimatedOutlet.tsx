import { useRef, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';

export function AnimatedOutlet() {
  const location = useLocation();
  const containerRef = useRef<HTMLDivElement>(null);
  const isFirstRender = useRef(true);

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    const el = containerRef.current;
    if (!el) return;

    // Remove class, force reflow, re-add to restart animation
    el.classList.remove('page-enter');
    void el.offsetHeight;
    el.classList.add('page-enter');
  }, [location.pathname]);

  return (
    <div ref={containerRef} className="page-transition-container page-enter">
      <Outlet />
    </div>
  );
}
