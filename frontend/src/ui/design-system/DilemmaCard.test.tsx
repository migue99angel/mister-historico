import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it, vi } from 'vitest';

import { DilemmaCard, type DilemmaCardData } from './DilemmaCard';

const dilemma: DilemmaCardData = {
  id: 'summer-striker',
  title: 'Delantero de verano',
  prompt: 'La directiva te da presupuesto para un delantero. ¿A quién quieres?',
  options: [
    { id: 'sign-the-veteran', label: 'Fichar al delantero veterano' },
    { id: 'promote-the-youth', label: 'Subir al delantero de la cantera' },
  ],
};

describe('DilemmaCard', () => {
  it('shows the dilemma title and prompt', () => {
    render(<DilemmaCard dilemma={dilemma} />);

    const card = screen.getByRole('region', { name: 'Delantero de verano' });
    expect(card).toHaveTextContent(dilemma.prompt);
  });

  it('groups one toggle button per option', () => {
    render(<DilemmaCard dilemma={dilemma} />);

    const group = screen.getByRole('group', { name: 'Opciones: Delantero de verano' });
    expect(within(group).getAllByRole('button').map((button) => button.textContent)).toEqual([
      'AFichar al delantero veterano',
      'BSubir al delantero de la cantera',
    ]);
  });

  it('marks only the selected option as pressed', () => {
    render(<DilemmaCard dilemma={dilemma} selectedOptionId="promote-the-youth" />);

    expect(screen.getByRole('button', { pressed: true })).toHaveAccessibleName(
      'Subir al delantero de la cantera',
    );
    expect(screen.getByRole('button', { pressed: false })).toHaveAccessibleName(
      'Fichar al delantero veterano',
    );
  });

  it('reports the chosen option id', async () => {
    const onSelect = vi.fn();
    render(<DilemmaCard dilemma={dilemma} onSelect={onSelect} />);

    await userEvent.click(screen.getByRole('button', { name: 'Fichar al delantero veterano' }));

    expect(onSelect).toHaveBeenCalledWith('sign-the-veteran');
  });

  it('disables every option once the decision is locked', () => {
    render(<DilemmaCard dilemma={dilemma} selectedOptionId="sign-the-veteran" disabled />);

    for (const button of screen.getAllByRole('button')) expect(button).toBeDisabled();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <DilemmaCard
        dilemma={dilemma}
        eyebrow="Dilema 2 de 2"
        headingLevel={3}
        selectedOptionId="sign-the-veteran"
      />,
    );

    expect(await axe(container)).toHaveNoViolations();
  });
});
