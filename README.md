Turn 3D staging parameters into image-generation control instructions. Describe a scene as a SceneBlock (camera position, focal length, aperture, subject placement, facing, key light) and this compiler deterministically emits the shot language image models understand — "medium shot, eye-level, shallow depth of field, back-lit" — instead of you hand-guessing prompt words and re-rolling for composition.

If you need reproducible framing (comics, storyboards, character consistency, previs), stage first, then compile. If you enjoy prompt roulette, move along.

## Problem

AI image/video creation is converging on "stage the scene in 3D first, generate second" — one art IDE (storytold/artcraft) built its whole workflow around it: 3D set → camera control → controlled generation, replacing prompt lottery with previs discipline. The overlooked angle is that the *pipeline* — deterministic compilation from geometry to generation controls — doesn't need an art IDE, a 3D engine, or a proprietary format. A small, versioned, human-editable intermediate format plus a transparent compiler gives anyone the same control surface.

Confidence: **High (≥80%)** that the compilation rules are deterministic and correct against their own definitions (fully tested); **Medium (60-79%)** that current image models respect these control phrases reliably — model obedience varies and is outside this repo's control.

## How it works

- **SceneBlock v0.1** is the intermediate format: meters, mm, degrees — one JSON document with `camera` (position, look_at, focal, aperture), `subjects` (position, height, rotation, tags), `light` (key direction, intensity), `style` (medium, aspect).
- **analyze** derives shot language from geometry: camera angle (eye/low/high/overhead via subject-relative camera height), shot size (close-up → wide via focal × height / distance), depth of field (f-number bands), facing (azimuth vs. subject rotation), composition (lateral offset from the camera axis), plus depth notes for secondary subjects.
- **backends** render the analysis: `natural` (sentence), `tags` (comma-separated), `params` (structured dict for parameterized generators).
- **Determinism contract:** same scene in → same prompt out, byte-for-byte (tested).

## Quickstart (~5 min)

```bash
# 1. self-test (~5 s)
python self_test.py

# 2. compile the example scene (~1 min)
python main.py compile --scene examples/scene.json --backend natural

# 3. validate your own scene (~1 min to hit one clear error)
python main.py validate --scene my_scene.json

# 4. iterate (~2 min): edit focal_mm / aperture_f / rotation_y_deg, recompile,
#    diff the output — you are now versioning composition in git
```

## Why not X

| Alternative | What it does | Why not enough |
|---|---|---|
| Hand-written camera prompts | Words like "low angle, cinematic" typed by feel | Non-reproducible; no link between your intended framing and the words; drifts per session |
| ControlNet / pose-conditioned generation | Conditions on skeleton/depth images | Powerful but needs rendered reference images and model-specific plumbing; no human-readable shot language to audit or diff |
| Full 3D pipeline (Blender → render → img2img) | Complete control | Heavyweight: installs, scene files, render time; overkill when you only need the *camera language* |
| Art IDE (e.g. artcraft-style) | Integrated 3D staging + generation | Proprietary workflow; your composition lives in their tool, not as a diffable file format |

## Minimal Fallback (PLAN B)

No Python: the five rules fit on a card.

1. Camera below subject eye height → "low angle"; above → "high angle".
2. Focal < 35mm → "wide shot"; 50 → "medium"; 85+ and close → "close-up".
3. Aperture f/2 → "shallow depth of field"; f/16 → "deep focus".
4. Subject's back to camera position → "back to the camera".
5. Keep these five in a fixed order in every prompt.

You lose facing math, composition offsets, and validation — but you keep reproducible shot vocabulary.

## Design Trade-offs

Priority order: **determinism > validation strictness > expressiveness.**

- **Rule-based, not learned.** Thresholds (0.3 m eye-level band, f-number bands, frame-ratio shot bands) are published, editable constants — auditable and testable, unlike a classifier. They encode one school of cinematography, not the law.
- **Strict validation, loud errors.** NaN, degenerate view (camera == look_at), duplicate IDs, zero focal — all rejected with the field named. A compiler that guesses silently is worse than one that refuses.
- **Intermediate format is ours.** SceneBlock v0.1 is deliberately tiny and versioned; it is not USD/glTF. Translation happens in *your* exporter; this repo stays dependency-free.
- **Nearest subject = hero.** Shot size/angle are derived from one subject; multi-subject scenes get secondary mentions, not per-subject framing (roadmap).

## Limits & Second-order Effects

- **Models don't obey reliably.** Compiled phrases are the *request*; diffusion models routinely ignore "eye-level" or blend shot sizes. Measure per model before trusting (hence Medium confidence).
- **One hero per frame.** Composition and shot size are computed from the nearest subject only.
- **No occlusion, no lens physics.** No raytracing: "is the pillar blocking the hero?" is your problem.
- **Second-order effect 1 — composition monoculture:** if many creators compile from the same rule bands, generated imagery converges on the same framings — the rules become a style homogenizer.
- **Second-order effect 2 — format lock-in by accretion:** once pipelines depend on SceneBlock v0.1, fixing a bad threshold is a breaking change; that's why the version field exists and is enforced.
- **Second-order effect 3 — false precision:** a deterministic compiler outputs confident-looking language even when the scene is degenerate (hero 200m away, f/0.5). Validation catches the illegal, not the absurd.

## FAQ

**Q: Does this generate images?**
No. It compiles staging into control text/params. Bring your own generator.

**Q: Why invent SceneBlock instead of using glTF/USD?**
Those are scene *graphs*; we need a scene *brief* — 30 lines, hand-editable, diffable in git, no schema tooling. Exporters are trivial to write.

**Q: How do I add a backend (e.g. Midjourney-style flags)?**
Three functions in `main.py` (`to_natural/to_tags/to_params`) show the pattern: consume the analysis dict, emit your dialect, keep it deterministic.

**Q: When NOT to use this tool?** *(ask this first)*
- You want stochastic artistic variation — determinism is the opposite of your goal.
- You need pixel-precise control (product shots, exact poses) — use ControlNet-style conditioning instead.
- Your "scene" is a single object on a table — the staging layer adds nothing.
- You need physics-accurate lenses/occlusion — use a real 3D renderer.

**Q: Are the cinematography thresholds correct?**
They are *one reasonable convention* (35/50/85mm bands, 0.3 m eye-level tolerance), visible in `analyze()`. Disagree? Change the constants and your diffs stay honest.

## [Core Assumptions]

1. Image generation models respond measurably to camera/shot vocabulary in prompts (obedience varies by model; unverified here).
2. Composition intent can be expressed with ~6 derived quantities (angle, shot, dof, facing, composition, light) for most staging needs.
3. Users can obtain subject positions/heights in meters — from any 3D tool, a floor plan, or rough estimation.
4. Deterministic compilation is preferable to learned inference for pipelines that must be audited and diffed.
5. One hero subject per frame is an acceptable simplification for v0.1.

---
Contact: hcac4735@agent.qq.com · License: MIT · Measured: 500-subject analysis ≈3.7 ms (repro: `python self_test.py`). Model-obedience claims are flagged [unverified]. As of 2026-10-11.
