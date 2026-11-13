"""DBC checks on real, public CAN databases: comma.ai opendbc.

Source: github.com/commaai/opendbc, pinned commit 27fa1c5d (2026-11-08), opendbc/dbc/*.dbc,
MIT licence, copyright comma.ai and contributors. Most files are reverse-engineered by the
community, not published by the carmakers, so a finding is a finding on that file, not on a
vehicle.

What it measures: that Zyn reads every file, and what its DBC checks report on files written
by many hands. There is no answer key, so nothing here is a precision or recall figure; the
findings are a sample for a person to look at.

Run from the project root:
  python -m evals.opendbc fetch    # downloads the pinned files into data/public/opendbc/
  python -m evals.opendbc run      # checks each file, prints counts, writes a JSON report
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

COMMIT = "27fa1c5d8eed3238a0a78c52ff5abb6cdc807bd2"
BASE = f"https://raw.githubusercontent.com/commaai/opendbc/{COMMIT}/opendbc/dbc/"
DEST = ROOT / "data" / "public" / "opendbc"
MANIFEST = Path(__file__).with_name("opendbc_manifest.json")


def fetch() -> None:
    names = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    DEST.mkdir(parents=True, exist_ok=True)
    for name, sha in names.items():
        data = urllib.request.urlopen(BASE + name, timeout=60).read()
        got = hashlib.sha256(data).hexdigest()
        if got != sha:
            raise SystemExit(f"{name}: sha256 {got} does not match the manifest {sha}")
        (DEST / name).write_bytes(data)
    print(f"{len(names)} files in {DEST}")


def run() -> dict:
    from harness.anvil.dbc import load_dbc
    from harness.anvil.dbc_check import check_file

    files = sorted(DEST.glob("*.dbc"))
    if not files:
        raise SystemExit("No files. Run: python -m evals.opendbc fetch")
    per_file, cats, unreadable = {}, Counter(), {}
    signals = 0
    for f in files:
        try:
            found = check_file(f)
            signals += len(load_dbc(f).signals)
        except ValueError as e:
            unreadable[f.name] = str(e)
            continue
        c = Counter(x["category"] for x in found)
        cats.update(c)
        per_file[f.name] = {"findings": dict(c),
                            "examples": [x["explanation"] for x in found[:3]]}
    report = {"commit": COMMIT, "files": len(files), "read": len(per_file),
              "unreadable": unreadable, "signals": signals, "findings_by_kind": dict(cats),
              "files_with_findings": sum(1 for v in per_file.values() if v["findings"]),
              "per_file": per_file}
    out = ROOT / "runs" / "evals" / "opendbc.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "per_file"}, indent=2))
    print(f"Full report: {out}")
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=["fetch", "run"])
    a = ap.parse_args()
    fetch() if a.action == "fetch" else run()


if __name__ == "__main__":
    main()
