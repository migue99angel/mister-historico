# Míster Histórico: Product Brief

> **Nombre provisional.** Documento de idea y alcance para un juego de navegador de fútbol.
> Fecha: 2026-10-22 · Autor de la idea: Miguel Ángel Posadas · Estado: **idea validada, sin planificar ni implementar**.

---

## 0. Cómo usar este documento (para agentes)

- Este documento recoge **qué** se quiere construir y **por qué**. No es un plan de implementación: la planificación detallada y las tareas se harán a partir de él.
- La sección **§19 Decisiones abiertas** lista lo que **no está decidido**. No lo des por cerrado: proponlo y pide confirmación al autor.
- Lo marcado como **[VERIFICAR]** son datos históricos o externos que hay que comprobar con fuentes antes de usarlos en el juego. **No se debe inventar ningún dato histórico de fútbol** (plantillas, fechas, resultados): el juego vive de que la historia real sea correcta.
- Restricciones del autor en **§20**.

---

## 1. Resumen

Un juego de navegador **gratuito, sin registro y con partidas de 3 a 5 minutos**. El jugador llega como **entrenador de un equipo histórico real**, con su plantilla de esa temporada (por ejemplo, el Real Madrid 2012-13), y toma decisiones a lo largo de la temporada: mercado, vestuario, táctica, rotaciones y **dilemas que ocurrieron de verdad**. Los partidos se simulan.

Al final, el juego **compara tu temporada con lo que pasó en la realidad** ("Tú: Liga + Champions. Mourinho: Supercopa") y genera una **tarjeta para compartir** en redes. Es el gancho viral.

**Frase clave:** *"¿Lo habrías hecho mejor que el míster?"*

---

## 2. Contexto y objetivos

Es un **proyecto personal** del autor, un ingeniero backend/IA senior con 5 años de experiencia y stack Python/FastAPI/PostgreSQL. Tiene dos objetivos a la vez:

1. **Producto:** que la gente lo juegue y lo comparta, sobre todo el público de **Twitter/X fútbol en España**.
2. **Portfolio:** demostrar de punta a punta la capacidad de **idear, construir, lanzar y operar un producto con usuarios reales**, con métricas propias. Tienen que verse especialmente las piezas de backend (motor de simulación, ranking, rendimiento ante picos de tráfico) y un uso sensato de IA.

Por eso el código debe ser **limpio, probado y presentable**: repo público, README con las decisiones, CI y tests.

---

## 3. Referencias: juegos similares

| Juego | Qué es | Qué tomamos | Qué lo diferencia de nuestra idea |
|---|---|---|---|
| **Copero** ("Convertite en leyenda") | Simulador de **carrera de futbolista** en el navegador, basado en decisiones (entrenar al máximo o dosificar, cambiar de club, vacaciones…) y con mucho azar. Partida de unos 2 minutos, gratis, sin registro ni descarga. Lo creó Jerónimo Grinóvero, estudiante de la UNL (Argentina); lo mantiene un equipo de 3 personas. Más de 100 millones de partidas según prensa de jul-2026. Se hizo viral con streamers (Davo Xeneize, La Cobra, el Kun Agüero). | Formato de **sesión corta, sin fricción, por decisiones y con azar**. Viralidad por streamers. | Eres **jugador**, no entrenador. Ficción, sin equipos históricos. |
| **7-0 / Sete a Zero** | Te toca una selección y un Mundial al azar (1962–2026); eliges jugadores de las convocatorias reales con sus medias; los partidos se simulan según las medias. El objetivo es ganar 7 partidos sin perder. Incluye un "modo memoria" con las medias ocultas. Gratis, sin registro. Lo hizo un desarrollador brasileño inspirado en **82-0** (formato equivalente de la NBA). Viral durante el Mundial 2026 en Brasil y Argentina. | **Datos históricos reales con medias**, simulación por medias, objetivo claro y fácil de compartir ("hice 7-0"). | Es un **draft** de selecciones, no la gestión de una temporada de club. Hay pocas decisiones durante la partida. |
| **El Ídolo** (app Potrero / web) | Carrera de futbolista (delantero o enganche) que empieza en la liga argentina o uruguaya, con eventos aleatorios (ofertas, conflictos con entrenador o agente) que afectan a la reputación. | Eventos aleatorios con consecuencias en la reputación y la relación con la afición. | Eres jugador, no entrenador, y no hay equipos históricos. |
| **F1 Glory** (f1-glory.com) | Proyecto fan de F1 en beta. **Modo Carrera** (de karting a F1), **modo Team Principal** (fichar pilotos, desarrollar el coche; marcado como "en pruebas"), **modo Retro** por décadas (de los 50 a los 2020), reto semanal "próximamente", ranking, ranking de leyendas, compartir carrera, Discord, donaciones por Ko-fi. | **El modo Team Principal es la inspiración directa del autor.** También el modo retro, el ranking, el reto semanal y la monetización por donaciones. | Es de F1. Es la referencia de "gestor + historia" más cercana. |
| **Football Manager / OSM / ManagerZone / TrophyManager / KickoffBoss** | Managers de fútbol completos: de escritorio de pago (FM) o online persistentes con ligas entre usuarios (OSM, ManagerZone, TrophyManager, KickoffBoss). | La profundidad de gestión como referencia de qué decisiones existen. | Partidas de horas o semanas, con cuenta obligatoria. **Lo contrario** de lo que buscamos. |

### Hueco detectado
No hemos encontrado ningún juego de **"entrenador de un club histórico real en una partida corta, comparado con la historia"**. Queda en un punto intermedio entre 7-0 (2 minutos, draft) y Football Manager (100 horas).
*Búsqueda hecha el 2026-10-22; puede existir algo que no apareció. [VERIFICAR antes de lanzar]*

---

## 4. Público y canal

- **Público principal:** aficionados al fútbol español en Twitter/X, de 18 a 40 años, con nostalgia de los equipos de 2000–2015 y ganas de debatir.
- **Público secundario:** streamers y creadores de contenido de fútbol (formato ideal para jugar en directo) y Latinoamérica más adelante.
- **Dispositivo:** **móvil primero**. La mayoría llegará desde un enlace en Twitter en el móvil.
- **Idioma de la V1:** español de España.

---

## 5. Principios de diseño

1. **De 3 a 5 minutos por partida.** Si una partida pasa de 5 minutos, sobra contenido.
2. **Cero fricción:** sin registro, sin descarga y jugable desde el primer toque.
3. **La historia real es el rival.** Toda partida termina comparada con lo que ocurrió.
4. **Debate antes que realismo.** Los dilemas tienen que generar opinión ("yo habría puesto a Casillas").
5. **Todo se puede compartir:** cada final produce una imagen o tarjeta que quede bien en Twitter.
6. **Fidelidad histórica:** las plantillas, fechas y resultados reales tienen que ser correctos. Un dato erróneo en Twitter fútbol se señala enseguida.
7. **Rejugable:** el azar más las decisiones dan resultados distintos en cada partida.

---

## 6. Bucle de juego

```
Elegir equipo histórico → Contexto (presentación del míster, objetivos de la directiva)
  → Temporada en 5–6 bloques (agosto, oct–nov, dic–ene, feb–mar, abr–may)
      cada bloque: 1–3 decisiones → simulación del bloque → resumen (resultados, clasificación, eventos)
  → Final: títulos, estadísticas, comparación con la historia real, nota del míster
  → Tarjeta para compartir + ranking (alias) + "jugar otro equipo"
```

### Tipos de decisión
- **Mercado (verano e invierno):** fichar o vender entre opciones plausibles para esa época, incluidos fichajes que se hicieron de verdad y otros que estuvieron cerca. [VERIFICAR cada uno]
- **Vestuario:** conflictos con estrellas, capitanes, jugadores que piden minutos; afectan a la **moral**.
- **Táctica:** estilo (presión, contragolpe, posesión) y sistema; afecta al rendimiento según la plantilla.
- **Rotaciones / estado físico:** priorizar competiciones; riesgo de lesiones.
- **Cantera:** dar minutos a un joven, con impacto a largo plazo o en la valoración.
- **Dilemas históricos:** decisiones que se tomaron de verdad, presentadas como dilema. Son la seña de identidad del juego.
- **Prensa (V2):** ruedas de prensa con IA (ver §11).

### Ejemplo ilustrativo: Real Madrid 2012-13 (Mourinho) [VERIFICAR todos los datos]
- *Agosto:* ¿Fichas a Modrić? (llegó en agosto de 2012).
- *Enero:* Casillas se lesiona. ¿Diego López o Adán? ¿Y cuando Casillas vuelve?
- *Vestuario:* tensión con los capitanes. ¿Respaldas al vestuario o impones tu autoridad?
- *Historia real a batir:* Supercopa de España ganada al Barça; 2.º en Liga; final de Copa perdida contra el Atlético; eliminado en semifinales de Champions por el Dortmund.

> Nota: en conversaciones previas se mezclaron dilemas de 2011-12 y 2012-13 (Modrić y Diego López son de 2012-13). Cada dilema tiene que pertenecer a la temporada correcta.

---

## 7. Contenido de lanzamiento: equipos candidatos

En la V1, **entre 3 y 5 equipos muy bien hechos**. Mejor eso que muchos a medias. Candidatos (todos **[VERIFICAR]**), elegidos por nostalgia y por cuánto debate generan:

| Equipo | Por qué |
|---|---|
| Real Madrid 2012-13 (Mourinho) | Máximo debate: Casillas, el vestuario, el Dortmund. |
| FC Barcelona 2008-09 (Guardiola) | Triplete real: *"¿eres capaz de igualarlo?"* (reto difícil). |
| Atlético de Madrid 2013-14 (Simeone) | Liga y final de Champions perdida: *"¿ganas Lisboa?"* |
| Valencia 2003-04 (Benítez) | Liga y Copa de la UEFA; nostalgia. |
| Sevilla 2005-06 (Juande Ramos) | Primera Copa de la UEFA de la época dorada. |

Hay que elegir los equipos para que **gusten a todas las aficiones** y no solo a una.

---

## 8. Puntuación y comparación con la historia

- **Resultado deportivo:** títulos y posición en cada competición frente a lo que pasó de verdad.
- **Puntuación del míster (0–100):** combina títulos (con peso por competición), puntos en liga, la evolución de la moral y el cumplimiento de los objetivos de la directiva.
- **Veredicto** para la tarjeta: *"Superaste a Mourinho"*, *"Igualaste la historia"*, *"La directiva te destituyó en febrero"*. **Que te destituyan a mitad de temporada** también es un final que se comparte.
- **Percentil:** *"Mejor que el 87 % de los místers"*, a partir de las estadísticas agregadas de las partidas.

---

## 9. Motor de simulación (requisitos, no diseño cerrado)

- Datos de entrada: medias de los jugadores por temporada, alineación, táctica, moral, estado físico y nivel del rival.
- Modelo de goles **probabilístico** (por ejemplo, Poisson con fuerza de ataque y defensa). El modelo concreto está por decidir.
- **RNG con semilla:** misma semilla y mismas decisiones dan el mismo resultado. Es imprescindible para el reto semanal, para reproducir partidas y para los tests.
- **Calibración:** jugando "como en la realidad", el resultado esperado debe parecerse a la historia real. Hacen falta tests de calibración sobre muchas simulaciones.
- Los partidos se simulan **por bloques** (no uno a uno con interfaz), con un resumen de resultados importantes (clásicos, eliminatorias).
- Rivales: plantillas y medias de los rivales principales de esa temporada; el resto, con una fuerza agregada.

---

## 10. Viralidad

- **Tarjeta para compartir:** imagen generada (Open Graph) con escudo genérico, títulos, veredicto y comparación con la historia. Sus metadatos tienen que verse bien al pegar el enlace en Twitter/X.
- **Enlace a la partida:** `/r/<id>` muestra el resumen de la temporada de otro jugador e invita a jugar ("¿lo mejoras?").
- **Reto semanal (V2):** el mismo equipo y la misma semilla para todos durante una semana, con ranking. Hace que todo el mundo hable de lo mismo.
- **Modo streamer (V2, opcional):** sin tiempos de espera y con textos más grandes.
- **Ranking** con alias, sin cuentas.

---

## 11. Uso de IA

Tiene que **aportar algo al juego y no dispararse en coste**. Si el juego se hace viral puede tener millones de partidas.

- **V1, contenido generado por adelantado (offline):** usar LLMs como apoyo para redactar textos de eventos, titulares de prensa de la época y variantes de los dilemas. **Revisión humana obligatoria** y textos guardados como datos estáticos. Coste cero por partida.
- **V2, ruedas de prensa en vivo:** el jugador responde a preguntas de periodistas; un LLM evalúa el tono y eso afecta a la moral del vestuario y a la afición. Requisitos: límite de llamadas por partida y por IP, caché, modelo barato, salida estructurada, una alternativa sin IA si falla o se supera el presupuesto, y moderación de lo que escribe el usuario.
- **Topes de coste** desde el primer día: presupuesto mensual y un interruptor para desactivar la IA en vivo.
- Controlar el coste de la IA a escala es parte de la historia técnica del proyecto.

---

## 12. Arquitectura técnica propuesta (sujeta a §19)

- **Backend:** Python, **FastAPI**, **PostgreSQL**, SQLAlchemy (el stack fuerte del autor). La simulación vive en el backend para que el ranking sea fiable.
- **Frontend:** SPA ligera y móvil primero (React o Svelte con Vite: **por decidir**). Mínimo JavaScript y carga rápida en 4G.
- **Caché y límites:** Redis (o equivalente) para el ranking, la limitación de peticiones y la caché.
- **Imágenes para compartir:** se generan en el servidor y se cachean en un CDN.
- **Datos de contenido** (equipos, plantillas, medias, dilemas): archivos versionados en el repo (YAML o JSON) con un esquema validado y tests. Se cargan en la base de datos al desplegar.
- **Infraestructura:** contenedores Docker; CI/CD con GitHub Actions (lint, tests, tests de calibración). El hosting está por decidir, priorizando bajo coste y que aguante picos (CDN delante).
- **Observabilidad:** logs estructurados, métricas básicas y analítica de producto **sin cookies** (respetuosa con el RGPD).
- **Antitrampas básico:** el estado de la partida y la semilla viven en el servidor; el cliente solo envía decisiones.

### Modelo de datos (esbozo, no definitivo)
`Club` · `TeamSeason` (club + temporada + entrenador real + historia real) · `Player` · `PlayerSeason` (media, posición, edad, rol) · `Competition` · `HistoricalOutcome` · `Dilemma` / `Event` (bloque, opciones, efectos, fuente histórica) · `Run` (partida: equipo, semilla, estado) · `Decision` · `RunResult` · `LeaderboardEntry` · `WeeklyChallenge` (V2)

---

## 13. Datos históricos

- **Fuentes:** para cada dato hay que poder citar una fuente (hemerotecas, Wikipedia con referencias, BDFutbol, Transfermarkt…). Guardar la URL de la fuente en el propio archivo de datos.
- **Medias:** las define el proyecto con un criterio propio y documentado (no copiar las medias de un juego comercial). Por decidir: escala y método.
- **Proceso:** recopilar, revisar a mano y validar el esquema. Es **el trabajo más pesado del proyecto**, así que conviene priorizar calidad sobre cantidad.

---

## 14. Legal y riesgos

- **Derechos de imagen y marcas:** **no usar escudos, fotos, equipaciones oficiales ni logos de competiciones** (LaLiga, UEFA). Usar escudos genéricos o colores. Lo de usar nombres reales de jugadores está **por decidir** (§19): otros juegos virales los usan, pero el riesgo crece con el éxito.
- **Aviso:** "Proyecto fan, sin afiliación con clubes, ligas ni jugadores".
- **Privacidad:** sin cuentas; alias opcional; analítica sin cookies; nada de datos personales.
- **Esto no es asesoramiento legal:** si el juego crece, conviene consultarlo.
- **Riesgo de copia:** el formato se copia rápido. Lanzar pronto una V1 pequeña es mejor que lanzar tarde una perfecta.
- **Riesgo de que no se haga viral:** aun así, el proyecto debe quedar como una pieza de portfolio sólida (código, README, métricas aunque sean modestas).

---

## 15. Métricas de éxito

- **Producto:** partidas empezadas y terminadas (% que termina), partidas por usuario, tarjetas compartidas y clics en los enlaces compartidos, usuarios recurrentes semanales.
- **Técnicas:** p95 de latencia por petición, errores, coste mensual de infraestructura e IA, picos de tráfico soportados.
- **Portfolio:** una cifra real que se pueda contar ("N partidas, M usuarios") y un artículo técnico o post de lanzamiento.

---

## 16. Alcance

### V1 (lanzamiento)
- De 3 a 5 equipos históricos españoles.
- Una temporada por partida, de 3 a 5 minutos, con unas 10 decisiones.
- Motor de simulación con semilla y calibrado.
- Final con comparación con la historia, puntuación y veredicto.
- Tarjeta para compartir y enlace a la partida.
- Ranking por equipo con alias.
- Móvil primero, en español, sin registro.
- Textos de eventos escritos o pregenerados con IA y revisados.

### V2
- Reto semanal con semilla compartida y ranking.
- Ruedas de prensa con IA en vivo (con topes de coste).
- Más equipos y temporadas; equipos internacionales; varias temporadas por partida.
- Modo streamer; inglés o versión para Latinoamérica.
- Donaciones (Ko-fi o similar), como F1 Glory.

### Fuera de alcance (por ahora)
- Cuentas de usuario, multijugador, partidos jugables en tiempo real o en 3D, app nativa, monetización con anuncios.

---

## 17. Plan orientativo

Al ritmo de un proyecto personal de fines de semana, unas **6 semanas hasta la V1**. Es orientativo: la planificación real se hará después.

1. Esquema de datos, primer equipo completo con fuentes, y prototipo del motor de simulación con tests de calibración.
2. API de partida (crear, decidir, avanzar, terminar) y estado en el servidor.
3. Frontend móvil con el bucle completo de un equipo.
4. Final, puntuación, tarjeta para compartir con Open Graph y ranking.
5. Del 2.º al 3.º–5.º equipo; textos; pulido.
6. Infraestructura, observabilidad, prueba de carga, beta cerrada con amigos y lanzamiento en Twitter.

---

## 18. Ideas de lanzamiento

- Hilo en Twitter/X con capturas de los mejores dilemas ("¿qué habríais hecho?").
- Enviárselo a creadores de contenido de fútbol español.
- Publicar el juego cuando el equipo protagonista esté de actualidad (aniversarios, partidos entre esos rivales).

---

## 19. Decisiones abiertas (las confirma el autor)

1. **Nombre definitivo** y dominio.
2. **Nombres reales de jugadores:** sí o no, o una alternativa.
3. **Equipos de lanzamiento** definitivos (de 3 a 5).
4. **Escala y criterio de las medias** de los jugadores.
5. **Framework del frontend** (React o Svelte u otro).
6. **Hosting** y presupuesto mensual máximo.
7. **Modelo de simulación** concreto.
8. Si la IA entra ya en la V1 (solo contenido offline) o solo en la V2.
9. Repo público desde el primer día o al lanzar.

---

## 20. Restricciones del autor

- Es un **proyecto personal**: **no se puede usar código, datos, prompts ni nada de la empresa** del autor (Nucleoo). Se hace con medios propios y en tiempo propio.
- El tiempo disponible es limitado (fines de semana): hay que priorizar sin descanso.
- El stack en el que el autor es más productivo es Python, FastAPI, PostgreSQL, SQLAlchemy, Docker y GitHub Actions. En el frontend tiene experiencia con Angular, React y TypeScript.
- El resultado debe servir como **pieza de portfolio**: calidad de código, tests, CI y un README con la arquitectura y las decisiones.

---

## 21. Fuentes (consultadas el 2026-10-22)

- Copero: [Canal 26](https://www.canal26.com/deportes/2026/07/24/copero-como-jugar-gratis-al-simulador-viral-que-te-convierte-en-futbolista-profesional/) · [Aire de Santa Fe (100 M de partidas, creador en la UNL)](https://www.airedesantafe.com.ar/gaming/copero-el-simulador-futbol-creado-un-estudiante-la-unl-que-ya-supero-las-100-millones-partidas-n665209) · [Androidphoria](https://androidphoria.com/juegos/copero-juego-futbol)
- 7-0 y El Ídolo: [Canal 26: minijuegos de fútbol virales](https://www.canal26.com/deportes/2026/07/28/los-minijuegos-de-futbol-gratuitos-que-se-volvieron-tendencia-al-igual-que-copero-de-que-tratan-7-0-y-el-idolo/) · [Canal 26: 7 a 0](https://www.canal26.com/deportes/2026/06/09/asi-es-7-a-0-el-juego-gratis-y-viral-con-el-que-podes-ganar-el-mundial-con-messi-maradona-y-kempes/) · [Culturageek: origen e inspiración en 82-0](https://culturageek.com.ar/7a0-videojuego-viral-futbol/) · [CrazyGames: 7-0 Cup Run](https://www.crazygames.com/ar/game/7-0-cup-run)
- F1 Glory: [f1-glory.com](https://f1-glory.com/)
- Managers online: [ManagerZone](https://www.managerzone.com/landing/online-soccer-manager/es/) · [TrophyManager](https://trophymanager.com/es/) · [KickoffBoss](https://kickoffboss.com/es-ES/)
