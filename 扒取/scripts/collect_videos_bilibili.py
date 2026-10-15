# -*- coding: utf-8 -*-
"""
collect_videos_bilibili.py - B站视频源文件归集 + 重命名工具
=========================================================================
【功能】
如果 B站视频通过 yt-dlp 单独下载到任意目录，按本地
`01-视频清单/videos_index.json` 映射关系，归集到项目
  02-Whisper转写/视频源文件/{NNN}-{完整标题}.mp4

【适用场景】
- yt-dlp 用 BVID 单条下载后文件名是标题（已含 `…`），直接复制即可
- yt-dlp 用 BV 号列表模式下载后是数字重命名，需按索引重命名
- 从第三方源（如 you-get / FFMPEG 备份）恢复

【使用方式】
1. 把脚本拷到项目 99-生成脚本/ 下
2. 准备 `01-视频清单/videos_index.json`，结构：
   {
     "001": {"bvid": "BV1xxx", "title": "标题…"},
     "002": ...
   }
3. 把 yt-dlp 下载的原始 mp4 放到 SOURCE_DIR（默认 ./raw_downloads/）
4. 跑：`python collect_videos_bilibili.py`

【依赖】
- 标准库 only（无第三方依赖）

=========================================================================
"""
import json
import os
import re
import shutil
import sys
from pathlib import Path

# ============== 用户自定义区（按实际项目改） ==============
BASE_DIR = Path(r"{工作目录}\示例博主_B站视频扒取")
# yt-dlp 下载的原始视频目录（按 BVID 命名 or 标题命名都行，脚本会智能匹配）
SOURCE_DIR = BASE_DIR / "raw_downloads"
# 也可以是外部下载目录： Path(r"D:/downloads/bili")

# ============== 内部逻辑 ==============
INDEX_FILE = BASE_DIR / "01-视频清单" / "videos_index.json"
TARGET_DIR = BASE_DIR / "02-Whisper转写" / "视频源文件"


def safe(name: str, max_len: int = 60) -> str:
    """统一文件名清洗规则"""
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
        print("   索引结构应为: {\"001\": {\"bvid\": \"BV1xxx\", \"title\": \"标题...\"}, ...}")
        sys.exit(1)

    if not SOURCE_DIR.exists():
        print(f"❌ 找不到源目录: {SOURCE_DIR}")
        print("   请把 yt-dlp 下载的视频放到该目录下，或修改 SOURCE_DIR。")
        sys.exit(1)

    print(f"📂 项目根: {BASE_DIR}")
    print(f"📂 源目录: {SOURCE_DIR}")
    print(f"📂 目标目录: {TARGET_DIR}")
    print()

    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        index = json.load(f)

    print(f"📋 索引条目: {len(index)} 个")
    print()

    success, failed = [], []
    source_files = list(SOURCE_DIR.glob("*.mp4")) + list(SOURCE_DIR.glob("*.flv"))

    for seq, info in index.items():
        bvid = info["bvid"]
        title = info["title"]

        # 1) 在 SOURCE_DIR 中找匹配的视频
        # 优先按 BVID 匹配；兜底按标题前 N 字匹配
        candidates = [f for f in source_files if bvid.lower() in f.name.lower()]
        if not candidates:
            safe_title_partial = safe(title)[:15]
            candidates = [f for f in source_files if safe_title_partial.lower() in f.name.lower()]

        if not candidates:
            failed.append((seq, f"找不到 BVID={bvid} 或 标题={title[:20]} 的源视频"))
            continue
        if len(candidates) > 1:
            # 取最大的（更可能是完整下载）
            candidates.sort(key=lambda f: os.path.getsize(f), reverse=True)

        src_path = candidates[0]

        # 2) 目标文件名
        safe_title = safe(title)
        target_name = f"{seq}-{safe_title}.mp4"
        target_name = re.sub(r'\.{2,}\.mp4$', '.mp4', target_name)
        target_path = TARGET_DIR / target_name

        # 3) 复制
        try:
            shutil.copy2(src_path, target_path)
            size_mb = os.path.getsize(target_path) / (1024 * 1024)
            print(f"  ✅ {seq}: {src_path.name} → {target_name} ({size_mb:.1f}MB)")
            success.append((seq, target_name, size_mb))
        except Exception as e:
            failed.append((seq, f"copy 失败: {e}"))

    print()
    print("=" * 60)
    print(f"✅ 成功: {len(success)} 个")
    print(f"❌ 失败: {len(failed)} 个")
    if failed:
        print()
        print("失败详情（可能需要单独用 yt-dlp 下载这些视频）:")
        for seq, reason in failed:
            print(f"  - {seq}: {reason}")
    print()
    print(f"📁 视频源文件目录: {TARGET_DIR}")


if __name__ == "__main__":
    main()
