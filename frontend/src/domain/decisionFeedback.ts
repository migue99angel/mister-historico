/** Published values only: this projection never evaluates effects or team strength. */
export interface DecisionView {
  runId: string;
  seasonId: string;
  version: number;
  status: string;
  block: { number: number };
  decisions: { dilemmaId: string; optionId: string; blockNumber: number }[];
  pendingDilemmas: { id: string }[];
  state: { morale: number; boardConfidence: number; fitness: number };
  squad: {
    size: number;
    averageRating: number;
    players: {
      id: string;
      displayName: string;
      morale: number;
      fitness: number;
      injury: { daysOut: number } | null;
    }[];
  };
  tactic: { style: string; system: string };
  competitionPriorities: { competitionId: string; priority: string }[];
}

export const TACTIC_LABELS: Record<string, string> = {
  balanced: 'Equilibrado',
  pressing: 'Presión',
  counter: 'Contraataque',
  possession: 'Posesión',
};
export const PRIORITY_LABELS: Record<string, string> = {
  low: 'Baja',
  normal: 'Normal',
  high: 'Alta',
};

export function injuryLabel(injury: { daysOut: number } | null): string {
  return injury === null ? 'Disponible' : `${String(injury.daysOut)} días de baja`;
}

/** Null means this pair cannot establish what changed during this decision. */
export function describeDecisionChanges(
  before: DecisionView,
  after: DecisionView,
  choice: { dilemmaId: string; optionId: string },
): string[] | null {
  const made = after.decisions.at(-1);
  if (
    before.runId !== after.runId ||
    before.seasonId !== after.seasonId ||
    after.version !== before.version + 1 ||
    before.status !== 'in_progress' ||
    after.status !== before.status ||
    after.block.number !== before.block.number ||
    after.decisions.length !== before.decisions.length + 1 ||
    made?.dilemmaId !== choice.dilemmaId ||
    made.optionId !== choice.optionId ||
    made.blockNumber !== before.block.number ||
    !before.pendingDilemmas.some(({ id }) => id === choice.dilemmaId) ||
    before.decisions.some((decision, index) => {
      const next = after.decisions[index];
      return (
        decision.dilemmaId !== next?.dilemmaId ||
        decision.optionId !== next.optionId ||
        decision.blockNumber !== next.blockNumber
      );
    }) ||
    JSON.stringify(
      before.pendingDilemmas.filter(({ id }) => id !== choice.dilemmaId).map(({ id }) => id),
    ) !== JSON.stringify(after.pendingDilemmas.map(({ id }) => id))
  )
    return null;

  const changes: string[] = [];
  let changed = false;
  function numeric(label: string, old: number, next: number, includeZero = false) {
    if (old !== next) changed = true;
    if (old === next && !includeZero) return;
    const delta = Number((next - old).toFixed(2));
    changes.push(
      `${label}: ${String(old)} → ${String(next)} (${delta > 0 ? '+' : ''}${String(delta)}).`,
    );
  }
  function text(label: string, old: string, next: string) {
    if (old === next) return;
    changed = true;
    changes.push(`${label}: ${old} → ${next}.`);
  }
  numeric('Moral', before.state.morale, after.state.morale, true);
  numeric(
    'Confianza de la directiva',
    before.state.boardConfidence,
    after.state.boardConfidence,
    true,
  );
  numeric('Físico medio', before.state.fitness, after.state.fitness, true);
  numeric('Jugadores en plantilla', before.squad.size, after.squad.size);
  numeric('Media nominal de la plantilla', before.squad.averageRating, after.squad.averageRating);
  const previousPlayers = new Map(before.squad.players.map((player) => [player.id, player]));
  const currentPlayers = new Map(after.squad.players.map((player) => [player.id, player]));
  for (const player of before.squad.players) {
    if (!currentPlayers.has(player.id)) {
      changed = true;
      changes.push(`Sale de la plantilla: ${player.displayName}.`);
    }
  }
  for (const player of after.squad.players) {
    const previous = previousPlayers.get(player.id);
    if (!previous) {
      changed = true;
      changes.push(`Entra en la plantilla: ${player.displayName}.`);
      continue;
    }
    numeric(`${player.displayName} · Moral`, previous.morale, player.morale);
    numeric(`${player.displayName} · Físico`, previous.fitness, player.fitness);
    text(
      `${player.displayName} · Lesión`,
      injuryLabel(previous.injury),
      injuryLabel(player.injury),
    );
  }
  text('Sistema', before.tactic.system, after.tactic.system);
  text(
    'Estilo',
    TACTIC_LABELS[before.tactic.style] ?? before.tactic.style,
    TACTIC_LABELS[after.tactic.style] ?? after.tactic.style,
  );
  const previousPriorities = new Map(
    before.competitionPriorities.map((p) => [p.competitionId, p.priority]),
  );
  const currentPriorities = new Map(
    after.competitionPriorities.map((p) => [p.competitionId, p.priority]),
  );
  for (const id of new Set([...previousPriorities.keys(), ...currentPriorities.keys()])) {
    text(
      `Prioridad ${id}`,
      PRIORITY_LABELS[previousPriorities.get(id) ?? ''] ?? 'Sin dato',
      PRIORITY_LABELS[currentPriorities.get(id) ?? ''] ?? 'Sin dato',
    );
  }
  if (!changed) changes.push('Sin cambios visibles en los datos publicados.');
  return changes;
}
