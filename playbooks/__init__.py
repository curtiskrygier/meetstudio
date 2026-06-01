# ═══════════════════════════════════════════════════════════════════════════
# STAGED FILE — destination: playbooks/__init__.py (REPLACES existing)
#
# ## TODO before apply
#   - This REPLACES the existing playbooks/__init__.py. The replacement
#     keeps `demo_poc` registered (back-compat) AND auto-discovers all
#     *.yaml files in playbooks/.
#   - If you'd prefer that demo_poc be migrated to YAML and the Python
#     version retired, delete the demo_poc import block after writing a
#     yaml equivalent (e.g. playbooks/demo_poc.yaml).
# ═══════════════════════════════════════════════════════════════════════════
"""Playbook registration entry point.

Importing `playbooks` triggers:
  1. Registration of the demo_poc Python-driven slides (back-compat).
  2. Auto-discovery + registration of every *.yaml playbook in this directory.

The fire endpoint then resolves slides via
`playbook_manager.get_slide(playbook_name, slide_id)`."""

from playbooks.manager import playbook_manager, Slide

# 1. Keep the existing Python-driven PoC registered.
from playbooks.demo_poc import SLIDES as _demo_poc_slides
playbook_manager.register_playbook("demo_poc", _demo_poc_slides)

import playbooks.a2ui_catalogue  # self-registers via playbook_manager.register_playbook
import playbooks.patterns  # self-registers via playbook_manager.register_playbook
import playbooks.dataviz_demo  # self-registers via playbook_manager.register_playbook
import playbooks.new_atoms_showcase  # self-registers via playbook_manager.register_playbook

# 2. Auto-register every *.yaml file in playbooks/ via the YAML loader.
from playbooks.yaml_loader import register_yaml_playbooks_in_dir
register_yaml_playbooks_in_dir()

# Re-export the singleton + Slide type for convenience.
__all__ = ["playbook_manager", "Slide"]
