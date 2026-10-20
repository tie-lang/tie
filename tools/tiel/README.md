# tiel

效率 · 性能 · 安全 · 通用

tie 轻量解释器 —— 类 Lua 的可嵌入脚本运行时，只吃 **tsc**（tie 的可嵌入子集）。前端（词法 / 语法 / 错误码）与内核（字节码 VM）均已落地。

## 目录

* [三种嵌入形态](#三种嵌入形态)
* [命令行](#命令行)
* [文件](#文件)
* [当前子集](#当前子集)

## 三种嵌入形态

**1. tie 软件（源码级嵌入）**

```tie
import "<path>/tiel/src/tiel.tie"
var err = tiel_check(src)      // 只校验：返回 CLI 形态错误行（error[E#####] @行:列: 消息。）；通过为空串
var rc  = tiel_run(src)        // 编译为内核字节码并执行：返回进程退出码（0 = 正常结束）
var msg = tiel_err()           // 最近一次 tiel_run 的编译/运行错误（空 = 无）
```

或按包依赖声明（见 `tie.pkg`）。

**2. 宿主软件（动态库）**

```sh
tiec --shared --dll-export "tiel$check,tiel$free_result" src/embed.tie -o target/tiel.dll
```

```c
/* C 面：输入输出全部走整数地址（详见 embed.tie 头注释） */
long long outn = 0;
char* p = check((long long)src, srclen, (long long)&outn);
if (outn > 0) { fwrite(p, 1, outn, stdout); free_result((long long)p); }
```

**3. 命令行**

```sh
tiec src/shell.tie -o target/tiel.exe
./target/tiel.exe script.tie          # 执行脚本
./target/tiel.exe --check script.tie  # 只做前端校验
```

## 命令行

* `tiel <script.tie…>` —— 执行脚本；编译拒绝、运行错误与脚本返回非零都记失败。
* `tiel --check <script.tie…>` —— 只做前端校验，打印 CLI 形态错误行或「校验通过」。
* `tiel -v` —— 版本信息。

退出码：`0` 全部正常 / `1` 存在失败 / `2` 用法错误。

## 文件

* 表示与前端 —— `src/emit.tie`（表示层）· `lex.tie`（词法）· `parse.tie`（语法）· `emcodes.tie`（错误码表）· `render.tie`（CLI 形态拼装）
* 内核 —— `src/ops.tie`（指令表）· `code.tie`（语法树 → 字节码）· `vm.tie`（执行核）
* 入口 —— `src/tiel.tie`（包门面：`tiel_check` / `tiel_run` / `tiel_err`）· `embed.tie`（宿主嵌入面）· `shell.tie`（命令行壳）

## 当前子集

已执行：整数字面量、算术与比较、变量声明与赋值、`if`/`else`、`while`、`break`/`continue`、函数定义与调用、递归、`return`、`println`/`print`。

字符串字面量可解析并作为常量参与 `println`；表、闭包、模式匹配、管道等语法由前端接受，内核暂未生成对应字节码，编译期会明确拒绝而不是静默产出错误代码。
