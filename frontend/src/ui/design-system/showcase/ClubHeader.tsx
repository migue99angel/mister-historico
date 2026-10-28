import { GenericCrest } from '../GenericCrest';
import { clubs, LEAGUE, SEASON_LABEL } from './sampleData';

/** Top bar of the mock-up screens. */
export function ClubHeader() {
  return (
    <div className="flex items-center gap-3 border-b border-line px-gutter py-3">
      <GenericCrest colors={clubs.testFc.colors} size={36} />
      <div className="min-w-0">
        <p className="font-display text-title leading-tight font-bold">{clubs.testFc.name}</p>
        <p className="text-caption text-ink-muted">
          {LEAGUE} · {SEASON_LABEL}
        </p>
      </div>
    </div>
  );
}
