#!/usr/bin/env python3
"""构建 tiej 可执行产物：LLVM-C 垫片以静态对象链入宿主。

用法：
    python tools/tiej/build.py --tiec build/tiec.exe --llvm-prefix D:/LLVM
    python tools/tiej/build.py --tiec build/tiec.exe --llvm-prefix D:/LLVM --selftest

产物形态：
    tiej 只依赖 LLVM-C 运行库（Windows 为 LLVM-C.dll，Linux 为 libLLVM-C.so）；
    运行期不再装载任何自研垫片 DLL，也不启动任何编译器进程。

构建期三步：
    1. clang -c -DTJ_STATIC 把 lib/jit/tiej_llvm.c 编成对象文件；
    2. 从 trm_lite.a 符号表生成可执行产物的导出定义（仅 Windows 需要）；
    3. tiec 编译 tools/tiej/main.tie，链接对象、LLVM-C 导入库与导出定义。
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(cmd, env=None, label=""):
    print("[build] " + label)
    print("        " + " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run([str(c) for c in cmd], cwd=str(ROOT), env=env)
    if r.returncode != 0:
        print("构建失败（%s，退出码 %d）" % (label, r.returncode), file=sys.stderr)
        sys.exit(r.returncode or 1)


def need_file(p, what):
    if not Path(p).is_file():
        print("缺少%s：%s" % (what, p), file=sys.stderr)
        sys.exit(2)


def main() -> int:
    ap = argparse.ArgumentParser(description="构建 tiej（LLVM-C 静态链入形态）")
    ap.add_argument("--tiec", required=True, help="本仓编译器路径")
    ap.add_argument("--llvm-prefix", default=os.environ.get("LLVM_PREFIX", ""),
                    help="LLVM 安装根")
    ap.add_argument("--out-dir", default="build", help="产物目录（相对仓根）")
    ap.add_argument("--runtime-lib", default="lib/rt/trm_lite.a", help="运行时静态库")
    ap.add_argument("--clang", default="clang", help="clang 命令")
    ap.add_argument("--selftest", action="store_true", help="构建后运行自检")
    args = ap.parse_args()

    if not args.llvm_prefix:
        print("需要 --llvm-prefix 或环境变量 LLVM_PREFIX", file=sys.stderr)
        return 2
    llvm = Path(args.llvm_prefix)
    need_file(llvm / "include" / "llvm-c" / "LLJIT.h", " LLVM-C 头文件")
    need_file(args.tiec, "编译器")
    need_file(args.runtime_lib, "运行时静态库")
    # tiec 把 --link-arg 拼进命令字符串后交给系统 shell，含空格的路径会被拆开。
    for p in (str(llvm), args.out_dir, args.runtime_lib):
        if " " in p:
            print("路径含空格，--link-arg 无法安全传递：%s" % p, file=sys.stderr)
            return 2

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    windows = sys.platform == "win32"
    exe = out / ("tiej.exe" if windows else "tiej")
    obj = out / "tiej_llvm.o"

    env = os.environ.copy()
    env["TIE_LIB_ROOT"] = str(ROOT)
    env["TIE_TRM_LITE_LIB"] = str(Path(args.runtime_lib).resolve())

    cflags = [args.clang, "-c", "-O2", "-DTJ_STATIC", "-I", str(llvm / "include")]
    if not windows:
        cflags.append("-fPIC")
    run(cflags + [str(ROOT / "lib/jit/tiej_llvm.c"), "-o", str(obj)],
        env=env, label="编译 LLVM-C 垫片对象")

    parts = []
    if windows:
        defn = out / "tiej_exports.def"
        run([sys.executable, str(ROOT / "tools/tiej/gen_exports.py"),
             str(args.runtime_lib), str(defn)], env=env, label="生成运行时导出定义")
        parts.append("-Wl,/DEF:" + str(defn))
    else:
        # ELF 默认不导出可执行产物的静态符号，JIT 进程符号解析需要显式打开。
        parts.append("-Wl,--export-dynamic")
    parts += [str(obj), "-L" + str(llvm / "lib"), "-lLLVM-C"]
    if not windows:
        parts.append("-Wl,-rpath," + str(llvm / "lib"))
    link_arg = " ".join(parts)

    run([str(Path(args.tiec).resolve()), "tools/tiej/main.tie", "-o", str(exe),
         "--link-arg", link_arg], env=env, label="编译并链接 tiej")

    print("[build] 产物：%s" % exe)
    if args.selftest:
        senv = env.copy()
        senv["PATH"] = str(llvm / "bin") + os.pathsep + senv.get("PATH", "")
        run([str(exe.resolve()), "--selftest"], env=senv, label="自检")
    return 0


if __name__ == "__main__":
    sys.exit(main())
