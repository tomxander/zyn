"""Old name of harness.anvil (Forge was renamed Anvil on 13 Nov 2026).

Kept so test folders exported before the rename, whose conftest.py imports harness.forge,
still run. New code imports harness.anvil."""

import importlib
import sys

for _name in ("dbc", "generate", "impact", "pipeline", "score", "scripts", "simbench",
              "simulate", "validate"):
    sys.modules[f"{__name__}.{_name}"] = importlib.import_module(f"harness.anvil.{_name}")
