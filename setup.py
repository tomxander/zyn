"""Build step for the Zyn wheel. Settings live in pyproject.toml.

Copies what an installed Zyn needs on its first run into harness/_bundle inside the wheel:
the config, rule profiles, the sample data and the built review screen. Build the screen
first (cd web; npm run build) or use scripts/build-release.ps1, which does both.
"""

import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

ROOT = Path(__file__).resolve().parent
BUNDLE_ITEMS = ("config.yaml", ".env.example", "knowledge.example.md",
                "taxonomy_placeholder.yaml", "rules", "data/synthetic", "web/dist",
                "LICENSE", "THIRD_PARTY_NOTICES.md")


class BuildWithBundle(build_py):
    def run(self):
        super().run()
        if getattr(self, "editable_mode", False):
            return  # an editable install reads these straight from the source folder
        if not (ROOT / "web" / "dist" / "index.html").is_file():
            # Still installable (every command-line check works); the screen says it is
            # missing. Release wheels come from scripts/build-release.ps1, which builds it.
            print("WARNING: review screen not built, so this install has none. "
                  "Run: cd web; npm run build")
        dest = Path(self.build_lib) / "harness" / "_bundle"
        if dest.exists():
            shutil.rmtree(dest)
        for item in BUNDLE_ITEMS:
            src = ROOT / item
            if not src.exists():
                continue
            target = dest / item
            target.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, target)
            else:
                shutil.copy2(src, target)


setup(cmdclass={"build_py": BuildWithBundle})
