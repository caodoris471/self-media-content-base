import json, sys

SNAP = sys.argv[1] if len(sys.argv) > 1 else "rq_snapshot.json"
data = json.load(open(SNAP, encoding="utf-8"))
ranges = data.get("ranges") or data.get("data", {}).get("ranges") or []
cells = ranges[0].get("cells") or ranges[0].get("values")

def cell(x):
    if isinstance(x, dict):
        v = x.get("value")
        if v is None:
            v = x.get("text")
        return "" if v is None else str(v)
    return "" if x is None else str(x)

for i, row in enumerate(cells, start=1):
    c = [cell(x) for x in row]
    while len(c) < 12:
        c.append("")
    d, f, g, h, ii, j, k = c[3], c[5], c[6], c[7], c[8], c[9], c[10]
    print(f"{i:>3} | D={d[:8]:<8} | F={f[:34]:<34} | G={g[:52]:<52} | I={ii:<5} | J={j:<4} | K={k[:10]:<10} | H={'Y' if h.strip() else '-'}")
