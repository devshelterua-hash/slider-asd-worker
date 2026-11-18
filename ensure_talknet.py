
"""Clone fast-asd TalkNet + download weights onto persistent volume (once)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

VOLUME = Path(os.environ.get("SLIDER_ASD_VOLUME", "/runpod-volume"))
TALKNET_DIR = VOLUME / "fast-asd" / "talknet"
WEIGHTS = Path(os.environ.get(
    "TALKNET_WEIGHTS",
    str(Path.home() / ".cache" / "models" / "pretrain_TalkSet.model"),
))
S3FD = TALKNET_DIR / "model" / "faceDetector" / "s3fd" / "sfd_face.pth"


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd)


def ensure() -> Path:
    VOLUME.mkdir(parents=True, exist_ok=True)
    if not TALKNET_DIR.exists():
        run([
            "git", "clone", "--depth", "1",
            "https://github.com/sieve-community/fast-asd.git",
            str(VOLUME / "fast-asd"),
        ])
    WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
    if not WEIGHTS.is_file():
        run([
            "gdown",
            "https://drive.google.com/uc?id=1J-PDWDAkYCdT8T2Nxn3Q_-iOHH_t-9YP",
            "-O", str(WEIGHTS),
        ])
    if not S3FD.is_file():
        S3FD.parent.mkdir(parents=True, exist_ok=True)
        run([
            "wget", "-O", str(S3FD),
            "https://storage.googleapis.com/mango-public-models/sfd_face.pth",
        ])
    # Make demoTalkNet find the weights path it hardcodes
    hardcoded = Path("/root/.cache/models/pretrain_TalkSet.model")
    if WEIGHTS.resolve() != hardcoded.resolve():
        hardcoded.parent.mkdir(parents=True, exist_ok=True)
        if not hardcoded.exists():
            try:
                hardcoded.symlink_to(WEIGHTS)
            except OSError:
                import shutil
                shutil.copy2(WEIGHTS, hardcoded)
    sys.path.insert(0, str(TALKNET_DIR))
    return TALKNET_DIR


if __name__ == "__main__":
    print(ensure())
