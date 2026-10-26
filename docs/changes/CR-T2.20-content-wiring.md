# CR-T2.20 · Cableado de la validación del catálogo

## Motivo y propiedad

T2.20a entregó el caso de uso `ValidateContent` y el adaptador `YamlContentValidator`, y T2.20b entregó el proveedor YAML de temporadas. El contrato de F1 reserva los archivos compartidos a una CR. Esta CR habilita su uso desde la CLI, `Makefile` y CI sin cambiar puertos, DTO, esquemas ni reglas de validación.

Propiedad de esta CR: `backend/src/mister/bootstrap.py`, `backend/src/mister/entrypoints/cli/app.py`, el nuevo `backend/src/mister/entrypoints/cli/content.py`, `Makefile`, `.github/workflows/content.yml`, sus pruebas y esta documentación. `bootstrap.py` sigue siendo el único lugar que construye el adaptador de infraestructura; la CLI solo llama al caso de uso.

## Comportamiento

`mister content validate [--release] [--root PATH]` valida toda la raíz y muestra todas las incidencias en el orden estable del informe. Sin `--root`, busca `./content` y después el `content/` del repositorio, igual que la herramienta de medias. El modo normal permite datos pendientes; `--release` aplica las restricciones de publicación del cargador existente.

Los códigos de salida distinguen éxito (`0`), contenido inválido (`1`) y raíz no disponible (`2`). El resumen de éxito incluye el número real de temporadas. Un árbol vacío puede ser válido, pero se informa expresamente como `0 temporadas jugables (catálogo vacío)`; ejecutar el comando con éxito sobre `content/` todavía no acredita que exista el piloto del Real Madrid.

`make validate-content` usa la raíz `content/` del proyecto en modo normal. El job `content.yml` instala el backend con las versiones fijadas de Python y uv y ejecuta el mismo comando en modo release. Sus rutas de activación incluyen contenido, catálogo, CLI, composición, bloqueo de dependencias y `Makefile`.

## Comprobación y límites

Las pruebas de CLI usan Test FC ficticio y cubren release válido, texto draft, incidencias múltiples, raíz ausente, árbol vacío y resolución de raíz por defecto. La integración exige además `make validate-content`, `make test`, `make lint`, CI y revisión independiente. No se añaden datos históricos en esta CR. La persistencia SQL sigue en T2.21 y el piloto real en T2.10–T2.16.
