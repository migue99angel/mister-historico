import { useCallback, useEffect, useMemo, useState, type MouseEvent, type ReactNode } from 'react';

import { RouterContext } from './routerContext';
import { useNavigate } from './routerHooks';

export function NativeRouter({ children }: { children: ReactNode }) {
  const [pathname, setPathname] = useState(() => window.location.pathname);

  useEffect(() => {
    const updatePath = () => {
      setPathname(window.location.pathname);
    };
    window.addEventListener('popstate', updatePath);
    return () => {
      window.removeEventListener('popstate', updatePath);
    };
  }, []);

  const navigate = useCallback((to: string, replace = false) => {
    const target = new URL(to, window.location.href);
    if (target.origin !== window.location.origin) {
      window.location.assign(target.href);
      return;
    }
    const nextPath = `${target.pathname}${target.search}${target.hash}`;
    if (replace) window.history.replaceState(null, '', nextPath);
    else window.history.pushState(null, '', nextPath);
    setPathname(target.pathname);
  }, []);

  const context = useMemo(() => ({ navigate, pathname }), [navigate, pathname]);
  return <RouterContext.Provider value={context}>{children}</RouterContext.Provider>;
}

export function RouterLink({
  to,
  children,
  onClick,
}: {
  to: string;
  children: ReactNode;
  onClick?: (event: MouseEvent<HTMLAnchorElement>) => void;
}) {
  const navigate = useNavigate();
  return (
    <a
      href={to}
      onClick={(event) => {
        onClick?.(event);
        if (
          event.defaultPrevented ||
          event.button !== 0 ||
          event.metaKey ||
          event.ctrlKey ||
          event.shiftKey ||
          event.altKey
        ) {
          return;
        }
        event.preventDefault();
        navigate(to);
      }}
    >
      {children}
    </a>
  );
}
