import sys, json
from playwright.sync_api import sync_playwright

STATE = r"{工作目录}\MediaCrawler\xhs_storage_state.json"
url = sys.argv[1]
JS = """() => {
  const s = window.__INITIAL_STATE__ || {};
  const map = s.note.noteDetailMap || {};
  const k = Object.keys(map)[0];
  const n = (map[k]||{}).note||{};
  const v = n.video || {};
  const m = v.mediaV2 || v.media || {};
  const mm = (typeof m === 'string') ? JSON.parse(m) : m;
  const st = mm.stream || {};
  const out = {};
  for (const [kk, val] of Object.entries(st)) {
    if (!val || typeof val !== 'object') continue;
    out[kk] = Object.keys(val).slice(0,20);
  }
  return {videoKeys: Object.keys(v), mediaKeys: Object.keys(mm), streamKeys: Object.keys(st), streamFields: out,
          raw: JSON.stringify(st).slice(0,1500), imageList: (n.imageList||[]).length};
}"""
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(storage_state=STATE)
    page = ctx.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(8000)
    print(json.dumps(page.evaluate(JS), ensure_ascii=False, indent=1)[:4000])
    b.close()
