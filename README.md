# Pocketcosm

A lightweight Pure Data granular memory effect for PocketTerm35 / Raspberry Pi 5,
with a dedicated native Pygame touchscreen interface.

## Requirements

- Raspberry Pi OS or Debian on a Raspberry Pi 5
- Pure Data 0.55 or newer
- Python 3 and Pygame 2
- ALSA output
- Optional class-compliant USB audio interface for live input

## Installation

Clone the project to `/home/pi/pocketcosm`, then install the included user
service and desktop launcher:

```sh
mkdir -p ~/.config/systemd/user ~/Desktop
cp deploy/pocketcosm.service ~/.config/systemd/user/
cp deploy/Pocketcosm.desktop ~/Desktop/
chmod +x launch-pocketcosm.sh restore-desktop-audio.sh toggle-pocketcosm.sh \
  ~/Desktop/Pocketcosm.desktop
systemctl --user daemon-reload
```

The supplied service and patches currently target the PocketTerm user and path
`/home/pi/pocketcosm`.

Optional audio and MIDI device overrides can be placed in `config.env`; start
from `config.env.example`. When a USB capture device is found, Demo input is
disabled automatically.

Interface:

- Perform: effect mode, per-engine variant row (three variants each),
  Texture/Density XY pad, macro controls, Freeze, Capture, and Bypass
- Loop: record, play, overdub, undo, reverse, pre/post routing, half-speed,
  fade, loop progress, and hold-to-clear
- Edit: 16 presets (A/B banks) and detailed sound controls
- Tap the bottom navigation bar or press Tab to change pages
- Tap the EXIT button in the top-right corner to close Pocketcosm
- Press F10 to close Pocketcosm

Controls:

- Space: freeze/unfreeze
- 1: demo generator on/off
- 2 / 3 / 4 / 5: Cloud / Glitch / Arp / Reverse
- T: tap tempo
- Q / W: short or long grains
- A / S: lower or higher wet mix
- Z / X: lower or higher feedback
- C / V: lower or higher reverb space
- F / G: darker or brighter tone
- R / O / P: record / overdub / play
- U / Y / Backspace: undo / reverse / clear
- L: switch looper recording between pre- and post-effects
- 6 / 7 / 8 / 9: recall presets
- 0: save the selected preset
- B / N: octave down / up pitch voice
- D / E: lower / higher rhythmic density
- I / K: lower / higher onset sensitivity

Modes:

- Cloud: overlapping diffuse grains
- Glitch: tempo-quantized random micro-cuts
- Arp: sequenced memory taps with resonant pitch coloring
- Reverse: overlapping backward fragments

The main effect memory is an always-listening eight-second rolling buffer.
Freeze stops new input from replacing that memory; the separate phrase looper
is optional.

The PocketTerm hardware exposes playback only. A class-compliant USB audio
interface is detected automatically at launch and used for live stereo input;
otherwise enable DEMO.

Phrase looper:

- Up to 60 seconds
- Record, overdub, play, undo, reverse, half-speed, fade, and clear
- Pre/post-effects recording route

MIDI:

- MIDI clock sets tempo
- Program changes 0-3 select modes
- Program changes 4-7 recall presets
- CC 1 mix, 2 feedback, 3 grain, 4 space, 5 tone, 6 density,
  7 pitch, 8 pitch mix
- Notes 36-40 control record, play, freeze, overdub, and undo
- Incoming MIDI is echoed to the MIDI output (Thru)

Launch or stop the app with the `Pocketcosm` desktop icon, or run:

```sh
/home/pi/pocketcosm/toggle-pocketcosm.sh
```

Stopping Pocketcosm restores the normal PipeWire desktop audio services.
