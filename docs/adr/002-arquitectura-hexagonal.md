# ADR-002 · Arquitectura hexagonal y su verificación automática

- **Estado:** Aceptada
- **Fecha:** 2026-10-22
- **Relacionado con:** [PLAN](../PLAN.md) §3.2, §4 y §6 · [ADR-001](./001-monorepo-y-stack.md) · [ADR-003](./003-contextos-delimitados.md) · [ADR-011](./011-arquitectura-frontend.md)

## Contexto

El valor del proyecto está en reglas de negocio que tienen que ser exactas y fáciles de probar: el motor determinista, los efectos de los dilemas, la directiva y la destitución, la puntuación. Esas reglas no deberían saber nada de HTTP, de la base de datos ni del formato YAML del contenido.

Además, el código lo escriben muchos agentes en paralelo, cada uno con su tarea y sus ficheros (PLAN §6). Un agente con prisa tiende a importar lo que tiene a mano: una sesión de SQLAlchemy en un servicio de dominio, un modelo de Pydantic en una entidad. Un error así no se ve en la revisión de una PR, pero con el tiempo acopla todo el sistema. Las reglas de capas tienen que **comprobarse en la CI**, no depender de la buena voluntad.

Por último, la estrategia de testing (PLAN §4) se basa en **fakes en memoria antes que mocks** y en **suites de contrato por puerto**. Eso solo funciona si cada dependencia externa está detrás de un puerto bien definido.

## Decisión

Cada contexto del backend (`backend/src/mister/<contexto>/`) se organiza en tres capas, más un `shared_kernel/`, unos `entrypoints/` y un composition root:

- **`domain/`**: entidades, value objects, servicios de dominio y eventos. **Python puro** con `dataclasses` (inmutables cuando son VOs) y la biblioteca estándar. **Sin Pydantic**, ni FastAPI, ni SQLAlchemy, ni Redis. El dominio no hace IO ni llama a puertos de infraestructura: recibe lo que necesita ya calculado (por ejemplo, `advance_block` recibe el resultado del simulador). Sí puede definir, en `domain/ports.py`, **protocolos de estrategias puras sin IO** (como `GoalModel` o `MatchSimulator` en `simulation`) y recibirlas por parámetro, igual que recibe el `RandomSource` del shared kernel.
- **`application/`**: casos de uso (comandos y consultas), DTOs y **puertos de IO** (repositorios, proveedores de contenido, renderizadores, `UnitOfWork`, sumideros de eventos…), definidos con `typing.Protocol` en `ports.py`. Orquesta el dominio y los puertos dentro de una unidad de trabajo. Además, `application/api.py` es la **API publicada** del contexto: DTOs y fachada, lo único que otro contexto puede importar.
- **`infrastructure/`**: adaptadores que implementan los puertos (SQLAlchemy, YAML con Pydantic, Pillow, Redis…) y los fakes en memoria (`in_memory/`).
- **`entrypoints/`**: FastAPI (routers y mapeo de `DomainError` a `problem+json`) y la CLI con typer. Solo invocan casos de uso.
- **`shared_kernel/`**: IDs tipados, `Seed`, `DomainError`, `DomainEvent` y los puertos transversales `RandomSource`, `Clock` y `EventBus`. El dominio recibe `RandomSource` por parámetro; `Clock` y `EventBus` los usan los casos de uso.
- **`bootstrap.py`**: **composition root**. Es el único sitio que instancia adaptadores y los inyecta en los casos de uso.

Reglas de dependencia (PLAN §3.2), comprobadas con **`import-linter`** en `make lint` y en la CI:

1. `domain` solo importa la biblioteca estándar y `shared_kernel`.
2. `application` importa `domain` y define puertos; no importa `infrastructure`.
3. `infrastructure` implementa puertos; solo la importa `bootstrap.py` (y los tests).
4. Un contexto no importa el `domain` de otro. Solo puede importar su **API publicada** (`<contexto>/application/api.py`: DTOs y fachada), y siempre desde un adaptador de su propia `infrastructure` (ACL). Por ejemplo, `game/infrastructure/simulation_adapter.py` importa `mister.simulation.application.api` y nunca `mister.simulation.domain`.
5. `entrypoints` solo llama a `application`.

Los contratos de `import-linter` viven en la sección `[tool.importlinter]` de `backend/pyproject.toml` y se escriben de forma genérica sobre `mister.*.domain`, `mister.*.application` y `mister.*.infrastructure`, de modo que un contexto nuevo queda cubierto sin tocar la configuración. Los tests de `backend/tests/architecture/` demuestran que una violación hace fallar el linter.

En el frontend se aplica una versión ligera de las mismas reglas con **`dependency-cruiser`** (detalle en el [ADR-011](./011-arquitectura-frontend.md)); su composition root es `frontend/src/app/` (incluido `main.tsx`), lo único que importa `infrastructure/`.

Cada puerto tiene **un fake en memoria y una suite de contrato parametrizable** (por ejemplo, `run_repository_contract(make_repo)`) que se ejecuta contra el fake y contra el adaptador real. Así el fake no puede mentir.

## Alternativas consideradas

- **Arquitectura por capas clásica (routers → servicios → modelos del ORM).** Es más rápida de arrancar y es lo habitual en FastAPI, pero ata el dominio al ORM: los tests de reglas de negocio necesitan base de datos y el motor dejaría de ser puro y determinista.
- **Clases base abstractas (`abc.ABC`) para los puertos.** Obligan a heredar, de modo que los adaptadores y los fakes dependen de la jerarquía de la aplicación. `typing.Protocol` permite el tipado estructural: `mypy --strict` comprueba que el adaptador cumple el puerto sin acoplarlo por herencia.
- **Pydantic en el dominio.** Daría validación y serialización gratis, pero mete una dependencia externa pesada en el núcleo, mezcla las reglas de negocio con el formato de entrada y salida, y complica la inmutabilidad y el rendimiento del motor. Pydantic se queda en los bordes: el esquema de contenido (infraestructura del catálogo) y los modelos de la API (entrypoints).
- **Un contenedor de inyección de dependencias (dependency-injector, punq…).** Añade magia y una dependencia más para un grafo de objetos pequeño. Un `bootstrap.py` explícito se lee de arriba abajo y es fácil de revisar.
- **Confiar en la revisión de código para respetar las capas.** No escala con agentes en paralelo: el coste de una violación se paga meses después y nadie la ve al revisar un diff.

## Consecuencias

- **Positivas:**
  - El dominio se prueba sin IO y en milisegundos, con Hypothesis, y la mutación (mutmut) tiene sentido sobre él.
  - Cambiar un adaptador (Poisson por Dixon-Coles detrás de `GoalModel`, YAML por SQL detrás de `SeasonContentProvider`) no toca el dominio ni los casos de uso.
  - Los agentes de distintas tareas trabajan contra puertos congelados en la F1 y no se pisan.
  - La CI rechaza las violaciones de capas, así que las reglas no se degradan con el tiempo.
- **Negativas y trade-offs:**
  - Más ficheros y más código de traducción (DTOs, mapeadores entre el modelo de dominio y el de persistencia o la API). Es el precio de mantener el dominio limpio.
  - Hace falta disciplina para no convertir `application` en un cajón de lógica de negocio: las reglas van en el dominio.
  - Los fakes y las suites de contrato son código que también hay que mantener.
  - La regla 4 es estricta: todo lo que un contexto ofrece a otro tiene que pasar por su `application/api.py`, con DTOs propios y no con sus VOs de dominio. Eso duplica algunos tipos (por ejemplo, los VOs del motor y los DTOs de `SeasonSimInput`), a cambio de poder cambiar el dominio interno sin romper a los consumidores.
  - La frontera entre «estrategia pura» (protocolo en `domain/ports.py`) y «puerto de IO» (protocolo en `application/ports.py`) exige criterio: si la implementación puede tocar red, disco, base de datos o el reloj, es un puerto de aplicación.
- **Seguimiento:** cualquier excepción a estas reglas se documenta con un comentario junto al contrato correspondiente en `[tool.importlinter]` de `backend/pyproject.toml` y, si es estructural, con un ADR nuevo.
