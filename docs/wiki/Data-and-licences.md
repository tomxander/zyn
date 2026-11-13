# Data and licences

Zyn uses public and synthetic data only. Public datasets are downloaded to `data/public/`, which Git ignores: nothing is redistributed. Each evaluation records the sha256 of the files it used.

| Dataset | What it is | Licence | Used for |
|---|---|---|---|
| **ICX-100** ([data/synthetic/](../../data/synthetic/)) | A fictional instrument cluster: specification, revision 2, requirement set, DBC, answer key | Written for this project | End-to-end demos, review recall, Anvil, Anvil Review |
| **QuRE 1.0.1** | 2,111 requirements from automotive industrial specifications, each weak word judged a defect or acceptable by a human. Femmer, Houdek, Unterbusch et al., Zenodo 16049822 | CC BY 4.0 | Quality-flag precision and recall |
| **PROMISE NFR** | 625 requirements from student projects, functional or one of 11 non-functional classes. (c) 2007 Jane Cleland-Huang | CC BY-SA 3.0 | Requirement type classification |
| **RTEMS rtems-central** | Action requirements of a real-time OS, pinned commit 82230386, rendered into a document by Zyn's script | Files offered as CC BY-SA 4.0 or BSD-2-Clause, used under BSD-2-Clause | Extraction and grounding |
| **opendbc** | 58 CAN databases, mostly reverse-engineered by the community, pinned commit 27fa1c5d | MIT | DBC checks on real files |

## About the ICX-100 answer key

The ICX-100 specification, its DBC and its answer key were written by Claude and checked by an independent AI reviewer pass, not by an engineer. Scores against it describe that key only. Every report that uses it says so.

## Excluded

The data survey put these on hold because no sufficient licence grant was found: PURE, ReqEval, the CoEST sets (EasyClinic, CM1, eTOUR), COMET and LibEST, AUTOSAR RS CAN, Loghub, and MISRA wording inside FreeRTOS. Zenodo 7867846 is CC BY, but its requirement text comes from CoEST and COMET, so it inherits their hold.

## Fonts and marks

The wordmarks use D-DIN Condensed, an open licence font, shipped in [zyn-identity/fonts/](../../zyn-identity/fonts/). The marks and icons are drawn for Zyn.
