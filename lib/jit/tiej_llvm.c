// tiej_llvm.c —— tiej 的 LLVM-C 薄垫片（C ABI）
// ============================================================
// 定位：只做「参数收敛 + 错误归一 + 句柄包装」，不含任何策略。
//   - 导出面一律 ≤5 个标量/指针参数（宿主侧 dyn_call_p 的硬约束）；
//   - 句柄统一 int64_t（宿主不碰 LLVM 类型）；
//   - 错误统一为 tj_last_error()（线程局部，宿主复制后调 tj_err_clear）。
//
// 与 tie 侧的唯一契约（lib/jit/tjdecl.tie 镜像）：
//   tj_jit_open()                        -> jit 句柄（0 = 失败）
//   tj_jit_add_ir(jit, ir, len)          -> 0 成功 / 非 0 见 last_error
//   tj_jit_lookup(jit, name)             -> 函数地址（0 = 失败）
//   tj_jit_close(jit)                    -> void
//   tj_last_error()                      -> const char*
//   tj_err_clear()                       -> void
//   tj_abi_version()                     -> 整数（宿主启动时校验）
//   tj_f64_ir / tj_f64_bits / tj_f64_text -> 十进制文本与位模式互换
//
// 能力（ABI 4）：
//   - 会话挂**进程符号解析**：JIT 代码可直接调用宿主进程已链接的符号
//     （libc、trm_lite 运行时），不必手工登记每个外部函数；
//   - 调用编组交给 JIT 侧生成的包装函数（按 tie 签名逐参编组），
//     垫片不再受「≤5 个标量参数」限制；
//   - 每个编译单元持有独立 ResourceTracker：装载走
//     LLVMOrcLLJITAddLLVMIRModuleWithRT，卸载走 ResourceTrackerRemove，
//     替换一个单元不会波及其它单元，lookup 仍在 main JITDylib 上完成。
//
// 两种构建形态：
//   1. 静态链入宿主（tiej 默认）：定义 TJ_STATIC，TJ_EXPORT 为空，编成 .o
//      后与 LLVM-C 导入库一起链进 tiej 可执行产物。tie 侧用 unsafe extern fn
//      直接调用这些符号，运行期不再装载任何自研垫片 DLL。
//      clang -c -O2 -DTJ_STATIC -I <LLVM>/include lib/jit/tiej_llvm.c -o build/tiej_llvm.o
//   2. 独立动态库（备用，供独立探针使用）：不定义 TJ_STATIC。
//      clang -shared -O2 -fPIC lib/jit/tiej_llvm.c \
//            -I <LLVM>/include -L <LLVM>/lib -lLLVM-C -o build/tiej_llvm.dll
//
// LLVM 侧只链 LLVM-C 这一个导入库 / DLL；本机 LLVM 安装未提供静态组件库，
// 把整套 LLVM 静态链入产物不是这套构建支持的形态。
//
// 说明：本文件不 import 任何 tie 仓源码——tiej 与 tiec/tief 的唯一数据面是
// tieir；本垫片只依赖 LLVM-C 的公开头文件与导入库。

#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#include <llvm-c/Core.h>
#include <llvm-c/Error.h>
#include <llvm-c/IRReader.h>
#include <llvm-c/LLJIT.h>
#include <llvm-c/Orc.h>
#include <llvm-c/Support.h>
#include <llvm-c/Target.h>

// 静态链入宿主时不需要导出修饰：符号由 clang 链接期解析，若仍带
// __declspec(dllexport) 会把 tj_* 塞进可执行产物的导出表，属于无意义的外露。
#ifdef TJ_STATIC
#define TJ_EXPORT
#elif defined(_WIN32)
#define TJ_EXPORT __declspec(dllexport)
#else
#define TJ_EXPORT __attribute__((visibility("default")))
#endif

#define TJ_ABI_VERSION 4

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
    // 进程符号解析：让 JIT 代码直接引用宿主已链接的符号（libc / trm_lite）。
    // 解析失败不致命——纯自包含函数仍可运行，只是外部符号会在链接期报错。
    LLVMOrcDefinitionGeneratorRef gen = NULL;
    LLVMErrorRef ge = LLVMOrcCreateDynamicLibrarySearchGeneratorForProcess(
        &gen, 0, NULL, NULL);
    if (!ge && gen) {
        LLVMOrcJITDylibAddGenerator(LLVMOrcLLJITGetMainJITDylib(j->jit), gen);
    } else if (ge) {
        LLVMConsumeError(ge);
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
    LLVMOrcDisposeThreadSafeContext(tsc);
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

// f64 位模式 → 十进制文本（JIT 包装统一用 i64 槽返回，宿主再经文本入口还原
// 为浮点；%.17g 保证 IEEE754 往返无损）。返回线程局部缓冲，调用方复制后即失效。
// 十进制文本 → LLVM IR 的 double 字面量（%.17e，IR 可直接解析）。
TJ_EXPORT const char *tj_f64_ir(const char *text) {
    static _Thread_local char b[64];
    double d = strtod(text ? text : "0", NULL);
    snprintf(b, sizeof(b), "%.17e", d);
    return b;
}

// 十进制文本 → f64 位模式（宿主把命令行文本变成 JIT 参数槽）。
TJ_EXPORT int64_t tj_f64_bits(const char *text) {
    double d = strtod(text ? text : "0", NULL);
    int64_t b;
    memcpy(&b, &d, sizeof(b));
    return b;
}

TJ_EXPORT const char *tj_f64_text(int64_t bits) {
    static _Thread_local char b[64];
    double d;
    memcpy(&d, &bits, sizeof(d));
    snprintf(b, sizeof(b), "%.17g", d);
    return b;
}

// ---- 按单元 ResourceTracker（ABI 4）------------------------------------
// 一个 LLJIT 会话里可以装载多个编译单元：每个单元一个 RT，卸载/替换只影响
// 该 RT 追踪的模块。所有符号仍加在 main JITDylib，故 tj_rt_lookup 与
// tj_jit_lookup 的查找路径完全一致。

TJ_EXPORT int64_t tj_rt_create(int64_t jit) {
    TJJit *j = (TJJit *)(intptr_t)jit;
    if (!j || !j->jit) {
        tj_err_set("tiej_llvm: rt_create 参数非法");
        return 0;
    }
    LLVMOrcResourceTrackerRef rt =
        LLVMOrcJITDylibCreateResourceTracker(LLVMOrcLLJITGetMainJITDylib(j->jit));
    if (!rt) {
        tj_err_set("tiej_llvm: 创建 ResourceTracker 失败");
        return 0;
    }
    return (int64_t)(intptr_t)rt;
}

TJ_EXPORT int64_t tj_rt_add_ir(int64_t jit, int64_t rt, const char *ir, int64_t len) {
    TJJit *j = (TJJit *)(intptr_t)jit;
    LLVMOrcResourceTrackerRef r = (LLVMOrcResourceTrackerRef)(intptr_t)rt;
    if (!j || !j->jit || !r || !ir || len <= 0) {
        tj_err_set("tiej_llvm: rt_add_ir 参数非法");
        return 1;
    }
    LLVMMemoryBufferRef buf = LLVMCreateMemoryBufferWithMemoryRangeCopy(
        ir, (size_t)len, "tiej-unit");
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
    LLVMErrorRef e = LLVMOrcLLJITAddLLVMIRModuleWithRT(j->jit, r, tsm);
    LLVMOrcDisposeThreadSafeContext(tsc);
    if (e) {
        tj_err_llvm(e);
        return 4;
    }
    return 0;
}

TJ_EXPORT int64_t tj_rt_remove(int64_t rt) {
    LLVMOrcResourceTrackerRef r = (LLVMOrcResourceTrackerRef)(intptr_t)rt;
    if (!r) {
        tj_err_set("tiej_llvm: rt_remove 参数非法");
        return 1;
    }
    LLVMErrorRef e = LLVMOrcResourceTrackerRemove(r);
    LLVMOrcReleaseResourceTracker(r);
    if (e) {
        tj_err_llvm(e);
        return 2;
    }
    return 0;
}

TJ_EXPORT int64_t tj_rt_lookup(int64_t jit, const char *name) {
    return tj_jit_lookup(jit, name);
}

TJ_EXPORT void tj_jit_close(int64_t jit) {
    TJJit *j = (TJJit *)(intptr_t)jit;
    if (!j) return;
    if (j->jit) LLVMOrcDisposeLLJIT(j->jit);
    if (j->ctx) LLVMContextDispose(j->ctx);
    free(j);
}
