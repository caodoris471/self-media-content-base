# -*- coding: utf-8 -*-
"""资讯表稿件发布器（2026-10-10 跑通固化）

用途：把一篇已过 qa_check 闸门的稿件 MD 建成知识库文档，并回写
      资讯表（Ai资讯热点 {AI资讯表ID} / 跨境资讯热点 {跨境资讯表ID}）的
      F 列（文档卡片）+ G 列（完成情况 = 已改写待审核）。

用法:
  python publish_news.py <row> "<原标题>" <md绝对路径> [--sheet {AI资讯表ID}]

四个已踩过的坑（别再踩）:
  1. docs +create 的返回在 data.document.document_id，不是 data.document_id
  2. rich_text 是【扁平】结构：type/text/mention_token/mention_type/link 同级，
     不是 {"mention": {...}} 嵌套，text 缺失会报 validation 错
  3. wiki +node-list 默认只返 50 条，新文档常在后面 → 必须 --page-all --page-limit 0
  4. wiki +node-delete 需要 --obj-type docx + --yes
"""
import subprocess, json, sys, time, argparse

LK = r"C:\Users\<你的用户名>\.workbuddy\binaries\node\cli-connector-packages\lark-cli.cmd"
SS = "{spreadsheet_token}"
PARENT = "EaZ5wDZCcini6IkwgMvcCXtznEs"
SPACE = "7686427942053743806"
WIKI_HOST = "https://{你的飞书域名}.feishu.cn/wiki/"


def cli(args):
    r = subprocess.run([LK] + args, capture_output=True, text=True,
                       encoding="utf-8", shell=True)
    return r.stdout, r.stderr


def jout(s):
    try:
        return json.loads(s)
    except Exception:
        return None


def create_doc(title, md):
    out, err = cli(["docs", "+create", "--parent-token", PARENT, "--title", title,
                    "--doc-format", "markdown", "--content", "@" + md, "--as", "user"])
    d = jout(out)
    if not d or not d.get("ok"):
        return None, out[:400] + err[:200]
    doc = d["data"].get("document") or d["data"]
    return doc.get("document_id") or doc.get("token"), None


def find_node(docx_token):
    out, _ = cli(["wiki", "+node-list", "--space-id", SPACE,
                  "--parent-node-token", PARENT, "--page-all", "--page-limit", "0",
                  "--as", "user"])
    d = jout(out)
    if not d or not d.get("ok"):
        return None
    for it in (d["data"].get("items") or d["data"].get("nodes") or []):
        if (it.get("obj_token") or it.get("obj_id")) == docx_token:
            return it.get("node_token")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("row", type=int)
    ap.add_argument("title")
    ap.add_argument("md")
    ap.add_argument("--sheet", default="{AI资讯表ID}")
    a = ap.parse_args()

    docx, err = create_doc(a.title, a.md)
    if not docx:
        print("CREATE FAILED:", err)
        return 1
    print("docx:", docx)
    time.sleep(1.5)

    node = find_node(docx)
    if not node:
        print("WARN: wiki node not found, fallback to docx link")
        url = "https://{你的飞书域名}.feishu.cn/docx/" + docx
        mention_token, mtype = docx, 22
    else:
        url = WIKI_HOST + node
        mention_token, mtype = node, 16
    print("node:", node, "| url:", url)

    cell = {"rich_text": [{"type": "mention", "text": a.title,
                           "mention_token": mention_token,
                           "mention_type": mtype, "link": url}]}
    writes = json.dumps([
        {"sheet_id": a.sheet, "range": "F%d" % a.row, "cells": [[cell]]},
        {"sheet_id": a.sheet, "range": "G%d" % a.row,
         "cells": [[{"value": "已改写待审核"}]]},
    ], ensure_ascii=False)
    out, err = cli(["sheets", "+cells-set", "--spreadsheet-token", SS,
                    "--writes", writes, "--as", "user"])
    d = jout(out)
    print("write:", "OK" if (d and d.get("ok") and d["data"].get("failed") == 0) else "FAIL")
    if not (d and d.get("ok")):
        print(out[:400], err[:300])
    return 0 if (d and d.get("ok")) else 1


if __name__ == "__main__":
    sys.exit(main())
