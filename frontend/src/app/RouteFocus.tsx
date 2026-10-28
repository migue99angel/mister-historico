import { useEffect, useLayoutEffect, useRef, type ReactNode } from 'react';

import { usePathname } from './routerHooks';

/**
 * Wraps every page and, after a navigation, moves the focus into it unless the new page has
 * focused something of its own (e.g. the final page's title). Otherwise the focus would stay on
 * the control that navigated: dropped on `<body>` once it unmounts, or on a hidden element while
 * Suspense keeps the previous page around for a lazy screen. The wrapper outlives the page's
 * loading and loaded states, so the focus is not dropped again when the content arrives.
 */
export function RouteFocus({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const container = useRef<HTMLDivElement>(null);
  const handledPathname = useRef(pathname);
  const focusBeforePage = useRef<Element | null>(null);

  // Layout effects run before any page effect can move the focus.
  useLayoutEffect(() => {
    focusBeforePage.current = document.activeElement;
  }, [pathname]);

  useEffect(() => {
    if (handledPathname.current === pathname) return;
    handledPathname.current = pathname;
    const page = container.current;
    const focused = document.activeElement;
    const pageTookFocus = focused !== focusBeforePage.current && page?.contains(focused) === true;
    if (page && !pageTookFocus) page.focus();
  }, [pathname]);

  return (
    <div ref={container} tabIndex={-1} className="outline-none">
      {children}
    </div>
  );
}
