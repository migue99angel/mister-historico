# Validación del contenido: T2.20a

T2.20a conecta el cargador existente con el
[puerto de validación integrado](../changes/CR-T2.20-validation-port.md).
Entrega el adaptador `YamlContentValidator` y el caso de uso `ValidateContent`.
Las reglas de contenido siguen perteneciendo a `load_content_tree`.

## Uso del componente

El adaptador recibe la raíz del contenido al construirse. El caso de uso recibe
un `ContentValidator` y delega la petición y su modo, sin IO directo ni reglas
adicionales:

```python
from pathlib import Path

from mister.catalog.application.validate_content import ValidateContent
from mister.catalog.infrastructure.yaml_validation import YamlContentValidator

validator = YamlContentValidator(Path("content"))
report = ValidateContent(validator).execute(release=False)
```

El ejemplo representa la composición explícita del componente. El cableado
compartido del proyecto llegará en una CR posterior.

## Informes y errores

Antes de cargar, el adaptador comprueba que la raíz sea un directorio y pueda
listarse. Una raíz inexistente, un fichero usado como raíz o un fallo operativo
de acceso producen `ContentValidationUnavailableError`, cuyo código es
`content_validation_unavailable`. También traduce los `OSError` y errores de
codificación que propague el cargador, conservando la excepción original como
causa.

Una vez disponible la raíz, se llama a `load_content_tree(root, release=...)`.
Es la única validación del contenido: esquema, referencias, fuentes, medias y
reglas de release se reutilizan sin duplicarlas. Si lanza
`ContentValidationError`, se traducen **todas** sus incidencias a
`ValidationIssue`, conservando exactamente ruta, campo y mensaje. El informe
de aplicación establece el orden estable y deja `season_count=None` cuando el
contenido es inválido.

Si la carga completa tiene éxito, el contador es el número de temporadas
validadas. Un directorio existente vacío puede devolver un informe válido con
cero temporadas. Ese cero conocido no afirma que haya un catálogo jugable ni
sustituye un contador desconocido por un éxito vacío.

Cada llamada vuelve a leer el contenido, de modo que una corrección posterior
se refleje en el informe siguiente. No se cachean informes entre modos. El
caso de uso devuelve el mismo informe del puerto y deja pasar su error
operativo, sin filtrar objetos de infraestructura hacia su consumidor.

La comprobación de acceso cubre la raíz. El adaptador conserva el recorrido
interno del cargador: no puede reconstruir errores de subdirectorios que
`Path.glob` silencie dentro de él. Endurecer ese recorrido requeriría una
tarea con propiedad del cargador; no se duplica su descubrimiento en esta capa.

## Verificación

`tests/contracts/test_yaml_content_validator.py` aplica la suite integrada
`ContentValidatorContract` al adaptador real. Usa copias temporales del árbol
ficticio de Test FC para los escenarios válido, pendiente e inválido, además
de un directorio vacío y una raíz no disponible. Comparte las mismas aserciones
que el fake; no se modifican sus scripts ni las fixtures globales.

Los tests propios comprueban la traducción completa de diagnósticos de esquema
y de YAML, un fichero obligatorio ausente, cambios entre llamadas, modos
booleanos explícitos, raíces no disponibles y fallos de lectura o codificación.
El caso de uso se prueba con el fake integrado, incluidos contador cero,
contador desconocido, incidencias múltiples y fallo operativo.

El historial conserva los commits separados de rojo observado, implementación
y limpieza. La comprobación local de entrega comprende los tests focales y
`make lint`. La aceptación requiere revisión independiente, CI y las pruebas
completas coordinadas por el orquestador; estas no se dan por ejecutadas en
esta rama sin disponer de sus resultados.

## Trabajo pendiente de T2.20

T2.20a es un componente revisable del catálogo. T2.20 permanece abierta:

- La fase b añadirá `YamlSeasonContentProvider`, el mapeo del catálogo y
  `NamePolicy`, después de estabilizar los contratos de competiciones.
- Una CR de cableado explícita conectará composición, CLI, Makefile y CI.
- `make validate-content` deberá ejecutar la validación real antes de cerrar
  la aceptación global de T2.20.

🤖 Generated with Codex
