# CR-T2.20 · Puerto de validación del catálogo

Planificación de Astra. Se implementa en paralelo al cierre de competiciones, sin modificar sus APIs ni esquemas. Debe integrarse antes del adaptador de validación de T2.20.

## Contrato

`ContentValidator.validate(*, release: bool) -> ContentValidationReport` es un puerto de IO de `catalog/application/ports.py`. Su adaptador se construirá con una raíz; el puerto no publica tipos de infraestructura.

En `catalog/application/validation_types.py`, valores inmutables propios:

- `ValidationIssue(path: str, field: str, message: str)`: ruta relativa POSIX, campo vacío para un problema de fichero completo y mensaje no vacío.
- `ContentValidationReport(issues: tuple[ValidationIssue, ...], season_count: int | None)`: `valid` se deriva de la ausencia de incidencias. Éxito con contador entero no negativo; informe inválido con contador desconocido (`None`). Orden estable por ruta, campo y mensaje.
- `ContentValidationUnavailableError(DomainError)`, código `content_validation_unavailable`, para fallos operativos de lectura. Los errores de contenido se devuelven acumulados en el informe; no filtrar `ContentIssue` ni `ContentValidationError` de infraestructura.

El modo normal conserva las reglas de desarrollo; release añade los requisitos ya existentes, sin suavizarlos. El adaptador posterior reutilizará `load_content_tree` y traducirá el resultado. Un árbol vacío puede ser válido con cero temporadas: no equivale a catálogo jugable. Las anclas actuales están fuera del recorrido de temporadas del cargador.

## Propiedad y aceptación

Nuevo módulo de tipos; ampliación del puerto y exportaciones pertinentes; fake programable en `catalog/infrastructure/in_memory/content_validation.py`; suite reutilizable del contrato, tests de tipos y este documento. Sin editar `application/api.py`, esquemas, CLI, bootstrap, Makefile ni workflows.

El fake devuelve informes o errores preconfigurados según el modo. No lee YAML ni duplica algoritmos de validación. Suite de éxito, varias incidencias, diferencia desarrollo/release, repetibilidad y error operativo; se reutilizará contra el adaptador real. TDD con rojo observado y commits separados; lint, tipos y arquitectura en verde. Revisión independiente Sol y CI antes de rebase-merge.

Después, T2.20 implementará adaptador y caso de uso. El cableado compartido irá en una tarea CR explícita: composición, registro CLI, Makefile y workflow. T2.20 no se declara cerrada hasta que `make validate-content` ejecute la validación real.
