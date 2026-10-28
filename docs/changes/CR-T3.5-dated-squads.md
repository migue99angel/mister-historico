# CR-T3.5: plantillas por fecha en la simulación

## Problema

El contrato anterior enviaba al motor una plantilla efectiva fija para todo el bloque.
Catalog conserva `joined_on` y `left_on`, mientras Game registra traspasos efectivos; al
simular se perdía cuándo pertenecía cada jugador a cada equipo. La plantilla de referencia
histórica debe seguir fijando la normalización de fuerza, pero cada partido debe usar la
plantilla efectiva de su fecha.

## Contrato

`BlockSimulationRequest` y `BlockSimRequest` añaden los campos opcionales
`squad_memberships` y `player_pool`. Los dos son `None` para solicitudes antiguas; las
solicitudes fechadas deben proporcionar ambos como tuplas. Cada `SquadMembership` /
`SquadMembershipInput` contiene jugador, equipo y fechas de entrada y salida inclusivas; `None`
indica un extremo abierto. El pool contiene una sola entrada mutable por jugador, con media,
moral, condición, lesión inicial y marca de minutos juveniles.

Se rechazan pares de campos incompletos, jugadores duplicados en el pool, intervalos
solapados, referencias a jugadores fuera del pool y equipos desconocidos. Una plantilla rival
agregada no se puede sustituir parcialmente por una plantilla de jugadores; un mercado o
propietario exterior se representa sin intervalo activo en los equipos simulados. La entrada
de Game valida identidad, tipos, pareja de campos, IDs únicos y solapamientos antes de cruzar
el ACL.

## Comportamiento

El ACL traduce memberships y estados del pool sin consultar Catalog en vivo. Simulation mantiene
las referencias originales de temporada para calcular fuerza normalizada, recupera la condición
y las lesiones de todos los jugadores entre fechas y selecciona los jugadores activos por equipo en
la fecha de cada fixture. El jugador que entra o sale conserva sus estados en el pool; un
traspaso no juega partidos externos ni recibe fatiga por ellos. Lesiones forzadas y requisitos
juveniles pueden referirse a cualquier jugador del pool, y estos últimos solo cuentan con
oportunidades en fechas en las que pertenecen a la plantilla propia.

La respuesta incluye el estado al cierre de cada jugador del pool, incluso si ya salió de la
plantilla o todavía no ha entrado. En el siguiente bloque el llamador puede devolver ese pool
con `state_as_of` para continuar recuperación, lesión y condición. Las solicitudes legacy
conservan el comportamiento de plantilla fija y la forma de respuesta anterior.

## Verificación

Los tests usan únicamente Test FC sintético. `tests/game/test_dated_squads_mapping.py` cubre el
ACL, compatibilidad legacy y validación del contrato; `tests/game/test_simulator_dtos_mapping.py`
actualiza la correspondencia exhaustiva de DTOs; `tests/simulation/test_dated_squads.py` cubre
intervalos inclusivos, traspasos efectivos, entradas y salidas, referencias inválidas, lesiones
futuras (también de un rival que entra después), oportunidad juvenil y continuidad física entre
bloques. Las suites existentes de mapeo Game y simulación verifican la compatibilidad legacy y
las referencias de fuerza permanecen fijas durante todos los casos.
