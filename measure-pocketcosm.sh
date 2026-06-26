#!/bin/bash
# Measure Pocketcosm DSP load and audio stability on the target hardware.
#
# Launches the Pd engine headless (no UI, demo input so DSP is busy), cycles
# through the four effect modes, samples the pd process CPU% and RSS for each,
# and counts ALSA underrun / resync warnings from Pd's stderr.
#
# Use it to (a) see which effect is the most expensive (drives voice-count
# budgeting for the bank phases) and (b) confirm the switch~ gating win:
#   git stash         # remove gating
#   ./measure-pocketcosm.sh
#   git stash pop     # restore gating
#   ./measure-pocketcosm.sh
# Total CPU should drop markedly once only the active effect computes.
set -u

project_dir="${POCKETCOSM_DIR:-$(cd "$(dirname "$0")" && pwd)}"
[ -f "$project_dir/config.env" ] && . "$project_dir/config.env"

pd_bin="${PD_BIN:-/usr/bin/pd}"
pdsend_bin="${PDSEND_BIN:-/usr/bin/pdsend}"
out_dev="${POCKETCOSM_OUTPUT_DEVICE:-1}"
seconds_per_mode="${SECONDS_PER_MODE:-6}"
log="$(mktemp -t pocketcosm-measure.XXXXXX.log)"
names=(CLOUD GLITCH ARP REVERSE)

command -v "$pd_bin" >/dev/null || { echo "pd not found at $pd_bin" >&2; exit 1; }
command -v "$pdsend_bin" >/dev/null || { echo "pdsend not found at $pdsend_bin" >&2; exit 1; }

echo "RAM before launch:"; free -m | awk 'NR==1||/Mem:/'

"$pd_bin" -nogui -stderr -alsa \
  -audiooutdev "$out_dev" -outchannels 2 -noadc \
  -audiobuf 80 -blocksize 128 \
  -path "$project_dir" \
  -open "$project_dir/pocketcosm-engine.pd" 2>"$log" &
pd_pid=$!
trap 'kill "$pd_pid" 2>/dev/null; rm -f "$log"' EXIT

sleep 3
kill -0 "$pd_pid" 2>/dev/null || { echo "Pd exited at startup. Log:" >&2; cat "$log" >&2; exit 1; }

# Average %CPU of the pd process over N seconds (single-thread DSP, so <100).
sample_cpu() {
  local secs="$1" iters=$(( $1 * 2 ))
  local i c
  : >/tmp/.pccpu
  for ((i=0; i<iters; i++)); do
    c=$(ps -o %cpu= -p "$pd_pid" 2>/dev/null | tr -d ' ')
    [ -n "$c" ] && echo "$c" >>/tmp/.pccpu
    sleep 0.5
  done
  awk '{s+=$1; n++} END{ if(n) printf "%.1f", s/n; else print "n/a" }' /tmp/.pccpu
}

printf '\n%-10s %-12s\n' "MODE" "CPU% (avg)"
for m in 0 1 2 3; do
  printf 'set mode %s;\n' "$m" | "$pdsend_bin" 9001 localhost udp >/dev/null 2>&1
  sleep 1
  cpu=$(sample_cpu "$seconds_per_mode")
  printf '%-10s %-12s\n' "${names[$m]}" "$cpu"
done

rss=$(ps -o rss= -p "$pd_pid" 2>/dev/null | tr -d ' ')
echo
echo "Pd resident memory: $(( ${rss:-0} / 1024 )) MB"
echo "RAM after run:"; free -m | awk '/Mem:/'

xruns=$(grep -ciE 'resync|underflow|overflow|did not complete|ALSA.*error' "$log" || true)
echo
echo "ALSA underrun/resync warnings: $xruns"
if [ "${xruns:-0}" -gt 0 ]; then
  echo "--- matching Pd log lines ---"
  grep -iE 'resync|underflow|overflow|did not complete|ALSA.*error' "$log" | head -n 20
fi
echo "(full Pd log retained until exit: $log)"
