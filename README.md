# tie

tie 是一门静态类型的系统编程语言。本仓是它的核心实现：自举编译器、标准库、
运行时、JIT 驱动，以及两种 tsc 解释器，全部用 tie 自身编写。

## 语言角色

源文件首行用 `type tie<角色>` 声明用途：

| 角色      | 用途                                  |
| ------- | ----------------------------------- |
| `logic` | 可执行程序：编译成原生产物，`main` 为入口             |
| `tsc`   | 脚本：由解释器直接执行，无需编译                    |
| `lib`   | 库：显式声明为库，禁止程序入口，可承载模块命名空间           |
| `class` | 库：编译器自身与其配套实现使用，不注入脚本前置             |

其余角色（`type` / `data` / `tsh` / `ui` / `db` / `port`）按各自工具链处理。

## 历史

早期实现分散在多个仓库：编译器与解释器在 `tiec` 仓，设计与文档在 `tie-main` 仓，
本仓只放标准库与工具；当时的编译器前端、解释器与 IR 后端用 Rust 编写。

编译器后来改用 tie 自身重写并完成自举，Rust 实现退役。编译器、标准库、解释器
与运行时相继迁入本仓，`tiec` 等旧仓不再维护，其脚本与门禁路径也不随本仓同步。
本仓由此成为核心实现的单一主体，`lib/`、`std/`、`tools/` 即合并后的布局。

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
| `tools/tshell`              | 命令行壳：REPL、脚本运行时、系统命令与值管道     |
| `examples/`                 | 示例程序                              |

## 环境要求

- Windows x86-64 或 Linux x86-64
- LLVM 工具链：`clang`、`opt`、`llvm-ar`、`llvm-nm`，以及 LLVM-C 的头文件与
  导入库（`LLVM-C.lib` / `libLLVM-C.so`）
- 一个可用的 `tiec` 作为引导编译器：从 Releases 下载，或使用系统中已安装的版本
- 可选：`tshell`（tie 语言的命令行壳），用于第二种构建方式
- Python 3：生成 JIT 导出定义、构建 JIT 驱动、运行 JIT 回归

`tiej` 运行期只需要 LLVM-C 运行库（Windows 为 `LLVM-C.dll`，Linux 为
`libLLVM-C.so`），把它所在目录加入 `PATH` / `LD_LIBRARY_PATH` 即可。产物不
需要额外的编译器进程，也不需要随附任何自研垫片动态库。

下文用 `TIEC` 表示引导编译器路径，`LLVM_PREFIX` 表示 LLVM 安装根。

## 构建

以下命令按 Windows 书写；Linux 去掉 `.exe` 后缀。命令均在仓库根执行，平台差异由构建脚本自动处理。

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
"$TIEC" tools/tiec/src/driver.tie -l2 -t0 --no-warn --no-cache -o build/tiec.exe

# 3. JIT 驱动：垫片对象、导出定义与链接一次完成
python tools/tiej/build.py --tiec build/tiec.exe --llvm-prefix "$LLVM_PREFIX" --selftest
```

### tshell

tshell 是 tie 语言的命令行壳：同一套解析里可直接求值 tie 表达式，也可执行
内建命令与外部命令（`exec`），并支持目录切换（`cd`）、环境变量（`set`）与
变量展开（`{NAME}`）。同样的步骤也可以写成 `.tsh.tie` 脚本。

```
tsh> cd /path/to/tie
tsh> set TIE_LIB_ROOT .
tsh> var TIEC = "/path/to/tiec"
tsh> mkdir build
tsh> cd lib/rt
tsh> exec {TIEC} src/trm_lite.run.tie -o trm_lite.a --no-warn
tsh> cd ../..
tsh> set TIE_TRM_LITE_LIB lib/rt/trm_lite.a
tsh> exec {TIEC} tools/tiec/src/driver.tie -l2 -t0 --no-warn --no-cache -o build/tiec.exe
tsh> python tools/tiej/build.py --tiec build/tiec.exe --llvm-prefix /path/to/llvm --selftest
```

外部命令直接写即可（解析顺序是 tie 表达式 → 内建命令 → 外部命令），不必加
`exec`；只有命令名本身是变量或表达式时才用 `exec {…}`。`var NAME = "值"` 定义的
变量在 `cd` 之后仍可用 `{NAME}` 展开；`set NAME VALUE` 设置环境变量并由子进程
继承，会话内可用 `get_env("NAME")` 取回。

### 各步骤说明

1. **运行时**：`trm_lite.a` 提供表、调度、通道与生成器。编译器自身使用表容器，
   链接时必须能找到它，所以运行时先于编译器构建。
2. **编译器**：用引导编译器编译仓内编译器源码，得到与本仓同步的 `tiec`。
   `-l2` 为后端优化档、`-t0` 为中端档；`--no-cache` 保证不复用旧产物。
3. **JIT 驱动**：`tools/tiej/build.py` 把 `lib/jit/tiej_llvm.c` 编成静态对象
   链进 `tiej`，并从 `trm_lite.a` 的符号表生成导出定义（含宿主分配器）。
   对象与导出定义都是构建期产物；JIT 运行期不启动任何编译器进程，也不装载
   自研垫片动态库。LLVM-C 垫片自身的导出面固定为不超过 5 个标量参数，这是
   宿主 `dyn_call_p` 的历史约束，与 `tiej` 能调用的函数签名无关——实参由 JIT
   侧生成的零参数包装函数承载。
4. **自检**：`--selftest` 走完整的 ABI 校验 → 会话创建 → IR 装载 → 查符号 →
   调用 → 关闭链路。

### 平台差异

- Windows：产物为 `.exe`；`build.py` 生成 `.def` 导出定义并用
  `-Wl,/DEF:...` 注入，运行需要 `LLVM-C.dll` 在 `PATH` 中。
- Linux：产物不加后缀，垫片对象加 `-fPIC`；可执行产物导出运行时符号改用
  `-Wl,--export-dynamic`，运行需要能定位 `libLLVM-C.so`。

平台判定与上述链接参数都由 `build.py` 自动完成，无需手工切换。

## 运行

```bash
# 程序（logic 角色）
build/tiec.exe examples/hello.tie -o build/hello.exe
build/hello.exe

# JIT：编译并直接调用函数
build/tiej.exe examples/hello.tie main
build/tiej.exe --macro examples/hello.tie main

# JIT 会话：同一进程装载多个单元、复用编译缓存、按单元卸载
build/tiej.exe --repl
```

`--repl` 从标准输入逐行读取，每行输出一条 `OK:` / `ERR:`。命令为
`call <源文件> <函数> [实参...] [--sig ...] [--ret ...] [--macro]`、
`drop <源文件> [函数]`、`list`、`stats`、`quit`；空行或 `quit` 退出并释放
所有会话资源。同一单元重复调用命中进程内缓存，源码变化则按新单元重新编译。

`tshell` 可以把求值后端切到 JIT：`set eval-backend jit` 后用
`jit-call <源文件> <函数> [实参...] [--sig ...] [--ret ...]` 把标量函数交给
同一进程内的 JIT 会话。实参类型与返回类型都支持 `str`：字符串按运行时数据
指针传（两侧共用同一段内存，长度头在指针前 8 字节），返回时宿主按长度头重建
`string`，因此 JIT 函数可以直接收发 tie 字符串。表达式与整文件脚本仍由
`lib/interp` 求值（`Value` 的其它复合载荷尚差一层句柄重解释）。构建带 JIT 后端的 tsh
时设置 `LLVM_PREFIX`，`tools/tshell/build.tsh.tie` 会自动附加
`tiej_llvm.o`、运行时导出定义与 `-lLLVM-C`；不设置则构建为纯 interp 装配。
tiej 本身不依赖 tshell，两种入口都可独立运行。

`tiej` 用 `--sig i64,f64,bool --ret f64` 指定类型表与返回类型，省略时全部按
`i64`。参数类型支持 `i64` / `bool` / `f64` / `ptr`，返回类型另支持 `void`；`--macro`
允许编译期宏展开，默认显式拒绝。

## 其它工具

```bash
build/tiec.exe tools/tiep/main.tie -o build/tiep.exe
build/tiec.exe tools/tiel/src/shell.tie -o build/tiel.exe
build/tiec.exe tools/diag/crashdiag.tie -o build/crashdiag.exe
build/tiec.exe tools/release/notes.tie -o build/notes.exe
build/tiec.exe tools/ci/dep_check.tie -o build/dep_check.exe
build/tiec.exe tools/tshell/src/tsh_main.tie -o build/tsh.exe
```

脚本（tsc 角色）由解释器直接执行，无需编译：

```bash
build/tiep.exe script.tie [参数...]
build/tiel.exe script.tie
build/tiel.exe --check script.tie
```

`tiel` 也可作为库嵌入：源码级 `import "tools/tiel/src/tiel.tie"`，或用
`--shared --dll-export "tiel$check,tiel$free_result"` 产出动态库。

## 测试

回归脚本用 tshell 运行，需要 `tshell` 与已构建的 `tiec`（脚本内部走 `cmd`，限 Windows）：

```bash
tsh -f tools/tiec/scripts/regress-s21.tsh.tie ".\build\tiec.exe"
```

JIT 驱动回归覆盖标量、混合签名、表运行时、越界检查与编译期宏，逐项比对
输出与退出码，并确认产物不含自研垫片名：

```bash
python tools/tiej/regress.py build/tiej.exe --llvm-prefix "$LLVM_PREFIX"
```

依赖方向门禁（只允许内置库、`lib/` 与同一工具项目内的分片）：

```bash
build/dep_check.exe
```

## 许可

Tie Public License v2.3，见 `LICENSE`。协议模板见 `tpl.txt`。
