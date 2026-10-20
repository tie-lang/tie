#!/usr/bin/env python3
"""库依赖方向守卫：lib/<layer> 只允许向下依赖。

层序（自下而上）：support → diag → ir → ast → front → codegen → backend；jit / rt 挂靠底层。
ast 是语法树契约层：节点标签常量、节点池、列式镜像表与访问器，零 import，供前端与
codegen 共同依赖；codegen 是「AST → tie-IR」的中层，位于前端之后、后端之前；backend
只剩「tie-IR → LLVM IR 文本」的发射层。
退出码 1 表示存在非法边。"""
import os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LIB = os.path.join(ROOT, "lib")

ALLOWED = {
    "support": {"support", "std", "sys", "ext"},
    "diag":    {"diag", "support", "std", "sys", "ext"},
    "ir":      {"ir", "support", "diag", "std", "sys", "ext"},
    "ast":     {"ast", "support", "diag", "std", "sys", "ext"},
    "front":   {"front", "ast", "ir", "support", "diag", "std", "sys", "ext"},
    "codegen": {"codegen", "ast", "front", "ir", "support", "diag", "std", "sys", "ext"},
    "backend": {"backend", "codegen", "ast", "ir", "support", "diag", "std", "sys", "ext"},
    "jit":     {"jit", "support", "std", "sys", "ext"},
    "rt":      {"rt"},
}

# 存量例外（只减不增）：修完即删。当前为零——codegen 层建立后，irgen 对前端的
# 依赖已成为合法的向下依赖，不再需要放行。
#
# codegen -> front 的依赖面（与 LLVM 的 CodeGen 消费 Sema 产物同构，显式登记于此，
# 避免后来者误以为是遗漏）：
#   * lib/codegen/irgen.tie  import ../front/semantic.tie  —— tig_src 的语义检查入口
#   * lib/codegen/irgen.tie  import ../front/consteval.tie —— 全局初值里的 const fn 折叠
#   * sstate 的语义查询（child / nchild / name_str / slot_off / fn_sig / fn_def_node /
#     bs_find）在 codegen 中约五百处，经上面的 import 链传递可见。这条隐式可见性是
#     本守卫的已知盲区：它只读显式 import 行，看不见裸标识符引用。lib/ast 契约层把
#     节点字段的裸表访问收成了访问器，语义查询的同等收敛需要单独的 lib/sema 层。
EXCEPTIONS = {}

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
