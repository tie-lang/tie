# tiel

tie 轻量解释器（前端已落地：词法 / 语法 / 错误码；内核在途）。类 Lua 的可嵌入脚本前端，只吃 **tsc**。

## 三种嵌入形态

**1. tie 软件（源码级嵌入）**

```tie
import "<path>/tiel/src/tiel.tie"
var err = tiel_check(src)     // 返回 CLI 形态错误行（error[E#####] @行:列: 消息。）；通过为空串
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
./target/tiel.exe script.tie
```

## 文件

- `src/emit.tie` 表示层 · `lex.tie` 词法 · `parse.tie` 语法 · `emcodes.tie` 错误码表 · `render.tie` CLI 形态拼装
- `src/tiel.tie` 包门面（`tiel_check`）· `embed.tie` 宿主嵌入面 · `shell.tie` 命令行壳
- `tie.pkg` 包元数据（name / version / role / main）

## 构建

```sh
tiec src/shell.tie -o target/tiel.exe
tiec --shared --dll-export "tiel$check,tiel$free_result" src/embed.tie -o target/tiel.dll
```

## 许可证

TPL 2.3（见 LICENSE）。
