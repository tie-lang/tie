# tie

tie 语言核心：库 + 薄工具的单主体仓。

## 布局

| 目录 | 职责 |
| --- | --- |
| `lib/support` | 诊断 / 内部化 / 编码 / 文件 / 参数 |
| `lib/ir` | tieir 模型 + 类型描述 + 序列化 + 版本 |
| `lib/front` | 前端（源码 → tieir） |
| `lib/backend` | 后端（tieir → LLVM IR） |
| `lib/rt` | 运行时薄核（panic 域 / 全局注册 / 版本） |
| `lib/jit` | LLVM-C 垫片 + LLJIT 会话 |
| `tools/tiec` | 编译器驱动（前 → ir → 后 → 链接） |
| `tools/tiej` | JIT 驱动（ir → LLJIT） |
| `tools/tiep` | 解释器驱动 |
| `tools/tiel` | 轻量解释器驱动 |
| `tools/tief` | 前端工具 |

每个库只暴露 `pub` 面；文件首部用 `namespace <库名>;` 声明归属，导入写在它之前。
工具只做装配，不复制库逻辑。

## 当前能力

`lib/ir` + `lib/backend` + `lib/jit` + `tools/tiej`：

tieir（函数 / 参数 / add·sub·mul / ret）→ LLVM 文本 → LLJIT → 查符号 → 调用。
`tests/jit_probe`（手写 `.ll`）与 `tests/backend_probe`（模型 → 文本 → JIT）均全绿。

```bash
# 1. LLVM-C 薄垫片（C ABI）
clang -shared -O2 lib/jit/tiej_llvm.c \
      -I D:/LLVM/include -L D:/LLVM/lib -lLLVM-C \
      -o _local_only/bin/tiej_llvm.dll

# 2. JIT 驱动（tieir → backend → JIT 自检）
../tiec/compiler/tiec.exe tools/tiej/main.tie -o _local_only/bin/tiej.exe --no-warn
_local_only/bin/tiej.exe

# 3. 探针
../tiec/compiler/tiec.exe tests/backend_probe.tie -o _local_only/bin/backend_probe.exe --no-warn
_local_only/bin/backend_probe.exe
```

## 许可

Tie Public License v2.3（见 `LICENSE`）。
