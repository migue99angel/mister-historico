import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { useBlockReveal } from './useBlockReveal';

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('useBlockReveal', () => {
  it('does not animate a loaded view, reveals dates within five seconds and never restarts on refetch', () => {
    vi.useFakeTimers();
    const { result, rerender } = renderHook(() => useBlockReveal(4, 20));
    expect(result.current.revealing).toBe(false);
    act(() => result.current.start(4, 20));
    expect(result.current.visibleDates).toBe(0);
    act(() => vi.advanceTimersByTime(225));
    expect(result.current.visibleDates).toBe(1);
    rerender();
    expect(result.current.visibleDates).toBe(1);
    act(() => vi.advanceTimersByTime(4775));
    expect(result.current.revealing).toBe(false);
    rerender();
    expect(result.current.revealing).toBe(false);
  });

  it('skips immediately and cancels pending timers on skip and unmount', () => {
    vi.useFakeTimers();
    const { result, unmount } = renderHook(() => useBlockReveal(4, 2));
    act(() => result.current.start(4, 2));
    expect(vi.getTimerCount()).toBeGreaterThan(0);
    act(() => result.current.complete());
    expect(result.current.revealing).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
    act(() => result.current.start(4, 2));
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('shows all with reduced motion or no results', () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const { result } = renderHook(() => useBlockReveal(4, 2));
    act(() => result.current.start(4, 2));
    expect(result.current.revealing).toBe(false);
    act(() => result.current.start(4, 0));
    expect(result.current.revealing).toBe(false);
  });

  it('abandons a sequence when the server supplies another version', () => {
    vi.useFakeTimers();
    const { result, rerender } = renderHook(({ version }) => useBlockReveal(version, 2), {
      initialProps: { version: 4 },
    });
    act(() => result.current.start(4, 2));
    rerender({ version: 5 });
    expect(result.current.revealing).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
  });
});
