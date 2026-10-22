"""Application ports of the Catalog context.

`SeasonContentProvider` is the Catalog's only outbound-facing port. It is defined next to the
DTOs of the published language (`api.py`) because consumers import both from there; it is
re-exported here so that every context finds its ports in `application/ports.py`.
"""

from mister.catalog.application.api import SeasonContentProvider

__all__ = ["SeasonContentProvider"]
