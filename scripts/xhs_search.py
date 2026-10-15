"""小红书搜索：找笔记链接（带有效 xsec_token）。
用法: python xhs_search.py "<关键词>"
"""
import json
import sys
from urllib.parse import quote

from playwright.sync_api import sync_playwright

STATE = r"{工作目录}\MediaCrawler\xhs_storage_state.json"
kw = sys.argv[1]
url = "https://www.xiaohongshu.com/search_result?keyword=" + quote(kw) + "&source=web_explore_feed"
JS = """() => {
  const cards = Array.from(document.querySelectorAll('section.note-item, div.note-item, .feeds-page .note-item'));
  const out = [];
  for (const c of cards) {
    const a = c.querySelector('a[href*="/search_result/"], a.cover, a[href*="/explore/"], a[href*="/discovery/item/"]');
    const t = c.querySelector('.title span, .title, a.title');
    if (a) out.push({href: a.getAttribute('href'), title: (t ? t.innerText : '').slice(0,80)});
  }
  return out.slice(0, 15);
}"""
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(storage_state=STATE)
    page = ctx.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(8000)
    try:
        page.wait_for_selector("section.note-item", timeout=15000)
    except Exception:
        pass
    res = page.evaluate(JS)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print("URL", page.url[:120])
    b.close()
