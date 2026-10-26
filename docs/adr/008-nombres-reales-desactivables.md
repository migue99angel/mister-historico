# ADR-008 · Nombres reales desactivables

- **Estado:** aceptado para la presentación; cableado de interfaz pendiente de F3/F4.
- **Contexto:** el catálogo conserva el nombre documentado y un alias para jugadores y entrenadores. La identidad estable de cada persona es su ID, no su nombre visible.

## Decisión

`NamePolicy(real_names: bool)` elige el nombre que muestra un presentador: `display_name` si el flag está activo y `alias_name` si está desactivado. La elección se aplica al construir la respuesta o la vista. No altera los DTO del catálogo, el contenido YAML, los identificadores ni las partidas guardadas. La configuración del flag y su conexión con los presentadores pertenecen a las tareas de interfaz y composición posteriores.

## Consecuencias

- La misma temporada y partida pueden mostrarse en ambos modos sin volver a cargar ni modificar datos.
- Los aliases son contenido revisable y obligatorio en el esquema; el modo desactivado no genera nombres al vuelo.
- Un consumidor que muestre nombres debe aplicar la política antes de renderizarlos. La cobertura de esos presentadores se verificará cuando existan.
