import { useId, type ReactNode } from 'react';

export interface SpecimenProps {
  name: string;
  description: string;
  children: ReactNode;
}

/** One design-system entry of the showcase: a named region with its variants. */
export function Specimen({ name, description, children }: SpecimenProps) {
  const titleId = useId();
  return (
    <section aria-labelledby={titleId} className="rounded-card border border-line p-gutter">
      <h3 id={titleId} className="font-display text-title font-bold">
        {name}
      </h3>
      <p className="mb-4 text-caption text-ink-muted">{description}</p>
      <div className="flex flex-col gap-4">{children}</div>
    </section>
  );
}

export interface VariantProps {
  label: string;
  children: ReactNode;
}

/** A labelled state of a component inside a specimen. */
export function Variant({ label, children }: VariantProps) {
  return (
    <div>
      <p className="mb-1.5 text-caption font-semibold tracking-wide text-ink-muted uppercase">
        {label}
      </p>
      {children}
    </div>
  );
}
