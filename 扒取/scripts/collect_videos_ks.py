#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨博主复用的快手视频归集脚本（skill scripts/collect_videos_ks.py）

用法（拷到项目目录，改 2 个常量即可）：
1. 修改下面的 BASE_DIR 为你的项目路径
2. 修改 JSONL_PATH 为 MediaCrawler 输出的 JSONL 路径
3. 修改 B_DAYS / B_THRESHOLD 为你的阈值
4. python collect_videos_ks.py
"""

import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ============ 改这 4 个常量 ============
B_DAYS = 30              # 近几日
B_THRESHOLD = 1000       # 点赞阈值
BASE_DIR = Path(r"{工作目录}/示例博主_快手视频扒取")
JSONL_PATH = Path(r"{工作目录}/MediaCrawler/data/kuaishou/jsonl/creator_contents_2026-09-11.jsonl")
# ======================================

SRC_DIR = BASE_DIR / "02-Whisper转写" / "视频源文件"
LIST_DIR = BASE_DIR / "01-视频清单"


def safe(name: str, max_len: int = 50) -> str:
    """跨脚本同源 safe 函数"""
    name = re.sub(r'[\\/:*?"<>|]', "-", name or "无标题")
    name = re.sub(r'[\n\r\t]', " ", name).strip()
    name = re.sub(r'-+', "-", name)
    name = re.sub(r'\s+', " ", name)
    name = re.sub(r'\.{2,}', '…', name)
    name = name.strip("-.\u3001\u3002 ")
    if len(name) > max_len:
        name = name[:max_len].rstrip("-")
    return name or "无标题"


def parse_wan(s):
    """'1.2万' → 12000"""
    if not s: return 0
    s = str(s)
    try:
        if '万' in s:
            return int(float(s.replace('万', '')) * 10000)
        return int(s)
    except: return 0


def download(url, dest, retries=3):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.kuaishou.com/',
    }
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
                if len(data) < 1024:
                    raise ValueError(f"too small: {len(data)} bytes")
                with open(dest, 'wb') as f:
                    f.write(data)
                return len(data)
        except Exception as e:
            print(f"   ⚠️ retry {i+1}/{retries}: {e}")
            time.sleep(2)
    return None


def main():
    if not JSONL_PATH.exists():
        print(f"❌ 找不到 JSONL: {JSONL_PATH}")
        print(f"   请先运行 MediaCrawler 并指定平台 ks")
        return

    # 读 JSONL
    recs = []
    with open(JSONL_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            try: recs.append(json.loads(line))
            except: pass
    print(f"[1/3] 读 JSONL: {len(recs)} 条")

    # 筛 命中
    now = datetime.now(timezone(timedelta(hours=8)))
    start_ms = int((now - timedelta(days=B_DAYS)).timestamp() * 1000)
    hits = []
    for r in recs:
        ct = r.get('create_time')
        try: ct = int(ct) if ct else 0
        except: continue
        if ct < start_ms: continue
        likes = parse_wan(r.get('liked_count', 0))
        if likes < B_THRESHOLD: continue
        r['_likes'] = likes
        r['_views'] = parse_wan(r.get('viewd_count', 0))
        r['_pub'] = datetime.fromtimestamp(ct/1000, tz=timezone(timedelta(hours=8)))
        hits.append(r)
    hits.sort(key=lambda v: v['_likes'], reverse=True)
    print(f"[2/3] 筛近{B_DAYS}天+≥{B_THRESHOLD}❤: {len(hits)} 条命中")

    SRC_DIR.mkdir(parents=True, exist_ok=True)
    LIST_DIR.mkdir(parents=True, exist_ok=True)

    # 下载
    print(f"[3/3] 下载到 {SRC_DIR}")
    ok, fail = 0, []
    for idx, v in enumerate(hits, 1):
        seq = f"{idx:03d}"
        title = re.sub(r'#\S+\s*', '', v.get('title') or '').strip()
        safe_t = safe(title)
        dst = SRC_DIR / f"{seq}-{safe_t}.mp4"
        v['_seq'] = seq
        v['_dst'] = str(dst)

        if dst.exists() and dst.stat().st_size > 1024:
            print(f"  ⏭️  {seq} - {dst.name} (已存在)")
            ok += 1
            continue

        url = v.get('video_play_url')
        if not url:
            fail.append(seq); continue
        size = download(url, dst)
        if size:
            print(f"  ✅ {seq} ({size//1024} KB)")
            ok += 1
        else:
            print(f"  ❌ {seq} 失败")
            fail.append(seq)
        time.sleep(1)

    # 写 index
    index = {
        "platform": "快手",
        "filter_rule": f"近{B_DAYS}天 + 点赞 ≥{B_THRESHOLD}",
        "crawl_date": now.strftime("%Y-%m-%d %H:%M"),
        "total_crawled": len(recs),
        "hits": len(hits),
        "downloaded_ok": ok,
        "videos": [
            {
                "seq": v["_seq"],
                "video_id": v["video_id"],
                "title_clean": re.sub(r'#\S+\s*', '', v.get('title') or '').strip(),
                "likes": v["_likes"],
                "views": v["_views"],
                "pub_date": v["_pub"].strftime("%Y-%m-%d"),
                "dst_name": Path(v["_dst"]).name,
            } for v in hits
        ],
    }
    with open(LIST_DIR / "videos_index.json", 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"\n📝 索引: {LIST_DIR / 'videos_index.json'}")
    print(f"✅ 成功: {ok}/{len(hits)}")


if __name__ == "__main__":
    main()
