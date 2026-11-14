# Third-Party Notices and Licenses

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
---

## 2. Bundled Web User Interface Packages (`web/dist`)

The following client-side packages are bundled into `web/dist` during the build and ship in the wheel and container image:

### @floating-ui/core (1.8.0)
- License: MIT
- Copyright: Copyright (c) 2021-present Floating UI contributors

### @floating-ui/dom (1.8.0)
- License: MIT
- Copyright: Copyright (c) 2021-present Floating UI contributors

### @floating-ui/react-dom (2.1.9)
- License: MIT
- Copyright: Copyright (c) 2021-present Floating UI contributors

### @floating-ui/utils (0.2.12)
- License: MIT
- Copyright: Copyright (c) 2021-present Floating UI contributors

### @formkit/auto-animate (0.10.2)
- License: MIT
- Copyright: Copyright 2022 FormKit Inc.

### @number-flow/react (0.6.2)
- License: MIT
- Copyright: Copyright (c) 2024 Maxwell Barvian

### @radix-ui/number (1.1.3)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/primitive (1.2.0)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-accessible-icon (1.2.0)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-accordion (1.3.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-alert-dialog (1.2.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-arrow (1.1.17)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-aspect-ratio (1.2.0)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-avatar (1.3.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-checkbox (1.4.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-collapsible (1.2.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-collection (1.2.0)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-compose-refs (1.1.5)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-context (1.3.0)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-context-menu (2.4.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-dialog (1.3.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-direction (1.2.0)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-dismissable-layer (1.2.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-dropdown-menu (2.2.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-focus-guards (1.2.0)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-focus-scope (1.3.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-form (0.3.0)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-hover-card (1.2.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-id (1.1.4)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-label (2.1.17)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-menu (2.2.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-menubar (1.2.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-navigation-menu (1.4.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-one-time-password-field (0.2.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-password-toggle-field (0.2.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-popover (1.3.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-popper (1.4.0)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-portal (1.2.0)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-presence (1.1.11)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-primitive (2.2.0)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-progress (1.2.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-radio-group (1.5.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-roving-focus (1.2.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-scroll-area (1.4.0)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-select (2.4.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-separator (1.2.0)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-slider (1.6.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-slot (1.5.0)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-switch (1.4.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-tabs (1.2.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-toast (1.3.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-toggle (1.2.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-toggle-group (1.2.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-toolbar (1.2.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-tooltip (1.4.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-use-callback-ref (1.1.5)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-use-controllable-state (1.3.0)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-use-effect-event (0.0.5)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-use-escape-keydown (1.1.6)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-use-is-hydrated (0.1.3)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-use-layout-effect (1.1.4)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-use-previous (1.1.4)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-use-rect (1.1.4)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-use-size (1.1.5)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/react-visually-hidden (1.2.13)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @radix-ui/rect (1.1.3)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### @tanstack/query-core (5.107.1)
- License: MIT
- Copyright: Copyright (c) 2021-present Tanner Linsley

### @tanstack/react-query (5.107.1)
- License: MIT
- Copyright: Copyright (c) 2021-present Tanner Linsley

### aria-hidden (1.2.6)
- License: MIT
- Copyright: Copyright (c) 2017 Anton Korzunov

### cmdk (1.1.1)
- License: MIT
- Copyright: Copyright (c) 2022 Paco Coursey

### detect-node-es (1.1.0)
- License: MIT
- Copyright: Copyright (c) 2017 Ilya Kantor

### esm-env (1.2.2)
- License: MIT
- Copyright: Copyright 2022 Benjamin McCann

### framer-motion (14.13.0)
- License: MIT
- Copyright: Copyright (c) 2018 Framer B.V.

### get-nonce (1.0.1)
- License: MIT
- Copyright: Copyright (c) 2020 Anton Korzunov

### js-tokens (4.0.0)
- License: MIT
- Copyright: Copyright (c) 2014, 2015, 2016, 2017, 2018 Simon Lydell

### loose-envify (1.4.0)
- License: MIT
- Copyright: Copyright (c) 2015 Andres Suarez <zertosh@gmail.com>

### motion (14.13.0)
- License: MIT
- Copyright: Copyright (c) 2024 [Motion](https://motion.dev) B.V.

### motion-dom (14.13.0)
- License: MIT
- Copyright: Copyright (c) 2024 [Motion](https://motion.dev) B.V.

### motion-utils (14.7.0)
- License: MIT
- Copyright: Copyright (c) 2024 [Motion](https://motion.dev) B.V.

### number-flow (0.6.2)
- License: MIT
- Copyright: Copyright (c) 2024 Maxwell Barvian

### radix-ui (1.8.1)
- License: MIT
- Copyright: Copyright (c) 2022 WorkOS

### react (18.3.1)
- License: MIT
- Copyright: Copyright (c) Facebook, Inc. and its affiliates.

### react-dom (18.3.1)
- License: MIT
- Copyright: Copyright (c) Facebook, Inc. and its affiliates.

### react-remove-scroll (2.7.2)
- License: MIT
- Copyright: Copyright (c) 2017 Anton Korzunov

### react-remove-scroll-bar (2.3.8)
- License: MIT
- Copyright: Copyright (c) Anton Korzunov <thekashey@gmail.com>

### react-style-singleton (2.2.3)
- License: MIT
- Copyright: Copyright (c) 2017 Anton Korzunov

### scheduler (0.23.2)
- License: MIT
- Copyright: Copyright (c) Facebook, Inc. and its affiliates.

### sonner (2.0.8)
- License: MIT
- Copyright: Copyright (c) 2023 Emil Kowalski

### tslib (2.9.1)
- License: 0BSD
- Copyright: Copyright (c) Microsoft Corporation.

### use-callback-ref (1.3.3)
- License: MIT
- Copyright: Copyright (c) 2017 Anton Korzunov

### use-sidecar (1.1.3)
- License: MIT
- Copyright: Copyright (c) 2017 Anton Korzunov

### vaul (1.1.2)
- License: MIT
- Copyright: Copyright (c) 2023 Emil Kowalski

#### Standard MIT License Text

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

#### Standard 0BSD License Text

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.
