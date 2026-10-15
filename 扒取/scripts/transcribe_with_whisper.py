# -*- coding: utf-8 -*-
"""
Whisper 批量转写脚本 - 视频号视频 → SRT 逐字稿
========================================================================
输入：02-Whisper转写/视频源文件/ 下的 .mp4 / .mov / .mkv
输出：02-Whisper转写/转写结果/ 下对应的 .srt（带时间戳）+ .txt（纯文本）
========================================================================
使用 faster-whisper（CTranslate2 后端，比原版 Whisper 快 4-10 倍）
首次跑会下载 large-v3 模型到 ~/.cache/huggingface/
"""

import os
import sys
from pathlib import Path

# ============== 关键：设置国内镜像（HuggingFace 在国内访问受限） ==============
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "120")

BASE_DIR = Path(r"{工作目录}\陈述出海视频号")
SRC_DIR = BASE_DIR / "02-Whisper转写" / "视频源文件"
DST_DIR = BASE_DIR / "02-Whisper转写" / "转写结果"

DST_DIR.mkdir(parents=True, exist_ok=True)

# 模型选择：
#   tiny / base / small / medium / large-v1 / large-v2 / large-v3
#   large-v3 中文识别率最高，模型 3GB
MODEL_SIZE = "large-v3"

# 计算类型：
#   float16（GPU 模式，最快）
#   int8（CPU 模式，推荐笔记本/无独显）
#   float32（精度最高但慢）
COMPUTE_TYPE = "int8"

# 支持的视频格式
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".flv", ".webm", ".m4a", ".mp3"}


def format_timestamp(seconds: float) -> str:
    """SRT 时间戳格式：HH:MM:SS,mmm"""
    ms = int((seconds - int(seconds)) * 1000)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def transcribe_one(model, video_path: Path, dst_dir: Path) -> dict:
    """转写单个视频，输出 SRT + TXT"""
    print(f"\n▶ 处理：{video_path.name}")
    print(f"  路径：{video_path}")
    print(f"  大小：{video_path.stat().st_size / 1024 / 1024:.1f} MB")

    # 输出路径
    base_name = video_path.stem
    srt_path = dst_dir / f"{base_name}.srt"
    txt_path = dst_dir / f"{base_name}.txt"

    if srt_path.exists():
        print(f"  ⏭️  已存在，跳过：{srt_path.name}")
        return {"skipped": True, "path": srt_path}

    # 转写
    print(f"  🎙️  Whisper {MODEL_SIZE} 转写中...")
    segments, info = model.transcribe(
        str(video_path),
        language="zh",
        beam_size=5,
        vad_filter=True,  # 静音过滤，提速
        vad_parameters={"min_silence_duration_ms": 500},
    )

    duration = info.duration
    print(f"  📊 视频时长：{duration:.1f} 秒，检测语言：{info.language}")

    # 写 SRT
    srt_content = []
    txt_content = []
    seg_count = 0

    for i, seg in enumerate(segments, 1):
        srt_content.append(f"{i}")
        srt_content.append(f"{format_timestamp(seg.start)} --> {format_timestamp(seg.end)}")
        srt_content.append(seg.text.strip())
        srt_content.append("")  # 空行
        txt_content.append(seg.text.strip())
        seg_count += 1

    srt_path.write_text("\n".join(srt_content), encoding="utf-8")
    txt_path.write_text("\n".join(txt_content), encoding="utf-8")

    print(f"  ✅ 完成：{seg_count} 段")
    print(f"     SRT → {srt_path.relative_to(BASE_DIR)}")
    print(f"     TXT → {txt_path.relative_to(BASE_DIR)}")

    return {
        "ok": True,
        "segments": seg_count,
        "duration": duration,
        "srt": srt_path,
        "txt": txt_path,
    }


def main():
    # 1. 检查源目录
    if not SRC_DIR.exists():
        SRC_DIR.mkdir(parents=True)
        print(f"❌ 源目录不存在，已自动创建：{SRC_DIR}")
        print(f"   请把视频文件 (.mp4) 放到这个目录下")
        sys.exit(1)

    # 2. 扫视频文件
    videos = sorted(
        p for p in SRC_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_EXT
    )

    if not videos:
        print(f"❌ 源目录 {SRC_DIR} 下没有视频文件")
        print(f"   支持的格式：{', '.join(VIDEO_EXT)}")
        sys.exit(1)

    print(f"📂 找到 {len(videos)} 个视频文件")
    print(f"🤖 模型：Whisper {MODEL_SIZE}（首次跑会下载 ~3GB）")
    print(f"💻 计算类型：{COMPUTE_TYPE}")
    print("=" * 60)

    # 3. 加载模型
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("❌ faster-whisper 未安装")
        print("   请先在 AI 端 venv 安装：")
        print('   "C:/Users/<你的用户名>/.workbuddy/binaries/python/envs/whisper/python.exe" -m pip install faster-whisper')
        sys.exit(1)

    print(f"\n⏳ 加载模型 {MODEL_SIZE}...")
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE)
    print(f"✅ 模型加载完成")

    # 4. 逐个转写
    success = 0
    failed = []
    total_duration = 0.0

    for i, video in enumerate(videos, 1):
        print(f"\n[{i}/{len(videos)}]")
        try:
            result = transcribe_one(model, video, DST_DIR)
            if result.get("ok") or result.get("skipped"):
                success += 1
                total_duration += result.get("duration", 0)
        except Exception as e:
            print(f"  ❌ 失败：{e}")
            failed.append((video.name, str(e)))

    # 5. 总结
    print("\n" + "=" * 60)
    print(f"✅ 成功：{success} / {len(videos)}")
    print(f"📊 累计转写时长：{total_duration / 60:.1f} 分钟")
    if failed:
        print(f"❌ 失败 {len(failed)}：")
        for name, err in failed:
            print(f"   - {name}: {err}")
    print(f"\n输出目录：{DST_DIR}")


if __name__ == "__main__":
    main()
