# Estado físico y lesiones · T2.5

Estos helpers son decisiones **provisionales de diseño de juego**, pendientes de calibración. Los coeficientes no son estadísticas históricas ni asesoramiento médico. No se atribuyen a fuentes externas. El dominio usa únicamente Python y `RandomSource`, sin IO, reloj implícito ni mutaciones de las entradas.

## Reglas provisionales

Para un intervalo de recuperación de `d` días y un partido con `m` minutos efectivos:

```text
F_pre  = min(100, F_anterior + 4 × d)
esfuerzo = low: 0,8 / normal: 0,9 / high: 1
coste  = ceil(12 × m / 90 × esfuerzo)
F_post = max(0, F_pre − coste)
p_lesión = min(1, 0,02 × m / 90 × (1 + (100 − F_pre) / 50))
```

El físico de entrada y salida es el objeto `Fitness` existente (entero 0–100). La recuperación satura en 100 y el desgaste tiene suelo en 0. Los minutos son enteros no booleanos de 0 a 120 por partido: no se pasa el acumulado de un bloque. Con cero minutos no hay desgaste, riesgo ni consumo de azar. La prioridad reduce el desgaste; no altera de nuevo la probabilidad ni las fuerzas del equipo.

La congestión ya está recogida por los días disponibles entre partidos. No se añade otra penalización. Se recupera la diferencia real entre fechas: `end - start`, sin sumar un día por incluir los extremos. La recuperación compone: recuperar de A a B y de B a C equivale a recuperar de A a C, también al saturar. El llamador conserva la fecha a la que corresponde el físico y avanza ese cursor tras cada recuperación; llamar dos veces con el mismo intervalo recuperaría dos veces y no es una operación idempotente. El helper no oculta un cursor ni presupone límites de bloque.

La duración sorteada es de 7, 14 o 28 días, con pesos 0,6 / 0,3 / 0,1. La extracción uniforme de duración se interpreta como `[0; 0,6)`, `[0,6; 0,9)` y `[0,9; 1)`. Una lesión ocurre cuando la extracción de accidente es estrictamente menor que el riesgo.

## API interna para T2.6

Las funciones se importan de `simulation.domain.fitness` o de `simulation.domain.injuries`. No se modifican los contratos públicos.

| Operación | Resultado |
|---|---|
| `recover_fitness(fitness, days)` | Nuevo `Fitness`; días enteros no negativos. |
| `recover_between(fitness, start, end)` | Nuevo `Fitness` sobre la diferencia de fechas; rechaza fechas invertidas. |
| `match_fitness(fitness, minutes, priority)` | Nuevo `Fitness` después de un único partido. |
| `Injury(player_id, date, days, forced=False)` | Intervalo inmutable; `available_on` es el primer día disponible. |
| `injury_risk(fitness, minutes)` | Probabilidad usando el físico **anterior al partido**, ya recuperado. |
| `simulate_injury(rng, fixture_id, player_id, on_date, *, fitness, minutes)` | `Injury` accidental o `None`; los dos últimos argumentos son nominales. |
| `injured_until(player_id, injuries, on_date)` | Fin más tardío entre los intervalos activos de ese jugador, o `None`. |
| `apply_injuries(squad, injuries, on_date)` | Nueva tupla de `SimPlayer` con los indicadores `injured` proyectados para la fecha. |

Las fechas son `datetime.date`, sin aceptar `datetime.datetime`. Los errores de validación producen `InvalidValueError`: minutos o días booleanos, fraccionarios o negativos; lesiones de cero días; prioridad, identificadores o físico sin su tipo de dominio; fecha de retorno fuera del calendario. Un número enorme de días de recuperación satura sin pasar por un `float` ni construir un `timedelta`. Una lesión enorme se rechaza antes de construirlo. No se inventan fechas cuando el calendario no permite representar el final.

## Disponibilidad e intervalos

Una lesión que empieza en `d` y dura `n` días impide jugar en `[d, d+n)`. El jugador está disponible **desde `d+n`, inclusive**. `injured_until` mantiene esa semántica del contrato publicado; no representa el último día de ausencia.

Las lesiones forzadas se construyen con `forced=True`, antes de seleccionar la alineación, sin sorteo ni dependencia de la semilla. Aunque se pase la cronología completa, una lesión futura no actúa antes de su fecha. Si coinciden varias ausencias activas se toma el final más tardío. Los intervalos separados no se funden: una ausencia de los días 1–2 y otra de los días 6–7 dejan disponibles los días 3–5.

`apply_injuries` trata la cronología recibida como autoritativa y completa. La tupla conserva todas las ausencias iniciales, forzadas y accidentales aplicables, incluidas las ya terminadas. Solo los intervalos activos determinan el indicador del día. Un indicador inicial `injured=True` sin ningún intervalo ya iniciado para ese jugador se rechaza: un booleano no permite deducir su fecha de alta. Un intervalo vencido sí permite retirar el indicador al llegar la fecha de retorno. El llamador es responsable de que ese historial explique el estado inicial; el helper no reconstruye el pasado desde un booleano.

La plantilla debe tener identificadores distintos. Un evento referido a alguien que no está en la plantilla aplicable se rechaza, sin fabricar jugadores. Con traspasos, T2.6 debe determinar qué eventos pertenecen a la plantilla de la fecha antes de llamar al helper; esta tarea no resuelve el registro de plantillas.

## Azar estable

Por participante se deriva exactamente una vez:

```python
leaf = rng.stream("match", str(fixture_id), "injury", str(player_id))
accident = leaf.random()
duration = leaf.random()
```

Siempre se consumen ambos números, incluso si no ocurre una lesión. No hay subclaves adicionales ni un flujo compartido entre jugadores. Una modificación en el orden o número de jugadores no desplaza sus sorteos. Con cero minutos no se deriva siquiera el flujo. El llamador debe simular cada pareja partido/jugador una vez con los minutos totales, incluidos los de prórroga: volver a solicitar la misma hoja reinicia su secuencia según ADR-005.

## Secuencia de integración

1. Recuperar el físico desde su fecha efectiva hasta la fecha del partido, avanzando el cursor temporal una sola vez.
2. Traducir los `ForcedInjuryDTO` aplicables a `Injury(..., forced=True)` y conservar los intervalos iniciales explícitos. El dominio no importa los DTO de aplicación.
3. Ejecutar `apply_injuries` con todas las ausencias aplicables antes de `select_lineup`.
4. Obtener los minutos efectivos de cada jugador. Pasar su `F_pre` a `simulate_injury` y conservar toda lesión resultante; aplicar `match_fitness` sobre ese mismo `F_pre`.
5. Al cierre del bloque, recuperar únicamente los días restantes desde el cursor y consultar `injured_until` en la fecha de cierre. T2.6 traduce esa fecha a `PlayerStateDTO.injured_until` y suma los minutos del bloque fuera de estos helpers.

Si T2.6 recibe únicamente una fecha `injured_until` inicial, conoce el intervalo restante desde la fecha del snapshot hasta el primer día disponible; debe representarlo explícitamente, sin inventar una fecha histórica de inicio. `SimPlayer.injured` sigue siendo un booleano para la selección; no se altera su semántica pública.

Las pruebas usan datos sintéticos de Test FC 2000-01: composición de recuperación, prioridades y congestión; cotas y entradas inválidas; riesgo monótono; bandas de duración y dos extracciones por participante; aislamiento por jugador, partido y orden; lesiones forzadas con cualquier semilla; fecha exacta de retorno, solapamientos y huecos entre intervalos.
