# -*- coding: utf-8 -*-
"""{作者}周采集 · Whisper 转写（faster-whisper）

用法:
  python transcribe_fw.py <音视频文件> <输出目录> [--model large-v3]

铁律：模型优先级 large-v3 > medium，禁用 tiny。
      HF_HUB_OFFLINE=1 + local_files_only + int8 + cpu。
      只能用 Python 3.12：C:\\Users\\<你的用户名>\\AppData\\Local\\Programs\\Python\\Python312\\python.exe
"""
import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

MODEL_CHAIN = ["large-v3", "medium"]


def fmt_ts(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return "%02d:%02d:%06.3f" % (h, m, s)


def fmt_srt(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("media")
    ap.add_argument("outdir")
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--language", default="zh")
    args = ap.parse_args()

    from faster_whisper import WhisperModel

    src = Path(args.media)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    stem = src.stem

    chain = [args.model] + [m for m in MODEL_CHAIN if m != args.model]
    segs, info, used, last_err = None, None, None, None
    for name in chain:
        if name == "tiny":
            continue
        try:
            model = WhisperModel(name, device="cpu", compute_type="int8",
                                 local_files_only=True, cpu_threads=4)
            print("[model] loaded %s (cpu/int8/local_files_only)" % name)
            segments, info = model.transcribe(
                str(src),
                language=args.language,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
                condition_on_previous_text=False,
            )
            segs = [{"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip()}
                    for s in segments]
            used = name
            del model
            break
        except Exception as e:  # noqa
            last_err = e
            print("[model] %s 失败: %s" % (name, e))
    if segs is None:
        print("FAIL: 无可用模型 %s" % last_err)
        return 2

    lines_srt, lines_timed, lines_plain = [], [], []
    for i, s in enumerate(segs, 1):
        lines_srt.append("%d\n%s --> %s\n%s\n" % (i, fmt_srt(s["start"]), fmt_srt(s["end"]), s["text"]))
        lines_timed.append("[%s -> %s] %s" % (fmt_ts(s["start"]), fmt_ts(s["end"]), s["text"]))
        lines_plain.append(s["text"])

    (outdir / (stem + ".srt")).write_text("\n".join(lines_srt), encoding="utf-8")
    (outdir / (stem + ".timed.txt")).write_text("\n".join(lines_timed), encoding="utf-8")
    (outdir / (stem + ".plain.txt")).write_text("\n".join(lines_plain), encoding="utf-8")
    (outdir / (stem + ".segments.json")).write_text(
        json.dumps({"model": used, "duration": getattr(info, "duration", None),
                    "language": getattr(info, "language", None), "segments": segs},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    dur = getattr(info, "duration", 0) or 0
    print("OK model=%s duration=%.1fs segments=%d chars=%d" % (used, dur, len(segs), sum(len(x) for x in lines_plain)))
    print("OUT %s" % (outdir / (stem + ".timed.txt")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
