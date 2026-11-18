#!/bin/bash
set -euxo pipefail
export SLIDER_ASD_VOLUME="${SLIDER_ASD_VOLUME:-/runpod-volume}"
REPO_URL="${SLIDER_ASD_REPO:-https://github.com/devshelterua-hash/slider-asd-worker.git}"
APP_DIR="${SLIDER_ASD_VOLUME}/slider-asd-worker"
LOCK="${SLIDER_ASD_VOLUME}/.asd-bootstrap.lock"

mkdir -p "$SLIDER_ASD_VOLUME"
exec 9>"$LOCK"
echo "[bootstrap] waiting for volume lock"
flock 9
echo "[bootstrap] lock acquired"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
  git ffmpeg wget curl ca-certificates \
  libgl1 libglib2.0-0 pkg-config

if [ ! -d "$APP_DIR/.git" ]; then
  echo "[bootstrap] cloning worker repo"
  git clone --depth 1 "$REPO_URL" "$APP_DIR"
else
  echo "[bootstrap] resetting worker repo to origin/main"
  git -C "$APP_DIR" fetch origin main
  git -C "$APP_DIR" reset --hard origin/main
fi

echo "[bootstrap] pip install (legacy resolver)"
pip install --no-cache-dir --use-deprecated=legacy-resolver -r "$APP_DIR/requirements.txt"
cd "$APP_DIR"
echo "[bootstrap] ensure_talknet"
python ensure_talknet.py
echo "[bootstrap] starting handler"
exec python -u rp_handler.py
