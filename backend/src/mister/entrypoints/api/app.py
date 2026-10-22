"""Factoría de la app FastAPI.

Se lanza con `uvicorn mister.entrypoints.api.app:create_app --factory`.
"""

from fastapi import FastAPI

from mister.bootstrap import Container, bootstrap


def create_app(container: Container | None = None) -> FastAPI:
    app = FastAPI(title="Míster Histórico")
    app.state.container = container if container is not None else bootstrap()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
