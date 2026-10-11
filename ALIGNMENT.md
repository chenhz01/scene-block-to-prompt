# Alignment Audit (Rules 85-100 / 16 items) — scene-block-to-prompt v0.1.1

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Safety/Ethics section | N/A | Not a security-research repo; "false precision" risk covered under Limits |
| 2 | Privacy/dezero | PASS | No secrets/real names; contact hcac4735@agent.qq.com only; grep `(sk-\|ghp_\|api[_-]?key=)` = 0 hits |
| 3 | Copyright boundary | PASS | artcraft insight restated ("previs discipline", "scene brief vs scene graph"), no copied text; MIT LICENSE present |
| 4 | Fact-check annotation | PASS | 3.7 ms/500 subjects marked *measured* + repro; model-obedience claims marked [unverified]; thresholds framed as conventions not facts |
| 5 | Confidence grading | PASS | High (≥80%) determinism/correctness vs Medium (60-79%) model obedience — both stated in Problem |
| 6 | PLAN B built-in | PASS | "Minimal Fallback (PLAN B)": 5-rule pocket card, no Python |
| 7 | Timeout preset | PASS | Quickstart "~5 min" with per-step (~5 s / ~1 min / ~1 min / ~2 min) |
| 8 | Rule-conflict arbitration | PASS | Trade-offs: determinism > validation strictness > expressiveness |
| 9 | Version changelog | PASS | CHANGELOG v0.1.0 + v0.1.1; v0.1.1 documents the mirrored-right-vector fix |
| 10 | Exemption instruction | N/A | Session-level rule |
| 11 | External-knowledge cutoff | PASS | No vendor data; footer "As of 2026-10-11"; obedience claims flagged |
| 12 | Assumption explicitness | PASS | "[Core Assumptions]" — 5 items incl. model responsiveness and meters availability |
| 13 | Logic-check trio | PASS | [A] functional 27 / [B] exception 16 / [C] edges 8 (empty subjects, 500 subjects, equidistant tie, rotation wrap, missing blocks, corrupt JSON); final: PASS 51/51 (`python self_test.py`) |
| 14 | Socratic question | PASS | FAQ "When NOT to use this tool?" — 4 anti-use-cases (stochastic art, pixel-precise, single object, lens physics) |
| 15 | Pareto improvement | PASS | v0.1.1: prompt coverage 1-subject → whole-scene (+3 backends × secondary subjects), 2 real bugs fixed (mirrored composition, boundary test); tests 48→51; traced + re-run |
| 16 | ≤60-word opener | PASS | First paragraph = 55 words; ends with explicit enjoy/move-along judgment |

Second-order effects: PASS — 3 effects (composition monoculture, format lock-in, false precision).
