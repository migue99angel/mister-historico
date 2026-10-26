# CR-T2.21 · Puerto y CLI de carga del catálogo

## Motivo y propiedad

T2.21a integró migración, persistencia transaccional y proveedor SQL. La CLI no puede importar directamente ese adaptador: el contrato de capas exige un puerto de aplicación y composición en `bootstrap.py`, archivo compartido reservado a una CR.

Esta CR posee los nuevos `catalog/application/load_types.py` y `load_catalog.py`, la ampliación de `catalog/application/ports.py`, el fake y el wrapper `catalog/infrastructure/sqlalchemy/publisher.py`, el ajuste de error operativo en `sqlalchemy/catalog.py`, `bootstrap.py`, el subcomando `load` de `entrypoints/cli/content.py`, su registro en `app.py`, los tests y esta documentación. No cambia el esquema YAML, la API publicada de temporadas ni el contrato de lectura `SeasonContentProvider`.

## Contrato

`CatalogPublisher.load(root: Path) -> CatalogLoadReport` publica una raíz en modo release. El informe inmutable contiene un hash SHA-256, al menos una temporada jugable y `changed`, que es falso cuando el hash ya estaba publicado. `LoadCatalog` delega al puerto sin reglas de IO. Un fake programable y la misma suite de contrato que usa el adaptador SQL comprueban éxito, contenido inválido e indisponibilidad.

`CatalogContentInvalidError` conserva todas las incidencias de validación como `ValidationIssue` de aplicación. El catálogo vacío se rechaza como contenido no publicable aunque `content validate` permita un árbol válido vacío. `CatalogLoadUnavailableError` distingue raíz o base de datos inaccesibles. Una versión singleton ausente es un fallo operativo, no un error del contenido.

## CLI y composición

`mister content load [--root PATH]` publica siempre en modo release y usa la misma resolución de raíz que `validate` y `ratings`. Devuelve salida `0` para carga o ausencia de cambios, `1` para contenido inválido y `2` para origen o base de datos no disponibles. Muestra el hash y el número de temporadas en la primera carga. La segunda informa expresamente «sin cambios».

`bootstrap.py` crea el motor SQL usando `Settings.database_url`, inyecta el adaptador en el caso de uso y cierra el motor al terminar cada invocación. La CLI solo importa aplicación y composición. La carga es un comando que el despliegue puede ejecutar después de migrar; el mecanismo concreto de despliegue se decidirá en F7.

## Comprobación

Las pruebas usan Test FC y Postgres real. Contrastan el contrato tanto con el fake como con SQL, dos invocaciones de CLI, rechazo de texto draft sin perder filas, raíz ausente, versión de base de datos ausente y cierre de recursos. Se exige además `make test`, `make lint`, CI, revisión independiente e integración por rebase.
