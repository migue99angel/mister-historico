import { useContext } from 'react';

import { matchRoute, type AppRoute } from './routeMatcher';
import { RouterContext, type RouterContextValue } from './routerContext';

export function useNavigate(): RouterContextValue['navigate'] {
  const context = useContext(RouterContext);
  if (!context) throw new Error('Navigation is only available inside NativeRouter.');
  return context.navigate;
}

export function usePathname(): string {
  const context = useContext(RouterContext);
  if (!context) throw new Error('Routing is only available inside NativeRouter.');
  return context.pathname;
}

export function useCurrentRoute(): AppRoute {
  return matchRoute(usePathname());
}
