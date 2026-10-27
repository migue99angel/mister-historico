# CR-T2.10 · Coeficiente UEFA como último desempate de grupos

## Motivo

El artículo 7.06.h del [reglamento UEFA 2012-13](https://www.eurocups.ru/docs/cl-12_13-rules.pdf)
sitúa el coeficiente acumulado del club y su federación durante cinco temporadas
después de la diferencia y los goles generales. El vocabulario actual del
catálogo y del motor termina en `goals_for`; si dos clubes siguen empatados,
el motor deja la clasificación sin resolver. Esto impide representar de forma
completa la fase de grupos de la Champions 2012-13 en T2.10.

La [lista contemporánea de UEFA](https://www.uefa.com/uefachampionsleague/news/01fe-0e7e4bbf672d-abefce7f49b8-1000--uefa-champions-league-list-of-participants/)
publica el coeficiente con tres decimales para los 32 participantes. Su columna
`Position` no es el coeficiente: Chelsea figura primero por ser el vigente
campeón, aunque Barcelona tiene más puntos. El desempate usará el valor numérico.

## Contrato propuesto

- Añadir `club_coefficient` al vocabulario de desempates de grupos en el esquema,
  el DTO de Catalog, la entrada de Simulation y el motor. No aplicarlo a ligas
  domésticas, que tienen reglamentos propios.
- Publicar en la etapa de grupos un valor por participante, con `club_season`,
  `milli_points`, `sources` y `verify`. `milli_points` representa los tres
  decimales de UEFA como entero exacto: `121.837` se guarda como `121837`.
  Rechazar duplicados, valores negativos, clubes ajenos y cobertura incompleta
  cuando se configure el criterio.
- Propagar los valores al motor mediante DTOs inmutables. Si falta un valor
  necesario para resolver un empate, fallar de forma explícita; el orden estable
  por identificador es solo presentación y no otorga una plaza deportiva.
- Mantener `None` y `verify: pending` durante la investigación. La validación
  release exige 32 valores verificados y con fuente para la etapa del piloto.
- Test FC conservará sus reglas sintéticas actuales salvo una prueba específica
  del nuevo criterio, con coeficientes inventados únicamente para el test.

## Alcance y puertas

Esta CR cambia el esquema y las API publicadas; precede a la integración de
T2.10. T2.10 añadirá los 32 valores oficiales, citará la URL por registro y
configurará `club_coefficient` al final de la lista UEFA. Se requiere TDD con
commits separados, prueba contractual del proveedor YAML, tests del motor,
`make test`, `make lint`, CI y revisión independiente antes de integrar.

El artículo 7.06.e se corrige en la CR de reaplicación anterior. Esta CR no
modifica calendarios, marcadores ni el reglamento de las competiciones españolas.
