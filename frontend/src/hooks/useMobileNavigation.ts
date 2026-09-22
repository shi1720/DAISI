import { useEffect, useRef, useState } from 'react';

// Treat the small-screen drawer as a modal navigation surface. A translated
// off-screen element alone remains reachable by keyboard and screen readers.
export function useMobileNavigation(open: boolean, close: () => void) {
  const sidebarRef = useRef<HTMLElement>(null);
  const [mobile, setMobile] = useState(() => typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 720px)').matches);
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return;
    const query = window.matchMedia('(max-width: 720px)');
    const change = () => { setMobile(query.matches); if (!query.matches) close(); };
    change(); query.addEventListener('change', change);
    return () => query.removeEventListener('change', change);
  }, [close]);
  useEffect(() => {
    if (!mobile || !open || !sidebarRef.current) return;
    const sidebar = sidebarRef.current;
    const previousFocus = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const controls = () => Array.from(sidebar.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]'));
    (sidebar.querySelector<HTMLElement>('[aria-current="page"]') ?? controls()[0])?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); close(); return; }
      if (event.key !== 'Tab') return;
      const items = controls(); const first = items[0]; const last = items.at(-1);
      if (!first || !last) return;
      if (event.shiftKey && (document.activeElement === first || !sidebar.contains(document.activeElement))) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && (document.activeElement === last || !sidebar.contains(document.activeElement))) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', keydown);
    return () => {
      document.removeEventListener('keydown', keydown);
      document.body.style.overflow = previousOverflow;
      if (previousFocus?.isConnected) previousFocus.focus();
    };
  }, [mobile, open, close]);
  return { mobile, sidebarRef };
}
