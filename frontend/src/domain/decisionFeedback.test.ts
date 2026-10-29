import { describe, expect, it } from 'vitest';

import { describeDecisionChanges, type DecisionView } from './decisionFeedback';

const choice = { dilemmaId: 'training', optionId: 'rest' };
function before(): DecisionView {
  return {
    runId: 'test-run', seasonId: 'test-fc-2000-01', version: 0,
    status: 'in_progress', block: { number: 1 },
    decisions: [], pendingDilemmas: [{ id: 'training' }],
    state: { morale: 50, boardConfidence: 100, fitness: 70 },
    squad: { size: 1, averageRating: 60, players: [
      { id: 'test-player', displayName: 'Test Player', morale: 50, fitness: 70, injury: null },
    ] },
    tactic: { style: 'balanced', system: '4-4-2' }, competitionPriorities: [],
  };
}
function after(): DecisionView {
  return { ...before(), version: 1, pendingDilemmas: [], decisions: [{ ...choice, blockNumber: 1 }] };
}

describe('describeDecisionChanges', () => {
  it('shows received values and exact differences, including zero at a limit', () => {
    const next = { ...after(), state: { morale: 54, boardConfidence: 100, fitness: 70 } };
    expect(describeDecisionChanges(before(), next, choice)).toEqual(expect.arrayContaining([
      'Moral: 50 → 54 (+4).', 'Confianza de la directiva: 100 → 100 (0).',
      'Físico medio: 70 → 70 (0).',
    ]));
  });

  it('reports no visible differences without promising deferred effects', () => {
    expect(describeDecisionChanges(before(), after(), choice)).toContain('Sin cambios visibles en los datos publicados.');
  });

  it.each([
    { version: 0 }, { version: 2 }, { runId: 'other-run' }, { seasonId: 'other-season' },
    { status: 'finished' }, { block: { number: 2 } }, { decisions: [] },
    { decisions: [{ ...choice, optionId: 'different', blockNumber: 1 }] },
    { pendingDilemmas: [{ id: 'training' }] },
  ])('does not attribute differences to an unrelated or nonconsecutive reply: %j', (patch) => {
    expect(describeDecisionChanges(before(), { ...after(), ...patch }, choice)).toBeNull();
  });

  it('rejects altered earlier decisions', () => {
    const previous = { ...choice, dilemmaId: 'earlier', blockNumber: 1 };
    expect(describeDecisionChanges(
      { ...before(), decisions: [previous] },
      { ...after(), decisions: [{ ...previous, optionId: 'different' }, { ...choice, blockNumber: 1 }] },
      choice,
    )).toBeNull();
  });

  it('does not treat an already confirmed choice as a new decision', () => {
    expect(describeDecisionChanges(after(), { ...after(), version: 2 }, choice)).toBeNull();
  });

  it('compares player availability, membership, tactic and published priorities', () => {
    const next = after();
    next.squad = { size: 1, averageRating: 65, players: [
      { id: 'new-player', displayName: 'New Player', morale: 65, fitness: 80, injury: { daysOut: 3 } },
    ] };
    next.tactic = { style: 'pressing', system: '4-3-3' };
    next.competitionPriorities = [{ competitionId: 'test-league', priority: 'high' }];
    expect(describeDecisionChanges(before(), next, choice)).toEqual(expect.arrayContaining([
      'Sale de la plantilla: Test Player.', 'Entra en la plantilla: New Player.',
      'Media nominal de la plantilla: 60 → 65 (+5).',
      'Sistema: 4-4-2 → 4-3-3.', 'Estilo: Equilibrado → Presión.',
      'Prioridad test-league: Sin dato → Alta.',
    ]));
  });

  it('reports individual morale, fitness and injuries without inferring causes', () => {
    const next = after();
    next.squad.players[0] = { ...next.squad.players[0]!, morale: 53, fitness: 68, injury: { daysOut: 7 } };
    expect(describeDecisionChanges(before(), next, choice)).toEqual(expect.arrayContaining([
      'Test Player · Moral: 50 → 53 (+3).', 'Test Player · Físico: 70 → 68 (-2).',
      'Test Player · Lesión: Disponible → 7 días de baja.',
    ]));
  });

  it('shows recovery and removed priorities from received values', () => {
    const previous = before();
    previous.squad.players[0]!.injury = { daysOut: 2 };
    previous.competitionPriorities = [{ competitionId: 'test-league', priority: 'low' }];
    expect(describeDecisionChanges(previous, after(), choice)).toEqual(expect.arrayContaining([
      'Test Player · Lesión: 2 días de baja → Disponible.',
      'Prioridad test-league: Baja → Sin dato.',
    ]));
  });
});
