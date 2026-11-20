
"""Run TalkNet ASD and convert speaking faces → focusX(t) track."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from ensure_talknet import ensure


def _video_size(path: str) -> tuple[int, int, float]:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "json",
            path,
        ],
        text=True,
    )
    data = json.loads(out)
    stream = (data.get("streams") or [{}])[0]
    w = int(stream.get("width") or 0)
    h = int(stream.get("height") or 0)
    dur = float(stream.get("duration") or 0)
    if dur <= 0:
        fmt = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path],
            text=True,
        ).strip()
        dur = float(fmt or 0)
    return w, h, dur


def faces_to_track(faces: list[dict[str, Any]], frame_w: int, fps: float = 25.0) -> dict[str, Any]:
    track: list[dict[str, float]] = []
    scores: list[float] = []
    for row in faces:
        frame_number = int(row.get("frame_number") or 0)
        boxes = row.get("faces") or []
        if not boxes:
            continue
        # Prefer speaking; else highest raw_score
        speaking = [b for b in boxes if b.get("speaking")]
        cand = speaking or boxes
        best = max(cand, key=lambda b: float(b.get("raw_score") or -999))
        x1 = float(best.get("x1") or 0)
        x2 = float(best.get("x2") or 0)
        cx = (x1 + x2) / 2.0
        focus = 0.5 if frame_w <= 0 else min(1.0, max(0.0, cx / frame_w))
        t = frame_number / fps
        track.append({"t": round(t, 3), "focusX": round(focus, 4)})
        scores.append(float(best.get("raw_score") or 0))

    # Compact: keep point when focus jumps >0.03 or every 0.5s
    compact: list[dict[str, float]] = []
    for p in track:
        if not compact:
            compact.append(p)
            continue
        prev = compact[-1]
        if abs(p["focusX"] - prev["focusX"]) >= 0.03 or (p["t"] - prev["t"]) >= 0.5:
            compact.append(p)
    if track and (not compact or compact[-1]["t"] != track[-1]["t"]):
        compact.append(track[-1])

    focusX = compact[len(compact) // 2]["focusX"] if compact else 0.5
    mean_score = sum(scores) / len(scores) if scores else 0.0
    speaker_ids = set()
    for row in faces:
        for b in (row.get("faces") or []):
            if b.get("speaking"):
                sid = b.get("track_id", b.get("id"))
                if sid is not None:
                    speaker_ids.add(sid)
                else:
                    speaker_ids.add(id(b))
    return {
        "focusX": focusX,
        "hits": len(track),
        "samples": len(track),
        "track": compact,
        "asd": {
            "engine": "talknet",
            "speakers": len(speaker_ids),
            "meanScore": round(mean_score, 3),
            "rawPoints": len(track),
        },
    }


_MODEL = None
_DET = None


def get_models():
    global _MODEL, _DET
    if _MODEL is None:
        ensure()
        from demoTalkNet import setup  # type: ignore
        _MODEL, _DET = setup()
    return _MODEL, _DET


def run_talknet_focus(video_path: str, max_seconds: float = 30.0) -> dict[str, Any]:
    talknet_dir = ensure()
    os.chdir(talknet_dir)
    if str(talknet_dir) not in sys.path:
        sys.path.insert(0, str(talknet_dir))

    w, h, dur = _video_size(video_path)
    end = min(dur, max_seconds) if max_seconds > 0 else dur
    s, DET = get_models()
    from demoTalkNet import main  # type: ignore

    faces = main(
        s,
        DET,
        video_path,
        start_seconds=0,
        end_seconds=end if end > 0 else None,
        return_visualization=False,
        in_memory_threshold=2500,
    )
    fps = max(1.0, (len(faces or []) / end) if end > 0 and faces else 25.0)
    # Prefer container fps from ffprobe when available
    try:
        import json as _json
        meta = _json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate", "-of", "json", video_path,
        ], text=True))
        rate = ((meta.get("streams") or [{}])[0].get("r_frame_rate") or "25/1")
        num, den = rate.split("/")
        fps = float(num) / float(den or 1)
    except Exception:
        pass
    result = faces_to_track(faces or [], frame_w=w, fps=fps)
    result["asd"]["frameW"] = w
    result["asd"]["frameH"] = h
    result["asd"]["durationSec"] = round(end, 2)
    return result


if __name__ == "__main__":
    path = sys.argv[1]
    print(json.dumps(run_talknet_focus(path), indent=2))
