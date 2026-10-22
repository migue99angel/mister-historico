"""Composition root: the only place that wires ports to adapters (PLAN §3.2).

It is the only module allowed to import `mister.*.infrastructure`.
"""

from dataclasses import dataclass

from mister.settings import Settings


@dataclass(frozen=True, slots=True)
class Container:
    settings: Settings


def bootstrap(settings: Settings | None = None) -> Container:
    return Container(settings=settings if settings is not None else Settings())
