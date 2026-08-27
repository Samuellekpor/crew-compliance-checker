from __future__ import annotations

from crew_compliance.frameworks.catalog import FRAMEWORKS, STUB_FRAMEWORKS, get_framework

_booted = False


def bootstrap() -> None:
    global _booted
    if _booted:
        return
    from crew_compliance.frameworks import easa, faa_part_117

    easa.register()
    faa_part_117.register()
    _booted = True


__all__ = ["FRAMEWORKS", "STUB_FRAMEWORKS", "bootstrap", "get_framework"]