"""Typed, immutable identifiers.

Design: every ID is its own frozen dataclass wrapping a single `value`. A plain `NewType` would
be erased at runtime and cannot validate; distinct classes make mypy reject passing a `ClubId`
where a `PlayerId` is expected, and dataclass equality (which compares the exact class) keeps
them from ever comparing equal at runtime either.

- Content IDs (`ClubSeasonId`, `PlayableSeasonId`, `PlayerId`, `ClubId`, `CompetitionId`,
  `FixtureId`, `DilemmaId`, `OptionId`) are kebab-case slugs (`str`) that come from the content
  files, at most 64 characters. Only `ClubSeasonId` allows a single leading underscore, for
  system slugs such as `_market-2012-13`.
- `RunId` is a UUID, because runs are created at play time and need no human-readable name.
"""

import re
import uuid
from dataclasses import dataclass
from typing import ClassVar, Self

from mister.shared_kernel.errors import InvalidValueError

_SLUG_BODY = r"[a-z0-9]+(-[a-z0-9]+)*"
_SLUG_MAX_LENGTH = 64
_UUID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


@dataclass(frozen=True, slots=True)
class _SlugId:
    """Base of the content IDs: a validated kebab-case slug."""

    value: str

    #: Pattern the whole value must match; subclasses may widen it.
    _pattern: ClassVar[re.Pattern[str]] = re.compile(_SLUG_BODY)

    def __post_init__(self) -> None:
        name = type(self).__name__
        if not isinstance(self.value, str):
            raise InvalidValueError(f"{name} must be a string, got {type(self.value).__name__}")
        if len(self.value) > _SLUG_MAX_LENGTH or self._pattern.fullmatch(self.value) is None:
            raise InvalidValueError(
                f"{name} must be a kebab-case slug of at most {_SLUG_MAX_LENGTH} characters, "
                f"got {self.value!r}"
            )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ClubSeasonId(_SlugId):
    """A club in a specific season (ADR-015), e.g. `real-madrid-2012-13`.

    The only ID that accepts a leading underscore (`_market-2012-13`).
    """

    _pattern: ClassVar[re.Pattern[str]] = re.compile(rf"_?{_SLUG_BODY}")


@dataclass(frozen=True, slots=True)
class PlayableSeasonId(_SlugId):
    """A playable `ClubSeason` (ADR-015)."""


@dataclass(frozen=True, slots=True)
class PlayerId(_SlugId):
    """A real person, stable across seasons."""


@dataclass(frozen=True, slots=True)
class ClubId(_SlugId):
    """A club, stable across seasons."""


@dataclass(frozen=True, slots=True)
class CompetitionId(_SlugId):
    """A competition in a season."""


@dataclass(frozen=True, slots=True)
class FixtureId(_SlugId):
    """A scheduled match."""


@dataclass(frozen=True, slots=True)
class DilemmaId(_SlugId):
    """A dilemma of a playable season."""


@dataclass(frozen=True, slots=True)
class BlockId(_SlugId):
    """A block of the season."""


@dataclass(frozen=True, slots=True)
class OptionId(_SlugId):
    """An option of a dilemma."""


@dataclass(frozen=True, slots=True)
class RunId:
    """A run (one play-through of a season). Wraps a UUID."""

    value: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            raise InvalidValueError(f"RunId must wrap a UUID, got {type(self.value).__name__}")

    @classmethod
    def new(cls) -> Self:
        """Generate a random run ID (the only non-deterministic factory in this module)."""
        return cls(uuid.uuid4())

    @classmethod
    def parse(cls, text: str) -> Self:
        """Build a run ID from its canonical form only: lowercase, hyphenated UUID."""
        if _UUID_PATTERN.fullmatch(text) is None:
            raise InvalidValueError(f"RunId is not a canonical lowercase UUID: {text!r}")
        return cls(uuid.UUID(text))

    def __str__(self) -> str:
        return str(self.value)
