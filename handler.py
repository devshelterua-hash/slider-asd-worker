
"""Runpod Serverless handler — Slider ASD TalkNet."""
from __future__ import annotations

import base64
import os
import tempfile
import traceback
import urllib.request
from typing import Any

from talknet_focus import run_talknet_focus


def _download(url: str, dest: str, timeout: int = 180) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "slider-asd/talknet"})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as out:
        out.write(resp.read())


def process_job(job_input: dict[str, Any]) -> dict[str, Any]:
    video_url = job_input.get("videoUrl") or job_input.get("video_url")
    video_b64 = job_input.get("videoBase64") or job_input.get("video_base64")
    max_seconds = float(job_input.get("maxSeconds") or os.environ.get("ASD_MAX_SECONDS") or 30)

    if not video_url and not video_b64:
        return {"error": "missing_video", "message": "Provide videoUrl or videoBase64"}

    with tempfile.TemporaryDirectory(prefix="slider-asd-") as tmp:
        path = os.path.join(tmp, "window.mp4")
        if video_url:
            _download(str(video_url), path)
        else:
            with open(path, "wb") as f:
                f.write(base64.b64decode(str(video_b64), validate=False))
        out = run_talknet_focus(path, max_seconds=max_seconds)
        if "jobId" in job_input:
            out["jobId"] = job_input["jobId"]
        if "clipId" in job_input:
            out["clipId"] = job_input["clipId"]
        return out


def handler(event: dict[str, Any]) -> dict[str, Any]:
    try:
        job_input = event.get("input") if isinstance(event, dict) else None
        if not isinstance(job_input, dict):
            return {"error": "invalid_input", "message": "expected { input: {...} }"}
        return process_job(job_input)
    except Exception as exc:  # noqa: BLE001
        return {
            "error": "asd_failed",
            "message": str(exc),
            "trace": traceback.format_exc()[-2000:],
        }
