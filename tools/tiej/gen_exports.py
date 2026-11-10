#!/usr/bin/env python3
"""生成 JIT 宿主可执行产物的导出定义。

JIT 代码通过进程符号解析调用运行时函数，可执行产物的静态符号默认不在
导出表里。本脚本从运行时静态库的符号表自动生成导出定义，避免手写白名单
在运行时新增函数后漏导出。

用法：
    python gen_exports.py <运行时静态库> <输出 .def>

产物只写 EXPORTS 段：写 LIBRARY 会让链接器把产物标成 DLL，Windows 拒绝
直接执行。可执行产物的导出定义不需要库名。
"""
import subprocess
import sys


def read_symbols(lib: str) -> str:
    for tool in ("llvm-nm", "nm"):
        try:
            r = subprocess.run([tool, "--defined-only", lib],
                               capture_output=True, text=True)
        except FileNotFoundError:
            continue
        if r.returncode == 0 and r.stdout:
            return r.stdout
    return ""


def main() -> int:
    if len(sys.argv) != 3:
        print("用法: gen_exports.py <运行时静态库> <输出 .def>", file=sys.stderr)
        return 2
    lib, out = sys.argv[1], sys.argv[2]
    text = read_symbols(lib)
    if not text:
        print("无法读取静态库符号表（需要 llvm-nm 或 nm）", file=sys.stderr)
        return 1

    funcs, data = set(), set()
    for line in text.splitlines():
        cols = line.split()
        if len(cols) < 3:
            continue
        kind, name = cols[1], cols[2]
        if not name or name.startswith("."):
            continue
        if kind in ("T", "t", "W"):
            funcs.add(name)
        elif kind in ("D", "d", "B", "b", "R", "r"):
            data.add(name)

    # JIT 模块里的分配与内存操作同样走进程符号解析。宿主若静态链接 CRT，
    # 运行时释放与 JIT 分配会落在不同堆，触发堆损坏；显式导出宿主实现
    # 可保证两侧使用同一套堆。
    funcs |= {"malloc", "free", "calloc", "realloc", "memcpy", "memset"}
    data -= funcs

    with open(out, "w", encoding="ascii", newline="\n") as f:
        f.write("EXPORTS\n")
        for name in sorted(funcs):
            f.write("    " + name + "\n")
        for name in sorted(data):
            f.write("    " + name + " DATA\n")
    print("导出函数 %d 个、数据 %d 个 -> %s" % (len(funcs), len(data), out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
