import type { ReactNode } from 'react';

import type { RunViewDto } from '../../../application/ports';
import { Button } from '../../design-system';
import { TeamPanel } from './TeamPanel';

interface CoachLayoutProps {
  run: RunViewDto;
  revealing: boolean;
  onDecisions: (() => void) | undefined;
  children: ReactNode;
}

/** One panel in DOM order, stacked on mobile and beside the play area on desktop. */
export function CoachLayout({ run, revealing, onDecisions, children }: CoachLayoutProps) {
  return (
    <div className="grid min-w-0 gap-6 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)] lg:items-start">
      {!revealing && (
        <aside aria-label="Panel del equipo" className="min-w-0">
          <TeamPanel run={run} />
          {onDecisions && (
            <div className="mt-2">
              <Button variant="ghost" fullWidth onClick={onDecisions}>
                Volver a decisiones
              </Button>
            </div>
          )}
        </aside>
      )}
      <div className={`flex min-w-0 flex-col gap-4 ${revealing ? 'lg:col-span-2' : ''}`}>
        {children}
      </div>
    </div>
  );
}
