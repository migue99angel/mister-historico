"""Request-scoped Game facade factory."""

from typing import cast

from fastapi import Request

from mister.game.application.api import GameApi


def game_api(request: Request) -> GameApi:
    runtime = request.app.state.runtime
    return cast("GameApi", runtime.api())
