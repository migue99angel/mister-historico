# Auditoría del consumo de los agentes

Herramienta local para medir cuánto trabajo integrado y probado sale de cada ventana de cuota de Claude Code y de Codex. No es parte del juego ni un servicio: lee los registros que ambas herramientas guardan en esta máquina y escribe métricas agregadas fuera del repositorio.

## Uso

```bash
make usage        # recoge y escribe en ~/.local/share/mister-historico/agent-usage/
make usage-test   # tests de la herramienta (datos sintéticos)
```

Necesita `npx` (ejecuta `ccusage@20.0.45`) y `gh` autenticado. `--no-ccusage` y `--no-github` permiten trabajar sin ellos: los costes y los datos de PR quedan entonces como no disponibles, nunca como cero.

Ficheros que escribe:

| Fichero | Contenido |
|---|---|
| `sessions.json` | Una fila por sesión (los subagentes, por separado): llamadas, contexto, esperas, tokens por tipo, modelos, rol, tareas y tipo de atribución. |
| `tasks.json` | Por tarea: tokens directos, inferidos y repartidos, rol, herramienta, PR, rondas de revisión, fallos de CI, estado y horas hasta la PR y hasta la integración. |
| `windows.json` | Ventanas de 5 horas con la cuota que informa la herramienta, el tiempo pasado en el límite, los tokens por rol y las PR abiertas e integradas. |
| `prs.json` | PR con su tarea, herramienta, estado, veredictos y fallos de CI. |
| `validation.json` | Totales del parser frente a ccusage, con las diferencias. |
| `overrides.json` | Atribuciones manuales (las escribe la persona; la herramienta solo las lee). |

Nada sale de la máquina: los prompts no se escriben en ningún fichero y el directorio de salida está fuera del repositorio.

## Métricas y de dónde salen

| Métrica | Fuente | Tipo |
|---|---|---|
| Tokens por sesión, modelo y tipo (entrada nueva, salida, escritura y lectura de caché) | Registros locales; contrastados con ccusage | Real |
| Llamadas al modelo, contexto por llamada (media, mediana, p90 y máximo) y su evolución por deciles | Registros locales | Real |
| Llamadas de espera | Registros locales: llamadas cuyas herramientas solo esperan (`sleep`, `wait`, `wait_agent`, `list_agents`, `TaskOutput`, `Monitor`, `gh pr checks`, `gh run watch`) | Real, con una definición explícita |
| Tiempo transcurrido y tiempo activo | Marcas temporales; activo suma los huecos entre llamadas de hasta 5 minutos | Transcurrido, real; activo, estimado |
| Coste equivalente de la API | ccusage | Estimado: no es lo que se paga con la suscripción, y los modelos sin precio en ccusage llevan un precio aproximado (`cost_estimated`) |
| Cuota de 5 horas y semanal de Codex | `rate_limits` que Codex escribe en sus registros | Real, desde el primer registro |
| Cuota de 5 horas y semanal de Claude Code | Status Line oficial (`rate_limits`), registrada al cambiar | Real desde que se instala la Status Line; no disponible antes |
| Tarea de cada sesión | Rama o worktree (directa), prompt o nombre del subagente (inferida), varias tareas (repartida), sin evidencia (desconocida), o `overrides.json` | Según su tipo |
| Rol | `overrides.json`; si no, rama de tarea (implementación) o prompt de revisión | Inferido |
| PR, rondas de revisión, fallos de CI y estado | GitHub: PR, comentarios con «veredicto», ejecuciones fallidas de la rama y Project | Real; las rondas cuentan comentarios de veredicto |
| Horas hasta la PR y hasta la integración | Primera sesión atribuida a la tarea frente a la PR | Tiempo transcurrido, no trabajo activo |

No se calcula ningún porcentaje de cuota a partir de tokens, y los bloques de 5 horas de ccusage no se usan como ventanas reales. Las ventanas de Claude Code y de Codex no tienen el mismo inicio y se muestran por separado.

### Calidad de los datos

- **Sin dobles conteos.** Codex repite a veces el evento `token_count` con el mismo total acumulado: se cuenta una vez. Claude Code puede repetir la misma petición en el registro de varios subagentes: se cuenta una vez en todo el conjunto.
- **Validación.** Con los registros hasta el 28 de octubre de 2026, el parser coincide exactamente con ccusage en las 64 sesiones de Claude Code. En Codex coincide en 60 de 63; en las otras 3, ccusage 20.0.45 suma entre un 0,6 % y un 3 % de más porque cuenta los eventos repetidos, y el parser coincide con el total acumulado del propio Codex.
- **Sesiones repartidas.** Se reparten a partes iguales solo como estimación y se guardan aparte (`tokens_repartida_est`). Los tokens de orquestación no se asignan a tareas.

## Status Line de Claude Code

La Status Line muestra modelo, contexto usado y cuota de 5 horas y semanal, y guarda cada cambio de cuota en `claude-quota.jsonl`, dentro del directorio de salida. Es la única fuente oficial de la cuota de Claude Code que se puede registrar sin tocar credenciales.

```bash
mkdir -p ~/.local/share/mister-historico/agent-usage
cp tools/agent_usage/agent_usage.py ~/.local/share/mister-historico/agent-usage/
```

y en `~/.claude/settings.json` (haz antes una copia):

```json
"statusLine": {"type": "command", "command": "python3 ~/.local/share/mister-historico/agent-usage/agent_usage.py statusline"}
```

Codex ya muestra el contexto y la cuota con `/status` y guarda la cuota en sus registros, así que no necesita nada más. OpenTelemetry no aporta, para esta auditoría, nada que no esté ya en los registros locales.

## Diagnóstico de partida (hasta el 28 de octubre de 2026)

- 1.519 M de tokens en 127 sesiones; el 97,4 % son lecturas de caché.
- La orquestación suma 599 M (39 %) en 12 sesiones. En los orquestadores de Codex, 682 de 2.860 llamadas (24 %) solo esperaban.
- Las tres sesiones más costosas fueron orquestadores persistentes: F2 en Codex (247 M, 1.493 llamadas, 33 horas abiertas y unas 5 activas), F1-F2 en Codex (145 M, 69 horas abiertas) y la oleada A4 en Codex (76 M en 6 horas).
- Reutilizar una conversación para implementar varias tareas fue poco frecuente: 11 sesiones de implementación o revisión con varias tareas suman 102 M (7 %).
- Las ventanas de Codex llegaron al 99-100 % en 11 de las 13 ventanas cerradas, entre 35 minutos y 2 horas después de empezar; el resto de la ventana se pasó en el límite.

## Experimento de validación

Para las próximas 4 a 6 tareas comparables (mismo tamaño en TASKS y mismo tipo, por ejemplo backend M):

1. Trabaja cada tarea con el flujo actual: issue asignada, una sesión por objetivo, carga progresiva, esperas fuera del bucle del modelo y revisión cruzada.
2. Al cerrar cada ventana de 5 horas, ejecuta `make usage`.
3. Compara con la línea base de las tareas del mismo tamaño anteriores al 28 de octubre de 2026 a las 15:32 UTC (integración de la PR #105):
   - tareas integradas por ventana y por herramienta;
   - porcentaje de cuota consumido por tarea integrada, cuando haya datos de cuota;
   - tokens por rol, contexto mediano y p90, y porcentaje de llamadas de espera;
   - horas hasta la PR revisable y hasta la integración;
   - rondas de revisión, fallos de CI y retrabajo (commits `fix` tras la revisión).
4. Anota cualquier cambio de modelo, de plan o de límites del proveedor durante el experimento: con ellos, una diferencia no se puede atribuir solo al flujo de trabajo.

No hay todavía sesiones suficientes posteriores a la PR #105 para concluir nada; lo anterior es la línea base.
