"""HTTP problem details mapping for public Game API failures."""

import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

_LOGGER = logging.getLogger(__name__)

_STATUS = {
    "validation_error": 400,
    "idempotency_key_required": 400,
    "run_token_required": 401,
    "run_token_invalid": 403,
    "run_not_found": 404,
    "season_not_found": 404,
    "version_conflict": 409,
    "pending_dilemmas": 409,
    "dilemma_already_decided": 409,
    "run_already_finished": 409,
    "invalid_option": 422,
    "idempotency_key_conflict": 422,
}


def problem(
    status: int,
    code: str,
    detail: str | None = None,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    body: dict[str, object] = {
        "type": f"https://misterhistorico.example/problems/{code.replace('_', '-')}",
        "title": code.replace("_", " ").title(),
        "status": status,
        "code": code,
    }
    if detail:
        body["detail"] = detail
    if errors:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


async def domain_error_handler(_: Request, error: Exception) -> JSONResponse:
    code = getattr(error, "code", "")
    if not isinstance(code, str) or code not in _STATUS:
        _LOGGER.error(
            "Unexpected Game API failure",
            exc_info=(type(error), error, error.__traceback__),
        )
        return problem(500, "internal_error", "An internal error occurred.")
    return problem(_STATUS[code], code, str(error))
