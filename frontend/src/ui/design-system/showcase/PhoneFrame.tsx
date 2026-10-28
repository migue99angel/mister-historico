import { useId, type ReactNode } from 'react';

export interface PhoneFrameProps {
  title: string;
  description: string;
  children: ReactNode;
}

/** A Pixel 7-wide (412 px) screen; on a real phone it simply fills the width. */
export function PhoneFrame({ title, description, children }: PhoneFrameProps) {
  const titleId = useId();
  return (
    <section aria-labelledby={titleId} className="flex flex-col gap-3">
      <div>
        <h3 id={titleId} className="font-display text-title font-bold">
          {title}
        </h3>
        <p className="text-caption text-ink-muted">{description}</p>
      </div>
      <div className="mx-auto w-full max-w-[412px] rounded-[2rem] border-4 border-line bg-canvas shadow-2xl shadow-black/50">
        {children}
      </div>
    </section>
  );
}
