import { cx, FOCUS_RING } from './styles';

export interface OptionButtonProps {
  label: string;
  /** Decorative letter (A, B…) that helps scan the options; hidden from screen readers. */
  marker?: string;
  selected?: boolean;
  disabled?: boolean;
  onSelect?: () => void;
}

export function OptionButton({
  label,
  marker,
  selected = false,
  disabled = false,
  onSelect,
}: OptionButtonProps) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      disabled={disabled}
      onClick={onSelect}
      className={cx(
        'flex min-h-touch w-full items-center gap-3 rounded-control border-2 px-4 py-3 text-left',
        'text-body text-ink transition-colors',
        'disabled:cursor-not-allowed',
        FOCUS_RING,
        selected
          ? 'border-accent bg-accent/15'
          : 'border-line bg-surface-raised enabled:hover:border-ink-muted disabled:opacity-60',
      )}
    >
      {marker !== undefined && (
        <span
          aria-hidden="true"
          className={cx(
            'grid size-7 shrink-0 place-items-center rounded-full text-caption font-bold',
            selected ? 'bg-accent text-on-accent' : 'bg-surface text-ink-muted',
          )}
        >
          {marker}
        </span>
      )}
      <span className="flex-1">{label}</span>
    </button>
  );
}
