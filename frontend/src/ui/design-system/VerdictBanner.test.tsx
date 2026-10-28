import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';

import { VerdictBanner, type VerdictKind } from './VerdictBanner';

describe('VerdictBanner', () => {
  it('is a region named by the verdict', () => {
    render(<VerdictBanner kind="surpassed" title="Superaste a Ramon Prueba" />);

    expect(screen.getByRole('region', { name: 'Superaste a Ramon Prueba' })).toHaveTextContent(
      'Veredicto',
    );
  });

  it('uses the requested heading level', () => {
    render(<VerdictBanner kind="matched" title="Igualaste la historia" headingLevel={1} />);

    expect(
      screen.getByRole('heading', { level: 1, name: 'Igualaste la historia' }),
    ).toBeInTheDocument();
  });

  it('shows the comparison with history', () => {
    render(
      <VerdictBanner
        kind="below"
        title="Te quedaste por debajo"
        description="Tú: Copa Test. Ramon Prueba: Liga Test y Copa Test."
      />,
    );

    expect(screen.getByText('Tú: Copa Test. Ramon Prueba: Liga Test y Copa Test.')).toBeVisible();
  });

  it('shows the manager score out of 100', () => {
    render(<VerdictBanner kind="surpassed" title="Superaste a Ramon Prueba" score={81} />);

    expect(screen.getByText('Puntuación del míster')).toBeInTheDocument();
    expect(screen.getByText('81')).toBeInTheDocument();
    expect(screen.getByText('/100')).toBeInTheDocument();
  });

  it('omits the score until there is one', () => {
    render(<VerdictBanner kind="sacked" title="La directiva te destituyó en enero" />);

    expect(screen.queryByText('Puntuación del míster')).not.toBeInTheDocument();
  });

  it.each<VerdictKind>(['surpassed', 'matched', 'below', 'sacked'])(
    'has no accessibility violations when %s',
    async (kind) => {
      const { container } = render(
        <VerdictBanner kind={kind} title="Veredicto de prueba" description="Detalle" score={50} />,
      );

      expect(await axe(container)).toHaveNoViolations();
    },
  );
});
