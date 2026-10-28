import { BlockProgress } from '../BlockProgress';
import { Button } from '../Button';
import { Card } from '../Card';
import { MiniStandings } from '../MiniStandings';
import { VerdictBanner } from '../VerdictBanner';
import { ClubHeader } from './ClubHeader';
import { PhoneFrame } from './PhoneFrame';
import { CUP, finalStandings, HISTORICAL_MANAGER, LEAGUE, progressStates } from './sampleData';

const COMPARISON = [
  { competition: LEAGUE, you: 'Campeón', history: '2.º' },
  { competition: CUP, you: 'Campeón', history: 'Campeón' },
];

/** Final screen (T4.6) with synthetic data: verdict, comparison and final standings. */
export function RunResultMockup() {
  return (
    <PhoneFrame
      title="Pantalla final"
      description="Veredicto, comparación con la historia y clasificación final."
    >
      <ClubHeader />
      <div className="flex flex-col gap-4 px-gutter py-4">
        <BlockProgress progress={progressStates.finished} />
        <VerdictBanner
          kind="surpassed"
          title={`Superaste a ${HISTORICAL_MANAGER}`}
          description={`Tú: ${LEAGUE} y ${CUP}. ${HISTORICAL_MANAGER}: ${CUP}.`}
          score={81}
          headingLevel={4}
        />
        <Card title="Tú frente a la historia" headingLevel={4}>
          <table className="w-full text-body">
            <thead>
              <tr className="text-caption text-ink-muted">
                <th scope="col" className="py-1 text-left font-semibold">
                  Competición
                </th>
                <th scope="col" className="py-1 text-right font-semibold">
                  Tú
                </th>
                <th scope="col" className="py-1 text-right font-semibold">
                  {HISTORICAL_MANAGER}
                </th>
              </tr>
            </thead>
            <tbody>
              {COMPARISON.map((row) => (
                <tr key={row.competition} className="border-t border-line">
                  <th scope="row" className="py-2 text-left font-normal">
                    {row.competition}
                  </th>
                  <td className="py-2 text-right font-bold text-gold">{row.you}</td>
                  <td className="py-2 text-right text-ink-muted">{row.history}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card title="Clasificación final" headingLevel={4}>
          <MiniStandings competitionName={LEAGUE} rows={finalStandings} />
        </Card>
        <div className="flex flex-col gap-2 pb-2">
          <Button fullWidth>Jugar otra partida</Button>
          <Button fullWidth variant="secondary">
            Compartir resultado
          </Button>
        </div>
      </div>
    </PhoneFrame>
  );
}
