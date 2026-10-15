# -*- coding: utf-8 -*-
"""
collect_videos_xhs.py - 小红书视频源文件归集 + 重命名工具
=========================================================================
【功能】
把 MediaCrawler 下载目录里以 note_id 命名的视频（如
  6a71c96d000000002701d65d.mp4）
按本地 `01-视频清单/note_id_to_seq.json` 映射关系，归集到项目
  02-Whisper转写/视频源文件/{NNN}-{完整标题}.mp4

【使用方式】
1. 把脚本拷到项目 99-生成脚本/ 下
2. 根据实际情况修改 BASE_DIR 和 SOURCE_DIR（MediaCrawler 的 videos 目录）
3. 跑：`python collect_videos_xhs.py`

【依赖】
- 标准库 only（无第三方依赖）
- 需要预先有 `01-视频清单/note_id_to_seq.json`（note_id → NNN 映射）

【输出】
- 复制（不删除）源文件到目标路径
- 输出重命名对照表 + 失败原因

=========================================================================
"""
import json
import os
import re
import shutil
import sys
from pathlib import Path

# ============== 用户自定义区（按实际项目改） ==============
# BASE_DIR = 项目根目录（含 01-视频清单/02-Whisper转写/）
# SOURCE_DIR = MediaCrawler 的 videos 输出目录
# 一般为 <MediaCrawler>/data/xhs/videos/

BASE_DIR = Path(r"{工作目录}\xhs_示例博主")
SOURCE_DIR = BASE_DIR.parent.parent / "MediaCrawler" / "data" / "xhs" / "videos"
# 兜底写法：脚本找不到时让用户填
# SOURCE_DIR = Path(r"<MediaCrawler>/data/xhs/videos")

# ============== 内部逻辑（无需改） ==============
INDEX_FILE = BASE_DIR / "01-视频清单" / "note_id_to_seq.json"
TARGET_DIR = BASE_DIR / "02-Whisper转写" / "视频源文件"


def safe(name: str, max_len: int = 60) -> str:
    """统一文件名清洗规则：与 generate_md_timed.py / whisper_transcribe.py 同源"""
    name = re.sub(r'[\\/:*?"<>|]', "-", name or "无标题")
    name = re.sub(r'[\n\r\t]', " ", name).strip()
    name = re.sub(r'-+', "-", name)
    name = re.sub(r'\s+', " ", name)
    name = re.sub(r'\.{2,}', '…', name)
    name = name.strip("-. ")
    if len(name) > max_len:
        name = name[:max_len].rstrip("-.")
    return name


def main():
    if not INDEX_FILE.exists():
        print(f"❌ 找不到索引文件: {INDEX_FILE}")
        print("   先跑媒体爬虫拿到 note_id → 标题 → 点赞数 的映射。")
        sys.exit(1)

    if not SOURCE_DIR.exists():
        print(f"❌ 找不到 MediaCrawler 视频目录: {SOURCE_DIR}")
        print("   请确认 MediaCrawler 已下载视频，或改 SOURCE_DIR 到实际路径。")
        sys.exit(1)

    print(f"📂 项目根: {BASE_DIR}")
    print(f"📂 源目录: {SOURCE_DIR}")
    print(f"📂 目标目录: {TARGET_DIR}")
    print()

    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    # 读 note_id → NNN 映射
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    print(f"📋 索引条目: {len(mapping)} 个")
    print()

    success, failed = [], []

    for note_id, info in mapping.items():
        seq = info["seq"]  # 如 "001"
        title = info["title"]

        # 1) 在 SOURCE_DIR 找以 note_id 开头的视频文件
        src_candidates = list(SOURCE_DIR.glob(f"{note_id}.*"))
        if not src_candidates:
            failed.append((note_id, "源目录找不到对应视频"))
            continue
        if len(src_candidates) > 1:
            print(f"  ⚠️ {note_id} 匹配到多个源文件: {[c.name for c in src_candidates]}，取第一个")
        src_path = src_candidates[0]

        # 2) 生成目标文件名
        ext = src_path.suffix  # .mp4
        safe_title = safe(title)
        target_name = f"{seq}-{safe_title}{ext}"
        # 末尾冗余点清理（….mp4 → …mp4）
        target_name = re.sub(r'\.{2,}\.mp4$', '.mp4', target_name)
        target_path = TARGET_DIR / target_name

        # 3) 复制
        try:
            shutil.copy2(src_path, target_path)
            size_mb = os.path.getsize(target_path) / (1024 * 1024)
            print(f"  ✅ {seq}: {src_path.name} → {target_name} ({size_mb:.1f}MB)")
            success.append((seq, target_name, size_mb))
        except Exception as e:
            failed.append((note_id, f"copy 失败: {e}"))

    print()
    print("=" * 60)
    print(f"✅ 成功: {len(success)} 个")
    print(f"❌ 失败: {len(failed)} 个")
    if failed:
        print()
        print("失败详情:")
        for note_id, reason in failed:
            print(f"  - {note_id}: {reason}")
    print()
    print(f"📁 视频源文件目录: {TARGET_DIR}")


if __name__ == "__main__":
    main()
