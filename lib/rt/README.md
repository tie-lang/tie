# lib/rt —— tie 运行时

以库形式静态链接进单一二进制：调度、GC、表、channel、同步、生成器。

- 聚合入口：`src/trm_lite.run.tie`
- 构建（须在 `lib/rt` 目录内，运行时分片的 `src/...` 导入按仓内根解析）：

```bash
cd lib/rt
../../_local_only/bin/tiec.exe src/trm_lite.run.tie -o trm_lite.a
```

编译器构建时用 `TIE_TRM_LITE_LIB=<仓根>/lib/rt/trm_lite.a` 链接。
