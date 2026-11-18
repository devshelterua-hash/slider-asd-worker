# slider-asd-worker

TalkNet Active Speaker Detection for Slider (Runpod Serverless).

- Scale-to-zero, idleTimeout 600s
- Weights cached on `/runpod-volume`
- Output contract: `{ focusX, track:[{t,focusX}], asd }`
