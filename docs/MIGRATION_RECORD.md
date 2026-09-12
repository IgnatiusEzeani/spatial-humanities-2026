# Repository separation record

The standalone Spatial Humanities 2026 repository was extracted from
`IgnatiusEzeani/spatio-textual` commit
`af511117` (`fix/sh2026-demo-release-gates`) on 12 September 2026.

## Boundary

- Reusable library code remains in `spatio-textual` and is released independently.
- Conference notebooks, teaching data, demo code, benchmark protocols, experiment
  runners and frozen results live in this repository.
- This repository does not vendor a `spatio_textual/` source tree.

## Intentional migration changes

- Paths formerly nested under the monorepo's SH2026 project directory are now
  repository-root relative.
- Package schema and evaluation-policy identifiers use the project-independent
  `spatio-textual-*` namespace introduced in package version 0.4.0.
- The deterministic holdout checksum is
  `fcd985d1727bb924d1b01a91166a1f792f7e15cf2ebf6f126d85eff1ac195453`.
- The deterministic journey development checksum is
  `34ce7c9d30739d0c051697ab7860d4fa5cf78c09e8d9efe02a9ce766860d95ec`.
- All workshop notebooks use one setup module. During rehearsal they target the
  standalone repository's `main` branch and the exact package-candidate commit;
  both references will move to release tags only after the release gates pass.

The checksum changes are caused by the intentional schema-identifier migration,
not by changes to the underlying teaching or benchmark source passages.
