# Benchmark serialization provenance

The standalone Spatial Humanities 2026 repository was extracted from
`IgnatiusEzeani/spatio-textual` commit `af511117` on 12 September 2026.
Reusable library code remained in `spatio-textual`; workshop materials,
benchmark specifications, experiment runners and frozen results moved here.

During that separation, package schema and evaluation-policy identifiers were
renamed to the project-independent `spatio-textual-*` namespace. This changed
the deterministic JSONL bytes and therefore the SHA-256 checksum, although the
underlying synthetic benchmark passages did not change.

| Serialization | SHA-256 | Use |
|---|---|---|
| Pre-migration | `be9c526af68230f22cb92507af69d8aacea8cbb5bd7ad5dfcf3d7c16767fdb9b` | Identifies the input cited by the original formal result documents |
| Standalone repository | `fcd985d1727bb924d1b01a91166a1f792f7e15cf2ebf6f126d85eff1ac195453` | Reconstructed and enforced by current CI and workflows |

The checksum difference must not be described as a new empirical benchmark or
silently ignored. Existing formal result documents remain historical records
and retain their recorded checksum. New runs use the standalone checksum.

The migration record establishes passage-level continuity, but checksum
continuity alone does not establish score equivalence. Pool or compare results
across the two serializations only after confirming that the identifier changes
do not alter loading, label interpretation, prediction conversion or scoring.

Any future change to passage text, annotations, offsets or evaluation semantics
requires a new benchmark version rather than another in-place checksum update.
