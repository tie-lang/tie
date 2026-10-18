# lib/rt —— tie 运行时

以库形式静态链接进单一二进制：调度、GC、channel、actor mailbox、并行池、生成器。

- 入口：`src/runtime/tl_runtime.tie`
- 构建：

```bash
tiec lib/rt/src/runtime/tl_runtime.tie -o lib/rt/trm_lite.a
```

编译器构建时用 `TIE_TRM_LITE_LIB=<仓根>/lib/rt/trm_lite.a` 链接。
