#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
verify_rewrite_distinct.py — 04 改写稿「必须与 03 逐字稿不同」的硬性验收闸门
=============================================================================
背景（2026-09-14 事故）：wx_pipeline.py 的 step_rewrite() 是纯规则脚本，
只会「套模板 + 摘原句」，产出的 04 实际是 03 的复制品（实测 04 正文 99-154 行
全抄 03，真正新写的只有 14 行模板占位话术），被用户当场指出「和逐字稿一样」。

因此任何平台、任何项目，交付 04 前**必须**跑本脚本，FAIL 一票否决、必须重写。

用法
----
python verify_rewrite_distinct.py <项目根目录> [--strict]

  默认自动识别 03 目录：03-逐字稿MD / 03-逐字稿 / 03-逐字稿MD
           04 目录：04-改写脚本 / 04-原视频脚本改写 / 04-改写

判定（任一命中即 FAIL）
----------------------
1. copy_lines  > 0            04 主体里有整行原样出现在 03 逐字稿中
2. lcs_len     > 15           04 与 03 存在 >15 个连续相同字符（去标点空白后）= 抄段
3. ngram8      > 0.15         04 主体的 8-gram 有 >15% 来自 03（改写腔调雷同）
4. placeholder > 0            出现模板占位话术（「直接抛出…」「在此填入」「TBD」等）
5. body_lines  < 8            04 主体有效行数太少 = 根本没写

--strict：阈值收紧（lcs>10、ngram8>0.08），用于高要求场景。

退出码：0 = 全部 PASS；1 = 有 FAIL；2 = 参数/目录错误
"""
import re
import sys
from pathlib import Path

MD3_NAMES = ["03-逐字稿MD", "03-逐字稿", "03-逐字稿MD文档"]
MD4_NAMES = ["04-改写脚本", "04-原视频脚本改写", "04-改写稿", "04-改写"]

# 模板占位话术（规则脚本套模板的典型产物，出现即说明没真正写）
PLACEHOLDER_PAT = re.compile(
    r"在此填入|待补充|（在此|TBD|TODO|直接抛出最有冲击力|参考角度|故事铺垫|"
    r"核心感悟|用 1 个具体场景|填写你的|xxx待写|\[待写\]",
    re.I,
)

TS_PREFIX = re.compile(r"^>\s*\[\d{1,2}:\d{2}(:\d{2})?\]\s*")
NON_BODY = ("|", "# ", "##", "---", "> **", "<", "![")


def norm(s: str) -> str:
    """归一化：去时间戳、标点、空白"""
    s = TS_PREFIX.sub("", s.strip())
    s = re.sub(r"[\s，。！？；：、,.!?;:\"'“”‘’（）()《》\-—…·|#*>`\[\]]", "", s)
    return s


def find_dir(base: Path, names):
    for n in names:
        d = base / n
        if d.is_dir():
            return d
    # 兜底：模糊匹配
    for d in base.iterdir():
        if d.is_dir() and any(n.strip("03-").strip("04-")[:3] in d.name for n in names):
            return d
    return None


def extract_original(md3_file: Path) -> str:
    """从 03 MD 提取逐字稿纯文本"""
    t = md3_file.read_text(encoding="utf-8", errors="ignore")
    lines = [TS_PREFIX.sub("", ln).strip() for ln in t.splitlines() if ln.startswith("> [")]
    if not lines:  # 兼容非分时段格式：整篇当原文
        lines = [ln.strip() for ln in t.splitlines() if ln.strip() and not ln.startswith(NON_BODY)]
    return "\n".join(lines)


def extract_rewrite_body(md4_file: Path) -> str:
    """取 04 中参考区之前、去掉表格/标题/元信息的「改写主体」"""
    t = md4_file.read_text(encoding="utf-8", errors="ignore")
    for marker in ("<details>", "## 📝 原稿参考", "## 原稿参考", "Original Core Script"):
        if marker in t:
            t = t.split(marker)[0]
            break
    body = []
    for ln in t.splitlines():
        s = ln.strip()
        if not s or s.startswith(NON_BODY) or re.match(r"^\d+\.\s*$", s):
            continue
        body.append(s)
    return "\n".join(body)


def lcs_len(a: str, b: str) -> int:
    """最长公共子串长度（a、b 为归一化后的纯字符串）"""
    if not a or not b:
        return 0
    # 二分 + 集合，避免 O(n*m) DP 爆内存
    lo, hi, best = 0, min(len(a), len(b)), 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if mid == 0:
            lo = mid + 1
            continue
        subs = {b[i:i + mid] for i in range(len(b) - mid + 1)}
        hit = any(a[i:i + mid] in subs for i in range(len(a) - mid + 1))
        if hit:
            best, lo = mid, mid + 1
        else:
            hi = mid - 1
    return best


def ngram_ratio(body: str, orig: str, n: int = 8) -> float:
    """body 中有多少比例的 n-gram 出现在 orig 中"""
    g = [body[i:i + n] for i in range(len(body) - n + 1)]
    if not g:
        return 0.0
    oset = {orig[i:i + n] for i in range(len(orig) - n + 1)}
    return sum(1 for x in set(g) if x in oset) / len(set(g))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    base = Path(sys.argv[1])
    strict = "--strict" in sys.argv
    lcs_th, ng_th = (10, 0.08) if strict else (15, 0.15)

    d3 = find_dir(base, MD3_NAMES)
    d4 = find_dir(base, MD4_NAMES)
    if not d3 or not d4:
        print(f"❌ 找不到目录：03={d3} 04={d4}")
        return 2

    md3 = sorted(d3.rglob("*.md"))
    print(f"项目：{base.name}")
    print(f"03={d3.name}（{len(md3)} 篇）  04={d4.name}")
    print(f"阈值：copy_lines=0  lcs≤{lcs_th}  ngram8≤{ng_th:.0%}  占位=0  主体≥8行"
          f"{'  [strict]' if strict else ''}")
    print()
    print(f"{'篇目':<26}{'主体行':>6}{'抄自03':>7}{'LCS':>6}{'8gram':>8}{'占位':>5}  判定")
    print("-" * 72)

    fails = 0
    for f3 in md3:
        cands = [d4 / (f3.stem + "_改写.md"), d4 / (f3.stem + "-改写脚本.md"), d4 / (f3.stem + ".md")]
        f4 = next((c for c in cands if c.exists()), None)
        if f4 is None:
            print(f"{f3.stem[:24]:<26}{'—':>6}{'—':>7}{'—':>6}{'—':>8}{'—':>5}  ❌ 缺改写稿")
            fails += 1
            continue

        orig_raw = extract_original(f3)
        orig = norm(orig_raw)
        body_raw = extract_rewrite_body(f4)
        body = norm(body_raw)

        orig_lines = {norm(l) for l in orig_raw.splitlines() if norm(l)}
        body_lines = [l for l in body_raw.splitlines() if l.strip()]
        copy = sum(1 for l in body_lines if norm(l) in orig_lines and len(norm(l)) >= 6)
        lc = lcs_len(body, orig)
        ng = ngram_ratio(body, orig)
        ph = len(PLACEHOLDER_PAT.findall(body_raw))

        ok = copy == 0 and lc <= lcs_th and ng <= ng_th and ph == 0 and len(body_lines) >= 8
        if not ok:
            fails += 1
        print(f"{f3.stem[:24]:<26}{len(body_lines):>6}{copy:>7}{lc:>6}{ng:>8.1%}{ph:>5}"
              f"  {'✅ PASS' if ok else '❌ FAIL'}")

        if not ok and len(body) > 0:
            # 打印最长重合片段，方便定位
            lo, hi = 0, min(len(body), len(orig))
            best = ""
            while lo <= hi:
                mid = (lo + hi) // 2
                if mid < 4:
                    lo = mid + 1
                    continue
                subs = {orig[i:i + mid] for i in range(len(orig) - mid + 1)}
                hit = next((body[i:i + mid] for i in range(len(body) - mid + 1)
                            if body[i:i + mid] in subs), None)
                if hit:
                    best, lo = hit, mid + 1
                else:
                    hi = mid - 1
            if best:
                print(f"    ↳ 最长重合片段（{len(best)}字）：{best[:60]}")

    print("-" * 72)
    total = len(md3)
    if fails:
        print(f"❌ {fails}/{total} 篇 FAIL —— 04 与 03 雷同，必须重写后才可交付")
        return 1
    print(f"✅ {total}/{total} 篇 PASS —— 04 与 03 已确认不同，可交付")
    return 0


if __name__ == "__main__":
    sys.exit(main())
