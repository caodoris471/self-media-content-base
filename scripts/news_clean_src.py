# -*- coding: utf-8 -*-
"""清洗四篇原文 → 正文纯文本（用于「原文文字稿」章节）"""
import urllib.request, ssl, gzip, re, os

BASE = r"C:\Users\<你的用户名>\AppData\Local\Temp\news_raw"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"

def get(url, lang="zh-CN,zh;q=0.9"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": lang})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
                d = r.read()
                if "gzip" in r.headers.get("Content-Encoding", ""):
                    d = gzip.decompress(d)
                return d.decode(r.headers.get_content_charset() or "utf-8", "ignore")
        except Exception as e:
            print("  retry", i, e)
    return None

def strip(h):
    b = re.sub(r"<script.*?</script>", "", h, flags=re.S)
    b = re.sub(r"<style.*?</style>", "", b, flags=re.S)
    m = re.search(r"<article[^>]*>(.*?)</article>", b, re.S)
    if m:
        b = m.group(1)
    else:
        m = re.search(r'class="[^"]*(?:post-content|entry-content|article-content)[^"]*"[^>]*>(.*?)</article>', b, re.S)
        if m:
            b = m.group(1)
    t = re.sub(r"<[^>]+>", "\n", b)
    t = re.sub(r"\n{2,}", "\n", t)
    return [l.strip() for l in t.split("\n") if l.strip()]

# 量子位：正文 = 从标题行到「版权所有」
def qbitai(lines):
    try:
        s = lines.index("量子位 | 公众号 QbitAI")
    except ValueError:
        s = 10
    try:
        e = next(i for i, l in enumerate(lines) if "版权所有" in l and i > s)
    except StopIteration:
        e = len(lines)
    return lines[s + 1:e]

# AIbase：正文 = 从标题行到「本文来自」
def aibase(lines):
    try:
        s = next(i for i, l in enumerate(lines) if "发布于" in l)
        s = next(i for i, l in enumerate(lines) if "Oct" in l and i >= s)
    except StopIteration:
        s = 3
    try:
        e = next(i for i, l in enumerate(lines) if "本文来自" in l)
    except StopIteration:
        e = len(lines)
    return lines[s + 1:e]

JOBS = [
    ("23_TRAE", "https://www.qbitai.com/2026/10/502426.html", qbitai),
    ("30_openJiuwen", "https://www.qbitai.com/2026/10/502106.html", qbitai),
    ("37_OSSScanner", "https://www.aibase.com/zh/news/31503", aibase),
    ("38_DoubaoCanvas", "https://www.aibase.com/zh/news/31504", aibase),
]

for name, url, fn in JOBS:
    h = get(url)
    lines = strip(h)
    body = fn(lines)
    txt = "\n".join(body)
    open(os.path.join(BASE, "src_" + name + ".txt"), "w", encoding="utf-8").write(txt)
    print("====", name, "chars:", len(txt))
    print(txt[:800])
    print("...")
