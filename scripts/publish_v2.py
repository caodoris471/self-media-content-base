#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""v2 重写稿回写飞书：把本地 md 整体 overwrite 到已有文档。

用法（本脚本同目录下执行）：
  python publish_v2.py kjx_v2:r31:PiCZwJn8LiE4e0kugJqcwKpqnQd rq_v2:r5:ESctwGuHWiXIkwkSBbJcvdYxnHf ...

参数格式  <子目录>:<文件名>:<wiki node_token>
"""
import json
import subprocess
import sys
from pathlib import Path

BASE = Path("{工作目录}/tools/scripts")


def run(args):
    r = subprocess.run(args, shell=True, capture_output=True, text=True,
                       encoding="utf-8", cwd=str(BASE))
    return r.returncode, (r.stdout or ""), (r.stderr or "")


def get_obj(node_token):
    rc, out, err = run(["lark-cli", "wiki", "+node-get", "--node-token", node_token])
    if rc != 0:
        return None
    try:
        return json.loads(out)["data"]["obj_token"]
    except Exception:
        return None


def overwrite(obj, md_path):
    rc, out, err = run([
        "lark-cli", "docs", "+update",
        "--doc", obj,
        "--command", "overwrite",
        "--doc-format", "markdown",
        "--content", "@" + str(md_path).replace("\\", "/"),
    ])
    return rc == 0, (out + err)[:300]


def main():
    ok, fail = [], []
    for spec in sys.argv[1:]:
        sub, name, node = spec.split(":")
        md = BASE / "work" / sub / f"{name}.md"
        if not md.exists():
            fail.append((name, "本地文件不存在"))
            print(f"{name} ✗ 本地文件不存在")
            continue
        obj = get_obj(node)
        if not obj:
            fail.append((name, "取 obj_token 失败"))
            print(f"{name} ✗ 取 obj 失败 node={node}")
            continue
        good, msg = overwrite(obj, md)
        if good:
            ok.append(name)
            print(f"{name} ✓ 已回写 obj={obj}")
        else:
            fail.append((name, msg))
            print(f"{name} ✗ 回写失败 {msg}")
    print(f"\n完成 {len(ok)} / 失败 {len(fail)}")
    for n, m in fail:
        print("  失败:", n, m)


if __name__ == "__main__":
    main()
