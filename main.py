#!/usr/bin/env python3
"""scene-block-to-prompt: compile 3D staging parameters into image-generation control instructions.

Workflow: stage a scene in any 3D tool (or by hand) -> export a SceneBlock
JSON -> compile to deterministic camera/lighting control language for image
models. Reproducible composition instead of prompt lottery.

CLI:
  python main.py compile --scene scene.json --backend natural|tags|params
  python main.py validate --scene scene.json
  python main.py schema          (print the SceneBlock v0.1 schema summary)

SceneBlock v0.1 (all units meters / mm / degrees):
{
  "version": "0.1",
  "camera": {"position": [x,y,z], "look_at": [x,y,z],
             "focal_mm": 50, "aperture_f": 2.0},
  "subjects": [{"id": "hero", "kind": "human|object",
                "position": [x,y,z], "height": 1.8,
                "rotation_y_deg": 180, "tags": ["red coat"]}],
  "light":   {"key_direction": "front|side|back|top", "intensity": "low|normal|high"},
  "style":   {"medium": "photoreal|illustration|any", "aspect": "16:9"}
}

Pure stdlib. Deterministic: same scene in, same prompt out.
"""
from __future__ import annotations

import argparse
import json
import math
import sys

FORMAT_VERSION = "0.1"
BACKENDS = ("natural", "tags", "params")

KEY_DIRECTIONS = ("front", "side", "back", "top")
INTENSITIES = ("low", "normal", "high")


class SceneError(ValueError):
    pass


# ---------------------------------------------------------------- validation
def _num(v, name):
    if not isinstance(v, (int, float)) or isinstance(v, bool) or v != v or v in (float("inf"),):
        raise SceneError(f"{name} must be a finite number, got {v!r}")
    return float(v)


def _vec3(v, name):
    if not isinstance(v, (list, tuple)) or len(v) != 3:
        raise SceneError(f"{name} must be [x, y, z]")
    return [_num(c, f"{name}[{i}]") for i, c in enumerate(v)]


def validate(scene: dict) -> dict:
    """Validate + normalize. Returns a normalized scene; raises SceneError."""
    if not isinstance(scene, dict):
        raise SceneError("scene must be a JSON object")
    version = scene.get("version", FORMAT_VERSION)
    if version != FORMAT_VERSION:
        raise SceneError(f"unsupported SceneBlock version {version!r} (want {FORMAT_VERSION})")
    cam = scene.get("camera")
    if not isinstance(cam, dict):
        raise SceneError("missing 'camera' object")
    focal = _num(cam.get("focal_mm"), "camera.focal_mm")
    if focal <= 0:
        raise SceneError("camera.focal_mm must be > 0")
    aperture = cam.get("aperture_f", 2.8)
    aperture = _num(aperture, "camera.aperture_f")
    if aperture <= 0:
        raise SceneError("camera.aperture_f must be > 0")
    pos = _vec3(cam.get("position"), "camera.position")
    look = _vec3(cam.get("look_at"), "camera.look_at")
    if pos == look:
        raise SceneError("camera.position == camera.look_at: view direction is undefined")
    subs = scene.get("subjects", [])
    if not isinstance(subs, list):
        raise SceneError("'subjects' must be a list")
    norm_subs = []
    seen_ids = set()
    for i, s in enumerate(subs):
        if not isinstance(s, dict):
            raise SceneError(f"subjects[{i}] must be an object")
        sid = s.get("id", f"subject{i}")
        if sid in seen_ids:
            raise SceneError(f"duplicate subject id {sid!r}")
        seen_ids.add(sid)
        kind = s.get("kind", "object")
        if kind not in ("human", "object"):
            raise SceneError(f"subjects[{i}].kind must be 'human' or 'object'")
        height = _num(s.get("height", 1.8 if kind == "human" else 0.5),
                      f"subjects[{i}].height")
        if height <= 0:
            raise SceneError(f"subjects[{i}].height must be > 0")
        rot = _num(s.get("rotation_y_deg", 0), f"subjects[{i}].rotation_y_deg") % 360
        tags = s.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            raise SceneError(f"subjects[{i}].tags must be a list of strings")
        norm_subs.append({"id": sid, "kind": kind, "position": _vec3(s.get("position", [0, 0, 0]), f"subjects[{i}].position"),
                          "height": height, "rotation_y_deg": rot, "tags": tags})
    light = scene.get("light", {})
    if not isinstance(light, dict):
        raise SceneError("'light' must be an object")
    kd = light.get("key_direction", "front")
    if kd not in KEY_DIRECTIONS:
        raise SceneError(f"light.key_direction must be one of {KEY_DIRECTIONS}")
    inten = light.get("intensity", "normal")
    if inten not in INTENSITIES:
        raise SceneError(f"light.intensity must be one of {INTENSITIES}")
    style = scene.get("style", {})
    if not isinstance(style, dict):
        raise SceneError("'style' must be an object")
    return {"version": version,
            "camera": {"position": pos, "look_at": look, "focal_mm": focal, "aperture_f": aperture},
            "subjects": norm_subs,
            "light": {"key_direction": kd, "intensity": inten},
            "style": {"medium": str(style.get("medium", "photoreal")),
                      "aspect": str(style.get("aspect", "1:1"))}}


# ---------------------------------------------------------------- analysis
def _dist(a, b):
    return math.dist(a, b)


def analyze(scene: dict) -> dict:
    """Derive shot language from geometry. All rules deterministic."""
    n = validate(scene)
    cam, subs = n["camera"], n["subjects"]
    if not subs:
        raise SceneError("at least one subject is required to derive shot language")

    # depth order: nearest subject drives shot size / angle
    ordered = sorted(subs, key=lambda s: _dist(cam["position"], s["position"]))
    hero = ordered[0]

    cam_y, eye_y = cam["position"][1], hero["height"] * 0.9
    dy = cam_y - eye_y
    if abs(dy) <= 0.30:
        angle = "eye-level"
    elif dy < 0:
        angle = "low-angle" if dy > -hero["height"] * 0.75 else "worm's-eye"
    else:
        angle = "high-angle" if dy < hero["height"] * 1.5 else "overhead"

    d = _dist(cam["position"], hero["position"])
    f = cam["focal_mm"]
    # normalized sharpness: focal * (subject height / distance) — classic framing
    frame_ratio = f * hero["height"] / (d * 36.0)  # 36mm full-frame width
    if frame_ratio >= 0.9:
        shot = "extreme close-up"
    elif frame_ratio >= 0.55:
        shot = "close-up"
    elif frame_ratio >= 0.30:
        shot = "medium shot"
    elif frame_ratio >= 0.12:
        shot = "full shot"
    else:
        shot = "wide shot"

    if cam["aperture_f"] <= 2.0:
        dof = "very shallow depth of field"
    elif cam["aperture_f"] <= 4.0:
        dof = "shallow depth of field"
    elif cam["aperture_f"] <= 9.0:
        dof = "moderate depth of field"
    else:
        dof = "deep focus"

    # facing: camera->hero azimuth vs hero rotation_y (0 = +z facing camera at +z)
    azimuth = math.degrees(math.atan2(cam["position"][0] - hero["position"][0],
                                      cam["position"][2] - hero["position"][2])) % 360
    rel = (azimuth - hero["rotation_y_deg"]) % 360
    if 315 <= rel or rel < 45:
        facing = "facing the camera"
    elif 45 <= rel < 135:
        facing = "turned left profile to camera"
    elif 135 <= rel < 225:
        facing = "back to the camera"
    else:
        facing = "turned right profile to camera"

    # composition: hero offset vs camera axis
    fwd = [cam["look_at"][i] - cam["position"][i] for i in range(3)]
    fwd_len = math.hypot(*fwd)
    # lateral offset of hero from the camera forward line
    to_hero = [hero["position"][i] - cam["position"][i] for i in range(3)]
    proj = sum(to_hero[i] * fwd[i] for i in range(3)) / (fwd_len ** 2)
    perp = [to_hero[i] - proj * fwd[i] for i in range(3)]
    right = [-fwd[2], 0, fwd[0]]  # camera-relative right in a y-up right-handed frame
    right_len = math.hypot(*right) or 1.0
    lateral = (perp[0] * right[0] + perp[2] * right[2]) / right_len
    if abs(lateral) < hero["height"] * 0.35:
        comp = "centered composition"
    elif lateral > 0:
        comp = "subject offset to frame right"
    else:
        comp = "subject offset to frame left"

    depth_notes = []
    if len(ordered) > 1:
        second = ordered[1]
        depth_notes.append(f"'{second['id']}' behind '{hero['id']}'" if
                           _dist(cam["position"], second["position"]) > d + 0.5
                           else f"'{second['id']}' at similar depth")

    return {"hero": hero["id"], "angle": angle, "shot": shot, "dof": dof,
            "facing": facing, "composition": comp,
            "light": f"{n['light']['key_direction']}-lit, {n['light']['intensity']} intensity",
            "hero_distance_m": round(d, 2),
            "depth_notes": depth_notes,
            "others": [s["id"] for s in ordered[1:]]}


# ---------------------------------------------------------------- backends
def _secondary_phrase(a: dict, scene: dict) -> str:
    """Describe non-hero subjects (round-2: prompts cover the whole scene)."""
    phrases = []
    for s in scene["subjects"]:
        if s["id"] == a["hero"]:
            continue
        tags = ", ".join(s["tags"]) if s["tags"] else s["kind"]
        phrases.append(f"{tags} ({s['id']})")
    return "; also in scene: " + ", ".join(phrases) if phrases else ""


def to_natural(a: dict, scene: dict) -> str:
    st = scene["style"]
    hero_tags = ", ".join(next(s["tags"] for s in scene["subjects"] if s["id"] == a["hero"]) or ["main subject"])
    s = (f"{st['medium']} image, {a['shot']} of a subject ({hero_tags}) "
         f"{a['facing']}, {a['angle']} camera, {a['dof']}, {a['composition']}, "
         f"{a['light']}, aspect ratio {st['aspect']}")
    s += _secondary_phrase(a, scene)
    if a["depth_notes"]:
        s += "; " + ", ".join(a["depth_notes"])
    return s + "."


def to_tags(a: dict, scene: dict) -> str:
    st = scene["style"]
    tags = [st["medium"], a["shot"], a["facing"], a["angle"], a["dof"],
            a["composition"], a["light"]]
    tags += [t for t in next(s["tags"] for s in scene["subjects"] if s["id"] == a["hero"])]
    for s in scene["subjects"]:  # round-2: include secondary subject tags
        if s["id"] != a["hero"]:
            tags += [f"secondary:{t}" for t in s["tags"]] or [f"secondary:{s['kind']}"]
    tags.append(f"aspect:{st['aspect']}")
    return ", ".join(dict.fromkeys(t for t in tags if t))


def to_params(a: dict, scene: dict) -> dict:
    return {"shot_type": a["shot"], "camera_angle": a["angle"],
            "depth_of_field": a["dof"], "subject_facing": a["facing"],
            "composition": a["composition"],
            "lighting": a["light"].split(", ")[0] + ", " + a["light"].split(", ")[1],
            "hero": a["hero"], "hero_distance_m": a["hero_distance_m"],
            "medium": scene["style"]["medium"], "aspect": scene["style"]["aspect"],
            "depth_notes": a["depth_notes"],
            "secondary_subjects": a["others"]}


def compile_scene(scene: dict, backend: str) -> dict:
    if backend not in BACKENDS:
        raise SceneError(f"unknown backend {backend!r}; choose from {BACKENDS}")
    a = analyze(scene)
    if backend == "natural":
        out = to_natural(a, scene)
    elif backend == "tags":
        out = to_tags(a, scene)
    else:
        out = to_params(a, scene)
    return {"backend": backend, "analysis": a, "output": out}


# ---------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="scene-block-to-prompt")
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("compile")
    sp.add_argument("--scene", required=True)
    sp.add_argument("--backend", choices=BACKENDS, default="natural")
    sp = sub.add_parser("validate"); sp.add_argument("--scene", required=True)
    sub.add_parser("schema")

    a = p.parse_args(argv)
    if a.cmd == "schema":
        print(__doc__.split("SceneBlock v0.1")[1].split("Pure stdlib")[0].strip())
        return 0
    try:
        with open(a.scene, "r", encoding="utf-8") as f:
            scene = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: cannot read scene: {e}", file=sys.stderr)
        return 2
    try:
        if a.cmd == "validate":
            validate(scene)
            print("OK: valid SceneBlock v0.1")
        else:
            print(json.dumps(compile_scene(scene, a.backend), indent=1, ensure_ascii=False))
    except SceneError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
