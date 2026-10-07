#!/usr/bin/env bash
# Stop the LIMS API and web app started by run-on-mac.sh or .devcontainer/start.sh.
for name in api web; do
  if [ -f "/tmp/lims-$name.pid" ]; then
    kill -- "-$(cat "/tmp/lims-$name.pid")" 2> /dev/null || true
    rm -f "/tmp/lims-$name.pid"
  fi
done
echo "DNA LIMS stopped."
