"""Published Game API: safe response facade over private run use cases."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from mister.game.application import key_starter_flow, ports
from mister.game.application.presentation_types import Presented, Started
from mister.game.application.use_cases import (
    AdvanceBlock,
    GetRun,
    RunAccessDeniedError,
    RunView,
    SelectKeyStarter,
    StartRun,
    TakeDecision,
)
from mister.game.domain.errors import (
    AlreadyDecidedError,
    InvalidDecisionError,
    InvalidRunTransitionError,
)
from mister.shared_kernel.errors import DomainError, InvalidValueError

if TYPE_CHECKING:
    from mister.game.application.presentation import GamePresentation
    from mister.shared_kernel.ids import (
        DilemmaId,
        FixtureId,
        OptionId,
        PlayableSeasonId,
        PlayerId,
        RunId,
    )


class GameApiError(DomainError):
    """Stable public application error that does not expose private domain codes."""

    code = "game_error"


class PendingDilemmasError(GameApiError):
    code = "pending_dilemmas"


class RunAlreadyFinishedError(GameApiError):
    code = "run_already_finished"


class DilemmaAlreadyDecidedError(GameApiError):
    code = "dilemma_already_decided"


class InvalidOptionError(GameApiError):
    code = "invalid_option"


class InvalidKeyStarterError(GameApiError):
    code = "invalid_key_starter"


class KeyStarterAlreadySelectedError(GameApiError):
    code = "key_starter_already_selected"


class SeasonNotFoundError(GameApiError):
    """The requested season isn't published as playable."""

    code = "season_not_found"


class SeasonQueries(Protocol):
    """Read-only season list and detail supplied by Game's infrastructure ACL."""

    def list_seasons(self) -> tuple[Presented, ...]: ...

    def get_season(self, season_id: PlayableSeasonId) -> Presented: ...


class KeyStarterCommands(Protocol):
    """Select the key starter of the current block's captured offer (T3.9)."""

    def select_key_starter(  # noqa: PLR0913, PLR0917 - public command fields
        self,
        run_id: RunId,
        token: str,
        idempotency_key: str,
        expected_version: int,
        fixture_id: FixtureId,
        player_id: PlayerId,
    ) -> Presented: ...


class GameApi(KeyStarterCommands):
    """Public facade that turns private use-case results into safe presentation DTOs."""

    def __init__(  # noqa: PLR0913 - explicit public dependencies
        self,
        *,
        start_run: StartRun,
        get_run: GetRun,
        take_decision: TakeDecision,
        advance_block: AdvanceBlock,
        uow: ports.UnitOfWork,
        token_hasher: ports.RunTokenHasher,
        presentation: GamePresentation,
        seasons: SeasonQueries,
        select_key_starter: SelectKeyStarter | None = None,
    ) -> None:
        self._start = start_run
        self._get = get_run
        self._take = take_decision
        self._advance = advance_block
        self._uow = uow
        self._token_hasher = token_hasher
        self._presentation = presentation
        self._seasons = seasons
        self._select = select_key_starter

    def list_seasons(self) -> tuple[Presented, ...]:
        return self._seasons.list_seasons()

    def get_season(self, season_id: PlayableSeasonId) -> Presented:
        try:
            return self._seasons.get_season(season_id)
        except DomainError as error:
            if error.code == "season_not_found":
                raise SeasonNotFoundError("playable season not found") from error
            raise

    def authenticate(self, run_id: RunId, token: str) -> None:
        """Check existence and access without decoding mutable state or captured content."""
        with self._uow as uow:
            record = uow.runs.get(run_id)
        if record is None:
            raise ports.RunNotFoundError(run_id)
        if not self._token_hasher.verify(token, record.run_token_hash):
            raise RunAccessDeniedError("invalid run token")

    def start_run(self, season_id: PlayableSeasonId) -> Started:
        started = self._start.execute(season_id)
        with self._uow as uow:
            record = uow.runs.get(started.run_id)
        if record is None:
            raise ports.RunNotFoundError(started.run_id)
        view = self._presentation.present_run(started.view, record.replay_inputs.content)
        return Started(started.token, view)

    def get_run(self, run_id: RunId, token: str) -> Presented:
        self.authenticate(run_id, token)
        view = self._get.execute(run_id, token)
        return self._present_latest_capture(run_id, view)

    def take_decision(  # noqa: PLR0913, PLR0917 - mirrors public command fields
        self,
        run_id: RunId,
        token: str,
        idempotency_key: str,
        expected_version: int,
        dilemma_id: DilemmaId,
        option_id: OptionId,
    ) -> Presented:
        try:
            view = self._take.execute(
                run_id, token, idempotency_key, expected_version, dilemma_id, option_id
            )
        except InvalidRunTransitionError as error:
            if str(error) == "terminal runs reject commands":
                raise RunAlreadyFinishedError("the run has already finished") from error
            raise
        except (InvalidValueError, InvalidDecisionError) as error:
            if isinstance(error, InvalidDecisionError) or str(error) in {
                "dilemma does not belong to the current block",
                "option does not belong to the selected dilemma",
            }:
                raise InvalidOptionError("the selected option is not available") from error
            raise
        except AlreadyDecidedError as error:
            raise DilemmaAlreadyDecidedError("the dilemma has already been decided") from error
        return self._present_latest_capture(run_id, view)

    def advance_block(
        self, run_id: RunId, token: str, idempotency_key: str, expected_version: int
    ) -> Presented:
        try:
            view = self._advance.execute(run_id, token, idempotency_key, expected_version)
        except InvalidRunTransitionError as error:
            if str(error) == "all current block dilemmas must be decided first":
                raise PendingDilemmasError("current block dilemmas are unresolved") from error
            if str(error) == "terminal runs reject commands":
                raise RunAlreadyFinishedError("the run has already finished") from error
            raise
        return self._present_latest_capture(run_id, view)

    def select_key_starter(  # noqa: PLR0913, PLR0917 - mirrors public command fields
        self,
        run_id: RunId,
        token: str,
        idempotency_key: str,
        expected_version: int,
        fixture_id: FixtureId,
        player_id: PlayerId,
    ) -> Presented:
        if self._select is None:
            raise InvalidKeyStarterError("this composition offers no key starter command")
        try:
            view = self._select.execute(
                run_id, token, idempotency_key, expected_version, fixture_id, player_id
            )
        except InvalidRunTransitionError as error:
            # Selection has a single transition guard: the run must still be in progress.
            raise RunAlreadyFinishedError("the run has already finished") from error
        except key_starter_flow.InvalidKeyStarterError as error:
            raise InvalidKeyStarterError(str(error)) from error
        except key_starter_flow.KeyStarterAlreadySelectedError as error:
            raise KeyStarterAlreadySelectedError(str(error)) from error
        return self._present_latest_capture(run_id, view)

    def _present_latest_capture(self, run_id: RunId, view: RunView) -> Presented:
        # Replayable content is immutable. The run snapshot is intentionally not read here:
        # `view` is the original response, including any idempotent replay.
        with self._uow as uow:
            record = uow.runs.get(run_id)
        if record is None:
            raise ports.RunNotFoundError(run_id)
        return self._presentation.present_run(view, record.replay_inputs.content)
