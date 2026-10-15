import sys, json
from playwright.sync_api import sync_playwright

STATE = r"{工作目录}\MediaCrawler\xhs_storage_state.json"
url = sys.argv[1]
JS = """() => {
  const s = window.__INITIAL_STATE__ || {};
  const note = s.note || {};
  const map = note.noteDetailMap || {};
  const keys = Object.keys(map);
  let info = null;
  if (keys.length) {
    const n = (map[keys[0]] || {}).note || {};
    info = {noteId: n.noteId, type: n.type, hasVideo: !!n.video, title: (n.title||n.desc||'').slice(0,60), desc: (n.desc||'').slice(0,80)};
  }
  return {topKeys: Object.keys(s), noteKeys: Object.keys(note), mapLen: keys.length, first: note.firstNoteId, info,
          hasUser: !!(s.user||{}).login, bodyText: document.body.innerText.slice(0,200)};
}"""
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(storage_state=STATE)
    page = ctx.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        print("goto err:", repr(e)[:200])
    page.wait_for_timeout(8000)
    print(json.dumps(page.evaluate(JS), ensure_ascii=False, indent=1))
    b.close()
