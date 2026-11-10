# tie

tie 是一门静态类型的系统编程语言。本仓是它的核心实现：自举编译器、标准库、
运行时、JIT 驱动，以及两种 tsc 解释器，全部用 tie 自身编写。

## 语言角色

源文件首行用 `type tie<角色>` 声明用途：

| 角色      | 用途                       |
| ------- | ------------------------ |
| `logic` | 可执行程序：编译成原生产物，`main` 为入口 |
| `tsc`   | 脚本：由解释器直接执行，无需编译         |
| `class` | 库与编译器自身：不注入脚本前置，不承载程序入口  |

其余角色（`type` / `data` / `tsh` / `ui` / `db` / `port`）按各自工具链处理。

## 仓库内容

| 路径                          | 说明                                |
| --------------------------- | --------------------------------- |
| `std/` `sys/` `ext/` `rdu/` | 标准库、平台库、扩展库、嵌入式库                  |
| `lib/`                      | 可共用代码：前端、IR、代码生成、后端、JIT、诊断、运行时    |
| `tools/tiec`                | 编译器：`logic` 源码 → 原生产物             |
| `tools/tiej`                | JIT 驱动：源码 → 进程内编译 → LLJIT → 按符号调用 |
| `tools/tiep`                | 重型 tsc 解释器：执行 `tsc` 脚本            |
| `tools/tiel`                | 轻量级嵌入式 tsc 解释器：可嵌入宿主              |
| `tools/diag`                | 崩溃诊断、剖析器、DAP 调试适配器                |
| `tools/release`             | 发行说明生成器                           |
| `tools/ci`                  | 依赖方向门禁                            |
| `examples/`                 | 示例程序                              |

## 环境要求

- Windows x86-64 或 Linux x86-64
- LLVM 工具链：`clang`、`opt`、`llvm-ar`、`llvm-nm`
- 一个可用的 `tiec` 作为引导编译器：从 Releases 下载，或使用系统中已安装的版本
- 可选：`tshell`（tie 语言的命令行壳），用于第二种构建方式

下文用 `TIEC` 表示引导编译器路径，`LLVM_PREFIX` 表示 LLVM 安装根。

## 构建

以下命令均在仓库根执行。Windows 产物带 `.exe` / `.dll` 后缀，Linux 去掉后缀并把 `.dll` 换成 `.so`。

### bash / POSIX shell

```bash
export TIE_LIB_ROOT=$PWD
TIEC=/path/to/tiec          # 引导编译器，请用绝对路径
LLVM_PREFIX=/path/to/llvm
mkdir -p build

# 1. 运行时（用引导编译器构建；编译器自身链接时需要它）
(cd lib/rt && "$TIEC" src/trm_lite.run.tie -o trm_lite.a --no-warn)
export TIE_TRM_LITE_LIB=$PWD/lib/rt/trm_lite.a

# 2. 编译器
"$TIEC" tools/tiec/src/driver.tie -l2 -t0 --no-warn --no-cache -o build/tiec

# 3. LLVM-C 垫片
clang -shared -O2 lib/jit/tiej_llvm.c \
      -I "$LLVM_PREFIX/include" -L "$LLVM_PREFIX/lib" -lLLVM-C \
      -o build/tiej_llvm.dll

# 4. JIT 驱动（导出定义让进程内 JIT 解析到宿主运行时符号）
python tools/tiej/gen_exports.py lib/rt/trm_lite.a build/tiej_exports.def
build/tiec tools/tiej/main.tie -o build/tiej \
      --link-arg "-Wl,/DEF:build/tiej_exports.def"

# 5. 验证
build/tiej --selftest
```

### tshell

tshell 是 tie 语言的命令行壳：同一套解析里可直接求值 tie 表达式，也可执行
内建命令与外部命令（`exec`），并支持目录切换（`cd`）、环境变量（`set`）与
变量展开（`{NAME}`）。同样的步骤也可以写成 `.tsh.tie` 脚本。

```
tsh> cd /path/to/tie
tsh> set TIE_LIB_ROOT .
tsh> var TIEC = "/path/to/tiec"
tsh> exec mkdir build
tsh> cd lib/rt
tsh> exec {TIEC} src/trm_lite.run.tie -o trm_lite.a --no-warn
tsh> cd ../..
tsh> set TIE_TRM_LITE_LIB lib/rt/trm_lite.a
tsh> exec {TIEC} tools/tiec/src/driver.tie -l2 -t0 --no-warn --no-cache -o build/tiec
tsh> exec clang -shared -O2 lib/jit/tiej_llvm.c -I /path/to/llvm/include -L /path/to/llvm/lib -lLLVM-C -o build/tiej_llvm.dll
tsh> exec python tools/tiej/gen_exports.py lib/rt/trm_lite.a build/tiej_exports.def
tsh> exec build/tiec tools/tiej/main.tie -o build/tiej --link-arg -Wl,/DEF:build/tiej_exports.def
tsh> exec build/tiej --selftest
```

`var NAME = "值"` 定义 REPL 变量，命令里用 `{NAME}` 展开（`cd` 之后仍可用）；
`set NAME VALUE` 设置环境变量并由子进程继承，会话内可用 `{get_env("NAME")}` 取回。

### 各步骤说明

1. **运行时**：`trm_lite.a` 提供表、调度、通道与生成器。编译器自身使用表容器，
   链接时必须能找到它，所以运行时先于编译器构建。
2. **编译器**：用引导编译器编译仓内编译器源码，得到与本仓同步的 `tiec`。
   `-l2` 为后端优化档、`-t0` 为中端档；`--no-cache` 保证不复用旧产物。
3. **垫片**：`lib/jit/tiej_llvm.c` 是 LLVM-C 薄封装，导出面固定、参数不超过
   5 个标量。
4. **JIT 驱动**：导出定义由运行时静态库符号表自动生成（含分配器）。
   它是构建期产物；JIT 运行期不依赖任何外部编译器进程。

### 平台差异

- Windows：产物为 `.exe` / `.dll`，导出定义用 `-Wl,/DEF:...` 注入。
- Linux：产物无后缀，垫片为 `.so`（加 `-fPIC`）；让可执行产物导出运行时
  符号改用 `--link-arg "-Wl,--export-dynamic"`。

## 运行

```bash
# 程序（logic 角色）
build/tiec examples/hello.tie -o build/hello
build/hello

# JIT：编译并直接调用函数
build/tiej examples/hello.tie main
build/tiej --macro examples/hello.tie main
```

`tiej` 用 `--sig i64,f64,bool --ret f64` 指定类型表与返回类型，省略时全部按
`i64`。参数类型支持 `i64` / `bool` / `f64` / `ptr`，返回类型另支持 `void`；`--macro`
允许编译期宏展开，默认显式拒绝。

## 其它工具

```bash
build/tiec tools/tiep/main.tie -o build/tiep
build/tiec tools/tiel/src/shell.tie -o build/tiel
build/tiec tools/diag/crashdiag.tie -o build/crashdiag
build/tiec tools/release/notes.tie -o build/notes
build/tiec tools/ci/dep_check.tie -o build/dep_check
```

脚本（tsc 角色）由解释器直接执行，无需编译：

```bash
build/tiep script.tie [参数...]
build/tiel script.tie
build/tiel --check script.tie
```

`tiel` 也可作为库嵌入：源码级 `import "tools/tiel/src/tiel.tie"`，或用
`--shared --dll-export "tiel$check,tiel$free_result"` 产出动态库。

## 测试

回归脚本用 tshell 运行，需要 `tshell` 与已构建的 `tiec`：

```bash
tsh -f tools/tiec/scripts/regress-s21.tsh.tie build/tiec
```

依赖方向门禁（只允许内置库、`lib/` 与同一工具项目内的分片）：

```bash
build/dep_check
```

## 许可

Tie Public License v2.3，见 `LICENSE`。协议模板见 `tpl.txt`。
