"""FastAPI application factory.

Run with `uvicorn mister.entrypoints.api.app:create_app --factory`.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from mister.bootstrap import Container, bootstrap
from mister.entrypoints.api.errors import domain_error_handler
from mister.entrypoints.api.routers.runs import router as runs_router
from mister.entrypoints.api.routers.seasons import router as seasons_router


def create_app(container: Container | None = None) -> FastAPI:
    configured = container if container is not None else bootstrap()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            engine = getattr(configured, "engine", None)
            if engine is not None:
                engine.dispose()

    app = FastAPI(title="Míster Histórico", lifespan=lifespan)
    app.state.container = configured
    app.state.runtime = app.state.container
    app.add_exception_handler(Exception, domain_error_handler)
    app.include_router(seasons_router)
    app.include_router(runs_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    generated_openapi = app.openapi

    def openapi_without_framework_validation_422() -> dict[str, object]:
        schema = generated_openapi()
        paths = schema.get("paths", {})
        if isinstance(paths, dict):
            for methods in paths.values():
                if isinstance(methods, dict):
                    for operation in methods.values():
                        if not isinstance(operation, dict):
                            continue
                        responses = operation.get("responses", {})
                        if not isinstance(responses, dict):
                            continue
                        for response in responses.values():
                            if (
                                isinstance(response, dict)
                                and response.get("description") == "Problem details."
                            ):
                                response["content"] = {
                                    "application/problem+json": {
                                        "schema": {"$ref": "#/components/schemas/Problem"}
                                    }
                                }
                        response = responses.get("422")
                        if isinstance(response, dict) and "HTTPValidationError" in str(response):
                            del responses["422"]
        return schema

    app.openapi = openapi_without_framework_validation_422  # type: ignore[method-assign]

    return app
