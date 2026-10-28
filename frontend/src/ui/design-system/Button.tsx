import type { ButtonHTMLAttributes, ReactNode } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost';

export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className'> {
  variant?: ButtonVariant;
  /** Shows a spinner, sets `aria-busy` and blocks further taps until the action ends. */
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
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={[
        'inline-flex min-h-touch min-w-touch items-center justify-center gap-2 rounded-control px-5',
        'text-body font-semibold transition-colors select-none',
        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold',
        'disabled:cursor-not-allowed disabled:opacity-50',
        VARIANT_CLASSES[variant],
        fullWidth ? 'w-full' : '',
      ].join(' ')}
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
