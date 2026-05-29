# ═══════════════════════════════════════════════════════════════════════════
# STAGED FILE — destination: playbooks/manager.py (NEW)
#
# ## TODO before apply
#   - This creates a new `playbooks/` Python package. Make sure the dir
#     doesn't already exist as something else.
#   - Singleton pattern (`playbook_manager` module-level) is fine for the
#     PoC. For production, consider injecting via FastAPI dependency.
# ═══════════════════════════════════════════════════════════════════════════
"""Lightweight playbook registry — indexes Python-defined playbooks by name
and resolves slides by id. One singleton instance per process."""

from typing import NamedTuple, Any, Optional, List, Callable


class Slide(NamedTuple):
    """One slide in a playbook.

    Calling convention for `builder`:
        builder(space_id: str, tick: int) -> list[dict]
            tick=0 for initial render (when slide is fired)
            tick=N for subsequent tick updates (when slide.ticks=True)

    For static slides without a tick loop, leave ticks=False and ignore the
    tick argument inside the builder (or use `tick=0` as the default — see
    `playbooks/demo_poc.py` for the pattern).
    """
    slide_id: str
    label:    str
    builder:  Callable[[str, int], list]  # (space_id, tick) -> components
    notes:    str  = ""
    ticks:    bool = False
    hz:       int  = 1                    # tick frequency in Hz, only used if ticks=True


class PlaybookManager:
    """Holds the registered playbooks. Discovery happens in `playbooks/__init__.py`."""

    def __init__(self):
        # {playbook_name: {slide_id: Slide}}
        self._playbooks: dict[str, dict[str, Slide]] = {}

    def register_playbook(self, name: str, slides: List[Slide]) -> None:
        self._playbooks[name] = {s.slide_id: s for s in slides}

    def get_slide(self, playbook_name: str, slide_id: str) -> Optional[Slide]:
        playbook = self._playbooks.get(playbook_name)
        if playbook is None:
            return None
        return playbook.get(slide_id)

    def list_slides(self, playbook_name: str) -> List[Slide]:
        """Used by the future /presenter/{space} URL to render the button strip."""
        playbook = self._playbooks.get(playbook_name)
        if playbook is None:
            return []
        return list(playbook.values())

    def list_playbooks(self) -> List[str]:
        return list(self._playbooks.keys())


# Singleton — imported by main.py's fire endpoint and by playbooks/__init__.py.
playbook_manager = PlaybookManager()
