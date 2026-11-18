type tie<data>
// compiler/data/locale/en-US.td —— 英文诊断消息包（扁平字符串表）
// 键形态：<码>.msg = 错误消息模板；<码>.help = --explain 说明。
// 占位符 <名字> 由 locale 层按调用点替换；缺项时回落内置文案。
[
    "E00554.msg": "undefined type '<nm>'",
    "E00377.msg": "variable '<nm>' type mismatch: declared <ann>, expression is <got>",
    "E00406.help": "E00406 · compound assignment needs both sides to share a type; convert one side explicitly.",
    "E00489.help": "E00489 · the function is not declared in scope; check the spelling, or import the module that defines it.",
    "E00588.help": "E00588 · a call passes an argument of the wrong type; align the argument with the parameter type.",
    "E00112.help": "E00112 · impl method parameter count differs from the port signature — mirror the port's parameter list",
    "E00113.help": "E00113 · impl method parameter type differs from the port signature — make the types identical",
    "E00114.help": "E00114 · impl method has no self receiver — write `func name(self, ...)`",
    "E00118.help": "E00118 · the first parameter of an impl method must be named self",
    "E00120.help": "E00120 · impl method return type differs from the port signature — align the return types",
    "E00210.help": "E00210 · the impl block is missing a method the port requires — every port method must be implemented",
    "E00456.help": "E00456 · promoting a value to a port/interface object needs an unsafe block or function — the object borrows the concrete value",
    "E00556.help": "E00556 · the type argument does not implement the port the generic bound requires — add `impl P for T`",
    "E00557.help": "E00557 · the type argument does not implement the interface the generic bound requires — add the missing methods in an impl block",
    "E00560.help": "E00560 · the concrete type does not satisfy the interface, so it cannot be promoted — implement the missing method or fix its signature",
    "E00561.help": "E00561 · the concrete type has no impl for this port, so it cannot be promoted — write `impl P for T` first",
]