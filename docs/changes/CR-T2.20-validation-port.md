# CR-T2.20 · Puerto de validación del catálogo

Contrato implementado a partir de la planificación de Astra, en paralelo al cierre de competiciones y pendiente de revisión independiente e integración. Debe integrarse antes del adaptador de validación de T2.20.

## Contrato

`ContentValidator.validate(*, release: bool) -> ContentValidationReport` es un puerto de IO de `catalog/application/ports.py`. Su adaptador se construirá con una raíz; el puerto no publica tipos de infraestructura.

En `catalog/application/validation_types.py`, valores inmutables propios:

- `ValidationIssue(path: str, field: str, message: str)`: ruta relativa POSIX, campo vacío para un problema de fichero completo y mensaje no vacío.
- `ContentValidationReport(issues: tuple[ValidationIssue, ...], season_count: int | None)`: `valid` se deriva de la ausencia de incidencias. Éxito con contador entero no negativo; informe inválido con contador desconocido (`None`). Orden estable por ruta, campo y mensaje.
- `ContentValidationUnavailableError(DomainError)`, código `content_validation_unavailable`, para fallos operativos de lectura. Los errores de contenido se devuelven acumulados en el informe; no filtrar `ContentIssue` ni `ContentValidationError` de infraestructura.

Los tres tipos se reexportan junto al puerto en `catalog/application/ports.py` y su `__all__`. No se modifican los puertos existentes ni la API publicada de temporadas.

Las rutas son texto POSIX relativo y canónico: no se admiten rutas absolutas, segmentos `..`, barras inversas, caracteres NUL ni formas que requieran normalización silenciosa (`./`, separadores repetidos o barra final). `.` identifica una incidencia de la raíz, como ya hace el cargador. El campo es texto y puede estar vacío; el mensaje debe contener texto no blanco. Estos valores no leen el sistema de ficheros.

El informe valida que las incidencias sean una tupla de `ValidationIssue`. Las ordena por `(path, field, message)` sin eliminar duplicados ni modificar la entrada. `valid` es una propiedad derivada, no un argumento del constructor. Un informe inválido siempre deja `season_count=None`: no publica el tamaño parcial del árbol ni sustituye desconocido por cero.

El modo normal conserva las reglas de desarrollo; release añade los requisitos ya existentes, sin suavizarlos. El adaptador posterior reutilizará `load_content_tree` y traducirá el resultado. Un árbol vacío puede ser válido con cero temporadas: no equivale a catálogo jugable. Las anclas actuales están fuera del recorrido de temporadas del cargador.

## Propiedad y aceptación

Nuevo módulo de tipos; ampliación del puerto y exportaciones pertinentes; fake programable en `catalog/infrastructure/in_memory/content_validation.py`; suite reutilizable del contrato, tests de tipos y este documento. Sin editar `application/api.py`, esquemas, CLI, bootstrap, Makefile ni workflows.

El fake devuelve informes o errores preconfigurados según el modo. No lee YAML ni duplica algoritmos de validación. Suite de éxito, varias incidencias, diferencia desarrollo/release, repetibilidad y error operativo; se reutilizará contra el adaptador real. TDD con rojo observado y commits separados; lint, tipos y arquitectura en verde. Revisión independiente Sol y CI antes de rebase-merge.

`InMemoryContentValidator` recibe un mapa de modos booleanos a informes o errores de aplicación y copia ese mapa. Cada llamada devuelve el informe programado o lanza el error operativo programado; no consume resultados. Un modo sin programación, un modo no booleano o un resultado de otro tipo se rechazan con `InvalidValueError`, evitando un éxito implícito del fake. Un error en release no cambia la respuesta normal.

## Suite reutilizable

`tests/contracts/suites/content_validator.py` define `ContentValidatorContract`. Cada implementación proporciona la fixture `make_validator`, una factoría de los escenarios `valid`, `empty`, `invalid`, `pending` y `unavailable`. La ejecución actual está en `tests/contracts/test_content_validators.py` para el fake.

El adaptador YAML posterior reutilizará las mismas aserciones: un árbol Test FC válido con una temporada; un directorio vacío conocido; dos campos desconocidos `unexpected` en `fixtures.yaml` y `texts.yaml`; el primer texto en estado draft; y un fallo operativo de lectura. Los diagnósticos esperados coinciden con los mensajes actuales del cargador. La suite no importa YAML, Pydantic ni tipos de infraestructura.

Las pruebas de tipos están en `tests/catalog/test_validation_types.py`. Cubren rutas, textos, contador desconocido frente a cero, exclusión de booleanos como contadores, orden estable, duplicados e inmutabilidad. El ciclo TDD conserva un commit de tests con rojo observado por ausencia de los tipos y del puerto, seguido de implementación y limpieza.

## Límites y validación de entrega

Después, T2.20 implementará adaptador y caso de uso. El cableado compartido irá en una tarea CR explícita: composición, registro CLI, Makefile y workflow. T2.20 no se declara cerrada hasta que `make validate-content` ejecute la validación real.

La entrega local comprueba las pruebas focales y `make lint`. La aceptación de integración requiere además revisión independiente, CI y la ejecución completa coordinada con la CR de competiciones. Este documento no declara ejecutada esa suite conjunta antes de disponer de sus resultados.

🤖 Generated with Codex
