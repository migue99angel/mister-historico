import { useId, type ReactNode } from 'react';

import { ComponentsSection } from './showcase/ComponentsSection';
import { RunLoopMockup } from './showcase/RunLoopMockup';
import { RunResultMockup } from './showcase/RunResultMockup';
import { TokensSection } from './showcase/TokensSection';
import { FOCUS_RING } from './styles';

const SECTIONS = [
  { id: 'tokens', title: 'Tokens' },
  { id: 'componentes', title: 'Componentes' },
  { id: 'maquetas', title: 'Maquetas' },
] as const;

function ShowcaseSection({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: ReactNode;
}) {
  const titleId = useId();
  return (
    <section id={id} aria-labelledby={titleId} className="scroll-mt-20">
      <h2 id={titleId} className="mb-4 font-display text-headline font-extrabold">
        {title}
      </h2>
      {children}
    </section>
  );
}

/**
 * Development-only page with the design tokens, every component in each state and two
 * mobile mock-ups with synthetic Test FC data. Loaded lazily, outside the initial bundle.
 */
export function Showcase() {
  return (
    <div className="min-h-dvh bg-canvas text-ink">
      <header className="mx-auto max-w-5xl px-gutter pt-8 pb-4">
        <p className="text-caption font-semibold tracking-widest text-accent uppercase">
          Míster Histórico · solo desarrollo
        </p>
        <h1 className="font-display text-display font-extrabold">Sistema de diseño</h1>
        <p className="mt-2 max-w-prose text-body text-ink-muted">
          Tokens, componentes y maquetas de pantalla con datos sintéticos de Test FC y la Liga Test.
          Nada de lo que aparece aquí es un dato histórico real.
        </p>
      </header>
      <nav
        aria-label="Secciones"
        className="sticky top-0 z-10 border-y border-line bg-canvas/95 backdrop-blur"
      >
        <ul className="mx-auto flex max-w-5xl gap-1 overflow-x-auto px-gutter">
          {SECTIONS.map((section) => (
            <li key={section.id}>
              <a
                href={`#${section.id}`}
                className={`inline-flex min-h-touch items-center rounded-control px-3 text-body font-semibold text-ink hover:bg-surface-raised ${FOCUS_RING}`}
              >
                {section.title}
              </a>
            </li>
          ))}
        </ul>
      </nav>
      <main className="mx-auto flex max-w-5xl flex-col gap-12 px-gutter py-8">
        <ShowcaseSection id="tokens" title="Tokens">
          <TokensSection />
        </ShowcaseSection>
        <ShowcaseSection id="componentes" title="Componentes">
          <ComponentsSection />
        </ShowcaseSection>
        <ShowcaseSection id="maquetas" title="Maquetas">
          <div className="grid gap-10 lg:grid-cols-2">
            <RunLoopMockup />
            <RunResultMockup />
          </div>
        </ShowcaseSection>
      </main>
    </div>
  );
}
