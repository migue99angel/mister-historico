# CR-T2.12 · Ubicación del inventario de participantes

## Motivo

T2.12 pide publicar primero `participants.md` para que T2.16 prepare las
plantillas rivales. El validador release considera cualquier directorio de
`content/seasons/` una temporada jugable y exige `season.yaml`,
`fixtures.yaml`, `standings.yaml`, `dilemmas.yaml` y `texts.yaml`. Un directorio
que solo contenga el inventario documental falla `make validate-content`.

## Cambio de propiedad

El primer entregable de T2.12 vive en
`docs/content/real-madrid-2012-13-participants.md`. T2.12 es dueño de ese
documento y de `fixtures.yaml` y `standings.yaml` dentro de la temporada.
T2.10 y T2.16 usarán los identificadores publicados. La lista es evidencia de
investigación, no un fichero que el juego cargue.

No cambia el esquema ni el validador. `content/seasons/real-madrid-2012-13/`
se creará cuando haya suficientes YAML para validarlo.
