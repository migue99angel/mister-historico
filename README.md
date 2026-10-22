# Míster Histórico

> *¿Lo habrías hecho mejor que el míster?*

Juego de navegador gratuito, sin registro y con partidas de 3 a 5 minutos. Eres el entrenador de un equipo histórico real (por ejemplo, el Real Madrid 2012-13), con su plantilla de esa temporada, y tomas las decisiones de la temporada: mercado, vestuario, táctica, rotaciones y dilemas que ocurrieron de verdad. Al final, el juego compara tu temporada con lo que pasó en la realidad y genera una tarjeta para compartir.

**Estado:** en desarrollo (fase F0: fundaciones).

## Documentación

- [Product brief](docs/PRODUCT_BRIEF.md): qué se construye y por qué.
- [Plan de implementación](docs/PLAN.md): arquitectura (DDD y hexagonal), estrategia de testing (TDD) y fases.
- [Tareas](docs/TASKS.md): el trabajo desglosado para ejecutarlo en paralelo.

## Estructura

```
backend/    API y dominio (Python, FastAPI, PostgreSQL)
frontend/   SPA móvil primero (React, Vite, TypeScript)
content/    Datos históricos versionados (YAML)
contracts/  Contrato de la API (OpenAPI)
tools/      Herramientas offline (generación de contenido)
infra/      Docker, despliegue y pruebas de carga
docs/       Brief, plan, ADR y documentación
```

`make help` lista los comandos disponibles.

## Licencia

Código bajo [MIT](LICENSE). Datos de `content/` bajo [CC BY-NC 4.0](content/LICENSE).

Proyecto fan, sin afiliación con clubes, ligas ni jugadores.
