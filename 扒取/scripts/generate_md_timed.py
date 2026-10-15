# -*- coding: utf-8 -*-
"""
============================================================================
通用分时段逐字稿 MD 生成器（全平台，替代已废弃的 md_generator.py）
============================================================================
为什么不用 md_generator.py（2026-09-14 实测，已废弃）：
  1. 把多段 SRT 合并成一坨，丢掉时间戳 → 无法按时间点检索
  2. 头部会错挂上一个项目的博主名 / 平台 ID
  3. 被后台任务反复调用时，会把正确 MD 覆盖成 `<!-- AI 提炼 -->` 占位版

本脚本产出的 MD：
  - 逐段带 `[00:00:12]` 时间戳（与 wx_pipeline.step_md 同源逻辑）
  - 繁转简（opencc，缺失时自动跳过，不报错）
  - 元信息可为空占位 `—`，但**绝不生成 `<!-- -->` 占位块**

用法（任意平台通用）：

    <python> generate_md_timed.py ^
        --srt-dir "<项目>/02-Whisper转写/转写结果" ^
        --md-dir  "<项目>/03-逐字稿MD" ^
        --author  "博主名" ^
        --platform "小红书" ^
        [--list-file "<项目>/01-视频清单/account_videos.json"] ^
        [--id "账号ID"]

参数说明：
    --srt-dir    存放 .srt 的目录（必填）
    --md-dir     输出 MD 的目录（不存在自动建）
    --author     博主显示名
    --platform   平台名（写进 MD 头部，如 小红书 / B站 / 快手 / YouTube / TikTok / 抖音 / Instagram）
    --list-file  可选。视频清单 JSON（含 createtime/likeCount/commentCount 等），
                 提供后 MD 头部会带发布日期 / 点赞 / 评论；不提供则填 —
    --id         可选。账号 ID
============================================================================
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path


def log(m=""):
    print(m, flush=True)


def hr(t=""):
    log("\n" + "=" * 64)
    if t:
        log(t)
        log("=" * 64)


def parse_srt(path: Path):
    txt = path.read_text(encoding="utf-8", errors="ignore")
    out = []
    for b in re.split(r"\n\s*\n", txt.strip()):
        lines = [l for l in b.splitlines() if l.strip()]
        ti = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if ti is None:
            continue
        m = re.match(r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})", lines[ti])
        if not m:
            continue
        h, mi, s, _ = m.groups()
        t = " ".join(lines[ti + 1:]).strip()
        if t:
            out.append((int(h) * 3600 + int(mi) * 60 + int(s), t))
    return out


def fmt_ts(sec):
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"[{h:02d}:{m:02d}:{s:02d}]"


def sanitize(name, limit=60):
    n = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", (name or "").strip())
    n = re.sub(r"\s+", " ", n).strip(" .")
    return n[:limit] or "untitled"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--srt-dir", required=True)
    ap.add_argument("--md-dir", required=True)
    ap.add_argument("--author", default="—")
    ap.add_argument("--platform", default="—")
    ap.add_argument("--list-file", default="")
    ap.add_argument("--id", dest="acc_id", default="—")
    a = ap.parse_args()

    srt_dir, md_dir = Path(a.srt_dir), Path(a.md_dir)
    if not srt_dir.exists():
        log(f"❌ SRT 目录不存在：{srt_dir}")
        return 1
    md_dir.mkdir(parents=True, exist_ok=True)

    try:
        from opencc import OpenCC
        cc = OpenCC("t2s")
    except Exception:
        cc = None
        log("  ⚠️  opencc 未装，跳过繁转简（pip install opencc-python-reimplemented）")

    # 元信息（可选）
    meta = {}
    lf = Path(a.list_file) if a.list_file else None
    if lf and lf.exists():
        try:
            d = json.loads(lf.read_text(encoding="utf-8"))
            for v in d.get("videos", []):
                desc = (v.get("objectDesc") or {}).get("description", "") if isinstance(v.get("objectDesc"), dict) \
                    else (v.get("desc") or v.get("title") or "")
                first = (desc or "").strip().split("\n")[0]
                meta[sanitize(first)] = {
                    "ct": int(v.get("createtime") or 0),
                    "likes": int(v.get("likeCount") or v.get("liked_count") or 0),
                    "comments": int(v.get("commentCount") or v.get("comment_count") or 0),
                }
        except Exception as e:
            log(f"  ⚠️  清单解析失败（忽略，元信息填 —）：{e}")

    srts = sorted(srt_dir.glob("*.srt"))
    if not srts:
        log("❌ 目录下没有 .srt 文件")
        return 1

    hr(f"分时段逐字稿 MD 生成（{a.platform}）· 共 {len(srts)} 个 SRT")
    ok = skip = 0
    total_seg = 0
    for i, srt in enumerate(srts, 1):
        stem = srt.stem
        key = stem[:-len("_xWT111")] if stem.endswith("_xWT111") else stem
        m = meta.get(key) or meta.get(stem) or {}
        ct, likes, comments = m.get("ct", 0), m.get("likes", 0), m.get("comments", 0)
        pub = datetime.datetime.fromtimestamp(ct).strftime("%Y-%m-%d") if ct else "—"
        segs = parse_srt(srt)
        if not segs:
            log(f"  [{i}] ⚠️  无内容，跳过：{srt.name[:50]}")
            skip += 1
            continue
        dur = segs[-1][0]
        body = "\n".join(f"> {fmt_ts(s)} {(cc.convert(t) if cc else t)}" for s, t in segs)
        md = f"""# {key}

> **平台**：{a.platform}
> **博主**：{a.author}
> **账号 ID**：{a.acc_id}
> **发布时间**：{pub}
> **点赞数**：{likes} ｜ **评论**：{comments}
> **视频时长**：{dur} 秒
> **逐字稿来源**：Whisper（int8 + CPU，已转简体）

---

## 📝 逐字稿（分时段）

{body}
"""
        (md_dir / f"{sanitize(key, 80)}.md").write_text(md, encoding="utf-8")
        total_seg += len(segs)
        ok += 1
        if i % 10 == 0 or i == len(srts):
            log(f"  [{i}/{len(srts)}] ✅ {key[:44]}（{len(segs)} 段 / {dur}s）")

    hr("✅ 完成")
    log(f"   MD  : {ok} 篇 → {md_dir}")
    log(f"   段落: {total_seg}")
    log(f"   跳过: {skip}")
    log("   注意：MD 内的「核心观点 / 关键点 / 金句 / 我的行动」由 AI 读稿补齐，脚本不生成占位块")
    return 0


if __name__ == "__main__":
    sys.exit(main())
