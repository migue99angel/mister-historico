from typing import Any, cast

from fastapi import APIRouter, Path, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from mister.entrypoints.api.errors import domain_error_handler, problem
from mister.entrypoints.api.schemas import Problem, SeasonDetail, SeasonList
from mister.shared_kernel.ids import PlayableSeasonId


def _problem_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    return {
        status: {
            "description": "Problem details.",
            "model": Problem,
        }
        for status in statuses
    }


router = APIRouter(prefix="/api/seasons", tags=["Seasons"])


@router.get(
    "",
    operation_id="listSeasons",
    response_model=SeasonList,
    response_model_exclude_unset=True,
    responses=_problem_responses(429),
)
async def list_seasons(request: Request) -> dict[str, Any]:
    api = request.app.state.runtime.api()
    values = await run_in_threadpool(api.list_seasons)
    return {"items": [value.to_json() for value in values]}


@router.get(
    "/{seasonId}",
    operation_id="getSeason",
    response_model=SeasonDetail,
    response_model_exclude_unset=True,
    responses=_problem_responses(400, 404, 429),
)
async def get_season(
    request: Request,
    season_id: str = Path(
        alias="seasonId",
        json_schema_extra={
            "minLength": 1,
            "maxLength": 64,
            "pattern": r"^[a-z0-9]+(-[a-z0-9]+)*$",
        },
    ),
) -> dict[str, Any] | JSONResponse:
    try:
        season_id_value = PlayableSeasonId(season_id)
    except Exception:
        return problem(400, "validation_error", "The seasonId is malformed.")
    api = request.app.state.runtime.api()
    try:
        value = await run_in_threadpool(api.get_season, season_id_value)
    except Exception as error:
        if getattr(error, "code", "") == "season_not_found":
            return problem(404, "season_not_found", "There is no playable season with that id.")
        return await domain_error_handler(request, error)
    return cast("dict[str, Any]", value.to_json())
