import type { ButtonHTMLAttributes, ReactNode } from 'react';

import { cx, FOCUS_RING } from './styles';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost';

export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className'> {
  variant?: ButtonVariant;
  /**
   * Shows a spinner, sets `aria-busy` and ignores further taps until the action ends. The
   * button stays focusable (`aria-disabled`, not `disabled`) so keyboard focus is not lost.
   */
  loading?: boolean;
  fullWidth?: boolean;
  children: ReactNode;
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: 'bg-accent text-on-accent enabled:hover:bg-accent-strong',
  secondary: 'border border-line bg-surface-raised text-ink enabled:hover:border-ink-muted',
  ghost: 'text-ink enabled:hover:bg-surface-raised',
};

export function Button({
  variant = 'primary',
  loading = false,
  fullWidth = false,
  disabled = false,
  type = 'button',
  onClick,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      type={type}
      disabled={disabled}
      aria-busy={loading || undefined}
      aria-disabled={loading || undefined}
      onClick={(event) => {
        if (loading) {
          event.preventDefault();
          return;
        }
        onClick?.(event);
      }}
      className={cx(
        'inline-flex min-h-touch min-w-touch items-center justify-center gap-2 rounded-control px-5',
        'text-body font-semibold transition-colors select-none',
        'disabled:cursor-not-allowed disabled:opacity-50 aria-busy:cursor-wait',
        FOCUS_RING,
        VARIANT_CLASSES[variant],
        fullWidth && 'w-full',
      )}
    >
      {loading && (
        <span
          aria-hidden="true"
          className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
        />
      )}
      {children}
    </button>
  );
}
