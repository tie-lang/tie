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
]
