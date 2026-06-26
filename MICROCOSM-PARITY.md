# PocketCosm vs Hologram Microcosm — parity assessment

Snapshot after the device-test work (gating, FX bus, resonant filter, 6 engines,
subdivisions, reverb styles, looper, MIDI, gain-staging). All items below are
**on-device load/CPU/level-verified** unless marked otherwise. Audio character
still wants a full ear pass on hardware with a real input source.

## Headline

**Roughly 80–85% of the Microcosm's feature surface.** The core identity —
always-listening granular memory + freeze, a 60 s looper, tempo-synced effects,
a resonant filter, stereo-style reverb with selectable voicings, and full MIDI
sync — is in place and balanced. The remaining gap is mostly **effect breadth /
voice depth** plus two hardware/architectural items (true stereo, expression).

## Scorecard

| Area | Microcosm | PocketCosm now | Status |
|---|---|---|---|
| Effect algorithms | 11 distinct, in 4 banks | **6 distinct engines** (Cloud·Glitch·Arp·Reverse·MultiDelay·MicroLoop) ×3 variant macros | ◐ breadth partial |
| Banks/structure | Micro Loop·Granules·Glitch·Multi Delay | 6 engines as tabs; both missing families (Multi Delay, Micro Loop) now built | ● |
| Grain density | dense overlapping clouds | ~2 voices/engine (thin); Phase 11 blocked then unblocked by gain-staging, not yet added | ◐ |
| Resonant LP filter | synth-style | `bob~` Moog ladder, cutoff+resonance | ● |
| Pitch | subtle→extreme | ±24 st | ● |
| Reverb | stereo, 4 styles | 4 styles (Room/Hall/Plate/Space), runtime `rev3~` | ● |
| Looper | 60 s, OD/rev/undo/half/fade | 60 s, record/OD/play/undo/reverse/clear/pre-post/**half-speed**/**fade** | ● |
| Subdivisions / quantize | yes | 1/4·1/8·1/8T·1/16·1/8D for synced engines | ● |
| Tap / MIDI clock / manual tempo | all | all (+ clock **out** master) | ● |
| MIDI In / Out / Thru | full | In (PC+8×CC+notes), Thru, clock-out | ● |
| Freeze / hold sampler | yes | yes | ● |
| Bypass | true + buffered trails | bypass + asymmetric trails | ● |
| User presets | 16 (+44 factory) | 16 slots (span 6 engines) + per-effect memory | ◐ no 44 factory bank |
| Wet/dry gain staging | balanced | balanced (wet≈dry after makeup fix) | ● |
| **True stereo I/O** | yes | mono memory buffer | ○ deferred |
| **Expression pedal** | mappable | none (Pi 5 has no ADC) | ○ hardware-gated |
| Forward/reverse (global) | yes | Reverse engine + looper reverse | ◐ |
| UI | hardware knobs/switches | 1970s missile-panel touchscreen (redesign) | ● (own direction) |

● in place · ◐ partial · ○ absent

## What's genuinely matched
Granular memory + freeze, the resonant filter, ±24 pitch, 4 reverb styles, the
full 60 s looper incl. half-speed/fade, tempo subdivisions, MIDI sync (in/thru/
clock-out), bypass trails, per-effect memory, and — after the gain-staging fix —
a balanced wet/dry so the effects sit at a usable level.

## The real remaining gaps (in priority order)
1. **Effect breadth & voice depth.** 6 real algorithms + parametric variants vs
   11 distinct algorithms; and the granular engines are still thin (~2 voices).
   Density is now *unblocked* (gain-staging fixed the masking) but not yet added.
2. **True stereo path.** Memory is mono-summed; needs dual buffers + stereo
   effect reads. Best done with a stereo USB interface connected to validate.
3. **Expression pedal.** Pi 5 has no analog input; needs an ADC/GPIO add-on
   before it's even possible.
4. **44 factory variations** + capturing reverb-style/subdivision in presets
   (preset format is currently the 13 sound params).

## Bottom line
Functionally it's a credible Microcosm-class instrument and exceeds it in a few
places (open/hackable, MIDI clock-out, the bespoke UI). To close the last ~15–20%
the highest-leverage work is **grain density + more effect variations** (now
unblocked), then **true stereo** and **expression** (both gated on hardware).
