// tiej_llvm.c —— tiej 的 LLVM-C 薄垫片（C ABI）
// ============================================================
// 定位：只做「参数收敛 + 错误归一 + 句柄包装」，不含任何策略。
//   - 导出面一律 ≤5 个标量/指针参数（宿主侧 dyn_call_p 的硬约束）；
//   - 句柄统一 int64_t（宿主不碰 LLVM 类型）；
//   - 错误统一为 tj_last_error()（线程局部，宿主复制后调 tj_err_clear）。
//
// 与 tie 侧的唯一契约（tiej/src/jit/llvmc.tie 镜像）：
//   tj_jit_open()                        -> jit 句柄（0 = 失败）
//   tj_jit_add_ir(jit, ir, len)          -> 0 成功 / 非 0 见 last_error
//   tj_jit_lookup(jit, name)             -> 函数地址（0 = 失败）
//   tj_jit_close(jit)                    -> void
//   tj_last_error()                      -> const char*
//   tj_err_clear()                       -> void
//   tj_abi_version()                     -> 整数（宿主启动时校验）
//
// 构建（tiej 仓根；产物进 _local_only/bin，不进源码树）：
//   clang -shared -O2 src/platform/tiej_llvm.c \
//         -I D:/LLVM/include -L D:/LLVM/lib -lLLVM-C \
//         -o _local_only/bin/tiej_llvm.dll
//
// 说明：本文件不 import 任何 tie 仓源码——tiej 与 tiec/tief 的唯一数据面是
// tieir；本垫片只依赖 LLVM-C 的公开头文件与导入库。

#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#include <llvm-c/Core.h>
#include <llvm-c/Error.h>
#include <llvm-c/IRReader.h>
#include <llvm-c/LLJIT.h>
#include <llvm-c/Orc.h>
#include <llvm-c/Support.h>
#include <llvm-c/Target.h>

#ifdef _WIN32
#define TJ_EXPORT __declspec(dllexport)
#else
#define TJ_EXPORT __attribute__((visibility("default")))
#endif

#define TJ_ABI_VERSION 1

static _Thread_local char g_err[1024];

static void tj_err_set(const char *s) {
    if (!s) {
        g_err[0] = '\0';
        return;
    }
    size_t n = strlen(s);
    if (n >= sizeof(g_err)) n = sizeof(g_err) - 1;
    memcpy(g_err, s, n);
    g_err[n] = '\0';
}

static void tj_err_llvm(LLVMErrorRef e) {
    if (!e) {
        tj_err_set("");
        return;
    }
    char *msg = LLVMGetErrorMessage(e);
    tj_err_set(msg ? msg : "LLVM 未提供错误信息");
    if (msg) LLVMDisposeErrorMessage(msg);
}

typedef struct {
    LLVMContextRef ctx;
    LLVMOrcLLJITRef jit;
} TJJit;

TJ_EXPORT int64_t tj_abi_version(void) { return TJ_ABI_VERSION; }

TJ_EXPORT const char *tj_last_error(void) { return g_err; }

TJ_EXPORT void tj_err_clear(void) { g_err[0] = '\0'; }

TJ_EXPORT int64_t tj_jit_open(void) {
    // ORC 需要本机 target 已注册；重复调用是幂等的。
    LLVMInitializeNativeTarget();
    LLVMInitializeNativeAsmPrinter();

    TJJit *j = (TJJit *)calloc(1, sizeof(TJJit));
    if (!j) {
        tj_err_set("tiej_llvm: 分配会话失败");
        return 0;
    }
    j->ctx = LLVMContextCreate();

    LLVMOrcLLJITBuilderRef b = LLVMOrcCreateLLJITBuilder();
    if (!b) {
        tj_err_set("tiej_llvm: 创建 LLJIT builder 失败");
        LLVMContextDispose(j->ctx);
        free(j);
        return 0;
    }
    LLVMErrorRef e = LLVMOrcCreateLLJIT(&j->jit, b);
    if (e) {
        tj_err_llvm(e);
        LLVMContextDispose(j->ctx);
        free(j);
        return 0;
    }
    return (int64_t)(intptr_t)j;
}

TJ_EXPORT int64_t tj_jit_add_ir(int64_t jit, const char *ir, int64_t len) {
    TJJit *j = (TJJit *)(intptr_t)jit;
    if (!j || !j->jit || !ir || len <= 0) {
        tj_err_set("tiej_llvm: add_ir 参数非法");
        return 1;
    }
    // LLVM 22 的 *Copy 形态只有 3 参（内部按长度拷贝）。
    LLVMMemoryBufferRef buf = LLVMCreateMemoryBufferWithMemoryRangeCopy(ir, (size_t)len, "tiej-ir");
    if (!buf) {
        tj_err_set("tiej_llvm: 创建内存缓冲失败");
        return 2;
    }
    LLVMModuleRef m = NULL;
    char *msg = NULL;
    if (LLVMParseIRInContext(j->ctx, buf, &m, &msg)) {
        tj_err_set(msg ? msg : "tiej_llvm: LLVM IR 解析失败");
        if (msg) LLVMDisposeMessage(msg);
        return 3;
    }
    LLVMOrcThreadSafeContextRef tsc = LLVMOrcCreateNewThreadSafeContext();
    LLVMOrcThreadSafeModuleRef tsm = LLVMOrcCreateNewThreadSafeModule(m, tsc);
    LLVMErrorRef e = LLVMOrcLLJITAddLLVMIRModule(j->jit, LLVMOrcLLJITGetMainJITDylib(j->jit), tsm);
    if (e) {
        tj_err_llvm(e);
        return 4;
    }
    return 0;
}

TJ_EXPORT int64_t tj_jit_lookup(int64_t jit, const char *name) {
    TJJit *j = (TJJit *)(intptr_t)jit;
    if (!j || !j->jit || !name) {
        tj_err_set("tiej_llvm: lookup 参数非法");
        return 0;
    }
    LLVMOrcExecutorAddress addr = 0;
    LLVMErrorRef e = LLVMOrcLLJITLookup(j->jit, &addr, name);
    if (e) {
        tj_err_llvm(e);
        return 0;
    }
    return (int64_t)addr;
}

TJ_EXPORT void tj_jit_close(int64_t jit) {
    TJJit *j = (TJJit *)(intptr_t)jit;
    if (!j) return;
    if (j->jit) LLVMOrcDisposeLLJIT(j->jit);
    if (j->ctx) LLVMContextDispose(j->ctx);
    free(j);
}
