# Míster Histórico

[![backend](https://github.com/migue99angel/mister-historico/actions/workflows/backend.yml/badge.svg?branch=main)](https://github.com/migue99angel/mister-historico/actions/workflows/backend.yml)
[![frontend](https://github.com/migue99angel/mister-historico/actions/workflows/frontend.yml/badge.svg?branch=main)](https://github.com/migue99angel/mister-historico/actions/workflows/frontend.yml)

> *¿Lo habrías hecho mejor que el míster?*

Juego de navegador gratuito, sin registro y con partidas de 3 a 5 minutos. Eres el entrenador de un equipo histórico real (por ejemplo, el Real Madrid 2012-13), con su plantilla de esa temporada, y tomas las decisiones de la temporada: mercado, vestuario, táctica, rotaciones y dilemas que ocurrieron de verdad. Al final, el juego compara tu temporada con lo que pasó en la realidad y genera una tarjeta para compartir.

**Estado:** en desarrollo. [v0.1.0](https://github.com/migue99angel/mister-historico/releases/tag/v0.1.0) es la primera versión jugable (hito A, pre-release interna): se juega una temporada completa con **Test FC**, un equipo sintético, todavía sin contenido histórico real. Ahora se trabaja en el hito A1 (gameplay y rejugabilidad); la primera beta histórica, con el Real Madrid 2012-13, será el hito B. El progreso se sigue en el [Project de GitHub](https://github.com/users/migue99angel/projects/1).

## Probarlo en local

Requisitos: Docker con Compose y [uv](https://docs.astral.sh/uv/).

```bash
make dev   # Postgres, API (aplica las migraciones) y frontend
cd backend && uv run mister content load --root tests/fixtures/content   # carga Test FC
```

Después, abre <http://localhost:5173>. Si algún puerto está ocupado, copia `.env.example` a `.env` y cámbialo; si cambias `POSTGRES_PORT`, exporta antes de la carga `DATABASE_URL=postgresql+psycopg://mister:mister@localhost:<puerto>/mister`.

## Documentación

- [Product brief](docs/PRODUCT_BRIEF.md): qué se construye y por qué.
- [Plan de implementación](docs/PLAN.md): arquitectura (DDD y hexagonal), estrategia de testing (TDD) y fases.
- [Tareas](docs/TASKS.md): el trabajo desglosado para ejecutarlo en paralelo.
- [Decisiones de arquitectura (ADR)](docs/adr/) y [glosario](docs/glossary.md).

## Estructura

```
backend/    API y dominio (Python, FastAPI, PostgreSQL)
frontend/   SPA móvil primero (React, Vite, TypeScript)
content/    Datos históricos versionados (YAML)
contracts/  Contrato de la API (OpenAPI)
tools/      Herramientas de desarrollo
infra/      Imágenes Docker
docs/       Brief, plan, ADR y documentación
```

`make help` lista los comandos disponibles.

## Licencia

Código bajo [MIT](LICENSE). Datos de `content/` bajo [CC BY-NC 4.0](content/LICENSE).

Proyecto fan, sin afiliación con clubes, ligas ni jugadores.
