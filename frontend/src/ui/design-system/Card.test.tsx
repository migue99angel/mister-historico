import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';

import { Card } from './Card';

describe('Card', () => {
  it('is a region named by its title', () => {
    render(
      <Card title="Resumen del bloque">
        <p>3 victorias</p>
      </Card>,
    );

    expect(screen.getByRole('region', { name: 'Resumen del bloque' })).toHaveTextContent(
      '3 victorias',
    );
  });

  it('uses the requested heading level for its title', () => {
    render(
      <Card title="Clasificación" headingLevel={3}>
        <p>Liga Test</p>
      </Card>,
    );

    expect(screen.getByRole('heading', { level: 3, name: 'Clasificación' })).toBeInTheDocument();
  });

  it('shows an eyebrow above the title', () => {
    render(
      <Card title="Reunión con la directiva" eyebrow="Dilema 1 de 2">
        <p>¿Cómo respondes?</p>
      </Card>,
    );

    expect(screen.getByText('Dilema 1 de 2')).toBeInTheDocument();
  });

  it('is a plain container without a title', () => {
    render(
      <Card>
        <p>Sin título</p>
      </Card>,
    );

    expect(screen.queryByRole('region')).not.toBeInTheDocument();
    expect(screen.getByText('Sin título')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <Card title="Resumen del bloque" eyebrow="Agosto" tone="highlight">
        <p>3 victorias</p>
      </Card>,
    );

    expect(await axe(container)).toHaveNoViolations();
  });
});
