"""Published presentation ports for Game responses."""

from typing import Protocol

from mister.game.application.presentation_types import Presented
from mister.game.application.run_content import RunContentSnapshot
from mister.game.application.use_cases import RunView


class GamePresentation(Protocol):
    """Build safe response values from fixed content and a private run view."""

    def present_run(self, view: RunView, content: RunContentSnapshot) -> Presented: ...
