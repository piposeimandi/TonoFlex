#!/usr/bin/env bash
# Run the Pitch Shifter app
DIR="$(cd "$(dirname "$0")" && pwd)"
exec /tmp/audio_app_venv/bin/python "$DIR/pitch_shifter_app.py" "$@"
