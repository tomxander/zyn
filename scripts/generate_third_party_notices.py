#!/usr/bin/env python3
"""Generates the npm production package section of THIRD_PARTY_NOTICES.md

Reads web/package-lock.json for production (non-dev) packages, extracts their
version, license, and copyright from their respective node_modules directories,
and writes the updated THIRD_PARTY_NOTICES.md.
"""

from __future__ import annotations

import json
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCK_FILE = PROJECT_ROOT / "web" / "package-lock.json"
NOTICES_FILE = PROJECT_ROOT / "THIRD_PARTY_NOTICES.md"

FONTS_SECTION = """# Third-Party Notices and Licenses

Zyn bundles client-side JavaScript packages in its web distribution (`web/dist`), which ships in the wheel package and container image. Third-party fonts are used in the repository and documentation site; fonts do not ship in the Python wheel or container image. Python dependencies are not bundled into the distribution and are resolved at installation time.

This file lists the third-party components bundled into Zyn, their copyright holders, and their respective licenses.

---

## 1. Third-Party Fonts (Repository and Documentation)

The following fonts are used in the repository and documentation site. They do not ship in the Python wheel distribution or container image:

### IBM Plex Mono
- License: SIL Open Font License, Version 1.1 (OFL-1.1)
- Copyright: Copyright 2017 IBM Corp. All rights reserved.
- Files: `site/public/fonts/IBMPlexMono-Regular.ttf`, `zyn-identity/fonts/IBMPlexMono-Regular.ttf`
- Notice: Reserved Font Name: Plex

### Space Grotesk
- License: SIL Open Font License, Version 1.1 (OFL-1.1)
- Copyright: Copyright 2020 The Space Grotesk Project Authors (https://github.com/floriankarsten/space-grotesk)
- Files: `site/public/fonts/SpaceGrotesk.ttf`, `zyn-identity/fonts/SpaceGrotesk.ttf`
- Notice: Reserved Font Name: Space Grotesk

### D-DIN Condensed
- License: SIL Open Font License, Version 1.1 (OFL-1.1)
- Copyright: Copyright 2017 Datto, Inc. (https://www.datto.com)
- Files: `zyn-identity/fonts/D-DINCondensed-Bold.ttf`
- Notice: Reserved Font Name: D-DIN

#### SIL Open Font License Version 1.1 Text

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is available with a FAQ at: https://openfontlicense.org

Permission is hereby granted, free of charge, to any person obtaining
a copy of the Font Software, to use, study, copy, merge, embed, modify,
redistribute, and sell modified and unmodified copies of the Font
Software, subject to the following conditions:

1) Neither the Font Software nor any of its individual components,
in Source or Compiled forms, may be sold by itself.

2) Original or Modified Versions of the Font Software may be bundled,
redistributed and/or sold with any software, provided that each copy
contains the above copyright notice and this license. These can be
included either as stand-alone text files, human-readable headers or
in the appropriate machine-readable metadata fields within text or
binary files as long as those fields can be easily viewed by the user.

3) No Modified Version of the Font Software may use the Reserved Font
Name(s) unless prominent written permission is granted by the
corresponding Copyright Holder. This restriction only applies to the
primary font name as presented to the users.

4) The name(s) of the Copyright Holder(s) or the Author(s) of the Font
Software shall not be used to promote, endorse or advertise any
Modified Version, except to acknowledge the contribution(s) of the
Copyright Holder(s) and the Author(s) or with their explicit written
permission.

5) The Font Software, modified or unmodified, in part or in whole,
must be distributed entirely under this license, and must not be
distributed under any other license. The requirement for fonts to
remain under this license does not apply to any document created
using the Font Software.

THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT
OF COPYRIGHT, PATENT, TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL THE
COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
INCLUDING ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL
DAMAGES, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF THE USE OR INABILITY TO USE THE FONT SOFTWARE OR FROM
OTHER DEALINGS IN THE FONT SOFTWARE.
"""

MIT_TEXT = """#### Standard MIT License Text

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

BSD0_TEXT = """#### Standard 0BSD License Text

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.
"""


def extract_package_info(name: str, meta: dict) -> dict:
    version = meta.get("version", "")
    license_id = meta.get("license")
    pdir = PROJECT_ROOT / "web" / "node_modules" / name

    copyright_str = None
    if pdir.exists():
        lic_files = [
            f for f in pdir.glob("*")
            if re.match(r"^(licen[sc]e|copying|notice)", f.name, re.I)
        ]
        if lic_files:
            content = lic_files[0].read_text(encoding="utf-8", errors="replace")
            m = re.search(r"copyright\s+(?:\(c\)\s+)?.*?(?=\r?\n|$)", content, re.I)
            if m:
                copyright_str = m.group(0).strip()
        pkg_json = pdir / "package.json"
        if pkg_json.exists():
            pj = json.loads(pkg_json.read_text(encoding="utf-8"))
            if not copyright_str:
                author = pj.get("author")
                if isinstance(author, dict):
                    author = author.get("name")
                if author:
                    copyright_str = f"Copyright (c) {author}"
            lic_in_pj = pj.get("license")
            if lic_in_pj and not license_id:
                license_id = lic_in_pj

    if not license_id:
        raise ValueError(f"Package '{name}' has no license defined in lock file or package.json")

    if not copyright_str:
        raise ValueError(f"Package '{name}' has no identifiable copyright notice in license files or package.json")

    return {
        "name": name,
        "version": version,
        "license": license_id,
        "copyright": copyright_str,
    }


def generate_notices() -> str:
    lock_data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    packages = lock_data.get("packages", {})

    prod_pkgs = {
        k.replace("node_modules/", ""): v
        for k, v in packages.items()
        if k and not v.get("dev") and not v.get("devOptional")
    }

    pkg_entries = []
    for name in sorted(prod_pkgs.keys()):
        pkg_entries.append(extract_package_info(name, prod_pkgs[name]))

    out = [FONTS_SECTION.strip(), "\n---\n\n## 2. Bundled Web User Interface Packages (`web/dist`)\n\n"]
    out.append(
        "The following client-side packages are bundled into `web/dist` during the build and ship in the wheel and container image:\n\n"
    )

    for p in pkg_entries:
        out.append(f"### {p['name']} ({p['version']})\n")
        out.append(f"- License: {p['license']}\n")
        out.append(f"- Copyright: {p['copyright']}\n\n")

    out.append(MIT_TEXT)
    out.append("\n" + BSD0_TEXT)

    return "".join(out)


def main():
    content = generate_notices()
    NOTICES_FILE.write_text(content, encoding="utf-8")
    print(f"Wrote {NOTICES_FILE}")


if __name__ == "__main__":
    main()
