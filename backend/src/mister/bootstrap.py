"""Composition root: el único sitio que cablea puertos con adaptadores (PLAN §3.2).

Es el único módulo autorizado a importar `mister.*.infrastructure`.
"""

from dataclasses import dataclass

from mister.settings import Settings


@dataclass(frozen=True, slots=True)
class Container:
    settings: Settings


def bootstrap(settings: Settings | None = None) -> Container:
    return Container(settings=settings if settings is not None else Settings())
