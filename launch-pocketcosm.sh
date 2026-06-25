#!/bin/bash
set -eu

project_dir=/home/pi/pocketcosm
if [ -f "$project_dir/config.env" ]; then
  # shellcheck disable=SC1091
  source "$project_dir/config.env"
fi

pd_output_device=${POCKETCOSM_OUTPUT_DEVICE:-1}
pd_midi_device=${POCKETCOSM_MIDI_DEVICE:-1}
input_args="-noadc"
has_capture=0

if [ -n "${POCKETCOSM_INPUT_DEVICE:-}" ]; then
  pd_input_device=$POCKETCOSM_INPUT_DEVICE
  input_args="-audioindev $pd_input_device -inchannels 2"
  has_capture=1
else
  capture_card=$(
    arecord -l 2>/dev/null |
      awk '/^card [0-9]+:/ && $0 !~ /HDMI|Pico/ {
        gsub(":", "", $2)
        print $2
        exit
      }'
  )

  if [ -n "${capture_card:-}" ]; then
    pd_input_device=$((capture_card * 2 + 1))
    input_args="-audioindev $pd_input_device -inchannels 2"
    has_capture=1
    printf 'Pocketcosm: using USB capture card %s (Pd device %s)\n' \
      "$capture_card" "$pd_input_device" >&2
  fi
fi

if [ "$has_capture" -eq 0 ]; then
  printf 'Pocketcosm: no USB capture interface; demo/input-memory mode only\n' >&2
fi

cleanup() {
  trap - EXIT INT TERM
  if [ -n "${ui_pid:-}" ]; then
    kill "$ui_pid" 2>/dev/null || true
  fi
  if [ -n "${pd_pid:-}" ]; then
    kill "$pd_pid" 2>/dev/null || true
  fi
  wait "${ui_pid:-}" 2>/dev/null || true
  wait "${pd_pid:-}" 2>/dev/null || true
}
on_term() {
  exit 0
}
trap cleanup EXIT
trap on_term INT TERM

/usr/bin/pd \
  -nogui \
  -stderr \
  -alsa \
  -audiooutdev "$pd_output_device" \
  -outchannels 2 \
  $input_args \
  -alsamidi \
  -mididev "$pd_midi_device" \
  -audiobuf 80 \
  -blocksize 128 \
  -path /home/pi/pocketcosm \
  -open /home/pi/pocketcosm/pocketcosm-engine.pd &
pd_pid=$!

sleep 1
if ! kill -0 "$pd_pid" 2>/dev/null; then
  wait "$pd_pid"
  exit $?
fi

if [ "$has_capture" -eq 1 ]; then
  printf 'set demo 0;\n' | /usr/bin/pdsend 9001 localhost udp >/dev/null 2>&1 || true
fi

/usr/bin/python3 /home/pi/pocketcosm/pocketcosm-ui.py &
ui_pid=$!

while kill -0 "$ui_pid" 2>/dev/null; do
  if ! kill -0 "$pd_pid" 2>/dev/null; then
    kill "$ui_pid" 2>/dev/null || true
    wait "$pd_pid"
    exit $?
  fi
  sleep 1
done

wait "$ui_pid"
