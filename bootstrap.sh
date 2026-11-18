#!/bin/bash
set -euo pipefail
export SLIDER_ASD_VOLUME="${SLIDER_ASD_VOLUME:-/runpod-volume}"
REPO_URL="${SLIDER_ASD_REPO:-https://github.com/devshelterua-hash/slider-asd-worker.git}"
APP_DIR="${SLIDER_ASD_VOLUME}/slider-asd-worker"

apt-get update -qq
apt-get install -y -qq --no-install-recommends \
  git ffmpeg wget curl ca-certificates \
  libgl1 libglib2.0-0 pkg-config \
  >/dev/null

if [ ! -d "$APP_DIR/.git" ]; then
  git clone --depth 1 "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" pull --ff-only || true
fi

pip install --no-cache-dir -r "$APP_DIR/requirements.txt"
cd "$APP_DIR"
python ensure_talknet.py
exec python -u rp_handler.py
