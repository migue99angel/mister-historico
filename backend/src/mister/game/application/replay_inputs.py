"""Fixed inputs required to reproduce a run."""

from dataclasses import dataclass
import json

from mister.game.application.run_content import RunContentSnapshot
from mister.shared_kernel.errors import InvalidValueError


def _canonical_object(name: str, value: str) -> None:
    try:
        parsed = json.loads(value, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
        canonical = json.dumps(
            parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
    except (ValueError, TypeError) as error:
        raise InvalidValueError(f"{name} must be a canonical JSON object") from error
    if not isinstance(parsed, dict) or canonical != value:
        raise InvalidValueError(f"{name} must be a canonical JSON object")


@dataclass(frozen=True, slots=True)
class ReplayInputs:
    content: RunContentSnapshot
    initial_state_json: str
    rules_configuration_json: str
    engine_revision: str
    rules_revision: str

    def __post_init__(self) -> None:
        _canonical_object("initial_state_json", self.initial_state_json)
        _canonical_object("rules_configuration_json", self.rules_configuration_json)
        if not self.engine_revision.strip() or not self.rules_revision.strip():
            raise InvalidValueError("engine and rules revisions must not be blank")

    def ensure_compatible(self, *, engine_revisions: set[str], rules_revisions: set[str]) -> None:
        if self.engine_revision not in engine_revisions or self.rules_revision not in rules_revisions:
            raise InvalidValueError("replay engine or rules revision is not supported")
