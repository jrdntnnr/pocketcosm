# Pocketcosm Roadmap — matching the Hologram Microcosm (1GB Pi 5 target)

Binding constraint is CPU/DSP headroom, not RAM. Audio buffers total ~26 MB;
the Pygame/X stack dominates memory. So the plan front-loads the topology fix
that frees CPU and treats per-effect voice count as the scarce resource.

## Phase 0 — `switch~` gating  ✅ (PR #1)
Only the active effect computes DSP (`pt-modeswitch.pd` + per-effect `switch~`).
Makes an N-effect catalog cost ~one effect's DSP at a time.
Includes `measure-pocketcosm.sh` to quantify CPU load / underruns on the Pi.

## Phase 1 — Sonic character
- 1a ✅ (PR #1): resonant Moog-ladder tone filter (`bob~`) replacing 1-pole `lop~`.
- 1b ✅: pitch range widened to ±24 st (UI + MIDI). "Subtle → extreme."
- 1c ⏳: reverb styles (4 selectable). **Gated on Pi verification** — the reverb/
  feedback section is where a blind wiring error is audible/dangerous.

## Phase 2 — Looper parity  ⏳
Half-speed (octave-down read) and loop fade/decay. Reuses existing arrays.

## Phase 3 — Effect breadth: 4 → 11 in 4 banks  ⏳
Reorganize into the Microcosm's families and fill them out:
Micro Loop (3, new), Granules (3), Glitch (3), Multi Delay (2, new); keep Arp +
Reverse as extras. Cheap at runtime thanks to Phase 0 gating; cost is authoring +
the bank→effect UI layer. Voice counts tuned against Phase 0 measurements.

## Phase 4 — Presets & control surface
- ✅: 16 user preset slots (engine addresses presets by line index; UI A/B bank).
- ⏳: MIDI Out/Thru (currently input-only); bypass trails; expression pedal
  (hardware-dependent — pending confirmation the PocketTerm exposes an input).

## Phase 5 — Validate against budget  ⏳
Re-run `measure-pocketcosm.sh` with the full catalog; confirm worst-case effect
stays under the dropout threshold and resident RAM well under 1GB.

## Phase 6 — Redesign  🚧 (to be defined)
Final pass. Scope TBD with the user. Expected to unify the UI that earlier phases
extended functionally-but-roughly (16-preset surface, bank navigation, reverb-style
and looper controls) into a cohesive, polished interface.
