# tshell

**tie 语言命令行壳** / *The tie-language command-line shell*

tshell 是 tie 平台的**命令行壳**与**交互基础设施**，三身份一个引擎：独立命令行壳
（REPL + 脚本运行时 + 系统命令 + 值管道）、`tedit` 终端模组的命令引擎（根基）、
`trm` 的交互面（tieir 观测 / 调试 / 动态加载，p.9.3.5 骨架）。

*EN: tshell is the command-line shell & interactive infrastructure of the tie
platform — one engine, three roles: standalone shell (REPL + script runtime +
system commands + value pipelines), the command engine behind tedit's terminal
module, and the interactive workbench trm lacks (tieir observation / debugging /
dynamic loading).*

## 设计 / Design

- [tshell-architecture.md v0.2](https://github.com/tie-lang/tie-main/blob/main/docs/designs/tshell-architecture.md)
  （三身份 + 五层架构 + 双形态集成协议 + 模块系统与可嵌入，ROAD p.9.3）

## 构建 / Build

tshell 核心用 **tie 语言**编写，REPL 求值内核**复用 tiec 自举解释器**（`interp.eval`，
不造新求值器）。要求：

- 本机克隆 [tie-lang/tiec](https://github.com/tie-lang/tiec) 为 tshell 的**兄弟目录**
  （否则调整 `src/backend_interp.tie` 顶部 import 相对路径）；
- 用 tiec 的 stage0 编译器（`tiec/compiler/tiec.exe`）自举编译。

```powershell
# 一次构建两装配（standalone + tedit 终端模组子集）
# build.tsh.tie 是 tsh 角色自举构建驱动（tie/tsh 改写自 build.ps1）：
# 须用独立装配实例运行（构建会重写产物，不可用其自身实例）
_local_only\bin\tsh_main.exe -f build.tsh.tie
# 或直接用 tiec 编译装配入口（--no-cache 强制重编）
..\tiec\compiler\tiec.exe --no-cache src\tsh_main.tie
```

## 运行 / Run

```powershell
_local_only\bin\tsh_main.exe            # 交互 REPL
_local_only\bin\tsh_main.exe -e "1+2"   # 单行求值（输出 3）
_local_only\bin\tsh_main.exe -f x.tie   # 脚本文件（p.9.3.3 run，含 shebang）
_local_only\bin\tsh_main.exe --stdio    # tink 帧协议服务（p.9.3.4 srv）
```

REPL 解析优先级（架构 §4）：**tie 表达式 → 内建命令 → 外部命令 → 拼写纠错**
（did-you-mean）。值管道传 tie 值不传文本：`ls | filter { str_len(x) > 3 } | count`。

## 模块 / Modules（九模块，可嵌入）

| 模块 | 职责 |
| ---- | ---- |
| `lineedit` | tie 自研行编辑（p.9.3.2） |
| `complete` | 可插拔补全源（p.9.3.2） |
| `command` | 命令解析 / 内建命令 / 拼写纠错 |
| `pipeline` | 值管道 / 谓词管段 / 结构化格式 |
| `render` | 表 / 文本 / 流式渲染（输出流可注入） |
| `session` | 历史持久化 / 配置（td）/ 别名 |
| `repl` | 求值循环 / 多行续行 / 执行后端可注入 |
| `run` | 脚本运行时（argv/env/exit/shebang） |
| `observe` | tieir 观测 / 调试（经 trm 对象模型） |

独立 `tsh_main.exe` = 默认全量装配；嵌入者按 `src/*.tie` 取子集：
见 [docs/modules.md](docs/modules.md)（九模块清单/依赖方向/装配子集）与
[docs/embed.md](docs/embed.md)（三嵌入形态 + tedit 终端模组子集说明）；双形态协议
对接见 [docs/srv.md](docs/srv.md)。

## 内容 / Contents

- `src/` tshell 模块源码（tie 语言）；`src/tsh_main.tie` 装配器/入口，
  `src/tedit_embed.tie` 终端模组子集装配
- `build.tsh.tie` 构建驱动（tsh 角色）；`tests/` 冒烟/验收探针
  （probe_l2 / probe_zd / smoke_repl.tsh.tie / smoke_stdio.tsh.tie）
- `docs/` 模块清单、三嵌入形态、srv 协议对接

## License

本仓库按 **Tie Public License v2.0（TPL 2.0）** 授权发布（全文见 [LICENSE](LICENSE)）：
你可自由使用、修改并分发本软件源码，包括用于商业产品，仅需保留版权声明并附本许可证。

EN: This repository is released under the **Tie Public License v2.0 (TPL 2.0)**
(full text in [LICENSE](LICENSE)): you may freely use, modify, and redistribute
the source code, including in commercial products, provided you retain the
copyright notice and a copy of the license.