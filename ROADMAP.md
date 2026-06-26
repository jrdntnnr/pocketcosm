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
