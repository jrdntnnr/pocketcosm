# Pocketcosm Roadmap — matching the Hologram Microcosm (1GB Pi 5 target)

Binding constraint is CPU/DSP headroom, not RAM. Audio buffers total ~26 MB;
the Pygame/X stack dominates memory. So the plan front-loads the topology fix
that frees CPU and treats per-effect voice count as the scarce resource.

Legend: ✅ built (untested on device) · 🔬 needs on-device verify/iteration · 🚧 TBD

## Phase 0 — `switch~` gating  ✅
Only the active effect computes DSP (`pt-modeswitch.pd` + per-effect `switch~`).
Makes an N-effect catalog cost ~one effect's DSP at a time.
`measure-pocketcosm.sh` quantifies CPU load / underruns on the Pi.

## Phase 1 — Sonic character
- 1a ✅ resonant Moog-ladder tone filter (`bob~`) replacing 1-pole `lop~`.
- 1b ✅ pitch range widened to ±24 st (UI + MIDI). "Subtle → extreme."
- 1c 🔬 reverb styles (4). `rev3~` decay/size are fixed creation args, so real
  multi-style reverb needs parallel instances or confirming `rev3~`'s runtime
  interface. A blind wiring error here blows up into the output — do it on
  device where it can be heard and bounded.

## Phase 2 — Looper parity
- ✅ Half-speed (octave-down playback) — switchable `*~` in the phasor path.
- ✅ Fade (4 s fade-to-silence; re-arms on play/record/load).

## Phase 3 — Effect breadth (4 banks)
- ✅ 12 effect characters: 4 engines × 3 variants (curated parameter macros
  per engine; UI variant row). Matches the Microcosm's effect+variation model.
- 🔬 Genuinely-new DSP algorithms (Micro Loop, Multi Delay banks) and higher
  grain-voice counts. Both want the FX-bus refactor + Phase 0 CPU numbers from
  the measurement harness, so they're on-device work.

## Phase 4 — Presets & control surface
- ✅ 16 user preset slots (engine addresses presets by line index; UI A/B bank).
- ✅ MIDI Thru (`midiin` → `midiout`).
- 🔬 MIDI clock-out (needs a master/slave toggle to avoid sync conflicts);
  bypass trails (buffered-bypass tail); expression pedal (hardware-dependent —
  pending confirmation the PocketTerm exposes an analog/GPIO input).

## Phase 5 — Validate against budget  🔬
Re-run `measure-pocketcosm.sh` with the full catalog; confirm worst-case effect
stays under the dropout threshold and resident RAM well under 1 GB. Tune voice
counts to the headroom that gating freed.

## Phase 6 — Redesign  ✅
Reimplemented the Pygame UI to the `design_handoff_pocketcosm` spec: a 1970s
Cold-War / missile-control instrument panel on the Hologram palette — cream
bakelite faceplate (bezel + corner screws), backlit annunciator lamp buttons
with machined collars and halo bloom, a phosphor radar XY scope, amber LED
readouts, brushed-metal faders, and footer pilot LEDs. All networking/state/
behavior (UDP set/action/sync) preserved; fonts bundled in `fonts/`. Pure-CSS
design recreated with pygame drawing primitives (gradients cached for the Pi).

---

# Part II — Remaining gaps vs Microcosm (prioritized)

The effect catalog is the biggest gap. The Microcosm has **11 distinct
algorithms in 4 banks** (Micro Loop, Granules, Glitch, Multi Delay); Pocketcosm
has 4 engines whose "variants" are parameter macros, and **two whole families —
Multi Delay and Micro Loop — are absent**. The redesigned UI already has the
right shape (4 bank tabs × 2–3 sub-mode effects), so most of this is DSP +
wiring, not layout. ★ = top priority · 🔬 = needs on-device iteration.

## Phase 7 — FX-bus refactor (enabler)  ✅ (built, untested on device)
`pt-modeswitch` gained a second outlet (immediate active flag); every effect
now multiplies its output by a 40 ms gain ramp from that flag and writes the
shared `pc-fx-l/r` bus, so only the active effect contributes and transitions
crossfade cleanly. `pt-output` reads `pc-fx` once. New engines now cost just a
`switch~` + gain + bus send — no `pt-output` wiring.
Note: the old per-effect mode-gating matrix in `pt-output` is left in place but
disconnected (reads now-unused sends → silent); prune in a later cleanup.

## Phase 8 — Multi Delay bank  ✅ (built, untested on device)
New tempo-synced stereo multi-tap delay engine (`pt-multidelay.pd`, mode 4):
four beat-divided taps (ping-pong L/R) with capped feedback and a safety clip.
Sub-modes DUAL / PING / SWARM (macros). Tabbed in the UI (blue).

## Phase 9 — Micro Loop bank  ✅ (built, untested on device)
New short-buffer stutter/repeat engine (`pt-microloop.pd`, mode 5): a
40–500 ms window replayed under a raised-cosine envelope (click-free), loop
length from GRAIN. Sub-modes REPEAT / STAB / STRETCH (macros). Tabbed (green).

> Implemented as a flat 6-engine catalog (modes 0–5) shown as 6 effect tabs,
> rather than re-banking to the Microcosm's 4-bank taxonomy. Delivers both
> missing algorithm families as real DSP. Re-banking/labeling can follow.

> Phases 8–9 also re-bank the four tabs to the Microcosm taxonomy
> (GRANULES · GLITCH · MULTI-DELAY · MICRO-LOOP), fold Arp/Reverse in as
> sub-modes or extras, and upgrade the placeholder macro-variants into the
> real per-bank sub-mode effects.

## Phase 10 — Tempo subdivisions / quantization  ★
Time-division selector (1/4, 1/8, 1/8T, 1/16, dotted) for every synced effect
(Glitch, Arp, Multi Delay, Micro Loop). UI control + MIDI. Cheap, high musical
payoff; a real interaction gap today.

## Phase 11 — Granular density / voice count  🔬
Raise grain-voice counts in Granules/Reverse for dense clouds, tuned to the CPU
headroom freed by Phases 0/7 (run `measure-pocketcosm.sh` first). Closes the
"thin vs dense" granular gap.

## Phase 12 — Reverb: 4 styles + decay  🔬
Selectable reverb styles (parallel instances or runtime-controlled) with
adjustable decay/size. Audio path — device session.

## Phase 13 — True stereo signal path
Stereo memory buffer + stereo-aware effects (input is currently mono-summed).
Architectural. Closes true stereo I/O.

## Phase 14 — Control & I/O completeness
MIDI clock-out / PC-out (master, with master/slave toggle), bypass trails
(buffered-bypass tail), global forward/reverse toggle, reverb pre/post routing.

## Phase 15 — Expression pedal  🔬 (hardware-gated)
Map an analog/GPIO input to parameters — pending confirmation the PocketTerm
exposes one. Closes expression control.

## Phase 16 — Depth & presets
Per-effect parameter memory (each effect recalls its own state) and factory
preset variations toward the Microcosm's 44.
