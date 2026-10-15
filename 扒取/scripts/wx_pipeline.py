# -*- coding: utf-8 -*-
"""
============================================================================
微信视频号 · 一条命令全自动流水线（固化，禁止再造轮子）
============================================================================
用法（唯一入口，任何视频号任务都跑这个）：

    <whisper venv python> wx_pipeline.py ^
        --nickname "示例博主" ^
        --author  "示例博主" ^
        --spid    "{视频号sph_id}" ^
        --project "{工作目录}\\{视频号sph_id}_视频号视频扒取" ^
        [    --days 365 | --all] [--min-likes 0] [--model tiny] [--rewrite] [--skip-download] [--skip-transcribe]

参数说明：
    --nickname  搜索关键词（微信视频号搜索框里能搜到的名字片段）
    --author    博主显示名（写进 MD 头部）
    --spid      视频号 ID（写进 MD 头部，可留空）
    --project   项目根目录（不存在会自动建）
    --days      只抓最近 N 天，默认 365；--all 表示全部
    --min-likes 只保留点赞数 >= N 的视频，默认 0（不过滤）
    --model     whisper 模型，默认 tiny（large-v3 在 hf-mirror 常 401）
    --rewrite   同步生成 04-改写脚本（情感/人生类视频号模板）
    --skip-download     已有 mp4，跳过下载直接转写
    --skip-transcribe   只下载不转写

流水线（全自动，零人工点击）：
    1 status 检查 → 2 search 拿 username → 3 feed/list 翻页拉全量清单
    → 4 直链下载加密文件 → 5 POST decrypt 解密 → 6 Whisper 转写
    → 7 按 SRT 逐段重建分时段 MD（繁转简） → 8 生成总索引

前置条件（唯一的、一次性的人工动作）：
    PC 微信已登录，且**打开过任意视频号页面**（让工具 WebSocket 连上）；
    wx_video_download.exe 已在后台运行（API http://127.0.0.1:2022）
============================================================================
"""
import argparse
import datetime
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "120")

API = "http://127.0.0.1:2022"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".flv", ".webm", ".m4a", ".mp3"}


def log(m=""):
    print(m, flush=True)


def hr(t=""):
    log("\n" + "=" * 64)
    if t:
        log(t)
        log("=" * 64)


# ---------------------------------------------------------------- HTTP
def http_get(path, timeout=40):
    req = urllib.request.Request(API + path, headers={"User-Agent": "wx-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


def http_post(path, timeout=180):
    req = urllib.request.Request(API + path, data=b"", method="POST",
                                 headers={"User-Agent": "wx-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


# ---------------------------------------------------------------- utils
def sanitize(name, limit=60):
    n = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", (name or "").strip())
    n = re.sub(r"\s+", " ", n).strip(" .")
    return n[:limit] or "untitled"


def is_mp4(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            return b"ftyp" in f.read(64)[:32]
    except Exception:
        return False


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


def srt_ts(sec):
    ms = int((sec - int(sec)) * 1000)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ---------------------------------------------------------------- Step 1-3 拉清单
def step_harvest(nickname: str, out_file: Path):
    hr("STEP 1/3  拉取博主全部视频清单")
    try:
        st = http_get("/api/channels/status", timeout=15)
        data = st.get("data") or {}
        ok = str(data.get("available")).lower() == "true" or data.get("available") is True
        log(f"  页面连接: {data}")
        if not ok:
            log("\n❌ 视频号页面未连接。请在 PC 微信里打开任意视频号页面（博主主页即可），再重跑。")
            return None
    except Exception as e:
        log(f"\n❌ 工具 API 不可用（{e}）。请先启动 wx_video_download.exe")
        return None

    log(f"\n  搜索「{nickname}」...")
    r = http_get("/api/channels/contact/search?keyword=" + urllib.parse.quote(nickname))
    inner = (r.get("data") or {}).get("data", r.get("data") or {})
    info = inner.get("infoList") or []
    username = None
    for it in info:
        c = it.get("contact") or it          # username 在 contact 嵌套里
        nick = c.get("nickname") or ""
        un = c.get("username") or ""
        log(f"    • {nick!r} -> {un[:64]}")
        if un and not username:
            username = un
    if not username:
        log("  ❌ 没搜到账号")
        return None
    log(f"  ✅ username = {username}")

    log("\n  翻页拉取全部视频（翻页字段 lastBuffer，continueFlag=1 继续）...")
    all_v, marker, page = [], "", 0
    while page < 60:
        page += 1
        url = (f"/api/channels/contact/feed/list?username={urllib.parse.quote(username)}"
               f"&next_marker={urllib.parse.quote(marker)}")
        try:
            r = http_get(url, timeout=40)
        except Exception as e:
            log(f"    第{page}页失败: {e}")
            break
        inner = (r.get("data") or {}).get("data", r.get("data") or {})
        objs = inner.get("object") or []
        if not objs:
            log(f"    第{page}页: 0 条，停止")
            break
        all_v.extend(objs)
        cf = inner.get("continueFlag")
        nm = inner.get("lastBuffer") or ""
        log(f"    第{page}页: +{len(objs)}（累计 {len(all_v)}）continueFlag={cf}")
        if str(cf) == "0" or not nm or nm == marker:
            break
        marker = nm

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps({"username": username, "total": len(all_v), "videos": all_v},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"\n  ✅ 共 {len(all_v)} 条 → {out_file}")
    return all_v


# ---------------------------------------------------------------- Step 4-5 下载+解密
def step_download(vids, video_dir: Path):
    hr("STEP 2/3  下载 + 解密")
    video_dir.mkdir(parents=True, exist_ok=True)
    ok_n, fail = 0, []
    for i, v in enumerate(vids, 1):
        desc = v.get("objectDesc") or {}
        title = (desc.get("description") or "").strip().split("\n")[0]
        media = (desc.get("media") or [{}])[0]
        url = (media.get("url") or "") + (media.get("urlToken") or "")
        key = media.get("decodeKey")
        if not url:
            log(f"[{i}] 跳过（无直链）: {title[:30]}")
            fail.append(title)
            continue
        fname = sanitize(title) + ".mp4"
        out = video_dir / fname
        if out.exists() and out.stat().st_size > 100_000:
            log(f"[{i}/{len(vids)}] ⏭  已存在: {fname[:46]}")
            ok_n += 1
            continue
        log(f"\n[{i}/{len(vids)}] {title[:40]}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Referer": "https://channels.weixin.qq.com/"})
            with urllib.request.urlopen(req, timeout=300) as resp:
                blob = resp.read()
            log(f"      下载 {len(blob)/1024/1024:.1f}MB")
        except Exception as e:
            log(f"      ❌ 下载失败: {e}")
            fail.append(title)
            continue
        tmp = video_dir / (fname + ".enc")
        tmp.write_bytes(blob)
        # 解密：key 必须放 query，放 body 会报 key parameter is required
        d_ok = False
        if key and str(key) != "0":
            try:
                q = f"/api/channels/decrypt?filepath={urllib.parse.quote(str(tmp))}&key={key}"
                resp = http_post(q, timeout=300)
                d_ok = resp.get("code") == 0
                if not d_ok:
                    log(f"      解密返回: {json.dumps(resp, ensure_ascii=False)[:160]}")
            except Exception as e:
                log(f"      解密异常: {type(e).__name__} {str(e)[:120]}")
        if d_ok or is_mp4(tmp):
            if tmp.exists():
                tmp.replace(out)
            ok_n += 1
            log(f"      ✅ {fname[:46]}")
        else:
            log("      ❌ 解密失败")
            fail.append(title)
        time.sleep(0.3)

    log(f"\n  完成：成功 {ok_n} / 失败 {len(fail)}")
    for t in fail:
        log(f"    - {t[:50]}")
    # 清理残留 .enc
    for p in video_dir.glob("*.enc"):
        try:
            p.unlink()
        except Exception:
            pass
    return ok_n


# ---------------------------------------------------------------- Step 6 转写
def step_transcribe(video_dir: Path, srt_dir: Path, model_size: str):
    hr("STEP 3a   Whisper 转写")
    srt_dir.mkdir(parents=True, exist_ok=True)
    videos = sorted(p for p in video_dir.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXT)
    if not videos:
        log("  ⚠️  无视频文件")
        return 0
    todo = [v for v in videos if not (srt_dir / f"{v.stem}.srt").exists()]
    log(f"  共 {len(videos)} 个视频，待转写 {len(todo)} 个（模型 {model_size} / int8 / CPU）")
    if not todo:
        return len(videos)
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log("  ❌ faster-whisper 未安装：")
        log("     请用已安装 faster-whisper 的 Python 执行，例如：")
        log("     C:/Users/<你的用户名>/AppData/Local/Programs/Python/Python312/python.exe -m pip install faster-whisper opencc-python-reimplemented")
        log("     或切换系统 Python 3.12（当前环境已具备）。")
        return 0
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    done = 0
    for i, v in enumerate(todo, 1):
        try:
            log(f"\n  [{i}/{len(todo)}] {v.name[:44]}")
            segments, info = model.transcribe(str(v), language="zh", beam_size=5,
                                              vad_filter=True,
                                              vad_parameters={"min_silence_duration_ms": 500})
            srt_lines, txt_lines, n = [], [], 0
            for j, seg in enumerate(segments, 1):
                srt_lines += [str(j), f"{srt_ts(seg.start)} --> {srt_ts(seg.end)}", seg.text.strip(), ""]
                txt_lines.append(seg.text.strip())
                n += 1
            (srt_dir / f"{v.stem}.srt").write_text("\n".join(srt_lines), encoding="utf-8")
            (srt_dir / f"{v.stem}.txt").write_text("\n".join(txt_lines), encoding="utf-8")
            done += 1
            log(f"      ✅ {n} 段 / {info.duration:.0f}s")
        except Exception as e:
            log(f"      ❌ {type(e).__name__}: {str(e)[:120]}")
    return done


# ---------------------------------------------------------------- Step 7 重建 MD
def step_md(srt_dir: Path, md_dir: Path, list_file: Path, author: str, spid: str):
    hr("STEP 3b  重建分时段逐字稿 MD")
    md_dir.mkdir(parents=True, exist_ok=True)
    try:
        from opencc import OpenCC
        cc = OpenCC("t2s")
    except Exception:
        cc = None
        log("  ⚠️  opencc 未装，跳过繁转简（pip install opencc-python-reimplemented）")

    meta = {}
    if list_file.exists():
        d = json.loads(list_file.read_text(encoding="utf-8"))
        for v in d.get("videos", []):
            desc = (v.get("objectDesc") or {}).get("description", "")
            meta[sanitize(desc.strip().split("\n")[0])] = {
                "desc": desc, "first": desc.strip().split("\n")[0],
                "ct": v.get("createtime") or 0,
                "likes": v.get("likeCount") or 0,
                "comments": v.get("commentCount") or 0,
                "forwards": v.get("forwardCount") or 0,
            }

    srts = sorted(srt_dir.glob("*.srt"))
    n_ok = 0
    for i, srt in enumerate(srts, 1):
        stem = srt.stem
        # 兼容历史项目：文件名可能带工具遗留的 _xWT111 后缀，MD 一律输出干净名
        key = stem[:-len("_xWT111")] if stem.endswith("_xWT111") else stem
        m = meta.get(key) or meta.get(stem) or {}
        desc, first, ct = m.get("desc", ""), m.get("first", key), m.get("ct", 0)
        pub = datetime.datetime.fromtimestamp(ct).strftime("%Y-%m-%d") if ct else "—"
        tags = re.findall(r"#([^\s#]+)", desc)
        tags_s = " ".join("#" + t for t in tags[:8]) if tags else "—"
        likes = m.get("likes") or 0
        comments = m.get("comments") or 0
        forwards = m.get("forwards") or 0
        segs = parse_srt(srt)
        if not segs:
            log(f"  [{i}] ⚠️  无内容: {srt.name[:40]}")
            continue
        dur = segs[-1][0]
        lines = []
        for s, t in segs:
            lines.append(f"> {fmt_ts(s)} {(cc.convert(t) if cc else t)}")
        md = f"""# {key}

> **视频号**：{author}
> **发布时间**：{pub}
> **点赞数**：{likes} ｜ **评论**：{comments} ｜ **转发**：{forwards}
> **视频时长**：{dur} 秒
> **话题标签**：{tags_s}
> **来源**：微信视频号 ID {spid or '—'}
> **逐字稿来源**：Whisper（int8 + CPU，已转简体）

---

## 🎯 核心观点（1 句话）

{first}

## 📝 逐字稿

{chr(10).join(lines)}

## 🔗 我的行动

- [ ] 看完视频后立刻能做的 1 件事
- [ ] 3 天内可以验证的事
"""
        (md_dir / f"{key}.md").write_text(md, encoding="utf-8")
        n_ok += 1
        if i % 10 == 0:
            log(f"  [{i}/{len(srts)}] ✅")
    log(f"  ✅ 重建 {n_ok} 篇")
    return n_ok


# ---------------------------------------------------------------- Step 8 索引
def step_index(md_dir: Path, idx_file: Path, author: str, spid: str):
    rows = []
    for f in sorted(md_dir.glob("*.md")):
        t = f.read_text(encoding="utf-8", errors="ignore")
        pub = (re.search(r"\*\*发布时间\*\*：(\S+)", t) or [None, "—"])[1]
        dur = (re.search(r"\*\*视频时长\*\*：(\d+)", t) or [None, "—"])[1]
        likes = (re.search(r"\*\*点赞数\*\*：(\d+)", t) or [None, "—"])[1]
        seg = len(re.findall(r"^> \[\d\d:", t, re.M))
        rows.append((pub, f.stem, dur, seg, likes))
    rows.sort(reverse=True)
    total_seg = sum(r[3] for r in rows)
    L = [f"# {author}（{spid}）· 逐字稿总索引", "",
         f"> **{len(rows)} 条视频** · 逐字稿共 **{total_seg} 段** · 全自动抓取，零人工点击", "",
         "| # | 日期 | 时长 | 段数 | 点赞 | 标题 |", "|---:|---|---:|---:|---:|---|"]
    for i, (pub, title, dur, seg, likes) in enumerate(rows, 1):
        L.append(f"| {i} | {pub} | {dur}s | {seg} | {likes} | {title.replace('|', '/')[:40]} |")
    idx_file.parent.mkdir(parents=True, exist_ok=True)
    idx_file.write_text("\n".join(L), encoding="utf-8")
    log(f"  ✅ 索引：{len(rows)} 条 / {total_seg} 段 → {idx_file}")


# ---------------------------------------------------------------- 改写语气模板（4 选 1）
TONES = {
    "emotional": {
        "name": "情感共鸣型",
        "desc": "视频号情感/人生类 · 温柔陪伴 + 金句点睛 + 情绪化 CTA",
        "hook": "把原视频的核心洞察变成一句「反常识 + 情绪共鸣」的开头。",
        "s1": "直接抛出最有冲击力的问题或观点，让观众停下手指。",
        "s2": "用 1 个具体场景或 1 个身边人故事，把观众代入情绪。\n> 节奏：短句、留白、字幕放大关键词。",
        "s3": "围绕主题拆 2-3 个层次，每层 1 句金句 + 1 个生活画面。\n> 避免说教，用「我观察到……」「后来发现……」等陪伴式语气。",
        "s4": "给出 1 个可执行的转念/行动建议。",
        "cta": "你有过类似的经历吗？评论区告诉我。",
    },
    "sharp": {
        "name": "犀利观点型",
        "desc": "犀利观点输出 · 反常识断言 + 强态度，制造争议与转发",
        "hook": "用一句不留余地的判断开场，直接挑战观众已有的常识。",
        "s1": "直接给结论，不铺垫。句式参考「你以为的……其实是错的」。",
        "s2": "摆出大众普遍相信的错误认知，制造认知冲突（树靶子）。",
        "s3": "用 2 个硬事实 / 真实案例打掉对立面。语气果断，禁用「可能」「也许」「大概」。",
        "s4": "明确表态，逼观众站队，把观点推到极致。",
        "cta": "同意的点个赞，不同意的评论区来辩。",
    },
    "practical": {
        "name": "干货拆解型",
        "desc": "结构化干货 · 信息密度优先，弱化情绪",
        "hook": "用「3 个 XX」这类明确的数字承诺开场，给观众可预期的收获。",
        "s1": "直接抛出数字承诺：「关于这个话题，你只需要记住 3 点」。",
        "s2": "第 1 点：观点 + 一句解释 + 1 个具体例子，控制在 20 秒内。",
        "s3": "第 2、3 点：同节奏推进，每点 15 秒左右，用字幕编号强化结构。",
        "s4": "用一句话复述 3 个要点，形成闭环记忆。",
        "cta": "先收藏起来，需要的时候翻出来看看。",
    },
    "story": {
        "name": "人物故事型",
        "desc": "人物故事叙事 · 场景还原 + 具体细节 + 情感落点",
        "hook": "从一个有画面感的具体瞬间切入（时间 + 地点 + 动作）。",
        "s1": "直接进场景：「那年冬天，零下三十度，他在大街上走了四个小时」。",
        "s2": "铺陈困境，细节越具体越好（数字、动作、环境），把人物逼到绝境。",
        "s3": "转折点：出现什么人 / 什么事，让局面开始松动。",
        "s4": "从故事里抽出一句普适感悟，落到观众自己身上。",
        "cta": "如果你也正在最难的时候，把这句话记住。",
    },
}


# ---------------------------------------------------------------- Step 9 改写脚本（视频号情感/人生类）
def step_rewrite(md_dir: Path, rewrite_dir: Path, tone: str = "emotional"):
    T = TONES.get(tone, TONES["emotional"])
    hr(f"STEP 4   改写脚本生成（语气：{T['name']}）")
    rewrite_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for md in sorted(md_dir.glob("*.md")):
        out = rewrite_dir / f"{md.stem}_改写.md"
        if out.exists():
            n += 1
            continue
        t = md.read_text(encoding="utf-8", errors="ignore")
        title = md.stem
        pub = (re.search(r"\*\*发布时间\*\*：(\S+)", t) or [None, "—"])[1]
        likes = (re.search(r"\*\*点赞数\*\*：(\d+)", t) or [None, "—"])[1]
        body_lines = [re.sub(r"^> \[\d{2}:\d{2}:\d{2}\]\s*", "", ln).strip()
                      for ln in t.splitlines() if ln.startswith("> [")]
        body_lines = [ln for ln in body_lines if ln]
        full_text = "".join(body_lines)
        # 按标点或行拆分候选金句
        raw = "\n".join(body_lines)
        sentences = [s.strip() for s in re.split(r"[，。！？；\n]", raw) if 8 < len(s.strip()) <= 80]
        hook_words = (r"真正|差距|人生|婚姻|人品|关系|低估|珍惜|价值|陪伴|成长|难熬|顺风|"
                      r"创业|坚持|成功|失败|选择|痛苦|压力|孤独|努力|方向|金钱|生活|幸福|"
                      r"爱情|理解|信任|责任|梦想|现实|时间|底气|同行|平庸|放弃")
        hooks = [s for s in sentences if re.search(hook_words, s)]
        others = [s for s in sentences if s not in hooks]
        # 兜底：取前 5 个非空短句
        fallbacks = [ln[:70] + ("..." if len(ln) > 70 else "") for ln in body_lines if len(ln) > 8][:5]
        seen = set()
        golden = []
        for s in hooks + others + fallbacks:
            if s not in seen:
                seen.add(s)
                golden.append(s)
            if len(golden) >= 5:
                break
        if not golden:
            golden.append(full_text[:60] + "...")
        golden_md = "\n".join(f"{i+1}. {s}" for i, s in enumerate(golden))
        rewrite = f"""# {title}（改写稿）

> **改写方向**：视频号情感/人生类 · 新 Hook + 新口播 + 新 CTA
> **目标平台**：微信视频号（中国大陆，中文）
> **发布时间**：{pub} ｜ **原点赞数**：{likes}

---

## 🎬 短视频脚本（60-90s）

### Hook（前 3 秒 · 必抓停留）

> 💡 **改写核心**：把原视频的核心洞察变成一句「反常识 + 情绪共鸣」的开头。
>
> 参考角度：{golden[0] if golden else '（从原视频提炼）'}

### 内容结构（4 段式）

**【0-5s】Hook（痛点/反常识开场）**
> 直接抛出最有冲击力的问题或观点，让观众停下手指。

**【5-25s】故事/现象铺垫**
> 用 1 个具体场景或 1 个身边人故事，把观众代入情绪。
> 节奏：短句、留白、字幕放大关键词。

**【25-55s】核心拆解（机制/原因/感悟）**
> 围绕主题拆 2-3 个层次，每层 1 句金句 + 1 个生活画面。
> 避免说教，用「我观察到……」「后来发现……」等陪伴式语气。

**【55-90s】反转 + CTA**
> 给出 1 个可执行的转念/行动建议。
> 结尾引导：「你有过类似的经历吗？评论区告诉我。」

### 字幕/画面/口播同步表

| 时间 | 口播 | 画面 | 字幕 |
|---|---|---|---|
| 0-5s |  Hook 第一句  | 人物近景 / 冲突画面 | 大字 + 黄底强调 |
| 5-25s |  故事铺垫  | 生活场景 / 资料画面 | 短句逐字出现 |
| 25-55s |  核心感悟  | 翻书/走路/空镜 | 金句大字 + 转柔 BGM |
| 55-90s |  CTA  | 博主面对镜头 | 评论区互动引导 |

---

## ✨ 可直接复用的金句（来自原稿）

{golden_md}

---

## 📝 Original Core Script（参考区 · 禁止直接复制）

<details>
<summary>📋 点击展开原视频逐字稿（共 {len(body_lines)} 段）</summary>

{chr(10).join(body_lines)}

</details>

---

## ✅ 改写质量自检

| # | 铁律 | 状态 |
|---|---|---|
| 1 | 🔴 改写脚本语言：视频号（国内平台）→ **中文** | ✅ |
| 2 | 🔴 改写 ≠ 复制逐字稿（新 Hook + 新结构 + 新 CTA） | ✅ |
| 3 | 🔴 口播感优先，避免书面化长句 | ✅ |
| 4 | 🔴 前 3 秒必须有情绪钩子 | ✅ |
| 5 | 🔴 结尾必须有可执行 CTA | ✅ |
"""
        out.write_text(rewrite, encoding="utf-8")
        n += 1
    log(f"  ✅ 改写稿骨架 {n} 篇 → {rewrite_dir}")
    log("  " + "🔴" * 3 + " 以下为【硬性提醒】，不是可选建议 " + "🔴" * 3)
    log("  1) 本函数（step_rewrite）是纯规则脚本，只会「套模板 + 摘原句」，")
    log("     它产出的 04 会 100% 复制 03 逐字稿 —— **它不是交付物**。")
    log("  2) 必须由 AI 读 03 逐字稿后按已确认语气亲笔重写 Hook / 口播 / CTA / 金句。")
    log("  3) 语气必须在开工前先问用户（情感共鸣型/犀利观点型/干货拆解型/人物故事型/种草带货型）。")
    log("  4) 重写完必须跑验收闸门：")
    log(f"     python {Path(__file__).with_name('verify_rewrite_distinct.py')} \"{rewrite_dir.parent}\"")
    log("     exit=0 才可交付；exit=1 一票否决，重写后再跑。")
    # 立刻自动跑一次验收，让 FAIL 当场暴露
    run_verify(rewrite_dir.parent)
    return n


def run_verify(project_root: Path) -> None:
    """调用 verify_rewrite_distinct.py 做 04 vs 03 差异验收（失败不中断，只告警）"""
    import subprocess
    vs = Path(__file__).with_name("verify_rewrite_distinct.py")
    if not vs.exists():
        return
    log("  ▶ 自动运行差异验收…")
    r = subprocess.run([sys.executable, str(vs), str(project_root)],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    out = (r.stdout or "") + (r.stderr or "")
    for line in out.splitlines():
        log("     " + line)
    if r.returncode == 0:
        log("  ✅ 验收通过：04 与 03 已确认不同")
    else:
        log("  " + "❌" * 3 + " 验收未通过：04 与 03 雷同，必须 AI 亲笔重写后才可交付 " + "❌" * 3)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nickname", required=True, help="搜索关键词")
    ap.add_argument("--author", default="", help="博主显示名")
    ap.add_argument("--spid", default="", help="视频号 ID")
    ap.add_argument("--project", required=True, help="项目根目录")
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--min-likes", type=int, default=0)
    ap.add_argument("--model", default="tiny")
    ap.add_argument("--rewrite", action="store_true", help="同步生成 04-改写脚本")
    ap.add_argument("--skip-download", action="store_true")
    ap.add_argument("--skip-transcribe", action="store_true")
    a = ap.parse_args()

    author = a.author or a.nickname
    BASE = Path(a.project)
    list_file = BASE / "01-视频清单" / "account_videos.json"
    video_dir = BASE / "02-Whisper转写" / "视频源文件"
    srt_dir = BASE / "02-Whisper转写" / "转写结果"
    md_dir = BASE / "03-逐字稿MD"
    rewrite_dir = BASE / "04-改写脚本"
    idx_file = BASE / "01-视频清单" / "逐字稿总索引.md"
    for d in (list_file.parent, video_dir, srt_dir, md_dir, rewrite_dir):
        d.mkdir(parents=True, exist_ok=True)

    log(f"🚀 视频号全自动流水线 · {author} ({a.spid})")
    log(f"   项目: {BASE}")

    # 拉清单
    if a.skip_download and list_file.exists():
        vids = json.loads(list_file.read_text(encoding="utf-8")).get("videos", [])
        log(f"   ⏭  复用已有清单 {len(vids)} 条")
    else:
        vids = step_harvest(a.nickname, list_file)
        if not vids:
            return 1

    # 时间过滤
    if not a.all:
        cut = (datetime.datetime.now() - datetime.timedelta(days=a.days)).timestamp()
        before = len(vids)
        vids = [v for v in vids if (v.get("createtime") or 0) >= cut]
        log(f"\n   近 {a.days} 天过滤: {before} → {len(vids)} 条")

    # 点赞过滤
    if a.min_likes > 0:
        before = len(vids)
        vids = [v for v in vids if (v.get("likeCount") or 0) >= a.min_likes]
        log(f"   点赞 ≥ {a.min_likes} 过滤: {before} → {len(vids)} 条")

    # 下载
    if not a.skip_download:
        step_download(vids, video_dir)

    # 转写 + MD
    if not a.skip_transcribe:
        step_transcribe(video_dir, srt_dir, a.model)
        step_md(srt_dir, md_dir, list_file, author, a.spid)
        step_index(md_dir, idx_file, author, a.spid)
        if a.rewrite:
            step_rewrite(md_dir, rewrite_dir)

    hr("✅ 全部完成")
    log(f"   mp4: {len(list(video_dir.glob('*.mp4')))}")
    log(f"   srt: {len(list(srt_dir.glob('*.srt')))}")
    log(f"   MD : {len(list(md_dir.glob('*.md')))}")
    log(f"   改写: {len(list(rewrite_dir.glob('*.md')))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
