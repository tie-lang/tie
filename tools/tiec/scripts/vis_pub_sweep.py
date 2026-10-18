# -*- coding: utf-8 -*-
"""vis_pub_sweep.py —— 全局可见性收紧的一次性迁移预处理。

用法：
    python scripts/vis_pub_sweep.py <tiec.exe> <入口.tie> <扫描根> [--lib-root DIR] [--apply]

流程：TIE_VIS_AUDIT=1 跑审计 → 收集「全局 <名>」清单 → 在每个扫描根下给
col-0 的 `var <名>` / `const <名>` 声明补 `pub ` 前缀（幂等；ns 成员同名行一并
补 pub 属正常拓宽，无害）→ 复跑直至审计清零。默认 dry-run，--apply 才落盘。

背景：2026-10-13 顶层全局/常量收紧（跨文件引用须 pub，与函数同制度）；
gb_decl_file 活体树反查见 sstate_q1。审计行格式：
    vis-audit: 全局 NAME（声明文件 N → 调用文件 M）
"""
import io, os, re, subprocess, sys

def audit(tiec, entry, lib_root):
    env = dict(os.environ)
    env["TIE_VIS_AUDIT"] = "1"
    cmd = [tiec, "--no-cache", entry, "-o", os.path.join(os.path.dirname(entry) or ".", "_sweep_tmp.exe")]
    if lib_root:
        cmd += ["--lib-root", lib_root]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    out = (p.stdout or "") + (p.stderr or "")
    names = sorted(set(re.findall(r"vis-audit-global: (\S+)", out)))
    return names, out

def patch_roots(roots, names, apply):
    hits = 0
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            if ".git" in dirpath or "_bak" in dirpath:
                continue
            for fn in filenames:
                if not fn.endswith(".tie"):
                    continue
                path = os.path.join(dirpath, fn)
                text = io.open(path, encoding="utf-8").read()
                lines = text.split("\n")
                changed = False
                for i, ln in enumerate(lines):
                    newln = ln
                    for kw in ("var", "const"):
                        for nm in names:
                            pat_lead = "pub " + kw + " " + nm
                            if newln.startswith(pat_lead):
                                continue
                            lead = kw + " " + nm
                            if newln.startswith(lead + " ") or newln.startswith(lead + ":"):
                                newln = "pub " + newln
                                hits += 1
                            else:
                                mid = "; " + kw + " " + nm
                                if (mid + " ") in newln or (mid + ":") in newln:
                                    newln = newln.replace(mid, "; pub " + kw + " " + nm, 1)
                                    hits += 1
                    if newln != ln:
                        lines[i] = newln
                        changed = True
                if changed:
                    print("patch: " + path)
                    if apply:
                        io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    return hits

def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    tiec, entry, scanroot = sys.argv[1], sys.argv[2], sys.argv[3]
    apply = "--apply" in sys.argv
    lib_root = None
    if "--lib-root" in sys.argv:
        lib_root = sys.argv[sys.argv.index("--lib-root") + 1]
    names, out = audit(tiec, entry, lib_root)
    print("审计命中全局数: %d" % len(names))
    if names:
        print("前 20: " + ", ".join(names[:20]))
    if apply and names:
        hits = patch_roots([scanroot], names, True)
        print("补 pub 行数: %d" % hits)
        names2, _ = audit(tiec, entry, lib_root)
        print("复审计余: %d" % len(names2))
        if names2:
            print("仍剩前 20: " + ", ".join(names2[:20]))
    return 0

if __name__ == "__main__":
    sys.exit(main())
