# T2.21a · Catálogo publicado en PostgreSQL

El adaptador SQL guarda una instantánea de cada `PlayableSeasonDTO` en `catalog_seasons` (JSONB) y un hash global en `catalog_version`. La migración `0002_catalog` crea ambas tablas. El formato JSON lleva etiquetas explícitas de dataclass, enum y fecha: varios efectos tienen los mismos campos y una conversión JSON sin etiquetas los confunde.

`SqlCatalogLoader.load(root)` valida el contenido en modo release mediante el proveedor YAML integrado. Rechaza una raíz sin temporadas jugables para evitar que una carga desde un directorio vacío borre el catálogo publicado. El hash SHA-256 incluye las rutas y los bytes de todos los YAML, también fuentes y texto editorial. Si coincide con la versión publicada, no escribe en la base de datos. Si cambia, sustituye todas las temporadas y el hash dentro de una sola transacción. Un fallo después del borrado revierte tanto filas como versión.

`SqlSeasonContentProvider` implementa la suite publicada del puerto sobre Postgres real. Las pruebas comprueban equivalencia completa con Test FC, repetibilidad, orden y error de temporada ausente. También contrastan que una segunda carga conserva la versión física de la fila, que cambiar una media válida cambia hash y DTO, y que contenido inválido o un fallo de inserción conservan el catálogo anterior.

En esta máquina, siete cargas iniciales de Test FC sobre Postgres de testcontainers dieron **192,18–218,85 ms**, con mediana **203,07 ms**. La medición excluye el arranque del contenedor y la migración; no garantiza ese tiempo en otros equipos.

La CLI `mister content load` y el cableado de despliegue quedan para una CR posterior: `bootstrap.py` y la composición compartida no pertenecen a esta parte de T2.21. La migración es manual; conectar la metadata a la generación automática de Alembic también requiere propiedad expresa de `migrations/env.py` si se decide hacerlo.
