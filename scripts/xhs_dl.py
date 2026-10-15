"""小红书视频下载：Playwright(Edge) + storage_state，取 mediaV2.stream 带音轨档位。
用法: python xhs_dl.py <url> <out_dir> [tag]
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

STATE = r"{工作目录}\MediaCrawler\xhs_storage_state.json"


def pick_stream(state):
    note = state.get("note", {})
    first = note.get("firstNoteId")
    n = note.get("noteDetailMap", {}).get(first, {}).get("note") or {}
    if not n:
        # 兜底：取第一个有 video 的 note
        for k, v in note.get("noteDetailMap", {}).items():
            if (v.get("note") or {}).get("video"):
                n = v["note"]
                break
    video = n.get("video") or {}
    media = video.get("mediaV2") or video.get("media") or {}
    if isinstance(media, str):
        try:
            media = json.loads(media)
        except Exception:
            media = {}
    stream = media.get("stream") or {}
    cands = []
    for k, v in stream.items():
        if not isinstance(v, dict):
            continue
        url = v.get("master_url") or v.get("masterUrl") or v.get("backup_url_1")
        ab = v.get("audio_bitrate") or v.get("audioBitrate") or 0
        vb = v.get("video_bitrate") or v.get("videoBitrate") or 0
        dur = v.get("duration") or 0
        if url:
            cands.append((k, url, ab, vb, dur))
    if not cands:
        return None, None, None
    with_audio = [c for c in cands if c[2] and c[2] > 0]
    pool = with_audio or cands
    # 选有音轨里 video_bitrate 最大的
    pool.sort(key=lambda c: (c[2] > 0, c[3]), reverse=True)
    best = pool[0]
    dur_ms = 0
    for c in cands:
        if c[4] and c[4] > dur_ms:
            dur_ms = c[4]
    title = (n.get("title") or n.get("desc") or "")[:80]
    return best[1], dur_ms, title


def main():
    url = sys.argv[1].strip()
    out_dir = Path(sys.argv[2])
    tag = sys.argv[3] if len(sys.argv) > 3 else "v"
    out_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = b.new_context(storage_state=STATE, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0")
        page = ctx.new_page()
        state = None
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(6000)
            state = page.evaluate(
                """() => {
                    const s = window.__INITIAL_STATE__;
                    if (!s || !s.note) return null;
                    const map = s.note.noteDetailMap || {};
                    let fid = s.note.firstNoteId;
                    if (fid && typeof fid === 'object') fid = fid._value || fid._rawValue || null;
                    const keys = Object.keys(map);
                    const id = (fid && map[fid]) ? fid : keys[0];
                    const n = (map[id] || {}).note || {};
                    const v = n.video || {};
                    const m = v.mediaV2 || v.media || {};
                    const mm = (typeof m === 'string') ? JSON.parse(m) : m;
                    const st = mm.stream || {};
                    const out = {};
                    for (const [k, val0] of Object.entries(st)) {
                        let val = val0;
                        if (Array.isArray(val)) val = val[0];
                        if (!val || typeof val !== 'object') continue;
                        out[k] = {
                            master_url: val.master_url || val.masterUrl || val.backup_url_1 || '',
                            audio_bitrate: val.audio_bitrate || val.audioBitrate || 0,
                            video_bitrate: val.video_bitrate || val.videoBitrate || 0,
                            duration: val.duration || 0
                        };
                    }
                    return {title: n.title || n.desc || '', streams: out};
                }"""
            )
        except Exception as e:
            print("eval err", repr(e)[:300])
        if not state:
            print("NO_STATE")
            b.close()
            return 1
        streams = state.get("streams") or {}
        cands = [(k, v.get("master_url"), v.get("audio_bitrate", 0), v.get("video_bitrate", 0), v.get("duration", 0)) for k, v in streams.items() if v.get("master_url")]
        if not cands:
            print("NO_STREAM")
            b.close()
            return 2
        with_audio = [c for c in cands if c[2] and c[2] > 0]
        pool = with_audio or cands
        pool.sort(key=lambda c: (c[2] > 0, c[3]), reverse=True)
        best = pool[0]
        dur = max(c[4] for c in cands)
        title = state.get("title", "")
        m3u8 = best[1]
        print("dur_ms", dur, "title", title)
        if not m3u8:
            print("NO_STREAM")
            print(json.dumps(state.get("note", {}).get("noteDetailMap", {}), ensure_ascii=False)[:800])
            b.close()
            return 2
        dest = out_dir / f"{tag}.mp4"
        if m3u8.endswith(".m3u8"):
            print("M3U8 need ffmpeg", m3u8)
            dest.write_text(m3u8, encoding="utf-8")
            b.close()
            return 3
        r = ctx.request.get(m3u8, headers={"Referer": "https://www.xiaohongshu.com/", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0"})
        print("status", r.status, "len", len(r.body()))
        if r.status == 200 and len(r.body()) > 10000:
            dest.write_bytes(r.body())
            print("SAVED", dest, len(r.body()))
            (out_dir / f"{tag}.meta.json").write_text(json.dumps({"title": title, "dur_ms": dur, "url": url, "stream": m3u8}, ensure_ascii=False), encoding="utf-8")
            b.close()
            return 0
        b.close()
        return 4


if __name__ == "__main__":
    sys.exit(main())
