#!/usr/bin/env python3
"""tiej 回归：输出、退出码与产物形态逐项比对。

用法：
    python tools/tiej/regress.py build/tiej.exe [--llvm-prefix D:/LLVM]

覆盖标量运算、任意参数个数、混合签名与 f64、表运行时、越界检查、编译期宏
的接受 / 默认拒绝 / 展开失败诊断，以及自检的完整 JIT 链路。同时断言产物里
不再含自研垫片名：运行期不需要随产物分发 tiej_llvm.dll。
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
T = "tools/tiej/tests/"

# (用例名, 参数, 期望退出码, 期望完整输出, 输出必须包含的片段)
# 成功路径比对完整文本；失败路径只比对 ASCII 诊断片段，避免本地代码页
# 影响中文错误串的解码结果。
CASES = [
    ("selftest", ["--selftest"], 0, None, "tiej selftest: PASS"),
    ("add", [T + "add.tie", "add", "3", "4"], 0, "add = 7", None),
    ("fact5", [T + "fact.tie", "fact", "5"], 0, "fact = 120", None),
    ("fact10", [T + "fact.tie", "fact", "10"], 0, "fact = 3628800", None),
    ("poly12", [T + "calc.tie", "poly", "12"], 0, "poly = 44", None),
    ("poly3", [T + "calc.tie", "poly", "3"], 0, "poly = 10", None),
    ("sum7", [T + "multi.tie", "sum7", "1", "2", "3", "4", "5", "6", "7"],
     0, "sum7 = 28", None),
    ("mix-true", [T + "multi.tie", "mix", "--sig", "i64,f64,bool", "--ret", "f64",
                  "1", "2.5", "1"], 0, "mix = 5", None),
    ("mix-false", [T + "multi.tie", "mix", "--sig", "i64,f64,bool", "--ret", "f64",
                   "1", "2.5", "0"], 0, "mix = 3.5", None),
    ("tblen", [T + "tbl.tie", "tblen"], 0, "tblen = 4", None),
    ("tsum", [T + "tbl.tie", "tsum"], 0, "tsum = 60", None),
    ("new-i64", [T + "tbl_full.tie", "new_i64"], 0, "new_i64 = 2", None),
    ("rw-i64", [T + "tbl_full.tie", "rw_i64"], 0, "rw_i64 = 9", None),
    ("sum-i64", [T + "tbl_full.tie", "sum_i64"], 0, "sum_i64 = 30", None),
    ("new-string", [T + "tbl_full.tie", "new_string"], 0, "new_string = 2", None),
    ("oob", [T + "tbl_oob.tie", "oob"], 1, None, "OOB"),
    ("macro-fldbl", [T + "macro.tie", "use_fldbl", "--macro"], 0, "use_fldbl = 42", None),
    ("macro-dbl", [T + "macro.tie", "use_dbl", "--macro"], 0, "use_dbl = 42", None),
    ("macro-hygiene", [T + "macro.tie", "hygiene", "--macro"], 0, "hygiene = 99", None),
    ("macro-rejected", [T + "macro.tie", "use_fldbl"], 1, None, "ERR:"),
    ("macro-bad", [T + "macro_bad.tie", "bad", "--macro"], 1, None, "ERR:"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="tiej 回归")
    ap.add_argument("exe", help="tiej 可执行产物路径")
    ap.add_argument("--llvm-prefix", default=os.environ.get("LLVM_PREFIX", ""),
                    help="LLVM 安装根（把 bin 目录加入 PATH）")
    args = ap.parse_args()
    exe = Path(args.exe)
    if not exe.is_file():
        print("找不到产物：%s" % exe, file=sys.stderr)
        return 2

    env = os.environ.copy()
    env["TIE_LIB_ROOT"] = str(ROOT)
    if args.llvm_prefix:
        env["PATH"] = str(Path(args.llvm_prefix) / "bin") + os.pathsep + env.get("PATH", "")

    failed = 0
    for name, argv, want_rc, exact, contains in CASES:
        try:
            p = subprocess.run([str(exe)] + argv, cwd=str(ROOT), env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               timeout=180)
        except subprocess.TimeoutExpired:
            print("[FAIL] %s: 超时" % name)
            failed += 1
            continue
        out = p.stdout.decode("utf-8", "replace").strip()
        ok = p.returncode == want_rc
        if exact is not None:
            ok = ok and out == exact
        if contains is not None:
            ok = ok and contains in out
        if ok:
            print("[PASS] %s" % name)
        else:
            failed += 1
            print("[FAIL] %s: rc=%d (期望 %d) out=%r" % (name, p.returncode, want_rc, out[:160]))

    # 产物形态：静态链入垫片后不应再出现自研 DLL 名。
    if b"tiej_llvm.dll" in exe.read_bytes():
        failed += 1
        print("[FAIL] 产物仍含自研垫片名 tiej_llvm.dll")
    else:
        print("[PASS] 产物不含自研垫片名")

    print("tiej 回归：%d 项，%d 失败" % (len(CASES) + 1, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
