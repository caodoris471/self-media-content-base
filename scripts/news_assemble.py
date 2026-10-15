# -*- coding: utf-8 -*-
"""拼装最终 MD：# 标题 + 一、原文文字稿 + 二、改写长文稿 + 三、口播稿"""
import os, re

BASE = r"C:\Users\<你的用户名>\AppData\Local\Temp\news_raw"

def wash(lines):
    """通用清洗：去纯 URL 行、表情占位符、HTML 实体"""
    out = []
    for l in lines:
        if re.fullmatch(r"https?://\S*", l.strip()):
            continue
        l = re.sub(r"\[[A-Za-z]{1,12}\]", "", l)          # [solute] 这类表情占位
        l = re.sub(r"&[a-zA-Z#0-9]{2,8};", "", l)          # &#8211; 实体
        if l.strip():
            out.append(l)
    return out

def tail_trim(lines):
    """去掉尾部孤立标签行（短且无标点）"""
    out = list(lines)
    while out:
        last = out[-1]
        if len(last) < 20 and not re.search(r"[。，、：；！？]", last):
            out.pop()
        else:
            break
    return out

JOBS = [
    ("23_TRAE", "TRAE终于把Code和Work合并了"),
    ("30_openJiuwen", "openJiuwen发布并开源企业级AgentOS，加速智能体规模落地企业"),
    ("37_OSSScanner", "Anthropic重磅推出OSS Scanner，用最强AI模型为全球开源软件免费扫漏洞"),
    ("38_DoubaoCanvas", "一张无限画布装下所有创作：豆包工作上新，图片、视频、HTML 自动汇入同一画布"),
]

for name, title in JOBS:
    src = open(os.path.join(BASE, "src_" + name + ".txt"), encoding="utf-8").read()
    lines = tail_trim(wash(src.split("\n")))
    body = open(os.path.join(BASE, "body_" + name + ".md"), encoding="utf-8").read()
    md = "# %s\n\n## 一、原文文字稿\n\n%s\n\n%s\n" % (title, "\n".join(lines), body.strip())
    p = os.path.join(BASE, "final_" + name + ".md")
    open(p, "w", encoding="utf-8").write(md)
    cjk = len(re.findall(r"[\u4e00-\u9fff]", md))
    print(name, "| total cjk:", cjk, "| src lines:", len(lines))
