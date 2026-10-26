# CR · Barras inversas literales en rutas POSIX de validación

## Motivo

El cargador puede diagnosticar un fichero POSIX llamado `clubs/bad\name.yaml`.
En POSIX, la barra inversa es parte literal del nombre; el separador es `/`.
La prohibición anterior de cualquier barra inversa en `ValidationIssue.path`
impedía traducir ese diagnóstico y lanzaba `InvalidValueError` en su lugar.

Esta CR corrige la restricción de barras inversas descrita en la
[CR del puerto de validación](CR-T2.20-validation-port.md). La firma del puerto,
los informes y las reglas del cargador se conservan.

## Decisión

`ValidationIssue` acepta barras inversas como caracteres literales de una ruta
POSIX y conserva exactamente el texto recibido. No las convierte en `/`, no
interpreta separadores de otro sistema y no reescribe los diagnósticos.

- `clubs/bad\name.yaml` identifica un fichero dentro de `clubs`.
- `seasons\season.yaml` y `..\season.yaml` tienen un único componente POSIX.
- `../season.yaml` sigue rechazándose porque contiene un segmento `..`.

Siguen rechazándose las rutas absolutas POSIX, los segmentos `..`, los
caracteres NUL y las formas no canónicas, como `./season.yaml`, separadores `/`
repetidos o una barra final. Se mantienen las demás invariantes de textos,
inmutabilidad, contador conocido frente a desconocido y orden del informe.

## Regresión y comprobación

Los tests de tipos sustituyen el caso que interpretaba la barra inversa como
separador por casos de preservación literal. La nueva prueba de compatibilidad
crea un fichero YAML malformado con ese nombre en una raíz temporal, obtiene
su incidencia real de `load_content_tree` y la traduce al informe de aplicación
sin cambiar ruta, campo ni mensaje. No importa el adaptador T2.20a pendiente
ni modifica el cargador o las fixtures compartidas.

Se observó el rojo antes del arreglo: cinco casos fallaban por
`InvalidValueError`. La corrección elimina únicamente la prohibición de barras
inversas; los 74 tests focales de tipos, compatibilidad y contrato del fake
pasan. La entrega añade `make lint`; la integración requiere revisión
independiente y CI. No se declara ejecutada una suite completa local.

Esta CR debe integrarse antes de T2.20a. Después, el adaptador real añadirá una
regresión para el mismo nombre sobre el contrato corregido.

🤖 Generated with Codex
