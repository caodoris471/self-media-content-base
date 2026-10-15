"""公众号正文抓取：Playwright Edge 取 #js_content。
用法: python fetch_wx_edge.py <url> <out.txt>
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

url = sys.argv[1]
out = Path(sys.argv[2])
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    ctx = b.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0")
    page = ctx.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)
    title = page.title()
    try:
        page.wait_for_selector("#js_content", timeout=15000)
    except Exception:
        pass
    txt = ""
    try:
        txt = page.evaluate("() => { const e = document.getElementById('js_content'); return e ? e.innerText : ''; }")
    except Exception as e:
        print("eval err", repr(e)[:200])
    if len(txt) < 250:
        txt = page.evaluate("() => document.body.innerText")
    out.write_text(f"# {title}\n\n{txt}", encoding="utf-8")
    print("TITLE:", title)
    print("LEN:", len(txt))
    print(txt[:600])
    b.close()
