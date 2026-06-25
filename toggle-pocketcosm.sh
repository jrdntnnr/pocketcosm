#!/bin/sh
if systemctl --user is-active --quiet pocketcosm.service; then
  systemctl --user stop pocketcosm.service
else
  systemctl --user start pocketcosm.service
fi
