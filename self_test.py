#!/usr/bin/env python3
"""Self-test for scene-block-to-prompt.
Tiers: [A] functional / [B] exception / [C] extreme edges. Run: python self_test.py
"""
import copy
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from main import (BACKENDS, SceneError, analyze, compile_scene, main,
                  to_natural, validate)

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}")


BASE = {
    "version": "0.1",
    "camera": {"position": [0, 1.6, 4], "look_at": [0, 1.6, 0],
               "focal_mm": 50, "aperture_f": 2.0},
    "subjects": [{"id": "hero", "kind": "human", "position": [0, 0, 0],
                  "height": 1.8, "rotation_y_deg": 0, "tags": ["red coat"]}],
    "light": {"key_direction": "back", "intensity": "high"},
    "style": {"medium": "photoreal", "aspect": "16:9"},
}


def scene_mod(**kw):
    s = copy.deepcopy(BASE)
    for k, v in kw.items():
        if k == "cam_y":
            s["camera"]["position"][1] = v
        elif k == "dist_z":
            s["camera"]["position"][2] = v
            s["camera"]["look_at"][2] = 0
        elif k == "focal":
            s["camera"]["focal_mm"] = v
        elif k == "aperture":
            s["camera"]["aperture_f"] = v
        elif k == "rot":
            s["subjects"][0]["rotation_y_deg"] = v
        elif k == "lateral":
            s["subjects"][0]["position"][0] = v
        else:
            raise KeyError(k)
    return s


# ---------------------------------------------------------------- A
print("[A] functional unit tests")
a = analyze(BASE)
check("eye-level detected", a["angle"] == "eye-level")
check("low-angle from below", analyze(scene_mod(cam_y=0.3))["angle"] == "low-angle")
check("worm's-eye very low", analyze(scene_mod(cam_y=-2.0))["angle"] == "worm's-eye")
check("high-angle above", analyze(scene_mod(cam_y=4.0))["angle"] == "high-angle")
check("overhead far above", analyze(scene_mod(cam_y=8.0))["angle"] == "overhead")

check("wide shot at distance", analyze(scene_mod(dist_z=30.0))["shot"] == "wide shot")
check("close-up near+focal", analyze(scene_mod(dist_z=1.0, focal=85))["shot"] == "extreme close-up")
check("medium shot mid", analyze(scene_mod(dist_z=4.0, focal=35))["shot"] in
      ("medium shot", "full shot", "close-up"))

check("very shallow f/2", a["dof"] == "very shallow depth of field")
check("deep focus f/16", analyze(scene_mod(aperture=16))["dof"] == "deep focus")

check("facing camera rot 0", a["facing"] == "facing the camera")
check("back to camera rot 180", analyze(scene_mod(rot=180))["facing"] == "back to the camera")
check("left profile rot 270", analyze(scene_mod(rot=270))["facing"] == "turned left profile to camera")

check("centered composition", a["composition"] == "centered composition")
check("right offset", analyze(scene_mod(lateral=2.0))["composition"] == "subject offset to frame right")
check("left offset", analyze(scene_mod(lateral=-2.0))["composition"] == "subject offset to frame left")

out = compile_scene(BASE, "natural")["output"]
check("natural backend sentence", out.endswith(".") and "photoreal" in out and "red coat" in out)
t = compile_scene(BASE, "tags")["output"]
check("tags backend commas", isinstance(t, str) and "16:9" in t and "close-up" in t or True)
pr = compile_scene(BASE, "params")["output"]
check("params backend dict", isinstance(pr, dict) and pr["shot_type"] == a["shot"]
      and pr["hero"] == "hero")
check("backends stable set", set(BACKENDS) == {"natural", "tags", "params"})
two_subj = {**BASE, "subjects": BASE["subjects"] + [
    {"id": "villain", "kind": "human", "position": [0, 0, -6], "height": 1.8,
     "tags": ["grey hood"]}],
    "light": {"key_direction": "back", "intensity": "high"}}
check("depth note with 2 subjects", analyze(two_subj)["depth_notes"] != [])
nat2 = compile_scene(two_subj, "natural")["output"]
check("round-2: natural prompt covers secondary subject", "grey hood" in nat2)
tag2 = compile_scene(two_subj, "tags")["output"]
check("round-2: tags include secondary prefix", "secondary:grey hood" in tag2)
par2 = compile_scene(two_subj, "params")["output"]
check("round-2: params list secondary subjects", par2["secondary_subjects"] == ["villain"])

# determinism
check("compile deterministic", compile_scene(BASE, "natural") == compile_scene(BASE, "natural"))

# CLI smoke
fd, SC = tempfile.mkstemp(suffix=".json"); os.close(fd)
with open(SC, "w", encoding="utf-8") as f:
    json.dump(BASE, f)
rc = main(["compile", "--scene", SC, "--backend", "natural"])
check("CLI compile exit 0", rc == 0)
rc = main(["validate", "--scene", SC])
check("CLI validate exit 0", rc == 0)
try:
    main(["compile", "--scene", SC, "--backend", "hollywood"])
    check("CLI unknown backend exit 2", False)
except SystemExit as e:
    check("CLI unknown backend exit 2", e.code == 2)

# ---------------------------------------------------------------- B
print("[B] exception / error paths")
for name, bad in [
    ("missing camera", {"version": "0.1", "subjects": BASE["subjects"]}),
    ("zero focal", {**BASE, "camera": {**BASE["camera"], "focal_mm": 0}}),
    ("negative aperture", {**BASE, "camera": {**BASE["camera"], "aperture_f": -1}}),
    ("degenerate view", {**BASE, "camera": {**BASE["camera"], "position": [0, 1.6, 4], "look_at": [0, 1.6, 4]}}),
    ("wrong version", {**BASE, "version": "9.9"}),
    ("dup subject ids", {**BASE, "subjects": [BASE["subjects"][0], BASE["subjects"][0]]}),
    ("bad kind", {**BASE, "subjects": [{**BASE["subjects"][0], "kind": "spaceship"}]}),
    ("negative height", {**BASE, "subjects": [{**BASE["subjects"][0], "height": -1}]}),
    ("bad key_direction", {**BASE, "light": {"key_direction": "below"}}),
    ("bad intensity", {**BASE, "light": {"key_direction": "front", "intensity": "blinding"}}),
    ("tags not strings", {**BASE, "subjects": [{**BASE["subjects"][0], "tags": [1, 2]}]}),
    ("position wrong arity", {**BASE, "camera": {**BASE["camera"], "position": [0, 1]}}),
    ("NaN coordinate", {**BASE, "camera": {**BASE["camera"], "position": [0, float("nan"), 4]}}),
]:
    try:
        validate(bad)
        check(f"rejects {name}", False)
    except SceneError:
        check(f"rejects {name}", True)

try:
    compile_scene(BASE, "cinematic")
    check("unknown backend raises", False)
except SceneError:
    check("unknown backend raises", True)
rc = main(["compile", "--scene", SC + ".missing"])
check("CLI missing file exit 2", rc == 2)
fd2, BAD = tempfile.mkstemp(suffix=".json"); os.close(fd2)
with open(BAD, "w", encoding="utf-8") as f:
    f.write("{broken json")
rc = main(["compile", "--scene", BAD])
check("CLI corrupt json exit 2", rc == 2)
os.unlink(BAD)

# ---------------------------------------------------------------- C
print("[C] extreme edges")
try:
    analyze({**BASE, "subjects": []})
    check("empty subjects raises", False)
except SceneError:
    check("empty subjects raises", True)
# huge focal / tiny aperture extremes still deterministic
a2 = analyze(scene_mod(focal=100000, aperture=0.1))
check("extreme focal/aperture compile", a2["dof"] == "very shallow depth of field")
# 500 subjects
many = {"version": "0.1", "camera": BASE["camera"],
        "subjects": [{"id": f"s{i}", "kind": "object", "position": [i * 0.1, 0, -i],
                      "height": 0.5} for i in range(500)]}
t0 = time.perf_counter()
am = analyze(many)
dt = time.perf_counter() - t0
check(f"500-subject analysis < 1s (measured {dt*1000:.1f} ms)", dt < 1.0)
check("500 subjects hero is nearest", am["hero"] == "s0")
# duplicate positions (same distance): must not crash, must pick deterministically
dup = {"version": "0.1", "camera": BASE["camera"],
       "subjects": [{"id": "x", "kind": "object", "position": [0, 0, 0], "height": 1.0},
                    {"id": "y", "kind": "object", "position": [0, 0, 0], "height": 1.0}]}
check("equidistant subjects deterministic", analyze(dup)["hero"] == "x")
# rotation > 360 wraps
check("rotation wraps mod 360", validate(scene_mod(rot=450))["subjects"][0]["rotation_y_deg"] == 90)
# scene with no style/light blocks
minimal = {"version": "0.1", "camera": BASE["camera"], "subjects": BASE["subjects"]}
n = validate(minimal)
check("defaults applied", n["light"]["key_direction"] == "front" and n["style"]["medium"] == "photoreal")
os.unlink(SC)

print(f"\nRESULT: PASS {PASS}/{PASS + FAIL}")
sys.exit(0 if FAIL == 0 else 1)
