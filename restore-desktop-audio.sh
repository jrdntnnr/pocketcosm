#!/bin/sh
set -u

systemctl --user start pipewire.socket pipewire-pulse.socket
systemctl --user start pipewire.service wireplumber.service

for _ in 1 2 3 4 5; do
  if systemctl --user is-active --quiet pipewire.service; then
    break
  fi
  sleep 0.2
done

systemctl --user start xdg-desktop-portal-wlr.service xdg-desktop-portal.service
exit 0
