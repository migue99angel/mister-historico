import { useState } from 'react';

import { BlockProgress } from '../BlockProgress';
import { Button } from '../Button';
import { Card } from '../Card';
import { DilemmaCard } from '../DilemmaCard';
import { GenericCrest } from '../GenericCrest';
import { MatchLine } from '../MatchLine';
import { MiniStandings } from '../MiniStandings';
import { OptionButton } from '../OptionButton';
import { VerdictBanner } from '../VerdictBanner';
import {
  clubs,
  extraTimeMatch,
  firstBlockStandings,
  lastBlockMatches,
  LEAGUE,
  loopStandings,
  progressStates,
  ROVERS_HISTORICAL_MANAGER,
  specimenDilemmas,
} from './sampleData';
import { Specimen, Variant } from './Specimen';

const [captainComplaint, winterSigning] = specimenDilemmas as [
  (typeof specimenDilemmas)[number],
  (typeof specimenDilemmas)[number],
];

export function ComponentsSection() {
  const [choice, setChoice] = useState<string | null>(null);

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Specimen name="Button" description="Acción principal, secundaria y discreta.">
        <Variant label="Primario">
          <Button>Simular bloque</Button>
        </Variant>
        <Variant label="Secundario">
          <Button variant="secondary">Ver clasificación</Button>
        </Variant>
        <Variant label="Discreto">
          <Button variant="ghost">Volver</Button>
        </Variant>
        <Variant label="Deshabilitado">
          <Button disabled>Deshabilitado</Button>
        </Variant>
        <Variant label="Cargando">
          <Button loading>Simulando…</Button>
        </Variant>
        <Variant label="Ancho completo">
          <Button fullWidth>Empezar</Button>
        </Variant>
      </Specimen>

      <Specimen name="Card" description="Contenedor con título opcional y dos tonos.">
        <Variant label="Con título">
          <Card title="Objetivos de la directiva" eyebrow="Temporada 2000-01" headingLevel={4}>
            <p className="text-body">Terminar entre los cuatro primeros de la {LEAGUE}.</p>
          </Card>
        </Variant>
        <Variant label="Destacada">
          <Card title="Partido clave" tone="highlight" headingLevel={4}>
            <p className="text-body">Final de la Copa Test contra Athletic Ensayo.</p>
          </Card>
        </Variant>
        <Variant label="Sin título">
          <Card>
            <p className="text-body text-ink-muted">Una tarjeta sin título es un contenedor.</p>
          </Card>
        </Variant>
      </Specimen>

      <Specimen name="OptionButton" description="Opción de un dilema: botón de alternancia.">
        <Variant label="Normal">
          <OptionButton label="Respaldar a la directiva en público" marker="A" />
        </Variant>
        <Variant label="Seleccionada">
          <OptionButton label="Fichar al delantero veterano" marker="B" selected />
        </Variant>
        <Variant label="Deshabilitada">
          <OptionButton label="Guardar el dinero para invierno" marker="C" disabled />
        </Variant>
        <Variant label="Seleccionada y bloqueada">
          <OptionButton label="Subir al delantero de la cantera" marker="A" selected disabled />
        </Variant>
      </Specimen>

      <Specimen name="DilemmaCard" description="Dilema con su pregunta y sus opciones.">
        <Variant label="Pendiente (interactivo)">
          <DilemmaCard
            dilemma={winterSigning}
            eyebrow="Dilema 2 de 2"
            headingLevel={4}
            selectedOptionId={choice}
            onSelect={setChoice}
          />
        </Variant>
        <Variant label="Decidido">
          <DilemmaCard
            dilemma={captainComplaint}
            eyebrow="Dilema 1 de 2"
            headingLevel={4}
            selectedOptionId="listen-to-captain"
            disabled
          />
        </Variant>
      </Specimen>

      <Specimen name="MatchLine" description="Resultado con desenlace, prórroga y penaltis.">
        <ul className="divide-y divide-line">
          {[...lastBlockMatches, extraTimeMatch].map((sample) => (
            <li key={`${sample.match.homeName}-${sample.match.awayName}`}>
              <MatchLine
                match={sample.match}
                competitionName={sample.competitionName}
                keyMatchLabel={sample.keyMatchLabel}
                userSide={sample.userSide}
              />
            </li>
          ))}
        </ul>
      </Specimen>

      <Specimen
        name="MiniStandings"
        description="Clasificación corta: sube, baja, se mantiene y tu equipo resaltado."
      >
        <Variant label="Tras varios bloques">
          <MiniStandings competitionName={LEAGUE} rows={loopStandings} />
        </Variant>
        <Variant label="Primer bloque (sin posición previa)">
          <MiniStandings competitionName={LEAGUE} rows={firstBlockStandings} />
        </Variant>
      </Specimen>

      <Specimen name="BlockProgress" description="Progreso de la temporada por bloques.">
        <Variant label="Inicio">
          <BlockProgress progress={progressStates.start} />
        </Variant>
        <Variant label="En juego">
          <BlockProgress progress={progressStates.middle} />
        </Variant>
        <Variant label="Terminada">
          <BlockProgress progress={progressStates.finished} />
        </Variant>
        <Variant label="Destituido">
          <BlockProgress progress={progressStates.sacked} status="sacked" />
        </Variant>
      </Specimen>

      <Specimen name="VerdictBanner" description="Los cuatro veredictos del final.">
        <VerdictBanner
          kind="surpassed"
          title={`Superaste a ${ROVERS_HISTORICAL_MANAGER}`}
          description={`Tú: Liga Test. ${ROVERS_HISTORICAL_MANAGER}: ningún título.`}
          score={81}
          headingLevel={4}
        />
        <VerdictBanner
          kind="matched"
          title="Igualaste la historia"
          description={`Tú y ${ROVERS_HISTORICAL_MANAGER}: Copa Test.`}
          score={64}
          headingLevel={4}
        />
        <VerdictBanner
          kind="below"
          title="Te quedaste por debajo"
          description={`Tú: ningún título. ${ROVERS_HISTORICAL_MANAGER}: Copa Test.`}
          score={38}
          headingLevel={4}
        />
        <VerdictBanner
          kind="sacked"
          title="La directiva te destituyó en enero"
          description="Tu equipo era décimo en la Liga Test."
          headingLevel={4}
        />
      </Specimen>

      <Specimen
        name="GenericCrest"
        description="Escudo generado solo con los colores del club: mismos colores, mismo escudo."
      >
        <ul className="grid grid-cols-4 gap-4">
          {Object.values(clubs).map((club) => (
            <li key={club.name} className="flex flex-col items-center gap-1 text-center">
              <GenericCrest colors={club.colors} label={club.name} size={56} />
              <span aria-hidden="true" className="text-caption text-ink-muted">
                {club.name}
              </span>
            </li>
          ))}
        </ul>
      </Specimen>
    </div>
  );
}
