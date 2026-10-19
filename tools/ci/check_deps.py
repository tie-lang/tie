#!/usr/bin/env python3
"""库依赖方向守卫：lib/<layer> 只允许向下依赖。
退出码 1 表示存在非法边。"""
import os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LIB = os.path.join(ROOT, "lib")

ALLOWED = {
    "support": {"support", "std", "sys", "ext"},
    "diag":    {"diag", "support", "std", "sys", "ext"},
    "ir":      {"ir", "support", "diag", "std", "sys", "ext"},
    "front":   {"front", "ir", "support", "diag", "std", "sys", "ext"},
    "backend": {"backend", "ir", "support", "diag", "std", "sys", "ext"},
    "jit":     {"jit", "support", "std", "sys", "ext"},
    "rt":      {"rt"},
}

# 存量例外（只减不增）：修完即删。
EXCEPTIONS = {
    ("lib/backend/irgen.tie", "../front/semantic.tie"): "tig_src 便捷入口，待下沉到 tools",
    ("lib/backend/irgen.tie", "../front/consteval.tie"): "const fn 折叠依赖前端 AST，待语义层预折叠",
}

def layer_of(path):
    rel = os.path.relpath(path, LIB).replace("\\", "/")
    return rel.split("/")[0] if "/" in rel else ""

def main():
    bad = []
    for dp, _, fns in os.walk(LIB):
        for fn in fns:
            if not fn.endswith(".tie"):
                continue
            p = os.path.join(dp, fn)
            lay = layer_of(p)
            if lay not in ALLOWED:
                continue
            src = open(p, encoding="utf-8", errors="replace").read()
            for m in re.finditer(r'^\s*import\s+"([^"]+)"', src, re.M):
                imp = m.group(1)
                if imp.startswith("/"):
                    continue
                tgt = os.path.abspath(os.path.normpath(os.path.join(dp, imp)))
                if not tgt.startswith(LIB + os.sep):
                    continue
                tl = layer_of(tgt)
                if tl and tl not in ALLOWED[lay]:
                    rel = os.path.relpath(p, ROOT).replace("\\", "/")
                    if (rel, imp) in EXCEPTIONS:
                        continue
                    bad.append((rel, imp, lay, tl))
    for p, imp, a, b in bad:
        print(f"ILLEGAL {p}: {a} -> {b}  ({imp})")
    print(f"deps: {len(bad)} illegal edge(s)")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
