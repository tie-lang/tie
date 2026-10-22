# tie

tie 语言核心：编译器、标准库、运行时与薄工具的单主体仓。

## 布局

| 目录            | 职责                             |
| ------------- | ------------------------------ |
| `std/`        | 标准库                            |
| `sys/`        | 平台库                            |
| `ext/`        | 扩展库                            |
| `rdu/`        | 嵌入式开发标准库                       |
| `lib/support` | 诊断 / 内部化 / 编码 / 文件 / 参数        |
| `lib/diag`    | 诊断聚合与报文渲染                      |
| `lib/ir`      | tieir 模型 + 类型描述 + 序列化 + 版本     |
| `lib/ast`     | 语法树契约（节点池 / 语义镜像 / tag 常量）     |
| `lib/sema`    | 语义状态（符号表 / 签名表 / 局部变量）        |
| `lib/front`   | 前端（源码 → tieir）                 |
| `lib/codegen` | 代码生成（AST → tieir）              |
| `lib/backend` | 后端（tieir → LLVM IR）            |
| `lib/rt`      | 运行时薄核（panic 域 / 全局注册 / 版本）     |
| `lib/jit`     | LLVM-C 垫片 + LLJIT 会话           |
| `tools/tiec`  | 编译器（`src/` 源码、`scripts/` 门禁脚本） |
| `tools/tiej`  | JIT 驱动（tieir → LLJIT）          |
| `tools/tiel`  | 轻量解释器（词法 / 语法 / 字节码内核）        |
| `tests/`      | 语言/工具探针与编译器回归用例                |

跨库引用写全名（`tie.ir::x`）；文件首部 `namespace <库名>;` 写在 import 之后。
`std/`、`sys/`、`ext/` 是 `/std/*` 等绝对导入的根，构建时令 `TIE_LIB_ROOT=<仓根>`。

## 构建

引导编译器（stage0）只需一次；之后所有工具都用仓内 `tiec` 构建：

```bash
export TIE_LIB_ROOT=$PWD

# 0. 引导：用 stage0 编译仓内编译器源码
<stage0>/tiec.exe tools/tiec/src/driver.tie -l2 -t0 --no-warn --no-cache \
      -o _local_only/bin/tiec.exe

# 1. 运行时（编译器链接用；须在 lib/rt 内构建）
(cd lib/rt && ../../_local_only/bin/tiec.exe src/trm_lite.run.tie -o trm_lite.a --no-warn)
export TIE_TRM_LITE_LIB=$PWD/lib/rt/trm_lite.a

# 2. LLVM-C 薄垫片（C ABI）
clang -shared -O2 lib/jit/tiej_llvm.c \
      -I D:/LLVM/include -L D:/LLVM/lib -lLLVM-C \
      -o _local_only/bin/tiej_llvm.dll

# 3. JIT 驱动
_local_only/bin/tiec.exe tools/tiej/main.tie -o _local_only/bin/tiej.exe --no-warn
_local_only/bin/tiej.exe

# 4. 语言层探针
_local_only/bin/tiec.exe tests/backend_probe.tie -o _local_only/bin/backend_probe.exe --no-warn
_local_only/bin/backend_probe.exe
```

## 当前能力

`lib/ir` + `lib/backend` + `lib/jit` + `tools/tiej`：
tieir（函数 / 参数 / add·sub·mul / ret）→ LLVM 文本 → LLJIT → 查符号 → 调用。

`tools/tiec` 是完整编译器源码；`std/` 是它的标准库根；`tests/` 保留编译器回归用例。

## 许可

Tie Public License v2.3（见 `LICENSE`；协议原文模板见 `tpl.txt`）。
