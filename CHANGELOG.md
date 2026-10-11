# Changelog

All notable changes to `scene-block-to-prompt` (ALIGNMENT-16 rule 93).

## v0.1.1 - 2026-10-11 (round 2: self-audit revision)

### Added
- Whole-scene coverage in compiled output: secondary subjects now appear in
  `natural` ("also in scene: ..."), `tags` (`secondary:` prefix), and `params`
  (`secondary_subjects`). Previously only the hero's tags were compiled —
  the prompt under-described multi-subject scenes. 3 new tests.
- `examples/scene.json` — a two-subject reference scene used by the README.

### Fixed
- Camera-relative "frame right/left" was mirrored (right vector used the
  left-handed convention). Caught by the composition offset tests; fixed and
  both offsets now assert the correct side.
- Self-test distance threshold for "wide shot" tightened from a boundary
  value (20 m → 30 m) that sat exactly on the 0.12 frame-ratio cutoff.

## v0.1.0 - 2026-10-11 (initial release)

### Added
- SceneBlock v0.1 format (validate + normalize), geometry-derived shot
  analysis (angle / shot size / dof / facing / composition / depth notes),
  three deterministic backends (natural, tags, params).
- CLI: `compile / validate / schema`.
- Three-tier self-test, 48 checks PASS.
