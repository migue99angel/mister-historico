import { createContext } from 'react';

export interface RouterContextValue {
  navigate: (to: string, replace?: boolean) => void;
  pathname: string;
}

export const RouterContext = createContext<RouterContextValue | null>(null);
