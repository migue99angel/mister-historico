# CR · Exclusión de ellipsis en la cobertura

## Problema

`tool.coverage.report.exclude_also` contenía la expresión no anclada
`\.\.\.`. Además de cuerpos de stubs, coincidía con anotaciones ejecutables
como `tuple[int, ...]`. Cuando la coincidencia aparece en la cabecera de una
función, coverage excluye también su cuerpo: podían desaparecer tanto líneas
ejecutables como ramas pendientes del denominador de la medición.

Las cifras comunicadas anteriormente corresponden a la configuración amplia
vigente en aquellas ejecuciones. Esta CR corrige el alcance de la exclusión;
las cifras nuevas requieren ejecutar de nuevo las suites con la configuración
corregida. No se sustituyen las mediciones anteriores por resultados que aún
no se hayan comprobado.

## Cambio

La expresión queda anclada al principio y al final de la línea. Solo admite
una sentencia `...` aislada, con espacios o tabuladores alrededor. Mantiene
la exclusión de los cuerpos de stubs y deja de coincidir con anotaciones de
tuplas, literales o expresiones que simplemente contienen tres puntos.

No cambian los umbrales: cobertura global del backend ≥ 85 %, y líneas y
ramas de dominio/aplicación ≥ 95 %. Tampoco se modifican las otras exclusiones,
los scripts de comprobación ni dependencias.

## Regresión y verificación

`tests/architecture/test_coverage_configuration.py` ejecuta el coverage instalado
en procesos separados, cargando el `pyproject.toml` real. Mide un módulo temporal
con una función anotada `tuple[int, ...]`, una rama deliberadamente sin ejecutar
y un stub cuyo cuerpo es `...`. Comprueba el informe JSON real:

- La función ejecutable y sus líneas siguen contándose.
- La línea y la rama no ejecutadas aparecen como pendientes.
- El cuerpo del stub continúa excluido.

El rojo observado con la configuración anterior omitía toda la función y
presentaba el módulo como cubierto al 100 %. Con la expresión corregida pasan
ambos tests y se conserva la rama pendiente. La prueba no compara cadenas de
configuración ni reconstruye el comportamiento de coverage.

La verificación local de esta CR comprende esos tests focales y `make lint`.
La ejecución global coordinada por el orquestador sobre el árbol que combina
liga, copas y esta corrección deberá establecer las nuevas cifras y comprobar
los mismos umbrales. Si aparecen huecos en otros módulos, su corrección
necesitará coordinarse con su tarea propietaria.

🤖 Generated with Codex
