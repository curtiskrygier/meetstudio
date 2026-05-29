# ═══════════════════════════════════════════════════════════════════════════
# STAGED FILE — destination: playbooks/yaml_loader.py (NEW)
#
# ## TODO before apply
#   - Loader is async-only (builders return coroutines). Requires the
#     main.py fire endpoint patch (see staging/main_py_async_builder_patch.md)
#     to await them. Sync demo_poc.py builders still work via the patch's
#     dual-path detection.
#   - `register_yaml_playbooks_in_dir()` is called from __init__.py at
#     module import. If you want lazy loading, move it to a startup hook.
#   - YAML parse errors abort registration but don't crash the process —
#     they log a warning. If you want stricter validation, raise instead.
# ═══════════════════════════════════════════════════════════════════════════
"""YAML playbook loader — orchestrator between YAML config + templates + data
sources. Discovers `*.yaml` files in `playbooks/` and registers each as a
playbook in the global `playbook_manager`."""

import os
import logging
from typing import Callable

import yaml

from playbooks.manager import Slide, playbook_manager
from playbooks.templates import TEMPLATES
from playbooks.data_sources import resolve_slide_data, slide_has_refresh_ticks

logger = logging.getLogger(__name__)


def _make_builder(slide_cfg: dict, playbook_name: str) -> Callable:
    """Return an ASYNC builder that resolves data per refresh policy on each
    call, then dispatches to the chosen template. Closes over slide_cfg +
    playbook_name so we don't have to thread them through the Slide tuple."""
    template_name = slide_cfg.get("template")
    template_fn   = TEMPLATES.get(template_name)
    slide_id      = slide_cfg.get("id", "unknown")
    data_decls    = slide_cfg.get("data") or {}

    async def builder(space_id: str, tick: int = 0):
        if template_fn is None:
            return _error_slide(slide_id, f"Unknown template: '{template_name}'")
        ctx = {"playbook_name": playbook_name, "space_id": space_id}
        try:
            data = await resolve_slide_data(slide_id, data_decls, ctx, tick)
        except Exception as e:
            logger.error(f"[yaml_loader] data resolution failed for "
                         f"{playbook_name}/{slide_id}: {e}")
            data = {k: d.get("fallback", "—") for k, d in data_decls.items()}
        # Hand resolved data + context to the template. Templates are sync.
        full_cfg = {**slide_cfg, **ctx}
        return template_fn(slide_id, full_cfg, data)

    return builder


def _error_slide(slide_id: str, message: str) -> list[dict]:
    """Fallback surface when a slide can't render — shown in red so the
    presenter sees the failure rather than a blank stage."""
    return [
        {"id": "root", "component": {"gdm-stage-grid": {
            "layout": "hero", "children": {"explicitList": ["main"]}}}},
        {"id": "main", "component": {"gdm-container": {
            "direction": "column", "justify": "center", "align": "center",
            "grow": 1, "gap": "20px", "padding": "60px",
            "children": {"explicitList": [f"err_badge_{slide_id}", f"err_msg_{slide_id}"]}}}},
        {"id": f"err_badge_{slide_id}", "component": {"gdm-badge": {
            "text": "SLIDE ERROR", "type": "danger", "pulse": True}}},
        {"id": f"err_msg_{slide_id}", "component": {"gdm-text": {
            "content": message, "size": "32px", "color": "#ff5d5d",
            "font": "mono", "weight": "700"}}},
    ]


def load_yaml_playbook(filepath: str) -> str | None:
    """Read one YAML playbook file and register it. Returns the playbook
    name on success, None on failure (with a logged warning)."""
    try:
        with open(filepath) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.warning(f"[yaml_loader] YAML parse error in {filepath}: {e}")
        return None
    except OSError as e:
        logger.warning(f"[yaml_loader] cannot read {filepath}: {e}")
        return None

    if not isinstance(config, dict):
        logger.warning(f"[yaml_loader] {filepath} did not parse to a dict — skipping")
        return None

    name = config.get("name")
    slides_cfg = config.get("slides")
    if not name or not isinstance(slides_cfg, list):
        logger.warning(f"[yaml_loader] {filepath} missing 'name' or 'slides' list — skipping")
        return None

    slides_built: list[Slide] = []
    for cfg in slides_cfg:
        if not isinstance(cfg, dict) or "id" not in cfg or "template" not in cfg:
            logger.warning(f"[yaml_loader] {filepath} has malformed slide entry: {cfg}")
            continue
        data_decls = cfg.get("data") or {}
        slides_built.append(Slide(
            slide_id=cfg["id"],
            label=cfg.get("label", str(cfg["id"]).replace("_", " ").title()),
            builder=_make_builder(cfg, name),
            notes=cfg.get("notes", ""),
            ticks=slide_has_refresh_ticks(data_decls),
            hz=int(cfg.get("hz", 1)),
        ))

    playbook_manager.register_playbook(name, slides_built)
    logger.info(f"[yaml_loader] registered '{name}' from {os.path.basename(filepath)} "
                f"with {len(slides_built)} slides")
    return name


def register_yaml_playbooks_in_dir(directory: str | None = None) -> list[str]:
    """Auto-discover and register every `*.yaml` file in `directory` (defaults
    to the playbooks/ folder containing this module). Returns the list of
    playbook names successfully registered."""
    if directory is None:
        directory = os.path.dirname(os.path.abspath(__file__))
    registered: list[str] = []
    for fname in sorted(os.listdir(directory)):
        if not (fname.endswith(".yaml") or fname.endswith(".yml")):
            continue
        path = os.path.join(directory, fname)
        name = load_yaml_playbook(path)
        if name:
            registered.append(name)
    return registered
