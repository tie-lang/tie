type tie<data>
// compiler/data/locale/zh-CN.td —— 简体中文诊断消息包（扁平字符串表）
// 键形态：<码>.msg = 错误消息模板；<码>.help = --explain 说明。
// 占位符 <名字> 由 locale 层按调用点替换；缺项时回落内置文案。
[
    "E00554.msg": "类型 '<nm>' 未定义",
    "E00377.msg": "变量 '<nm>' 类型不匹配：标注 <ann>，表达式推导为 <got>",
    "E00406.help": "E00406 · 复合赋值要求两侧同型；先显式转换其中一侧。",
    "E00489.help": "E00489 · 该函数不在作用域内；检查拼写，或 import 定义它的模块。",
    "E00588.help": "E00588 · 调用实参类型与形参不符；把实参调整成形参类型。",
    "E00112.help": "E00112 · impl 方法参数个数与 port 签名不符——照 port 的参数列表写",
    "E00113.help": "E00113 · impl 方法参数类型与 port 签名不符——类型必须完全一致",
    "E00114.help": "E00114 · impl 方法缺 self 接收者——写成 `func name(self, ...)`",
    "E00118.help": "E00118 · impl 方法的第一参数必须命名为 self",
    "E00120.help": "E00120 · impl 方法返回类型与 port 签名不符——对齐返回类型",
    "E00210.help": "E00210 · impl 区块漏掉 port 要求的方法——port 方法必须全部实现",
    "E00456.help": "E00456 · 提升到 port/interface 对象需在 unsafe 块或函数内——对象借用具体值",
    "E00556.help": "E00556 · 类型实参未实现泛型约束要求的 port——补写 `impl P for T`",
    "E00557.help": "E00557 · 类型实参未实现泛型约束要求的 interface——在 impl 块补齐缺少的方法",
    "E00560.help": "E00560 · 具体类型不满足 interface，不能提升——实现缺少的方法或修正签名",
    "E00561.help": "E00561 · 具体类型没有该 port 的 impl，不能提升——先写 `impl P for T`",
]