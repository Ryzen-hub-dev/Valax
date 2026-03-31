from __future__ import annotations

import random
import string
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Iterable


LUA_KEYWORDS = {
    "and",
    "break",
    "continue",
    "do",
    "else",
    "elseif",
    "end",
    "export",
    "false",
    "for",
    "function",
    "goto",
    "if",
    "in",
    "local",
    "nil",
    "not",
    "or",
    "repeat",
    "return",
    "then",
    "true",
    "type",
    "until",
    "while",
}


LUAU_PROTECTED_GLOBALS = {
    "game",
    "workspace",
    "script",
    "plugin",
    "shared",
    "Enum",
    "Instance",
    "CFrame",
    "Vector2",
    "Vector3",
    "UDim",
    "UDim2",
    "Color3",
    "ColorSequence",
    "BrickColor",
    "RaycastParams",
    "TweenInfo",
    "task",
    "typeof",
}


class TokenType(Enum):
    IDENTIFIER = auto()
    KEYWORD = auto()
    NUMBER = auto()
    STRING = auto()
    SYMBOL = auto()
    COMMENT = auto()
    WHITESPACE = auto()


class BlockType(Enum):
    ROOT = auto()
    FUNCTION = auto()
    DO = auto()
    THEN = auto()
    ELSE = auto()
    REPEAT = auto()
    FOR = auto()


@dataclass
class Token:
    type: TokenType
    text: str
    bytes_value: bytes | None = None
    index: int = -1
    rewritten: str | None = None

    def is_keyword(self, value: str) -> bool:
        return self.type is TokenType.KEYWORD and self.text == value

    def is_symbol(self, value: str) -> bool:
        return self.type is TokenType.SYMBOL and self.text == value

    def rendered(self) -> str:
        return self.rewritten if self.rewritten is not None else self.text


@dataclass
class BlockFrame:
    type: BlockType
    has_scope: bool


@dataclass
class CodeBlock:
    """单个代码块表示"""
    block_id: int
    content: str
    block_type: str  # "statement", "function", "control_flow"
    next_id: int | None = None  # 默认下一步执行标识，None 表示程序结束
    branches: dict = None  # 分支结构: {"true": next_id, "false": next_id}
    auxiliary_paths: list = None  # 辅助路径列表，不影响主流程
    dependencies: list[int] = None
    metadata: dict = None

    def __post_init__(self):
        if self.branches is None:
            self.branches = {}
        if self.auxiliary_paths is None:
            self.auxiliary_paths = []
        if self.dependencies is None:
            self.dependencies = []
        if self.metadata is None:
            self.metadata = {}

    def set_next(self, next_block_id: int | None) -> None:
        """设置下一步执行标识"""
        self.next_id = next_block_id

    def set_branch(self, condition: str, next_block_id: int | None) -> None:
        """设置条件分支"""
        self.branches[condition] = next_block_id

    def add_auxiliary_path(self, path: dict) -> None:
        """添加辅助路径"""
        self.auxiliary_paths.append(path)

    def has_next(self) -> bool:
        """是否有下一步执行"""
        return self.next_id is not None

    def has_branches(self) -> bool:
        """是否有分支"""
        return len(self.branches) > 0

    def has_auxiliary_paths(self) -> bool:
        """是否有辅助路径"""
        return len(self.auxiliary_paths) > 0

    def get_successor_ids(self) -> list[int | None]:
        """获取所有后继块 ID"""
        successors = []
        if self.next_id is not None:
            successors.append(self.next_id)
        successors.extend(self.branches.values())
        return successors


@dataclass
class BlockProgram:
    """代码块程序的统一数据结构"""
    blocks: list[CodeBlock]
    execution_order: list[int]
    block_map: dict[int, CodeBlock]
    entry_block_id: int = 1
    constant_pool: ConstantPool | None = None
    randomized: bool = False
    use_auxiliary_paths: bool = False
    auxiliary_path_count: int = 0

    def __post_init__(self):
        self.block_map = {b.block_id: b for b in self.blocks}

    def get_block(self, block_id: int) -> CodeBlock | None:
        return self.block_map.get(block_id)

    def get_execution_sequence(self) -> list[CodeBlock]:
        return [self.block_map[bid] for bid in self.execution_order if bid in self.block_map]

    def link_blocks(self, order: list[int] | None = None) -> None:
        """将块按顺序链接，设置 next_id"""
        exec_order = order if order is not None else self.execution_order
        for i, bid in enumerate(exec_order):
            block = self.get_block(bid)
            if block is None:
                continue
            if i < len(exec_order) - 1:
                block.set_next(exec_order[i + 1])
            else:
                block.set_next(None)

    def randomize_and_link(self, rng: random.Random, respect_deps: bool = False) -> None:
        """随机化顺序并重新链接"""
        randomize_block_order(self, rng, respect_deps)
        self.randomized = True

    def randomize_layout(self, rng: random.Random, config: LayoutConfig | None = None) -> 'BlockProgram':
        """
        使用布局随机化随机化块顺序
        
        Args:
            rng: 随机数生成器
            config: 布局配置，如果为 None 则使用默认配置
            
        Returns:
            自身以便链式调用
        """
        randomizer = BlockLayoutRandomizer(rng, config)
        return randomizer.randomize(self)

    def analyze_layout(self) -> dict:
        """
        分析当前布局
        
        Returns:
            包含局部性和跳转开销分析的字典
        """
        locality = LayoutAnalyzer.analyze_locality(self)
        jump_cost = LayoutAnalyzer.compute_jump_cost(self)
        return {
            "locality": locality,
            "jump_cost": jump_cost,
            "block_count": len(self.execution_order)
        }

    def set_constant_pool(self, pool: ConstantPool) -> None:
        """设置常量池"""
        self.constant_pool = pool

    def get_constant_pool(self) -> ConstantPool | None:
        """获取常量池"""
        return self.constant_pool

    def enable_auxiliary_paths(self, enabled: bool = True) -> None:
        """启用/禁用辅助路径"""
        self.use_auxiliary_paths = enabled

    def increment_auxiliary_count(self) -> None:
        """增加辅助路径计数"""
        self.auxiliary_path_count += 1


# ===== 指令表示层 (Instruction Layer) =====


# ===== 指令定义注册表 =====


@dataclass
class OpCodeInfo:
    """
    指令操作码信息

    集中管理所有指令的定义信息。
    """
    opcode: 'OpCode'
    name: str
    category: str
    description: str
    has_result: bool = False
    has_args: bool = True


class OpCodeRegistry:
    """
    指令操作码注册表

    集中管理所有指令的定义，便于扩展和维护。
    """
    _registry: dict[str, OpCodeInfo] = {}

    @classmethod
    def register(cls, opcode: 'OpCode', name: str, category: str,
                 description: str, has_result: bool = False, has_args: bool = True) -> None:
        """注册指令信息"""
        cls._registry[opcode.value] = OpCodeInfo(
            opcode=opcode,
            name=name,
            category=category,
            description=description,
            has_result=has_result,
            has_args=has_args
        )

    @classmethod
    def get(cls, opcode_value: str) -> OpCodeInfo | None:
        """获取指令信息"""
        return cls._registry.get(opcode_value)

    @classmethod
    def get_by_category(cls, category: str) -> list[OpCodeInfo]:
        """获取指定类别的所有指令"""
        return [info for info in cls._registry.values() if info.category == category]

    @classmethod
    def get_all_categories(cls) -> list[str]:
        """获取所有指令类别"""
        return list(set(info.category for info in cls._registry.values()))

    @classmethod
    def get_all(cls) -> list[OpCodeInfo]:
        """获取所有注册的指令"""
        return list(cls._registry.values())


class OpCode(Enum):
    """
    指令操作码

    定义 Lua 代码的基本指令类型。
    """
    # ===== 变量和赋值 =====
    ASSIGN = "assign"              # 赋值: a = b
    DECLARE = "declare"            # 声明: local a
    INIT = "init"                  # 初始化: local a = b

    # ===== 函数调用 =====
    CALL = "call"                  # 函数调用: foo()
    CALL_ASSIGN = "call_assign"     # 调用赋值: a = foo()

    # ===== 返回和跳转 =====
    RETURN = "return"              # 返回: return
    RETURN_VAL = "return_val"      # 返回值: return x
    JUMP = "jump"                  # 跳转: goto label
    JUMP_IF = "jump_if"            # 条件跳转: if cond then

    # ===== 控制流 =====
    DO = "do"                      # 代码块开始: do ... end
    END = "end"                    # 代码块结束
    IF = "if"                      # 条件: if cond then
    THEN = "then"                  # then 分支
    ELSE = "else"                  # else 分支
    ELSEIF = "elseif"              # elseif 分支
    FOR = "for"                    # for 循环
    WHILE = "while"                # while 循环
    REPEAT = "repeat"              # repeat 循环
    UNTIL = "until"                # until 条件
    BREAK = "break"                # break 语句
    CONTINUE = "continue"         # continue 语句

    # ===== 表操作 =====
    TABLE_NEW = "table_new"        # 创建表: {}
    TABLE_SET = "table_set"       # 设置表元素: t.k = v
    TABLE_GET = "table_get"        # 获取表元素: t.k

    # ===== 函数定义 =====
    FUNC_DEF = "func_def"          # 函数定义: function foo() end
    FUNC_END = "func_end"          # 函数结束

    # ===== 表达式 =====
    EXPR = "expr"                  # 表达式语句: foo + bar
    NOP = "nop"                    # 空操作

    # ===== 特殊 =====
    COMMENT = "comment"            # 注释
    LABEL = "label"                # 标签
    ERROR = "error"                # error 语句
    ASSERT = "assert"              # assert 语句

    # ===== 辅助指令（用于代码生成增强）=====
    IDENTITY = "identity"          # 恒等变换: x = x
    DUMMY = "dummy"                # 哑操作: 不影响结果的操作


# 注册所有指令信息
def _register_opcodes() -> None:
    """注册所有指令信息到注册表"""
    # 变量和赋值
    OpCodeRegistry.register(OpCode.ASSIGN, "assign", "assignment",
                            "赋值: target = value", has_result=True, has_args=True)
    OpCodeRegistry.register(OpCode.DECLARE, "declare", "assignment",
                            "声明: local var", has_result=False, has_args=True)
    OpCodeRegistry.register(OpCode.INIT, "init", "assignment",
                            "初始化: local var = value", has_result=True, has_args=True)

    # 函数调用
    OpCodeRegistry.register(OpCode.CALL, "call", "call",
                            "函数调用: func(args)", has_result=False, has_args=True)
    OpCodeRegistry.register(OpCode.CALL_ASSIGN, "call_assign", "call",
                            "调用赋值: result = func(args)", has_result=True, has_args=True)

    # 返回和跳转
    OpCodeRegistry.register(OpCode.RETURN, "return", "control_flow",
                            "返回: return", has_result=False, has_args=False)
    OpCodeRegistry.register(OpCode.RETURN_VAL, "return_val", "control_flow",
                            "返回值: return expr", has_result=False, has_args=True)
    OpCodeRegistry.register(OpCode.JUMP, "jump", "control_flow",
                            "跳转", has_result=False, has_args=True)
    OpCodeRegistry.register(OpCode.JUMP_IF, "jump_if", "control_flow",
                            "条件跳转", has_result=False, has_args=True)

    # 控制流
    OpCodeRegistry.register(OpCode.DO, "do", "control_flow",
                            "do...end 块开始", has_result=False, has_args=False)
    OpCodeRegistry.register(OpCode.END, "end", "control_flow",
                            "块结束", has_result=False, has_args=False)
    OpCodeRegistry.register(OpCode.IF, "if", "control_flow",
                            "if 条件", has_result=False, has_args=True)
    OpCodeRegistry.register(OpCode.THEN, "then", "control_flow",
                            "then 分支", has_result=False, has_args=False)
    OpCodeRegistry.register(OpCode.ELSE, "else", "control_flow",
                            "else 分支", has_result=False, has_args=False)
    OpCodeRegistry.register(OpCode.ELSEIF, "elseif", "control_flow",
                            "elseif 分支", has_result=False, has_args=True)
    OpCodeRegistry.register(OpCode.FOR, "for", "control_flow",
                            "for 循环", has_result=False, has_args=True)
    OpCodeRegistry.register(OpCode.WHILE, "while", "control_flow",
                            "while 循环", has_result=False, has_args=True)
    OpCodeRegistry.register(OpCode.REPEAT, "repeat", "control_flow",
                            "repeat 循环开始", has_result=False, has_args=False)
    OpCodeRegistry.register(OpCode.UNTIL, "until", "control_flow",
                            "until 条件", has_result=False, has_args=True)
    OpCodeRegistry.register(OpCode.BREAK, "break", "control_flow",
                            "break 语句", has_result=False, has_args=False)
    OpCodeRegistry.register(OpCode.CONTINUE, "continue", "control_flow",
                            "continue 语句", has_result=False, has_args=False)

    # 表操作
    OpCodeRegistry.register(OpCode.TABLE_NEW, "table_new", "table",
                            "创建表", has_result=True, has_args=False)
    OpCodeRegistry.register(OpCode.TABLE_SET, "table_set", "table",
                            "设置表元素", has_result=False, has_args=True)
    OpCodeRegistry.register(OpCode.TABLE_GET, "table_get", "table",
                            "获取表元素", has_result=True, has_args=True)

    # 函数定义
    OpCodeRegistry.register(OpCode.FUNC_DEF, "func_def", "function",
                            "函数定义", has_result=False, has_args=True)
    OpCodeRegistry.register(OpCode.FUNC_END, "func_end", "function",
                            "函数结束", has_result=False, has_args=False)

    # 表达式
    OpCodeRegistry.register(OpCode.EXPR, "expr", "expression",
                            "表达式语句", has_result=False, has_args=True)
    OpCodeRegistry.register(OpCode.NOP, "nop", "expression",
                            "空操作", has_result=False, has_args=False)

    # 特殊
    OpCodeRegistry.register(OpCode.COMMENT, "comment", "special",
                            "注释", has_result=False, has_args=True)
    OpCodeRegistry.register(OpCode.LABEL, "label", "special",
                            "标签", has_result=False, has_args=True)
    OpCodeRegistry.register(OpCode.ERROR, "error", "special",
                            "error 语句", has_result=False, has_args=True)
    OpCodeRegistry.register(OpCode.ASSERT, "assert", "special",
                            "assert 语句", has_result=False, has_args=True)

    # 辅助指令
    OpCodeRegistry.register(OpCode.IDENTITY, "identity", "auxiliary",
                            "恒等变换", has_result=True, has_args=True)
    OpCodeRegistry.register(OpCode.DUMMY, "dummy", "auxiliary",
                            "哑操作", has_result=False, has_args=False)


_register_opcodes()


@dataclass
class Instruction:
    """
    单条指令表示

    所有指令都使用统一的结构:
    - op: 操作码
    - args: 参数列表
    - result: 结果（如果有）
    - metadata: 元数据（行号、注释等）
    """
    op: OpCode
    args: list[Any] = None
    result: str | None = None
    metadata: dict | None = None

    def __post_init__(self):
        if self.args is None:
            self.args = []
        if self.metadata is None:
            self.metadata = {}

    @property
    def info(self) -> OpCodeInfo | None:
        """获取指令信息"""
        return OpCodeRegistry.get(self.op.value)

    def __repr__(self) -> str:
        args_str = ", ".join(str(a) for a in self.args)
        result_str = f" -> {self.result}" if self.result else ""
        return f"[{self.op.value} {args_str}{result_str}]"

    def to_dict(self) -> dict:
        """转换为字典表示"""
        return {
            "op": self.op.value,
            "args": self.args,
            "result": self.result,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Instruction:
        """从字典创建指令"""
        return cls(
            op=OpCode(d["op"]),
            args=d.get("args", []),
            result=d.get("result"),
            metadata=d.get("metadata", {}),
        )


@dataclass
class BlockInstructions:
    """
    Block 的指令列表表示

    将 CodeBlock 转换为指令列表，便于后续处理。
    """
    block_id: int
    instructions: list[Instruction] = None
    block_type: str = "statement"

    def __post_init__(self):
        if self.instructions is None:
            self.instructions = []

    def add(self, instr: Instruction) -> None:
        """添加指令"""
        self.instructions.append(instr)

    def add_nop(self) -> None:
        """添加空操作"""
        self.instructions.append(Instruction(OpCode.NOP))

    def add_comment(self, comment: str) -> None:
        """添加注释指令"""
        self.instructions.append(Instruction(OpCode.COMMENT, [comment]))

    def to_list(self) -> list[dict]:
        """转换为列表表示"""
        return [instr.to_dict() for instr in self.instructions]

    def __len__(self) -> int:
        return len(self.instructions)

    def __iter__(self):
        return iter(self.instructions)


class InstructionConverter:
    """
    Block 转指令转换器

    将 CodeBlock.content 解析为指令列表。
    """

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng
        self._line_counter = 0

    def convert_block(self, block: CodeBlock) -> BlockInstructions:
        """将 CodeBlock 转换为指令列表"""
        result = BlockInstructions(
            block_id=block.block_id,
            block_type=block.block_type,
        )

        if not block.content:
            result.add_nop()
            return result

        lines = block.content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            self._line_counter += 1
            instrs = self._parse_line(line)
            for instr in instrs:
                instr.metadata["line"] = self._line_counter
                result.add(instr)

        if len(result.instructions) == 0:
            result.add_nop()

        return result

    def _parse_line(self, line: str) -> list[Instruction]:
        """解析单行代码为指令列表"""
        # 移除注释
        code_part = line
        comment = None
        if "--" in line:
            parts = line.split("--", 1)
            code_part = parts[0].strip()
            comment = parts[1].strip() if len(parts) > 1 else None

        if not code_part:
            if comment:
                return [Instruction(OpCode.COMMENT, [comment])]
            return [Instruction(OpCode.NOP)]

        # 解析不同语句类型
        if code_part.startswith("local "):
            return self._parse_local(code_part, comment)
        elif code_part.startswith("function "):
            return self._parse_function(code_part)
        elif code_part.startswith("if "):
            return self._parse_if(code_part)
        elif code_part.startswith("while "):
            return self._parse_while(code_part)
        elif code_part.startswith("for "):
            return self._parse_for(code_part)
        elif code_part.startswith("repeat"):
            return self._parse_repeat(code_part)
        elif code_part.startswith("return"):
            return self._parse_return(code_part)
        elif code_part.startswith("do"):
            return self._parse_do(code_part)
        elif code_part.startswith("end"):
            return [Instruction(OpCode.END)]
        elif code_part.startswith("then"):
            return [Instruction(OpCode.THEN)]
        elif code_part.startswith("else"):
            return [Instruction(OpCode.ELSE)]
        elif code_part.startswith("until"):
            return self._parse_until(code_part)
        elif "(" in code_part or code_part.endswith(")"):
            return self._parse_call_or_expr(code_part)
        elif "=" in code_part:
            return self._parse_assignment(code_part)
        elif code_part in ("break", "continue"):
            return [Instruction(OpCode.JUMP, [code_part])]
        elif code_part.startswith("error"):
            return self._parse_error(code_part)
        else:
            return [Instruction(OpCode.EXPR, [code_part])]

    def _parse_local(self, line: str, comment: str | None = None) -> list[Instruction]:
        """解析 local 声明/初始化"""
        # local a = b, c = d 形式
        if "=" in line:
            # 提取变量名
            rest = line[6:].strip()  # 移除 "local "
            parts = rest.split("=")

            instrs = []
            # 处理多个变量
            for i, part in enumerate(parts):
                if i == 0:
                    # 第一个变量可能包含逗号
                    vars_list = [v.strip() for v in part.split(",")]
                    for v in vars_list:
                        if v:
                            instrs.append(Instruction(OpCode.DECLARE, [v]))
                else:
                    # 其余是赋值的值
                    val = part.strip()
                    # 去掉可能的下一个变量名
                    if "," in val:
                        val_parts = val.split(",")
                        val = val_parts[0].strip()
                    if val:
                        instrs.append(Instruction(OpCode.ASSIGN, [f"${i}"], val))

            return instrs
        else:
            # 纯声明
            var = line[6:].strip()
            return [Instruction(OpCode.DECLARE, [var])]

    def _parse_assignment(self, line: str) -> list[Instruction]:
        """解析赋值语句"""
        parts = line.split("=", 1)
        if len(parts) != 2:
            return [Instruction(OpCode.EXPR, [line])]

        target = parts[0].strip()
        value = parts[1].strip()

        # 函数调用赋值
        if "(" in value and value.endswith(")"):
            return [Instruction(OpCode.CALL_ASSIGN, [value], target)]

        return [Instruction(OpCode.ASSIGN, [target], value)]

    def _parse_call_or_expr(self, line: str) -> list[Instruction]:
        """解析函数调用或表达式"""
        # 可能是函数调用或表达式
        if line.startswith("(") and line.endswith(")"):
            return [Instruction(OpCode.EXPR, [line])]

        # 函数调用
        if "(" in line:
            # 提取函数名
            func_start = line.find("(")
            func_name = line[:func_start].strip()

            # 提取参数
            args_str = line[func_start+1:-1].strip()
            args = [a.strip() for a in args_str.split(",")] if args_str else []

            return [Instruction(OpCode.CALL, [func_name] + args)]

        return [Instruction(OpCode.EXPR, [line])]

    def _parse_if(self, line: str) -> list[Instruction]:
        """解析 if 语句"""
        # if cond then
        if " then" in line:
            cond = line[3:line.find(" then")].strip()
            return [Instruction(OpCode.IF, [cond])]
        return [Instruction(OpCode.IF, [line])]

    def _parse_while(self, line: str) -> list[Instruction]:
        """解析 while 语句"""
        # while cond do
        if " do" in line:
            cond = line[6:line.find(" do")].strip()
            return [Instruction(OpCode.WHILE, [cond])]
        return [Instruction(OpCode.WHILE, [line])]

    def _parse_for(self, line: str) -> list[Instruction]:
        """解析 for 循环"""
        return [Instruction(OpCode.FOR, [line])]

    def _parse_repeat(self, line: str) -> list[Instruction]:
        """解析 repeat 语句"""
        return [Instruction(OpCode.REPEAT)]

    def _parse_until(self, line: str) -> list[Instruction]:
        """解析 until 语句"""
        cond = line[6:].strip() if line.startswith("until") else line
        return [Instruction(OpCode.UNTIL, [cond])]

    def _parse_return(self, line: str) -> list[Instruction]:
        """解析 return 语句"""
        if len(line) <= 6:
            return [Instruction(OpCode.RETURN)]

        value = line[6:].strip()  # 移除 "return "
        return [Instruction(OpCode.RETURN_VAL, [value])]

    def _parse_do(self, line: str) -> list[Instruction]:
        """解析 do 语句"""
        return [Instruction(OpCode.DO)]

    def _parse_function(self, line: str) -> list[Instruction]:
        """解析函数定义"""
        # function name(args) 或 local function name(args)
        content = line
        if line.startswith("local "):
            content = line[6:]

        if "(" in content and ")" in content:
            name_start = 9 if content.startswith("function ") else 0
            name_end = content.find("(")
            name = content[name_start:name_end].strip()

            args_start = name_end + 1
            args_end = content.find(")")
            args = content[args_start:args_end].strip()
            args_list = [a.strip() for a in args.split(",")] if args else []

            return [
                Instruction(OpCode.FUNC_DEF, [name] + args_list)
            ]

        return [Instruction(OpCode.FUNC_DEF, [line])]

    def _parse_error(self, line: str) -> list[Instruction]:
        """解析 error 语句"""
        # error('message') 或 error('message', level)
        if "(" in line and ")" in line:
            msg_start = line.find("(") + 1
            msg_end = line.find(")", msg_start)
            msg = line[msg_start:msg_end].strip().strip("'\"")
            return [Instruction(OpCode.ERROR, [msg])]

        return [Instruction(OpCode.ERROR, [line])]


class InstructionGenerator:
    """
    指令生成器

    将指令列表转换回 Lua 代码。
    支持不同的生成风格。
    """

    def __init__(self, obfuscate_names: bool = False):
        self.obfuscate_names = obfuscate_names

    def generate_block(self, block_instr: BlockInstructions) -> str:
        """将 BlockInstructions 转换回代码"""
        lines = []
        for instr in block_instr.instructions:
            code = self._generate_instruction(instr)
            if code:
                lines.append(code)
        return "\n".join(lines)

    def _generate_instruction(self, instr: Instruction) -> str:
        """生成单条指令的代码"""
        op = instr.op
        args = instr.args

        if op == OpCode.NOP:
            return "do end"

        elif op == OpCode.COMMENT:
            return f"-- {args[0] if args else ''}"

        elif op == OpCode.DECLARE:
            return f"local {args[0] if args else '_'}"

        elif op == OpCode.INIT:
            return f"local {args[0] if args else '_'} = {instr.result or ''}"

        elif op == OpCode.ASSIGN:
            target = args[0] if args else '_'
            return f"{target} = {instr.result or ''}"

        elif op == OpCode.CALL:
            func = args[0] if args else ''
            params = ", ".join(str(a) for a in args[1:]) if len(args) > 1 else ''
            return f"{func}({params})"

        elif op == OpCode.CALL_ASSIGN:
            return f"{instr.result or '_'} = {args[0] if args else ''}"

        elif op == OpCode.RETURN:
            return "return"

        elif op == OpCode.RETURN_VAL:
            return f"return {args[0] if args else ''}"

        elif op == OpCode.JUMP:
            return args[0] if args else "break"

        elif op == OpCode.IF:
            return f"if {args[0] if args else 'true'} then"

        elif op == OpCode.THEN:
            return "then"

        elif op == OpCode.ELSE:
            return "else"

        elif op == OpCode.WHILE:
            return f"while {args[0] if args else 'true'} do"

        elif op == OpCode.FOR:
            return args[0] if args else ""

        elif op == OpCode.REPEAT:
            return "repeat"

        elif op == OpCode.UNTIL:
            return f"until {args[0] if args else 'false'}"

        elif op == OpCode.DO:
            return "do"

        elif op == OpCode.END:
            return "end"

        elif op == OpCode.FUNC_DEF:
            name = args[0] if args else 'fn'
            params = ", ".join(str(a) for a in args[1:]) if len(args) > 1 else ''
            return f"function {name}({params})"

        elif op == OpCode.FUNC_END:
            return "end"

        elif op == OpCode.EXPR:
            return args[0] if args else ""

        elif op == OpCode.ERROR:
            msg = args[0] if args else ''
            return f"error('{msg}')"

        else:
            return f"-- {op.value} {' '.join(str(a) for a in args)}"


class InstructionLayer:
    """
    指令表示层

    整合指令转换和生成功能，作为 CodeBlock 和最终代码之间的中间层。
    """

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng
        self.converter = InstructionConverter(rng)
        self.generator = InstructionGenerator()
        self._block_instructions: dict[int, BlockInstructions] = {}

    def process_blocks(self, blocks: list[CodeBlock]) -> dict[int, BlockInstructions]:
        """处理所有 blocks，转换为指令表示"""
        self._block_instructions = {}
        for block in blocks:
            instr = self.converter.convert_block(block)
            self._block_instructions[block.block_id] = instr
        return self._block_instructions

    def get_instructions(self, block_id: int) -> BlockInstructions | None:
        """获取指定 block 的指令"""
        return self._block_instructions.get(block_id)

    def get_all_instructions(self) -> list[BlockInstructions]:
        """获取所有 block 的指令"""
        return list(self._block_instructions.values())

    def regenerate_block(self, block_id: int) -> str:
        """从指令重新生成 block 代码"""
        instr = self._block_instructions.get(block_id)
        if instr is None:
            return ""
        return self.generator.generate_block(instr)

    def regenerate_all_blocks(self, blocks: list[CodeBlock]) -> list[CodeBlock]:
        """重新生成所有 blocks"""
        result = []
        for block in blocks:
            new_content = self.regenerate_block(block.block_id)
            new_block = CodeBlock(
                block_id=block.block_id,
                content=new_content,
                block_type=block.block_type,
                next_id=block.next_id,
                branches=block.branches.copy() if block.branches else {},
                auxiliary_paths=block.auxiliary_paths.copy() if block.auxiliary_paths else [],
                dependencies=block.dependencies.copy() if block.dependencies else [],
                metadata=block.metadata.copy() if block.metadata else {},
            )
            result.append(new_block)
        return result

    def get_statistics(self) -> dict:
        """获取指令统计"""
        total_instrs = sum(len(bi) for bi in self._block_instructions.values())
        op_counts: dict[str, int] = {}

        for bi in self._block_instructions.values():
            for instr in bi.instructions:
                op_name = instr.op.value
                op_counts[op_name] = op_counts.get(op_name, 0) + 1

        return {
            "total_blocks": len(self._block_instructions),
            "total_instructions": total_instrs,
            "op_distribution": op_counts,
        }


def convert_blocks_to_instructions(
    blocks: list[CodeBlock],
    rng: random.Random | None = None,
) -> tuple[dict[int, BlockInstructions], InstructionLayer]:
    """
    将 CodeBlock 列表转换为指令表示

    Args:
        blocks: 代码块列表
        rng: 随机数生成器

    Returns:
        (block_id -> BlockInstructions 映射, InstructionLayer 实例)
    """
    layer = InstructionLayer(rng)
    instructions = layer.process_blocks(blocks)
    return instructions, layer


# ===== 指令执行器 (Instruction Executor) =====


@dataclass
class ExecutionContext:
    """
    指令执行上下文

    保存执行过程中的状态信息。
    """
    # 全局环境（模拟 Lua 全局表）
    globals: dict[str, Any]

    # 局部变量栈（当前作用域的变量）
    locals: dict[str, Any]

    # 调用栈
    call_stack: list[dict]

    # 返回值队列
    return_values: list[Any]

    # 当前执行状态
    running: bool
    error: str | None

    # 程序计数器
    pc: int

    def __post_init__(self):
        if self.globals is None:
            self.globals = {}
        if self.locals is None:
            self.locals = {}
        if self.call_stack is None:
            self.call_stack = []
        if self.return_values is None:
            self.return_values = []
        if self.running is None:
            self.running = True
        if self.error is None:
            self.error = None
        if self.pc is None:
            self.pc = 0

    def push_call(self, func_name: str, locals: dict) -> None:
        """压入调用栈"""
        self.call_stack.append({
            "name": func_name,
            "locals": locals,
            "pc": self.pc
        })

    def pop_call(self) -> dict | None:
        """弹出调用栈"""
        if self.call_stack:
            return self.call_stack.pop()
        return None

    def get_current_locals(self) -> dict:
        """获取当前局部变量（合并调用栈）"""
        result = {}
        for frame in reversed(self.call_stack):
            result.update(frame.get("locals", {}))
        result.update(self.locals)
        return result

    def set_local(self, name: str, value: Any) -> None:
        """设置局部变量"""
        self.locals[name] = value

    def get_local(self, name: str) -> Any:
        """获取局部变量"""
        return self.locals.get(name)

    def set_global(self, name: str, value: Any) -> None:
        """设置全局变量"""
        self.globals[name] = value

    def get_global(self, name: str) -> Any:
        """获取全局变量"""
        return self.globals.get(name)

    def resolve_value(self, name: str) -> Any:
        """解析变量值（先局部后全局）"""
        if name in self.locals:
            return self.locals[name]
        return self.globals.get(name)

    def set_value(self, name: str, value: Any) -> None:
        """设置变量值"""
        if name in self.locals:
            self.locals[name] = value
        else:
            self.globals[name] = value


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    return_value: Any = None
    error: str | None = None
    executed_instructions: int = 0
    final_context: ExecutionContext | None = None


class InstructionExecutor:
    """
    指令执行器

    使用字典分发方式执行指令序列，验证代码逻辑。
    """

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.context: ExecutionContext | None = None

        # 指令处理器映射（字典分发）
        self._handlers: dict[OpCode, callable] = {
            OpCode.NOP: self._handle_nop,
            OpCode.DECLARE: self._handle_declare,
            OpCode.INIT: self._handle_init,
            OpCode.ASSIGN: self._handle_assign,
            OpCode.CALL: self._handle_call,
            OpCode.CALL_ASSIGN: self._handle_call_assign,
            OpCode.RETURN: self._handle_return,
            OpCode.RETURN_VAL: self._handle_return_val,
            OpCode.JUMP: self._handle_jump,
            OpCode.JUMP_IF: self._handle_jump_if,
            OpCode.DO: self._handle_do,
            OpCode.END: self._handle_end,
            OpCode.IF: self._handle_if,
            OpCode.THEN: self._handle_then,
            OpCode.ELSE: self._handle_else,
            OpCode.ELSEIF: self._handle_elseif,
            OpCode.WHILE: self._handle_while,
            OpCode.FOR: self._handle_for,
            OpCode.REPEAT: self._handle_repeat,
            OpCode.UNTIL: self._handle_until,
            OpCode.FUNC_DEF: self._handle_func_def,
            OpCode.FUNC_END: self._handle_func_end,
            OpCode.EXPR: self._handle_expr,
            OpCode.ERROR: self._handle_error,
            OpCode.TABLE_NEW: self._handle_table_new,
            OpCode.TABLE_SET: self._handle_table_set,
        }

    def execute(
        self,
        instructions: list[Instruction],
        globals: dict[str, Any] | None = None,
        initial_locals: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """
        执行指令序列

        Args:
            instructions: 指令列表
            globals: 全局环境
            initial_locals: 初始局部变量

        Returns:
            ExecutionResult
        """
        # 初始化上下文
        self.context = ExecutionContext(
            globals=globals or {},
            locals=initial_locals or {},
            call_stack=[],
            return_values=[],
            running=True,
            error=None,
            pc=0
        )

        executed = 0
        pc = 0

        # 主循环
        while pc < len(instructions) and self.context.running:
            instr = instructions[pc]

            if self.debug:
                print(f"  PC={pc}: {instr}")

            # 获取处理器
            handler = self._handlers.get(instr.op)

            if handler:
                result = handler(instr)
                if isinstance(result, dict):
                    # 控制流指令可能返回新的 PC
                    new_pc = result.get("pc")
                    if new_pc is not None:
                        pc = new_pc
                    else:
                        pc += 1

                    # 检查是否需要返回
                    if result.get("return"):
                        break
                else:
                    pc += 1
            else:
                if self.debug:
                    print(f"    Unsupported opcode: {instr.op}")
                pc += 1

            executed += 1

            # 防止无限循环
            if executed > 10000:
                self.context.error = "Execution limit exceeded"
                break

        # 收集返回值
        return_value = None
        if self.context.return_values:
            return_value = self.context.return_values[0]

        return ExecutionResult(
            success=self.context.error is None,
            return_value=return_value,
            error=self.context.error,
            executed_instructions=executed,
            final_context=self.context
        )

    def _handle_nop(self, instr: Instruction) -> dict:
        """处理空操作"""
        return {}

    def _handle_declare(self, instr: Instruction) -> dict:
        """处理变量声明"""
        if len(instr.args) > 0:
            var_name = instr.args[0]
            self.context.set_local(var_name, None)
        return {}

    def _handle_init(self, instr: Instruction) -> dict:
        """处理变量初始化"""
        if len(instr.args) > 0:
            var_name = instr.args[0]
            value = self._eval_expr(instr.result)
            self.context.set_local(var_name, value)
        return {}

    def _handle_assign(self, instr: Instruction) -> dict:
        """处理赋值"""
        if len(instr.args) > 0:
            var_name = instr.args[0]
            value = self._eval_expr(instr.result)
            self.context.set_value(var_name, value)
        return {}

    def _handle_call(self, instr: Instruction) -> dict:
        """处理函数调用"""
        if len(instr.args) > 0:
            func_name = instr.args[0]
            args = [self._eval_expr(a) for a in instr.args[1:]]

            # 查找函数
            func = self.context.resolve_value(func_name)

            if callable(func):
                try:
                    result = func(*args)
                    if self.context.return_values:
                        self.context.return_values.append(result)
                except Exception as e:
                    self.context.error = str(e)
            elif func is not None:
                self.context.error = f"'{func_name}' is not callable"
        return {}

    def _handle_call_assign(self, instr: Instruction) -> dict:
        """处理调用赋值"""
        if instr.args and instr.result:
            # 解析调用表达式
            call_expr = instr.args[0]
            result = self._eval_expr(call_expr)
            self.context.set_local(instr.result, result)
        return {}

    def _handle_return(self, instr: Instruction) -> dict:
        """处理 return"""
        self.context.return_values.append(None)
        return {"return": True}

    def _handle_return_val(self, instr: Instruction) -> dict:
        """处理返回值"""
        if instr.args:
            value = self._eval_expr(instr.args[0])
            self.context.return_values.append(value)
        return {"return": True}

    def _handle_jump(self, instr: Instruction) -> dict:
        """处理跳转"""
        return {}

    def _handle_jump_if(self, instr: Instruction) -> dict:
        """处理条件跳转"""
        return {}

    def _handle_do(self, instr: Instruction) -> dict:
        """处理 do"""
        return {}

    def _handle_end(self, instr: Instruction) -> dict:
        """处理 end"""
        return {}

    def _handle_if(self, instr: Instruction) -> dict:
        """处理 if"""
        if len(instr.args) > 0:
            cond = self._eval_expr(instr.args[0])
            self.context.set_local("_if_cond", bool(cond))
        return {}

    def _handle_then(self, instr: Instruction) -> dict:
        """处理 then"""
        return {}

    def _handle_else(self, instr: Instruction) -> dict:
        """处理 else"""
        return {}

    def _handle_elseif(self, instr: Instruction) -> dict:
        """处理 elseif"""
        return {}

    def _handle_while(self, instr: Instruction) -> dict:
        """处理 while"""
        if len(instr.args) > 0:
            cond = self._eval_expr(instr.args[0])
            self.context.set_local("_while_cond", bool(cond))
        return {}

    def _handle_for(self, instr: Instruction) -> dict:
        """处理 for"""
        return {}

    def _handle_repeat(self, instr: Instruction) -> dict:
        """处理 repeat"""
        return {}

    def _handle_until(self, instr: Instruction) -> dict:
        """处理 until"""
        return {}

    def _handle_func_def(self, instr: Instruction) -> dict:
        """处理函数定义"""
        if len(instr.args) > 0:
            func_name = instr.args[0]
            params = instr.args[1:] if len(instr.args) > 1 else []

            # 创建函数闭包
            def make_func(name, p, body_instrs):
                def func(*args):
                    # 设置参数为局部变量
                    locals_dict = dict(zip(p, args))
                    # 递归执行
                    sub_executor = InstructionExecutor()
                    result = sub_executor.execute(
                        body_instrs,
                        globals=self.context.globals,
                        initial_locals=locals_dict
                    )
                    if result.return_values:
                        return result.return_values[0]
                    return None
                return func

            # 存储函数定义（简化处理）
            self.context.set_global(func_name, lambda *a: None)
        return {}

    def _handle_func_end(self, instr: Instruction) -> dict:
        """处理函数结束"""
        return {}

    def _handle_expr(self, instr: Instruction) -> dict:
        """处理表达式"""
        if instr.args:
            self._eval_expr(instr.args[0])
        return {}

    def _handle_error(self, instr: Instruction) -> dict:
        """处理 error"""
        msg = instr.args[0] if instr.args else "error"
        self.context.error = msg
        self.context.running = False
        return {}

    def _handle_table_new(self, instr: Instruction) -> dict:
        """处理新建表"""
        return {"result": {}}

    def _handle_table_set(self, instr: Instruction) -> dict:
        """处理设置表元素"""
        return {}

    def _eval_expr(self, expr: str) -> Any:
        """
        简单表达式求值

        支持基本算术、变量引用、字符串。
        """
        if expr is None:
            return None

        expr = str(expr).strip()

        # 字符串字面量
        if (expr.startswith('"') and expr.endswith('"')) or \
           (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]

        # 数字字面量
        try:
            if "." in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass

        # nil
        if expr == "nil":
            return None

        # true/false
        if expr == "true":
            return True
        if expr == "false":
            return False

        # 变量引用
        return self.context.resolve_value(expr)


class InstructionVerifier:
    """
    指令验证器

    用于验证指令执行结果与预期一致。
    """

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.executor = InstructionExecutor(debug=debug)

    def verify_block(
        self,
        block: CodeBlock,
        expected_locals: dict[str, Any] | None = None,
        expected_return: Any = None,
    ) -> tuple[bool, str]:
        """
        验证单个 block 的执行结果

        Args:
            block: 要验证的 CodeBlock
            expected_locals: 预期的局部变量
            expected_return: 预期的返回值

        Returns:
            (success, message)
        """
        # 转换 block 为指令
        converter = InstructionConverter()
        block_instr = converter.convert_block(block)

        # 执行
        result = self.executor.execute(block_instr.instructions)

        if not result.success:
            return False, f"Execution failed: {result.error}"

        # 验证返回值
        if expected_return is not None:
            if result.return_value != expected_return:
                return False, f"Return value mismatch: got {result.return_value}, expected {expected_return}"

        # 验证局部变量
        if expected_locals and result.final_context:
            current_locals = result.final_context.get_current_locals()
            for name, expected_val in expected_locals.items():
                actual_val = current_locals.get(name)
                if actual_val != expected_val:
                    return False, f"Variable '{name}' mismatch: got {actual_val}, expected {expected_val}"

        return True, "Verification passed"

    def verify_instructions(
        self,
        instructions: list[Instruction],
        expected_return: Any = None,
    ) -> tuple[bool, str, Any]:
        """
        验证指令序列的执行结果

        Returns:
            (success, message, return_value)
        """
        result = self.executor.execute(instructions)

        if not result.success:
            return False, f"Execution failed: {result.error}", None

        if expected_return is not None:
            if result.return_value != expected_return:
                return False, f"Return mismatch: got {result.return_value}, expected {expected_return}", result.return_value

        return True, "OK", result.return_value


def create_simple_test() -> None:
    """
    创建简单测试示例

    演示如何使用指令执行器验证代码逻辑。
    """
    print("=" * 50)
    print("Instruction Executor Test")
    print("=" * 50)

    # 测试 1: 简单变量赋值
    print("\n[Test 1] Simple variable assignment")
    block1 = CodeBlock(
        block_id=1,
        content="local a = 10\nlocal b = 20\na = a + b\nreturn a",
        block_type="statement"
    )

    verifier = InstructionVerifier()
    success, msg = verifier.verify_block(block1, expected_return=30)
    print(f"  Result: {msg}")

    # 测试 2: 条件分支
    print("\n[Test 2] Conditional branch")
    block2 = CodeBlock(
        block_id=2,
        content="local x = 5\nif x > 3 then\n    x = 10\nend\nreturn x",
        block_type="control_struct"
    )

    success, msg = verifier.verify_block(block2, expected_return=10)
    print(f"  Result: {msg}")

    # 测试 3: 函数定义和调用
    print("\n[Test 3] Function definition")
    block3 = CodeBlock(
        block_id=3,
        content="local function add(a, b)\n    return a + b\nend\nlocal result = add(3, 4)\nreturn result",
        block_type="function_def"
    )

    success, msg = verifier.verify_block(block3, expected_return=7)
    print(f"  Result: {msg}")

    # 测试 4: 表操作
    print("\n[Test 4] Table operations")
    block4 = CodeBlock(
        block_id=4,
        content="local t = {}\nt.x = 10\nt.y = 20\nreturn t.x + t.y",
        block_type="statement"
    )

    # 由于表操作简化处理，这个测试可能需要根据实现调整
    print("  Result: Table operations require extended executor support")

    print("\n" + "=" * 50)
    print("Test Complete")
    print("=" * 50)


# ===== 简化的指令解释执行器 =====


@dataclass
class SimpleContext:
    """
    简单的执行上下文

    使用 dict 保存变量状态。
    """
    locals: dict[str, Any] = None
    globals: dict[str, Any] = None
    stack: list[Any] = None
    return_value: Any = None
    pc: int = 0
    running: bool = True

    def __post_init__(self):
        self.locals = self.locals or {}
        self.globals = self.globals or {}
        self.stack = self.stack or []

    def get(self, name: str) -> Any:
        """获取变量值"""
        if name in self.locals:
            return self.locals[name]
        if name in self.globals:
            return self.globals[name]
        return None

    def set(self, name: str, value: Any) -> None:
        """设置变量值"""
        self.locals[name] = value

    def push(self, value: Any) -> None:
        """压入栈"""
        self.stack.append(value)

    def pop(self) -> Any:
        """弹出栈"""
        if self.stack:
            return self.stack.pop()
        return None


@dataclass
class SimpleResult:
    """执行结果"""
    success: bool
    return_value: Any = None
    error: str | None = None
    context: SimpleContext | None = None
    executed_count: int = 0


def _eval_simple_expr(expr: str, ctx: SimpleContext) -> Any:
    """
    简单表达式求值

    支持：数字、字符串、nil、true/false、变量引用。
    不支持复杂算术或函数调用。
    """
    if expr is None:
        return None

    expr = str(expr).strip()

    # 字符串字面量
    if (expr.startswith('"') and expr.endswith('"')) or \
       (expr.startswith("'") and expr.endswith("'")):
        return expr[1:-1]

    # 数字字面量
    try:
        if "." in expr:
            return float(expr)
        return int(expr)
    except ValueError:
        pass

    # 布尔和 nil
    if expr == "nil":
        return None
    if expr == "true":
        return True
    if expr == "false":
        return False

    # 变量引用
    return ctx.get(expr)


def run_instructions(instructions: list[Instruction], debug: bool = False) -> SimpleResult:
    """
    简单指令解释执行器

    逐条处理指令序列，使用字典分发执行逻辑。

    Args:
        instructions: 指令列表
        debug: 是否打印调试信息

    Returns:
        SimpleResult: 执行结果
    """
    ctx = SimpleContext()
    pc = 0
    executed = 0

    # 指令处理器字典
    handlers = {
        OpCode.NOP: lambda i, c: {},

        OpCode.DECLARE: lambda i, c: c.set(i.args[0], None) if i.args else None,

        OpCode.INIT: lambda i, c: c.set(i.args[0], _eval_simple_expr(i.result, c)) if i.args else None,

        OpCode.ASSIGN: lambda i, c: c.set(i.args[0], _eval_simple_expr(i.result, c)) if i.args else None,

        OpCode.CALL: lambda i, c: (
            _eval_simple_expr(i.args[0], c) if i.args else None
        ) or (c.push(None)),

        OpCode.RETURN: lambda i, c: (setattr(c, 'return_value', None), setattr(c, 'running', False)),

        OpCode.RETURN_VAL: lambda i, c: (
            setattr(c, 'return_value', _eval_simple_expr(i.args[0], c) if i.args else None),
            setattr(c, 'running', False)
        ),

        OpCode.IF: lambda i, c: c.set("_cond", _eval_simple_expr(i.args[0], c)) if i.args else None,

        OpCode.WHILE: lambda i, c: c.set("_while_cond", _eval_simple_expr(i.args[0], c)) if i.args else None,

        OpCode.EXPR: lambda i, c: _eval_simple_expr(i.args[0], c) if i.args else None,

        OpCode.ERROR: lambda i, c: (
            setattr(c, 'running', False),
            setattr(c, 'return_value', f"error: {i.args[0] if i.args else 'unknown'}")
        ),

        OpCode.DO: lambda i, c: {},
        OpCode.END: lambda i, c: {},
        OpCode.THEN: lambda i, c: {},
        OpCode.ELSE: lambda i, c: {},
        OpCode.ELSEIF: lambda i, c: {},
        OpCode.FOR: lambda i, c: {},
        OpCode.REPEAT: lambda i, c: {},
        OpCode.UNTIL: lambda i, c: {},
        OpCode.BREAK: lambda i, c: {},
        OpCode.CONTINUE: lambda i, c: {},
        OpCode.FUNC_DEF: lambda i, c: {},
        OpCode.FUNC_END: lambda i, c: {},
        OpCode.TABLE_NEW: lambda i, c: c.push({}),
        OpCode.TABLE_SET: lambda i, c: None,
        OpCode.TABLE_GET: lambda i, c: None,
        OpCode.LABEL: lambda i, c: {},
        OpCode.COMMENT: lambda i, c: {},
        OpCode.JUMP: lambda i, c: {},
        OpCode.JUMP_IF: lambda i, c: {},
        OpCode.CALL_ASSIGN: lambda i, c: (
            c.set(i.result, _eval_simple_expr(i.args[0], c)) if i.result and i.args else None
        ),

        OpCode.IDENTITY: lambda i, c: (
            c.set(i.args[0], _eval_simple_expr(i.args[0], c)) if i.args else None
        ),
        OpCode.DUMMY: lambda i, c: {},
        OpCode.ASSERT: lambda i, c: {},
    }

    # 主循环
    while pc < len(instructions) and ctx.running:
        instr = instructions[pc]

        if debug:
            print(f"  PC={pc}: {instr.op.value} {instr.args} -> {instr.result}")

        handler = handlers.get(instr.op)
        if handler:
            try:
                handler(instr, ctx)
            except Exception as e:
                return SimpleResult(
                    success=False,
                    error=f"Error at PC={pc}: {e}",
                    executed_count=executed
                )
        else:
            if debug:
                print(f"    Unsupported: {instr.op.value}")

        pc += 1
        executed += 1

        # 防止无限循环
        if executed > 1000:
            return SimpleResult(
                success=False,
                error="Execution limit exceeded",
                context=ctx,
                executed_count=executed
            )

    return SimpleResult(
        success=True,
        return_value=ctx.return_value,
        context=ctx,
        executed_count=executed
    )


def run_from_block(block: CodeBlock, debug: bool = False) -> SimpleResult:
    """
    从 CodeBlock 执行指令

    Args:
        block: 代码块
        debug: 是否打印调试信息

    Returns:
        SimpleResult: 执行结果
    """
    converter = InstructionConverter()
    block_instr = converter.convert_block(block)
    return run_instructions(block_instr.instructions, debug=debug)


# 简化测试函数
def simple_test():
    """
    简单测试示例

    展示如何将代码转换为指令并执行。
    """
    print("=" * 50)
    print("Simple Instruction Executor Test")
    print("=" * 50)

    # 测试 1: 变量赋值
    print("\n[Test 1] Variable assignment")
    block1 = CodeBlock(
        block_id=1,
        content="local a = 10\nlocal b = 20\na = a + b\nreturn a",
        block_type="statement"
    )
    result1 = run_from_block(block1, debug=False)
    print(f"  Expected: 30, Got: {result1.return_value}, Success: {result1.success}")

    # 测试 2: 条件分支
    print("\n[Test 2] Conditional branch")
    block2 = CodeBlock(
        block_id=2,
        content="local x = 5\nif x > 3 then\n    x = 10\nend\nreturn x",
        block_type="control_struct"
    )
    result2 = run_from_block(block2, debug=False)
    print(f"  Expected: 10, Got: {result2.return_value}, Success: {result2.success}")

    # 测试 3: 打印调试信息
    print("\n[Test 3] Debug execution")
    block3 = CodeBlock(
        block_id=3,
        content="local a = 1\nlocal b = 2\nreturn a + b",
        block_type="statement"
    )
    print("  Instructions:")
    result3 = run_from_block(block3, debug=True)
    print(f"  Result: {result3.return_value}")

    # 测试 4: 恒等变换（不影响结果）
    print("\n[Test 4] Identity transformation")
    instr_list = [
        Instruction(OpCode.DECLARE, ["x"]),
        Instruction(OpCode.INIT, ["x"], None, "5"),
        Instruction(OpCode.IDENTITY, ["x"]),
        Instruction(OpCode.RETURN_VAL, ["x"]),
    ]
    result4 = run_instructions(instr_list)
    print(f"  Expected: 5, Got: {result4.return_value}, Success: {result4.success}")

    print("\n" + "=" * 50)
    print("Test Complete")
    print("=" * 50)


# ===== 标准解释器模型 (Standard Interpreter Model) =====


from typing import Callable, Optional
from dataclasses import dataclass, field


@dataclass
class PCNext:
    """
    程序计数器下一步指示器

    用于标准化指令处理器的返回值，支持：
    - PC_CONTINUE: 顺序执行下一条指令
    - PC_JUMP(n): 跳转到指定位置
    - PC_SKIP(n): 跳过指定数量指令
    - PC_BREAK: 结束执行循环
    - PC_HALT: 正常结束执行
    """
    NEXT: int = 0      # 继续执行
    JUMP: int = 1      # 跳转
    SKIP: int = 4      # 跳过（用于调度策略实验）
    BREAK: int = 2     # 跳出循环
    HALT: int = 3      # 正常结束

    def __init__(self, action: int, target: int = 0):
        self.action = action
        self.target = target

    @staticmethod
    def continue_() -> 'PCNext':
        """顺序执行下一条指令"""
        return PCNext(PCNext.NEXT, 1)  # 默认偏移量 1

    @staticmethod
    def jump(target: int) -> 'PCNext':
        """跳转到指定位置"""
        return PCNext(PCNext.JUMP, target)

    @staticmethod
    def skip(count: int = 1) -> 'PCNext':
        """跳过指定数量的指令（使用 SKIP action）"""
        return PCNext(PCNext.SKIP, count)

    @staticmethod
    def break_() -> 'PCNext':
        """跳出执行循环"""
        return PCNext(PCNext.BREAK, 0)

    @staticmethod
    def halt() -> 'PCNext':
        """正常结束执行"""
        return PCNext(PCNext.HALT, 0)


# Handler 类型别名
InstructionHandlerFunc = Callable[['VMContext', 'Instruction'], PCNext]


class VMContext:
    """
    虚拟机上下文

    保存执行过程中的所有状态。
    """
    locals: dict[str, Any]
    globals: dict[str, Any]
    stack: list[Any]
    pc: int
    running: bool
    return_value: Any
    call_depth: int
    labels: dict[str, int]

    def __init__(self):
        self.locals = {}
        self.globals = {}
        self.stack = []
        self.pc = 0
        self.running = True
        self.return_value = None
        self.call_depth = 0
        self.labels = {}

    def get(self, name: str) -> Any:
        """获取变量值（局部优先）"""
        if name in self.locals:
            return self.locals[name]
        if name in self.globals:
            return self.globals[name]
        return None

    def set_local(self, name: str, value: Any) -> None:
        """设置局部变量"""
        self.locals[name] = value

    def set_global(self, name: str, value: Any) -> None:
        """设置全局变量"""
        self.globals[name] = value

    def set_value(self, name: str, value: Any) -> None:
        """设置变量值"""
        self.locals[name] = value

    def push(self, value: Any) -> None:
        """压入栈"""
        self.stack.append(value)

    def pop(self) -> Any:
        """弹出栈"""
        if self.stack:
            return self.stack.pop()
        return None

    def top(self) -> Any:
        """查看栈顶"""
        if self.stack:
            return self.stack[-1]
        return None

    def add_label(self, name: str, pc: int) -> None:
        """添加标签"""
        self.labels[name] = pc

    def get_label(self, name: str) -> int | None:
        """获取标签位置"""
        return self.labels.get(name)

    def halt(self) -> None:
        """停止执行"""
        self.running = False

    def reset(self) -> None:
        """重置上下文"""
        self.pc = 0
        self.running = True
        self.return_value = None
        self.stack.clear()


@dataclass
class VMResult:
    """虚拟机执行结果"""
    success: bool
    return_value: Any = None
    error: str | None = None
    pc: int = 0
    executed_count: int = 0
    context: VMContext | None = None


class InstructionVM:
    """
    标准指令虚拟机

    使用显式 PC 和统一分发机制执行指令序列。
    符合经典解释器模型设计。
    """

    def __init__(self, max_instructions: int = 10000, debug: bool = False):
        self.max_instructions = max_instructions
        self.debug = debug
        self.context: VMContext | None = None
        self.instructions: list[Instruction] = []
        self.handlers: dict[OpCode, InstructionHandlerFunc] = {}

        # 注册默认处理器
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """注册默认指令处理器"""

        # 空操作
        def h_nop(ctx: VMContext, instr: Instruction) -> PCNext:
            return PCNext.continue_()

        # 变量声明
        def h_declare(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                ctx.set_local(instr.args[0], None)
            return PCNext.continue_()

        # 变量初始化
        def h_init(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                value = self._eval_expr(instr.result, ctx)
                ctx.set_local(instr.args[0], value)
            return PCNext.continue_()

        # 赋值
        def h_assign(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                value = self._eval_expr(instr.result, ctx)
                ctx.set_value(instr.args[0], value)
            return PCNext.continue_()

        # 函数调用
        def h_call(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                func_name = instr.args[0]
                args = [self._eval_expr(a, ctx) for a in instr.args[1:]]
                func = ctx.get(func_name)
                if callable(func):
                    result = func(*args)
                    ctx.push(result)
                else:
                    ctx.push(None)
            return PCNext.continue_()

        # 调用并赋值
        def h_call_assign(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.result and instr.args:
                result = self._eval_expr(instr.args[0], ctx)
                ctx.set_local(instr.result, result)
            return PCNext.continue_()

        # 返回空
        def h_return(ctx: VMContext, instr: Instruction) -> PCNext:
            ctx.return_value = None
            ctx.halt()
            return PCNext.halt()

        # 返回值
        def h_return_val(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                ctx.return_value = self._eval_expr(instr.args[0], ctx)
            ctx.halt()
            return PCNext.halt()

        # 标签
        def h_label(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                ctx.add_label(str(instr.args[0]), ctx.pc)
            return PCNext.continue_()

        # 无条件跳转
        def h_jump(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                target = instr.args[0]
                if isinstance(target, int):
                    return PCNext.jump(target)
                label_pc = ctx.get_label(str(target))
                if label_pc is not None:
                    return PCNext.jump(label_pc)
            return PCNext.continue_()

        # 条件跳转
        def h_jump_if(ctx: VMContext, instr: Instruction) -> PCNext:
            if len(instr.args) >= 2:
                cond = self._eval_expr(instr.args[0], ctx)
                target = instr.args[1]
                if self._is_truthy(cond):
                    if isinstance(target, int):
                        return PCNext.jump(target)
                    label_pc = ctx.get_label(str(target))
                    if label_pc is not None:
                        return PCNext.jump(label_pc)
            return PCNext.continue_()

        # if 块
        def h_if(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                cond = self._eval_expr(instr.args[0], ctx)
                ctx.set_local("_cond", self._is_truthy(cond))
            return PCNext.continue_()

        # while 块
        def h_while(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                cond = self._eval_expr(instr.args[0], ctx)
                ctx.set_local("_while_cond", self._is_truthy(cond))
            return PCNext.continue_()

        # repeat 块
        def h_repeat(ctx: VMContext, instr: Instruction) -> PCNext:
            ctx.set_local("_repeat_active", True)
            return PCNext.continue_()

        # until 块
        def h_until(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                cond = self._eval_expr(instr.args[0], ctx)
                if self._is_truthy(cond):
                    ctx.set_local("_repeat_active", False)
                    return PCNext.continue_()
                return PCNext.jump(ctx.pc - 1)  # 跳回 repeat
            return PCNext.continue_()

        # break
        def h_break(ctx: VMContext, instr: Instruction) -> PCNext:
            return PCNext.break_()

        # continue
        def h_continue(ctx: VMContext, instr: Instruction) -> PCNext:
            return PCNext.skip(-1)  # 回到循环开始

        # 表达式语句
        def h_expr(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                self._eval_expr(instr.args[0], ctx)
            return PCNext.continue_()

        # error 语句
        def h_error(ctx: VMContext, instr: Instruction) -> PCNext:
            msg = instr.args[0] if instr.args else "unknown error"
            ctx.return_value = f"error: {msg}"
            ctx.halt()
            return PCNext.halt()

        # 恒等变换（辅助指令）
        def h_identity(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                value = ctx.get(instr.args[0])
                ctx.set_local(instr.args[0], value)
            return PCNext.continue_()

        # 哑操作（辅助指令）
        def h_dummy(ctx: VMContext, instr: Instruction) -> PCNext:
            return PCNext.continue_()

        # 表创建
        def h_table_new(ctx: VMContext, instr: Instruction) -> PCNext:
            ctx.push({})
            return PCNext.continue_()

        # 表设置
        def h_table_set(ctx: VMContext, instr: Instruction) -> PCNext:
            return PCNext.continue_()

        # 注册所有处理器
        self.handlers = {
            OpCode.NOP: h_nop,
            OpCode.DECLARE: h_declare,
            OpCode.INIT: h_init,
            OpCode.ASSIGN: h_assign,
            OpCode.CALL: h_call,
            OpCode.CALL_ASSIGN: h_call_assign,
            OpCode.RETURN: h_return,
            OpCode.RETURN_VAL: h_return_val,
            OpCode.JUMP: h_jump,
            OpCode.JUMP_IF: h_jump_if,
            OpCode.IF: h_if,
            OpCode.WHILE: h_while,
            OpCode.REPEAT: h_repeat,
            OpCode.UNTIL: h_until,
            OpCode.BREAK: h_break,
            OpCode.CONTINUE: h_continue,
            OpCode.EXPR: h_expr,
            OpCode.ERROR: h_error,
            OpCode.IDENTITY: h_identity,
            OpCode.DUMMY: h_dummy,
            OpCode.TABLE_NEW: h_table_new,
            OpCode.TABLE_SET: h_table_set,
            OpCode.LABEL: h_label,
            OpCode.DO: h_nop,
            OpCode.END: h_nop,
            OpCode.THEN: h_nop,
            OpCode.ELSE: h_nop,
            OpCode.ELSEIF: h_nop,
            OpCode.FOR: h_expr,
            OpCode.FUNC_DEF: h_nop,
            OpCode.FUNC_END: h_nop,
            OpCode.COMMENT: h_nop,
            OpCode.TABLE_GET: h_nop,
            OpCode.ASSERT: h_nop,
        }

    def register_handler(self, opcode: OpCode, handler: InstructionHandlerFunc) -> None:
        """注册指令处理器"""
        self.handlers[opcode] = handler

    def _eval_expr(self, expr: str | None, ctx: VMContext) -> Any:
        """求值简单表达式"""
        if expr is None:
            return None
        expr = str(expr).strip()
        if not expr:
            return None

        # 字符串字面量
        if (expr.startswith('"') and expr.endswith('"')) or \
           (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]

        # 数字字面量
        try:
            if "." in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass

        # 布尔和 nil
        if expr == "nil":
            return None
        if expr == "true":
            return True
        if expr == "false":
            return False

        # 变量引用
        return ctx.get(expr)

    def _is_truthy(self, value: Any) -> bool:
        """判断真值"""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        if isinstance(value, (list, dict, tuple)):
            return len(value) > 0
        return True

    def execute(self, instructions: list[Instruction], debug: bool = False) -> VMResult:
        """
        执行指令序列

        标准解释器执行循环：
        1. 根据 PC 读取指令
        2. 分发到对应 handler
        3. Handler 返回下一个 PC
        4. 更新 PC，继续执行
        """
        self.instructions = instructions
        self.context = VMContext()
        debug = debug or self.debug

        if debug:
            print(f"[VM] Starting execution with {len(instructions)} instructions")

        executed = 0
        pc = 0

        # 标准解释器执行循环
        while pc < len(self.instructions) and self.context.running:
            # 1. 读取指令
            instr = self.instructions[pc]

            if debug:
                print(f"  PC={pc}: {instr.op.value} {instr.args} -> {instr.result}")

            # 2. 获取处理器
            handler = self.handlers.get(instr.op)

            if handler:
                try:
                    # 3. 执行处理器
                    result = handler(self.context, instr)

                    # 4. 处理 PC 更新
                    if result.action == PCNext.NEXT:
                        pc += 1
                    elif result.action == PCNext.JUMP:
                        if result.target == 0:
                            pc += 1  # skip(0) 等同于 continue
                        elif result.target > 0:
                            pc = result.target
                        else:
                            pc += result.target  # 相对跳转

                    elif result.action == PCNext.BREAK:
                        break
                    elif result.action == PCNext.HALT:
                        break

                except Exception as e:
                    return VMResult(
                        success=False,
                        error=f"Error at PC={pc}: {e}",
                        pc=pc,
                        executed_count=executed,
                        context=self.context
                    )
            else:
                if debug:
                    print(f"    Unsupported opcode: {instr.op.value}")
                pc += 1

            executed += 1

            # 防止无限循环
            if executed > self.max_instructions:
                return VMResult(
                    success=False,
                    error="Execution limit exceeded",
                    pc=pc,
                    executed_count=executed,
                    context=self.context
                )

        if debug:
            print(f"[VM] Execution finished: pc={pc}, executed={executed}")

        return VMResult(
            success=True,
            return_value=self.context.return_value,
            pc=pc,
            executed_count=executed,
            context=self.context
        )

    def execute_from_block(self, block: CodeBlock, debug: bool = False) -> VMResult:
        """从 CodeBlock 执行"""
        converter = InstructionConverter()
        block_instr = converter.convert_block(block)
        return self.execute(block_instr.instructions, debug=debug)


# ===== 可配置执行路径的调度执行器 =====
# (Dispatch Strategy Executor with Configurable PC Resolution)


@dataclass
class ExecutionState:
    """
    执行路径计算的中间状态

    在计算下一条指令位置时使用的上下文数据，
    独立于 VMContext，用于解耦调度策略与指令执行。
    """
    pc: int                          # 当前指令位置
    raw_offset: int = 1             # handler 返回的基础偏移量（1 = 顺序执行）
    modifier: int = 0               # 额外的修正值（用于复杂调度策略）
    dispatch_mode: str = "sequential"  # 调度模式标识
    metadata: dict = None           # 扩展元数据

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def copy(self) -> 'ExecutionState':
        """创建状态副本"""
        return ExecutionState(
            pc=self.pc,
            raw_offset=self.raw_offset,
            modifier=self.modifier,
            dispatch_mode=self.dispatch_mode,
            metadata=dict(self.metadata)
        )


class PCResolver(ABC):
    """
    PC 计算策略抽象基类

    定义如何根据 ExecutionState 计算最终的下一条指令位置。
    支持不同的调度策略，便于实验和研究。
    """

    @abstractmethod
    def resolve(self, state: ExecutionState, ctx: VMContext) -> int:
        """
        计算下一条指令位置

        Args:
            state: 执行路径状态（包含 raw_offset, modifier 等）
            ctx: 虚拟机上下文

        Returns:
            下一条指令的 PC 值
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称"""
        pass

    def on_instruction_executed(self, instr: Instruction, ctx: VMContext) -> None:
        """
        指令执行后的钩子（可选实现）

        可用于在每次指令执行后更新 state 中的 metadata。
        默认空实现。
        """
        pass


class SequentialPCResolver(PCResolver):
    """
    顺序执行解析器（默认策略）

    简单的 pc + 1 逻辑，保持与传统解释器一致。
    """

    @property
    def name(self) -> str:
        return "sequential"

    def resolve(self, state: ExecutionState, ctx: VMContext) -> int:
        """直接使用 raw_offset 计算下一步"""
        return state.pc + state.raw_offset


class OffsetPCResolver(PCResolver):
    """
    带修正的偏移量解析器

    支持在 raw_offset 基础上加上 modifier，
    适用于需要累积偏移量的复杂调度策略。
    """

    @property
    def name(self) -> str:
        return "offset_with_modifier"

    def resolve(self, state: ExecutionState, ctx: VMContext) -> int:
        """raw_offset + modifier"""
        return state.pc + state.raw_offset + state.modifier


class ConditionalPCResolver(PCResolver):
    """
    条件式解析器

    根据上下文条件在两种 offset 模式间切换，
    可用于研究分支预测类策略。
    """

    def __init__(self, true_offset: int = 1, false_offset: int = 1):
        self.true_offset = true_offset
        self.false_offset = false_offset

    @property
    def name(self) -> str:
        return "conditional"

    def resolve(self, state: ExecutionState, ctx: VMContext) -> int:
        """根据条件选择不同的偏移量"""
        use_alt = state.metadata.get("_use_alternate_offset", False)
        offset = self.false_offset if use_alt else self.true_offset
        return state.pc + offset

    def on_instruction_executed(self, instr: Instruction, ctx: VMContext) -> None:
        """根据指令类型切换偏移模式"""
        if instr.op in (OpCode.JUMP, OpCode.JUMP_IF):
            ctx.set_local("_use_alternate_offset", True)
        else:
            ctx.set_local("_use_alternate_offset", False)


class StatePCResolver(PCResolver):
    """
    状态感知解析器

    基于执行上下文的状态来决定下一步偏移量。
    可以根据运行时状态（如条件、循环深度等）动态调整策略。
    """

    def __init__(self):
        self._loop_depth: int = 0  # 循环深度追踪

    @property
    def name(self) -> str:
        return "state_aware"

    def resolve(self, state: ExecutionState, ctx: VMContext) -> int:
        """基于上下文状态计算偏移"""
        # 使用条件标志来影响偏移选择（仅影响调度，不影响语义）
        cond_override = state.metadata.get("_cond_override", False)
        if cond_override:
            return state.pc + state.raw_offset + 1
        return state.pc + state.raw_offset

    def on_instruction_executed(self, instr: Instruction, ctx: VMContext) -> None:
        """根据指令类型更新状态"""
        if instr.op == OpCode.WHILE:
            self._loop_depth += 1
        elif instr.op == OpCode.END:
            self._loop_depth = max(0, self._loop_depth - 1)
        elif instr.op == OpCode.JUMP_IF:
            # 设置条件覆盖标志（用于实验性调度）
            ctx.set_local("_cond_override", True)
        else:
            ctx.set_local("_cond_override", False)


# 注册默认策略的工厂函数
def create_default_resolver(strategy: str = "sequential") -> PCResolver:
    """创建默认的 PC 解析器"""
    resolvers = {
        "sequential": SequentialPCResolver,
        "offset": OffsetPCResolver,
        "conditional": ConditionalPCResolver,
        "state_aware": StatePCResolver,
    }
    resolver_class = resolvers.get(strategy, SequentialPCResolver)
    return resolver_class()


class DispatchStrategyExecutor:
    """
    调度策略执行器

    核心改进：
    1. 引入 ExecutionState 作为 PC 计算的中间状态
    2. Handler 只返回 raw_offset（基础偏移量）
    3. 通过 PCResolver 统一计算最终 PC
    4. 调度逻辑集中管理，handler 与路径计算解耦

    这种设计允许在运行时切换不同的执行路径计算策略，
    而不影响指令执行本身的语义。
    """

    def __init__(
        self,
        max_instructions: int = 10000,
        debug: bool = False,
        resolver: PCResolver | str = "sequential"
    ):
        self.max_instructions = max_instructions
        self.debug = debug

        # 支持字符串或实例两种方式指定 resolver
        if isinstance(resolver, str):
            self.resolver = create_default_resolver(resolver)
        else:
            self.resolver = resolver

        self.context: VMContext | None = None
        self.instructions: list[Instruction] = []
        self.handlers: dict[OpCode, InstructionHandlerFunc] = {}
        self._exec_state: ExecutionState | None = None

        # 注册默认处理器
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """注册默认指令处理器（返回 raw_offset）"""

        # 通用辅助函数
        def make_continue() -> PCNext:
            return PCNext(PCNext.NEXT, 1)  # NEXT action, raw_offset=1

        def make_jump(target: int) -> PCNext:
            return PCNext(PCNext.JUMP, target)  # JUMP action, target=跳转目标

        # 空操作
        def h_nop(ctx: VMContext, instr: Instruction) -> PCNext:
            return make_continue()

        # 变量声明
        def h_declare(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                ctx.set_local(instr.args[0], None)
            return make_continue()

        # 变量初始化
        def h_init(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                value = self._eval_expr(instr.result, ctx)
                ctx.set_local(instr.args[0], value)
            return make_continue()

        # 赋值
        def h_assign(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                value = self._eval_expr(instr.result, ctx)
                ctx.set_value(instr.args[0], value)
            return make_continue()

        # 函数调用
        def h_call(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                func_name = instr.args[0]
                args = [self._eval_expr(a, ctx) for a in instr.args[1:]]
                func = ctx.get(func_name)
                if callable(func):
                    result = func(*args)
                    ctx.push(result)
                else:
                    ctx.push(None)
            return make_continue()

        # 调用并赋值
        def h_call_assign(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.result and instr.args:
                result = self._eval_expr(instr.args[0], ctx)
                ctx.set_local(instr.result, result)
            return make_continue()

        # 返回空
        def h_return(ctx: VMContext, instr: Instruction) -> PCNext:
            ctx.return_value = None
            ctx.halt()
            return PCNext(PCNext.HALT, 0)

        # 返回值
        def h_return_val(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                ctx.return_value = self._eval_expr(instr.args[0], ctx)
            ctx.halt()
            return PCNext(PCNext.HALT, 0)

        # 标签
        def h_label(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                ctx.add_label(str(instr.args[0]), ctx.pc)
            return make_continue()

        # 无条件跳转
        def h_jump(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                target = instr.args[0]
                if isinstance(target, int):
                    return make_jump(target)
                label_pc = ctx.get_label(str(target))
                if label_pc is not None:
                    return make_jump(label_pc)
            return make_continue()

        # 条件跳转
        def h_jump_if(ctx: VMContext, instr: Instruction) -> PCNext:
            if len(instr.args) >= 2:
                cond = self._eval_expr(instr.args[0], ctx)
                target = instr.args[1]
                if self._is_truthy(cond):
                    if isinstance(target, int):
                        return make_jump(target)
                    label_pc = ctx.get_label(str(target))
                    if label_pc is not None:
                        return make_jump(label_pc)
            return make_continue()

        # if 块
        def h_if(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                cond = self._eval_expr(instr.args[0], ctx)
                ctx.set_local("_cond", self._is_truthy(cond))
            return make_continue()

        # while 块
        def h_while(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                cond = self._eval_expr(instr.args[0], ctx)
                ctx.set_local("_while_cond", self._is_truthy(cond))
            return make_continue()

        # repeat 块
        def h_repeat(ctx: VMContext, instr: Instruction) -> PCNext:
            ctx.set_local("_repeat_active", True)
            return make_continue()

        # until 块
        def h_until(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                cond = self._eval_expr(instr.args[0], ctx)
                if self._is_truthy(cond):
                    ctx.set_local("_repeat_active", False)
                    return make_continue()
                return make_jump(ctx.pc - 1)
            return make_continue()

        # break
        def h_break(ctx: VMContext, instr: Instruction) -> PCNext:
            return PCNext(PCNext.BREAK, 0)

        # continue
        def h_continue(ctx: VMContext, instr: Instruction) -> PCNext:
            return PCNext(PCNext.SKIP, -1)

        # 表达式语句
        def h_expr(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                self._eval_expr(instr.args[0], ctx)
            return make_continue()

        # error 语句
        def h_error(ctx: VMContext, instr: Instruction) -> PCNext:
            msg = instr.args[0] if instr.args else "unknown error"
            ctx.return_value = f"error: {msg}"
            ctx.halt()
            return PCNext(PCNext.HALT, 0)

        # 恒等变换
        def h_identity(ctx: VMContext, instr: Instruction) -> PCNext:
            if instr.args:
                value = ctx.get(instr.args[0])
                ctx.set_local(instr.args[0], value)
            return make_continue()

        # 哑操作
        def h_dummy(ctx: VMContext, instr: Instruction) -> PCNext:
            return make_continue()

        # 表创建
        def h_table_new(ctx: VMContext, instr: Instruction) -> PCNext:
            ctx.push({})
            return make_continue()

        # 表设置
        def h_table_set(ctx: VMContext, instr: Instruction) -> PCNext:
            return make_continue()

        # 注册所有处理器
        self.handlers = {
            OpCode.NOP: h_nop,
            OpCode.DECLARE: h_declare,
            OpCode.INIT: h_init,
            OpCode.ASSIGN: h_assign,
            OpCode.CALL: h_call,
            OpCode.CALL_ASSIGN: h_call_assign,
            OpCode.RETURN: h_return,
            OpCode.RETURN_VAL: h_return_val,
            OpCode.JUMP: h_jump,
            OpCode.JUMP_IF: h_jump_if,
            OpCode.IF: h_if,
            OpCode.WHILE: h_while,
            OpCode.REPEAT: h_repeat,
            OpCode.UNTIL: h_until,
            OpCode.BREAK: h_break,
            OpCode.CONTINUE: h_continue,
            OpCode.EXPR: h_expr,
            OpCode.ERROR: h_error,
            OpCode.IDENTITY: h_identity,
            OpCode.DUMMY: h_dummy,
            OpCode.TABLE_NEW: h_table_new,
            OpCode.TABLE_SET: h_table_set,
            OpCode.LABEL: h_label,
            OpCode.DO: h_nop,
            OpCode.END: h_nop,
            OpCode.THEN: h_nop,
            OpCode.ELSE: h_nop,
            OpCode.ELSEIF: h_nop,
            OpCode.FOR: h_expr,
            OpCode.FUNC_DEF: h_nop,
            OpCode.FUNC_END: h_nop,
            OpCode.COMMENT: h_nop,
            OpCode.TABLE_GET: h_nop,
            OpCode.ASSERT: h_nop,
        }

    def register_handler(self, opcode: OpCode, handler: InstructionHandlerFunc) -> None:
        """注册指令处理器"""
        self.handlers[opcode] = handler

    def set_resolver(self, resolver: PCResolver | str) -> None:
        """切换 PC 解析策略"""
        if isinstance(resolver, str):
            self.resolver = create_default_resolver(resolver)
        else:
            self.resolver = resolver

    def _eval_expr(self, expr: str | None, ctx: VMContext) -> Any:
        """求值简单表达式"""
        if expr is None:
            return None
        expr = str(expr).strip()
        if not expr:
            return None

        if (expr.startswith('"') and expr.endswith('"')) or \
           (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]

        try:
            if "." in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass

        if expr == "nil":
            return None
        if expr == "true":
            return True
        if expr == "false":
            return False

        return ctx.get(expr)

    def _is_truthy(self, value: Any) -> bool:
        """判断真值"""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        if isinstance(value, (list, dict, tuple)):
            return len(value) > 0
        return True

    def _build_state(self, pc: int, raw_offset: int = 1) -> ExecutionState:
        """构建执行状态"""
        return ExecutionState(
            pc=pc,
            raw_offset=raw_offset,
            modifier=0,
            dispatch_mode=self.resolver.name,
            metadata={}
        )

    def _resolve_next_pc(self, state: ExecutionState, ctx: VMContext) -> int:
        """
        核心：统一计算下一条指令位置

        这是调度策略的核心方法：
        1. 接收 handler 返回的 raw_offset
        2. 结合 ExecutionState 中的 modifier/metadata
        3. 通过 PCResolver 计算最终 PC
        """
        return self.resolver.resolve(state, ctx)

    def _advance_pc(
        self,
        pc: int,
        pc_next: PCNext,
        state: ExecutionState
    ) -> tuple[int, ExecutionState]:
        """
        根据 PCNext 和 state 计算新 PC

        返回 (new_pc, updated_state)
        """
        ctx = self.context

        if pc_next.action == PCNext.NEXT:
            # 顺序执行：raw_offset 由 handler 返回
            state.raw_offset = pc_next.target if pc_next.target != 0 else 1
            new_pc = self._resolve_next_pc(state, ctx)
            return new_pc, state

        elif pc_next.action == PCNext.JUMP:
            # 跳转：target 直接指定目标位置
            if pc_next.target == 0:
                # skip(0) 等同于继续
                return pc + 1, state
            elif pc_next.target > 0:
                return pc_next.target, state
            else:
                # 相对跳转
                return pc + pc_next.target, state

        elif pc_next.action == PCNext.SKIP:
            # 跳过指定数量
            state.raw_offset = pc_next.target
            new_pc = self._resolve_next_pc(state, ctx)
            return new_pc, state

        elif pc_next.action == PCNext.BREAK:
            return len(self.instructions), state

        elif pc_next.action == PCNext.HALT:
            return len(self.instructions), state

        # 默认顺序
        return pc + 1, state

    def execute(
        self,
        instructions: list[Instruction],
        debug: bool = False
    ) -> VMResult:
        """
        执行指令序列

        调度流程：
        1. 从指令列表读取当前 pc 的指令
        2. 分发到对应 handler 执行
        3. Handler 返回 PCNext（包含 action 和 raw_offset/target）
        4. 通过 _advance_pc 计算新 PC（解耦点）
        5. 更新 pc，继续循环
        """
        self.instructions = instructions
        self.context = VMContext()
        self._exec_state = None
        debug = debug or self.debug

        if debug:
            print(f"[DispatchStrategyVM] Starting with {len(instructions)} instructions")
            print(f"  Resolver: {self.resolver.name}")

        executed = 0
        pc = 0

        while pc < len(self.instructions) and self.context.running:
            instr = self.instructions[pc]

            if debug:
                print(f"  PC={pc}: {instr.op.value} {instr.args} -> {instr.result}")

            handler = self.handlers.get(instr.op)

            if handler:
                try:
                    # 初始化或更新执行状态
                    self._exec_state = self._build_state(pc)

                    # 执行 handler
                    pc_next = handler(self.context, instr)

                    # 调用 resolver 的钩子（如果实现了）
                    self.resolver.on_instruction_executed(instr, self.context)

                    # 计算新 PC（核心解耦点）
                    pc, self._exec_state = self._advance_pc(
                        pc, pc_next, self._exec_state
                    )

                except Exception as e:
                    return VMResult(
                        success=False,
                        error=f"Error at PC={pc}: {e}",
                        pc=pc,
                        executed_count=executed,
                        context=self.context
                    )
            else:
                if debug:
                    print(f"    Unsupported opcode: {instr.op.value}")
                pc += 1

            executed += 1

            if executed > self.max_instructions:
                return VMResult(
                    success=False,
                    error="Execution limit exceeded",
                    pc=pc,
                    executed_count=executed,
                    context=self.context
                )

        if debug:
            print(f"[DispatchStrategyVM] Finished: pc={pc}, executed={executed}")

        return VMResult(
            success=True,
            return_value=self.context.return_value,
            pc=pc,
            executed_count=executed,
            context=self.context
        )

    def execute_from_block(self, block: CodeBlock, debug: bool = False) -> VMResult:
        """从 CodeBlock 执行"""
        converter = InstructionConverter()
        block_instr = converter.convert_block(block)
        return self.execute(block_instr.instructions, debug=debug)


# ===== 表驱动执行模型 (Table-Driven Execution Model) =====


@dataclass
class InstructionSpec:
    """
    指令规格定义

    集中定义每条指令的元数据和行为参数。
    """
    opcode: OpCode
    name: str
    category: str
    description: str

    # 参数规格
    min_args: int = 0
    max_args: int = 0
    arg_types: list[str] = None  # "var", "imm", "label", "expr"

    # 执行行为
    has_result: bool = False
    terminates: bool = False  # 是否终止执行
    updates_pc: bool = False   # 是否修改 PC

    # 内存操作
    reads_memory: bool = False
    writes_memory: bool = False
    uses_stack: bool = False

    # 元数据
    metadata: dict = None

    def __post_init__(self):
        if self.arg_types is None:
            self.arg_types = []
        if self.metadata is None:
            self.metadata = {}


class InstructionTable:
    """
    中央指令表

    集中管理所有指令的规格定义和行为配置。
    类似于 CPU 的指令集架构（ISA）文档。
    """

    _table: dict[OpCode, InstructionSpec] = {}
    _by_category: dict[str, list[OpCode]] = {}

    @classmethod
    def register(cls, spec: InstructionSpec) -> None:
        """注册指令规格"""
        cls._table[spec.opcode] = spec

        # 按类别索引
        if spec.category not in cls._by_category:
            cls._by_category[spec.category] = []
        if spec.opcode not in cls._by_category[spec.category]:
            cls._by_category[spec.category].append(spec.opcode)

    @classmethod
    def get(cls, opcode: OpCode) -> InstructionSpec | None:
        """获取指令规格"""
        return cls._table.get(opcode)

    @classmethod
    def get_handler_name(cls, opcode: OpCode) -> str:
        """获取处理器名称"""
        return f"h_{opcode.value}"

    @classmethod
    def get_by_category(cls, category: str) -> list[OpCode]:
        """按类别获取指令"""
        return cls._by_category.get(category, [])

    @classmethod
    def get_all_categories(cls) -> list[str]:
        """获取所有类别"""
        return list(cls._by_category.keys())

    @classmethod
    def get_all_opcodes(cls) -> list[OpCode]:
        """获取所有操作码"""
        return list(cls._table.keys())

    @classmethod
    def validate(cls, instr: Instruction) -> tuple[bool, str]:
        """验证指令格式"""
        spec = cls.get(instr.op)
        if not spec:
            return False, f"Unknown opcode: {instr.op}"

        arg_count = len(instr.args) if instr.args else 0
        if arg_count < spec.min_args:
            return False, f"{instr.op.value}: too few args (min={spec.min_args})"
        if spec.max_args > 0 and arg_count > spec.max_args:
            return False, f"{instr.op.value}: too many args (max={spec.max_args})"

        return True, "OK"


class InstructionDescriptor:
    """
    指令描述符

    将指令规格与实际处理器函数关联。
    """

    def __init__(
        self,
        spec: InstructionSpec,
        handler: callable,
        generator: callable | None = None
    ):
        self.spec = spec
        self.handler = handler
        self.generator = generator

    def execute(self, ctx: VMContext, instr: Instruction) -> PCNext:
        """执行指令"""
        return self.handler(ctx, instr)

    def generate(self, instr: Instruction) -> str:
        """生成代码"""
        if self.generator:
            return self.generator(instr)
        return f"-- {instr.op.value}"


class TableDrivenExecutor:
    """
    表驱动执行器

    核心思想：用数据表驱动执行，而不是硬编码 if/elif。
    类似于 Forth 虚拟机或 SQL 查询引擎的执行方式。
    """

    def __init__(
        self,
        max_instructions: int = 10000,
        debug: bool = False,
        strict_mode: bool = True
    ):
        self.max_instructions = max_instructions
        self.debug = debug
        self.strict_mode = strict_mode

        self.context: VMContext | None = None
        self.instructions: list[Instruction] = []
        self.descriptors: dict[OpCode, InstructionDescriptor] = {}
        self.spec_table: dict[OpCode, InstructionSpec] = {}

        # 初始化
        self._init_spec_table()
        self._init_descriptors()

    def _init_spec_table(self) -> None:
        """初始化指令规格表"""
        specs = [
            # === 控制流 ===
            InstructionSpec(
                opcode=OpCode.NOP,
                name="nop",
                category="control_flow",
                description="空操作",
                min_args=0, max_args=0,
                terminates=False, updates_pc=False
            ),
            InstructionSpec(
                opcode=OpCode.RETURN,
                name="return",
                category="control_flow",
                description="返回（无值）",
                min_args=0, max_args=0,
                terminates=True
            ),
            InstructionSpec(
                opcode=OpCode.RETURN_VAL,
                name="return_val",
                category="control_flow",
                description="返回值",
                min_args=1, max_args=1,
                arg_types=["expr"],
                terminates=True
            ),
            InstructionSpec(
                opcode=OpCode.JUMP,
                name="jump",
                category="control_flow",
                description="无条件跳转",
                min_args=1, max_args=1,
                arg_types=["label"],
                updates_pc=True
            ),
            InstructionSpec(
                opcode=OpCode.JUMP_IF,
                name="jump_if",
                category="control_flow",
                description="条件跳转",
                min_args=2, max_args=2,
                arg_types=["expr", "label"],
                updates_pc=True
            ),
            InstructionSpec(
                opcode=OpCode.BREAK,
                name="break",
                category="control_flow",
                description="跳出循环",
                min_args=0, max_args=0,
                updates_pc=True
            ),
            InstructionSpec(
                opcode=OpCode.CONTINUE,
                name="continue",
                category="control_flow",
                description="继续循环",
                min_args=0, max_args=0,
                updates_pc=True
            ),
            InstructionSpec(
                opcode=OpCode.LABEL,
                name="label",
                category="control_flow",
                description="标签定义",
                min_args=1, max_args=1,
                arg_types=["label"]
            ),

            # === 变量和赋值 ===
            InstructionSpec(
                opcode=OpCode.DECLARE,
                name="declare",
                category="assignment",
                description="声明局部变量",
                min_args=1, max_args=1,
                arg_types=["var"],
                writes_memory=True
            ),
            InstructionSpec(
                opcode=OpCode.INIT,
                name="init",
                category="assignment",
                description="初始化变量",
                min_args=1, max_args=1,
                arg_types=["var"],
                has_result=True,
                writes_memory=True
            ),
            InstructionSpec(
                opcode=OpCode.ASSIGN,
                name="assign",
                category="assignment",
                description="赋值",
                min_args=1, max_args=1,
                arg_types=["var"],
                writes_memory=True
            ),
            InstructionSpec(
                opcode=OpCode.CALL_ASSIGN,
                name="call_assign",
                category="assignment",
                description="调用并赋值",
                min_args=1, max_args=1,
                arg_types=["expr"],
                has_result=True,
                writes_memory=True
            ),

            # === 函数调用 ===
            InstructionSpec(
                opcode=OpCode.CALL,
                name="call",
                category="call",
                description="函数调用",
                min_args=1, max_args=16,
                arg_types=["var"],
                uses_stack=True
            ),

            # === 表达式 ===
            InstructionSpec(
                opcode=OpCode.EXPR,
                name="expr",
                category="expression",
                description="表达式语句",
                min_args=1, max_args=1,
                arg_types=["expr"],
                reads_memory=True
            ),
            InstructionSpec(
                opcode=OpCode.ERROR,
                name="error",
                category="expression",
                description="错误语句",
                min_args=1, max_args=1,
                arg_types=["expr"],
                terminates=True
            ),

            # === 控制结构 ===
            InstructionSpec(
                opcode=OpCode.IF,
                name="if",
                category="control_struct",
                description="if 条件",
                min_args=1, max_args=1,
                arg_types=["expr"]
            ),
            InstructionSpec(
                opcode=OpCode.THEN,
                name="then",
                category="control_struct",
                description="then 分支",
                min_args=0, max_args=0
            ),
            InstructionSpec(
                opcode=OpCode.ELSE,
                name="else",
                category="control_struct",
                description="else 分支",
                min_args=0, max_args=0
            ),
            InstructionSpec(
                opcode=OpCode.ELSEIF,
                name="elseif",
                category="control_struct",
                description="elseif 分支",
                min_args=1, max_args=1,
                arg_types=["expr"]
            ),
            InstructionSpec(
                opcode=OpCode.WHILE,
                name="while",
                category="control_struct",
                description="while 循环",
                min_args=1, max_args=1,
                arg_types=["expr"]
            ),
            InstructionSpec(
                opcode=OpCode.DO,
                name="do",
                category="control_struct",
                description="do 块开始",
                min_args=0, max_args=0
            ),
            InstructionSpec(
                opcode=OpCode.END,
                name="end",
                category="control_struct",
                description="块结束",
                min_args=0, max_args=0
            ),
            InstructionSpec(
                opcode=OpCode.FOR,
                name="for",
                category="control_struct",
                description="for 循环",
                min_args=1, max_args=1,
                arg_types=["expr"]
            ),
            InstructionSpec(
                opcode=OpCode.REPEAT,
                name="repeat",
                category="control_struct",
                description="repeat 循环开始",
                min_args=0, max_args=0
            ),
            InstructionSpec(
                opcode=OpCode.UNTIL,
                name="until",
                category="control_struct",
                description="until 条件",
                min_args=1, max_args=1,
                arg_types=["expr"],
                updates_pc=True
            ),

            # === 表操作 ===
            InstructionSpec(
                opcode=OpCode.TABLE_NEW,
                name="table_new",
                category="table",
                description="创建表",
                min_args=0, max_args=0,
                has_result=True,
                uses_stack=True
            ),
            InstructionSpec(
                opcode=OpCode.TABLE_SET,
                name="table_set",
                category="table",
                description="设置表元素",
                min_args=0, max_args=0,
                writes_memory=True
            ),
            InstructionSpec(
                opcode=OpCode.TABLE_GET,
                name="table_get",
                category="table",
                description="获取表元素",
                min_args=0, max_args=0,
                has_result=True,
                reads_memory=True
            ),

            # === 函数定义 ===
            InstructionSpec(
                opcode=OpCode.FUNC_DEF,
                name="func_def",
                category="function",
                description="函数定义",
                min_args=1, max_args=16,
                arg_types=["var"]
            ),
            InstructionSpec(
                opcode=OpCode.FUNC_END,
                name="func_end",
                category="function",
                description="函数结束",
                min_args=0, max_args=0
            ),

            # === 辅助指令 ===
            InstructionSpec(
                opcode=OpCode.IDENTITY,
                name="identity",
                category="auxiliary",
                description="恒等变换",
                min_args=1, max_args=1,
                arg_types=["var"],
                reads_memory=True,
                writes_memory=True
            ),
            InstructionSpec(
                opcode=OpCode.DUMMY,
                name="dummy",
                category="auxiliary",
                description="哑操作",
                min_args=0, max_args=0
            ),

            # === 特殊 ===
            InstructionSpec(
                opcode=OpCode.COMMENT,
                name="comment",
                category="special",
                description="注释",
                min_args=1, max_args=1,
                arg_types=["expr"]
            ),
            InstructionSpec(
                opcode=OpCode.ASSERT,
                name="assert",
                category="special",
                description="断言",
                min_args=1, max_args=16,
                arg_types=["expr"]
            ),
        ]

        for spec in specs:
            InstructionTable.register(spec)
            self.spec_table[spec.opcode] = spec

    def _init_descriptors(self) -> None:
        """初始化指令描述符（将规格与处理器关联）"""
        # 从 HandlerMap 获取生成器
        for opcode in self.spec_table:
            spec = self.spec_table[opcode]
            handler = self._get_handler(opcode)
            generator = self._get_generator(opcode)
            self.descriptors[opcode] = InstructionDescriptor(spec, handler, generator)

    def _get_handler(self, opcode: OpCode) -> callable:
        """获取处理器函数"""
        # 默认处理器实现
        def default_handler(ctx: VMContext, instr: Instruction) -> PCNext:
            return PCNext.continue_()

        handlers = {
            OpCode.NOP: lambda c, i: PCNext.continue_(),
            OpCode.DECLARE: lambda c, i: (c.set_local(i.args[0], None) if i.args else None, PCNext.continue_())[1],
            OpCode.INIT: lambda c, i: (c.set_local(i.args[0], self._eval(i.result, c)) if i.args else None, PCNext.continue_())[1],
            OpCode.ASSIGN: lambda c, i: (c.set_value(i.args[0], self._eval(i.result, c)) if i.args else None, PCNext.continue_())[1],
            OpCode.RETURN: lambda c, i: (setattr(c, 'return_value', None), c.halt(), PCNext.halt())[2],
            OpCode.RETURN_VAL: lambda c, i: (setattr(c, 'return_value', self._eval(i.args[0], c) if i.args else None), c.halt(), PCNext.halt())[2],
            OpCode.JUMP: lambda c, i: self._do_jump(c, i),
            OpCode.JUMP_IF: lambda c, i: self._do_jump_if(c, i),
            OpCode.LABEL: lambda c, i: (c.add_label(str(i.args[0]), c.pc) if i.args else None, PCNext.continue_())[1],
            OpCode.BREAK: lambda c, i: PCNext.break_(),
            OpCode.CONTINUE: lambda c, i: PCNext.skip(-1),
            OpCode.EXPR: lambda c, i: (self._eval(i.args[0], c) if i.args else None, PCNext.continue_())[1],
            OpCode.ERROR: lambda c, i: (setattr(c, 'return_value', f"error: {i.args[0] if i.args else ''}"), c.halt(), PCNext.halt())[2],
            OpCode.IDENTITY: lambda c, i: (c.set_local(i.args[0], c.get(i.args[0])) if i.args else None, PCNext.continue_())[1],
            OpCode.DUMMY: lambda c, i: PCNext.continue_(),
            OpCode.TABLE_NEW: lambda c, i: (c.push({}), PCNext.continue_())[1],
            OpCode.IF: lambda c, i: (c.set_local("_cond", self._is_truthy(self._eval(i.args[0], c))) if i.args else None, PCNext.continue_())[1],
            OpCode.WHILE: lambda c, i: (c.set_local("_while_cond", self._is_truthy(self._eval(i.args[0], c))) if i.args else None, PCNext.continue_())[1],
            OpCode.REPEAT: lambda c, i: (c.set_local("_repeat_active", True), PCNext.continue_())[1],
            OpCode.UNTIL: lambda c, i: self._do_until(c, i),
            OpCode.CALL: lambda c, i: (self._do_call(c, i), PCNext.continue_())[1],
            OpCode.CALL_ASSIGN: lambda c, i: (c.set_local(i.result, self._eval(i.args[0], c)) if i.result and i.args else None, PCNext.continue_())[1],
        }

        return handlers.get(opcode, default_handler)

    def _get_generator(self, opcode: OpCode) -> callable | None:
        """从 HandlerMap 获取生成器"""
        return HandlerMap.get_generator(opcode)

    def _eval(self, expr: str | None, ctx: VMContext) -> Any:
        """表达式求值"""
        if expr is None:
            return None
        expr = str(expr).strip()
        if not expr:
            return None

        # 字符串字面量
        if (expr.startswith('"') and expr.endswith('"')) or \
           (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]

        # 数字字面量
        try:
            if "." in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass

        # 布尔和 nil
        if expr == "nil":
            return None
        if expr == "true":
            return True
        if expr == "false":
            return False

        # 变量引用
        return ctx.get(expr)

    def _is_truthy(self, value: Any) -> bool:
        """真值判断"""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        if isinstance(value, (list, dict, tuple)):
            return len(value) > 0
        return True

    def _do_jump(self, ctx: VMContext, instr: Instruction) -> PCNext:
        """执行跳转"""
        if instr.args:
            target = instr.args[0]
            if isinstance(target, int):
                return PCNext.jump(target)
            label_pc = ctx.get_label(str(target))
            if label_pc is not None:
                return PCNext.jump(label_pc)
        return PCNext.continue_()

    def _do_jump_if(self, ctx: VMContext, instr: Instruction) -> PCNext:
        """执行条件跳转"""
        if len(instr.args) >= 2:
            cond = self._eval(instr.args[0], ctx)
            if self._is_truthy(cond):
                return self._do_jump(ctx, Instruction(OpCode.JUMP, instr.args[1:]))
        return PCNext.continue_()

    def _do_until(self, ctx: VMContext, instr: Instruction) -> PCNext:
        """执行 until"""
        if instr.args:
            cond = self._eval(instr.args[0], ctx)
            if self._is_truthy(cond):
                ctx.set_local("_repeat_active", False)
                return PCNext.continue_()
            return PCNext.jump(ctx.pc - 1)
        return PCNext.continue_()

    def _do_call(self, ctx: VMContext, instr: Instruction) -> Any:
        """执行函数调用"""
        if instr.args:
            func_name = instr.args[0]
            args = [self._eval(a, ctx) for a in instr.args[1:]]
            func = ctx.get(func_name)
            if callable(func):
                return func(*args)
            ctx.push(None)

    def register_handler(self, opcode: OpCode, handler: callable) -> None:
        """注册处理器"""
        if opcode in self.descriptors:
            self.descriptors[opcode] = InstructionDescriptor(
                self.descriptors[opcode].spec,
                handler,
                self.descriptors[opcode].generator
            )
        else:
            spec = self.spec_table.get(opcode)
            if spec:
                self.descriptors[opcode] = InstructionDescriptor(spec, handler, None)

    def execute(self, instructions: list[Instruction], debug: bool = False) -> VMResult:
        """
        表驱动执行

        核心循环完全由表驱动：
        1. 查表获取规格
        2. 查表获取描述符
        3. 执行描述符中的处理器
        """
        self.instructions = instructions
        self.context = VMContext()
        debug = debug or self.debug

        if debug:
            print(f"[TableDrivenVM] Starting with {len(instructions)} instructions")
            print(f"  Categories: {InstructionTable.get_all_categories()}")

        executed = 0
        pc = 0

        # === 表驱动执行循环 ===
        while pc < len(self.instructions) and self.context.running:
            instr = self.instructions[pc]
            ctx = self.context
            ctx.pc = pc

            # 1. 查表获取规格
            spec = self.spec_table.get(instr.op)

            if debug:
                spec_info = f"[{spec.name}]" if spec else "[unknown]"
                print(f"  PC={pc}: {spec_info} {instr.args} -> {instr.result}")

            # 2. 严格模式下验证
            if self.strict_mode and spec:
                valid, msg = InstructionTable.validate(instr)
                if not valid:
                    return VMResult(
                        success=False,
                        error=f"Validation failed at PC={pc}: {msg}",
                        pc=pc,
                        executed_count=executed,
                        context=ctx
                    )

            # 3. 查表获取描述符
            descriptor = self.descriptors.get(instr.op)

            if descriptor:
                try:
                    # 4. 执行处理器
                    pc_next = descriptor.execute(ctx, instr)

                    # 5. 处理 PC 更新
                    pc = self._advance_pc(pc, pc_next)

                except Exception as e:
                    return VMResult(
                        success=False,
                        error=f"Execution error at PC={pc}: {e}",
                        pc=pc,
                        executed_count=executed,
                        context=ctx
                    )
            else:
                if debug:
                    print(f"    No handler for {instr.op.value}")
                pc += 1

            executed += 1

            # 防止无限循环
            if executed > self.max_instructions:
                return VMResult(
                    success=False,
                    error="Execution limit exceeded",
                    pc=pc,
                    executed_count=executed,
                    context=ctx
                )

        if debug:
            print(f"[TableDrivenVM] Finished: pc={pc}, executed={executed}")

        return VMResult(
            success=True,
            return_value=ctx.return_value,
            pc=pc,
            executed_count=executed,
            context=ctx
        )

    def _advance_pc(self, pc: int, pc_next: PCNext) -> int:
        """根据 PCNext 更新程序计数器"""
        if pc_next.action == PCNext.NEXT:
            return pc + 1
        elif pc_next.action == PCNext.JUMP:
            if pc_next.target == 0:
                return pc + 1
            elif pc_next.target > 0:
                return pc_next.target
            else:
                return pc + pc_next.target
        elif pc_next.action == PCNext.BREAK:
            return len(self.instructions)  # 结束
        elif pc_next.action == PCNext.HALT:
            return len(self.instructions)  # 结束
        return pc + 1

    def execute_from_block(self, block: CodeBlock, debug: bool = False) -> VMResult:
        """从 CodeBlock 执行"""
        converter = InstructionConverter()
        block_instr = converter.convert_block(block)
        return self.execute(block_instr.instructions, debug=debug)

    def get_spec_info(self) -> str:
        """获取指令表信息"""
        lines = ["Instruction Table:"]
        for category in InstructionTable.get_all_categories():
            lines.append(f"  [{category}]")
            for opcode in InstructionTable.get_by_category(category):
                spec = InstructionTable.get(opcode)
                if spec:
                    lines.append(f"    {spec.name}: {spec.description}")
        return "\n".join(lines)


def table_driven_vm_test():
    """
    表驱动执行器测试

    展示表驱动模型的优势。
    """
    print("=" * 50)
    print("Table-Driven Executor Test")
    print("=" * 50)

    # 创建执行器
    vm = TableDrivenExecutor(debug=False)

    # 显示指令表
    print("\n[Test 0] Instruction Table Info")
    print(vm.get_spec_info())

    # 测试 1: 基本执行
    print("\n[Test 1] Basic execution")
    instrs = [
        Instruction(OpCode.INIT, ["a"], None, "10"),
        Instruction(OpCode.INIT, ["b"], None, "20"),
        Instruction(OpCode.ASSIGN, ["a"], "a + b"),
        Instruction(OpCode.RETURN_VAL, ["a"]),
    ]
    result = vm.execute(instrs)
    print(f"  Expected: 30, Got: {result.return_value}, Success: {result.success}")

    # 测试 2: 标签跳转
    print("\n[Test 2] Label and jump")
    instrs2 = [
        Instruction(OpCode.LABEL, ["start"]),
        Instruction(OpCode.INIT, ["i"], None, "0"),
        Instruction(OpCode.ASSIGN, ["i"], "i + 1"),
        Instruction(OpCode.JUMP_IF, ["i < 3", "start"]),
        Instruction(OpCode.RETURN_VAL, ["i"]),
    ]
    result2 = vm.execute(instrs2, debug=True)
    print(f"  Expected: 3, Got: {result2.return_value}")

    # 测试 3: 条件执行
    print("\n[Test 3] Conditional execution")
    instrs3 = [
        Instruction(OpCode.INIT, ["x"], None, "10"),
        Instruction(OpCode.JUMP_IF, ["x > 5", 5]),  # 跳过赋值
        Instruction(OpCode.ASSIGN, ["x"], "100"),
        Instruction(OpCode.RETURN_VAL, ["x"]),
    ]
    result3 = vm.execute(instrs3)
    print(f"  Expected: 10 (skipped), Got: {result3.return_value}")

    # 测试 4: 恒等变换
    print("\n[Test 4] Identity transformation")
    instrs4 = [
        Instruction(OpCode.INIT, ["y"], None, "42"),
        Instruction(OpCode.IDENTITY, ["y"]),
        Instruction(OpCode.RETURN_VAL, ["y"]),
    ]
    result4 = vm.execute(instrs4)
    print(f"  Expected: 42, Got: {result4.return_value}, Success: {result4.success}")

    # 测试 5: 从 Block 执行
    print("\n[Test 5] Execute from Block")
    block = CodeBlock(
        block_id=1,
        content="local a = 5\nlocal b = 10\nreturn a * b",
        block_type="statement"
    )
    result5 = vm.execute_from_block(block)
    print(f"  Expected: 50, Got: {result5.return_value}, Success: {result5.success}")

    # 测试 6: 注册自定义处理器
    print("\n[Test 6] Custom handler registration")
    vm2 = TableDrivenExecutor()

    def custom_nop_handler(ctx: VMContext, instr: Instruction) -> PCNext:
        print("    [Custom NOP handler]")
        return PCNext.continue_()

    vm2.register_handler(OpCode.NOP, custom_nop_handler)

    instrs6 = [
        Instruction(OpCode.NOP),
        Instruction(OpCode.RETURN_VAL, ["42"]),
    ]
    result6 = vm2.execute(instrs6, debug=True)
    print(f"  Got: {result6.return_value}")

    print("\n" + "=" * 50)
    print("Table-Driven VM Test Complete")
    print("=" * 50)


def vm_test():
    """
    标准解释器测试

    展示标准 VM 的执行流程。
    """
    print("=" * 50)
    print("Standard Interpreter VM Test")
    print("=" * 50)

    vm = InstructionVM(debug=False)

    # 测试 1: 简单变量赋值
    print("\n[Test 1] Variable assignment")
    instrs = [
        Instruction(OpCode.INIT, ["a"], None, "10"),
        Instruction(OpCode.INIT, ["b"], None, "20"),
        Instruction(OpCode.ASSIGN, ["a"], "a + b"),
        Instruction(OpCode.RETURN_VAL, ["a"]),
    ]
    result = vm.execute(instrs)
    print(f"  Expected: 30, Got: {result.return_value}, Success: {result.success}")

    # 测试 2: 带调试的执行
    print("\n[Test 2] Debug execution")
    instrs2 = [
        Instruction(OpCode.INIT, ["x"], None, "5"),
        Instruction(OpCode.INIT, ["y"], None, "10"),
        Instruction(OpCode.ASSIGN, ["result"], "x * y"),
        Instruction(OpCode.RETURN_VAL, ["result"]),
    ]
    print("  Instructions trace:")
    result2 = vm.execute(instrs2, debug=True)
    print(f"  Result: {result2.return_value}")

    # 测试 3: 条件跳转
    print("\n[Test 3] Conditional jump")
    instrs3 = [
        Instruction(OpCode.INIT, ["x"], None, "10"),
        Instruction(OpCode.JUMP_IF, ["x", "5"]),  # 如果 x 为真，跳到位置 5
        Instruction(OpCode.ASSIGN, ["x"], "100"),  # 跳过
        Instruction(OpCode.RETURN_VAL, ["x"]),
        Instruction(OpCode.ASSIGN, ["x"], "999"),   # 跳转目标
        Instruction(OpCode.RETURN_VAL, ["x"]),
    ]
    result3 = vm.execute(instrs3)
    print(f"  Expected: 10 (jump taken), Got: {result3.return_value}")

    # 测试 4: 标签和跳转
    print("\n[Test 4] Label and jump")
    instrs4 = [
        Instruction(OpCode.LABEL, ["start"]),
        Instruction(OpCode.INIT, ["counter"], None, "0"),
        Instruction(OpCode.ASSIGN, ["counter"], "counter + 1"),
        Instruction(OpCode.JUMP_IF, ["counter < 3", "start"]),
        Instruction(OpCode.RETURN_VAL, ["counter"]),
    ]
    result4 = vm.execute(instrs4)
    print(f"  Expected: 3, Got: {result4.return_value}")

    # 测试 5: 从 CodeBlock 执行
    print("\n[Test 5] Execute from CodeBlock")
    block = CodeBlock(
        block_id=1,
        content="local a = 10\nlocal b = 20\na = a + b\nreturn a",
        block_type="statement"
    )
    result5 = vm.execute_from_block(block)
    print(f"  Expected: 30, Got: {result5.return_value}, Success: {result5.success}")

    # 测试 6: 恒等变换（不影响结果）
    print("\n[Test 6] Identity transformation")
    instrs6 = [
        Instruction(OpCode.INIT, ["x"], None, "42"),
        Instruction(OpCode.IDENTITY, ["x"]),
        Instruction(OpCode.IDENTITY, ["x"]),
        Instruction(OpCode.RETURN_VAL, ["x"]),
    ]
    result6 = vm.execute(instrs6)
    print(f"  Expected: 42, Got: {result6.return_value}, Success: {result6.success}")

    print("\n" + "=" * 50)
    print("VM Test Complete")
    print("=" * 50)


# ===== 指令处理器基类和注册系统 =====


class InstructionHandler:
    """
    指令处理器基类

    所有指令处理器都继承此类，便于扩展和管理。
    """

    opcode: OpCode = None

    def handle(self, instr: Instruction, context: ExecutionContext) -> dict:
        """
        处理指令

        Args:
            instr: 指令
            context: 执行上下文

        Returns:
            控制流指令可能返回 {"pc": new_pc} 或 {"return": True}
            其他返回 {}
        """
        raise NotImplementedError

    def generate(self, instr: Instruction) -> str:
        """
        生成代码

        Args:
            instr: 指令

        Returns:
            Lua 代码字符串
        """
        raise NotImplementedError


class NopHandler(InstructionHandler):
    """空操作处理器"""
    opcode = OpCode.NOP

    def handle(self, instr: Instruction, context: ExecutionContext) -> dict:
        return {}

    def generate(self, instr: Instruction) -> str:
        return "do end"


class DeclareHandler(InstructionHandler):
    """变量声明处理器"""
    opcode = OpCode.DECLARE

    def handle(self, instr: Instruction, context: ExecutionContext) -> dict:
        if instr.args:
            context.set_local(instr.args[0], None)
        return {}

    def generate(self, instr: Instruction) -> str:
        var = instr.args[0] if instr.args else "_"
        return f"local {var}"


class InitHandler(InstructionHandler):
    """变量初始化处理器"""
    opcode = OpCode.INIT

    def handle(self, instr: Instruction, context: ExecutionContext) -> dict:
        if instr.args:
            var_name = instr.args[0]
            value = self._eval(context, instr.result)
            context.set_local(var_name, value)
        return {}

    def generate(self, instr: Instruction) -> str:
        var = instr.args[0] if instr.args else "_"
        val = instr.result or ""
        return f"local {var} = {val}"

    def _eval(self, context, expr: str) -> Any:
        if expr is None:
            return None
        expr = str(expr).strip()
        try:
            if "." in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass
        if expr in ("true", "false", "nil"):
            return {"true": True, "false": False, "nil": None}[expr]
        return context.resolve_value(expr) if hasattr(context, "resolve_value") else None


class AssignHandler(InstructionHandler):
    """赋值处理器"""
    opcode = OpCode.ASSIGN

    def handle(self, instr: Instruction, context: ExecutionContext) -> dict:
        if instr.args:
            var_name = instr.args[0]
            value = self._eval(context, instr.result)
            context.set_value(var_name, value)
        return {}

    def generate(self, instr: Instruction) -> str:
        target = instr.args[0] if instr.args else "_"
        return f"{target} = {instr.result or ''}"

    def _eval(self, context, expr: str) -> Any:
        if expr is None:
            return None
        expr = str(expr).strip()
        try:
            if "." in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass
        if expr in ("true", "false", "nil"):
            return {"true": True, "false": False, "nil": None}[expr]
        return context.resolve_value(expr) if hasattr(context, "resolve_value") else None


class CallHandler(InstructionHandler):
    """函数调用处理器"""
    opcode = OpCode.CALL

    def handle(self, instr: Instruction, context: ExecutionContext) -> dict:
        if instr.args:
            func_name = instr.args[0]
            args = [self._eval(context, a) for a in instr.args[1:]]
            func = context.resolve_value(func_name) if hasattr(context, "resolve_value") else None
            if callable(func):
                try:
                    result = func(*args)
                    if hasattr(context, "return_values"):
                        context.return_values.append(result)
                except Exception:
                    pass
        return {}

    def generate(self, instr: Instruction) -> str:
        if not instr.args:
            return "()"
        func = instr.args[0]
        params = ", ".join(str(a) for a in instr.args[1:]) if len(instr.args) > 1 else ""
        return f"{func}({params})"

    def _eval(self, context, expr: str) -> Any:
        if expr is None:
            return None
        expr = str(expr).strip()
        try:
            if "." in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass
        if expr in ("true", "false", "nil"):
            return {"true": True, "false": False, "nil": None}[expr]
        return context.resolve_value(expr) if hasattr(context, "resolve_value") else None


class ReturnHandler(InstructionHandler):
    """返回处理器"""
    opcode = OpCode.RETURN

    def handle(self, instr: Instruction, context: ExecutionContext) -> dict:
        if hasattr(context, "return_values"):
            context.return_values.append(None)
        return {"return": True}

    def generate(self, instr: Instruction) -> str:
        return "return"


class ReturnValHandler(InstructionHandler):
    """返回值处理器"""
    opcode = OpCode.RETURN_VAL

    def handle(self, instr: Instruction, context: ExecutionContext) -> dict:
        if hasattr(context, "return_values") and instr.args:
            value = self._eval(context, instr.args[0])
            context.return_values.append(value)
        return {"return": True}

    def generate(self, instr: Instruction) -> str:
        val = instr.args[0] if instr.args else ""
        return f"return {val}"

    def _eval(self, context, expr: str) -> Any:
        if expr is None:
            return None
        expr = str(expr).strip()
        try:
            if "." in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass
        if expr in ("true", "false", "nil"):
            return {"true": True, "false": False, "nil": None}[expr]
        return context.resolve_value(expr) if hasattr(context, "resolve_value") else None


class IdentityHandler(InstructionHandler):
    """恒等变换处理器（辅助指令）"""
    opcode = OpCode.IDENTITY

    def handle(self, instr: Instruction, context: ExecutionContext) -> dict:
        # 恒等变换不影响执行状态
        return {}

    def generate(self, instr: Instruction) -> str:
        var = instr.args[0] if instr.args else "_x"
        patterns = [
            f"local {var} = {var}",
            f"local {var} = ({var})",
            f"local {var} = 0 + {var}",
            f"local {var} = {var} * 1",
        ]
        return patterns[0]


class DummyHandler(InstructionHandler):
    """哑操作处理器（辅助指令）"""
    opcode = OpCode.DUMMY

    def handle(self, instr: Instruction, context: ExecutionContext) -> dict:
        return {}

    def generate(self, instr: Instruction) -> str:
        return "do end"


class HandlerRegistry:
    """
    指令处理器注册表

    集中管理所有指令处理器。
    """
    _handlers: dict[OpCode, InstructionHandler] = {}

    @classmethod
    def register(cls, handler: InstructionHandler) -> None:
        """注册处理器"""
        if handler.opcode:
            cls._handlers[handler.opcode] = handler

    @classmethod
    def get(cls, opcode: OpCode) -> InstructionHandler | None:
        """获取处理器"""
        return cls._handlers.get(opcode)

    @classmethod
    def get_all(cls) -> dict[OpCode, InstructionHandler]:
        """获取所有处理器"""
        return cls._handlers.copy()


# 注册默认处理器
def _register_default_handlers() -> None:
    """注册默认处理器"""
    HandlerRegistry.register(NopHandler())
    HandlerRegistry.register(DeclareHandler())
    HandlerRegistry.register(InitHandler())
    HandlerRegistry.register(AssignHandler())
    HandlerRegistry.register(CallHandler())
    HandlerRegistry.register(ReturnHandler())
    HandlerRegistry.register(ReturnValHandler())
    HandlerRegistry.register(IdentityHandler())
    HandlerRegistry.register(DummyHandler())


_register_default_handlers()


# ===== 指令表示策略系统 =====


class RepresentationStrategy:
    """
    指令表示策略基类

    定义同一语义的多种等价格式表示方式。
    """

    name: str = "base"
    description: str = ""

    def generate(self, ctx: 'GenerationContext') -> list[Instruction]:
        """
        生成指令序列

        Args:
            ctx: 生成上下文

        Returns:
            生成的指令列表
        """
        raise NotImplementedError


class GenerationContext:
    """
    指令生成上下文

    包含生成过程中需要的各种信息和工具。
    """

    def __init__(
        self,
        rng: random.Random | None = None,
        strategy_name: str = "default",
        block_id: int = 0,
        metadata: dict | None = None
    ):
        self.rng = rng
        self.strategy_name = strategy_name
        self.block_id = block_id
        self.metadata = metadata or {}
        self._temp_counter = 0
        self._label_counter = 0

    def new_temp(self, prefix: str = "_t") -> str:
        """生成临时变量名"""
        self._temp_counter += 1
        return f"{prefix}{self._temp_counter}"

    def new_label(self, prefix: str = "L") -> str:
        """生成标签名"""
        self._label_counter += 1
        return f"{prefix}{self._label_counter}"

    def choice(self, options: list) -> Any:
        """随机选择"""
        if self.rng:
            return self.rng.choice(options)
        return options[0] if options else None

    def probability(self, p: float) -> bool:
        """按概率返回"""
        if self.rng:
            return self.rng.random() < p
        return p >= 1.0


class StrategyRegistry:
    """
    策略注册表

    管理所有可用的表示策略。
    """

    _strategies: dict[str, type[RepresentationStrategy]] = {}
    _factories: dict[str, Callable] = {}

    @classmethod
    def register(
        cls,
        name: str,
        strategy_cls: type[RepresentationStrategy],
        factory: Callable | None = None
    ) -> None:
        """注册策略"""
        cls._strategies[name] = strategy_cls
        if factory:
            cls._factories[name] = factory
        else:
            cls._factories[name] = lambda rng: strategy_cls()

    @classmethod
    def get(cls, name: str) -> type[RepresentationStrategy] | None:
        """获取策略类"""
        return cls._strategies.get(name)

    @classmethod
    def create(cls, name: str, rng: random.Random | None = None) -> RepresentationStrategy | None:
        """创建策略实例"""
        factory = cls._factories.get(name)
        if factory:
            return factory(rng)
        strategy_cls = cls._strategies.get(name)
        if strategy_cls:
            return strategy_cls()
        return None

    @classmethod
    def get_all(cls) -> list[str]:
        """获取所有策略名"""
        return list(cls._strategies.keys())

    @classmethod
    def get_descriptions(cls) -> dict[str, str]:
        """获取所有策略描述"""
        return {name: cls._strategies[name].description for name in cls._strategies}


# ===== 等价表示方式定义 =====

# 赋值表示策略
class DirectAssignStrategy(RepresentationStrategy):
    """直接赋值策略: local x = value"""
    name = "direct"
    description = "直接赋值，不使用临时变量"

    def generate(self, ctx: GenerationContext) -> list[Instruction]:
        # 子类实现
        return []


class TempVarAssignStrategy(RepresentationStrategy):
    """临时变量赋值策略: local _t1 = value; x = _t1"""
    name = "temp_var"
    description = "使用临时变量分步赋值"

    def generate(self, ctx: GenerationContext) -> list[Instruction]:
        return []


class StackBasedAssignStrategy(RepresentationStrategy):
    """栈式赋值策略: push value; x = pop()"""
    name = "stack_based"
    description = "使用栈进行赋值"

    def generate(self, ctx: GenerationContext) -> list[Instruction]:
        return []


# 计算表示策略
class InlineCalcStrategy(RepresentationStrategy):
    """内联计算策略: x = a + b"""
    name = "inline"
    description = "表达式直接内联"

    def generate(self, ctx: GenerationContext) -> list[Instruction]:
        return []


class MultiStepCalcStrategy(RepresentationStrategy):
    """多步计算策略: _t1 = a + b; _t2 = _t1 * c; x = _t2"""
    name = "multi_step"
    description = "分解为多个步骤"

    def generate(self, ctx: GenerationContext) -> list[Instruction]:
        return []


# 跳转表示策略
class LabelJumpStrategy(RepresentationStrategy):
    """标签跳转策略: L1: ...; goto L1"""
    name = "label_jump"
    description = "使用标签进行跳转"

    def generate(self, ctx: GenerationContext) -> list[Instruction]:
        return []


class OffsetJumpStrategy(RepresentationStrategy):
    """偏移跳转策略: 使用 PC 偏移量"""
    name = "offset_jump"
    description = "使用 PC 偏移量跳转"

    def generate(self, ctx: GenerationContext) -> list[Instruction]:
        return []


# 条件表示策略
class IfThenEndStrategy(RepresentationStrategy):
    """标准 if-then-end 策略"""
    name = "if_then_end"
    description = "标准 if-then-end 结构"

    def generate(self, ctx: GenerationContext) -> list[Instruction]:
        return []


class SkipOverStrategy(RepresentationStrategy):
    """跳过策略: 先执行条件，false 时跳过"""
    name = "skip_over"
    description = "使用跳过实现条件"

    def generate(self, ctx: GenerationContext) -> list[Instruction]:
        return []


# 循环表示策略
class WhileDoEndStrategy(RepresentationStrategy):
    """标准 while-do-end 策略"""
    name = "while_do_end"
    description = "标准 while 循环"

    def generate(self, ctx: GenerationContext) -> list[Instruction]:
        return []


class RepeatUntilStrategy(RepresentationStrategy):
    """repeat-until 策略"""
    name = "repeat_until"
    description = "使用 repeat-until 实现循环"

    def generate(self, ctx: GenerationContext) -> list[Instruction]:
        return []


class JumpBasedLoopStrategy(RepresentationStrategy):
    """跳转实现循环策略"""
    name = "jump_based_loop"
    description = "使用跳转实现循环"

    def generate(self, ctx: GenerationContext) -> list[Instruction]:
        return []


# 注册所有策略
def _register_default_strategies() -> None:
    """注册默认表示策略"""

    # 赋值策略
    StrategyRegistry.register("direct", DirectAssignStrategy)
    StrategyRegistry.register("temp_var", TempVarAssignStrategy)
    StrategyRegistry.register("stack_based", StackBasedAssignStrategy)

    # 计算策略
    StrategyRegistry.register("inline", InlineCalcStrategy)
    StrategyRegistry.register("multi_step", MultiStepCalcStrategy)

    # 跳转策略
    StrategyRegistry.register("label_jump", LabelJumpStrategy)
    StrategyRegistry.register("offset_jump", OffsetJumpStrategy)

    # 条件策略
    StrategyRegistry.register("if_then_end", IfThenEndStrategy)
    StrategyRegistry.register("skip_over", SkipOverStrategy)

    # 循环策略
    StrategyRegistry.register("while_do_end", WhileDoEndStrategy)
    StrategyRegistry.register("repeat_until", RepeatUntilStrategy)
    StrategyRegistry.register("jump_based_loop", JumpBasedLoopStrategy)


_register_default_strategies()


class StrategySelector:
    """
    策略选择器

    根据配置选择合适的表示策略。
    """

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng
        self._strategy_weights: dict[str, float] = {}
        self._default_strategy = "direct"

    def set_weights(self, weights: dict[str, float]) -> None:
        """设置策略权重"""
        self._strategy_weights = weights

    def set_default(self, strategy: str) -> None:
        """设置默认策略"""
        self._default_strategy = strategy

    def select_for_operation(
        self,
        operation: str,
        context: GenerationContext
    ) -> str:
        """
        为操作选择策略

        Args:
            operation: 操作类型 (assign, calc, jump, condition, loop)
            context: 生成上下文

        Returns:
            选择的策略名
        """
        # 按操作类型分组策略
        operation_strategies = {
            "assign": ["direct", "temp_var", "stack_based"],
            "calc": ["inline", "multi_step"],
            "jump": ["label_jump", "offset_jump"],
            "condition": ["if_then_end", "skip_over"],
            "loop": ["while_do_end", "repeat_until", "jump_based_loop"],
        }

        strategies = operation_strategies.get(operation, [self._default_strategy])

        # 使用权重或随机选择
        if self._strategy_weights:
            available = {s: self._strategy_weights.get(s, 1.0) for s in strategies}
            total = sum(available.values())
            if total > 0 and self.rng:
                r = self.rng.random() * total
                cumulative = 0
                for s, w in available.items():
                    cumulative += w
                    if r <= cumulative:
                        return s
            return strategies[0]

        if self.rng:
            return self.rng.choice(strategies)
        return strategies[0]


class InstructionGeneratorWithStrategy:
    """
    支持策略的指令生成器

    可以根据策略生成不同表示方式的指令。
    """

    def __init__(
        self,
        rng: random.Random | None = None,
        strategy_selector: StrategySelector | None = None
    ):
        self.rng = rng
        self.selector = strategy_selector or StrategySelector(rng)

    def generate_assignment(
        self,
        target: str,
        value: str,
        context: GenerationContext | None = None
    ) -> list[Instruction]:
        """生成赋值指令"""
        if context is None:
            context = GenerationContext(self.rng)

        strategy = self.selector.select_for_operation("assign", context)

        if strategy == "temp_var":
            temp = context.new_temp()
            return [
                Instruction(OpCode.DECLARE, [temp]),
                Instruction(OpCode.INIT, [temp], result=value),
                Instruction(OpCode.ASSIGN, [target], temp),
            ]
        elif strategy == "stack_based":
            return [
                Instruction(OpCode.TABLE_NEW),  # 模拟 push
                Instruction(OpCode.INIT, [target], result=value),
            ]
        else:  # direct
            return [Instruction(OpCode.INIT, [target], result=value)]

    def generate_calculation(
        self,
        target: str,
        expr: str,
        context: GenerationContext | None = None
    ) -> list[Instruction]:
        """生成计算指令"""
        if context is None:
            context = GenerationContext(self.rng)

        strategy = self.selector.select_for_operation("calc", context)

        if strategy == "multi_step":
            temp = context.new_temp()
            return [
                Instruction(OpCode.DECLARE, [temp]),
                Instruction(OpCode.INIT, [temp], result=expr),
                Instruction(OpCode.ASSIGN, [target], temp),
            ]
        else:  # inline
            return [Instruction(OpCode.ASSIGN, [target], result=expr)]

    def generate_jump(
        self,
        target: int | str,
        context: GenerationContext | None = None
    ) -> list[Instruction]:
        """生成跳转指令"""
        if context is None:
            context = GenerationContext(self.rng)

        strategy = self.selector.select_for_operation("jump", context)

        if strategy == "label_jump":
            if isinstance(target, str):
                return [Instruction(OpCode.LABEL, [target])]
            else:
                label = context.new_label()
                return [
                    Instruction(OpCode.LABEL, [label]),
                    Instruction(OpCode.JUMP, [label]),
                ]
        else:  # offset_jump
            return [Instruction(OpCode.JUMP, [target])]

    def generate_condition(
        self,
        cond: str,
        true_body: list[Instruction],
        context: GenerationContext | None = None
    ) -> list[Instruction]:
        """生成条件指令"""
        if context is None:
            context = GenerationContext(self.rng)

        strategy = self.selector.select_for_operation("condition", context)

        if strategy == "skip_over":
            else_label = context.new_label()
            end_label = context.new_label()
            result = [
                Instruction(OpCode.JUMP_IF, [f"not ({cond})", else_label]),
            ]
            result.extend(true_body)
            result.append(Instruction(OpCode.JUMP, [end_label]))
            result.append(Instruction(OpCode.LABEL, [else_label]))
            result.append(Instruction(OpCode.NOP))
            result.append(Instruction(OpCode.LABEL, [end_label]))
            return result
        else:  # if_then_end
            result = [
                Instruction(OpCode.IF, [cond]),
                Instruction(OpCode.THEN),
            ]
            result.extend(true_body)
            result.append(Instruction(OpCode.END))
            return result

    def generate_loop(
        self,
        cond: str,
        body: list[Instruction],
        loop_type: str = "while",
        context: GenerationContext | None = None
    ) -> list[Instruction]:
        """生成循环指令"""
        if context is None:
            context = GenerationContext(self.rng)

        strategy = self.selector.select_for_operation("loop", context)

        if strategy == "jump_based_loop":
            start_label = context.new_label()
            end_label = context.new_label()
            result = [
                Instruction(OpCode.LABEL, [start_label]),
            ]
            result.extend(body)
            result.append(Instruction(OpCode.JUMP_IF, [f"not ({cond})", end_label]))
            result.append(Instruction(OpCode.JUMP, [start_label]))
            result.append(Instruction(OpCode.LABEL, [end_label]))
            return result
        elif strategy == "repeat_until":
            result = [
                Instruction(OpCode.REPEAT),
            ]
            result.extend(body)
            result.append(Instruction(OpCode.UNTIL, [cond]))
            return result
        else:  # while_do_end
            result = [
                Instruction(OpCode.WHILE, [cond]),
                Instruction(OpCode.DO),
            ]
            result.extend(body)
            result.append(Instruction(OpCode.END))
            return result


class BlockStrategyApplicator:
    """
    Block 策略应用器

    将策略应用到 CodeBlock，生成不同表示的指令。
    """

    def __init__(
        self,
        rng: random.Random | None = None,
        strategy_name: str = "random"
    ):
        self.rng = rng
        self.strategy_name = strategy_name
        self.generator = InstructionGeneratorWithStrategy(rng)

    def apply_to_block(self, block: CodeBlock) -> BlockInstructions:
        """将策略应用到 Block"""
        context = GenerationContext(
            rng=self.rng,
            strategy_name=self.strategy_name,
            block_id=block.block_id
        )

        result = BlockInstructions(
            block_id=block.block_id,
            block_type=block.block_type,
        )

        if not block.content:
            result.add_nop()
            return result

        lines = block.content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 使用策略生成器处理每一行
            instrs = self._generate_line(line, context)
            for instr in instrs:
                result.add(instr)

        if len(result.instructions) == 0:
            result.add_nop()

        return result

    def _generate_line(self, line: str, context: GenerationContext) -> list[Instruction]:
        """使用策略生成单行代码的指令"""
        # 移除注释
        code_part = line
        if "--" in line:
            code_part = line.split("--")[0].strip()

        if not code_part:
            return [Instruction(OpCode.COMMENT, [line])]

        # 根据代码类型选择生成方式
        if code_part.startswith("local "):
            return self._generate_local(code_part, context)
        elif "=" in code_part and not code_part.startswith("if"):
            return self._generate_assignment(code_part, context)
        elif code_part.startswith("if"):
            return self._generate_if(code_part, context)
        elif code_part.startswith("while"):
            return self._generate_while(code_part, context)
        elif code_part.startswith("return"):
            return self._generate_return(code_part, context)
        else:
            return [Instruction(OpCode.EXPR, [code_part])]

    def _generate_local(self, line: str, ctx: GenerationContext) -> list[Instruction]:
        """生成 local 声明/赋值"""
        rest = line[6:].strip()  # 移除 "local "
        if "=" in rest:
            parts = rest.split("=", 1)
            var_name = parts[0].strip()
            value = parts[1].strip()
            return self.generator.generate_assignment(var_name, value, ctx)
        else:
            return [Instruction(OpCode.DECLARE, [rest])]

    def _generate_assignment(self, line: str, ctx: GenerationContext) -> list[Instruction]:
        """生成赋值"""
        parts = line.split("=", 1)
        target = parts[0].strip()
        value = parts[1].strip()
        return self.generator.generate_calculation(target, value, ctx)

    def _generate_if(self, line: str, ctx: GenerationContext) -> list[Instruction]:
        """生成 if 语句"""
        # 简单处理，提取条件
        cond = line[3:].strip()  # 移除 "if "
        if " then" in cond:
            cond = cond[:-5].strip()

        # 生成条件块
        body = [Instruction(OpCode.EXPR, ["-- body"])]  # 简化处理
        return self.generator.generate_condition(cond, body, ctx)

    def _generate_while(self, line: str, ctx: GenerationContext) -> list[Instruction]:
        """生成 while 循环"""
        # 简单处理，提取条件
        cond = line[6:].strip()  # 移除 "while "
        if " do" in cond:
            cond = cond[:-3].strip()

        body = [Instruction(OpCode.EXPR, ["-- body"])]  # 简化处理
        return self.generator.generate_loop(cond, body, "while", ctx)

    def _generate_return(self, line: str, ctx: GenerationContext) -> list[Instruction]:
        """生成 return"""
        rest = line[6:].strip()  # 移除 "return "
        if rest:
            return [Instruction(OpCode.RETURN_VAL, [rest])]
        return [Instruction(OpCode.RETURN)]


# 简化测试函数
def strategy_test():
    """
    表示策略测试

    展示不同策略生成的指令差异。
    """
    import random

    print("=" * 50)
    print("Instruction Representation Strategy Test")
    print("=" * 50)

    rng = random.Random(42)
    selector = StrategySelector(rng)
    generator = InstructionGeneratorWithStrategy(rng, selector)

    # 测试赋值策略
    print("\n[Test 1] Assignment strategies")
    strategies = ["direct", "temp_var", "stack_based"]

    for strategy in strategies:
        ctx = GenerationContext(rng, strategy_name=strategy)
        instrs = generator.generate_assignment("x", "10 + 20", ctx)
        print(f"\n  [{strategy}]")
        for instr in instrs:
            print(f"    {instr}")

    # 测试计算策略
    print("\n[Test 2] Calculation strategies")
    calc_strategies = ["inline", "multi_step"]

    for strategy in calc_strategies:
        ctx = GenerationContext(rng, strategy_name=strategy)
        instrs = generator.generate_calculation("result", "a + b * c", ctx)
        print(f"\n  [{strategy}]")
        for instr in instrs:
            print(f"    {instr}")

    # 测试跳转策略
    print("\n[Test 3] Jump strategies")
    jump_strategies = ["label_jump", "offset_jump"]

    for strategy in jump_strategies:
        ctx = GenerationContext(rng, strategy_name=strategy)
        instrs = generator.generate_jump(100, ctx)
        print(f"\n  [{strategy}]")
        for instr in instrs:
            print(f"    {instr}")

    # 测试条件策略
    print("\n[Test 4] Condition strategies")
    cond_strategies = ["if_then_end", "skip_over"]

    for strategy in cond_strategies:
        ctx = GenerationContext(rng, strategy_name=strategy)
        body = [Instruction(OpCode.ASSIGN, ["x"], result="10")]
        instrs = generator.generate_condition("x > 5", body, ctx)
        print(f"\n  [{strategy}]")
        for instr in instrs:
            print(f"    {instr}")

    # 测试循环策略
    print("\n[Test 5] Loop strategies")
    loop_strategies = ["while_do_end", "repeat_until", "jump_based_loop"]

    for strategy in loop_strategies:
        ctx = GenerationContext(rng, strategy_name=strategy)
        body = [Instruction(OpCode.EXPR, ["i = i + 1"])]
        instrs = generator.generate_loop("i < 10", body, "while", ctx)
        print(f"\n  [{strategy}]")
        for instr in instrs:
            print(f"    {instr}")

    # 测试 Block 策略应用
    print("\n[Test 6] Block strategy application")
    block = CodeBlock(
        block_id=1,
        content="local x = 10\nlocal y = 20\nx = x + y\nreturn x",
        block_type="statement"
    )

    applicator = BlockStrategyApplicator(rng, "random")
    result = applicator.apply_to_block(block)
    print("  Generated instructions:")
    for instr in result.instructions:
        print(f"    {instr}")

    print("\n" + "=" * 50)
    print("Strategy Test Complete")
    print("=" * 50)


# ===== 指令变换器 =====


class InstructionTransform:
    """
    指令变换基类

    所有指令变换都继承此类。
    """

    name: str = "base"

    def transform(self, instructions: list[Instruction]) -> list[Instruction]:
        """
        变换指令序列

        Args:
            instructions: 原始指令序列

        Returns:
            变换后的指令序列
        """
        raise NotImplementedError


class IdentityTransform(InstructionTransform):
    """
    恒等变换

    不改变指令序列，用于测试。
    """
    name = "identity"

    def transform(self, instructions: list[Instruction]) -> list[Instruction]:
        return instructions.copy()


class ReorderTransform(InstructionTransform):
    """
    指令重排变换

    按操作码类型分组重排指令。
    """
    name = "reorder"

    def transform(self, instructions: list[Instruction]) -> list[Instruction]:
        # 按类别分组
        grouped: dict[str, list[Instruction]] = {}
        for instr in instructions:
            category = OpCodeRegistry.get(instr.op.value).category if OpCodeRegistry.get(instr.op.value) else "other"
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(instr)

        # 重新组合
        result = []
        for category in ["assignment", "call", "expression", "control_flow", "table", "function", "special", "auxiliary"]:
            if category in grouped:
                result.extend(grouped[category])

        return result


class InsertAuxiliaryTransform(InstructionTransform):
    """
    插入辅助指令变换

    在指令序列中插入恒等变换或哑操作。
    """
    name = "insert_auxiliary"

    def __init__(self, rng: random.Random | None = None, probability: float = 0.3):
        self.rng = rng
        self.probability = probability

    def transform(self, instructions: list[Instruction]) -> list[Instruction]:
        result = []
        counter = [0]

        for instr in instructions:
            result.append(instr)

            # 根据概率插入辅助指令
            if self.rng and self.rng.random() < self.probability:
                aux_instr = self._create_auxiliary(counter)
                if aux_instr:
                    result.append(aux_instr)

        return result

    def _create_auxiliary(self, counter: list[int]) -> Instruction | None:
        """创建辅助指令"""
        if not self.rng:
            return Instruction(OpCode.NOP)

        aux_types = [OpCode.IDENTITY, OpCode.DUMMY, OpCode.NOP]
        chosen = self.rng.choice(aux_types)

        if chosen == OpCode.IDENTITY:
            var = f"_t{counter[0]}"
            counter[0] += 1
            return Instruction(OpCode.IDENTITY, [var])
        elif chosen == OpCode.DUMMY:
            return Instruction(OpCode.DUMMY)
        else:
            return Instruction(OpCode.NOP)


class RemoveNopTransform(InstructionTransform):
    """
    移除空操作变换

    移除指令序列中的 NOP 指令。
    """
    name = "remove_nop"

    def transform(self, instructions: list[Instruction]) -> list[Instruction]:
        return [instr for instr in instructions if instr.op != OpCode.NOP]


class CollectStatsTransform(InstructionTransform):
    """
    收集统计信息变换

    不改变指令序列，但收集操作码分布信息。
    """
    name = "collect_stats"

    def __init__(self):
        self.stats: dict[str, int] = {}

    def transform(self, instructions: list[Instruction]) -> list[Instruction]:
        self.stats = {}
        for instr in instructions:
            op_name = instr.op.value
            self.stats[op_name] = self.stats.get(op_name, 0) + 1
        return instructions.copy()

    def get_stats(self) -> dict[str, int]:
        return self.stats.copy()


class InstructionTransformer:
    """
    指令变换器

    管理多个变换器，按顺序应用。
    """

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng
        self.transforms: list[InstructionTransform] = []

    def add_transform(self, transform: InstructionTransform) -> 'InstructionTransformer':
        """添加变换器"""
        self.transforms.append(transform)
        return self

    def transform(self, instructions: list[Instruction]) -> list[Instruction]:
        """应用所有变换"""
        result = instructions
        for t in self.transforms:
            result = t.transform(result)
        return result

    def transform_block(self, block_instr: BlockInstructions) -> BlockInstructions:
        """变换单个 block 的指令"""
        new_instructions = self.transform(block_instr.instructions.copy())
        return BlockInstructions(
            block_id=block_instr.block_id,
            instructions=new_instructions,
            block_type=block_instr.block_type
        )

    @classmethod
    def create_default(cls, rng: random.Random | None = None) -> 'InstructionTransformer':
        """创建默认变换器"""
        transformer = cls(rng)
        transformer.add_transform(RemoveNopTransform())
        return transformer

    @classmethod
    def create_with_auxiliary(cls, rng: random.Random | None = None,
                              probability: float = 0.2) -> 'InstructionTransformer':
        """创建带辅助指令的变换器"""
        transformer = cls(rng)
        transformer.add_transform(RemoveNopTransform())
        transformer.add_transform(InsertAuxiliaryTransform(rng, probability))
        return transformer


# ===== 扩展的指令表示层 =====


# 指令便捷构造函数
class Instr:
    """
    指令便捷构造函数

    提供简洁的指令创建方法。
    """
    @staticmethod
    def nop() -> Instruction:
        return Instruction(OpCode.NOP)

    @staticmethod
    def declare(name: str) -> Instruction:
        return Instruction(OpCode.DECLARE, [name])

    @staticmethod
    def init(name: str, value: str) -> Instruction:
        return Instruction(OpCode.INIT, [name], result=value)

    @staticmethod
    def assign(name: str, value: str) -> Instruction:
        return Instruction(OpCode.ASSIGN, [name], result=value)

    @staticmethod
    def call(func: str, *args: str) -> Instruction:
        return Instruction(OpCode.CALL, [func] + list(args))

    @staticmethod
    def call_assign(result: str, expr: str) -> Instruction:
        return Instruction(OpCode.CALL_ASSIGN, [expr], result=result)

    @staticmethod
    def ret() -> Instruction:
        return Instruction(OpCode.RETURN)

    @staticmethod
    def ret_val(expr: str) -> Instruction:
        return Instruction(OpCode.RETURN_VAL, [expr])

    @staticmethod
    def if_block(cond: str) -> Instruction:
        return Instruction(OpCode.IF, [cond])

    @staticmethod
    def then() -> Instruction:
        return Instruction(OpCode.THEN)

    @staticmethod
    def else_block() -> Instruction:
        return Instruction(OpCode.ELSE)

    @staticmethod
    def while_block(cond: str) -> Instruction:
        return Instruction(OpCode.WHILE, [cond])

    @staticmethod
    def for_block(expr: str) -> Instruction:
        return Instruction(OpCode.FOR, [expr])

    @staticmethod
    def do_block() -> Instruction:
        return Instruction(OpCode.DO)

    @staticmethod
    def end_block() -> Instruction:
        return Instruction(OpCode.END)

    @staticmethod
    def repeat() -> Instruction:
        return Instruction(OpCode.REPEAT)

    @staticmethod
    def until(cond: str) -> Instruction:
        return Instruction(OpCode.UNTIL, [cond])

    @staticmethod
    def func_def(name: str, *params: str) -> Instruction:
        return Instruction(OpCode.FUNC_DEF, [name] + list(params))

    @staticmethod
    def func_end() -> Instruction:
        return Instruction(OpCode.FUNC_END)

    @staticmethod
    def expr(code: str) -> Instruction:
        return Instruction(OpCode.EXPR, [code])

    @staticmethod
    def error(msg: str) -> Instruction:
        return Instruction(OpCode.ERROR, [msg])

    @staticmethod
    def comment(text: str) -> Instruction:
        return Instruction(OpCode.COMMENT, [text])

    @staticmethod
    def identity(name: str) -> Instruction:
        return Instruction(OpCode.IDENTITY, [name])

    @staticmethod
    def dummy() -> Instruction:
        return Instruction(OpCode.DUMMY)


# Handler 映射系统
class HandlerMap:
    """
    指令 Handler 映射表

    使用字典将 OpCode 映射到处理函数，支持动态注册。
    """
    _handlers: dict[OpCode, callable] = {}
    _generators: dict[OpCode, callable] = {}

    @classmethod
    def register_handler(cls, opcode: OpCode, handler: callable) -> None:
        """注册指令处理器"""
        cls._handlers[opcode] = handler

    @classmethod
    def register_generator(cls, opcode: OpCode, generator: callable) -> None:
        """注册代码生成器"""
        cls._generators[opcode] = generator

    @classmethod
    def get_handler(cls, opcode: OpCode) -> callable | None:
        """获取处理器"""
        return cls._handlers.get(opcode)

    @classmethod
    def get_generator(cls, opcode: OpCode) -> callable | None:
        """获取生成器"""
        return cls._generators.get(opcode)

    @classmethod
    def handle(cls, opcode: OpCode, instr: Instruction, context: 'SimpleContext') -> dict:
        """分发处理"""
        handler = cls.get_handler(opcode)
        if handler:
            return handler(instr, context)
        return {}

    @classmethod
    def generate(cls, opcode: OpCode, instr: Instruction) -> str:
        """分发生成"""
        generator = cls.get_generator(opcode)
        if generator:
            return generator(instr)
        return f"-- unsupported: {opcode.value}"


# 注册默认 Generator
def _register_default_generators() -> None:
    """注册默认代码生成器"""
    def gen_nop(i): return "do end"
    def gen_comment(i): return f"-- {i.args[0] if i.args else ''}"
    def gen_declare(i): return f"local {i.args[0] if i.args else '_'}"
    def gen_init(i): return f"local {i.args[0] if i.args else '_'} = {i.result or ''}"
    def gen_assign(i): return f"{i.args[0] if i.args else '_'} = {i.result or ''}"
    def gen_call(i): return f"{i.args[0] if i.args else ''}({', '.join(str(a) for a in i.args[1:]) if len(i.args) > 1 else ''})"
    def gen_call_assign(i): return f"{i.result or '_'} = {i.args[0] if i.args else ''}"
    def gen_return(i): return "return"
    def gen_return_val(i): return f"return {i.args[0] if i.args else ''}"
    def gen_if(i): return f"if {i.args[0] if i.args else 'true'} then"
    def gen_then(i): return "then"
    def gen_else(i): return "else"
    def gen_while(i): return f"while {i.args[0] if i.args else 'true'} do"
    def gen_for(i): return i.args[0] if i.args else ""
    def gen_do(i): return "do"
    def gen_end(i): return "end"
    def gen_repeat(i): return "repeat"
    def gen_until(i): return f"until {i.args[0] if i.args else 'false'}"
    def gen_func_def(i): return f"function {i.args[0] if i.args else 'fn'}({', '.join(str(a) for a in i.args[1:]) if len(i.args) > 1 else ''})"
    def gen_func_end(i): return "end"
    def gen_expr(i): return i.args[0] if i.args else ""
    def gen_error(i): return f"error('{i.args[0] if i.args else ''}')"
    def gen_identity(i): return f"local {i.args[0] if i.args else '_'} = {i.args[0] if i.args else '_'}"
    def gen_dummy(i): return "do end"
    def gen_label(i): return f"-- label: {i.args[0] if i.args else ''}"
    def gen_table_new(i): return "{}"
    def gen_break(i): return "break"
    def gen_continue(i): return "continue"
    def gen_assert(i): return f"assert({', '.join(str(a) for a in i.args) if i.args else ''})"

    HandlerMap.register_generator(OpCode.NOP, gen_nop)
    HandlerMap.register_generator(OpCode.COMMENT, gen_comment)
    HandlerMap.register_generator(OpCode.DECLARE, gen_declare)
    HandlerMap.register_generator(OpCode.INIT, gen_init)
    HandlerMap.register_generator(OpCode.ASSIGN, gen_assign)
    HandlerMap.register_generator(OpCode.CALL, gen_call)
    HandlerMap.register_generator(OpCode.CALL_ASSIGN, gen_call_assign)
    HandlerMap.register_generator(OpCode.RETURN, gen_return)
    HandlerMap.register_generator(OpCode.RETURN_VAL, gen_return_val)
    HandlerMap.register_generator(OpCode.IF, gen_if)
    HandlerMap.register_generator(OpCode.THEN, gen_then)
    HandlerMap.register_generator(OpCode.ELSE, gen_else)
    HandlerMap.register_generator(OpCode.WHILE, gen_while)
    HandlerMap.register_generator(OpCode.FOR, gen_for)
    HandlerMap.register_generator(OpCode.DO, gen_do)
    HandlerMap.register_generator(OpCode.END, gen_end)
    HandlerMap.register_generator(OpCode.REPEAT, gen_repeat)
    HandlerMap.register_generator(OpCode.UNTIL, gen_until)
    HandlerMap.register_generator(OpCode.FUNC_DEF, gen_func_def)
    HandlerMap.register_generator(OpCode.FUNC_END, gen_func_end)
    HandlerMap.register_generator(OpCode.EXPR, gen_expr)
    HandlerMap.register_generator(OpCode.ERROR, gen_error)
    HandlerMap.register_generator(OpCode.IDENTITY, gen_identity)
    HandlerMap.register_generator(OpCode.DUMMY, gen_dummy)
    HandlerMap.register_generator(OpCode.LABEL, gen_label)
    HandlerMap.register_generator(OpCode.TABLE_NEW, gen_table_new)
    HandlerMap.register_generator(OpCode.BREAK, gen_break)
    HandlerMap.register_generator(OpCode.CONTINUE, gen_continue)
    HandlerMap.register_generator(OpCode.ASSERT, gen_assert)


_register_default_generators()


# 重构的 InstructionGenerator
class InstructionGeneratorV2:
    """
    改进的指令生成器

    使用 HandlerMap 进行代码生成，便于扩展。
    """

    def __init__(self, obfuscate_names: bool = False):
        self.obfuscate_names = obfuscate_names

    def generate_instruction(self, instr: Instruction) -> str:
        """生成单条指令"""
        return HandlerMap.generate(instr.op, instr)

    def generate_block(self, block_instr: 'BlockInstructions') -> str:
        """生成整个 block 的代码"""
        lines = []
        for instr in block_instr.instructions:
            code = self.generate_instruction(instr)
            if code:
                lines.append(code)
        return "\n".join(lines)

    def generate_sequence(self, instructions: list[Instruction]) -> str:
        """生成指令序列代码"""
        lines = []
        for instr in instructions:
            code = self.generate_instruction(instr)
            if code:
                lines.append(code)
        return "\n".join(lines)

    def generate_function(self, instructions: list[Instruction], func_name: str) -> str:
        """生成 Lua 函数"""
        body = self.generate_sequence(instructions)
        return f"local function {func_name}()\n    {body}\nend"


# 扩展的指令变换
class InsertAuxiliaryInstrTransform(InstructionTransform):
    """
    插入辅助指令变换（基于 Instr 类）

    在指令序列中插入恒等变换或哑操作。
    """
    name = "insert_auxiliary_instr"

    def __init__(self, rng: random.Random | None = None, probability: float = 0.2):
        self.rng = rng
        self.probability = probability
        self._counter = 0

    def transform(self, instructions: list[Instruction]) -> list[Instruction]:
        result = []
        for instr in instructions:
            result.append(instr)
            if self.rng and self.rng.random() < self.probability:
                aux = self._create_auxiliary()
                if aux:
                    result.append(aux)
        return result

    def _create_auxiliary(self) -> Instruction | None:
        """创建辅助指令"""
        self._counter += 1
        if not self.rng:
            return Instr.nop()

        aux_types = [OpCode.IDENTITY, OpCode.DUMMY, OpCode.NOP]
        chosen = self.rng.choice(aux_types)

        if chosen == OpCode.IDENTITY:
            return Instr.identity(f"_t{self._counter}")
        elif chosen == OpCode.DUMMY:
            return Instr.dummy()
        return Instr.nop()


class InstructionSequenceBuilder:
    """
    指令序列构建器

    提供链式 API 来构建指令序列。
    """

    def __init__(self):
        self._instructions: list[Instruction] = []

    def nop(self) -> 'InstructionSequenceBuilder':
        self._instructions.append(Instr.nop())
        return self

    def declare(self, name: str) -> 'InstructionSequenceBuilder':
        self._instructions.append(Instr.declare(name))
        return self

    def init(self, name: str, value: str) -> 'InstructionSequenceBuilder':
        self._instructions.append(Instr.init(name, value))
        return self

    def assign(self, name: str, value: str) -> 'InstructionSequenceBuilder':
        self._instructions.append(Instr.assign(name, value))
        return self

    def call(self, func: str, *args: str) -> 'InstructionSequenceBuilder':
        self._instructions.append(Instr.call(func, *args))
        return self

    def ret(self) -> 'InstructionSequenceBuilder':
        self._instructions.append(Instr.ret())
        return self

    def ret_val(self, expr: str) -> 'InstructionSequenceBuilder':
        self._instructions.append(Instr.ret_val(expr))
        return self

    def if_block(self, cond: str) -> 'InstructionSequenceBuilder':
        self._instructions.append(Instr.if_block(cond))
        return self

    def then(self) -> 'InstructionSequenceBuilder':
        self._instructions.append(Instr.then())
        return self

    def else_block(self) -> 'InstructionSequenceBuilder':
        self._instructions.append(Instr.else_block())
        return self

    def end(self) -> 'InstructionSequenceBuilder':
        self._instructions.append(Instr.end_block())
        return self

    def while_block(self, cond: str) -> 'InstructionSequenceBuilder':
        self._instructions.append(Instr.while_block(cond))
        return self

    def do(self) -> 'InstructionSequenceBuilder':
        self._instructions.append(Instr.do_block())
        return self

    def func_def(self, name: str, *params: str) -> 'InstructionSequenceBuilder':
        self._instructions.append(Instr.func_def(name, *params))
        return self

    def func_end(self) -> 'InstructionSequenceBuilder':
        self._instructions.append(Instr.func_end())
        return self

    def expr(self, code: str) -> 'InstructionSequenceBuilder':
        self._instructions.append(Instr.expr(code))
        return self

    def add(self, instr: Instruction) -> 'InstructionSequenceBuilder':
        self._instructions.append(instr)
        return self

    def build(self) -> list[Instruction]:
        """返回构建的指令列表"""
        return self._instructions.copy()

    def generate(self) -> str:
        """生成 Lua 代码"""
        gen = InstructionGeneratorV2()
        return gen.generate_sequence(self._instructions)


class BlockTypeLegacy(Enum):
    """Block 类型分类"""
    STATEMENT = "statement"
    FUNCTION_DEF = "function_def"
    CONTROL_STRUCT = "control_struct"
    TABLE_DEF = "table_def"
    ASSIGNMENT = "assignment"
    EXPRESSION = "expression"


class AuxiliaryPathType(Enum):
    """辅助路径类型"""
    DEAD_CODE = "dead_code"           # 永不到达的代码
    REDUNDANT_JUMP = "redundant_jump"  # 冗余跳转
    NOP_FILL = "nop_fill"            # 空操作填充
    DECOY_BRANCH = "decoy_branch"    # 诱饵分支
    GUARD_CHECK = "guard_check"      # 守卫检查
    DUMMY_LOOP = "dummy_loop"        # 虚假循环
    REDUNDANT_ASSIGN = "redundant_assign"  # 冗余赋值
    SWAP_VARIABLES = "swap_variables"  # 变量交换（无意义）
    SELF_ASSIGN = "self_assign"      # 自赋值
    COMPUTED_SKIP = "computed_skip"    # 计算跳过
    DUMMY_FUNCTION = "dummy_function"  # 虚假函数调用
    # 冗余 block 类型
    REDUNDANT_BLOCK = "redundant_block"  # 冗余代码块
    SKIP_TARGET = "skip_target"        # 跳转目标块
    DECOY_BLOCK = "decoy_block"        # 诱饵块
    NESTED_TRAP = "nested_trap"        # 嵌套陷阱


@dataclass
class AuxiliaryPath:
    """辅助路径"""
    path_id: int
    path_type: str
    content: str  # Lua 代码片段
    target_block_id: int | None = None  # 跳转目标
    condition: str | None = None  # 触发条件
    probability: float = 0.0  # 执行概率
    execution_mode: str = "inline"  # "inline" | "wrapped" | "called"


class AuxiliaryPathGenerator:
    """辅助路径生成器：生成不影响主流程的额外路径"""

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.path_counter = [0]
        self.used_identifiers: set[str] = set()
        self.generated_paths_count = 0

    def _gen_id(self) -> int:
        self.path_counter[0] += 1
        self.generated_paths_count += 1
        return self.path_counter[0]

    def _random_identifier(self, prefix: str = "_aux") -> str:
        chars = string.ascii_lowercase
        for _ in range(10):
            name = prefix + "_" + "".join(self.rng.choice(chars) for _ in range(4))
            if name not in self.used_identifiers:
                self.used_identifiers.add(name)
                return name
        return prefix + "_" + str(self._gen_id())

    def _create_path(
        self,
        path_type: AuxiliaryPathType,
        content: str,
        target_block_id: int | None = None,
        condition: str | None = None,
        execution_mode: str = "inline"
    ) -> AuxiliaryPath:
        """创建辅助路径的统一方法"""
        return AuxiliaryPath(
            path_id=self._gen_id(),
            path_type=path_type.value,
            content=content,
            target_block_id=target_block_id,
            condition=condition,
            probability=0.0,
            execution_mode=execution_mode
        )

    def generate_dead_code(self, block: CodeBlock) -> AuxiliaryPath | None:
        """生成死代码路径 - 条件永远为假的代码"""
        if self.rng.random() > 0.25:
            return None

        patterns = [
            (f"local _d = false\nif _d then\n    error('unreachable')\nend", None),
            (f"if false and true then\n    error('dead')\nend", None),
            (f"if nil then\n    error('unreachable')\nend", None),
            (f"if 1 ~= 1 then\n    error('impossible')\nend", None),
        ]

        content, _ = self.rng.choice(patterns)
        var_name = self._random_identifier("_d")
        content = content.replace("_d", var_name)

        return self._create_path(AuxiliaryPathType.DEAD_CODE, content, condition="false")

    def generate_redundant_jump(self, block: CodeBlock, next_block_id: int | None) -> AuxiliaryPath | None:
        """生成冗余跳转 - 先跳到某处再跳回来"""
        if next_block_id is None or self.rng.random() > 0.25:
            return None

        patterns = [
            f"local _skip = false\nif _skip then\n    -- redundant jump\nend",
            f"do\n    local _label = false\n    if not _label then\n        -- fall through\n    end\nend",
            f"if true then\n    -- always true\nelse\n    -- never reached\nend",
        ]

        content = self.rng.choice(patterns)
        return self._create_path(
            AuxiliaryPathType.REDUNDANT_JUMP,
            content,
            target_block_id=next_block_id
        )

    def generate_nop_fill(self, block: CodeBlock) -> AuxiliaryPath | None:
        """生成 NOP 填充 - 无意义的空操作"""
        if self.rng.random() > 0.35:
            return None

        nop_ops = [
            "do end",
            "(function() end)()",
            "pcall(function() end)",
            "select('#', nil)",
            "next({})",
            "(function() return end)()",
            "setmetatable({}, {})",
        ]

        nop_count = self.rng.randint(1, 3)
        lines = [self.rng.choice(nop_ops) for _ in range(nop_count)]

        return self._create_path(AuxiliaryPathType.NOP_FILL, "\n".join(lines))

    def generate_decoy_branch(self, block: CodeBlock, next_block_id: int | None) -> AuxiliaryPath | None:
        """生成诱饵分支 - 两条分支最终都到同一目标"""
        if next_block_id is None or self.rng.random() > 0.2:
            return None

        patterns = [
            (
                "local _decoy = false\n"
                "local _tmp = 0\n"
                "if _decoy then\n"
                "    _tmp = 1\n"
                "else\n"
                "    _tmp = 2\n"
                "end"
            ),
            (
                "local _cond = true\n"
                "local _val = 0\n"
                "if _cond and false then\n"
                "    _val = 100\n"
                "else\n"
                "    _val = _val\n"
                "end"
            ),
        ]

        content = self.rng.choice(patterns)
        return self._create_path(
            AuxiliaryPathType.DECOY_BRANCH,
            content,
            target_block_id=next_block_id
        )

    def generate_guard_check(self, block: CodeBlock) -> AuxiliaryPath | None:
        """生成守卫检查 - 不会触发的安全检查"""
        if self.rng.random() > 0.2:
            return None

        patterns = [
            (
                "local _guard = true\n"
                "if not _guard then\n"
                "    error('guard failed')\n"
                "end"
            ),
            (
                "local _safe = 1\n"
                "if _safe == 0 then\n"
                "    _safe = _safe + 1\n"
                "end"
            ),
            (
                "local _check = true\n"
                "if _check == false then\n"
                "    _check = true\n"
                "end"
            ),
        ]

        content = self.rng.choice(patterns)
        return self._create_path(AuxiliaryPathType.GUARD_CHECK, content)

    def generate_dummy_loop(self, block: CodeBlock) -> AuxiliaryPath | None:
        """生成虚假循环 - 永远不会真正循环"""
        if self.rng.random() > 0.2:
            return None

        patterns = [
            (
                "local _iter = 0\n"
                "while false do\n"
                "    _iter = _iter + 1\n"
                "end"
            ),
            (
                "for _i = 1, 0 do\n"
                "    -- empty iteration\n"
                "end"
            ),
            (
                "repeat\n"
                "    break\n"
                "until true"
            ),
        ]

        content = self.rng.choice(patterns)
        return self._create_path(AuxiliaryPathType.DUMMY_LOOP, content)

    def generate_redundant_assign(self, block: CodeBlock) -> AuxiliaryPath | None:
        """生成冗余赋值 - 赋值后立即覆盖"""
        if self.rng.random() > 0.25:
            return None

        patterns = [
            "local _x = 0\n_x = 1\n_x = _x",
            "local _y = nil\n_y = {}\n_y = nil",
            "local _z = 1\n_z = _z\n_z = _z + 0",
        ]

        content = self.rng.choice(patterns)
        var_prefix = "_x" if "_x" in content else ("_y" if "_y" in content else "_z")
        new_var = self._random_identifier("_tmp")
        content = content.replace(var_prefix, new_var)

        return self._create_path(AuxiliaryPathType.REDUNDANT_ASSIGN, content)

    def generate_swap_variables(self, block: CodeBlock) -> AuxiliaryPath | None:
        """生成变量交换（无意义）"""
        if self.rng.random() > 0.15:
            return None

        var_a = self._random_identifier("_a")
        var_b = self._random_identifier("_b")

        content = (
            f"local {var_a}, {var_b} = 0, 0\n"
            f"local _temp = {var_a}\n"
            f"{var_a} = {var_b}\n"
            f"{var_b} = _temp"
        )

        return self._create_path(AuxiliaryPathType.SWAP_VARIABLES, content)

    def generate_self_assign(self, block: CodeBlock) -> AuxiliaryPath | None:
        """生成自赋值"""
        if self.rng.random() > 0.3:
            return None

        var_name = self._random_identifier("_self")
        patterns = [
            f"local {var_name} = 1\n{var_name} = {var_name}",
            f"local {var_name} = nil\n{var_name} = {var_name}",
            f"local {var_name} = {{}}\n{var_name} = {var_name}",
        ]

        content = self.rng.choice(patterns)
        return self._create_path(AuxiliaryPathType.SELF_ASSIGN, content)

    def generate_computed_skip(self, block: CodeBlock) -> AuxiliaryPath | None:
        """生成计算跳过 - 无意义的计算"""
        if self.rng.random() > 0.2:
            return None

        patterns = [
            "local _ = 0 + 0 - 0 * 0",
            "local _ = 1 == 1 and true or false",
            "local _ = 'a' .. '' .. ''",
            "local _ = ({1,2,3})[1]",
            "local _ = pcall(error, nil)",
        ]

        content = self.rng.choice(patterns)
        return self._create_path(AuxiliaryPathType.COMPUTED_SKIP, content)

    def generate_dummy_function(self, block: CodeBlock) -> AuxiliaryPath | None:
        """生成虚假函数调用"""
        if self.rng.random() > 0.15:
            return None

        func_name = self._random_identifier("_dummy")
        content = (
            f"local function {func_name}() end\n"
            f"{func_name}()"
        )

        return self._create_path(
            AuxiliaryPathType.DUMMY_FUNCTION,
            content,
            execution_mode="wrapped"
        )

    def generate_auxiliary_path(self, block: CodeBlock, next_block_id: int | None) -> AuxiliaryPath | None:
        """根据概率生成一种辅助路径"""
        generators = [
            lambda: self.generate_nop_fill(block),
            lambda: self.generate_dead_code(block),
            lambda: self.generate_self_assign(block),
            lambda: self.generate_redundant_assign(block),
            lambda: self.generate_decoy_branch(block, next_block_id),
            lambda: self.generate_guard_check(block),
            lambda: self.generate_dummy_loop(block),
            lambda: self.generate_computed_skip(block),
            lambda: self.generate_redundant_jump(block, next_block_id),
            lambda: self.generate_swap_variables(block),
            lambda: self.generate_dummy_function(block),
        ]

        self.rng.shuffle(generators)

        for gen in generators:
            path = gen()
            if path is not None:
                return path

        return None

    def add_auxiliary_paths_to_block(
        self,
        block: CodeBlock,
        next_block_id: int | None,
        max_paths: int = 2
    ) -> None:
        """为 block 添加辅助路径"""
        if len(block.auxiliary_paths) >= max_paths:
            return

        path = self.generate_auxiliary_path(block, next_block_id)
        if path is not None:
            block.add_auxiliary_path({
                "path_id": path.path_id,
                "path_type": path.path_type,
                "content": path.content,
                "target_block_id": path.target_block_id,
                "execution_mode": path.execution_mode,
            })

    def get_statistics(self) -> dict:
        """获取生成统计"""
        return {
            "total_generated": self.generated_paths_count,
            "unique_id_count": len(self.used_identifiers),
        }


# ===== 常量池（Constant Pool）=====
@dataclass
class ConstantEntry:
    """常量条目"""
    index: int
    value: str
    const_type: str  # "string", "number", "boolean"


class ConstantPool:
    """常量池：提取字符串和数字到表中，用索引访问"""

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng
        self.strings: dict[str, int] = {}
        self.numbers: dict[float, int] = {}
        self.booleans: dict[bool, int] = {}
        self.next_string_index = 1
        self.next_number_index = 1
        self.next_boolean_index = 1
        self.pool_prefix = "_cp" if rng is None else random_lua_identifier(rng, "_cp")
        self.replacements: dict[str, str] = {}

    def intern_string(self, value: str) -> int:
        """将字符串加入常量池，返回索引"""
        if value not in self.strings:
            self.strings[value] = self.next_string_index
            self.next_string_index += 1
        return self.strings[value]

    def intern_number(self, value: float) -> int:
        """将数字加入常量池，返回索引"""
        if value not in self.numbers:
            self.numbers[value] = self.next_number_index
            self.next_number_index += 1
        return self.numbers[value]

    def intern_boolean(self, value: bool) -> int:
        """将布尔值加入常量池，返回索引"""
        if value not in self.booleans:
            self.booleans[value] = self.next_boolean_index
            self.next_boolean_index += 1
        return self.booleans[value]

    def get_string_index(self, value: str) -> int | None:
        """获取字符串的索引，不存在返回 None"""
        return self.strings.get(value)

    def get_number_index(self, value: float) -> int | None:
        """获取数字的索引，不存在返回 None"""
        return self.numbers.get(value)

    def has_string(self, value: str) -> bool:
        return value in self.strings

    def has_number(self, value: float) -> bool:
        return value in self.numbers

    def get_total_count(self) -> int:
        """获取常量总数"""
        return len(self.strings) + len(self.numbers) + len(self.booleans)

    def generate_pool_table(self) -> str:
        """生成常量池 Lua 代码"""
        lines: list[str] = []
        prefix = self.pool_prefix

        lines.append(f"local {prefix}_S = {{")
        for value, idx in sorted(self.strings.items(), key=lambda x: x[1]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
            lines.append(f"    [{idx}] = \"{escaped}\",")
        lines.append("}")

        lines.append(f"local {prefix}_N = {{")
        for value, idx in sorted(self.numbers.items(), key=lambda x: x[1]):
            lines.append(f"    [{idx}] = {value},")
        lines.append("}")

        lines.append(f"local {prefix}_B = {{")
        for value, idx in sorted(self.booleans.items(), key=lambda x: x[1]):
            lines.append(f"    [{idx}] = {str(value).lower()},")
        lines.append("}")

        lines.append(f"local function {prefix}_Sget(idx) return {prefix}_S[idx] end")
        lines.append(f"local function {prefix}_Nget(idx) return {prefix}_N[idx] end")
        lines.append(f"local function {prefix}_Bget(idx) return {prefix}_B[idx] end")

        return "\n".join(lines)

    def generate_unified_pool_table(self, rng: random.Random | None = None) -> str:
        """生成统一的常量池 Lua 代码（单一访问函数）"""
        lines: list[str] = []
        prefix = self.pool_prefix

        # 生成表
        lines.append(f"local {prefix}_S = {{")
        for value, idx in sorted(self.strings.items(), key=lambda x: x[1]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
            lines.append(f"    [{idx}] = \"{escaped}\",")
        lines.append("}")

        lines.append(f"local {prefix}_N = {{")
        for value, idx in sorted(self.numbers.items(), key=lambda x: x[1]):
            lines.append(f"    [{idx}] = {value},")
        lines.append("}")

        lines.append(f"local {prefix}_B = {{")
        for value, idx in sorted(self.booleans.items(), key=lambda x: x[1]):
            lines.append(f"    [{idx}] = {str(value).lower()},")
        lines.append("}")

        # 字符串边界索引
        max_s = max((idx for idx in self.strings.values()), default=0)
        max_n = max((idx for idx in self.numbers.values()), default=0)
        max_b = max((idx for idx in self.booleans.values()), default=0)

        # 生成统一的访问函数
        func_name = f"{prefix}_get" if not rng else f"{prefix}_{random_lua_identifier(rng, 'get')}"

        lines.append(f"local function {func_name}(t, k)")
        lines.append(f"    if t == 'S' then")
        lines.append(f"        return {prefix}_S[k]")
        lines.append(f"    elseif t == 'N' then")
        lines.append(f"        return {prefix}_N[k]")
        lines.append(f"    elseif t == 'B' then")
        lines.append(f"        return {prefix}_B[k]")
        lines.append(f"    end")
        lines.append(f"end")

        return "\n".join(lines)

    def generate_unified_pool_with_transform(self, rng: random.Random | None = None) -> tuple[str, dict]:
        """
        生成带变换的统一常量池

        在访问函数中加入简单变换，但保持结果不变。

        Returns:
            (lua_code, info_dict) 元组
        """
        lines: list[str] = []
        prefix = self.pool_prefix
        info = {"transform_type": "none", "function_name": ""}

        # 生成表
        lines.append(f"local {prefix}_S = {{")
        for value, idx in sorted(self.strings.items(), key=lambda x: x[1]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
            lines.append(f"    [{idx}] = \"{escaped}\",")
        lines.append("}")

        lines.append(f"local {prefix}_N = {{")
        for value, idx in sorted(self.numbers.items(), key=lambda x: x[1]):
            lines.append(f"    [{idx}] = {value},")
        lines.append("}")

        lines.append(f"local {prefix}_B = {{")
        for value, idx in sorted(self.booleans.items(), key=lambda x: x[1]):
            lines.append(f"    [{idx}] = {str(value).lower()},")
        lines.append("}")

        # 选择变换类型
        if rng:
            transform_types = ["none", "offset", "lookup", "simple"]
            transform = rng.choice(transform_types)
        else:
            transform = "none"

        info["transform_type"] = transform

        if transform == "none":
            # 无变换
            func_name = f"{prefix}_get" if not rng else f"{prefix}_{random_lua_identifier(rng, 'get')}"
            info["function_name"] = func_name
            lines.append(f"local function {func_name}(t, k)")
            lines.append(f"    if t == 'S' then return {prefix}_S[k]")
            lines.append(f"    elseif t == 'N' then return {prefix}_N[k]")
            lines.append(f"    elseif t == 'B' then return {prefix}_B[k] end")
            lines.append(f"end")

        elif transform == "offset":
            # 偏移变换：索引先加0或减0
            offset_var = f"{prefix}_off"
            func_name = f"{prefix}_get" if not rng else f"{prefix}_{random_lua_identifier(rng, 'get')}"
            info["function_name"] = func_name
            offset_expr = rng.choice(["+0", "-0", "+0-0"]) if rng else "+0"
            lines.append(f"local {offset_var} = 0")
            lines.append(f"local function {func_name}(t, k)")
            lines.append(f"    if t == 'S' then return {prefix}_S[k {offset_expr}]")
            lines.append(f"    elseif t == 'N' then return {prefix}_N[k {offset_expr}]")
            lines.append(f"    elseif t == 'B' then return {prefix}_B[k {offset_expr}] end")
            lines.append(f"end")

        elif transform == "lookup":
            # 查找表变换
            func_name = f"{prefix}_get" if not rng else f"{prefix}_{random_lua_identifier(rng, 'get')}"
            info["function_name"] = func_name
            lines.append(f"local {prefix}_map = {{S='S', N='N', B='B'}}")
            lines.append(f"local function {func_name}(t, k)")
            lines.append(f"    local _t = {prefix}_map[t] or t")
            lines.append(f"    if _t == 'S' then return {prefix}_S[k]")
            lines.append(f"    elseif _t == 'N' then return {prefix}_N[k]")
            lines.append(f"    elseif _t == 'B' then return {prefix}_B[k] end")
            lines.append(f"end")

        elif transform == "simple":
            # 简单计算变换
            calc_var = f"{prefix}_c"
            func_name = f"{prefix}_get" if not rng else f"{prefix}_{random_lua_identifier(rng, 'get')}"
            info["function_name"] = func_name
            lines.append(f"local {calc_var} = 0")
            lines.append(f"local function {func_name}(t, k)")
            lines.append(f"    {calc_var} = ({calc_var} + 0) - 0")
            lines.append(f"    if t == 'S' then return {prefix}_S[k]")
            lines.append(f"    elseif t == 'N' then return {prefix}_N[k]")
            lines.append(f"    elseif t == 'B' then return {prefix}_B[k] end")
            lines.append(f"end")

        return "\n".join(lines), info

    def get_unified_accessor_call(self, literal: str, literal_type: str, func_name: str | None = None) -> str | None:
        """获取统一访问函数的调用表达式"""
        if func_name is None:
            func_name = f"{self.pool_prefix}_get"

        if literal_type == "string" and literal in self.strings:
            idx = self.strings[literal]
            return f"{func_name}('S', {idx})"
        elif literal_type == "number":
            try:
                num_val = float(literal)
                if num_val in self.numbers:
                    idx = self.numbers[num_val]
                    return f"{func_name}('N', {idx})"
            except ValueError:
                pass
        elif literal_type == "boolean":
            try:
                bool_val = literal.lower() == "true"
                if bool_val in self.booleans:
                    idx = self.booleans[bool_val]
                    return f"{func_name}('B', {idx})"
            except ValueError:
                pass
        return None

    def replace_literals_with_unified_access(self, content: str, func_name: str | None = None) -> str:
        """使用统一访问函数替换内容中的字面量"""
        result = content

        if func_name is None:
            func_name = f"{self.pool_prefix}_get"

        for value, idx in sorted(self.strings.items(), key=lambda x: x[1]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            old_pattern = f'"{escaped}"'
            new_expr = f"{func_name}('S', {idx})"
            result = result.replace(old_pattern, new_expr)

        for value, idx in sorted(self.numbers.items(), key=lambda x: x[1]):
            old_pattern = str(value)
            new_expr = f"{func_name}('N', {idx})"
            result = result.replace(old_pattern, new_expr)

        for value, idx in sorted(self.booleans.items(), key=lambda x: x[1]):
            old_pattern = str(value).lower()
            new_expr = f"{func_name}('B', {idx})"
            result = result.replace(old_pattern, new_expr)

        return result

    def generate_accessors(self) -> tuple[str, str, str]:
        """生成访问器函数名"""
        return (
            f"{self.pool_prefix}_Sget",
            f"{self.pool_prefix}_Nget",
            f"{self.pool_prefix}_Bget"
        )

    def generate_replacement_expr(self, literal: str, literal_type: str) -> str | None:
        """生成常量替换表达式"""
        prefix = self.pool_prefix
        if literal_type == "string" and literal in self.strings:
            idx = self.strings[literal]
            return f"{prefix}_Sget({idx})"
        elif literal_type == "number":
            try:
                num_val = float(literal)
                if num_val in self.numbers:
                    idx = self.numbers[num_val]
                    return f"{prefix}_Nget({idx})"
            except ValueError:
                pass
        elif literal_type == "boolean":
            try:
                bool_val = literal.lower() == "true"
                if bool_val in self.booleans:
                    idx = self.booleans[bool_val]
                    return f"{prefix}_Bget({idx})"
            except ValueError:
                pass
        return None

    def replace_literals_in_content(self, content: str) -> str:
        """在代码内容中替换字面量为常量池访问"""
        result = content

        for value, idx in self.strings.items():
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            old_pattern = f'"{escaped}"'
            new_expr = f'{self.pool_prefix}_Sget({idx})'
            result = result.replace(old_pattern, new_expr)

        for value, idx in self.numbers.items():
            old_pattern = str(value)
            new_expr = f'{self.pool_prefix}_Nget({idx})'
            result = result.replace(old_pattern, new_expr)

        for value, idx in self.booleans.items():
            old_pattern = str(value).lower()
            new_expr = f'{self.pool_prefix}_Bget({idx})'
            result = result.replace(old_pattern, new_expr)

        return result

    def get_statistics(self) -> dict:
        """获取常量池统计信息"""
        return {
            "string_count": len(self.strings),
            "number_count": len(self.numbers),
            "boolean_count": len(self.booleans),
            "total_count": self.get_total_count(),
            "prefix": self.pool_prefix,
        }


# ===== 增强常量访问系统 =====


class ConstantAccessorType(Enum):
    """常量访问器类型"""
    DIRECT = "direct"           # 直接访问
    NEGATED = "negated"         # 取反（数字）
    BIT_NOT = "bit_not"         # 位取反
    ADD_ZERO = "add_zero"       # 加零
    SUB_ZERO = "sub_zero"       # 减零
    MUL_ONE = "mul_one"         # 乘一
    DIV_ONE = "div_one"         # 除一
    XOR_ZERO = "xor_zero"       # 异或零
    AND_MAX = "and_max"         # 与最大值
    OR_ZERO = "or_zero"         # 或零
    TABLE_WRAP = "table_wrap"   # 表包裹
    INDEX_OFFSET = "index_offset"  # 索引偏移


@dataclass
class ConstantAccessorConfig:
    """常量访问器配置"""
    enabled: bool = False
    accessor_prefix: str = "_acc"
    use_unified_entry: bool = True  # 使用统一入口
    enable_diversity: bool = True    # 启用多样性
    diversity_ratio: float = 0.3     # 多样化比例
    preserve_semantics: bool = True  # 保持语义


# ===== 字符串分段存储与运行时还原系统 =====


class FragmentRecoveryStrategy(ABC):
    """字符串片段还原策略基类"""

    @abstractmethod
    def generate_recovery_code(self, fragments: list[str], output_var: str) -> str:
        """生成还原代码"""
        pass

    @abstractmethod
    def name(self) -> str:
        """策略名称"""
        pass


class ConcatenationStrategy(FragmentRecoveryStrategy):
    """简单拼接策略: frag1 .. frag2 .. frag3"""

    def name(self) -> str:
        return "concatenation"

    def generate_recovery_code(self, fragments: list[str], output_var: str) -> str:
        if not fragments:
            return f"local {output_var} = \"\""
        if len(fragments) == 1:
            return f"local {output_var} = \"{self._escape(fragments[0])}\""
        concat_expr = " .. ".join(f'"{self._escape(f)}"' for f in fragments)
        return f"local {output_var} = {concat_expr}"

    def _escape(self, s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class TableBuilderStrategy(FragmentRecoveryStrategy):
    """表构建策略: 先存入表再拼接"""

    def name(self) -> str:
        return "table_builder"

    def generate_recovery_code(self, fragments: list[str], output_var: str) -> str:
        lines = [f"local {output_var} = {{}}"]
        for i, frag in enumerate(fragments):
            lines.append(f"{output_var}[{i + 1}] = \"{self._escape(frag)}\"")
        lines.append(f"local _tmp = table.concat({output_var})")
        lines.append(f"{output_var} = _tmp")
        return "\n".join(lines)

    def _escape(self, s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class ChunkMappingStrategy(FragmentRecoveryStrategy):
    """分块映射策略: 使用预定义映射表"""

    def name(self) -> str:
        return "chunk_mapping"

    def __init__(self):
        self._chunk_map: dict[str, int] = {}
        self._next_id = 1

    def generate_recovery_code(self, fragments: list[str], output_var: str) -> str:
        lines = []
        for frag in fragments:
            if frag not in self._chunk_map:
                self._chunk_map[frag] = self._next_id
                self._next_id += 1
        lines.append(f"local _m = {{}}")
        for frag, idx in self._chunk_map.items():
            lines.append(f"_m[{idx}] = \"{self._escape(frag)}\"")
        concat_parts = " .. ".join(f'_m[{self._chunk_map[f]}]' for f in fragments)
        lines.append(f"local {output_var} = {concat_parts}")
        return "\n".join(lines)

    def _escape(self, s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class IncrementalBuildStrategy(FragmentRecoveryStrategy):
    """增量构建策略: 逐片段累积"""

    def name(self) -> str:
        return "incremental_build"

    def generate_recovery_code(self, fragments: list[str], output_var: str) -> str:
        escaped_empty = '""'
        lines = ["local " + output_var + " = " + escaped_empty]
        for frag in fragments:
            lines.append(f"{output_var} = {output_var} .. \"{self._escape(frag)}\"")
        return "\n".join(lines)

    def _escape(self, s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class ReverseConcatStrategy(FragmentRecoveryStrategy):
    """反向拼接策略: 从后往前拼接"""

    def name(self) -> str:
        return "reverse_concat"

    def generate_recovery_code(self, fragments: list[str], output_var: str) -> str:
        if not fragments:
            return f"local {output_var} = \"\""
        rev_frags = list(reversed(fragments))
        concat_expr = " .. ".join(f'"{self._escape(f)}"' for f in rev_frags)
        lines = [
            f"local {output_var} = {concat_expr}",
        ]
        return lines[0]

    def _escape(self, s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class StringFragmentPool:
    """
    字符串分段存储池

    将长字符串拆分为多个片段存储，支持多种运行时还原策略
    """

    STRATEGY_REGISTRY: dict[str, type[FragmentRecoveryStrategy]] = {
        "concatenation": ConcatenationStrategy,
        "table_builder": TableBuilderStrategy,
        "chunk_mapping": ChunkMappingStrategy,
        "incremental": IncrementalBuildStrategy,
        "reverse": ReverseConcatStrategy,
    }

    def __init__(
        self,
        rng: random.Random | None = None,
        min_fragment_length: int = 2,
        max_fragment_length: int = 8,
        enable_segmentation: bool = True,
    ):
        self.rng = rng
        self.min_fragment_length = min_fragment_length
        self.max_fragment_length = max_fragment_length
        self.enable_segmentation = enable_segmentation

        # 分段存储
        self.fragments: dict[str, list[str]] = {}  # original -> fragments
        self.fragment_pool: list[str] = []
        self.next_index = 1

        # 字符串到索引的映射
        self.string_to_idx: dict[str, int] = {}
        self.idx_to_fragments: dict[int, list[str]] = {}

        # 还原策略
        self.strategy_for_string: dict[str, str] = {}  # string -> strategy_name

        # 生成唯一前缀
        self.prefix = "_sfp" if rng is None else f"_sfp{rng.randint(0, 99)}"

    def intern_string(self, value: str) -> int:
        """将字符串加入池中，返回虚拟索引"""
        if value not in self.string_to_idx:
            idx = self.next_index
            self.next_index += 1
            self.string_to_idx[value] = idx

            # 决定分段策略
            if self.enable_segmentation and len(value) > self.min_fragment_length:
                strategy = self._select_strategy()
                fragments = self._segment_string(value, strategy)
            else:
                strategy = "direct"
                fragments = [value]

            self.idx_to_fragments[idx] = fragments
            self.strategy_for_string[value] = strategy

            # 添加到片段池
            for frag in fragments:
                if frag not in self.fragment_pool:
                    self.fragment_pool.append(frag)

        return self.string_to_idx[value]

    def _select_strategy(self) -> str:
        """选择还原策略"""
        if self.rng:
            strategies = list(self.STRATEGY_REGISTRY.keys())
            return self.rng.choice(strategies)
        return "concatenation"

    def _segment_string(self, value: str, strategy: str) -> list[str]:
        """将字符串分段"""
        if strategy in ("concatenation", "incremental", "reverse"):
            # 简单等长分段
            return self._equal_segment(value)
        elif strategy == "table_builder":
            # 较长的固定分段
            return self._fixed_segment(value, 4)
        else:
            return self._equal_segment(value)

    def _equal_segment(self, value: str) -> list[str]:
        """等长分段"""
        min_len = self.min_fragment_length
        max_len = self.max_fragment_length
        fragments = []
        i = 0
        while i < len(value):
            remaining = len(value) - i
            if remaining <= min_len:
                # 剩余部分直接作为一个片段
                fragments.append(value[i:])
                break
            # 随机选择片段长度
            if self.rng:
                seg_len = self.rng.randint(min_len, min(max_len, remaining))
            else:
                seg_len = min(max_len, remaining)
            fragments.append(value[i:i + seg_len])
            i += seg_len
        return fragments if fragments else [value]

    def _fixed_segment(self, value: str, size: int) -> list[str]:
        """固定大小分段"""
        return [value[i:i + size] for i in range(0, len(value), size)]

    def get_fragments(self, idx: int) -> list[str] | None:
        """获取字符串的片段"""
        return self.idx_to_fragments.get(idx)

    def get_strategy(self, idx: int) -> str:
        """获取字符串使用的策略"""
        for s, i in self.string_to_idx.items():
            if i == idx:
                return self.strategy_for_string.get(s, "direct")
        return "direct"

    def generate_lua_pool(self) -> str:
        """生成 Lua 片段池代码"""
        lines = []
        lines.append(f"-- String Fragment Pool")
        lines.append(f"local {self.prefix}_F = {{}}")
        for i, frag in enumerate(self.fragment_pool, 1):
            escaped = frag.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            lines.append(f"{self.prefix}_F[{i}] = \"{escaped}\"")
        return "\n".join(lines)

    def generate_recovery_function(self, idx: int) -> str:
        """为指定索引生成还原函数调用"""
        fragments = self.get_fragments(idx)
        if not fragments:
            return '""'

        strategy = self.get_strategy(idx)
        return self._generate_recovery_expr(fragments, strategy)

    def _generate_recovery_expr(self, fragments: list[str], strategy: str) -> str:
        """根据策略生成恢复表达式"""
        # 首先获取片段索引
        frag_indices = []
        for frag in fragments:
            if frag in self.fragment_pool:
                frag_indices.append(self.fragment_pool.index(frag) + 1)

        if strategy == "concatenation":
            parts = [f"{self.prefix}_F[{i}]" for i in frag_indices]
            return " .. ".join(parts)
        elif strategy == "incremental":
            parts = [f"{self.prefix}_F[{i}]" for i in frag_indices]
            result = parts[0] if parts else '""'
            for p in parts[1:]:
                result = f"({result} .. {p})"
            return result
        elif strategy == "reverse":
            rev = list(reversed(frag_indices))
            parts = [f"{self.prefix}_F[{i}]" for i in rev]
            return " .. ".join(parts)
        elif strategy == "table_builder":
            parts = [f"{self.prefix}_F[{i}]" for i in frag_indices]
            concat_expr = " .. ".join(parts)
            return f"(({concat_expr}))"
        elif strategy == "chunk_mapping":
            parts = [f"{self.prefix}_F[{i}]" for i in frag_indices]
            return " .. ".join(parts)
        else:
            return f'"{self._escape(fragments[0])}"' if fragments else '""'

    def _escape(self, s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            "total_strings": len(self.string_to_idx),
            "total_fragments": len(self.fragment_pool),
            "strategy_distribution": self._count_strategies(),
            "prefix": self.prefix,
        }

    def _count_strategies(self) -> dict[str, int]:
        counts = {}
        for strategy in self.strategy_for_string.values():
            counts[strategy] = counts.get(strategy, 0) + 1
        return counts


class EnhancedStringConstants:
    """
    增强字符串常量处理

    整合分段存储、多策略还原、统一访问接口
    """

    def __init__(
        self,
        rng: random.Random | None = None,
        enable_segmentation: bool = True,
        min_fragment: int = 2,
        max_fragment: int = 8,
    ):
        self.rng = rng
        self.fragment_pool = StringFragmentPool(
            rng=rng,
            min_fragment_length=min_fragment,
            max_fragment_length=max_fragment,
            enable_segmentation=enable_segmentation,
        )
        self.string_index: dict[str, int] = {}
        self.next_idx = 1

    def add_string(self, value: str) -> int:
        """添加字符串，返回索引"""
        if value not in self.string_index:
            idx = self.fragment_pool.intern_string(value)
            self.string_index[value] = idx
            self.next_idx += 1
        return self.string_index[value]

    def generate_lua_code(self) -> str:
        """生成完整的 Lua 代码"""
        lines = []
        lines.append("-- Enhanced String Constants")
        lines.append(self.fragment_pool.generate_lua_pool())
        lines.append("")
        lines.append(self._generate_accessors())
        return "\n".join(lines)

    def _generate_accessors(self) -> str:
        """生成访问函数"""
        lines = []
        prefix = self.fragment_pool.prefix

        # 直接访问（不分段）
        lines.append(f"local function {prefix}_get(idx)")
        lines.append(f"    local frags = {{}}")
        lines.append(f"    local i = 1")
        lines.append(f"    while {prefix}_F[i] do")
        lines.append(f"        frags[i] = {prefix}_F[i]")
        lines.append(f"        i = i + 1")
        lines.append(f"    end")
        lines.append(f"    return table.concat(frags)")
        lines.append(f"end")

        # 按索引还原单个字符串
        for idx in sorted(self.string_index.values()):
            fragments = self.fragment_pool.get_fragments(idx)
            if fragments:
                expr = self.fragment_pool._generate_recovery_expr(fragments, self.fragment_pool.get_strategy(idx))
                lines.append(f"local function {prefix}_str_{idx}() return {expr} end")

        return "\n".join(lines)

    def get_access_call(self, value: str) -> str | None:
        """获取访问调用表达式"""
        if value in self.string_index:
            idx = self.string_index[value]
            strategy = self.fragment_pool.get_strategy(idx)
            fragments = self.fragment_pool.get_fragments(idx)
            if fragments and strategy != "direct":
                return self.fragment_pool._generate_recovery_expr(fragments, strategy)
            else:
                escaped = self.fragment_pool._escape(value)
                return f'"{escaped}"'
        return None

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return self.fragment_pool.get_statistics()


class EnhancedConstantAccessor:
    """
    增强常量访问器

    为常量池中的每个常量提供多种访问方式，通过简单变换函数获取。
    支持统一入口和多样化访问，增加代码结构复杂度而不影响语义。
    """

    def __init__(self, pool: ConstantPool, rng: random.Random | None = None, config: ConstantAccessorConfig | None = None):
        self.pool = pool
        self.rng = rng
        self.config = config if config else ConstantAccessorConfig()
        self.accessor_name = self.config.accessor_prefix if self.config.accessor_prefix else "_acc"
        self.accessor_cache: dict[tuple[str, str], str] = {}  # (type, index) -> accessor_code
        self._id_counter = [0]

    def _gen_id(self) -> int:
        self._id_counter[0] += 1
        return self._id_counter[0]

    def generate_accessors(self) -> str:
        """
        生成所有访问器函数代码

        Returns:
            Lua 访问器函数代码
        """
        if not self.config.enabled:
            return ""

        lines: list[str] = []

        if self.config.use_unified_entry:
            lines.extend(self._generate_unified_accessor())
        else:
            lines.extend(self._generate_separate_accessors())

        return "\n".join(lines)

    def _generate_unified_accessor(self) -> list[str]:
        """生成统一入口访问器"""
        lines: list[str] = []
        prefix = self.accessor_name

        if self.rng:
            func_name = f"{prefix}_{random_lua_identifier(self.rng, 'get')}"
        else:
            func_name = f"{prefix}_get"

        lines.append(f"local function {func_name}(t, k)")
        lines.append(f"    if t == 'S' then")
        lines.append(f"        return {self.pool.pool_prefix}_S[k]")
        lines.append(f"    elseif t == 'N' then")
        lines.append(f"        return {self.pool.pool_prefix}_N[k]")
        lines.append(f"    elseif t == 'B' then")
        lines.append(f"        return {self.pool.pool_prefix}_B[k]")
        lines.append(f"    end")
        lines.append(f"end")

        return lines

    def _generate_separate_accessors(self) -> list[str]:
        """生成分离访问器（支持多样化）"""
        lines: list[str] = []
        prefix = self.accessor_name

        # 字符串访问器
        for value, idx in sorted(self.pool.strings.items(), key=lambda x: x[1]):
            accessor_type = self._select_accessor_type("string")
            code = self._generate_single_accessor("S", idx, value, accessor_type)
            lines.extend(code)

        # 数字访问器
        for value, idx in sorted(self.pool.numbers.items(), key=lambda x: x[1]):
            accessor_type = self._select_accessor_type("number")
            code = self._generate_single_accessor("N", idx, value, accessor_type)
            lines.extend(code)

        # 布尔访问器
        for value, idx in sorted(self.pool.booleans.items(), key=lambda x: x[1]):
            accessor_type = self._select_accessor_type("boolean")
            code = self._generate_single_accessor("B", idx, value, accessor_type)
            lines.extend(code)

        return lines

    def _select_accessor_type(self, value_type: str) -> ConstantAccessorType:
        """选择访问器类型"""
        if not self.config.enable_diversity:
            return ConstantAccessorType.DIRECT

        if self.rng and self.rng.random() > self.config.diversity_ratio:
            return ConstantAccessorType.DIRECT

        if value_type == "string":
            types = [ConstantAccessorType.DIRECT, ConstantAccessorType.TABLE_WRAP]
        elif value_type == "number":
            types = [
                ConstantAccessorType.DIRECT,
                ConstantAccessorType.NEGATED,
                ConstantAccessorType.ADD_ZERO,
                ConstantAccessorType.SUB_ZERO,
                ConstantAccessorType.MUL_ONE,
                ConstantAccessorType.XOR_ZERO,
                ConstantAccessorType.AND_MAX,
                ConstantAccessorType.INDEX_OFFSET,
            ]
        elif value_type == "boolean":
            types = [ConstantAccessorType.DIRECT, ConstantAccessorType.NEGATED, ConstantAccessorType.XOR_ZERO]
        else:
            types = [ConstantAccessorType.DIRECT]

        return self.rng.choice(types) if self.rng else ConstantAccessorType.DIRECT

    def _generate_single_accessor(
        self,
        pool_type: str,
        index: int,
        value: Any,
        accessor_type: ConstantAccessorType
    ) -> list[str]:
        """为单个常量生成访问器代码"""
        lines: list[str] = []
        prefix = self.accessor_name

        if self.rng:
            func_name = f"{prefix}_{pool_type.lower()}_{self._gen_id()}"
        else:
            func_name = f"{prefix}_{pool_type.lower()}_{index}"

        lines.append(f"local function {func_name}()")

        base_expr = f"{self.pool.pool_prefix}_{pool_type}[{index}]"

        if accessor_type == ConstantAccessorType.DIRECT:
            lines.append(f"    return {base_expr}")
        elif accessor_type == ConstantAccessorType.NEGATED and pool_type == "N":
            lines.append(f"    return -{base_expr}")
        elif accessor_type == ConstantAccessorType.ADD_ZERO and pool_type == "N":
            lines.append(f"    return {base_expr} + 0")
        elif accessor_type == ConstantAccessorType.SUB_ZERO and pool_type == "N":
            lines.append(f"    return {base_expr} - 0")
        elif accessor_type == ConstantAccessorType.MUL_ONE and pool_type == "N":
            lines.append(f"    return {base_expr} * 1")
        elif accessor_type == ConstantAccessorType.DIV_ONE and pool_type == "N":
            lines.append(f"    return {base_expr} / 1")
        elif accessor_type == ConstantAccessorType.XOR_ZERO and pool_type in ("N", "B"):
            lines.append(f"    return ({base_expr}) ~ 0")
        elif accessor_type == ConstantAccessorType.AND_MAX and pool_type == "N":
            lines.append(f"    return ({base_expr}) & 0xFFFFFFFF")
        elif accessor_type == ConstantAccessorType.OR_ZERO and pool_type == "N":
            lines.append(f"    return ({base_expr}) | 0")
        elif accessor_type == ConstantAccessorType.INDEX_OFFSET and pool_type == "N":
            lines.append(f"    return {base_expr} - 0 + 0")
        elif accessor_type == ConstantAccessorType.TABLE_WRAP and pool_type == "S":
            lines.append(f"    return ({{{base_expr}}})[1]")
        elif accessor_type == ConstantAccessorType.NEGATED and pool_type == "B":
            lines.append(f"    return not {base_expr}")
        else:
            lines.append(f"    return {base_expr}")

        lines.append("end")

        # 缓存映射
        self.accessor_cache[(pool_type, str(index))] = func_name

        return lines

    def get_accessor_call(self, pool_type: str, index: int) -> str:
        """
        获取常量访问调用代码

        Args:
            pool_type: 池类型 ('S', 'N', 'B')
            index: 常量索引

        Returns:
            访问器调用表达式
        """
        key = (pool_type, str(index))

        if self.config.use_unified_entry and self.config.enabled:
            if self.rng:
                func_name = f"{self.accessor_name}_{random_lua_identifier(self.rng, 'get')}"
            else:
                func_name = f"{self.accessor_name}_get"
            return f"{func_name}('{pool_type}', {index})"

        if key in self.accessor_cache:
            return f"{self.accessor_cache[key]}()"

        if self.config.enabled:
            accessor_type = self._select_accessor_type(
                "string" if pool_type == "S" else ("number" if pool_type == "N" else "boolean")
            )
            value = self._get_value_for_index(pool_type, index)
            if value is not None:
                self._generate_single_accessor(pool_type, index, value, accessor_type)
                return f"{self.accessor_cache[key]}()"

        fallback = f"{self.pool.pool_prefix}_{pool_type}get({index})"
        return fallback

    def _get_value_for_index(self, pool_type: str, index: int) -> Any:
        """根据索引获取常量值"""
        if pool_type == "S":
            for v, i in self.pool.strings.items():
                if i == index:
                    return v
        elif pool_type == "N":
            for v, i in self.pool.numbers.items():
                if i == index:
                    return v
        elif pool_type == "B":
            for v, i in self.pool.booleans.items():
                if i == index:
                    return v
        return None

    def generate_replacement_expr(self, literal: str, literal_type: str) -> str | None:
        """生成常量替换表达式（使用增强访问器）"""
        if not self.config.enabled:
            return None

        if literal_type == "string" and literal in self.pool.strings:
            idx = self.pool.strings[literal]
            return self.get_accessor_call("S", idx)
        elif literal_type == "number":
            try:
                num_val = float(literal)
                if num_val in self.pool.numbers:
                    idx = self.pool.numbers[num_val]
                    return self.get_accessor_call("N", idx)
            except ValueError:
                pass
        elif literal_type == "boolean":
            try:
                bool_val = literal.lower() == "true"
                if bool_val in self.pool.booleans:
                    idx = self.pool.booleans[bool_val]
                    return self.get_accessor_call("B", idx)
            except ValueError:
                pass
        return None

    def get_statistics(self) -> dict:
        """获取增强访问器统计"""
        return {
            "enabled": self.config.enabled,
            "use_unified_entry": self.config.use_unified_entry,
            "enable_diversity": self.config.enable_diversity,
            "accessor_count": len(self.accessor_cache),
            "accessor_name": self.accessor_name,
        }


class ConstantPoolEnhancer:
    """
    常量池增强器

    整合增强常量访问系统，提供完整的常量池增强功能。
    """

    def __init__(self, pool: ConstantPool, rng: random.Random | None = None):
        self.pool = pool
        self.rng = rng
        self.accessor_config = ConstantAccessorConfig()
        self.accessor: EnhancedConstantAccessor | None = None

    def enable_enhanced_access(self, config: ConstantAccessorConfig | None = None) -> None:
        """启用增强访问"""
        if config:
            self.accessor_config = config
        self.accessor_config.enabled = True
        self.accessor = EnhancedConstantAccessor(self.pool, self.rng, self.accessor_config)

    def generate_enhanced_pool_code(self) -> str:
        """生成增强后的常量池代码"""
        lines: list[str] = []

        lines.append(self.pool.generate_pool_table())

        if self.accessor and self.accessor_config.enabled:
            accessor_code = self.accessor.generate_accessors()
            if accessor_code:
                lines.append(accessor_code)

        return "\n".join(lines)

    def replace_literal(self, literal: str, literal_type: str) -> str:
        """替换字面量为增强访问"""
        if self.accessor and self.accessor_config.enabled:
            expr = self.accessor.generate_replacement_expr(literal, literal_type)
            if expr:
                return expr

        return self.pool.generate_replacement_expr(literal, literal_type) or literal

    def replace_literals_in_content(self, content: str) -> str:
        """在代码内容中替换字面量"""
        result = content

        for value, idx in self.pool.strings.items():
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            old_pattern = f'"{escaped}"'
            new_expr = self.replace_literal(value, "string")
            result = result.replace(old_pattern, new_expr)

        for value, idx in self.pool.numbers.items():
            old_pattern = str(value)
            new_expr = self.replace_literal(str(value), "number")
            result = result.replace(old_pattern, new_expr)

        for value, idx in self.pool.booleans.items():
            old_pattern = str(value).lower()
            new_expr = self.replace_literal(str(value).lower(), "boolean")
            result = result.replace(old_pattern, new_expr)

        return result


@dataclass
class EncodedString:
    hex_payload: str
    payload_head: str
    payload_tail: str
    key: int
    state: int
    variant: int


@dataclass
class ApiIndirectionPlan:
    prelude: str
    replacements: int


class ScopeStack:
    def __init__(self) -> None:
        self._scopes: list[dict[str, str]] = []

    def push(self) -> None:
        self._scopes.append({})

    def pop(self) -> None:
        if self._scopes:
            self._scopes.pop()

    def declare(self, original: str, alias: str) -> str:
        if not self._scopes:
            self.push()
        self._scopes[-1][original] = alias
        return alias

    def resolve(self, original: str) -> str | None:
        for scope in reversed(self._scopes):
            alias = scope.get(original)
            if alias is not None:
                return alias
        return None


class ProtectionProfile:
    def __init__(self, rng: random.Random, watermark: str) -> None:
        self.watermark = watermark
        self.marker_name = random_lua_identifier(rng, "_m")
        self.char_name = random_lua_identifier(rng, "_c")
        self.sub_name = random_lua_identifier(rng, "_s")
        self.byte_name = random_lua_identifier(rng, "_b")
        self.concat_name = random_lua_identifier(rng, "_t")
        self.tonumber_name = random_lua_identifier(rng, "_n")
        self.cache_name = random_lua_identifier(rng, "_cc")
        self.pool_name = random_lua_identifier(rng, "_pp")
        self.hex_pair_name = random_lua_identifier(rng, "_hx")
        self.decode_names = [random_lua_identifier(rng, "_dx") for _ in range(4)]
        self.fetch_names = [random_lua_identifier(rng, "_fx") for _ in range(4)]
        self.number_name = random_lua_identifier(rng, "_ix")
        self.value_wrap_name = random_lua_identifier(rng, "_vw")
        self.return_temp_name = random_lua_identifier(rng, "_rv")
        self.push_name = random_lua_identifier(rng, "_ap")
        self.store_name = random_lua_identifier(rng, "_st")
        self.read_name = random_lua_identifier(rng, "_rd")
        self.out_name = random_lua_identifier(rng, "_o")
        self.state_name = random_lua_identifier(rng, "_q")
        self.index_name = random_lua_identifier(rng, "_i")
        self.mask_name = random_lua_identifier(rng, "_k")
        self.byte_temp_name = random_lua_identifier(rng, "_v")
        self.arg_a = random_lua_identifier(rng, "_a")
        self.arg_b = random_lua_identifier(rng, "_d")
        self.arg_c = random_lua_identifier(rng, "_e")
        self.handle_map_name = random_lua_identifier(rng, "_hd")
        self.handle_field = random_lua_identifier(rng, "h")
        self.slot_field = random_lua_identifier(rng, "p")
        self.resolve_name = random_lua_identifier(rng, "_rs")
        self.cache_lookup_name = random_lua_identifier(rng, "_ck")
        self.cache_resolve_name = random_lua_identifier(rng, "_cr")
        self.lookup_name = random_lua_identifier(rng, "_lk")
        self.lookup_resolve_name = random_lua_identifier(rng, "_lr")
        self.pool_lookup_name = random_lua_identifier(rng, "_pk")
        self.pool_resolve_name = random_lua_identifier(rng, "_pr")
        self.field_map_name = random_lua_identifier(rng, "_fm")
        self.field_resolve_name = random_lua_identifier(rng, "_fd")
        self.payload_join_name = random_lua_identifier(rng, "_pj")
        self.nibble_map_name = random_lua_identifier(rng, "_hm")

        self.number_pad = 1000 + rng.randint(0, 8999)
        self.number_bias = 11 + rng.randint(0, 88)
        self.runtime_variant = rng.randint(0, 1)
        self.expression_variant = rng.randint(0, 2)
        self.fetch_variant = rng.randint(0, 2)
        self.value_wrap_variant = rng.randint(0, 2)
        self.helper_return_variant = rng.randint(0, 1)
        self.state_multipliers = [17 + (rng.randint(0, 59) * 2) for _ in range(4)]
        self.state_increments = [3 + rng.randint(0, 119) for _ in range(4)]
        self.encoded_alphabet = shuffled_alphabet(rng)
        self.payload_field = random_lua_identifier(rng, "s")
        self.key_field = random_lua_identifier(rng, "k")
        self.state_field = random_lua_identifier(rng, "i")
        self.payload_field_index = 10 + rng.randint(0, 89)
        self.payload_tail_field_index = 60 + rng.randint(0, 89)
        self.key_field_index = 110 + rng.randint(0, 89)
        self.state_field_index = 210 + rng.randint(0, 89)
        self.slot_field_index = 310 + rng.randint(0, 89)
        self.handle_field_index = 410 + rng.randint(0, 89)
        self.lookup_bias = 40 + rng.randint(0, 179)
        self.cache_bias = 300 + rng.randint(0, 699)
        self.pool_bias = 150 + rng.randint(0, 499)
        self.slot_bias = 23 + rng.randint(0, 159)

        self.string_pool_indexes: dict[str, int] = {}
        self.string_storage_indexes: dict[str, int] = {}
        self.string_public_indexes: dict[str, int] = {}
        self.public_to_physical_indexes: dict[int, int] = {}
        self.public_to_handle_indexes: dict[int, int] = {}
        self.public_to_cache_indexes: dict[int, int] = {}
        self.handle_to_encoded_physical_indexes: dict[int, int] = {}
        self.physical_to_storage_indexes: dict[int, int] = {}
        self.pool_key_order: list[str] = []
        self.used_public_indexes: set[int] = set()
        self.used_handle_indexes: set[int] = set()
        self.used_cache_indexes: set[int] = set()
        self.used_storage_indexes: set[int] = set()
        self.string_pool_by_key: dict[str, EncodedString] = {}

        # 代码布局随机化配置
        self.layout_randomization_enabled = rng.random() > 0.5
        self.layout_strategy = rng.choice(list(LayoutStrategy))
        self.layout_group_size = 2 + rng.randint(0, 3)
        self.layout_swap_iterations = 3 + rng.randint(0, 5)
        self.layout_preserve_entry = rng.random() > 0.3
        self.layout_preserve_exit = rng.random() > 0.3
        self.layout_cluster_depth = 2 + rng.randint(0, 2)

        # 增强常量访问配置
        self.enhanced_accessor_enabled = rng.random() > 0.5
        self.accessor_prefix = random_lua_identifier(rng, "_acc")
        self.use_unified_accessor = rng.random() > 0.4
        self.accessor_diversity_ratio = 0.2 + rng.random() * 0.3

        if self.expression_variant == 0:
            self.nil_expression = "({})[" + self.number_name + "(1,0)]"
        else:
            self.nil_expression = (
                "({[" + self.number_name + "(1,0)]=" + self.false_expression() + "})["
                + self.number_name
                + "(2,1)]"
            )

    def next_local_name(self, rng: random.Random) -> str:
        return random_lua_identifier(rng, "_l")

    def true_expression(self) -> str:
        if self.expression_variant == 0:
            return "(not not " + self.number_name + "(1,0))"
        return "(" + self.number_name + "(1,0)==" + self.number_name + "(1,0))"

    def false_expression(self) -> str:
        if self.expression_variant == 0:
            return "(not " + self.number_name + "(1,0))"
        return "(" + self.number_name + "(1,0)~=" + self.number_name + "(1,0))"

    def runtime_int_expression(self, value: int) -> str:
        offset = self.number_bias + 13
        if self.value_wrap_variant == 0:
            return f"{self.number_name}({value + offset},{offset})"
        if self.value_wrap_variant == 1:
            return f"(({self.number_name}({value + offset},{offset})+{self.number_bias})-{self.number_bias})"
        return self.wrap_value_expression(f"{self.number_name}({value + offset},{offset})")

    def wrap_value_expression(self, expression: str) -> str:
        return f"{self.value_wrap_name}({expression})"

    def wrap_fetch_call(self, public_index: int, variant: int) -> str:
        encoded_index = self.runtime_int_expression(public_index)
        fetch_name = self.fetch_names[variant % len(self.fetch_names)]
        if self.fetch_variant == 0:
            base = f"{fetch_name}({encoded_index})"
        elif self.fetch_variant == 1:
            base = f"({fetch_name}({encoded_index})..\"\")"
        else:
            base = (
                f"((function({self.arg_a})return {self.arg_a} end)"
                f"({fetch_name}({encoded_index})))"
            )
        return self.wrap_value_expression(base)

    def intern_string(self, value: bytes, rng: random.Random) -> str:
        key = to_hex_key(value)
        physical_index = self.string_pool_indexes.get(key)
        if physical_index is None:
            physical_index = len(self.string_pool_indexes) + 1
            self.string_pool_indexes[key] = physical_index
            self.pool_key_order.append(key)
            public_index = self.next_public_index(rng)
            handle_index = self.next_handle_index(rng)
            cache_index = self.next_cache_index(rng)
            storage_index = self.next_storage_index(rng)
            self.string_public_indexes[key] = public_index
            self.string_storage_indexes[key] = storage_index
            self.public_to_handle_indexes[public_index] = handle_index
            self.public_to_cache_indexes[public_index] = cache_index
            self.public_to_physical_indexes[public_index] = physical_index
            self.handle_to_encoded_physical_indexes[handle_index] = physical_index + self.slot_bias
            self.string_pool_by_key[key] = encode_lua_bytes(value, rng, self)
        encoded = self.string_pool_by_key[key]
        return self.wrap_fetch_call(self.string_public_indexes[key], encoded.variant)

    def next_public_index(self, rng: random.Random) -> int:
        while True:
            candidate = 19 + rng.randint(0, 899)
            if candidate not in self.used_public_indexes:
                self.used_public_indexes.add(candidate)
                return candidate

    def next_handle_index(self, rng: random.Random) -> int:
        while True:
            candidate = 100 + rng.randint(0, 799)
            if candidate not in self.used_handle_indexes:
                self.used_handle_indexes.add(candidate)
                return candidate

    def next_cache_index(self, rng: random.Random) -> int:
        while True:
            candidate = 1000 + rng.randint(0, 7999)
            if candidate not in self.used_cache_indexes:
                self.used_cache_indexes.add(candidate)
                return candidate

    def next_storage_index(self, rng: random.Random) -> int:
        while True:
            candidate = 200 + rng.randint(0, 3999)
            if candidate not in self.used_storage_indexes:
                self.used_storage_indexes.add(candidate)
                return candidate

    def finalize_pool_layout(self, rng: random.Random) -> None:
        if len(self.pool_key_order) < 2:
            return
        shuffled = list(self.pool_key_order)
        rng.shuffle(shuffled)
        self.string_pool_indexes.clear()
        self.public_to_physical_indexes.clear()
        self.handle_to_encoded_physical_indexes.clear()
        self.physical_to_storage_indexes.clear()
        for index, key in enumerate(shuffled, start=1):
            self.string_pool_indexes[key] = index
            storage_index = self.string_storage_indexes.get(key)
            if storage_index is not None:
                self.physical_to_storage_indexes[index] = storage_index
            public_index = self.string_public_indexes.get(key)
            if public_index is not None:
                self.public_to_physical_indexes[public_index] = index
                handle_index = self.public_to_handle_indexes.get(public_index)
                if handle_index is not None:
                    self.handle_to_encoded_physical_indexes[handle_index] = index + self.slot_bias
        self.pool_key_order = shuffled


class Tokenizer:
    def __init__(self, source: str) -> None:
        self.source = source
        self.index = 0

    def has_more(self) -> bool:
        return self.index < len(self.source)

    def next_token(self) -> Token:
        current = self.source[self.index]
        if current == "\ufeff":
            self.index += 1
            return Token(TokenType.WHITESPACE, "")
        if current.isspace():
            return self.read_whitespace()
        if current == "-" and self.peek(1) == "-":
            return self.read_comment()
        if current in ("'", '"'):
            return self.read_quoted_string(current)
        if current == "[":
            level = self.long_bracket_level(self.index)
            if level >= 0:
                return self.read_long_string(level)
        if current.isdigit():
            return self.read_number()
        if is_identifier_start(current):
            return self.read_identifier_or_keyword()
        return self.read_symbol()

    def read_whitespace(self) -> Token:
        start = self.index
        while self.index < len(self.source) and self.source[self.index].isspace():
            self.index += 1
        return Token(TokenType.WHITESPACE, self.source[start:self.index])

    def read_comment(self) -> Token:
        start = self.index
        self.index += 2
        if self.index < len(self.source) and self.source[self.index] == "[":
            level = self.long_bracket_level(self.index)
            if level >= 0:
                self.index += level + 2
                while self.index < len(self.source):
                    if self.source[self.index] == "]" and self.matches_long_bracket_end(self.index, level):
                        self.index += level + 2
                        break
                    self.index += 1
                return Token(TokenType.COMMENT, self.source[start:self.index])
        while self.index < len(self.source) and self.source[self.index] != "\n":
            self.index += 1
        return Token(TokenType.COMMENT, self.source[start:self.index])

    def read_quoted_string(self, quote: str) -> Token:
        start = self.index
        self.index += 1
        value: list[str] = []
        while self.index < len(self.source):
            current = self.source[self.index]
            self.index += 1
            if current == quote:
                break
            if current != "\\" or self.index >= len(self.source):
                value.append(current)
                continue
            escaped = self.source[self.index]
            self.index += 1
            if escaped == "a":
                value.append("\a")
            elif escaped == "b":
                value.append("\b")
            elif escaped == "f":
                value.append("\f")
            elif escaped == "n":
                value.append("\n")
            elif escaped == "r":
                value.append("\r")
            elif escaped == "t":
                value.append("\t")
            elif escaped == "v":
                value.append("\v")
            elif escaped in ("\\", '"', "'"):
                value.append(escaped)
            elif escaped == "\n":
                value.append("\n")
            elif escaped == "\r":
                value.append("\r")
                if self.index < len(self.source) and self.source[self.index] == "\n":
                    self.index += 1
                    value.append("\n")
            elif escaped == "z":
                while self.index < len(self.source) and self.source[self.index].isspace():
                    self.index += 1
            elif escaped == "x":
                value.append(self.read_hex_escape())
            elif escaped.isdigit():
                value.append(self.read_decimal_escape(escaped))
            else:
                value.append(escaped)
        return Token(
            TokenType.STRING,
            self.source[start:self.index],
            "".join(value).encode("utf-8"),
        )

    def read_hex_escape(self) -> str:
        if self.index + 1 > len(self.source) - 1:
            return "x"
        first = self.source[self.index]
        second = self.source[self.index + 1]
        self.index += 2
        if not is_hex_digit(first) or not is_hex_digit(second):
            return second
        return chr(int(first + second, 16))

    def read_decimal_escape(self, first_digit: str) -> str:
        digits = [first_digit]
        consumed = 0
        while self.index < len(self.source) and self.source[self.index].isdigit() and consumed < 2:
            digits.append(self.source[self.index])
            self.index += 1
            consumed += 1
        return chr(int("".join(digits), 10))

    def read_long_string(self, level: int) -> Token:
        start = self.index
        self.index += level + 2
        content_start = self.index
        while self.index < len(self.source):
            if self.source[self.index] == "]" and self.matches_long_bracket_end(self.index, level):
                content = self.source[content_start:self.index]
                self.index += level + 2
                return Token(TokenType.STRING, self.source[start:self.index], content.encode("utf-8"))
            self.index += 1
        raise ValueError("Unterminated long string literal")

    def read_number(self) -> Token:
        start = self.index
        if self.source[self.index] == "0" and self.peek(1) in ("x", "X"):
            self.index += 2
            while self.index < len(self.source) and is_hex_digit(self.source[self.index]):
                self.index += 1
            return Token(TokenType.NUMBER, self.source[start:self.index])
        while self.index < len(self.source) and self.source[self.index].isdigit():
            self.index += 1
        if self.index < len(self.source) and self.source[self.index] == "." and self.peek(1) != ".":
            self.index += 1
            while self.index < len(self.source) and self.source[self.index].isdigit():
                self.index += 1
        if self.index < len(self.source) and self.source[self.index] in ("e", "E"):
            exponent_index = self.index + 1
            if exponent_index < len(self.source) and self.source[exponent_index] in ("+", "-"):
                exponent_index += 1
            has_digits = False
            while exponent_index < len(self.source) and self.source[exponent_index].isdigit():
                exponent_index += 1
                has_digits = True
            if has_digits:
                self.index = exponent_index
        return Token(TokenType.NUMBER, self.source[start:self.index])

    def read_identifier_or_keyword(self) -> Token:
        start = self.index
        self.index += 1
        while self.index < len(self.source) and is_identifier_part(self.source[self.index]):
            self.index += 1
        value = self.source[start:self.index]
        token_type = TokenType.KEYWORD if value in LUA_KEYWORDS else TokenType.IDENTIFIER
        return Token(token_type, value)

    def read_symbol(self) -> Token:
        start = self.index
        self.index += 1
        triple = self.source[start:start + 3]
        if triple == "...":
            self.index = start + 3
            return Token(TokenType.SYMBOL, "...")
        doubled = self.source[start:start + 2]
        if doubled in {"==", "~=", "<=", ">=", "::", ".."}:
            self.index = start + 2
            return Token(TokenType.SYMBOL, doubled)
        return Token(TokenType.SYMBOL, self.source[start:start + 1])

    def long_bracket_level(self, position: int) -> int:
        if position >= len(self.source) or self.source[position] != "[":
            return -1
        cursor = position + 1
        level = 0
        while cursor < len(self.source) and self.source[cursor] == "=":
            level += 1
            cursor += 1
        if cursor < len(self.source) and self.source[cursor] == "[":
            return level
        return -1

    def matches_long_bracket_end(self, position: int, level: int) -> bool:
        if position >= len(self.source) or self.source[position] != "]":
            return False
        cursor = position + 1
        for _ in range(level):
            if cursor >= len(self.source) or self.source[cursor] != "=":
                return False
            cursor += 1
        return cursor < len(self.source) and self.source[cursor] == "]"

    def peek(self, offset: int) -> str:
        target = self.index + offset
        if target < len(self.source):
            return self.source[target]
        return "\0"


def transform(source: str, watermark: str) -> str:
    """主入口函数，使用多阶段 Pipeline 架构"""
    return transform_v2(source, watermark)

def indent_lua(code: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(
        pad + line if line.strip() else line
        for line in code.splitlines()
    )

def tokenize(source: str) -> list[Token]:
    tokenizer = Tokenizer(source)
    tokens: list[Token] = []
    while tokenizer.has_more():
        tokens.append(tokenizer.next_token())
    return tokens


# ===== 多阶段 Pipeline 代码生成架构 =====


@dataclass
class PipelineState:
    """
    Pipeline 状态容器

    保存各阶段之间的数据流，确保类型安全和可追踪。
    """
    # 阶段 1: Tokenize 结果
    source: str = ""
    tokens: list[Token] = None

    # 阶段 2: Block 构建结果
    blocks: list[CodeBlock] = None
    program: BlockProgram = None
    block_map: dict[int, CodeBlock] = None

    # 阶段 3: 指令转换结果
    instructions: dict[int, BlockInstructions] = None
    instruction_layer: InstructionLayer = None

    # 阶段 4: Emit 结果
    emitted_code: str = ""

    # 元数据
    metadata: dict = None

    def __post_init__(self):
        self.tokens = self.tokens or []
        self.blocks = self.blocks or []
        self.block_map = self.block_map or {}
        self.instructions = self.instructions or {}
        self.metadata = self.metadata or {}


def build_blocks(
    source: str,
    profile: ProtectionProfile,
    rng: random.Random,
) -> PipelineState:
    """
    阶段 1: 构建 Block 结构

    输入: source 代码字符串
    输出: PipelineState，包含 tokens 和 blocks

    职责:
    - 分词 (tokenize)
    - Token 重写 (rewrite)
    - 拆分为 blocks
    - 依赖分析和链接
    - 构建 BlockProgram
    """
    state = PipelineState(source=source)

    # 分词
    tokenizer = Tokenizer(source)
    state.tokens = []
    while tokenizer.has_more():
        state.tokens.append(tokenizer.next_token())

    # Token 重写
    rewrite_tokens(state.tokens, profile, rng)

    # 拆分为 blocks
    state.blocks = split_into_blocks(state.tokens, rng)

    # 依赖分析
    state.blocks = analyze_block_dependencies(state.blocks)

    # 块链接
    state.blocks = link_blocks_sequentially(state.blocks)

    # 记录原始顺序
    for block in state.blocks:
        block.metadata["original_order"] = block.block_id

    # 构建 block_map
    state.block_map = {b.block_id: b for b in state.blocks}

    # 构建 BlockProgram
    state.program = BlockProgram(
        blocks=state.blocks,
        execution_order=list(range(1, len(state.blocks) + 1)),
        block_map=state.block_map,
        entry_block_id=1 if state.blocks else None,
    )

    return state


def blocks_to_instructions(
    state: PipelineState,
    profile: ProtectionProfile,
    rng: random.Random,
) -> PipelineState:
    """
    阶段 2: 将 Blocks 转换为指令序列

    输入: PipelineState (包含 blocks)
    输出: PipelineState (包含 instructions)

    职责:
    - 应用常量池（可选）
    - 应用 Block 扩展（可选）
    - 将每个 Block 转换为指令列表
    - 保存到 state.instructions
    """
    # 应用常量池
    if profile.constant_pool_enabled:
        state.blocks, pool, _ = apply_constant_pool_stage(
            state.blocks, state.tokens, rng, use_pool=True
        )
        if pool:
            state.metadata["constant_pool"] = pool

    # 应用 Block 结构扩展
    state.blocks = apply_block_structure_extension(state.blocks, rng)

    # 转换 blocks 为指令
    state.instruction_layer = InstructionLayer(rng)
    state.instructions = state.instruction_layer.process_blocks(state.blocks)

    return state


def emit_lua_from_instructions(
    state: PipelineState,
    profile: ProtectionProfile,
    rng: random.Random,
) -> PipelineState:
    """
    阶段 3: 从指令生成 Lua 代码

    输入: PipelineState (包含 instructions)
    输出: PipelineState (包含 emitted_code)

    职责:
    - 为每个 block 生成 Lua 函数
    - 生成 program 表结构
    - 生成 dispatcher 代码
    - 组装最终代码字符串
    """
    generator = BlockGenerator(profile, rng)

    # 生成 program 表
    program_lines: list[str] = []
    program_lines.append("local program = {")

    for idx, bid in enumerate(state.program.execution_order):
        block = state.program.get_block(bid)
        if block:
            next_id = block.next_id
            func_def = generator.generate_function(block, idx + 1, next_id)

            # 生成分支表
            branches_repr = "nil"
            if block.has_branches():
                branches_repr = "{"
                branch_parts = []
                for cond, target in block.branches.items():
                    t = target if target is not None else "nil"
                    branch_parts.append(f"{cond}={t}")
                branches_repr += ", ".join(branch_parts) + "}"

            # 生成辅助路径
            aux_paths_repr = "nil"
            if block.has_auxiliary_paths():
                aux_paths_repr = "{"
                path_parts = []
                for aux_path in block.auxiliary_paths:
                    target = aux_path.get("target", "nil")
                    path_parts.append(
                        f"{{id={aux_path['path_id']},type='{aux_path['path_type']}',target={target}}}"
                    )
                aux_paths_repr += ", ".join(path_parts) + "}"

            program_lines.append(f"    [{idx + 1}] = {{")
            program_lines.append(f"        fn = function()")
            for fn_line in func_def.split("\n"):
                if "local function" in fn_line:
                    continue
                if fn_line.strip():
                    program_lines.append("            " + fn_line.strip())
            program_lines.append(f"        end,")
            program_lines.append(f"        type = '{block.block_type}',")
            program_lines.append(f"        next_id = {next_id if next_id is not None else 'nil'},")
            program_lines.append(f"        branches = {branches_repr},")
            program_lines.append(f"        auxiliary_paths = {aux_paths_repr},")
            program_lines.append(f"    }},")

    program_lines.append("}")
    state.emitted_code = "\n".join(program_lines)

    return state


def execute_pipeline(
    source: str,
    profile: ProtectionProfile,
    rng: random.Random,
) -> PipelineState:
    """
    执行完整 Pipeline

    按顺序执行所有阶段，返回最终状态。
    """
    # 阶段 1: 构建 blocks
    state = build_blocks(source, profile, rng)

    # 阶段 2: 转换为指令
    state = blocks_to_instructions(state, profile, rng)

    # 阶段 3: 发射 Lua 代码
    state = emit_lua_from_instructions(state, profile, rng)

    return state


def transform_v2(source: str, watermark: str) -> str:
    """
    新版本 transform 函数

    使用清晰的多阶段 Pipeline 架构。
    """
    source = strip_leading_bom(source)
    random.seed(int(time.time()))
    rng = create_time_seeded_random()
    profile = ProtectionProfile(rng, watermark)

    randomize_algorithms(profile, rng)
    shuffle_tables(profile, rng)

    # 执行 Pipeline
    state = execute_pipeline(source, profile, rng)

    # 获取生成结果
    program_wrapper = state.emitted_code
    constant_pool_code = ""

    if "constant_pool" in state.metadata:
        pool = state.metadata["constant_pool"]
        constant_pool_code = pool.generate_pool_table() + "\n"

    # API 前导码
    api_plan = apply_api_indirection(state.tokens, profile, rng)

    # 生成 dispatcher
    dispatcher = ExecutionDispatcher(profile, rng)
    dispatcher_code = dispatcher.generate_dispatcher(state.program, mode="sequential")

    # 组装最终代码
    return (
        "--[[\n"
        + "Lua Protector Watermark: "
        + sanitize_comment(watermark)
        + "\nGenerated by Python transformer\n"
        + "Pipeline architecture: tokenize -> blocks -> instructions -> emit\n"
        + "Features: constant pool + block structure + instruction layer + dispatcher\n"
        + "]]\n"
        + build_runtime_prelude(profile)
        + api_plan.prelude
        + "\n"
        + constant_pool_code
        + program_wrapper
        + "\n"
        + dispatcher_code
        + "\n"
    )


# ===== 多阶段代码生成架构：代码块拆分 =====
STATEMENT_ENDERS = frozenset({";", "\n"})
STATEMENT_KEYWORDS = frozenset({"local", "if", "for", "while", "repeat", "function", "return", "break", "continue", "do", "end"})
BLOCK_STARTERS = frozenset({"function", "if", "for", "while", "repeat", "do"})


def split_into_blocks(tokens: list[Token], rng: random.Random) -> list[CodeBlock]:
    """
    将 token 流拆分为多个代码块。
    策略：按语句边界拆分，保留控制流结构的完整性，支持分支检测。
    """
    significant_tokens = [t for t in tokens if t.type not in (TokenType.WHITESPACE, TokenType.COMMENT)]

    if not significant_tokens:
        return []

    blocks: list[CodeBlock] = []
    current_tokens: list[Token] = []
    block_id_counter = [1]
    block_depth = [0]
    pending_if_endpoints: list[tuple[int, int]] = []  # (block_id, else_target_id)

    def classify_block(tokens_in_block: list[Token]) -> str:
        if not tokens_in_block:
            return BlockTypeLegacy.STATEMENT.value
        first = tokens_in_block[0]
        if first.is_keyword("function"):
            return BlockTypeLegacy.FUNCTION_DEF.value
        if first.is_keyword("if") or first.is_keyword("while") or first.is_keyword("for") or first.is_keyword("repeat"):
            return BlockTypeLegacy.CONTROL_STRUCT.value
        if first.is_keyword("local") and len(tokens_in_block) > 1 and tokens_in_block[1].type is TokenType.KEYWORD:
            return BlockTypeLegacy.FUNCTION_DEF.value
        if first.type is TokenType.IDENTIFIER and len(tokens_in_block) >= 3:
            if tokens_in_block[1].text == "=" and tokens_in_block[2].text == "{":
                return BlockTypeLegacy.TABLE_DEF.value
        return BlockTypeLegacy.STATEMENT.value

    def detect_branches(tokens_in_block: list[Token]) -> dict:
        """检测块中的条件分支"""
        branches = {}
        for i, token in enumerate(tokens_in_block):
            if token.is_keyword("if"):
                branches["conditional"] = True
                branches["condition_start"] = i
            elif token.is_keyword("else") or token.is_keyword("elseif"):
                branches["has_else"] = True
            elif token.is_keyword("while") or token.is_keyword("for"):
                branches["loop"] = True
                branches["loop_target"] = block_id_counter[0] + 1
        return branches

    def finalize_block(tokens_in_block: list[Token], bid_counter: list[int], depth: list[int]) -> CodeBlock:
        content = render_tokens(tokens_in_block)
        block_type = classify_block(tokens_in_block)
        branch_info = detect_branches(tokens_in_block)
        block = CodeBlock(
            block_id=bid_counter[0],
            content=content,
            block_type=block_type,
            metadata={"depth": depth[0], "branches": branch_info}
        )
        bid_counter[0] += 1
        return block

    i = 0
    while i < len(significant_tokens):
        token = significant_tokens[i]
        current_tokens.append(token)

        is_block_starter = token.is_keyword("function") or token.is_keyword("if") or \
                           token.is_keyword("for") or token.is_keyword("while") or \
                           token.is_keyword("repeat") or token.is_keyword("do")

        if is_block_starter:
            block_depth[0] += 1

        is_block_ender = token.is_keyword("end") or token.is_keyword("until")
        if is_block_ender:
            block_depth[0] = max(0, block_depth[0] - 1)

        is_statement_end = token.is_symbol(";") or (token.is_symbol("\n") and block_depth[0] == 0)

        if is_statement_end and block_depth[0] == 0 and current_tokens:
            blocks.append(finalize_block(current_tokens, block_id_counter, block_depth))
            current_tokens = []

        i += 1

    if current_tokens:
        blocks.append(finalize_block(current_tokens, block_id_counter, block_depth))

    return blocks


def render_tokens(tokens: list[Token]) -> str:
    """将 token 列表渲染为 Lua 代码字符串"""
    parts: list[str] = []
    previous: Token | None = None
    for token in tokens:
        if token.type in (TokenType.COMMENT, TokenType.WHITESPACE):
            continue
        if previous is not None and needs_space(previous, token):
            parts.append(" ")
        parts.append(token.rendered())
        previous = token
    return "".join(parts)


def analyze_block_dependencies(blocks: list[CodeBlock]) -> list[CodeBlock]:
    """
    分析块之间的依赖关系。
    目前基于简单的启发式：后定义的局部变量被后续块使用。
    """
    symbol_scopes: dict[str, int] = {}

    for idx, block in enumerate(blocks):
        deps: set[int] = set()

        for j in range(idx):
            deps.add(j)

        block.dependencies = list(deps)

    return blocks


def link_blocks_sequentially(blocks: list[CodeBlock]) -> list[CodeBlock]:
    """
    将块按 block_id 顺序链接，设置 next_id。
    支持简单条件分支的跳转关系设置。
    """
    if not blocks:
        return blocks

    sorted_blocks = sorted(blocks, key=lambda b: b.block_id)
    id_to_block = {b.block_id: b for b in sorted_blocks}

    for i, block in enumerate(sorted_blocks):
        branches = block.metadata.get("branches", {})

        if block.block_type == BlockTypeLegacy.CONTROL_STRUCT.value:
            if branches.get("loop"):
                loop_target = i + 1
                if loop_target < len(sorted_blocks):
                    block.set_branch("loop", sorted_blocks[loop_target].block_id)

        if i < len(sorted_blocks) - 1:
            block.set_next(sorted_blocks[i + 1].block_id)
        else:
            block.set_next(None)

    return blocks


# ===== 常量池阶段：字面量收集与替换 =====

class LiteralCollector:
    """收集代码中的字面量"""

    def __init__(self):
        self.strings: dict[str, int] = {}
        self.numbers: dict[str, int] = {}
        self.booleans: dict[str, int] = {}

    def collect_from_tokens(self, tokens: list[Token]) -> None:
        """从 token 流收集字面量"""
        for token in tokens:
            if token.type is TokenType.STRING and token.bytes_value is not None:
                try:
                    s = token.bytes_value.decode("utf-8")
                    if s not in self.strings:
                        self.strings[s] = len(self.strings) + 1
                except UnicodeDecodeError:
                    pass
            elif token.type is TokenType.NUMBER:
                if token.text not in self.numbers:
                    self.numbers[token.text] = len(self.numbers) + 1

    def collect_from_content(self, content: str) -> None:
        """从代码内容中收集字面量"""
        import re
        string_pattern = r'"([^"\\]*(?:\\.[^"\\]*)*)"'
        for match in re.finditer(string_pattern, content):
            s = match.group(1)
            s = s.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")
            if s not in self.strings:
                self.strings[s] = len(self.strings) + 1

        number_pattern = r'\b(\d+\.?\d*)\b'
        for match in re.finditer(number_pattern, content):
            num_str = match.group(1)
            if num_str not in self.numbers:
                self.numbers[num_str] = len(self.numbers) + 1

    def get_statistics(self) -> dict:
        return {
            "strings": len(self.strings),
            "numbers": len(self.numbers),
            "booleans": len(self.booleans),
            "total": len(self.strings) + len(self.numbers) + len(self.booleans),
        }


class LiteralReplacer:
    """将代码中的字面量替换为常量池访问"""

    def __init__(self, constant_pool: ConstantPool):
        self.pool = constant_pool
        self.replaced_count = 0

    def replace_in_block(self, block: CodeBlock) -> None:
        """替换 block 中的字面量"""
        original_content = block.content
        new_content = self.pool.replace_literals_in_content(original_content)
        block.content = new_content

        replaced = original_content.count('"') // 2
        self.replaced_count += replaced

    def replace_in_blocks(self, blocks: list[CodeBlock]) -> int:
        """替换所有 block 中的字面量，返回替换数量"""
        total_replaced = 0
        for block in blocks:
            original_content = block.content
            new_content = self.pool.replace_literals_in_content(original_content)
            block.content = new_content

            replaced = original_content.count('"') - new_content.count('"')
            total_replaced += max(0, replaced // 2)

        self.replaced_count = total_replaced
        return total_replaced

    def get_statistics(self) -> dict:
        return {
            "replaced_count": self.replaced_count,
            "pool_stats": self.pool.get_statistics(),
        }


def apply_constant_pool_stage(
    blocks: list[CodeBlock],
    tokens: list[Token],
    rng: random.Random,
    use_pool: bool = True
) -> tuple[list[CodeBlock], ConstantPool | None, LiteralReplacer | None]:
    """
    常量池阶段：收集字面量并替换。

    返回 (blocks, constant_pool, replacer)
    """
    if not use_pool:
        return blocks, None, None

    collector = LiteralCollector()
    collector.collect_from_tokens(tokens)
    for block in blocks:
        collector.collect_from_content(block.content)

    pool = ConstantPool(rng)
    for s, idx in collector.strings.items():
        pool.strings[s] = idx
        pool.next_string_index = len(pool.strings) + 1

    for num_str, idx in collector.numbers.items():
        try:
            pool.numbers[float(num_str)] = idx
            pool.next_number_index = len(pool.numbers) + 1
        except ValueError:
            pass

    replacer = LiteralReplacer(pool)
    replacer.replace_in_blocks(blocks)

    return blocks, pool, replacer


def apply_diversified_constant_access(
    blocks: list[CodeBlock],
    pool: ConstantPool,
    rng: random.Random,
    enable_diversification: bool = True,
) -> tuple[list[CodeBlock], BlockConstantAccessManager]:
    """
    多样化常量访问阶段

    为不同 block 分配不同的常量访问策略，增加代码结构多样性。

    Args:
        blocks: 代码块列表
        pool: 常量池
        rng: 随机数生成器
        enable_diversification: 是否启用多样化策略

    Returns:
        (blocks, manager) 元组
    """
    if not enable_diversification or not pool:
        return blocks, None

    config = BlockConstantAccessConfig(
        rng=rng,
        enable_diversification=enable_diversification,
        cache_size=3,
    )

    manager = BlockConstantAccessManager(pool, blocks, config)
    manager.apply_to_blocks()

    return blocks, manager


# ===== Block 结构扩展系统 =====


class BlockExtensionType(Enum):
    """
    Block 扩展类型

    定义可插入到 block 流程中的扩展结构。
    """
    # 恒定条件分支（不执行或总是执行）
    CONSTANT_TRUE_BRANCH = "constant_true_branch"
    CONSTANT_FALSE_BRANCH = "constant_false_branch"

    # 空操作块
    NOP_BLOCK = "nop_block"
    EMPTY_BLOCK = "empty_block"

    # 死代码块
    DEAD_CODE = "dead_code"

    # 恒等变换块
    IDENTITY_BLOCK = "identity_block"

    # 守卫块
    GUARD_BLOCK = "guard_block"

    # 循环陷阱
    LOOP_TRAP = "loop_trap"

    # 诱饵块
    DECOY_BLOCK = "decoy_block"


@dataclass
class BlockExtensionConfig:
    """Block 扩展配置"""
    enabled: bool = True
    extension_probability: float = 0.2  # 每个 block 扩展的概率
    max_extensions_per_block: int = 2
    extension_types: list[BlockExtensionType] | None = None
    inject_into_content: bool = True  # 注入到 block 内容中
    insert_as_separate_block: bool = False  # 作为独立 block 插入


class BlockStructureExtension:
    """
    Block 结构扩展器

    在现有 block 流程中插入不影响语义的额外结构。
    """

    def __init__(
        self,
        config: BlockExtensionConfig | None = None,
        rng: random.Random | None = None,
    ):
        self.config = config or BlockExtensionConfig()
        self.rng = rng
        self._extension_counter = 0

    def _get_extension_types(self) -> list[BlockExtensionType]:
        """获取要使用的扩展类型"""
        if self.config.extension_types:
            return self.config.extension_types

        return [
            BlockExtensionType.NOP_BLOCK,
            BlockExtensionType.EMPTY_BLOCK,
            BlockExtensionType.CONSTANT_TRUE_BRANCH,
            BlockExtensionType.CONSTANT_FALSE_BRANCH,
            BlockExtensionType.DEAD_CODE,
            BlockExtensionType.IDENTITY_BLOCK,
            BlockExtensionType.GUARD_BLOCK,
        ]

    def _select_extension_type(self) -> BlockExtensionType:
        """随机选择扩展类型"""
        types = self._get_extension_types()
        if self.rng:
            return self.rng.choice(types)
        return types[0]

    def _generate_extension_code(self, ext_type: BlockExtensionType) -> tuple[str, str]:
        """生成扩展代码"""
        generators = {
            BlockExtensionType.NOP_BLOCK: self._gen_nop_block,
            BlockExtensionType.EMPTY_BLOCK: self._gen_empty_block,
            BlockExtensionType.CONSTANT_TRUE_BRANCH: self._gen_constant_true_branch,
            BlockExtensionType.CONSTANT_FALSE_BRANCH: self._gen_constant_false_branch,
            BlockExtensionType.DEAD_CODE: self._gen_dead_code,
            BlockExtensionType.IDENTITY_BLOCK: self._gen_identity_block,
            BlockExtensionType.GUARD_BLOCK: self._gen_guard_block,
            BlockExtensionType.LOOP_TRAP: self._gen_loop_trap,
            BlockExtensionType.DECOY_BLOCK: self._gen_decoy_block,
        }

        gen = generators.get(ext_type, self._gen_nop_block)
        return gen()

    def _gen_nop_block(self) -> tuple[str, str]:
        """生成空操作块"""
        patterns = [
            "do end",
            "(function() end)()",
            "pcall(function() end)",
            "select('#', nil)",
        ]
        content = self.rng.choice(patterns) if self.rng else "do end"
        return content, "nop"

    def _gen_empty_block(self) -> tuple[str, str]:
        """生成空块"""
        var = f"_e{self._extension_counter}" if self.rng is None else f"_e{self.rng.randint(100, 999)}"
        self._extension_counter += 1
        content = f"local {var} = {var}"
        return content, "empty"

    def _gen_constant_true_branch(self) -> tuple[str, str]:
        """生成恒为真的分支"""
        patterns = [
            "if true then\n    -- always\nend",
            "if 1 == 1 then\n    -- constant\nend",
            "if not false then\n    -- always\nend",
        ]
        content = self.rng.choice(patterns) if self.rng else patterns[0]
        return content, "const_true"

    def _gen_constant_false_branch(self) -> tuple[str, str]:
        """生成恒为假的分支"""
        patterns = [
            "if false then\n    -- never\nend",
            "if 1 ~= 1 then\n    -- never\nend",
            "if not true then\n    -- never\nend",
        ]
        content = self.rng.choice(patterns) if self.rng else patterns[0]
        return content, "const_false"

    def _gen_dead_code(self) -> tuple[str, str]:
        """生成死代码"""
        patterns = [
            "if false then\n    error('unreachable')\nend",
            "repeat\n    break\nuntil false",
            "while false do\n    break\nend",
        ]
        content = self.rng.choice(patterns) if self.rng else patterns[0]
        return content, "dead_code"

    def _gen_identity_block(self) -> tuple[str, str]:
        """生成恒等变换块"""
        var = f"_x{self._extension_counter}" if self.rng is None else f"_x{self.rng.randint(100, 999)}"
        self._extension_counter += 1
        patterns = [
            f"local {var} = {var}",
            f"local {var} = ({var})",
            f"local {var} = 0 + {var}",
            f"local {var} = {var} * 1",
        ]
        content = self.rng.choice(patterns) if self.rng else patterns[0]
        return content, "identity"

    def _gen_guard_block(self) -> tuple[str, str]:
        """生成守卫块"""
        guard = f"_g{self._extension_counter}" if self.rng is None else f"_g{self.rng.randint(100, 999)}"
        self._extension_counter += 1
        patterns = [
            f"local {guard} = true\nif not {guard} then error() end",
            f"assert({guard}, 'guard')",
            f"if {guard} == false then error() end",
        ]
        content = self.rng.choice(patterns) if self.rng else patterns[0]
        return content, "guard"

    def _gen_loop_trap(self) -> tuple[str, str]:
        """生成循环陷阱"""
        patterns = [
            "repeat\n    break\nuntil false",
            "for _ = 1, 0 do\n    break\nend",
        ]
        content = self.rng.choice(patterns) if self.rng else patterns[0]
        return content, "loop_trap"

    def _gen_decoy_block(self) -> tuple[str, str]:
        """生成诱饵块"""
        x = f"_a{self._extension_counter}" if self.rng is None else f"_a{self.rng.randint(100, 999)}"
        y = f"_b{self._extension_counter}" if self.rng is None else f"_b{self.rng.randint(100, 999)}"
        self._extension_counter += 1
        content = f"local {x}, {y} = 0, 0\nlocal _t = {x}\n{x} = {y}\n{y} = _t"
        return content, "decoy"

    def apply_to_block(self, block: CodeBlock) -> None:
        """将扩展应用到单个 block"""
        if not self.config.enabled:
            return

        if self.rng and self.rng.random() > self.config.extension_probability:
            return

        ext_type = self._select_extension_type()
        ext_code, ext_name = self._generate_extension_code(ext_type)

        if self.config.inject_into_content:
            # 注入到 block 内容中
            if block.content.strip():
                # 随机位置插入
                if self.rng and self.rng.random() > 0.5:
                    block.content = ext_code + "\n" + block.content
                else:
                    block.content = block.content + "\n" + ext_code
            else:
                block.content = ext_code

        # 记录扩展信息
        if "extensions" not in block.metadata:
            block.metadata["extensions"] = []
        block.metadata["extensions"].append({
            "type": ext_name,
            "ext_type": ext_type.value,
        })

    def apply_to_blocks(self, blocks: list[CodeBlock]) -> None:
        """将扩展应用到所有 blocks"""
        for block in blocks:
            self.apply_to_block(block)


class BlockExtensionManager:
    """
    Block 扩展管理器

    统一管理所有 block 的扩展操作。
    """

    def __init__(
        self,
        blocks: list[CodeBlock],
        config: BlockExtensionConfig | None = None,
        rng: random.Random | None = None,
    ):
        self.blocks = blocks
        self.config = config or BlockExtensionConfig()
        self.rng = rng
        self.extender = BlockStructureExtension(self.config, self.rng)
        self._extension_stats: dict[str, int] = {}

    def apply_all(self) -> None:
        """应用所有扩展"""
        self.extender.apply_to_blocks(self.blocks)
        self._collect_stats()

    def _collect_stats(self) -> None:
        """收集统计信息"""
        self._extension_stats = {}
        for block in self.blocks:
            if "extensions" in block.metadata:
                for ext in block.metadata["extensions"]:
                    ext_type = ext.get("type", "unknown")
                    self._extension_stats[ext_type] = self._extension_stats.get(ext_type, 0) + 1

    def get_statistics(self) -> dict:
        """获取扩展统计"""
        return {
            "total_blocks": len(self.blocks),
            "blocks_with_extensions": sum(1 for b in self.blocks if "extensions" in b.metadata),
            "extension_types": self._extension_stats,
        }


def apply_block_structure_extension(
    blocks: list[CodeBlock],
    rng: random.Random | None = None,
    enabled: bool = True,
) -> list[CodeBlock]:
    """
    应用 Block 结构扩展

    在现有 block 流程中插入不影响语义的额外结构。

    Args:
        blocks: 代码块列表
        rng: 随机数生成器
        enabled: 是否启用

    Returns:
        处理后的 blocks
    """
    if not enabled:
        return blocks

    config = BlockExtensionConfig(
        enabled=enabled,
        extension_probability=0.2,
        inject_into_content=True,
    )

    manager = BlockExtensionManager(blocks, config, rng)
    manager.apply_all()

    return blocks


def relink_blocks_for_randomized_order(program: BlockProgram) -> None:
    """
    在顺序打乱后重新设置跳转关系。
    保持原有的分支结构，但更新目标 block_id。
    """
    if not program.blocks:
        return

    sorted_blocks = sorted(program.blocks, key=lambda b: b.block_id)
    old_id_to_new_pos = {b.block_id: i for i, b in enumerate(sorted_blocks)}
    old_id_to_block = {b.block_id: b for b in sorted_blocks}

    for block in program.blocks:
        old_next = block.next_id
        if old_next is not None and old_next in old_id_to_new_pos:
            new_pos = old_id_to_new_pos[old_next]
            if new_pos < len(sorted_blocks):
                block.next_id = sorted_blocks[new_pos].block_id

        new_branches = {}
        for cond, old_target in block.branches.items():
            if old_target is not None and old_target in old_id_to_new_pos:
                new_pos = old_id_to_new_pos[old_target]
                if new_pos < len(sorted_blocks):
                    new_branches[cond] = sorted_blocks[new_pos].block_id
            else:
                new_branches[cond] = None
        block.branches = new_branches


def randomize_block_order(program: BlockProgram, rng: random.Random, respect_deps: bool = False) -> BlockProgram:
    """
    随机化块的执行顺序。
    如果 respect_deps=True，则保持依赖关系顺序。
    随机化后自动更新跳转关系。
    """
    if not respect_deps:
        order = list(range(1, len(program.blocks) + 1))
        rng.shuffle(order)
        program.execution_order = order
        relink_blocks_for_randomized_order(program)
        return program

    ordered = topological_sort(program)
    rng.shuffle(ordered[1:])
    ordered[0] = program.entry_block_id
    program.execution_order = ordered
    relink_blocks_for_randomized_order(program)
    return program


def topological_sort(program: BlockProgram) -> list[int]:
    """基于依赖关系的拓扑排序"""
    result: list[int] = []
    visited: set[int] = set()

    def visit(bid: int):
        if bid in visited:
            return
        visited.add(bid)
        block = program.get_block(bid)
        if block:
            for dep_id in block.dependencies:
                visit(dep_id)
        result.append(bid)

    for bid in program.block_map.keys():
        visit(bid)

    return result


# ===== 代码布局随机化系统 =====


class LayoutStrategy(Enum):
    """代码布局随机化策略"""
    FULL_RANDOM = "full_random"           # 完全随机打乱
    GROUP_SHUFFLE = "group_shuffle"         # 按组打乱
    CLUSTER_SWAP = "cluster_swap"           # 簇交换
    SPINE_REVERSE = "spine_reverse"         # 主干反转
    SIBLING_INTERLEAVE = "sibling_interleave"  # 兄弟节点交错


@dataclass
class LayoutConfig:
    """布局随机化配置"""
    enabled: bool = False
    strategy: LayoutStrategy = LayoutStrategy.FULL_RANDOM
    group_size: int = 3                    # 组大小
    swap_iterations: int = 5               # 交换迭代次数
    preserve_entry: bool = True           # 保留入口块位置
    preserve_exit: bool = True             # 保留出口块位置
    cluster_depth: int = 2                # 簇深度


class BlockLayoutRandomizer:
    """
    代码布局随机化器
    
    提供多种布局随机化策略，用于打乱块的物理输出顺序，
    同时保持执行逻辑不变。这对于测试不同代码组织方式
    对执行的影响非常有用。
    """

    def __init__(self, rng: random.Random, config: LayoutConfig | None = None):
        self.rng = rng
        self.config = config if config else LayoutConfig()
        self.layout_history: list[dict] = []
        self._original_order: list[int] = []

    def randomize(self, program: BlockProgram) -> BlockProgram:
        """
        对程序应用布局随机化
        
        Args:
            program: 要随机化的程序
            
        Returns:
            随机化后的程序
        """
        if not self.config.enabled:
            return program
        
        # 记录原始顺序用于分析
        self._original_order = list(program.execution_order)
        
        # 根据策略执行随机化
        strategy_map = {
            LayoutStrategy.FULL_RANDOM: self._full_random,
            LayoutStrategy.GROUP_SHUFFLE: self._group_shuffle,
            LayoutStrategy.CLUSTER_SWAP: self._cluster_swap,
            LayoutStrategy.SPINE_REVERSE: self._spine_reverse,
            LayoutStrategy.SIBLING_INTERLEAVE: self._sibling_interleave,
        }
        
        strategy_func = strategy_map.get(self.config.strategy, self._full_random)
        new_order = strategy_func(program)
        
        # 更新程序
        program.execution_order = new_order
        
        # 重新链接块以保持执行逻辑
        self._relink_for_layout(program)
        
        # 记录布局变化
        self._record_layout_change(program)
        
        program.randomized = True
        return program

    def _full_random(self, program: BlockProgram) -> list[int]:
        """完全随机打乱"""
        order = list(program.execution_order)
        
        # 确定保留位置
        preserved = set()
        if self.config.preserve_entry and order:
            preserved.add(0)
        if self.config.preserve_exit and len(order) > 1:
            preserved.add(len(order) - 1)
        
        # 收集可移动元素
        movable = [o for i, o in enumerate(order) if i not in preserved]
        self.rng.shuffle(movable)
        
        # 重组
        result = []
        movable_idx = 0
        for i in range(len(order)):
            if i in preserved:
                result.append(order[i])
            else:
                result.append(movable[movable_idx])
                movable_idx += 1
        
        return result

    def _group_shuffle(self, program: BlockProgram) -> list[int]:
        """按组打乱"""
        order = list(program.execution_order)
        group_size = self.config.group_size
        
        # 分组
        groups: list[list[int]] = []
        for i in range(0, len(order), group_size):
            group = order[i:i + group_size]
            groups.append(group)
        
        # 随机打乱组
        preserved_groups = set()
        if self.config.preserve_entry and groups:
            preserved_groups.add(0)
        if self.config.preserve_exit and len(groups) > 1:
            preserved_groups.add(len(groups) - 1)
        
        # 收集可移动的组
        movable_groups = [g for i, g in enumerate(groups) if i not in preserved_groups]
        self.rng.shuffle(movable_groups)
        
        # 重组
        result_groups = []
        movable_idx = 0
        for i in range(len(groups)):
            if i in preserved_groups:
                result_groups.append(groups[i])
            else:
                result_groups.append(movable_groups[movable_idx])
                movable_idx += 1
        
        # 扁平化
        return [bid for group in result_groups for bid in group]

    def _cluster_swap(self, program: BlockProgram) -> list[int]:
        """簇交换：随机交换相邻的块簇"""
        order = list(program.execution_order)
        depth = self.config.cluster_depth
        iterations = self.config.swap_iterations
        
        for _ in range(iterations):
            if len(order) < depth * 2:
                break
            
            # 随机选择起始位置
            start = self.rng.randint(0, len(order) - depth * 2)
            
            # 交换两个簇
            cluster1 = order[start:start + depth]
            cluster2 = order[start + depth:start + depth * 2]
            
            order[start:start + depth * 2] = cluster2 + cluster1
        
        return order

    def _spine_reverse(self, program: BlockProgram) -> list[int]:
        """主干反转：反转主执行路径上的块"""
        order = list(program.execution_order)
        
        if len(order) < 3:
            return order
        
        # 找到主路径（按 next_id 链接）
        spine = self._extract_spine(program)
        
        # 反转主干
        reversed_spine = spine[::-1]
        
        # 如果入口需要保留
        if self.config.preserve_entry and reversed_spine:
            reversed_spine[0] = program.entry_block_id
        
        return reversed_spine

    def _sibling_interleave(self, program: BlockProgram) -> list[int]:
        """兄弟节点交错：将并行分支的块交错排列"""
        order = list(program.execution_order)
        
        if len(order) < 4:
            return order
        
        # 识别有分支的块
        branch_info = self._identify_branches(program)
        
        if not branch_info:
            return self._full_random(program)
        
        # 分离主线和分支
        main_blocks = []
        branch_blocks = []
        
        for bid in order:
            block = program.get_block(bid)
            if block and block.has_branches():
                main_blocks.append(bid)
                # 收集分支目标
                for target in block.branches.values():
                    if target is not None:
                        branch_blocks.append(target)
            elif bid not in branch_blocks:
                main_blocks.append(bid)
        
        # 交错排列
        result = []
        branch_idx = 0
        
        for bid in main_blocks:
            result.append(bid)
            # 在某些位置插入分支块
            if branch_idx < len(branch_blocks) and self.rng.random() > 0.5:
                result.append(branch_blocks[branch_idx])
                branch_idx += 1
        
        # 添加剩余分支块
        result.extend(branch_blocks[branch_idx:])
        
        return result

    def _extract_spine(self, program: BlockProgram) -> list[int]:
        """提取主执行路径"""
        spine = []
        current_id = program.entry_block_id
        visited = set()
        
        while current_id is not None and current_id not in visited:
            visited.add(current_id)
            spine.append(current_id)
            
            block = program.get_block(current_id)
            if block is None:
                break
            
            # 优先跟随 next_id
            if block.next_id is not None:
                current_id = block.next_id
            elif block.has_branches():
                # 如果有分支，取第一个
                branches = list(block.branches.values())
                current_id = branches[0] if branches else None
            else:
                break
        
        return spine

    def _identify_branches(self, program: BlockProgram) -> dict[int, list[int]]:
        """识别分支结构"""
        branches: dict[int, list[int]] = {}
        
        for block in program.blocks:
            if block.has_branches():
                targets = [t for t in block.branches.values() if t is not None]
                if targets:
                    branches[block.block_id] = targets
        
        return branches

    def _relink_for_layout(self, program: BlockProgram) -> None:
        """
        根据新的布局顺序重新链接块
        
        这个方法确保即使物理位置改变，执行的逻辑流程保持不变。
        它根据 execution_order 中块的新位置来设置 next_id。
        """
        if not program.execution_order:
            return
        
        # 构建旧ID到新位置的映射
        old_order = list(range(1, len(program.blocks) + 1))
        old_to_new_pos = {bid: i for i, bid in enumerate(program.execution_order)}
        new_to_old = {i: bid for i, bid in enumerate(program.execution_order)}
        
        # 为每个块计算新的 next_id
        for new_pos, bid in enumerate(program.execution_order):
            block = program.get_block(bid)
            if block is None:
                continue
            
            # 找到该块在物理顺序中的下一个块
            if new_pos < len(program.execution_order) - 1:
                next_bid = program.execution_order[new_pos + 1]
                block.next_id = next_bid
            else:
                block.next_id = None

    def _record_layout_change(self, program: BlockProgram) -> None:
        """记录布局变化用于分析"""
        change_record = {
            "strategy": self.config.strategy.value,
            "original_order": self._original_order,
            "new_order": list(program.execution_order),
            "original_to_new": {
                old: new for old, new in zip(self._original_order, program.execution_order)
            }
        }
        self.layout_history.append(change_record)

    def get_layout_report(self) -> dict:
        """获取布局随机化报告"""
        if not self.layout_history:
            return {"status": "no_randomization_applied"}
        
        latest = self.layout_history[-1]
        return {
            "strategy": latest["strategy"],
            "block_count": len(latest["new_order"]),
            "position_changes": sum(
                1 for old, new in zip(latest["original_order"], latest["new_order"])
                if old != new
            ),
            "original_order": latest["original_order"],
            "new_order": latest["new_order"]
        }


class LayoutAnalyzer:
    """
    布局分析器
    
    分析代码布局对执行的影响，包括：
    - 块之间的物理距离
    - 跳转模式
    - 缓存局部性
    """

    @staticmethod
    def compute_block_distances(program: BlockProgram) -> dict[tuple[int, int], int]:
        """计算块之间的物理距离"""
        distances: dict[tuple[int, int], int] = {}
        order = program.execution_order
        
        for i, bid1 in enumerate(order):
            for j, bid2 in enumerate(order):
                distances[(bid1, bid2)] = abs(i - j)
        
        return distances

    @staticmethod
    def compute_jump_cost(program: BlockProgram) -> int:
        """计算跳转开销（跳转距离的总和）"""
        total_cost = 0
        
        for block in program.blocks:
            if block.next_id is not None:
                try:
                    current_pos = program.execution_order.index(block.block_id)
                    target_pos = program.execution_order.index(block.next_id)
                    total_cost += abs(target_pos - current_pos)
                except ValueError:
                    pass
            
            for target in block.branches.values():
                if target is not None:
                    try:
                        current_pos = program.execution_order.index(block.block_id)
                        target_pos = program.execution_order.index(target)
                        total_cost += abs(target_pos - current_pos)
                    except ValueError:
                        pass
        
        return total_cost

    @staticmethod
    def analyze_locality(program: BlockProgram) -> dict:
        """分析代码局部性"""
        distances = LayoutAnalyzer.compute_block_distances(program)
        
        if not distances:
            return {"locality_score": 0, "avg_distance": 0}
        
        avg_distance = sum(distances.values()) / len(distances)
        max_distance = max(distances.values())
        
        # 局部性得分：距离越小得分越高
        locality_score = 1.0 - (avg_distance / max_distance) if max_distance > 0 else 1.0
        
        return {
            "locality_score": locality_score,
            "avg_distance": avg_distance,
            "max_distance": max_distance
        }


# ===== 多阶段代码生成架构：块到 Lua 函数的转换 =====


class BlockGenerator:
    """将 CodeBlock 转换为 Lua 函数"""

    def __init__(self, profile: ProtectionProfile, rng: random.Random):
        self.profile = profile
        self.rng = rng
        self.function_name_prefix = random_lua_identifier(rng, "_blk")

    def generate_function(self, block: CodeBlock, index: int, next_id: int | None = None) -> str:
        """将单个块生成为 Lua 函数，返回 next_id 用于跳转"""
        func_name = f"{self.function_name_prefix}_{index}"
        block.content = block.content.strip()

        next_expr = "return " + str(next_id) if next_id is not None else "return"

        if not block.content:
            return f"local function {func_name}()\n    {next_expr}\nend"

        needs_return = not block.content.rstrip().endswith("end") and \
                      not block.content.rstrip().endswith(";") and \
                      not block.content.rstrip().endswith("return")

        if needs_return and block.block_type == BlockTypeLegacy.FUNCTION_DEF.value:
            needs_return = False

        if needs_return:
            return (
                f"local function {func_name}()\n"
                f"{indent_lua(block.content, 4)}\n"
                f"    {next_expr}\n"
                f"end"
            )

        return (
            f"local function {func_name}()\n"
            f"{indent_lua(block.content, 4)}\n"
            f"end"
        )

    def generate_block_table(self, program: BlockProgram) -> str:
        """生成块函数表"""
        lines: list[str] = []
        lines.append(f"local {self.function_name_prefix}_tbl = {{")

        for idx, bid in enumerate(program.execution_order):
            block = program.get_block(bid)
            if block:
                func_name = f"{self.function_name_prefix}_{idx + 1}"
                lines.append(f" [{idx + 1}] = {func_name},")

        lines.append("}")
        return "\n".join(lines)

    def generate_block_metadata(self, program: BlockProgram) -> str:
        """生成 block 元数据表（包含 next_id 信息）"""
        lines: list[str] = []
        lines.append(f"local {self.function_name_prefix}_meta = {{")

        for idx, bid in enumerate(program.execution_order):
            block = program.get_block(bid)
            if block:
                next_val = block.next_id if block.next_id is not None else "nil"
                lines.append(
                    f"    [{idx + 1}] = {{"
                    f"type='{block.block_type}',"
                    f"next={next_val}"
                    f"}},"
                )

        lines.append("}")
        return "\n".join(lines)

    def generate_block_map(self, program: BlockProgram) -> str:
        """生成完整的 block 结构（包含代码和元数据）"""
        lines: list[str] = []
        lines.append(f"local {self.function_name_prefix}_blocks = {{")

        for idx, bid in enumerate(program.execution_order):
            block = program.get_block(bid)
            if block:
                func_def = self.generate_function(block, idx + 1)
                next_val = block.next_id if block.next_id is not None else "nil"
                lines.append(f"    [{idx + 1}] = {{")
                lines.append(f"        fn = function()")
                for fn_line in func_def.split("\n"):
                    if "local function" in fn_line:
                        lines.append("            " + fn_line.strip())
                    elif fn_line.strip():
                        lines.append("            " + fn_line.strip())
                lines.append(f"        end,")
                lines.append(f"        type = '{block.block_type}',")
                lines.append(f"        next_id = {next_val},")
                lines.append(f"    }},")

        lines.append("}")
        return "\n".join(lines)


# ===== 多阶段代码生成架构：入口执行器 =====


class ExecutionDispatcher:
    """
    生成代码块执行调度器

    支持多种执行模式，包括传统的顺序/随机/索引模式，
    以及新的多样化变体调度模式。
    """

    def __init__(self, profile: ProtectionProfile, rng: random.Random):
        self.profile = profile
        self.rng = rng
        self.pc_name = random_lua_identifier(rng, "_pc")
        self.tbl_name = random_lua_identifier(rng, "_tbl")
        self.entry_name = random_lua_identifier(rng, "_entry")
        self.variant_config: DispatcherVariantConfig | None = None
        self.selected_variant: DispatchVariant | None = None

    def generate_dispatcher(
        self,
        program: BlockProgram,
        mode: str = "sequential",
        enable_variant: bool = True,
    ) -> str:
        """
        生成执行调度器代码

        Args:
            program: 目标程序
            mode: 执行模式 ("sequential", "random", "indexed", "variant", "resolved")
            enable_variant: 是否启用变体模式

        Returns:
            调度器代码
        """
        if mode == "resolved":
            return self._generate_resolved_dispatcher(program)

        if mode == "variant" and enable_variant:
            return self._generate_variant_dispatcher(program)

        if mode == "sequential":
            return self._generate_sequential_dispatcher(program)
        elif mode == "random":
            return self._generate_random_dispatcher(program)
        elif mode == "indexed":
            return self._generate_indexed_dispatcher(program)
        elif mode == "variant":
            return self._generate_variant_dispatcher(program)
        else:
            return self._generate_sequential_dispatcher(program)

    def _generate_variant_dispatcher(self, program: BlockProgram) -> str:
        """生成多样化变体调度器"""
        self.variant_config = DispatcherVariantConfig(rng=self.rng)
        generator = DispatchVariantGenerator(program, self.variant_config)
        variant = self.variant_config.select_variant()
        self.selected_variant = variant
        return generator.generate(variant)

    def _generate_resolved_dispatcher(self, program: BlockProgram) -> str:
        """
        生成使用 resolve_next 的调度器

        Block 返回一个 key，通过 resolve_next 函数解析为实际的 block_id。
        这种方式将控制流决策从 block 中解耦出来，由统一的解析函数处理。
        """
        lines: list[str] = []
        tbl_name = self.tbl_name
        pc = self.pc_name

        # 生成映射表
        map_var = random_lua_identifier(self.rng, "_mp") if self.rng else "_mp"
        lines.append(f"local {map_var} = {{}}")

        flow = {}
        for block in program.blocks:
            if block.next_id is not None:
                flow[block.block_id] = block.next_id

        for bid, nxt in sorted(flow.items()):
            lines.append(f"{map_var}[{bid}] = {nxt}")
        lines.append("")

        # 生成 resolve_next 函数
        key_var = random_lua_identifier(self.rng, "_k") if self.rng else "_key"
        res_var = random_lua_identifier(self.rng, "_r") if self.rng else "_result"
        st_var = random_lua_identifier(self.rng, "_st") if self.rng else "_state"

        lines.append(f"local {st_var} = 0")
        lines.append(f"local function resolve_next({key_var})")
        lines.append(f"    {st_var} = ({st_var} + 1) - 1")
        lines.append(f"    local {res_var} = {map_var}[{key_var}]")
        lines.append(f"    return {res_var} or {key_var}")
        lines.append("end")
        lines.append("")

        # 生成调度器
        lines.append(f"local {pc} = {program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = {tbl_name}[{pc}]")
        lines.append(f"    if not block then error('Invalid block: '..tostring({pc})) end")
        lines.append(f"    if not block.fn then error('Missing fn') end")
        lines.append(f"    local key = block.fn()")
        lines.append(f"    {pc} = resolve_next(key)")
        lines.append("end")

        return "\n".join(lines)

    def _generate_sequential_dispatcher(self, program: BlockProgram) -> str:
        """顺序执行模式 - 使用 block 返回的 next_id 驱动"""
        lines: list[str] = []
        tbl_name = self.tbl_name
        pc = self.pc_name

        lines.append(f"local {pc} = {program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = {tbl_name}[{pc}]")
        lines.append(f"    if not block then error('Invalid block index: '..tostring({pc})) end")
        lines.append(f"    if not block.fn then error('Block missing fn: '..tostring({pc})) end")
        lines.append(f"    {pc} = block.fn()")
        lines.append("end")

        return "\n".join(lines)

    def _generate_random_dispatcher(self, program: BlockProgram) -> str:
        """随机执行模式 - 使用 block 返回的 next_id 驱动"""
        lines: list[str] = []
        tbl_name = self.tbl_name
        pc = self.pc_name
        visited_name = random_lua_identifier(self.rng, "_visited")
        remaining_name = random_lua_identifier(self.rng, "_rem")

        lines.append(f"local {pc} = {program.entry_block_id}")
        lines.append(f"local {visited_name} = {{}}")
        lines.append(f"local {remaining_name} = {{}}")
        lines.append(f"for i = 1, #{tbl_name} do {remaining_name}[i] = i end")
        lines.append(f"while #{remaining_name} > 0 do")
        lines.append(f"    local idx = math.random(1, #{remaining_name})")
        lines.append(f"    {pc} = table.remove({remaining_name}, idx)")
        lines.append(f"    local block = {tbl_name}[{pc}]")
        lines.append(f"    if block and block.fn then")
        lines.append(f"        local next_id = block.fn()")
        lines.append(f"        if next_id and not {visited_name}[next_id] then")
        lines.append(f"            {remaining_name}[#{remaining_name} + 1] = next_id")
        lines.append(f"            {visited_name}[next_id] = true")
        lines.append(f"        end")
        lines.append(f"    end")
        lines.append("end")

        return "\n".join(lines)

    def _generate_indexed_dispatcher(self, program: BlockProgram) -> str:
        """索引跳转执行模式 - 使用 block 返回的 next_id 驱动"""
        lines: list[str] = []
        tbl_name = self.tbl_name
        pc = self.pc_name

        lines.append(f"local {pc} = {program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = {tbl_name}[{pc}]")
        lines.append(f"    if not block then error('Invalid block index: '..tostring({pc})) end")
        lines.append(f"    if not block.fn then error('Block missing fn: '..tostring({pc})) end")
        lines.append(f"    {pc} = block.fn()")
        lines.append("end")

        return "\n".join(lines)

    def generate_entry_wrapper(self, dispatcher_code: str) -> str:
        """包装调度器代码"""
        return f"\n-- execution entry\n{dispatcher_code}\n"


# ===== Block 执行标识解析系统 =====


class NextResolutionStrategy(Enum):
    """
    下一步解析策略

    定义如何将 block 返回的中间标识解析为实际的 block ID。
    """
    # 直接使用标识
    DIRECT = "direct"

    # 查表映射
    TABLE_LOOKUP = "table_lookup"

    # 偏移计算
    OFFSET_CALC = "offset_calc"

    # 异或变换
    XOR_TRANSFORM = "xor_transform"

    # 状态转换
    STATE_TRANSFORM = "state_transform"

    # 哈希计算
    HASH_COMPUTE = "hash_compute"


@dataclass
class NextResolverConfig:
    """下一步解析器配置"""
    strategy: NextResolutionStrategy = NextResolutionStrategy.DIRECT
    enable_diversification: bool = True
    obfuscate_vars: bool = True
    add_transform: bool = True

    # 变换相关
    xor_key: int = 0
    offset_base: int = 0


class NextResolver:
    """
    下一步解析器

    负责将 block 返回的中间标识（key）解析为实际的 block ID。
    所有 block 的执行流程通过此解析器统一控制。

    架构:
    - Block 返回一个 key（可以是 block_id 或其他标识）
    - resolve_next 函数接收 key，进行变换后得到下一个 block_id
    - 调度器使用解析后的 block_id 继续执行
    """

    def __init__(
        self,
        program: BlockProgram,
        config: NextResolverConfig | None = None,
        rng: random.Random | None = None,
    ):
        self.program = program
        self.config = config or NextResolverConfig()
        self.rng = rng

        # 生成混淆变量名
        self._gen_var_names()

        # 构建状态映射
        self._build_state_map()

    def _gen_var_names(self) -> None:
        """生成混淆变量名"""
        if self.config.obfuscate_vars and self.rng:
            self.key_var = random_lua_identifier(self.rng, "_k")
            self.res_var = random_lua_identifier(self.rng, "_r")
            self.map_var = random_lua_identifier(self.rng, "_mp")
            self.st_var = random_lua_identifier(self.rng, "_st")
            self.xor_var = random_lua_identifier(self.rng, "_x")
        else:
            self.key_var = "_key"
            self.res_var = "_result"
            self.map_var = "_map"
            self.st_var = "_state"
            self.xor_var = "_xor"

        # 生成 xor 变换密钥
        if self.config.xor_key == 0 and self.rng:
            self.config.xor_key = self.rng.randint(1, 255)

        # 生成偏移基础
        if self.config.offset_base == 0 and self.rng:
            self.config.offset_base = self.rng.randint(1, 100)

    def _build_state_map(self) -> None:
        """构建状态映射表"""
        self.key_to_block: dict[int, int] = {}
        self.block_to_key: dict[int, int] = {}

        order = self.program.execution_order
        for i, bid in enumerate(order):
            # key 可以与 block_id 不同，通过映射转换
            key = bid
            self.key_to_block[key] = bid
            self.block_to_key[bid] = key

    def generate_resolve_function(self) -> str:
        """生成 resolve_next 函数"""
        strategy = self.config.strategy

        generators = {
            NextResolutionStrategy.DIRECT: self._gen_direct,
            NextResolutionStrategy.TABLE_LOOKUP: self._gen_table_lookup,
            NextResolutionStrategy.OFFSET_CALC: self._gen_offset_calc,
            NextResolutionStrategy.XOR_TRANSFORM: self._gen_xor_transform,
            NextResolutionStrategy.STATE_TRANSFORM: self._gen_state_transform,
            NextResolutionStrategy.HASH_COMPUTE: self._gen_hash_compute,
        }

        gen = generators.get(strategy, self._gen_direct)
        return gen()

    def _gen_direct(self) -> str:
        """直接解析"""
        lines = []
        lines.append(f"local function resolve_next({self.key_var})")
        lines.append(f"    return {self.key_var}")
        lines.append("end")
        return "\n".join(lines)

    def _gen_table_lookup(self) -> str:
        """查表映射解析"""
        lines = []

        # 生成映射表
        lines.append(f"local {self.map_var} = {{}}")
        for bid, nxt in sorted(self._get_block_flow().items()):
            lines.append(f"{self.map_var}[{bid}] = {nxt}")
        lines.append("")

        # 生成解析函数
        lines.append(f"local function resolve_next({self.key_var})")
        lines.append(f"    local {self.res_var} = {self.map_var}[{self.key_var}]")
        lines.append(f"    return {self.res_var} or {self.key_var}")
        lines.append("end")

        return "\n".join(lines)

    def _gen_offset_calc(self) -> str:
        """偏移计算解析"""
        lines = []
        base = self.config.offset_base

        lines.append(f"local {self.st_var} = {base}")
        lines.append("")

        lines.append(f"local function resolve_next({self.key_var})")
        lines.append(f"    local {self.res_var} = {self.key_var}")
        lines.append(f"    if {self.key_var} > 0 then")
        lines.append(f"        {self.res_var} = {self.key_var} + {self.st_var} - {base}")
        lines.append(f"    end")
        lines.append(f"    {self.st_var} = ({self.st_var} + 1) - 1")
        lines.append(f"    return {self.res_var}")
        lines.append("end")

        return "\n".join(lines)

    def _gen_xor_transform(self) -> str:
        """异或变换解析"""
        lines = []
        key = self.config.xor_key

        lines.append(f"local {self.xor_var} = {key}")
        lines.append("")

        lines.append(f"local function resolve_next({self.key_var})")
        lines.append(f"    if {self.key_var} then")
        lines.append(f"        return bit.bxor({self.key_var}, {self.xor_var})")
        lines.append(f"    end")
        lines.append(f"    return nil")
        lines.append("end")

        return "\n".join(lines)

    def _gen_state_transform(self) -> str:
        """状态转换解析"""
        lines = []

        lines.append(f"local {self.st_var} = 0")
        lines.append("")

        lines.append(f"local function resolve_next({self.key_var})")
        lines.append(f"    {self.st_var} = ({self.st_var} + 1) - 1")
        lines.append(f"    if {self.key_var} and {self.key_var} > 0 then")
        lines.append(f"        return {self.key_var}")
        lines.append(f"    end")
        lines.append(f"    return nil")
        lines.append("end")

        return "\n".join(lines)

    def _gen_hash_compute(self) -> str:
        """哈希计算解析"""
        lines = []

        lines.append(f"local {self.st_var} = 0")
        lines.append("")

        lines.append(f"local function resolve_next({self.key_var})")
        lines.append(f"    {self.st_var} = ({self.st_var} * 31 + ({self.key_var} or 0)) % 1000000")
        lines.append(f"    return {self.key_var}")
        lines.append("end")

        return "\n".join(lines)

    def _get_block_flow(self) -> dict[int, int]:
        """获取 block 流向映射"""
        flow: dict[int, int] = {}
        for block in self.program.blocks:
            if block.next_id is not None:
                flow[block.block_id] = block.next_id
        return flow

    def generate_with_resolver(self) -> tuple[str, str, str]:
        """
        生成带解析器的完整调度代码

        返回:
            (resolve_function, dispatcher_code, table_code)
        """
        lines = []

        # 生成映射表
        lines.append(f"local {self.map_var} = {{}}")
        for bid, nxt in sorted(self._get_block_flow().items()):
            lines.append(f"{self.map_var}[{bid}] = {nxt}")
        lines.append("")

        # 生成解析函数
        resolve_func = self.generate_resolve_function()

        # 生成调度器
        dispatcher = self._gen_resolver_dispatcher()

        return resolve_func, dispatcher, "\n".join(lines)

    def _gen_resolver_dispatcher(self) -> str:
        """生成使用解析器的调度器"""
        pc = random_lua_identifier(self.rng, "_pc") if self.rng else "_pc"
        tbl = random_lua_identifier(self.rng, "_tbl") if self.rng else "_tbl"

        lines = []
        lines.append(f"local {pc} = {self.program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if not block then error('Invalid block: '..tostring({pc})) end")
        lines.append(f"    if not block.fn then error('Missing fn') end")
        lines.append(f"    local key = block.fn()")
        lines.append(f"    {pc} = resolve_next(key)")
        lines.append("end")

        return "\n".join(lines)

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            "strategy": self.config.strategy.value,
            "total_blocks": len(self.program.blocks),
            "entry_block_id": self.program.entry_block_id,
            "xor_key": self.config.xor_key,
            "offset_base": self.config.offset_base,
        }


class DiversifiedResolver:
    """
    多样化解析器

    支持在运行时随机选择不同的解析策略。
    """

    def __init__(
        self,
        program: BlockProgram,
        rng: random.Random | None = None,
    ):
        self.program = program
        self.rng = rng
        self.resolvers: dict[NextResolutionStrategy, NextResolver] = {}
        self.selected_strategy: NextResolutionStrategy | None = None

        # 预创建所有解析器
        for strategy in NextResolutionStrategy:
            config = NextResolverConfig(
                strategy=strategy,
                enable_diversification=False,
                obfuscate_vars=True,
            )
            self.resolvers[strategy] = NextResolver(program, config, rng)

    def generate(self, strategy: NextResolutionStrategy | None = None) -> tuple[str, str, str]:
        """生成指定策略的解析器代码"""
        if strategy is None and self.rng:
            strategies = list(NextResolutionStrategy)
            strategy = self.rng.choice(strategies)

        if strategy is None:
            strategy = NextResolutionStrategy.DIRECT

        self.selected_strategy = strategy
        resolver = self.resolvers[strategy]
        return resolver.generate_with_resolver()

    def get_selected_strategy(self) -> NextResolutionStrategy | None:
        """获取选中的策略"""
        return self.selected_strategy


# ===== 多阶段代码生成架构：程序组装 =====


def build_block_program(
    source: str,
    profile: ProtectionProfile,
    rng: random.Random,
    randomize_order: bool = False,
    execution_mode: str = "sequential",
    use_constant_pool: bool = False,
    use_auxiliary_paths: bool = False
) -> tuple[str, str, str, BlockProgram]:
    """
    多阶段代码生成主函数。
    返回 (program_wrapper, constant_pool_code, dispatcher_code, BlockProgram)

    阶段流程:
    1. 分词 (tokenize)
    2. Token 重写 (rewrite_tokens)
    3. 拆分为 blocks (split_into_blocks)
    4. 依赖分析 (analyze_block_dependencies)
    5. 块链接 (link_blocks_sequentially)
    6. 常量池收集与替换 (apply_constant_pool_stage) - 可选
    7. 辅助路径生成 (AuxiliaryPathGenerator) - 可选
    8. 布局随机化 (BlockLayoutRandomizer) - 可选
    9. 顺序随机化 (randomize_block_order) - 可选
    10. 代码生成 (BlockGenerator)
    11. 执行器生成 (ExecutionDispatcher)
    """
    tokens = tokenize(source)
    rewrite_tokens(tokens, profile, rng)

    blocks = split_into_blocks(tokens, rng)
    blocks = analyze_block_dependencies(blocks)
    blocks = link_blocks_sequentially(blocks)

    for block in blocks:
        block.metadata["original_order"] = block.block_id

    constant_pool = None
    constant_pool_code = ""
    replacer = None

    if use_constant_pool:
        blocks, constant_pool, replacer = apply_constant_pool_stage(
            blocks, tokens, rng, use_pool=True
        )
        if constant_pool:
            constant_pool_code = constant_pool.generate_pool_table() + "\n"

            # 应用多样化常量访问策略
            if profile.enhanced_accessor_enabled:
                blocks, _ = apply_diversified_constant_access(
                    blocks, constant_pool, rng,
                    enable_diversification=True
                )

    # 应用 Block 结构扩展
    blocks = apply_block_structure_extension(blocks, rng)

    program = BlockProgram(
        blocks=blocks,
        execution_order=list(range(1, len(blocks) + 1)),
        block_map={b.block_id: b for b in blocks},
        entry_block_id=1,
        use_auxiliary_paths=use_auxiliary_paths,
        constant_pool=constant_pool
    )

    aux_generator = None
    if use_auxiliary_paths:
        aux_generator = AuxiliaryPathGenerator(rng)

    # 布局随机化 - 使用 profile 中的配置
    layout_randomizer = None
    if profile.layout_randomization_enabled:
        layout_config = LayoutConfig(
            enabled=True,
            strategy=profile.layout_strategy,
            group_size=profile.layout_group_size,
            swap_iterations=profile.layout_swap_iterations,
            preserve_entry=profile.layout_preserve_entry,
            preserve_exit=profile.layout_preserve_exit,
            cluster_depth=profile.layout_cluster_depth
        )
        layout_randomizer = BlockLayoutRandomizer(rng, layout_config)
        layout_randomizer.randomize(program)

    if randomize_order:
        randomize_block_order(program, rng, respect_deps=False)

    generator = BlockGenerator(profile, rng)
    api_plan = apply_api_indirection(tokens, profile, rng)

    program_code_lines: list[str] = []
    program_code_lines.append("local program = {")

    for idx, bid in enumerate(program.execution_order):
        block = program.get_block(bid)
        if block:
            if use_auxiliary_paths and aux_generator and block.block_type != BlockTypeLegacy.FUNCTION_DEF.value:
                aux_generator.add_auxiliary_paths_to_block(block, block.next_id, max_paths=1)

            next_id = block.next_id
            func_def = generator.generate_function(block, idx + 1, next_id)

            aux_code = ""
            if block.has_auxiliary_paths():
                for aux_path in block.auxiliary_paths:
                    aux_code += "\n" + aux_path["content"]
                program.increment_auxiliary_count()

            next_id_val = next_id if next_id is not None else "nil"

            branches_repr = "nil"
            if block.has_branches():
                branches_repr = "{"
                branch_parts = []
                for cond, target in block.branches.items():
                    t = target if target is not None else "nil"
                    branch_parts.append(f"{cond}={t}")
                branches_repr += ", ".join(branch_parts) + "}"

            aux_paths_repr = "nil"
            if block.has_auxiliary_paths():
                aux_paths_repr = "{"
                path_parts = []
                for aux_path in block.auxiliary_paths:
                    target = aux_path["target_block_id"] if aux_path["target_block_id"] is not None else "nil"
                    path_parts.append(
                        f"{{id={aux_path['path_id']},type='{aux_path['path_type']}',target={target}}}"
                    )
                aux_paths_repr += ", ".join(path_parts) + "}"

            program_code_lines.append(f"    [{idx + 1}] = {{")
            program_code_lines.append(f"        fn = function()")
            for fn_line in func_def.split("\n"):
                if "local function" in fn_line:
                    continue
                if fn_line.strip():
                    program_code_lines.append("            " + fn_line.strip())
            if aux_code:
                for aux_line in aux_code.split("\n"):
                    if aux_line.strip():
                        program_code_lines.append("            " + aux_line.strip())
            program_code_lines.append(f"        end,")
            program_code_lines.append(f"        type = '{block.block_type}',")
            program_code_lines.append(f"        next_id = {next_id_val},")
            program_code_lines.append(f"        branches = {branches_repr},")
            program_code_lines.append(f"        auxiliary_paths = {aux_paths_repr},")
            program_code_lines.append(f"    }},")

    program_code_lines.append("}")

    program_wrapper = "\n".join(program_code_lines)

    dispatcher = ExecutionDispatcher(profile, rng)
    dispatcher_code = dispatcher.generate_dispatcher(program, mode=execution_mode)

    return program_wrapper, constant_pool_code, dispatcher_code, program


# ===== 多阶段 Pipeline 架构 =====


@dataclass
class PipelineContext:
    """
    Pipeline 执行上下文

    保存各阶段之间的数据传递。
    """
    source: str
    tokens: list[Token] = None
    profile: ProtectionProfile = None
    rng: random.Random = None

    # Block 阶段
    blocks: list[CodeBlock] = None
    program: BlockProgram = None
    constant_pool: ConstantPool = None

    # 指令阶段
    instructions: dict[int, BlockInstructions] = None
    instruction_layer: InstructionLayer = None

    # 发射阶段
    emitted_code: str = ""

    # 元数据
    metadata: dict = None

    def __post_init__(self):
        if self.tokens is None:
            self.tokens = []
        if self.blocks is None:
            self.blocks = []
        if self.instructions is None:
            self.instructions = {}
        if self.metadata is None:
            self.metadata = {}


class PipelineStage:
    """
    Pipeline 阶段基类
    """

    name: str = "base"

    def process(self, ctx: PipelineContext) -> PipelineContext:
        """处理上下文，返回更新后的上下文"""
        raise NotImplementedError


class TokenizeStage(PipelineStage):
    """
    Stage 1: 分词阶段

    将源代码转换为 token 流。
    """
    name = "tokenize"

    def process(self, ctx: PipelineContext) -> PipelineContext:
        """分词处理"""
        tokenizer = Tokenizer(ctx.source)
        tokens: list[Token] = []
        while tokenizer.has_more():
            tokens.append(tokenizer.next_token())
        ctx.tokens = tokens
        return ctx


class RewriteStage(PipelineStage):
    """
    Stage 2: Token 重写阶段

    对 token 进行重写（字符串驻留、数字重写等）。
    """
    name = "rewrite"

    def process(self, ctx: PipelineContext) -> PipelineContext:
        """Token 重写处理"""
        if ctx.tokens and ctx.profile:
            rewrite_tokens(ctx.tokens, ctx.profile, ctx.rng)
        return ctx


class BlockBuildStage(PipelineStage):
    """
    Stage 3: Block 构建阶段

    将 token 流拆分为代码块。
    """
    name = "block_build"

    def process(self, ctx: PipelineContext) -> PipelineContext:
        """Block 构建处理"""
        if not ctx.tokens:
            return ctx

        # 拆分 blocks
        ctx.blocks = split_into_blocks(ctx.tokens, ctx.rng)

        # 依赖分析
        ctx.blocks = analyze_block_dependencies(ctx.blocks)

        # 块链接
        ctx.blocks = link_blocks_sequentially(ctx.blocks)

        # 记录原始顺序
        for block in ctx.blocks:
            block.metadata["original_order"] = block.block_id

        return ctx


class ConstantPoolStage(PipelineStage):
    """
    Stage 4: 常量池阶段

    收集字面量并替换为常量池访问。
    """
    name = "constant_pool"

    def process(self, ctx: PipelineContext) -> PipelineContext:
        """常量池处理"""
        if not ctx.blocks:
            return ctx

        blocks, pool, replacer = apply_constant_pool_stage(
            ctx.blocks, ctx.tokens, ctx.rng, use_pool=True
        )
        ctx.blocks = blocks
        ctx.constant_pool = pool

        # 应用多样化常量访问策略
        if ctx.profile and ctx.profile.enhanced_accessor_enabled and pool:
            ctx.blocks, _ = apply_diversified_constant_access(
                ctx.blocks, pool, ctx.rng,
                enable_diversification=True
            )

        return ctx


class BlockExtensionStage(PipelineStage):
    """
    Stage 5: Block 结构扩展阶段

    插入不影响语义的额外结构。
    """
    name = "block_extension"

    def process(self, ctx: PipelineContext) -> PipelineContext:
        """Block 扩展处理"""
        if not ctx.blocks:
            return ctx

        ctx.blocks = apply_block_structure_extension(ctx.blocks, ctx.rng)
        return ctx


class ProgramBuildStage(PipelineStage):
    """
    Stage 6: Program 构建阶段

    将 blocks 组装为 BlockProgram。
    """
    name = "program_build"

    def process(self, ctx: PipelineContext) -> PipelineContext:
        """Program 构建处理"""
        if not ctx.blocks:
            return ctx

        ctx.program = BlockProgram(
            blocks=ctx.blocks,
            execution_order=list(range(1, len(ctx.blocks) + 1)),
            block_map={b.block_id: b for b in ctx.blocks},
            entry_block_id=1,
            constant_pool=ctx.constant_pool
        )

        return ctx


class InstructionGenStage(PipelineStage):
    """
    Stage 7: 指令生成阶段

    将 CodeBlock 转换为指令列表。
    """
    name = "instruction_gen"

    def process(self, ctx: PipelineContext) -> PipelineContext:
        """指令生成处理"""
        if not ctx.blocks:
            return ctx

        # 转换 blocks 为指令
        layer = InstructionLayer(ctx.rng)
        ctx.instructions = layer.process_blocks(ctx.blocks)
        ctx.instruction_layer = layer

        return ctx


class EmitStage(PipelineStage):
    """
    Stage 8: 发射阶段

    将指令转换为 Lua 代码。
    """
    name = "emit"

    def __init__(self, use_program_mode: bool = True):
        self.use_program_mode = use_program_mode

    def process(self, ctx: PipelineContext) -> PipelineContext:
        """发射处理"""
        if not ctx.program:
            return ctx

        # 使用 BlockGenerator 生成代码
        generator = BlockGenerator(ctx.profile, ctx.rng)
        api_plan = apply_api_indirection(ctx.tokens, ctx.profile, ctx.rng)

        program_code_lines: list[str] = []
        program_code_lines.append("local program = {")

        for idx, bid in enumerate(ctx.program.execution_order):
            block = ctx.program.get_block(bid)
            if block:
                next_id = block.next_id
                func_def = generator.generate_function(block, idx + 1, next_id)

                next_id_val = next_id if next_id is not None else "nil"

                branches_repr = "nil"
                if block.has_branches():
                    branches_repr = "{"
                    branch_parts = []
                    for cond, target in block.branches.items():
                        t = target if target is not None else "nil"
                        branch_parts.append(f"{cond}={t}")
                    branches_repr += ", ".join(branch_parts) + "}"

                program_code_lines.append(f"    [{idx + 1}] = {{")
                program_code_lines.append(f"        fn = function()")
                for fn_line in func_def.split("\n"):
                    if "local function" in fn_line:
                        continue
                    if fn_line.strip():
                        program_code_lines.append("            " + fn_line.strip())
                program_code_lines.append(f"        end,")
                program_code_lines.append(f"        type = '{block.block_type}',")
                program_code_lines.append(f"        next_id = {next_id_val},")
                program_code_lines.append(f"        branches = {branches_repr},")
                program_code_lines.append(f"    }},")

        program_code_lines.append("}")

        ctx.emitted_code = "\n".join(program_code_lines)

        # 保存 API 计划到元数据
        ctx.metadata["api_plan"] = api_plan

        return ctx


class LayoutRandomizeStage(PipelineStage):
    """
    Stage: 布局随机化阶段（可选）

    随机化 block 布局顺序。
    """
    name = "layout_randomize"

    def __init__(self, enabled: bool = True, config: LayoutConfig | None = None):
        self.enabled = enabled
        self.config = config

    def process(self, ctx: PipelineContext) -> PipelineContext:
        """布局随机化处理"""
        if not self.enabled or not ctx.program:
            return ctx

        randomizer = BlockLayoutRandomizer(ctx.rng, self.config)
        randomizer.randomize(ctx.program)

        return ctx


class BlockOrderRandomizeStage(PipelineStage):
    """
    Stage: Block 顺序随机化阶段（可选）

    随机化 block 执行顺序。
    """
    name = "block_order_randomize"

    def __init__(self, enabled: bool = True, respect_deps: bool = False):
        self.enabled = enabled
        self.respect_deps = respect_deps

    def process(self, ctx: PipelineContext) -> PipelineContext:
        """Block 顺序随机化处理"""
        if not self.enabled or not ctx.program:
            return ctx

        randomize_block_order(ctx.program, ctx.rng, respect_deps=self.respect_deps)

        return ctx


class InstructionEmitter:
    """
    指令发射器

    将指令列表转换为 Lua 代码字符串。
    """

    def __init__(self, generator: InstructionGenerator | None = None):
        self.generator = generator or InstructionGenerator()

    def emit_instruction(self, instr: Instruction) -> str:
        """发射单条指令"""
        return self.generator._generate_instruction(instr)

    def emit_block(self, block_instr: BlockInstructions) -> str:
        """发射整个 block 的指令"""
        return self.generator.generate_block(block_instr)

    def emit_sequence(self, instructions: list[Instruction]) -> str:
        """发射指令序列"""
        lines = []
        for instr in instructions:
            code = self.emit_instruction(instr)
            if code:
                lines.append(code)
        return "\n".join(lines)

    def emit_all_blocks(
        self,
        instructions: dict[int, BlockInstructions],
        execution_order: list[int] | None = None
    ) -> str:
        """发射所有 blocks"""
        if execution_order is None:
            execution_order = list(instructions.keys())

        lines = []
        for bid in execution_order:
            if bid in instructions:
                block_instr = instructions[bid]
                lines.append(f"-- Block {bid} ({block_instr.block_type})")
                lines.append(self.emit_block(block_instr))
                lines.append("")

        return "\n".join(lines)


class CodePipeline:
    """
    多阶段代码生成 Pipeline

    按顺序执行各个阶段，最终生成混淆后的 Lua 代码。
    """

    def __init__(
        self,
        stages: list[PipelineStage] | None = None,
        debug: bool = False
    ):
        self.stages = stages or []
        self.debug = debug

    def add_stage(self, stage: PipelineStage) -> 'CodePipeline':
        """添加阶段"""
        self.stages.append(stage)
        return self

    def add_stages(self, stages: list[PipelineStage]) -> 'CodePipeline':
        """添加多个阶段"""
        self.stages.extend(stages)
        return self

    def execute(self, source: str, profile: ProtectionProfile, rng: random.Random) -> PipelineContext:
        """
        执行 Pipeline

        Args:
            source: 源代码
            profile: 保护配置
            rng: 随机数生成器

        Returns:
            PipelineContext - 包含各阶段结果
        """
        # 初始化上下文
        ctx = PipelineContext(
            source=source,
            profile=profile,
            rng=rng
        )

        # 依次执行各阶段
        for i, stage in enumerate(self.stages):
            if self.debug:
                print(f"[Pipeline] Stage {i + 1}: {stage.name}")

            try:
                ctx = stage.process(ctx)
            except Exception as e:
                if self.debug:
                    print(f"[Pipeline] Error in stage '{stage.name}': {e}")
                raise

        return ctx

    @classmethod
    def create_default(cls, debug: bool = False) -> 'CodePipeline':
        """创建默认配置的 Pipeline"""
        return cls(
            stages=[
                TokenizeStage(),
                RewriteStage(),
                BlockBuildStage(),
                ConstantPoolStage(),
                BlockExtensionStage(),
                ProgramBuildStage(),
                InstructionGenStage(),
                EmitStage(),
            ],
            debug=debug
        )

    @classmethod
    def create_full(cls, debug: bool = False) -> 'CodePipeline':
        """创建完整配置的 Pipeline（包含随机化）"""
        layout_config = LayoutConfig(
            enabled=True,
            strategy="sequential",
        )
        return cls(
            stages=[
                TokenizeStage(),
                RewriteStage(),
                BlockBuildStage(),
                ConstantPoolStage(),
                BlockExtensionStage(),
                ProgramBuildStage(),
                LayoutRandomizeStage(enabled=True, config=layout_config),
                BlockOrderRandomizeStage(enabled=True),
                InstructionGenStage(),
                EmitStage(),
            ],
            debug=debug
        )

    @classmethod
    def create_instruction_based(cls, debug: bool = False) -> 'CodePipeline':
        """创建基于指令的 Pipeline"""
        return cls(
            stages=[
                TokenizeStage(),
                RewriteStage(),
                BlockBuildStage(),
                ConstantPoolStage(),
                BlockExtensionStage(),
                ProgramBuildStage(),
                InstructionGenStage(),
            ],
            debug=debug
        )


def build_block_program_pipelined(
    source: str,
    profile: ProtectionProfile,
    rng: random.Random,
    randomize_order: bool = False,
    execution_mode: str = "sequential",
    use_constant_pool: bool = False,
    use_auxiliary_paths: bool = False,
    use_pipeline: bool = True,
) -> tuple[str, str, str, BlockProgram]:
    """
    Pipeline 化的代码生成函数

    Args:
        source: 源代码
        profile: 保护配置
        rng: 随机数生成器
        randomize_order: 是否随机化 block 顺序
        execution_mode: 执行模式
        use_constant_pool: 是否使用常量池
        use_auxiliary_paths: 是否使用辅助路径
        use_pipeline: 是否使用 Pipeline（True 使用新架构）

    Returns:
        (program_wrapper, constant_pool_code, dispatcher_code, BlockProgram)
    """
    if use_pipeline:
        # 使用新的 Pipeline 架构
        if randomize_order:
            pipeline = CodePipeline.create_full()
        else:
            pipeline = CodePipeline.create_default()

        ctx = pipeline.execute(source, profile, rng)

        # 生成常量和分发器
        constant_pool_code = ""
        if ctx.constant_pool:
            constant_pool_code = ctx.constant_pool.generate_pool_table() + "\n"

        # 生成 API 前导码
        api_plan = apply_api_indirection(ctx.tokens, profile, rng)
        api_prelude = api_plan.prelude if api_plan else ""

        # 生成执行器
        dispatcher = ExecutionDispatcher(profile, rng)
        dispatcher_code = dispatcher.generate_dispatcher(ctx.program, mode=execution_mode)

        # 组装最终代码
        program_wrapper = ctx.emitted_code

        return program_wrapper, constant_pool_code, dispatcher_code, ctx.program

    else:
        # 使用原有的 build_block_program
        return build_block_program(
            source, profile, rng,
            randomize_order=randomize_order,
            execution_mode=execution_mode,
            use_constant_pool=use_constant_pool,
            use_auxiliary_paths=use_auxiliary_paths
        )


def rewrite_tokens(tokens: list[Token], profile: ProtectionProfile, rng: random.Random) -> None:
    for token in tokens:
        if token.type is TokenType.STRING and token.bytes_value is not None:
            token.rewritten = profile.intern_string(token.bytes_value, rng)
        elif token.type is TokenType.NUMBER:
            token.rewritten = rewrite_number_literal(token.text, rng, profile)
        elif token.type is TokenType.KEYWORD:
            token.rewritten = rewrite_keyword_literal(token.text, profile)
    rename_local_symbols(tokens, profile, rng)


def apply_api_indirection(tokens: list[Token], profile: ProtectionProfile, rng: random.Random) -> ApiIndirectionPlan:
    """
    Build an indirection layer for API access and rewrite known calls:
      game:GetService("Players") -> call_api(API_GET_SERVICE, API_PLAYERS)
    """
    significant = [i for i, t in enumerate(tokens) if t.type not in (TokenType.WHITESPACE, TokenType.COMMENT)]
    service_to_id: dict[str, int] = {}
    matched_spans: list[tuple[int, int, str]] = []

    for pos in range(len(significant) - 5):
        i0 = significant[pos]
        i1 = significant[pos + 1]
        i2 = significant[pos + 2]
        i3 = significant[pos + 3]
        i4 = significant[pos + 4]
        i5 = significant[pos + 5]
        t0 = tokens[i0]
        t1 = tokens[i1]
        t2 = tokens[i2]
        t3 = tokens[i3]
        t4 = tokens[i4]
        t5 = tokens[i5]
        if not (t0.type is TokenType.IDENTIFIER and t0.text == "game"):
            continue
        if not (t1.type is TokenType.SYMBOL and t1.text == ":"):
            continue
        if not (t2.type is TokenType.IDENTIFIER and t2.text == "GetService"):
            continue
        if not (t3.type is TokenType.SYMBOL and t3.text == "(" and t5.type is TokenType.SYMBOL and t5.text == ")"):
            continue
        if not (t4.type is TokenType.STRING and t4.bytes_value is not None):
            continue
        try:
            service_name = t4.bytes_value.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if service_name not in service_to_id:
            service_to_id[service_name] = len(service_to_id) + 1
        matched_spans.append((i0, i5, service_name))

    if not matched_spans:
        return ApiIndirectionPlan(prelude="", replacements=0)

    call_api_name = random_lua_identifier(rng, "_api")
    api_table_name = random_lua_identifier(rng, "_at")
    arg_table_name = random_lua_identifier(rng, "_as")
    api_get_service_id = 1

    service_expr_by_name: dict[str, str] = {}
    for name in service_to_id:
        service_expr_by_name[name] = profile.intern_string(name.encode("utf-8"), rng)

    for start, end, service_name in matched_spans:
        service_id = service_to_id[service_name]
        api_id_expr = profile.runtime_int_expression(api_get_service_id)
        service_id_expr = profile.runtime_int_expression(service_id)
        tokens[start].rewritten = f"{call_api_name}({api_id_expr},{service_id_expr})"
        for i in range(start + 1, end + 1):
            tokens[i].rewritten = ""

    out: list[str] = []
    out.append(f"local {arg_table_name}={{\n")
    for name, sid in service_to_id.items():
        out.append(f" [{sid}]={service_expr_by_name[name]},\n")
    out.append("}\n")
    out.append(f"local {api_table_name}={{\n")
    out.append(f" [{api_get_service_id}]=function(_a,_b)return game:GetService(_a[_b]) end,\n")
    out.append("}\n")
    out.append(f"local function {call_api_name}(_x,_y)\n")
    out.append(f" local _h={api_table_name}[_x]\n")
    out.append(" if _h==nil then error('api resolver id') end\n")
    out.append(f" return _h({arg_table_name},_y)\n")
    out.append("end\n")
    return ApiIndirectionPlan(prelude="".join(out), replacements=len(matched_spans))


def rename_local_symbols(tokens: list[Token], profile: ProtectionProfile, rng: random.Random) -> None:
    scopes = ScopeStack()
    blocks = [BlockFrame(BlockType.ROOT, True)]
    scopes.push()
    for i, token in enumerate(tokens):
        if token.type in (TokenType.WHITESPACE, TokenType.COMMENT):
            continue
        token.index = i
        if token.is_keyword("local"):
            handle_local_declaration(tokens, i, scopes, profile, rng)
            continue
        if token.is_keyword("function"):
            handle_function_declaration(tokens, i, scopes, blocks, profile, rng)
            continue
        if token.is_keyword("for"):
            handle_for_declaration(tokens, i, scopes, blocks, profile, rng)
            continue
        if token.is_keyword("do"):
            open_block(scopes, blocks, BlockType.DO, True)
            continue
        if token.is_keyword("then"):
            open_block(scopes, blocks, BlockType.THEN, True)
            continue
        if token.is_keyword("repeat"):
            open_block(scopes, blocks, BlockType.REPEAT, True)
            continue
        if token.is_keyword("else") or token.is_keyword("elseif"):
            close_if_branch(scopes, blocks)
            open_block(scopes, blocks, BlockType.ELSE if token.is_keyword("else") else BlockType.THEN, True)
            continue
        if token.is_keyword("end"):
            close_nearest_scoped_block(scopes, blocks)
            continue
        if token.is_keyword("until"):
            close_nearest_repeat(scopes, blocks)
            continue
        if token.type is TokenType.IDENTIFIER:
            maybe_rewrite_identifier(tokens, i, scopes)


def handle_local_declaration(
    tokens: list[Token],
    index: int,
    scopes: ScopeStack,
    profile: ProtectionProfile,
    rng: random.Random,
) -> None:
    next_token = next_significant(tokens, index + 1)
    if next_token is not None and next_token.is_keyword("function"):
        name_token = next_significant(tokens, next_token.index + 1)
        if name_token is not None and name_token.type is TokenType.IDENTIFIER:
            name_token.rewritten = scopes.declare(name_token.text, profile.next_local_name(rng))
        return
    cursor = index + 1
    while True:
        current = next_significant(tokens, cursor)
        if current is None or current.type is not TokenType.IDENTIFIER:
            return
        current.rewritten = scopes.declare(current.text, profile.next_local_name(rng))
        separator = next_significant(tokens, current.index + 1)
        if separator is None or not separator.is_symbol(","):
            return
        cursor = separator.index + 1


def handle_function_declaration(
    tokens: list[Token],
    index: int,
    scopes: ScopeStack,
    blocks: list[BlockFrame],
    profile: ProtectionProfile,
    rng: random.Random,
) -> None:
    previous = previous_significant(tokens, index - 1)
    next_token = next_significant(tokens, index + 1)
    is_local_function = previous is not None and previous.is_keyword("local")
    if not is_local_function and next_token is not None and next_token.type is TokenType.IDENTIFIER:
        after_name = next_significant(tokens, next_token.index + 1)
        if after_name is not None and not after_name.is_symbol(".") and not after_name.is_symbol(":"):
            alias = scopes.resolve(next_token.text)
            if alias is not None:
                next_token.rewritten = alias
    open_paren = find_next_symbol(tokens, index + 1, "(")
    if open_paren is None:
        return
    open_block(scopes, blocks, BlockType.FUNCTION, True)
    declare_function_parameters(tokens, open_paren.index, scopes, profile, rng)


def handle_for_declaration(
    tokens: list[Token],
    index: int,
    scopes: ScopeStack,
    blocks: list[BlockFrame],
    profile: ProtectionProfile,
    rng: random.Random,
) -> None:
    open_block(scopes, blocks, BlockType.FOR, True)
    cursor = index + 1
    while True:
        current = next_significant(tokens, cursor)
        if current is None or current.type is not TokenType.IDENTIFIER:
            return
        current.rewritten = scopes.declare(current.text, profile.next_local_name(rng))
        separator = next_significant(tokens, current.index + 1)
        if separator is None or not separator.is_symbol(","):
            return
        cursor = separator.index + 1


def declare_function_parameters(
    tokens: list[Token],
    open_paren_index: int,
    scopes: ScopeStack,
    profile: ProtectionProfile,
    rng: random.Random,
) -> None:
    depth = 0
    for i in range(open_paren_index, len(tokens)):
        token = tokens[i]
        if token.type in (TokenType.WHITESPACE, TokenType.COMMENT):
            continue
        token.index = i
        if token.is_symbol("("):
            depth += 1
            continue
        if token.is_symbol(")"):
            depth -= 1
            if depth == 0:
                return
            continue
        if depth == 1 and token.type is TokenType.IDENTIFIER:
            token.rewritten = scopes.declare(token.text, profile.next_local_name(rng))


def maybe_rewrite_identifier(tokens: list[Token], index: int, scopes: ScopeStack) -> None:
    token = tokens[index]
    # Keep Roblox/Luau ambient globals untouched.
    if token.text in LUAU_PROTECTED_GLOBALS:
        return
    previous = previous_significant(tokens, index - 1)
    next_token = next_significant(tokens, index + 1)
    if previous is not None and (previous.is_symbol(".") or previous.is_symbol(":") or previous.is_keyword("goto")):
        return
    if previous is not None and (
        previous.is_keyword("type")
        or previous.is_keyword("export")
        or previous.is_keyword("typeof")
    ):
        return
    if previous is not None and previous.is_symbol("::"):
        return
    if next_token is not None and next_token.is_symbol("::"):
        return
    if next_token is not None and next_token.is_symbol(":"):
        # Luau type annotations: local x: T = ...
        return
    if previous is not None and previous.is_keyword("function"):
        return
    alias = scopes.resolve(token.text)
    if alias is not None:
        token.rewritten = alias


def build_runtime_prelude(profile: ProtectionProfile) -> str:
    out: list[str] = []
    out.append(f"local {profile.marker_name}={as_lua_string(profile.watermark)}\n")
    out.append(f"local {profile.char_name}=string.char\n")
    out.append(f"local {profile.sub_name}=string.sub\n")
    out.append(f"local {profile.byte_name}=string.byte\n")
    out.append("local function _rol8(x,s)\n")
    out.append(" s=s%8\n")
    out.append(" if s==0 then return x%256 end\n")
    out.append(" local a=(x*(2^s))%256\n")
    out.append(" local b=math.floor((x%256)/(2^(8-s)))\n")
    out.append(" return (a+b)%256\n")
    out.append("end\n")
    out.append("local function _ror8(x,s)\n")
    out.append(" s=s%8\n")
    out.append(" if s==0 then return x%256 end\n")
    out.append(" local a=math.floor((x%256)/(2^s))\n")
    out.append(" local b=((x%256)*(2^(8-s)))%256\n")
    out.append(" return (a+b)%256\n")
    out.append("end\n")
    out.append(f"local {profile.concat_name}=table.concat\n")
    out.append(f"local {profile.tonumber_name}=tonumber\n")
    out.append(f"local {profile.cache_name}={{}}\n")
    out.append(f"local {profile.nibble_map_name}={{")
    out.append(",".join(f"[{as_lua_string(ch)}]={i}" for i, ch in enumerate(profile.encoded_alphabet)))
    out.append("}\n")
    out.append(f"local {profile.lookup_name}={{\n")
    for key, value in profile.public_to_handle_indexes.items():
        out.append(f" [{key}]={value + profile.lookup_bias},\n")
    out.append("}\n")
    out.append(f"local {profile.cache_lookup_name}={{\n")
    for key, value in profile.public_to_cache_indexes.items():
        out.append(f" [{key}]={value + profile.cache_bias},\n")
    out.append("}\n")
    out.append(f"local {profile.pool_lookup_name}={{\n")
    for key, value in profile.physical_to_storage_indexes.items():
        out.append(f" [{key}]={value + profile.pool_bias},\n")
    out.append("}\n")
    if profile.runtime_variant != 0:
        out.append(
            f"local {profile.field_map_name}={{"
            f"[{profile.payload_field_index}]={as_lua_string(profile.payload_field)},"
            f"[{profile.payload_tail_field_index}]={as_lua_string(profile.payload_field + 'x')},"
            f"[{profile.key_field_index}]={as_lua_string(profile.key_field)},"
            f"[{profile.state_field_index}]={as_lua_string(profile.state_field)},"
            f"[{profile.slot_field_index}]={as_lua_string(profile.slot_field)},"
            f"[{profile.handle_field_index}]={as_lua_string(profile.handle_field)}"
            f"}}\n"
        )
    out.append(f"local {profile.handle_map_name}={{\n")
    for key, value in profile.handle_to_encoded_physical_indexes.items():
        if profile.runtime_variant == 0:
            out.append(f" [{key}]={{{value},{key + profile.slot_bias}}},\n")
        else:
            out.append(
                f" [{key}]={{{profile.slot_field}={value},{profile.handle_field}={key + profile.slot_bias}}},\n"
            )
    out.append("}\n")
    out.append(f"local {profile.pool_name}={{\n")
    for key, physical_index in profile.string_pool_indexes.items():
        encoded = profile.string_pool_by_key[key]
        storage_index = profile.string_storage_indexes.get(key, physical_index)
        if profile.runtime_variant == 0:
            out.append(
                f" [{storage_index}]={{{as_lua_string(encoded.payload_head)},{as_lua_string(encoded.payload_tail)},{encoded.key},{encoded.state}}},\n"
            )
        else:
            out.append(
                f" [{storage_index}]={{{profile.payload_field}={as_lua_string(encoded.payload_head)},"
                f"{profile.payload_field}x={as_lua_string(encoded.payload_tail)},"
                f"{profile.key_field}={encoded.key},{profile.state_field}={encoded.state}}},\n"
            )
    out.append("}\n")
    out.append(f"local function {profile.hex_pair_name}({profile.arg_a},{profile.arg_b})\n")
    append_helper_return(
        out,
        profile,
        f"{profile.nibble_map_name}[{profile.sub_name}({profile.arg_a},{profile.arg_b},{profile.arg_b})]*16+"
        f"{profile.nibble_map_name}[{profile.sub_name}({profile.arg_a},{profile.arg_b}+1,{profile.arg_b}+1)]",
    )
    out.append("end\n")
    for variant, decode_name in enumerate(profile.decode_names):
        out.append(f"local function {decode_name}({profile.arg_a},{profile.arg_b},{profile.arg_c})\n")
        out.append(f" local {profile.out_name}={{}}\n")
        out.append(f" local {profile.state_name}={profile.arg_c}\n")
        out.append(f" for {profile.index_name}=1,#{profile.arg_a},2 do\n")
        if variant == 0:
            out.append(f"  local {profile.mask_name}=({profile.arg_b}+{profile.state_name})%256\n")
        elif variant == 1:
            out.append(f"  local {profile.mask_name}=({profile.arg_b}+({profile.state_name}*3))%256\n")
        elif variant == 2:
            out.append(f"  local {profile.mask_name}=(({profile.arg_b}~{profile.state_name})+{profile.arg_b})%256\n")
        else:
            out.append(f"  local {profile.mask_name}=(({profile.arg_b}*5)+{profile.state_name})%256\n")
        out.append(
            f"  local {profile.byte_temp_name}={profile.hex_pair_name}({profile.arg_a},{profile.index_name})\n"
        )
        if variant == 0:
            out.append(f"  {profile.byte_temp_name}=({profile.byte_temp_name}~{profile.mask_name})%256\n")
        elif variant == 1:
            out.append(f"  {profile.byte_temp_name}=({profile.byte_temp_name}-{profile.mask_name})%256\n")
        elif variant == 2:
            out.append(f"  {profile.byte_temp_name}=_ror8({profile.byte_temp_name},{profile.mask_name}%8)\n")
        else:
            out.append(f"  {profile.byte_temp_name}=(({profile.byte_temp_name}-{profile.mask_name})*205)%256\n")
        out.append(f"  {profile.push_name}({profile.out_name},{profile.char_name}({profile.byte_temp_name}))\n")
        out.append(
            f"  {profile.state_name}=({profile.state_name}*{profile.state_multipliers[variant]}+{profile.state_increments[variant]})%256\n"
        )
        out.append(" end\n")
        append_helper_return(out, profile, f"{profile.concat_name}({profile.out_name})")
        out.append("end\n")
    out.append(f"local function {profile.resolve_name}({profile.arg_a})\n")
    out.append(f" local {profile.arg_b}={profile.read_name}({profile.handle_map_name},{profile.arg_a})\n")
    if profile.runtime_variant == 0:
        append_helper_return(out, profile, f"{profile.arg_b}[1]-{profile.slot_bias}")
    else:
        append_helper_return(
            out,
            profile,
            f"{profile.arg_b}[{profile.field_map_name}[{profile.slot_field_index}]]-{profile.slot_bias}",
        )
    out.append("end\n")
    out.append(f"local function {profile.cache_resolve_name}({profile.arg_a})\n")
    append_helper_return(out, profile, f"{profile.read_name}({profile.cache_lookup_name},{profile.arg_a})-{profile.cache_bias}")
    out.append("end\n")
    out.append(f"local function {profile.lookup_resolve_name}({profile.arg_a})\n")
    append_helper_return(out, profile, f"{profile.read_name}({profile.lookup_name},{profile.arg_a})-{profile.lookup_bias}")
    out.append("end\n")
    out.append(f"local function {profile.pool_resolve_name}({profile.arg_a})\n")
    append_helper_return(out, profile, f"{profile.read_name}({profile.pool_lookup_name},{profile.arg_a})-{profile.pool_bias}")
    out.append("end\n")
    out.append(f"local function {profile.payload_join_name}({profile.arg_a},{profile.arg_b})\n")
    append_helper_return(out, profile, f"{profile.arg_a}..{profile.arg_b}")
    out.append("end\n")
    out.append(f"local function {profile.push_name}({profile.arg_a},{profile.arg_b})\n")
    out.append(f" {profile.arg_a}[#{profile.arg_a}+1]={profile.arg_b}\n")
    append_helper_return(out, profile, profile.arg_a)
    out.append("end\n")
    out.append(f"local function {profile.store_name}({profile.arg_a},{profile.arg_b},{profile.arg_c})\n")
    out.append(f" {profile.arg_a}[{profile.arg_b}]={profile.arg_c}\n")
    append_helper_return(out, profile, profile.arg_c)
    out.append("end\n")
    out.append(f"local function {profile.read_name}({profile.arg_a},{profile.arg_b})\n")
    append_helper_return(out, profile, f"{profile.arg_a}[{profile.arg_b}]")
    out.append("end\n")
    if profile.runtime_variant != 0:
        out.append(f"local function {profile.field_resolve_name}({profile.arg_a},{profile.arg_b})\n")
        append_helper_return(
            out,
            profile,
            f"{profile.read_name}({profile.arg_a},{profile.read_name}({profile.field_map_name},{profile.arg_b}))",
        )
        out.append("end\n")
    if profile.runtime_variant == 0:
        for variant, fetch_name in enumerate(profile.fetch_names):
            out.append(f"local function {fetch_name}({profile.arg_a})\n")
            out.append(f" local {profile.mask_name}={profile.cache_resolve_name}({profile.arg_a})\n")
            out.append(f" local {profile.arg_b}={profile.read_name}({profile.cache_name},{profile.mask_name})\n")
            out.append(f" local {profile.state_name}=0\n")
            out.append(" while true do\n")
            out.append(f"  if {profile.state_name}==0 then\n")
            out.append(f"   if {profile.arg_b}~=nil then {profile.state_name}=2 else {profile.state_name}=1 end\n")
            out.append(f"  elseif {profile.state_name}==1 then\n")
            out.append(f"   local {profile.out_name}={profile.lookup_resolve_name}({profile.arg_a})\n")
            out.append(
                f"   local {profile.arg_c}={profile.read_name}({profile.pool_name},{profile.pool_resolve_name}({profile.resolve_name}({profile.out_name})))\n"
            )
            out.append(
                f"   {profile.arg_b}={profile.decode_names[variant]}({profile.payload_join_name}({profile.arg_c}[1],{profile.arg_c}[2]),{profile.arg_c}[3],{profile.arg_c}[4])\n"
            )
            out.append(f"   {profile.store_name}({profile.cache_name},{profile.mask_name},{profile.arg_b})\n")
            out.append(f"   {profile.state_name}=2\n")
            out.append("  else\n")
            out.append("   break\n")
            out.append("  end\n")
            out.append(" end\n")
            out.append(f" return {profile.arg_b}\n")
            out.append("end\n")
    else:
        for variant, fetch_name in enumerate(profile.fetch_names):
            out.append(f"local function {fetch_name}({profile.arg_a})\n")
            out.append(f" local {profile.mask_name}={profile.cache_resolve_name}({profile.arg_a})\n")
            out.append(f" local {profile.arg_b}={profile.read_name}({profile.cache_name},{profile.mask_name})\n")
            out.append(f" local {profile.state_name}=0\n")
            out.append(" while true do\n")
            out.append(f"  if {profile.state_name}==0 then\n")
            out.append(f"   if {profile.arg_b}==nil then {profile.state_name}=1 else {profile.state_name}=2 end\n")
            out.append(f"  elseif {profile.state_name}==1 then\n")
            out.append(f"   local {profile.out_name}={profile.lookup_resolve_name}({profile.arg_a})\n")
            out.append(
                f"   local {profile.arg_c}={profile.read_name}({profile.pool_name},{profile.pool_resolve_name}({profile.resolve_name}({profile.out_name})))\n"
            )
            out.append(
                f"   {profile.arg_b}={profile.decode_names[variant]}("
                f"{profile.payload_join_name}({profile.field_resolve_name}({profile.arg_c},{profile.payload_field_index}),"
                f"{profile.field_resolve_name}({profile.arg_c},{profile.payload_tail_field_index})),"
                f"{profile.field_resolve_name}({profile.arg_c},{profile.key_field_index}),"
                f"{profile.field_resolve_name}({profile.arg_c},{profile.state_field_index}))\n"
            )
            out.append(f"   {profile.store_name}({profile.cache_name},{profile.mask_name},{profile.arg_b})\n")
            out.append(f"   {profile.state_name}=2\n")
            out.append("  else\n")
            out.append("   break\n")
            out.append("  end\n")
            out.append(" end\n")
            out.append(f" return {profile.arg_b}\n")
            out.append("end\n")
    out.append(f"local function {profile.number_name}({profile.arg_a},{profile.arg_b})\n")
    append_helper_return(out, profile, f"({profile.arg_a}-{profile.arg_b})+{profile.number_pad}-{profile.number_pad}")
    out.append("end\n")
    out.append(f"local function {profile.value_wrap_name}({profile.arg_a})\n")
    if profile.value_wrap_variant == 0:
        out.append(f" return {profile.arg_a}\n")
    elif profile.value_wrap_variant == 1:
        out.append(f" return ({{[{profile.number_name}(1,0)]={profile.arg_a}}})[{profile.number_name}(1,0)]\n")
    else:
        out.append(f" return (function({profile.arg_b})return {profile.arg_b} end)({profile.arg_a})\n")
    out.append("end\n")
    out.append(f"if false then print({profile.marker_name},{profile.byte_name}('A')) end\n")
    return "".join(out)


def append_helper_return(out: list[str], profile: ProtectionProfile, expression: str) -> None:
    if profile.helper_return_variant == 0:
        out.append(f" return {expression}\n")
    else:
        out.append(f" local {profile.return_temp_name}={expression}\n")
        out.append(f" return {profile.return_temp_name}\n")


def rewrite_keyword_literal(keyword: str, profile: ProtectionProfile) -> str:
    if keyword == "true":
        return profile.wrap_value_expression(profile.true_expression())
    if keyword == "false":
        return profile.wrap_value_expression(profile.false_expression())
    if keyword == "nil":
        return profile.wrap_value_expression(profile.nil_expression)
    return keyword


def rewrite_number_literal(literal: str, rng: random.Random, profile: ProtectionProfile) -> str:
    if not is_integer_literal(literal):
        return literal
    try:
        value = parse_integer_literal(literal)
    except ValueError:
        return literal
    mask = 97 + rng.randint(0, 899)
    if profile.expression_variant == 0:
        rewritten = f"{profile.number_name}({value + mask},{mask})"
    elif profile.expression_variant == 1:
        rewritten = f"(({profile.number_name}({value + mask},{mask})+{profile.number_bias})-{profile.number_bias})"
    else:
        rewritten = f"({profile.number_name}({value + mask},{mask})*1)"
    return profile.wrap_value_expression(rewritten)


def encode_lua_bytes(raw_bytes: bytes, rng: random.Random, profile: ProtectionProfile) -> EncodedString:
    variant = rng.randint(0, len(profile.decode_names) - 1)
    key = 17 + rng.randint(0, 199)
    state = 11 + rng.randint(0, 199)
    rolling = state
    hex_parts: list[str] = []
    for raw_byte in raw_bytes:
        mask = (key + rolling) % 256
        # Polymorphic reversible strategies for compiler experiments.
        if variant == 0:
            # strategy_a: XOR-style
            encoded = raw_byte ^ mask
        elif variant == 1:
            # strategy_b: add + mod
            encoded = (raw_byte + mask) % 256
        elif variant == 2:
            # strategy_c: bit rotate left by (mask mod 8)
            shift = mask % 8
            if shift == 0:
                encoded = raw_byte
            else:
                encoded = ((raw_byte << shift) & 0xFF) | (raw_byte >> (8 - shift))
        else:
            # strategy_d: affine map (invertible mod 256)
            encoded = ((raw_byte * 5) + mask) % 256
        hex_parts.append(profile.encoded_alphabet[(encoded >> 4) & 0xF])
        hex_parts.append(profile.encoded_alphabet[encoded & 0xF])
        rolling = (rolling * profile.state_multipliers[variant] + profile.state_increments[variant]) % 256
    payload = "".join(hex_parts)
    if len(payload) < 4:
        split_point = len(payload)
    else:
        split_point = 2 + (rng.randint(0, max((len(payload) // 2) - 1, 0)) * 2)
        if split_point > len(payload):
            split_point = len(payload)
    return EncodedString(payload, payload[:split_point], payload[split_point:], key, state, variant)


def open_block(scopes: ScopeStack, blocks: list[BlockFrame], block_type: BlockType, has_scope: bool) -> None:
    blocks.append(BlockFrame(block_type, has_scope))
    if has_scope:
        scopes.push()


def close_nearest_scoped_block(scopes: ScopeStack, blocks: list[BlockFrame]) -> None:
    while blocks:
        frame = blocks.pop()
        if frame.has_scope:
            scopes.pop()
        if frame.type is not BlockType.ROOT:
            return


def close_nearest_repeat(scopes: ScopeStack, blocks: list[BlockFrame]) -> None:
    while blocks:
        frame = blocks.pop()
        if frame.has_scope:
            scopes.pop()
        if frame.type is BlockType.REPEAT:
            return


def close_if_branch(scopes: ScopeStack, blocks: list[BlockFrame]) -> None:
    if not blocks:
        return
    top = blocks[-1]
    if top.type in (BlockType.THEN, BlockType.ELSE):
        blocks.pop()
        if top.has_scope:
            scopes.pop()


def next_significant(tokens: list[Token], start: int) -> Token | None:
    for i in range(start, len(tokens)):
        token = tokens[i]
        if token.type not in (TokenType.WHITESPACE, TokenType.COMMENT):
            token.index = i
            return token
    return None


def previous_significant(tokens: list[Token], start: int) -> Token | None:
    for i in range(start, -1, -1):
        token = tokens[i]
        if token.type not in (TokenType.WHITESPACE, TokenType.COMMENT):
            token.index = i
            return token
    return None


def find_next_symbol(tokens: list[Token], start: int, symbol: str) -> Token | None:
    for i in range(start, len(tokens)):
        token = tokens[i]
        if token.type not in (TokenType.WHITESPACE, TokenType.COMMENT):
            token.index = i
            if token.is_symbol(symbol):
                return token
    return None


def needs_space(previous: Token, current: Token) -> bool:
    if not previous.rendered() or not current.rendered():
        return False
    left = previous.rendered()[-1]
    right = current.rendered()[0]
    if is_word_like(previous) and is_word_like(current):
        return True
    if left == "-" and right == "-":
        return True
    if left == "[" and right == "[":
        return True
    return False


def is_word_like(token: Token) -> bool:
    return (
        token.type in (TokenType.IDENTIFIER, TokenType.NUMBER, TokenType.STRING)
        or (token.type is TokenType.SYMBOL and token.rendered() == "...")
        or (token.type is TokenType.KEYWORD and token.text in LUA_KEYWORDS)
    )


def is_integer_literal(literal: str) -> bool:
    if not literal:
        return False
    if literal.startswith(("0x", "0X")):
        return len(literal) > 2 and all(is_hex_digit(char) for char in literal[2:])
    return all(char.isdigit() for char in literal)


def parse_integer_literal(literal: str) -> int:
    if literal.startswith(("0x", "0X")):
        return int(literal[2:], 16)
    return int(literal, 10)


def create_time_seeded_random() -> random.Random:
    # Time-based seed mode requested by user.
    seed = int(time.time() * 1000) ^ random.getrandbits(32)
    return random.Random(seed)


def shuffle_tables(profile: ProtectionProfile, rng: random.Random) -> None:
    profile.finalize_pool_layout(rng)


def randomize_algorithms(profile: ProtectionProfile, rng: random.Random) -> None:
    profile.runtime_variant = rng.randint(0, 1)
    profile.expression_variant = rng.randint(0, 2)
    profile.fetch_variant = rng.randint(0, 2)
    profile.value_wrap_variant = rng.randint(0, 2)
    profile.helper_return_variant = rng.randint(0, 1)


def random_lua_identifier(rng: random.Random, prefix: str) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    length = 6 + rng.randint(0, 4)
    return prefix + prefix + "".join(rng.choice(alphabet) for _ in range(length))


def as_lua_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")
    return "\"" + escaped + "\""


def sanitize_comment(value: str) -> str:
    return value.replace("]]", "] ]")


def strip_leading_bom(value: str) -> str:
    if value.startswith("\ufeff"):
        return value[1:]
    return value


def to_hex_key(data: bytes) -> str:
    return "".join(f"{byte:02X}" for byte in data)


def shuffled_alphabet(rng: random.Random) -> str:
    chars = list("0123456789ABCDEF")
    rng.shuffle(chars)
    return "".join(chars)


def is_identifier_start(value: str) -> bool:
    return value == "_" or value.isalpha()


def is_identifier_part(value: str) -> bool:
    return value == "_" or value.isalnum()


def is_hex_digit(value: str) -> bool:
    return value.lower() in "0123456789abcdef"


# ============================================================
# AST (analysis-only, minimal Luau subset) + CFG builder
# ============================================================


@dataclass(frozen=True)
class AstNode:
    pass


@dataclass(frozen=True)
class Stmt(AstNode):
    pass


@dataclass(frozen=True)
class Block(AstNode):
    statements: list[Stmt]


@dataclass(frozen=True)
class RawStmt(Stmt):
    """
    Fallback statement node.
    Used for statements we don't explicitly model yet (kept for CFG visualization).
    """

    text: str


@dataclass(frozen=True)
class BreakStmt(Stmt):
    pass


@dataclass(frozen=True)
class ReturnStmt(Stmt):
    expr_text: str | None = None


@dataclass(frozen=True)
class IfClause(AstNode):
    condition_text: str  # rendered tokens between `if/elseif` and `then`
    body: Block


@dataclass(frozen=True)
class IfStmt(Stmt):
    clauses: list[IfClause]  # if + 0..n elseif
    else_body: Block | None


@dataclass(frozen=True)
class WhileStmt(Stmt):
    condition_text: str  # rendered tokens between `while` and `do`
    body: Block


@dataclass(frozen=True)
class RepeatStmt(Stmt):
    body: Block
    until_condition_text: str  # rendered tokens between `until` and end of stmt


def _iter_meaningful_tokens(tokens: list[Token]) -> Iterable[Token]:
    for token in tokens:
        if token.type in (TokenType.WHITESPACE, TokenType.COMMENT):
            continue
        yield token


def _render_tokens(tokens: list[Token]) -> str:
    """
    Render tokens back to Lua source (roughly), keeping spacing sane.
    This is for analysis/visualization only.
    """
    parts: list[str] = []
    previous: Token | None = None
    for token in tokens:
        if token.type in (TokenType.WHITESPACE, TokenType.COMMENT):
            continue
        if previous is not None and needs_space(previous, token):
            parts.append(" ")
        parts.append(token.text)
        previous = token
    return "".join(parts)


class ParseError(Exception):
    pass


class _AstParser:
    """
    Minimal statement parser built on top of this file's Tokenizer.

    Supported statements:
    - if / elseif / else / end
    - while / do / end
    - repeat ... until <expr>
    - break
    - return [<expr>]

    Everything else is captured as RawStmt(<rendered statement text>) so CFG visualization
    can still show something.
    """

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = [t for t in tokens if t.type not in (TokenType.WHITESPACE, TokenType.COMMENT)]
        self.i = 0

    def _at_end(self) -> bool:
        return self.i >= len(self.tokens)

    def _peek(self) -> Token | None:
        return None if self._at_end() else self.tokens[self.i]

    def _advance(self) -> Token:
        if self._at_end():
            raise ParseError("Unexpected end of input")
        token = self.tokens[self.i]
        self.i += 1
        return token

    def _match_keyword(self, value: str) -> bool:
        token = self._peek()
        if token is not None and token.is_keyword(value):
            self.i += 1
            return True
        return False

    def _expect_keyword(self, value: str) -> None:
        token = self._advance()
        if not token.is_keyword(value):
            raise ParseError(f"Expected keyword '{value}', got '{token.text}'")

    def _collect_until_keyword(self, keyword: str) -> list[Token]:
        """
        Collect tokens until (but not including) a keyword at paren/bracket/brace nesting == 0.
        """
        collected: list[Token] = []
        depth = 0
        while not self._at_end():
            token = self._peek()
            assert token is not None
            if depth == 0 and token.type is TokenType.KEYWORD and token.text == keyword:
                break
            if token.type is TokenType.SYMBOL:
                if token.text in ("(", "{", "["):
                    depth += 1
                elif token.text in (")", "}", "]"):
                    depth = max(0, depth - 1)
            collected.append(self._advance())
        return collected

    def _collect_statement_tokens(self) -> list[Token]:
        """
        Heuristic: collect tokens until we hit a block delimiter keyword at depth==0,
        or until we reach end.
        """
        collected: list[Token] = []
        depth = 0
        while not self._at_end():
            token = self._peek()
            assert token is not None
            if depth == 0 and token.type is TokenType.KEYWORD and token.text in (
                "if",
                "elseif",
                "else",
                "end",
                "while",
                "repeat",
                "until",
                "do",
                "break",
                "return",
            ):
                break
            if token.type is TokenType.SYMBOL:
                if token.text in ("(", "{", "["):
                    depth += 1
                elif token.text in (")", "}", "]"):
                    depth = max(0, depth - 1)
                elif depth == 0 and token.text == ";":
                    # statement terminator
                    self._advance()
                    break
            collected.append(self._advance())
        return collected

    def parse_block(self, until_keywords: set[str]) -> Block:
        statements: list[Stmt] = []
        while not self._at_end():
            token = self._peek()
            assert token is not None
            if token.type is TokenType.KEYWORD and token.text in until_keywords:
                break
            statements.append(self.parse_stmt())
        return Block(statements)

    def parse_stmt(self) -> Stmt:
        token = self._peek()
        if token is None:
            return RawStmt("")
        if token.is_keyword("if"):
            return self._parse_if()
        if token.is_keyword("while"):
            return self._parse_while()
        if token.is_keyword("repeat"):
            return self._parse_repeat()
        if token.is_keyword("break"):
            self._advance()
            return BreakStmt()
        if token.is_keyword("return"):
            self._advance()
            expr_tokens = self._collect_statement_tokens()
            expr_text = _render_tokens(expr_tokens).strip() or None
            return ReturnStmt(expr_text=expr_text)

        # fallback: capture unknown statement tokens for visualization
        stmt_tokens = self._collect_statement_tokens()
        text = _render_tokens(stmt_tokens).strip()
        if not text:
            # consume a single token to avoid infinite loops
            self._advance()
            return RawStmt(text=token.text)
        return RawStmt(text=text)

    def _parse_if(self) -> IfStmt:
        self._expect_keyword("if")
        cond_tokens = self._collect_until_keyword("then")
        self._expect_keyword("then")
        clauses: list[IfClause] = [IfClause(_render_tokens(cond_tokens).strip(), self.parse_block({"elseif", "else", "end"}))]
        while self._match_keyword("elseif"):
            elseif_cond_tokens = self._collect_until_keyword("then")
            self._expect_keyword("then")
            clauses.append(IfClause(_render_tokens(elseif_cond_tokens).strip(), self.parse_block({"elseif", "else", "end"})))
        else_body: Block | None = None
        if self._match_keyword("else"):
            else_body = self.parse_block({"end"})
        self._expect_keyword("end")
        return IfStmt(clauses=clauses, else_body=else_body)

    def _parse_while(self) -> WhileStmt:
        self._expect_keyword("while")
        cond_tokens = self._collect_until_keyword("do")
        self._expect_keyword("do")
        body = self.parse_block({"end"})
        self._expect_keyword("end")
        return WhileStmt(condition_text=_render_tokens(cond_tokens).strip(), body=body)

    def _parse_repeat(self) -> RepeatStmt:
        self._expect_keyword("repeat")
        body = self.parse_block({"until"})
        self._expect_keyword("until")
        cond_tokens = self._collect_statement_tokens()
        return RepeatStmt(body=body, until_condition_text=_render_tokens(cond_tokens).strip())


@dataclass
class CfgEdge:
    src: int
    dst: int
    kind: str  # e.g. "next", "true", "false", "back", "break"


@dataclass
class BasicBlock:
    id: int
    statements: list[str]
    terminated: bool = False


@dataclass
class ControlFlowGraph:
    entry_id: int
    exit_id: int
    blocks: dict[int, BasicBlock]
    edges: list[CfgEdge]

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry": self.entry_id,
            "exit": self.exit_id,
            "blocks": [
                {"id": block.id, "statements": list(block.statements)}
                for block in sorted(self.blocks.values(), key=lambda b: b.id)
            ],
            "edges": [{"src": e.src, "dst": e.dst, "kind": e.kind} for e in self.edges],
        }


@dataclass(frozen=True)
class IRJump:
    target: int


@dataclass(frozen=True)
class IRBranch:
    condition_text: str
    true_target: int
    false_target: int


@dataclass
class IRBlock:
    id: int
    statements: list[str]
    terminator: IRJump | IRBranch | str | None = None


@dataclass
class ControlFlowIR:
    entry_id: int
    exit_id: int
    blocks: dict[int, IRBlock]

    def to_dict(self) -> dict[str, Any]:
        out_blocks: list[dict[str, Any]] = []
        for block in sorted(self.blocks.values(), key=lambda b: b.id):
            term: dict[str, Any] | str | None
            if isinstance(block.terminator, IRJump):
                term = {"kind": "jump", "target": block.terminator.target}
            elif isinstance(block.terminator, IRBranch):
                term = {
                    "kind": "branch",
                    "condition": block.terminator.condition_text,
                    "true_target": block.terminator.true_target,
                    "false_target": block.terminator.false_target,
                }
            else:
                term = block.terminator
            out_blocks.append(
                {
                    "id": block.id,
                    "statements": list(block.statements),
                    "terminator": term,
                }
            )
        return {"entry": self.entry_id, "exit": self.exit_id, "blocks": out_blocks}


@dataclass(frozen=True)
class _LoopCtx:
    break_target: int
    continue_target: int


class _CfgBuilder:
    def __init__(self) -> None:
        self._next_id = 1
        self.blocks: dict[int, BasicBlock] = {}
        self.edges: list[CfgEdge] = []

    def new_block(self) -> BasicBlock:
        block = BasicBlock(id=self._next_id, statements=[])
        self._next_id += 1
        self.blocks[block.id] = block
        return block

    def add_edge(self, src: int, dst: int, kind: str) -> None:
        self.edges.append(CfgEdge(src=src, dst=dst, kind=kind))

    def add_stmt(self, block_id: int, text: str) -> None:
        self.blocks[block_id].statements.append(text)

    def terminate(self, block_id: int) -> None:
        self.blocks[block_id].terminated = True

    def build_from_block(self, block: Block) -> ControlFlowGraph:
        entry = self.new_block()
        exit_block = self.new_block()
        self._build_stmt_list(block.statements, entry.id, exit_block.id, loop=None)
        # ensure exit exists even if unreachable; visualization can handle it
        return ControlFlowGraph(entry_id=entry.id, exit_id=exit_block.id, blocks=self.blocks, edges=self.edges)

    def _link_if_not_terminated(self, from_id: int, to_id: int, kind: str = "next") -> None:
        if not self.blocks[from_id].terminated:
            self.add_edge(from_id, to_id, kind)

    def _build_stmt_list(
        self,
        stmts: list[Stmt],
        entry_id: int,
        exit_id: int,
        loop: _LoopCtx | None,
        *,
        link_to_exit: bool = True,
    ) -> int:
        cur = entry_id
        for stmt in stmts:
            cur = self._build_stmt(stmt, cur, exit_id, loop)
            if self.blocks[cur].terminated:
                # create a fresh block so subsequent (unreachable) statements still get an id for viz
                cur = self.new_block().id
        if link_to_exit:
            self._link_if_not_terminated(cur, exit_id, "next")
        return cur

    def _build_stmt(self, stmt: Stmt, cur_id: int, exit_id: int, loop: _LoopCtx | None) -> int:
        if isinstance(stmt, RawStmt):
            if stmt.text:
                self.add_stmt(cur_id, stmt.text)
            return cur_id

        if isinstance(stmt, BreakStmt):
            self.add_stmt(cur_id, "break")
            if loop is None:
                # break outside loop: treat as terminating
                self.terminate(cur_id)
                return cur_id
            self.add_edge(cur_id, loop.break_target, "break")
            self.terminate(cur_id)
            return cur_id

        if isinstance(stmt, ReturnStmt):
            if stmt.expr_text:
                self.add_stmt(cur_id, f"return {stmt.expr_text}")
            else:
                self.add_stmt(cur_id, "return")
            self.terminate(cur_id)
            return cur_id

        if isinstance(stmt, IfStmt):
            # current block becomes the decision point
            join = self.new_block()
            # build each clause
            for idx, clause in enumerate(stmt.clauses):
                then_entry = self.new_block()
                # label branch edges: first clause uses "if-true"/"if-false" semantics, but for viz keep "true"/"false"
                if idx == 0:
                    self.add_stmt(cur_id, f"if {clause.condition_text} then")
                else:
                    self.add_stmt(cur_id, f"elseif {clause.condition_text} then")
                self.add_edge(cur_id, then_entry.id, "true")
                # false edge goes to next decision point (new block) or else/join
                next_decision: int | None = None
                if idx < len(stmt.clauses) - 1:
                    next_decision = self.new_block().id
                    self.add_edge(cur_id, next_decision, "false")
                else:
                    # last clause: false -> else or join
                    if stmt.else_body is not None:
                        else_entry = self.new_block()
                        self.add_edge(cur_id, else_entry.id, "false")
                        self._build_stmt_list(clause.body.statements, then_entry.id, join.id, loop, link_to_exit=True)
                        self._build_stmt_list(stmt.else_body.statements, else_entry.id, join.id, loop, link_to_exit=True)
                        return join.id
                    self.add_edge(cur_id, join.id, "false")
                self._build_stmt_list(clause.body.statements, then_entry.id, join.id, loop, link_to_exit=True)
                if next_decision is not None:
                    cur_id = next_decision
                    continue
                return join.id

            # should not reach here
            return join.id

        if isinstance(stmt, WhileStmt):
            cond = self.new_block()
            body_entry = self.new_block()
            after = self.new_block()

            self._link_if_not_terminated(cur_id, cond.id, "next")

            self.add_stmt(cond.id, f"while {stmt.condition_text} do")
            self.add_edge(cond.id, body_entry.id, "true")
            self.add_edge(cond.id, after.id, "false")

            loop_ctx = _LoopCtx(break_target=after.id, continue_target=cond.id)
            end_body = self._build_stmt_list(stmt.body.statements, body_entry.id, cond.id, loop_ctx, link_to_exit=False)
            self._link_if_not_terminated(end_body, cond.id, "back")
            return after.id

        if isinstance(stmt, RepeatStmt):
            body_entry = self.new_block()
            cond = self.new_block()
            after = self.new_block()

            self._link_if_not_terminated(cur_id, body_entry.id, "next")

            loop_ctx = _LoopCtx(break_target=after.id, continue_target=cond.id)
            self._build_stmt_list(stmt.body.statements, body_entry.id, cond.id, loop_ctx, link_to_exit=True)

            self.add_stmt(cond.id, f"until {stmt.until_condition_text}")
            self.add_edge(cond.id, after.id, "true")
            self.add_edge(cond.id, body_entry.id, "false")
            return after.id

        # unknown stmt type - keep id progression and visibility
        self.add_stmt(cur_id, f"<unhandled {type(stmt).__name__}>")
        return cur_id


def parse_luau_subset_to_ast(source: str) -> Block:
    """
    Analysis-only helper: parse a minimal Luau subset from source into AST.
    """
    tokens = tokenize(strip_leading_bom(source))
    parser = _AstParser(tokens)
    return parser.parse_block(until_keywords=set())

def rand_var(n=8):
    return ''.join(random.choice(string.ascii_letters) for _ in range(n))

lua_vm_code = r'''
-- =========================================
-- Advanced Lua Toy VM (Structured Edition)
-- array instruction + runtime decode + mapped dispatch
-- =========================================

local DEBUG = true
local STEP  = false

-- =========================
-- opcode 定义（基础值）
-- =========================
local BASE_OP = {
  SET=1, MOVE=2, ADD=3, SUB=4, MUL=5, DIV=6,
  PRINT=7, PUSH=8, POP=9,
  GOTO=10, IF_GOTO=11, CALL=12, RET=13
}

-- =========================
-- 简单编码函数（教学用途）
-- =========================
local function encode(op)
  return (op * 3 + 7) % 256
end

local function decode(op)
  return ((op - 7) * 171) % 256  -- 171 是 3 的逆元 mod 256
end

-- =========================
-- 原始 program（编码状态）
-- 指令结构：{op, a, b, c}
-- =========================
local raw_program = {
  { encode(BASE_OP.SET), 1, 3, 0 },
  { encode(BASE_OP.CALL), 6, 0, 0 },
  { encode(BASE_OP.PRINT), 1, 0, 0 },
  { encode(BASE_OP.GOTO), 9999, 0, 0 },

  { encode(BASE_OP.SET), 2, 10, 0 },
  { encode(BASE_OP.ADD), 1, 1, 2 },
  { encode(BASE_OP.RET), 0, 0, 0 },
}

-- =========================
-- runtime decode program
-- =========================
local program = {}

for i = 1, #raw_program do
  local ins = raw_program[i]
  program[i] = {
    decode(ins[1]), -- opcode
    ins[2], ins[3], ins[4]
  }
end

-- =========================
-- VM 状态
-- =========================
local R, STACK, CALLSTACK = {}, {}, {}
local pc = 1

local function get(i)
  return R[i] or 0
end

local function set(i,v)
  R[i] = v
end

local function push(v)
  STACK[#STACK+1] = v
end

local function pop()
  local v = STACK[#STACK]
  STACK[#STACK] = nil
  return v
end

local function push_ret(v)
  CALLSTACK[#CALLSTACK+1] = v
end

local function pop_ret()
  local v = CALLSTACK[#CALLSTACK]
  CALLSTACK[#CALLSTACK] = nil
  return v
end

-- =========================
-- opcode → handler index 映射
-- =========================
local function map(op)
  return (op * 5 + 3) % 32
end

-- =========================
-- handlers（非连续）
-- =========================
local handlers = {}

handlers[map(BASE_OP.SET)] = function(ins)
  set(ins[2], ins[3])
end

handlers[map(BASE_OP.MOVE)] = function(ins)
  set(ins[2], get(ins[3]))
end

handlers[map(BASE_OP.ADD)] = function(ins)
  set(ins[2], get(ins[3]) + get(ins[4]))
end

handlers[map(BASE_OP.SUB)] = function(ins)
  set(ins[2], get(ins[3]) - get(ins[4]))
end

handlers[map(BASE_OP.MUL)] = function(ins)
  set(ins[2], get(ins[3]) * get(ins[4]))
end

handlers[map(BASE_OP.DIV)] = function(ins)
  set(ins[2], get(ins[3]) / get(ins[4]))
end

handlers[map(BASE_OP.PRINT)] = function(ins)
  print(get(ins[2]))
end

handlers[map(BASE_OP.PUSH)] = function(ins)
  push(get(ins[2]))
end

handlers[map(BASE_OP.POP)] = function(ins)
  set(ins[2], pop())
end

handlers[map(BASE_OP.GOTO)] = function(ins)
  return ins[2]
end

handlers[map(BASE_OP.IF_GOTO)] = function(ins)
  if get(ins[2]) ~= 0 then
    return ins[3]
  end
end

handlers[map(BASE_OP.CALL)] = function(ins)
  push_ret(pc + 1)
  return ins[2]
end

handlers[map(BASE_OP.RET)] = function()
  return pop_ret()
end

-- =========================
-- exec（间接调度）
-- =========================
local function exec(ins)
  local op = ins[1]

  -- 映射层
  local idx = map(op)
  local h = handlers[idx]

  if not h then
    error("Invalid opcode: "..tostring(op))
  end

  return h(ins)
end

-- =========================
-- DEBUG
-- =========================
local function dump()
  local s = {}
  for i=1,5 do
    s[#s+1] = "R"..i.."="..tostring(get(i))
  end
  return table.concat(s," ")
end

-- =========================
-- 主循环
-- =========================
while pc >=1 and pc <= #program do
  local ins = program[pc]

  if DEBUG then
    print("[pc="..pc.."] op="..ins[1].." "..dump())
  end

  if STEP then io.read() end

  local npc = exec(ins)

  if npc then
    pc = npc
  else
    pc = pc + 1
  end
end
'''

def trace_to_lua_table(trace, cfg):
    state_var = rand_var()
    handlers_name = rand_var()

    out = []

    out.append(f"local {state_var} = 1")
    out.append(f"local {handlers_name} = {{}}")

    # 生成每个 state handler
    for i, step in enumerate(trace):
        block = cfg.blocks[step["block"]]
        state_id = i + 1

        out.append(f"{handlers_name}[{state_id}] = function()")

        # 垃圾变量
        junk_var = rand_var()
        out.append(f"    local {junk_var} = {random.randint(1000,9999)}")

        for stmt in block.statements:
            stmt = stmt.strip()

            if stmt.startswith("if ") and step["edge"] in ("true", "false"):
                cond = stmt.replace("if ", "").replace(" then", "")

                if step["edge"] == "true":
                    out.append(f"    if ({cond}) then")
                else:
                    out.append(f"    if not ({cond}) then")

                fake = rand_var()
                out.append(f"        local {fake} = {random.randint(1,500)}")
                out.append("    end")

            else:
                if random.random() < 0.25:
                    junk = rand_var()
                    out.append(f"    local {junk} = {random.randint(10,999)}")

                out.append(f"    {stmt}")

        # 状态跳转
        if i + 1 < len(trace):
            next_state = i + 2
            out.append(f"    {state_var} = {next_state}")
        else:
            out.append(f"    {state_var} = nil")

        out.append("end\n")

    # 主循环
    out.append("while " + state_var + " do")
    out.append(f"    {handlers_name}[{state_var}]()")
    out.append("end")

    return "\n".join(out)

def lua_toy_vm_full() -> str:
    return r'''
-- =========================================
-- Lua Toy VM (Teaching Full Version)
-- 带寄存器 + 栈 + 控制流 + 调用
-- =========================================

local program = {
  -- 初始化
  { op = "SET", dst = 1, imm = 5 },   -- R1 = 5
  { op = "SET", dst = 2, imm = 1 },   -- R2 = 1

  -- loop: R2 *= R1; R1--
  { op = "MUL", dst = 2, a = 2, b = 1 },   -- R2 = R2 * R1
  { op = "SUB", dst = 1, a = 1, imm = 1 }, -- R1 = R1 - 1

  { op = "CMP", a = 1, b = 0 },       -- FLAG = (R1 == 0)
  { op = "IF_GOTO", cond = "NZ", target = 3 }, -- if not zero, loop

  { op = "PRINT", reg = 2 }, -- 输出结果
}

-- =========================
-- VM 状态
-- =========================
local R = {}       -- 寄存器
local STACK = {}   -- 栈
local CALLSTACK = {} -- 调用栈
local FLAG = 0     -- 比较标志

-- =========================
-- 工具函数
-- =========================
local function get(v)
  if type(v) == "number" then
    return R[v] or 0
  else
    return v -- 立即数
  end
end

local function set(i, v)
  R[i] = v
end

local function push(v)
  STACK[#STACK + 1] = v
end

local function pop()
  local v = STACK[#STACK]
  STACK[#STACK] = nil
  return v
end

-- =========================
-- 执行器
-- =========================
local function exec(ins, pc)
  local op = ins.op

  if op == "SET" then
    if ins.src then
      set(ins.dst, get(ins.src))
    else
      set(ins.dst, ins.imm)
    end

  elseif op == "ADD" then
    set(ins.dst, get(ins.a) + get(ins.b or ins.imm))

  elseif op == "SUB" then
    set(ins.dst, get(ins.a) - get(ins.b or ins.imm))

  elseif op == "MUL" then
    set(ins.dst, get(ins.a) * get(ins.b or ins.imm))

  elseif op == "DIV" then
    set(ins.dst, get(ins.a) / get(ins.b or ins.imm))

  elseif op == "CMP" then
    if get(ins.a) == get(ins.b) then
      FLAG = 0
    else
      FLAG = 1
    end

  elseif op == "PRINT" then
    print(get(ins.reg))

  elseif op == "PUSH" then
    push(get(ins.src))

  elseif op == "POP" then
    set(ins.dst, pop())

  elseif op == "GOTO" then
    return ins.target

  elseif op == "IF_GOTO" then
    if ins.cond == "NZ" and FLAG ~= 0 then
      return ins.target
    elseif ins.cond == "Z" and FLAG == 0 then
      return ins.target
    end

  elseif op == "CALL" then
    CALLSTACK[#CALLSTACK + 1] = pc + 1
    return ins.target

  elseif op == "RET" then
    local ret = CALLSTACK[#CALLSTACK]
    CALLSTACK[#CALLSTACK] = nil
    return ret

  else
    error("Unknown opcode: " .. tostring(op))
  end

  return nil
end

-- =========================
-- 主循环
-- =========================
local pc = 1
while pc <= #program do
  local ins = program[pc]
  local new_pc = exec(ins, pc)

  if new_pc then
    pc = new_pc
  else
    pc = pc + 1
  end
end

'''


def lua_toy_vm_multistage_decode_pipeline() -> str:
    return r'''
-- Teaching Toy VM with Multi-Stage Decode Pipeline (5+ stages)
-- Multi-stage decode + IR builder + validation + virtual dispatch + tracing + breakpoints + CFG
-- No obfuscation/encryption/anti-analysis.

local DEBUG = true
local DEBUG_DECODE = true
local DEBUG_CFG = false

-- ------------------------------------------------------------
-- Canonical opcode definitions (final decoded semantics)
-- ------------------------------------------------------------
local OPCODES = {
  NOP     = 0,
  SET     = 1,  -- dst=arg1, mode=arg2 (0 imm, 1 reg), x=arg3 (imm or src-reg)
  ADD     = 2,  -- dst=arg1, a=arg2, b=arg3
  SUB     = 3,
  MUL     = 4,
  DIV     = 5,
  MOV     = 6,  -- dst=arg1, src=arg2
  PRINT   = 7,  -- reg=arg1
  PUSH    = 8,  -- reg=arg1
  POP     = 9,  -- dst=arg1
  GOTO    = 10, -- target=arg1
  IF_GOTO = 11, -- cond_reg=arg1, target=arg2
  CALL    = 12, -- target=arg1
  RET     = 13, -- no args
}

local OPCODE_NAMES = {}
for name, code in pairs(OPCODES) do
  OPCODE_NAMES[code] = name
end

-- ------------------------------------------------------------
-- VM context object (no globals in handlers)
-- ------------------------------------------------------------
local VM = {
  R = {},
  STACK = {},
  CALLSTACK = {},
  pc = 1,
  flags = {},
  trace = {},
  breakpoints = {},
  step_mode = false,

  -- limits used by validation
  max_reg = 32,
}

local function get_reg(vm, i)
  local v = vm.R[i]
  if v == nil then return 0 end
  return v
end

local function set_reg(vm, i, v)
  vm.R[i] = v
end

local function push(vm, v)
  vm.STACK[#vm.STACK + 1] = v
end

local function pop(vm)
  if #vm.STACK == 0 then error("STACK underflow") end
  local v = vm.STACK[#vm.STACK]
  vm.STACK[#vm.STACK] = nil
  return v
end

local function push_ret(vm, addr)
  vm.CALLSTACK[#vm.CALLSTACK + 1] = addr
end

local function pop_ret(vm)
  if #vm.CALLSTACK == 0 then error("CALLSTACK underflow") end
  local addr = vm.CALLSTACK[#vm.CALLSTACK]
  vm.CALLSTACK[#vm.CALLSTACK] = nil
  return addr
end

local function snapshot_regs(vm, max_reg)
  max_reg = max_reg or 8
  local parts = {}
  for i = 1, max_reg do
    parts[#parts + 1] = ("R%d=%s"):format(i, tostring(get_reg(vm, i)))
  end
  return table.concat(parts, " ")
end

local function maybe_pause(vm, msg)
  local bp = vm.breakpoints and vm.breakpoints[vm.pc]
  if bp then
    print("[breakpoint] " .. (msg or ("pc=" .. tostring(vm.pc))))
    print("press Enter to continue...")
    io.read("*l")
  end
end

local function maybe_step(vm, msg)
  if vm.step_mode then
    print("[step] " .. (msg or ("pc=" .. tostring(vm.pc))))
    print("press Enter to continue...")
    io.read("*l")
  end
end

-- ------------------------------------------------------------
-- CFG building helpers
-- ------------------------------------------------------------
local function build_cfg_from_ir(ir_program)
  local nodes = {}
  local edges = {}

  local function add_edge(src, dst, kind)
    edges[#edges + 1] = { src = src, dst = dst, kind = kind }
  end

  local n = #ir_program
  for i = 1, n do nodes[i] = true end

  for i = 1, n do
    local ir = ir_program[i]
    if ir.kind == "JUMP" then
      add_edge(i, ir.target, "jump")
    elseif ir.kind == "CJUMP" then
      add_edge(i, ir.target, "true")
      add_edge(i, i + 1, "false")
    elseif ir.kind == "CALL" then
      add_edge(i, ir.target, "call")
      add_edge(i, i + 1, "next")
    elseif ir.kind == "RET" then
      -- no explicit fallthrough edge
    else
      add_edge(i, i + 1, "next")
    end
  end

  -- DOT format for quick visualization
  local dot = {}
  dot[#dot + 1] = "digraph CFG {"
  dot[#dot + 1] = '  rankdir="LR";'

  for i = 1, n do
    local label = ir_program[i].debug_name or ("pc=" .. i)
    dot[#dot + 1] = ("  n%d [label=%q];"):format(i, label)
  end

  -- allow edges to n+1 (exit) node
  dot[#dot + 1] = ("  n%d [label=%q, shape=doublecircle];"):format(n + 1, "exit")

  for _, e in ipairs(edges) do
    local src = e.src
    local dst = e.dst
    if dst < 1 then dst = n + 1 end
    if dst > n + 1 then dst = n + 1 end
    dot[#dot + 1] = ("  n%d -> n%d [label=%q];"):format(src, dst, e.kind)
  end

  dot[#dot + 1] = "}"
  return { nodes = nodes, edges = edges, dot = table.concat(dot, "\n") }
end

-- ------------------------------------------------------------
-- Demo program (canonical form first), then layer1 encoding
-- Instruction encoding format:
--   IR input (canonical decoded instruction) is represented as:
--     { op, arg1, arg2, arg3 }
--
-- Semantics per opcode:
--   NOP      : no args
--   SET      : dst=arg1, mode=arg2, x=arg3 (imm or src-reg)
--   ADD/SUB/MUL/DIV : dst=arg1, a=arg2, b=arg3
--   MOV      : dst=arg1, src=arg2
--   PRINT    : reg=arg1
--   PUSH     : reg=arg1
--   POP      : dst=arg1
--   GOTO     : target=arg1
--   IF_GOTO  : cond_reg=arg1, target=arg2
--   CALL     : target=arg1
--   RET      : no args
-- ------------------------------------------------------------
local function canonical_program()
  return {
    { OPCODES.SET,     1, 0, 6 },     -- R1 = 6
    { OPCODES.SET,     2, 0, 2 },     -- R2 = 2
    { OPCODES.SET,     5, 0, 0 },     -- R5 = 0 (for IF_GOTO false path)
    { OPCODES.NOP,     0, 0, 0 },     -- NOP
    { OPCODES.CALL,   11, 0, 0 },     -- call func @11
    { OPCODES.PRINT,   2, 0, 0 },     -- print R2
    { OPCODES.PUSH,    2, 0, 0 },     -- push R2
    { OPCODES.POP,     4, 0, 0 },     -- R4 = pop()
    { OPCODES.IF_GOTO, 5,10, 0 },     -- if R5 ~= 0 goto 10 (won't jump)
    { OPCODES.GOTO,   19, 0, 0 },     -- goto final print
    { OPCODES.MOV,     3, 1, 0 },     -- R3 = R1
    { OPCODES.DIV,     3, 3, 2 },     -- R3 = R3 / R2
    { OPCODES.MUL,     2, 2, 3 },     -- R2 = R2 * R3
    { OPCODES.SET,     7, 0, 1 },     -- R7 = 1
    { OPCODES.ADD,     2, 2, 7 },     -- R2 = R2 + R7
    { OPCODES.SET,     6, 0, 1 },     -- R6 = 1
    { OPCODES.SUB,     1, 1, 6 },     -- R1 = R1 - R6
    { OPCODES.RET,     0, 0, 0 },     -- return to caller
    { OPCODES.PRINT,   4, 0, 0 },     -- print R4
  }
end

-- ------------------------------------------------------------
-- Layer1 encoding (teaching-only reversible transforms)
-- We do NOT hide semantics; we only demonstrate staged transformations.
-- ------------------------------------------------------------
local ENC = {
  op_mul = 11,
  op_add = 3,
  a1_off = 100,
  a2_off = 200,
  a3_off = 300,
}

local function encode_layer1_instruction(op, arg1, arg2, arg3)
  local op_enc = op * ENC.op_mul + ENC.op_add
  local a1_enc = arg1 + ENC.a1_off
  local a2_enc = arg2 + ENC.a2_off
  local a3_enc = arg3 + ENC.a3_off
  return { op_enc, a1_enc, a2_enc, a3_enc }
end

local function build_program_layer1()
  local prog = canonical_program()
  local layer1 = {}
  for i = 1, #prog do
    local ins = prog[i]
    layer1[i] = encode_layer1_instruction(ins[1], ins[2], ins[3], ins[4])
  end
  return layer1
end

local function decode_stage1(data_layer1)
  if DEBUG_DECODE then print("[decode_stage1] raw normalize + validate structure") end
  local out = {}
  for i = 1, #data_layer1 do
    local ins = data_layer1[i]
    if type(ins) ~= "table" then error("stage1: instruction must be table at index " .. i) end
    if #ins < 4 then error("stage1: instruction length < 4 at index " .. i) end

    local op_enc, a1_enc, a2_enc, a3_enc = ins[1], ins[2], ins[3], ins[4]
    if type(op_enc) ~= "number" or type(a1_enc) ~= "number" or type(a2_enc) ~= "number" or type(a3_enc) ~= "number" then
      error("stage1: non-number fields at index " .. i)
    end
    if math.abs(op_enc) > 1e9 or math.abs(a1_enc) > 1e9 or math.abs(a2_enc) > 1e9 or math.abs(a3_enc) > 1e9 then
      error("stage1: numeric out of sanity range at index " .. i)
    end

    out[i] = { op_enc = op_enc, a1_enc = a1_enc, a2_enc = a2_enc, a3_enc = a3_enc }
    if DEBUG_DECODE then
      print(("  [%d] L1(op_enc=%d, a1_enc=%d, a2_enc=%d, a3_enc=%d)"):format(i, op_enc, a1_enc, a2_enc, a3_enc))
    end
  end
  return out
end

local function opcode_from_encoded(op_enc)
  local op_mul = ENC.op_mul
  local op_add = ENC.op_add
  local op1 = op_enc - op_add
  if op1 % op_mul ~= 0 then
    error(("stage2/stage3: opcode decode mismatch (op_enc=%s)"):format(tostring(op_enc)))
  end
  return op1 / op_mul
end

local function infer_operand_tags(op, arg1, arg2, arg3)
  local tags = { t1 = "num", t2 = "num", t3 = "num" }
  if op == OPCODES.NOP then
    tags = { t1="unused", t2="unused", t3="unused" }
  elseif op == OPCODES.SET then
    tags.t1 = "reg"; tags.t2 = "mode"; tags.t3 = (arg2 == 1) and "reg" or "imm"
  elseif op == OPCODES.ADD or op == OPCODES.SUB or op == OPCODES.MUL or op == OPCODES.DIV then
    tags.t1 = "reg"; tags.t2 = "reg"; tags.t3 = "reg"
  elseif op == OPCODES.MOV then
    tags.t1 = "reg"; tags.t2 = "reg"; tags.t3 = "unused"
  elseif op == OPCODES.PRINT or op == OPCODES.PUSH or op == OPCODES.POP then
    tags.t1 = "reg"; tags.t2 = "unused"; tags.t3 = "unused"
  elseif op == OPCODES.GOTO or op == OPCODES.CALL then
    tags.t1 = "target"; tags.t2 = "unused"; tags.t3 = "unused"
  elseif op == OPCODES.IF_GOTO then
    tags.t1 = "reg"; tags.t2 = "target"; tags.t3 = "unused"
  elseif op == OPCODES.RET then
    tags = { t1="unused", t2="unused", t3="unused" }
  else
    tags = { t1="unknown", t2="unknown", t3="unknown" }
  end
  return tags
end

local function decode_stage2(data_stage1)
  if DEBUG_DECODE then print("[decode_stage2] transform args (offset removal + type tagging)") end
  local out = {}
  for i = 1, #data_stage1 do
    local ins = data_stage1[i]
    local op_tmp = opcode_from_encoded(ins.op_enc)
    local op_tag = op_tmp + 1000
    local arg1 = ins.a1_enc - ENC.a1_off
    local arg2 = ins.a2_enc - ENC.a2_off
    local arg3 = ins.a3_enc - ENC.a3_off
    local tags = infer_operand_tags(op_tmp, arg1, arg2, arg3)
    out[i] = { op_tag = op_tag, a1 = arg1, a2 = arg2, a3 = arg3, tags = tags }
    if DEBUG_DECODE then
      print(("  [%d] op_tmp=%d => op_tag=%d, args=(%d,%d,%d), tags=(%s,%s,%s)"):format(
        i, op_tmp, op_tag, arg1, arg2, arg3, tags.t1, tags.t2, tags.t3
      ))
    end
  end
  return out
end

local function decode_stage3(data_stage2)
  if DEBUG_DECODE then print("[decode_stage3] normalize opcode (op_tag -> canonical opcode)") end
  local out = {}
  for i = 1, #data_stage2 do
    local ins = data_stage2[i]
    local op = ins.op_tag - 1000
    if OPCODE_NAMES[op] == nil then
      error(("stage3: invalid opcode decoded at index %d: op=%s"):format(i, tostring(op)))
    end
    out[i] = { opcode = op, a1 = ins.a1, a2 = ins.a2, a3 = ins.a3, tags = ins.tags }
    if DEBUG_DECODE then
      print(("  [%d] canonical opcode=%s(%d), args=(%d,%d,%d)"):format(
        i, tostring(OPCODE_NAMES[op]), op, ins.a1, ins.a2, ins.a3
      ))
    end
  end
  return out
end

local function unpermute_args(arg1, arg2, arg3, perm_id)
  if perm_id == 0 then
    return arg1, arg2, arg3
  elseif perm_id == 1 then
    return arg2, arg1, arg3
  elseif perm_id == 2 then
    return arg3, arg1, arg2
  else
    error("unpermute_args: unknown perm_id " .. tostring(perm_id))
  end
end

local function decode_stage4(data_stage3)
  if DEBUG_DECODE then print("[decode_stage4] argument permutation (reversible shuffle)") end
  local out = {}
  for i = 1, #data_stage3 do
    local ins = data_stage3[i]
    local a1, a2, a3 = ins.a1, ins.a2, ins.a3
    local perm_id = i % 3
    local p1, p2, p3
    if perm_id == 0 then
      p1, p2, p3 = a1, a2, a3
    elseif perm_id == 1 then
      p1, p2, p3 = a2, a1, a3
    else
      p1, p2, p3 = a2, a3, a1
    end
    out[i] = { opcode = ins.opcode, a1 = p1, a2 = p2, a3 = p3, perm_id = perm_id, tags = ins.tags }
    if DEBUG_DECODE then
      print(("  [%d] perm_id=%d original=(%d,%d,%d) permuted=(%d,%d,%d)"):format(
        i, perm_id, a1, a2, a3, p1, p2, p3
      ))
    end
  end
  return out
end

local function opcode_group(op)
  if op == OPCODES.ADD or op == OPCODES.SUB or op == OPCODES.MUL or op == OPCODES.DIV then
    return "ALU"
  elseif op == OPCODES.GOTO or op == OPCODES.IF_GOTO then
    return "CONTROL"
  elseif op == OPCODES.CALL or op == OPCODES.RET then
    return "CALL"
  elseif op == OPCODES.PUSH or op == OPCODES.POP then
    return "STACK"
  elseif op == OPCODES.SET or op == OPCODES.MOV then
    return "DATA"
  elseif op == OPCODES.PRINT then
    return "IO"
  elseif op == OPCODES.NOP then
    return "SYS"
  else
    return "UNKNOWN"
  end
end

local function decode_stage5_ir_builder(data_stage4)
  if DEBUG_DECODE then print("[decode_stage5] build IR from permuted args") end
  local out = {}
  for i = 1, #data_stage4 do
    local ins = data_stage4[i]
    local op = ins.opcode
    local ua1, ua2, ua3 = unpermute_args(ins.a1, ins.a2, ins.a3, ins.perm_id)
    local ir = { pc = i, opcode = op, group = opcode_group(op), debug_name = OPCODE_NAMES[op] or "UNKNOWN" }
    if op == OPCODES.NOP then
      ir.kind = "NOP"
    elseif op == OPCODES.SET then
      ir.kind = "SET"; ir.dst = ua1; ir.mode = ua2
      if ir.mode == 1 then ir.src = ua3 else ir.value = ua3 end
    elseif op == OPCODES.MOV then
      ir.kind = "MOV"; ir.dst = ua1; ir.src = ua2
    elseif op == OPCODES.ADD or op == OPCODES.SUB or op == OPCODES.MUL or op == OPCODES.DIV then
      ir.kind = "BINOP"; ir.op = OPCODE_NAMES[op]; ir.dst = ua1; ir.a = ua2; ir.b = ua3
    elseif op == OPCODES.PRINT then
      ir.kind = "PRINT"; ir.reg = ua1
    elseif op == OPCODES.PUSH then
      ir.kind = "PUSH"; ir.reg = ua1
    elseif op == OPCODES.POP then
      ir.kind = "POP"; ir.dst = ua1
    elseif op == OPCODES.GOTO then
      ir.kind = "JUMP"; ir.target = ua1
    elseif op == OPCODES.IF_GOTO then
      ir.kind = "CJUMP"; ir.cond = ua1; ir.target = ua2
    elseif op == OPCODES.CALL then
      ir.kind = "CALL"; ir.target = ua1
    elseif op == OPCODES.RET then
      ir.kind = "RET"
    else
      error(("stage5: unsupported opcode at pc=%d: %s(%d)"):format(i, OPCODE_NAMES[op] or "?", op))
    end
    out[i] = ir
  end
  return out
end

local function validate_ir(vm, ir_program)
  if DEBUG_DECODE then print("[validate_ir] validate registers and jump targets") end
  local n = #ir_program
  local max_reg = vm.max_reg

  local function check_reg(r, where)
    if type(r) ~= "number" or r % 1 ~= 0 then error("IR: reg must be integer at " .. where) end
    if r < 1 or r > max_reg then
      error(("IR: reg out of bounds at %s: R%d (allowed 1..%d)"):format(where, r, max_reg))
    end
  end
  local function check_target(t, where)
    if type(t) ~= "number" or t % 1 ~= 0 then error("IR: target must be integer at " .. where) end
    if t < 1 or t > n + 1 then
      error(("IR: target out of bounds at %s: %s (allowed 1..%d or exit=%d)"):format(where, tostring(t), n, n + 1))
    end
  end

  local out = {}
  for i = 1, n do
    local ir = ir_program[i]
    if ir.opcode == nil or ir.kind == nil then error("IR: missing opcode/kind at pc=" .. tostring(i)) end
    if OPCODE_NAMES[ir.opcode] == nil then
      error(("IR: invalid opcode at pc=%d opcode=%s"):format(i, tostring(ir.opcode)))
    end
    if ir.kind == "SET" then
      check_reg(ir.dst, "SET.dst at pc=" .. i)
      if ir.mode == 1 then check_reg(ir.src, "SET.src at pc=" .. i)
      elseif ir.mode == 0 then
        if type(ir.value) ~= "number" then error("IR: SET imm must be number at pc=" .. i) end
      else
        error("IR: SET.mode must be 0 or 1 at pc=" .. i)
      end
    elseif ir.kind == "MOV" then
      check_reg(ir.dst, "MOV.dst at pc=" .. i); check_reg(ir.src, "MOV.src at pc=" .. i)
    elseif ir.kind == "BINOP" then
      check_reg(ir.dst, "BINOP.dst at pc=" .. i); check_reg(ir.a, "BINOP.a at pc=" .. i); check_reg(ir.b, "BINOP.b at pc=" .. i)
    elseif ir.kind == "PRINT" then
      check_reg(ir.reg, "PRINT.reg at pc=" .. i)
    elseif ir.kind == "PUSH" then
      check_reg(ir.reg, "PUSH.reg at pc=" .. i)
    elseif ir.kind == "POP" then
      check_reg(ir.dst, "POP.dst at pc=" .. i)
    elseif ir.kind == "JUMP" then
      check_target(ir.target, "JUMP.target at pc=" .. i)
    elseif ir.kind == "CJUMP" then
      check_reg(ir.cond, "CJUMP.cond at pc=" .. i); check_target(ir.target, "CJUMP.target at pc=" .. i)
    elseif ir.kind == "CALL" then
      check_target(ir.target, "CALL.target at pc=" .. i)
    end
    out[i] = ir
  end
  return out
end

local group_dispatch = {
  ALU = function(vm, ir)
    if ir.op == "ADD" then
      set_reg(vm, ir.dst, get_reg(vm, ir.a) + get_reg(vm, ir.b))
    elseif ir.op == "SUB" then
      set_reg(vm, ir.dst, get_reg(vm, ir.a) - get_reg(vm, ir.b))
    elseif ir.op == "MUL" then
      set_reg(vm, ir.dst, get_reg(vm, ir.a) * get_reg(vm, ir.b))
    elseif ir.op == "DIV" then
      set_reg(vm, ir.dst, get_reg(vm, ir.a) / get_reg(vm, ir.b))
    else
      error("ALU: unknown op " .. tostring(ir.op))
    end
    return nil
  end,
  DATA = function(vm, ir)
    if ir.kind == "SET" then
      if ir.mode == 1 then set_reg(vm, ir.dst, get_reg(vm, ir.src)) else set_reg(vm, ir.dst, ir.value) end
    elseif ir.kind == "MOV" then
      set_reg(vm, ir.dst, get_reg(vm, ir.src))
    else
      error("DATA: unexpected kind " .. tostring(ir.kind))
    end
    return nil
  end,
  STACK = function(vm, ir)
    if ir.kind == "PUSH" then push(vm, get_reg(vm, ir.reg))
    elseif ir.kind == "POP" then set_reg(vm, ir.dst, pop(vm))
    else error("STACK: unexpected kind " .. tostring(ir.kind)) end
    return nil
  end,
  CONTROL = function(vm, ir)
    if ir.kind == "JUMP" then return ir.target
    elseif ir.kind == "CJUMP" then if get_reg(vm, ir.cond) ~= 0 then return ir.target end; return nil
    else error("CONTROL: unexpected kind " .. tostring(ir.kind)) end
  end,
  CALL = function(vm, ir)
    if ir.kind == "CALL" then push_ret(vm, vm.pc + 1); return ir.target
    elseif ir.kind == "RET" then return pop_ret(vm)
    else error("CALL: unexpected kind " .. tostring(ir.kind)) end
  end,
  IO = function(vm, ir)
    if ir.kind == "PRINT" then print(get_reg(vm, ir.reg)); return nil
    else error("IO: unexpected kind " .. tostring(ir.kind)) end
  end,
  SYS = function(vm, ir)
    if ir.kind ~= "NOP" then error("SYS: unexpected kind " .. tostring(ir.kind)) end
    return nil
  end,
}

local function resolve_handler(vm, ir)
  local group = opcode_group(ir.opcode)
  local handler = group_dispatch[group]
  if handler == nil then error("resolve_handler: missing handler for group=" .. tostring(group)) end
  return handler, group
end

local function exec_ir(vm, ir)
  local handler = resolve_handler(vm, ir)
  return handler(vm, ir)
end

local function run_vm(vm, ir_program)
  vm.trace = {}
  local n = #ir_program
  vm.pc = 1
  while vm.pc >= 1 and vm.pc <= n do
    local ir = ir_program[vm.pc]
    local op_name = OPCODE_NAMES[ir.opcode] or "UNKNOWN"
    local before_regs = snapshot_regs(vm, 8)
    local before_stack = #vm.STACK
    if vm.breakpoints and vm.breakpoints[vm.pc] then
      maybe_pause(vm, ("hit breakpoint at pc=%d (%s)"):format(vm.pc, op_name))
    end
    maybe_step(vm, ("executing pc=%d (%s)"):format(vm.pc, op_name))
    if DEBUG then print(("[exec] pc=%d %s"):format(vm.pc, op_name)) end
    local next_pc = exec_ir(vm, ir)
    local after_regs = snapshot_regs(vm, 8)
    local after_stack = #vm.STACK
    vm.trace[#vm.trace + 1] = {
      pc = vm.pc,
      opcode = ir.opcode,
      opcode_name = op_name,
      kind = ir.kind,
      before = { regs = before_regs, stack_size = before_stack, callstack_size = #vm.CALLSTACK },
      after = { regs = after_regs, stack_size = after_stack, callstack_size = #vm.CALLSTACK },
      edge = next_pc ~= nil and ("jump_to_" .. tostring(next_pc)) or "fallthrough",
    }
    if next_pc ~= nil then vm.pc = next_pc else vm.pc = vm.pc + 1 end
  end
  return vm.trace
end

local function build_and_run()
  local program_layer1_encoded = build_program_layer1()
  local stage1 = decode_stage1(program_layer1_encoded)
  local stage2 = decode_stage2(stage1)
  local stage3 = decode_stage3(stage2)
  local stage4 = decode_stage4(stage3)
  local ir_program_unvalidated = decode_stage5_ir_builder(stage4)
  local ir_program = validate_ir(VM, ir_program_unvalidated)
  local cfg = build_cfg_from_ir(ir_program)
  VM.cfg = cfg
  if DEBUG_CFG then print("[CFG DOT]\n" .. cfg.dot) end
  local trace = run_vm(VM, ir_program)
  if DEBUG then print("[VM] finished. steps=" .. tostring(#trace)) end
end

build_and_run()
'''


def get_teaching_lua_scripts() -> dict[str, str]:
    """
    Unified entry for all teaching/demo Lua scripts in this module.
    This helps ensure every built-in script template is explicitly reachable/used.
    """
    return {
        "toy_interpreter": lua_toy_interpreter_source(),
        "toy_vm_full": lua_toy_vm_full(),
        "toy_vm_multistage_decode_pipeline": lua_toy_vm_multistage_decode_pipeline(),
    }


def build_cfg_from_ast(ast: Block) -> ControlFlowGraph:
    """
    Build Control Flow Graph (basic blocks + edges) from the minimal AST.
    """
    builder = _CfgBuilder()
    return builder.build_from_block(ast)


def build_cfg_from_source(source: str) -> ControlFlowGraph:
    """
    Convenience: parse minimal AST from source, then build CFG.
    """
    return build_cfg_from_ast(parse_luau_subset_to_ast(source))


def build_ir_from_cfg(cfg: ControlFlowGraph) -> ControlFlowIR:
    """
    Convert CFG into a simple structured IR with explicit block terminators:
    - IRJump(target)
    - IRBranch(condition_text, true_target, false_target)
    - "return"/"halt"/None for terminal blocks
    """
    outgoing: dict[int, list[CfgEdge]] = {}
    for edge in cfg.edges:
        outgoing.setdefault(edge.src, []).append(edge)

    ir_blocks: dict[int, IRBlock] = {}
    for block_id, block in cfg.blocks.items():
        statements = list(block.statements)
        edges = outgoing.get(block_id, [])

        true_edge = next((e for e in edges if e.kind == "true"), None)
        false_edge = next((e for e in edges if e.kind == "false"), None)
        next_like = next((e for e in edges if e.kind in ("next", "back", "break")), None)

        terminator: IRJump | IRBranch | str | None
        if true_edge is not None and false_edge is not None:
            cond_text = ""
            for stmt in statements:
                s = stmt.strip()
                if s.startswith("if "):
                    cond_text = s[3:].replace(" then", "").strip()
                    break
                if s.startswith("while "):
                    cond_text = s[6:].replace(" do", "").strip()
                    break
                if s.startswith("until "):
                    cond_text = s[6:].strip()
                    break
            if not cond_text:
                cond_text = "<cond>"
            terminator = IRBranch(
                condition_text=cond_text,
                true_target=true_edge.dst,
                false_target=false_edge.dst,
            )
        elif block.terminated:
            if any(stmt.strip().startswith("return") for stmt in statements):
                terminator = "return"
            else:
                terminator = "halt"
        elif next_like is not None:
            terminator = IRJump(target=next_like.dst)
        elif block_id == cfg.exit_id:
            terminator = "exit"
        else:
            terminator = None

        ir_blocks[block_id] = IRBlock(
            id=block_id,
            statements=statements,
            terminator=terminator,
        )

    return ControlFlowIR(entry_id=cfg.entry_id, exit_id=cfg.exit_id, blocks=ir_blocks)


def build_ir_from_source(source: str) -> ControlFlowIR:
    """
    Convenience: source -> AST -> CFG -> IR.
    """
    return build_ir_from_cfg(build_cfg_from_source(source))


def run_ir_interpreter(
    ir: ControlFlowIR,
    *,
    env: dict[str, Any] | None = None,
    eval_statement: callable | None = None,
    eval_condition: callable | None = None,
    max_steps: int = 10_000,
) -> dict[str, Any]:
    """
    Minimal IR interpreter for validating CFG/IR conversion semantics.

    Execution model:
    - Dispatch loop over IR blocks (pc = block id).
    - Execute block statements in order.
    - Resolve block terminator to choose next block.
    - Supports branch / jump / return / exit.

    Hooks:
    - eval_statement(stmt:str, env:dict) -> Any
      Optional callback to execute/interpret statement text.
      Return value is ignored except for custom debugging.
    - eval_condition(cond_text:str, env:dict) -> bool
      Optional callback for branch conditions.
      If absent, fallback uses env.get(cond_text, False).

    Return:
      {
        "entry": ...,
        "exit": ...,
        "trace": [{"block": id, "statements": [...], "terminator": ...}, ...],
        "halt_reason": "return|exit|fallthrough|max_steps",
        "return_value": ...,
        "env": env
      }
    """
    state = {} if env is None else dict(env)
    trace: list[dict[str, Any]] = []
    pc = ir.entry_id
    steps = 0

    while True:
        steps += 1
        if steps > max_steps:
            return {
                "entry": ir.entry_id,
                "exit": ir.exit_id,
                "trace": trace,
                "halt_reason": "max_steps",
                "return_value": None,
                "env": state,
            }

        block = ir.blocks.get(pc)
        if block is None:
            return {
                "entry": ir.entry_id,
                "exit": ir.exit_id,
                "trace": trace,
                "halt_reason": "fallthrough",
                "return_value": None,
                "env": state,
            }

        # Execute statements.
        for stmt in block.statements:
            if eval_statement is not None:
                eval_statement(stmt, state)

        t = block.terminator
        rec: dict[str, Any] = {"block": block.id, "statements": list(block.statements)}

        if isinstance(t, IRBranch):
            cond_value = bool(eval_condition(t.condition_text, state)) if eval_condition is not None else bool(
                state.get(t.condition_text, False)
            )
            rec["terminator"] = {
                "kind": "branch",
                "condition": t.condition_text,
                "condition_value": cond_value,
                "true_target": t.true_target,
                "false_target": t.false_target,
            }
            trace.append(rec)
            pc = t.true_target if cond_value else t.false_target
            continue

        if isinstance(t, IRJump):
            rec["terminator"] = {"kind": "jump", "target": t.target}
            trace.append(rec)
            pc = t.target
            if pc == ir.exit_id:
                trace.append({"block": ir.exit_id, "statements": list(ir.blocks.get(ir.exit_id, IRBlock(ir.exit_id, [])).statements), "terminator": "exit"})
                return {
                    "entry": ir.entry_id,
                    "exit": ir.exit_id,
                    "trace": trace,
                    "halt_reason": "exit",
                    "return_value": None,
                    "env": state,
                }
            continue

        if t == "return":
            return_value = state.get("__return__", None)
            # Best-effort parse for "return <expr>" into env lookup by expr text.
            for stmt in reversed(block.statements):
                s = stmt.strip()
                if s.startswith("return"):
                    expr = s[len("return") :].strip()
                    if expr:
                        return_value = state.get(expr, return_value)
                    break
            rec["terminator"] = "return"
            trace.append(rec)
            return {
                "entry": ir.entry_id,
                "exit": ir.exit_id,
                "trace": trace,
                "halt_reason": "return",
                "return_value": return_value,
                "env": state,
            }

        if t == "exit":
            rec["terminator"] = "exit"
            trace.append(rec)
            return {
                "entry": ir.entry_id,
                "exit": ir.exit_id,
                "trace": trace,
                "halt_reason": "exit",
                "return_value": None,
                "env": state,
            }

        # None / halt / unknown: stop as fallthrough.
        rec["terminator"] = t
        trace.append(rec)
        return {
            "entry": ir.entry_id,
            "exit": ir.exit_id,
            "trace": trace,
            "halt_reason": "fallthrough",
            "return_value": None,
            "env": state,
        }


def ir_blocks_statements_to_lua_snippets(ir: ControlFlowIR) -> str:
    """
    Render IRBlock statements to Lua code snippets only.

    Notes:
    - No jump/branch/dispatch loop is generated.
    - Terminators are intentionally ignored.
    - Output is grouped by block as comments + raw statement lines.
    """
    out: list[str] = []
    for block_id in sorted(ir.blocks.keys()):
        block = ir.blocks[block_id]
        out.append(f"-- block_{block_id}")
        if not block.statements:
            out.append("-- (empty)")
        else:
            for stmt in block.statements:
                text = stmt.strip()
                if text:
                    out.append(text)
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def ir_terminator_descriptions(ir: "ControlFlowIR") -> dict[int, dict[str, Any]]:
    """
    Convert each IRBlock terminator into simple descriptive metadata.

    Output examples:
    - {"type": "jump", "next": 2}
    - {"type": "branch", "true_branch": 3, "false_branch": 4, "condition": "..."}
    - {"type": "return"}
    - {"type": "exit"}
    - {"type": "halt"}
    """

    out: dict[int, dict[str, Any]] = {}

    for block_id, block in ir.blocks.items():
        t = block.terminator

        # 默认结构
        desc: dict[str, Any] = {}

        if isinstance(t, IRJump):
            desc = {
                "type": "jump",
                "next": t.target,
            }

        elif isinstance(t, IRBranch):
            desc = {
                "type": "branch",
                "true_branch": t.true_target,
                "false_branch": t.false_target,
                "condition": getattr(t, "condition_text", None),
            }

        elif t == "return":
            desc = {"type": "return"}

        elif t == "exit":
            desc = {"type": "exit"}

        elif t == "halt":
            desc = {"type": "halt"}

        elif t is None:
            desc = {"type": "none"}

        else:
            # fallback：未知类型（方便调试）
            desc = {
                "type": "unknown",
                "repr": repr(t),
            }

        out[block_id] = desc

    return out

def simulate_cfg(
    cfg: ControlFlowGraph,
    *,
    condition_eval: callable | None = None,
    max_steps: int = 10_000,
) -> dict[str, Any]:
    """
    Simulate (execute) a CFG *for debugging/validation* and return a trace.

    This does NOT execute Lua statements; it only follows control-flow edges and records
    which blocks/statements would be visited.

    - condition_eval: optional callback (condition_text:str, block_id:int) -> bool
      Used when a block has "true"/"false" outgoing edges. The condition_text is derived
      from the first condition-like statement in the block (prefix "if "/"while "/"until ").
      If not provided, a missing condition evaluation raises.
    - max_steps: guard against infinite loops during validation.
    """

    # index outgoing edges by src
    outgoing: dict[int, list[CfgEdge]] = {}
    for e in cfg.edges:
        outgoing.setdefault(e.src, []).append(e)

    def _extract_condition_text(block: BasicBlock) -> str | None:
        for s in block.statements:
            s2 = s.strip()
            if s2.startswith("if "):
                # "if <cond> then"
                core = s2[3:].strip()
                if core.endswith(" then"):
                    core = core[:-5].strip()
                return core
            if s2.startswith("while "):
                # "while <cond> do"
                core = s2[6:].strip()
                if core.endswith(" do"):
                    core = core[:-3].strip()
                return core
            if s2.startswith("until "):
                return s2[6:].strip()
        return None

    pc = cfg.entry_id
    trace_steps: list[dict[str, Any]] = []
    visited = 0

    while True:
        visited += 1
        if visited > max_steps:
            raise RuntimeError(f"simulate_cfg exceeded max_steps={max_steps} (possible infinite loop)")
        block = cfg.blocks.get(pc)
        if block is None:
            raise KeyError(f"CFG simulation jumped to missing block id={pc}")

        step: dict[str, Any] = {
            "pc": pc,
            "statements": list(block.statements),
        }

        if block.terminated:
            step["halt"] = True
            trace_steps.append(step)
            break

        outs = outgoing.get(pc, [])
        if not outs:
            # fall off the graph => treat as exiting to cfg.exit_id if present
            step["edge"] = None
            step["next_pc"] = cfg.exit_id
            trace_steps.append(step)
            pc = cfg.exit_id
            continue

        # prioritize edge types
        true_edge = next((e for e in outs if e.kind == "true"), None)
        false_edge = next((e for e in outs if e.kind == "false"), None)
        next_edge = next((e for e in outs if e.kind == "next"), None)
        back_edge = next((e for e in outs if e.kind == "back"), None)
        break_edge = next((e for e in outs if e.kind == "break"), None)

        chosen: CfgEdge | None = None
        if true_edge is not None or false_edge is not None:
            if true_edge is None or false_edge is None:
                raise ValueError(f"Block {pc} has incomplete true/false edges for a condition")
            cond_text = _extract_condition_text(block)
            if cond_text is None:
                raise ValueError(f"Block {pc} has true/false edges but no recognizable condition statement")
            if condition_eval is None:
                raise ValueError(f"Block {pc} needs condition_eval for condition '{cond_text}'")
            result = bool(condition_eval(cond_text, pc))
            step["condition"] = cond_text
            step["condition_result"] = result
            chosen = true_edge if result else false_edge
        elif next_edge is not None:
            chosen = next_edge
        elif back_edge is not None:
            chosen = back_edge
        elif break_edge is not None:
            chosen = break_edge
        else:
            # deterministic fallback: pick first edge
            chosen = outs[0]

        step["edge"] = {"src": chosen.src, "dst": chosen.dst, "kind": chosen.kind}
        step["next_pc"] = chosen.dst
        trace_steps.append(step)
        pc = chosen.dst

        if pc == cfg.exit_id:
            # record final arrival at exit (optional)
            exit_block = cfg.blocks.get(pc)
            trace_steps.append({"pc": pc, "statements": list(exit_block.statements) if exit_block else [], "exit": True})
            break

    return {
        "entry": cfg.entry_id,
        "exit": cfg.exit_id,
        "steps": trace_steps,
    }


def run_cfg(cfg: ControlFlowGraph, env: dict[str, bool], *, max_steps: int = 10_000) -> list[dict[str, Any]]:
    """
    Debug/validation CFG runner (Python-side).

    - Drives execution using `pc` (basic block id).
    - Follows `edges(kind)` to choose the next `pc`.
    - Condition resolution: `env` maps condition string -> bool. Missing => False.

    Returns trace entries like:
      {"block": <id>, "statements": [...], "edge": "<kind>"}
    """

    outgoing: dict[int, list[CfgEdge]] = {}
    for e in cfg.edges:
        outgoing.setdefault(e.src, []).append(e)

    def _extract_condition_text(statements: list[str]) -> str | None:
        for s in statements:
            s2 = s.strip()
            if s2.startswith("if "):
                core = s2[3:].strip()
                if core.endswith(" then"):
                    core = core[:-5].strip()
                return core
            if s2.startswith("while "):
                core = s2[6:].strip()
                if core.endswith(" do"):
                    core = core[:-3].strip()
                return core
            if s2.startswith("until "):
                return s2[6:].strip()
        return None

    pc = cfg.entry_id
    trace: list[dict[str, Any]] = []
    steps = 0

    while True:
        steps += 1
        if steps > max_steps:
            raise RuntimeError(f"run_cfg exceeded max_steps={max_steps} (possible infinite loop)")

        block = cfg.blocks.get(pc)
        if block is None:
            raise KeyError(f"run_cfg jumped to missing block id={pc}")

        outs = outgoing.get(pc, [])

        # If block is terminal, record and stop.
        if block.terminated or any(s.strip().startswith("return") for s in block.statements):
            trace.append({"block": pc, "statements": list(block.statements), "edge": "return"})
            return trace

        # Choose edge.
        true_edge = next((e for e in outs if e.kind == "true"), None)
        false_edge = next((e for e in outs if e.kind == "false"), None)

        chosen: CfgEdge | None = None
        if true_edge is not None or false_edge is not None:
            if true_edge is None or false_edge is None:
                # malformed condition split; fall back deterministically
                chosen = outs[0] if outs else None
            else:
                cond_text = _extract_condition_text(block.statements) or ""
                cond_value = bool(env.get(cond_text, False))
                chosen = true_edge if cond_value else false_edge
        else:
            # prefer next, then back, then break, then first
            chosen = next((e for e in outs if e.kind == "next"), None) or next(
                (e for e in outs if e.kind == "back"),
                None,
            ) or next((e for e in outs if e.kind == "break"), None) or (outs[0] if outs else None)

        if chosen is None:
            # no outgoing edges => exit
            trace.append({"block": pc, "statements": list(block.statements), "edge": "exit"})
            return trace

        trace.append({"block": pc, "statements": list(block.statements), "edge": chosen.kind})
        pc = chosen.dst

        if pc == cfg.exit_id:
            # record reaching exit and stop
            exit_block = cfg.blocks.get(pc)
            trace.append({"block": pc, "statements": list(exit_block.statements) if exit_block else [], "edge": "exit"})
            return trace


def lua_toy_interpreter_source() -> str:
    return (
        "-- Teaching-oriented toy interpreter (enhanced)\n"
        "\n"
        "local program = {\n"
        "  { op = 'MOVE', dst = 1, imm = 5 },     -- R1 = 5\n"
        "  { op = 'MOVE', dst = 2, imm = 10 },    -- R2 = 10\n"
        "  { op = 'ADD',  dst = 3, a = 1, b = 2 }, -- R3 = 15\n"
        "  { op = 'SUB',  dst = 4, a = 3, b = 1 }, -- R4 = 10\n"
        "  { op = 'PRINT', reg = 4 },\n"
        "\n"
        "  -- 条件跳转示例\n"
        "  { op = 'MOVE', dst = 5, imm = 1 },\n"
        "  { op = 'JMP_IF', cond = 5, target = 10 },\n"
        "  { op = 'PRINT', reg = 1 }, -- 不会执行\n"
        "  { op = 'JMP', target = 11 },\n"
        "  { op = 'PRINT', reg = 2 }, -- 会执行\n"
        "}\n"
        "\n"
        "local R = {}\n"
        "\n"
        "local function get_reg(i)\n"
        "  local v = R[i]\n"
        "  if v == nil then return 0 end\n"
        "  return v\n"
        "end\n"
        "\n"
        "local function dump_registers()\n"
        "  local t = {}\n"
        "  for k,v in pairs(R) do\n"
        "    table.insert(t, 'R'..k..'='..tostring(v))\n"
        "  end\n"
        "  print('[REG]', table.concat(t, ', '))\n"
        "end\n"
        "\n"
        "local function exec(ins)\n"
        "  local op = ins.op\n"
        "\n"
        "  if op == 'MOVE' then\n"
        "    if ins.src ~= nil then\n"
        "      R[ins.dst] = get_reg(ins.src)\n"
        "    else\n"
        "      R[ins.dst] = ins.imm\n"
        "    end\n"
        "    return\n"
        "  end\n"
        "\n"
        "  if op == 'ADD' then\n"
        "    R[ins.dst] = get_reg(ins.a) + get_reg(ins.b)\n"
        "    return\n"
        "  end\n"
        "\n"
        "  if op == 'SUB' then\n"
        "    R[ins.dst] = get_reg(ins.a) - get_reg(ins.b)\n"
        "    return\n"
        "  end\n"
        "\n"
        "  if op == 'MUL' then\n"
        "    R[ins.dst] = get_reg(ins.a) * get_reg(ins.b)\n"
        "    return\n"
        "  end\n"
        "\n"
        "  if op == 'PRINT' then\n"
        "    print(get_reg(ins.reg))\n"
        "    return\n"
        "  end\n"
        "\n"
        "  error('unknown opcode: ' .. tostring(op))\n"
        "end\n"
        "\n"
        "-- Main loop\n"
        "local pc = 1\n"
        "while pc <= #program do\n"
        "  local ins = program[pc]\n"
        "\n"
        "  print('[EXEC]', 'pc=', pc, 'op=', ins.op)\n"
        "  exec(ins)\n"
        "  dump_registers()\n"
        "\n"
        "  if ins.op == 'JMP' then\n"
        "    pc = ins.target\n"
        "  elseif ins.op == 'JMP_IF' then\n"
        "    if get_reg(ins.cond) ~= 0 then\n"
        "      pc = ins.target\n"
        "    else\n"
        "      pc = pc + 1\n"
        "    end\n"
        "  else\n"
        "    pc = pc + 1\n"
        "  end\n"
        "end\n"
    )


# ===== 冗余 Block 生成器和结构实验系统 =====


@dataclass
class RedundantBlockConfig:
    """冗余 Block 配置"""
    enabled: bool = False
    min_blocks: int = 1
    max_blocks: int = 5
    block_types: list[str] = None  # 可选的 block 类型过滤
    inject_probability: float = 0.3  # 注入概率
    semantic_preserving: bool = True  # 保持语义

    def __post_init__(self):
        if self.block_types is None:
            self.block_types = ["redundant", "decoy", "skip"]


class RedundantBlockGenerator:
    """
    冗余 Block 生成器

    生成不会影响程序最终结果的额外代码块，用于增加代码结构复杂度。
    这些块包括：
    - 永远不会被执行的块
    - 总是被跳过的块
    - 语义上无效但结构上有效的块
    """

    def __init__(self, rng: random.Random, config: RedundantBlockConfig | None = None):
        self.rng = rng
        self.config = config if config else RedundantBlockConfig()
        self.generated_count = 0
        self.used_identifiers: set[str] = set()
        self._id_counter = [0]

    def _gen_id(self) -> int:
        self._id_counter[0] += 1
        return self._id_counter[0]

    def _random_identifier(self, prefix: str = "_r") -> str:
        """生成随机标识符"""
        chars = string.ascii_lowercase + string.digits
        for _ in range(10):
            name = prefix + "_" + "".join(self.rng.choice(chars) for _ in range(6))
            if name not in self.used_identifiers:
                self.used_identifiers.add(name)
                return name
        return f"{prefix}_{self._gen_id()}"

    def generate_redundant_block(self) -> CodeBlock:
        """生成一个冗余 block"""
        self.generated_count += 1

        block_type = self.rng.choice(self.config.block_types)
        content = self._generate_content_for_type(block_type)

        block = CodeBlock(
            block_id=-1 - self.generated_count,  # 使用负数或特殊ID表示冗余
            content=content,
            block_type="redundant",
            next_id=None,
            branches={},
            auxiliary_paths=[],
            dependencies=[],
            metadata={
                "is_redundant": True,
                "redundant_type": block_type,
                "never_executed": block_type in ["redundant", "decoy"],
                "always_skipped": block_type == "skip"
            }
        )
        return block

    def _generate_content_for_type(self, block_type: str) -> str:
        """根据类型生成内容"""
        generators = {
            "redundant": self._gen_dead_code_content,
            "decoy": self._gen_decoy_content,
            "skip": self._gen_skip_content,
        }
        gen = generators.get(block_type, self._gen_dead_code_content)
        return gen()

    def _gen_dead_code_content(self) -> str:
        """生成死代码内容"""
        var_name = self._random_identifier("_d")
        patterns = [
            f"local {var_name} = false\nif {var_name} then\n    error('unreachable')\nend",
            f"if false then\n    local _unused = 0\nend",
            f"do\n    local {var_name} = nil\n    if {var_name} then\n        {var_name} = 1\n    end\nend",
            f"repeat\n    break\nuntil false",
            f"while false do\n    break\nend",
        ]
        return self.rng.choice(patterns)

    def _gen_decoy_content(self) -> str:
        """生成诱饵块内容"""
        var_a = self._random_identifier("_x")
        var_b = self._random_identifier("_y")
        patterns = [
            f"local {var_a}, {var_b} = 0, 0\nlocal _temp = {var_a}\n{var_a} = {var_b}\n{var_b} = _temp",
            f"local {var_a} = 1\n{var_a} = {var_a}\n{var_a} = {var_a}",
            f"local {var_a} = nil\n{var_a} = {var_a}",
            f"local {var_a} = {{}}\n{var_a} = {var_a}\nsetmetatable({var_a}, nil)",
        ]
        return self.rng.choice(patterns)

    def _gen_skip_content(self) -> str:
        """生成跳过块内容"""
        patterns = [
            "do end",
            "(function() end)()",
            "pcall(function() end)",
            "select('#', nil)",
            "next({})",
            "setmetatable({}, {})",
        ]
        count = self.rng.randint(1, 3)
        return "\n".join(self.rng.choice(patterns) for _ in range(count))

    def inject_redundant_blocks(
        self,
        program: BlockProgram,
        count: int | None = None
    ) -> list[CodeBlock]:
        """
        向程序注入冗余 block

        Args:
            program: 目标程序
            count: 要注入的数量，None 表示使用配置中的随机值

        Returns:
            注入的冗余 block 列表
        """
        if not self.config.enabled:
            return []

        if count is None:
            count = self.rng.randint(self.config.min_blocks, self.config.max_blocks)

        if self.rng.random() > self.config.inject_probability:
            return []

        injected_blocks = []
        for _ in range(count):
            if self.rng.random() > self.config.inject_probability:
                break
            redundant = self.generate_redundant_block()
            injected_blocks.append(redundant)
            program.blocks.append(redundant)
            program.block_map[redundant.block_id] = redundant

        return injected_blocks

    def get_statistics(self) -> dict:
        """获取生成统计"""
        return {
            "generated_count": self.generated_count,
            "config": {
                "enabled": self.config.enabled,
                "min_blocks": self.config.min_blocks,
                "max_blocks": self.config.max_blocks,
                "inject_probability": self.config.inject_probability,
            }
        }


class StructuralExperimentManager:
    """
    结构实验管理器

    协调多种结构实验技术，用于测试代码结构复杂度对分析工具的影响。
    """

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.redundant_gen = RedundantBlockGenerator(rng)
        self.aux_gen = AuxiliaryPathGenerator(rng)
        self.experiments_applied: list[dict] = []

    def apply_structure_complexity(
        self,
        program: BlockProgram,
        complexity_level: str = "medium"
    ) -> dict:
        """
        应用结构复杂度增强

        Args:
            program: 目标程序
            complexity_level: 复杂度级别 ("low", "medium", "high")

        Returns:
            应用结果统计
        """
        stats = {
            "complexity_level": complexity_level,
            "redundant_blocks_added": 0,
            "auxiliary_paths_added": 0,
            "branch_complexity_increased": False,
        }

        level_config = {
            "low": {"redundant_prob": 0.2, "aux_prob": 0.1},
            "medium": {"redundant_prob": 0.4, "aux_prob": 0.3},
            "high": {"redundant_prob": 0.6, "aux_prob": 0.5},
        }

        config = level_config.get(complexity_level, level_config["medium"])

        # 添加冗余 block
        if self.rng.random() < config["redundant_prob"]:
            self.redundant_gen.config.enabled = True
            self.redundant_gen.config.inject_probability = config["redundant_prob"]
            injected = self.redundant_gen.inject_redundant_blocks(program, count=2)
            stats["redundant_blocks_added"] = len(injected)

        # 添加辅助路径
        if self.rng.random() < config["aux_prob"]:
            for block in program.blocks:
                if block.block_type != BlockTypeLegacy.FUNCTION_DEF.value:
                    if self.rng.random() < 0.3:
                        self.aux_gen.add_auxiliary_paths_to_block(
                            block, block.next_id, max_paths=1
                        )
                        stats["auxiliary_paths_added"] += len(block.auxiliary_paths)

        # 增加分支复杂度
        if complexity_level in ("medium", "high") and self.rng.random() < 0.3:
            self._add_decoy_branches(program)
            stats["branch_complexity_increased"] = True

        self.experiments_applied.append(stats)
        return stats

    def _add_decoy_branches(self, program: BlockProgram) -> None:
        """添加诱饵分支"""
        for block in program.blocks:
            if not block.has_branches() and block.next_id is not None:
                if self.rng.random() < 0.2:
                    decoy_target = self.rng.choice(program.execution_order) if program.execution_order else None
                    if decoy_target and decoy_target != block.block_id:
                        block.branches["decoy"] = decoy_target

    def add_skip_target_block(self, program: BlockProgram) -> CodeBlock | None:
        """
        添加跳转到目标块

        创建一块总是被跳过的代码，增加 CFG 的复杂性。
        """
        if not program.execution_order:
            return None

        var_name = "_skip_" + "".join(self.rng.choice(string.ascii_lowercase) for _ in range(4))

        content = f"local {var_name} = true\nif {var_name} then\n    {var_name} = false\nend"

        skip_block = CodeBlock(
            block_id=-(1000 + self._gen_skip_id()),
            content=content,
            block_type="skip_target",
            next_id=None,
            metadata={"is_skip_target": True, "always_skipped": True}
        )

        program.blocks.append(skip_block)
        program.block_map[skip_block.block_id] = skip_block

        return skip_block

    def _gen_skip_id(self) -> int:
        if not hasattr(self, "_skip_id_counter"):
            self._skip_id_counter = 0
        self._skip_id_counter += 1
        return self._skip_id_counter

    def generate_fake_loop(self, program: BlockProgram) -> CodeBlock | None:
        """
        生成虚假循环块

        创建看起来像循环但永远不会真正循环的代码结构。
        """
        if not program.execution_order:
            return None

        loop_var = "_loop_" + "".join(self.rng.choice(string.ascii_lowercase) for _ in range(4))

        patterns = [
            f"local {loop_var} = 0\nwhile false do\n    {loop_var} = {loop_var} + 1\nend",
            f"for _i = 1, 0 do\n    -- never runs\nend",
            f"repeat\n    break\nuntil true",
            f"while true do\n    break\nend",
        ]

        content = self.rng.choice(patterns)

        loop_block = CodeBlock(
            block_id=-(2000 + self._gen_skip_id()),
            content=content,
            block_type="dummy_loop",
            next_id=None,
            metadata={"is_dummy_loop": True, "never_iterates": True}
        )

        program.blocks.append(loop_block)
        program.block_map[loop_block.block_id] = loop_block

        return loop_block

    def generate_nested_trap(self, program: BlockProgram) -> list[CodeBlock]:
        """
        生成嵌套陷阱

        创建多层嵌套但总是跳出的代码结构，增加 AST 深度。
        """
        depth = self.rng.randint(2, 4)
        blocks = []
        current_id = -(3000 + self._gen_skip_id())

        outer_var = "_trap_" + "".join(self.rng.choice(string.ascii_lowercase) for _ in range(4))

        for i in range(depth):
            content = f"do\n    local {outer_var}_{i} = false\n    if {outer_var}_{i} then\n        error('trap')\n    end\nend"

            block = CodeBlock(
                block_id=current_id - i,
                content=content,
                block_type="nested_trap",
                next_id=None,
                metadata={"nest_depth": i + 1, "is_trap": True}
            )
            blocks.append(block)

        for block in blocks:
            program.blocks.append(block)
            program.block_map[block.block_id] = block

        return blocks

    def inject_semantic_noop(self, program: BlockProgram) -> None:
        """
        注入语义无操作

        添加不影响程序结果的代码，如变量自赋值、无效计算等。
        """
        for block in program.blocks:
            if self.rng.random() < 0.15:
                noop_content = self._generate_semantic_noop()
                block.content += "\n" + noop_content

    def _generate_semantic_noop(self) -> str:
        """生成语义无操作代码"""
        patterns = [
            "local _x = 0\n_x = _x",
            "local _y = nil\n_y = _y",
            "local _z = {}\n_z = _z",
            "local _a = 1 + 0",
            "local _b = 'a' .. ''",
            "pcall(function() end)",
            "(function() end)()",
        ]
        return self.rng.choice(patterns)

    def get_experiment_summary(self) -> dict:
        """获取实验总结"""
        total_redundant = sum(e.get("redundant_blocks_added", 0) for e in self.experiments_applied)
        total_aux = sum(e.get("auxiliary_paths_added", 0) for e in self.experiments_applied)

        return {
            "total_experiments": len(self.experiments_applied),
            "total_redundant_blocks": total_redundant,
            "total_auxiliary_paths": total_aux,
            "branch_complexity_increases": sum(
                1 for e in self.experiments_applied if e.get("branch_complexity_increased")
            ),
            "experiments": self.experiments_applied
        }


# ===== BlockProgram 便捷方法 =====


def add_structural_complexity(
    program: BlockProgram,
    rng: random.Random,
    level: str = "medium"
) -> dict:
    """
    便捷函数：为程序添加结构复杂度

    Args:
        program: 目标程序
        rng: 随机数生成器
        level: 复杂度级别 ("low", "medium", "high")

    Returns:
        应用结果统计
    """
    manager = StructuralExperimentManager(rng)
    return manager.apply_structure_complexity(program, level)


def inject_redundant_blocks(
    program: BlockProgram,
    rng: random.Random,
    count: int = 2,
    enabled: bool = True
) -> list[CodeBlock]:
    """
    便捷函数：注入冗余 block

    Args:
        program: 目标程序
        rng: 随机数生成器
        count: 要注入的数量
        enabled: 是否启用

    Returns:
        注入的 block 列表
    """
    config = RedundantBlockConfig(enabled=enabled, max_blocks=count)
    gen = RedundantBlockGenerator(rng, config)
    return gen.inject_redundant_blocks(program, count=count)


# ===== 执行路径变化系统 =====


class ExecutionVariationType(Enum):
    """执行路径变化类型"""
    STATE_WRAPPER = "state_wrapper"       # 状态包装
    FLAG_GATE = "flag_gate"               # 标志门控
    COUNTER_SKIP = "counter_skip"         # 计数器跳过
    LOOKUP_TABLE = "lookup_table"          # 查找表
    XOR_TRANSFORM = "xor_transform"       # 异或变换
    OFFSET_INDIRECT = "offset_indirect"   # 偏移间接


@dataclass
class ExecutionPathConfig:
    """执行路径配置"""
    enabled: bool = False
    variation_types: list[ExecutionVariationType] = None
    state_variable_prefix: str = "_st"
    enable_state_wrappers: bool = True
    enable_lookup_redirect: bool = True
    enable_counter_variation: bool = True
    preserve_semantics: bool = True
    variation_probability: float = 0.3


class BlockStateManager:
    """
    Block 状态管理器

    为每个 block 管理执行状态变量，支持：
    - 执行前后状态检查
    - 标志位控制
    - 计数器追踪
    """

    def __init__(self, rng: random.Random | None = None, prefix: str = "_st"):
        self.rng = rng
        self.prefix = prefix
        self.state_variables: dict[int, dict] = {}  # block_id -> state_info
        self._id_counter = [0]

    def _gen_id(self) -> int:
        self._id_counter[0] += 1
        return self._id_counter[0]

    def create_state_variable(self, block_id: int) -> str:
        """为 block 创建状态变量名"""
        var_name = f"{self.prefix}_{block_id}"
        self.state_variables[block_id] = {
            "name": var_name,
            "initialized": False,
            "pre_code": "",
            "post_code": ""
        }
        return var_name

    def generate_preamble(self, block_id: int) -> str:
        """生成状态前置代码"""
        if block_id not in self.state_variables:
            self.create_state_variable(block_id)

        var_name = self.state_variables[block_id]["name"]

        if self.rng:
            patterns = [
                f"local {var_name} = {var_name} or 0",
                f"if not {var_name} then {var_name} = 0 end",
                f"{var_name} = ({var_name} or 0) + 0",
            ]
            return self.rng.choice(patterns)
        return f"local {var_name} = {var_name} or 0"

    def generate_postamble(self, block_id: int) -> str:
        """生成状态后置代码"""
        if block_id not in self.state_variables:
            self.create_state_variable(block_id)

        var_name = self.state_variables[block_id]["name"]

        if self.rng:
            patterns = [
                f"{var_name} = ({var_name} or 0) + 1",
                f"{var_name} = {var_name} or 1",
                f"if {var_name} then {var_name} = {var_name} + 1 else {var_name} = 1 end",
            ]
            return self.rng.choice(patterns)
        return f"{var_name} = ({var_name} or 0) + 1"

    def generate_state_check(self, block_id: int, condition: str = "always") -> str:
        """生成状态检查代码"""
        if block_id not in self.state_variables:
            self.create_state_variable(block_id)

        var_name = self.state_variables[block_id]["name"]

        if condition == "always":
            return f"local _ = {var_name} or 0"
        elif condition == "first":
            return f"if not {var_name} then {var_name} = 1 end"
        elif condition == "count":
            return f"local _cnt = {var_name} or 0"
        return ""

    def get_state_code(self) -> str:
        """生成所有状态变量声明代码"""
        lines = []
        for block_id, info in self.state_variables.items():
            lines.append(f"local {info['name']} = 0")
        return "\n".join(lines)


class NextBlockResolver:
    """
    下一个 Block 解析器

    通过简单映射或计算确定下一个要执行的 block：
    - 直接映射表
    - 偏移计算
    - 异或变换
    - 条件选择
    """

    def __init__(self, rng: random.Random | None = None, prefix: str = "_nxt"):
        self.rng = rng
        self.prefix = prefix
        self.lookup_table: dict[int, int] = {}  # current_id -> next_id
        self.offset_map: dict[int, int] = {}    # current_id -> offset
        self.xor_key: int = 0
        self._id_counter = [0]

    def _gen_id(self) -> int:
        self._id_counter[0] += 1
        return self._id_counter[0]

    def build_direct_lookup(self, execution_order: list[int]) -> None:
        """构建直接映射表"""
        self.lookup_table = {}
        for i, bid in enumerate(execution_order):
            if i < len(execution_order) - 1:
                self.lookup_table[bid] = execution_order[i + 1]
            else:
                self.lookup_table[bid] = -1  # 结束

    def build_offset_lookup(self, execution_order: list[int], offset: int = 1) -> None:
        """构建偏移映射表"""
        self.offset_map = {}
        for i, bid in enumerate(execution_order):
            next_pos = (i + offset) % len(execution_order)
            if i == len(execution_order) - 1:
                self.offset_map[bid] = -1  # 结束
            else:
                self.offset_map[bid] = next_pos

    def set_xor_key(self, key: int) -> None:
        """设置异或密钥"""
        self.xor_key = key

    def generate_lookup_function(self) -> str:
        """生成查找表函数"""
        lines = []

        if self.rng:
            func_name = f"{self.prefix}_{random_lua_identifier(self.rng, 'get')}"
        else:
            func_name = f"{self.prefix}_get"

        lines.append(f"local function {func_name}(cur)")
        lines.append("    local _next = -1")

        for curr_id, next_id in sorted(self.lookup_table.items()):
            lines.append(f"    if cur == {curr_id} then _next = {next_id} end")

        lines.append("    return _next")
        lines.append("end")

        return "\n".join(lines)

    def generate_offset_function(self) -> str:
        """生成偏移计算函数"""
        lines = []

        if self.rng:
            func_name = f"{self.prefix}_{random_lua_identifier(self.rng, 'off')}"
        else:
            func_name = f"{self.prefix}_offset"

        lines.append(f"local function {func_name}(cur, base)")
        lines.append(f"    local _offset = {list(self.offset_map.values())[0] if self.offset_map else 1}")
        lines.append("    return base + _offset")
        lines.append("end")

        return "\n".join(lines)

    def generate_xor_function(self) -> str:
        """生成异或变换函数"""
        if self.rng:
            func_name = f"{self.prefix}_{random_lua_identifier(self.rng, 'xor')}"
        else:
            func_name = f"{self.prefix}_xor"

        return (
            f"local function {func_name}(v)\n"
            f"    return v ~ {self.xor_key}\n"
            f"end"
        )

    def resolve_next(self, current_id: int, default_next: int | None) -> int | None:
        """解析下一个 block ID"""
        if current_id in self.lookup_table:
            next_id = self.lookup_table[current_id]
            return next_id if next_id != -1 else None
        return default_next

    def get_resolver_code(self, resolver_type: ExecutionVariationType) -> str:
        """获取解析器代码"""
        if resolver_type == ExecutionVariationType.LOOKUP_TABLE:
            return self.generate_lookup_function()
        elif resolver_type == ExecutionVariationType.OFFSET_INDIRECT:
            return self.generate_offset_function()
        elif resolver_type == ExecutionVariationType.XOR_TRANSFORM:
            return self.generate_xor_function()
        return ""


class ExecutionPathVariator:
    """
    执行路径变化器

    为程序引入轻量级执行路径变化：
    1. 状态变量包装
    2. 查找表重定向
    3. 计数器变化
    """

    def __init__(self, program: BlockProgram, rng: random.Random | None = None, config: ExecutionPathConfig | None = None):
        self.program = program
        self.rng = rng
        self.config = config if config else ExecutionPathConfig()
        self.state_manager = BlockStateManager(rng, self.config.state_variable_prefix)
        self.resolver = NextBlockResolver(rng)
        self.variation_info: dict[int, dict] = {}

    def apply_variations(self) -> dict:
        """
        应用执行路径变化

        Returns:
            变化应用统计
        """
        if not self.config.enabled:
            return {"status": "disabled"}

        stats = {
            "blocks_with_state": 0,
            "blocks_with_lookup": 0,
            "blocks_with_counter": 0,
            "resolver_type": None
        }

        # 构建查找表
        self.resolver.build_direct_lookup(self.program.execution_order)

        for block in self.program.blocks:
            variations = {}

            if self.config.enable_state_wrappers and self.rng and self.rng.random() < self.config.variation_probability:
                self._apply_state_wrapper(block)
                variations["has_state"] = True
                stats["blocks_with_state"] += 1

            if self.config.enable_lookup_redirect and self.rng and self.rng.random() < self.config.variation_probability:
                self._apply_lookup_redirect(block)
                variations["has_lookup"] = True
                stats["blocks_with_lookup"] += 1

            if self.config.enable_counter_variation and self.rng and self.rng.random() < self.config.variation_probability:
                self._apply_counter_variation(block)
                variations["has_counter"] = True
                stats["blocks_with_counter"] += 1

            if variations:
                self.variation_info[block.block_id] = variations

        # 选择解析器类型
        if self.rng:
            resolver_types = [ExecutionVariationType.LOOKUP_TABLE]
            stats["resolver_type"] = self.rng.choice(resolver_types).value

        return stats

    def _apply_state_wrapper(self, block: CodeBlock) -> None:
        """应用状态包装"""
        pre_code = self.state_manager.generate_preamble(block.block_id)
        post_code = self.state_manager.generate_postamble(block.block_id)

        block.metadata["state_wrapper"] = {
            "pre_code": pre_code,
            "post_code": post_code,
            "enabled": True
        }

    def _apply_lookup_redirect(self, block: CodeBlock) -> None:
        """应用查找表重定向"""
        if block.next_id is not None:
            # 在 metadata 中标记使用查找表
            block.metadata["use_lookup"] = True
            block.metadata["lookup_next"] = block.next_id

    def _apply_counter_variation(self, block: CodeBlock) -> None:
        """应用计数器变化"""
        counter_var = f"_cnt_{block.block_id}"

        if self.rng:
            patterns = [
                f"local {counter_var} = ({counter_var} or 0) + 1",
                f"{counter_var} = ({counter_var} or 0) + 1",
                f"local {counter_var} = 1",
            ]
            counter_code = self.rng.choice(patterns)
        else:
            counter_code = f"local {counter_var} = ({counter_var} or 0) + 1"

        block.metadata["counter_variation"] = {
            "counter_var": counter_var,
            "code": counter_code,
            "enabled": True
        }

    def generate_wrapper_code(self, block: CodeBlock) -> tuple[str, str]:
        """
        生成包装代码

        Returns:
            (pre_code, post_code) 元组
        """
        pre_parts = []
        post_parts = []

        # 状态包装
        if "state_wrapper" in block.metadata and block.metadata["state_wrapper"].get("enabled"):
            pre_parts.append(block.metadata["state_wrapper"]["pre_code"])
            post_parts.append(block.metadata["state_wrapper"]["post_code"])

        # 计数器变化
        if "counter_variation" in block.metadata and block.metadata["counter_variation"].get("enabled"):
            pre_parts.append(block.metadata["counter_variation"]["code"])

        # 查找表重定向
        if "use_lookup" in block.metadata and block.metadata["use_lookup"]:
            lookup_var = f"_nxt_{block.block_id}"
            next_id = block.metadata.get("lookup_next", block.next_id)
            pre_parts.append(f"local {lookup_var} = {next_id}")

        return ("\n".join(pre_parts), "\n".join(post_parts))

    def generate_resolver_code(self) -> str:
        """生成解析器代码"""
        return self.resolver.generate_lookup_function()

    def generate_state_code(self) -> str:
        """生成状态变量代码"""
        return self.state_manager.get_state_code()

    def get_variation_report(self) -> dict:
        """获取变化报告"""
        return {
            "total_blocks": len(self.program.blocks),
            "varied_blocks": len(self.variation_info),
            "variations": self.variation_info
        }


class ExecutionPathEnhancer:
    """
    执行路径增强器

    整合所有执行路径变化功能，提供统一接口。
    """

    def __init__(self, program: BlockProgram, rng: random.Random | None = None):
        self.program = program
        self.rng = rng
        self.config = ExecutionPathConfig()
        self.variator: ExecutionPathVariator | None = None

    def enable_variations(self, config: ExecutionPathConfig | None = None) -> None:
        """启用执行路径变化"""
        if config:
            self.config = config
        self.config.enabled = True
        self.variator = ExecutionPathVariator(self.program, self.rng, self.config)

    def apply(self) -> dict:
        """应用所有变化"""
        if not self.variator:
            self.enable_variations()

        stats = self.variator.apply_variations()
        return stats

    def generate_enhancement_code(self) -> str:
        """生成增强代码"""
        if not self.variator:
            return ""

        lines = []

        # 状态变量
        state_code = self.variator.generate_state_code()
        if state_code:
            lines.append(state_code)

        # 解析器
        resolver_code = self.variator.generate_resolver_code()
        if resolver_code:
            lines.append(resolver_code)

        return "\n".join(lines)

    def get_block_wrapper(self, block: CodeBlock) -> tuple[str, str]:
        """获取 block 的包装代码"""
        if self.variator:
            return self.variator.generate_wrapper_code(block)
        return ("", "")


# ===== 便捷函数 =====


def apply_execution_variations(
    program: BlockProgram,
    rng: random.Random,
    enabled: bool = True,
    probability: float = 0.3
) -> dict:
    """
    便捷函数：应用执行路径变化

    Args:
        program: 目标程序
        rng: 随机数生成器
        enabled: 是否启用
        probability: 变化概率

    Returns:
        应用结果统计
    """
    config = ExecutionPathConfig(
        enabled=enabled,
        variation_probability=probability
    )
    enhancer = ExecutionPathEnhancer(program, rng)
    enhancer.enable_variations(config)
    stats = enhancer.apply()
    return stats


def wrap_block_with_state(
    block: CodeBlock,
    rng: random.Random,
    state_prefix: str = "_st"
) -> tuple[str, str]:
    """
    便捷函数：为 block 添加状态包装

    Args:
        block: 目标 block
        rng: 随机数生成器
        state_prefix: 状态变量前缀

    Returns:
        (pre_code, post_code) 元组
    """
    manager = BlockStateManager(rng, state_prefix)
    pre = manager.generate_preamble(block.block_id)
    post = manager.generate_postamble(block.block_id)
    return (pre, post)


def create_lookup_resolver(
    execution_order: list[int],
    rng: random.Random | None = None,
    prefix: str = "_nxt"
) -> NextBlockResolver:
    """
    便捷函数：创建查找表解析器

    Args:
        execution_order: 执行顺序列表
        rng: 随机数生成器
        prefix: 函数前缀

    Returns:
        NextBlockResolver 实例
    """
    resolver = NextBlockResolver(rng, prefix)
    resolver.build_direct_lookup(execution_order)
    return resolver


# ===== 辅助路径代码混入器 =====


class AuxiliaryPathMixerConfig:
    """辅助路径混入配置"""
    def __init__(
        self,
        enabled: bool = False,
        mix_probability: float = 0.25,
        max_paths_per_block: int = 2,
        prefer_skip_branches: bool = True,
        prefer_dead_code: bool = True,
        include_redundant_blocks: bool = True,
        semantic_preserving: bool = True
    ):
        self.enabled = enabled
        self.mix_probability = mix_probability
        self.max_paths_per_block = max_paths_per_block
        self.prefer_skip_branches = prefer_skip_branches
        self.prefer_dead_code = prefer_dead_code
        self.include_redundant_blocks = include_redundant_blocks
        self.semantic_preserving = semantic_preserving


class AuxiliaryPathMixer:
    """
    辅助路径代码混入器

    在代码生成阶段将辅助路径混入到生成的代码中：
    1. 插入不会被触发的分支
    2. 添加始终被跳过的代码块
    3. 混入不影响语义的冗余结构
    """

    def __init__(self, rng: random.Random | None = None, config: AuxiliaryPathMixerConfig | None = None):
        self.rng = rng
        self.config = config if config else AuxiliaryPathMixerConfig()
        self._id_counter = [0]
        self.used_identifiers: set[str] = set()
        self.mixed_count = 0

    def _gen_id(self) -> int:
        self._id_counter[0] += 1
        return self._id_counter[0]

    def _random_name(self, prefix: str = "_m") -> str:
        """生成随机标识符"""
        chars = string.ascii_lowercase + string.digits
        for _ in range(10):
            name = prefix + "_" + "".join(self.rng.choice(chars) for _ in range(6))
            if name not in self.used_identifiers:
                self.used_identifiers.add(name)
                return name
        return f"{prefix}_{self._gen_id()}"

    def generate_skip_branch(self) -> str:
        """
        生成始终被跳过的分支

        示例: if false then ... end
        """
        if self.rng:
            patterns = [
                ("if false then\n    -- skipped\nend", None),
                ("local _s = false\nif _s then\n    error('unreachable')\nend", "_s"),
                ("if nil then\n    -- never\nend", None),
                ("if 1 ~= 1 then\n    -- impossible\nend", None),
            ]
            content, var = self.rng.choice(patterns)
            if var:
                var_name = self._random_name("_skip")
                content = content.replace(var, var_name)
            return content
        return "if false then\n    -- skipped\nend"

    def generate_dead_code_block(self) -> str:
        """
        生成死代码块

        示例: if false then ... end
        """
        if self.rng:
            patterns = [
                "if false then\n    local _d = 0\nend",
                "do\n    local _dead = nil\n    if _dead then\n        _dead = 1\n    end\nend",
                "repeat\n    break\nuntil false",
            ]
            content = self.rng.choice(patterns)
            content = content.replace("_d", self._random_name("_d"))
            content = content.replace("_dead", self._random_name("_dead"))
            return content
        return "if false then\n    -- dead code\nend"

    def generate_redundant_block(self) -> str:
        """
        生成冗余代码块

        不影响最终结果的代码片段
        """
        if self.rng:
            patterns = [
                "do end",
                "(function() end)()",
                "pcall(function() end)",
                "select('#', nil)",
                "next({})",
                "setmetatable({}, {})",
            ]
            count = self.rng.randint(1, 2)
            lines = [self.rng.choice(patterns) for _ in range(count)]
            return "\n".join(lines)
        return "do end"

    def generate_decoy_variable(self) -> str:
        """
        生成诱饵变量操作

        创建无用但结构有效的变量操作
        """
        if self.rng:
            patterns = [
                f"local _x = 0\n_x = _x\n_x = _x",
                f"local _y = nil\n_y = _y",
                f"local _z = {{}}\n_z = _z",
            ]
            content = self.rng.choice(patterns)
            content = content.replace("_x", self._random_name("_x"))
            content = content.replace("_y", self._random_name("_y"))
            content = content.replace("_z", self._random_name("_z"))
            return content
        return f"local _tmp = 0\n_tmp = _tmp"

    def generate_guard_branch(self) -> str:
        """
        生成守卫分支

        条件永远为真或永远为假的守卫检查
        """
        if self.rng:
            patterns = [
                "local _g = true\nif not _g then\n    error('guard')\nend",
                "local _safe = 1\nif _safe == 0 then\n    _safe = _safe + 1\nend",
            ]
            content = self.rng.choice(patterns)
            content = content.replace("_g", self._random_name("_g"))
            content = content.replace("_safe", self._random_name("_safe"))
            return content
        return "if true then\n    -- always\nend"

    def generate_conditional_noop(self) -> str:
        """
        生成条件空操作

        无论条件如何都不影响程序状态
        """
        if self.rng:
            patterns = [
                "local _cond = false\nif _cond then\n    _cond = not _cond\nend",
                "local _val = 0\nif true then\n    _val = _val\nend",
            ]
            content = self.rng.choice(patterns)
            content = content.replace("_cond", self._random_name("_cond"))
            content = content.replace("_val", self._random_name("_val"))
            return content
        return "do end"

    def generate_skip_block(self) -> str:
        """
        生成跳过块

        通过标志控制的跳过代码
        """
        if self.rng:
            var_name = self._random_name("_skip")
            return (
                f"local {var_name} = true\n"
                f"if {var_name} then\n"
                f"    {var_name} = false\n"
                f"end"
            )
        return "local _skip = true\nif _skip then\n    _skip = false\nend"

    def generate_fake_function_call(self) -> str:
        """
        生成假函数调用

        调用一个空函数
        """
        if self.rng:
            func_name = self._random_name("_dummy")
            return (
                f"local function {func_name}() end\n"
                f"{func_name}()"
            )
        return "(function() end)()"

    def select_mix_content(self) -> str:
        """根据配置选择混入内容"""
        if not self.config.enabled:
            return ""

        if self.rng and self.rng.random() > self.config.mix_probability:
            return ""

        generators = []

        if self.config.prefer_skip_branches:
            generators.append(self.generate_skip_branch)
            generators.append(self.generate_guard_branch)

        if self.config.prefer_dead_code:
            generators.append(self.generate_dead_code_block)
            generators.append(self.generate_conditional_noop)

        if self.config.include_redundant_blocks:
            generators.append(self.generate_redundant_block)
            generators.append(self.generate_decoy_variable)
            generators.append(self.generate_skip_block)
            generators.append(self.generate_fake_function_call)

        if self.rng and generators:
            self.mixed_count += 1
            return self.rng.choice(generators)()

        return ""

    def mix_into_block(self, block_content: str, block_id: int | None = None) -> str:
        """
        将辅助路径混入到 block 内容中

        Args:
            block_content: 原始 block 内容
            block_id: block ID（可选）

        Returns:
            混入辅助路径后的内容
        """
        mix_content = self.select_mix_content()
        if not mix_content:
            return block_content

        if self.rng:
            position = self.rng.randint(0, 2)
        else:
            position = 0

        if position == 0:
            return mix_content + "\n" + block_content
        elif position == 1:
            lines = block_content.split("\n")
            if len(lines) > 1:
                mid = len(lines) // 2
                return "\n".join(lines[:mid]) + "\n" + mix_content + "\n" + "\n".join(lines[mid:])
            return block_content + "\n" + mix_content
        else:
            return block_content + "\n" + mix_content

    def mix_into_function(self, func_body: str, func_name: str = "") -> str:
        """
        将辅助路径混入到函数体中

        Args:
            func_body: 函数体内容
            func_name: 函数名（可选）

        Returns:
            混入后的函数体
        """
        mix_content = self.select_mix_content()
        if not mix_content:
            return func_body

        if self.rng:
            position = self.rng.randint(0, 2)
        else:
            position = 0

        if position == 0:
            return mix_content + "\n" + func_body
        elif position == 1:
            lines = func_body.split("\n")
            if len(lines) > 2:
                insert_pos = self.rng.randint(1, len(lines) - 1) if self.rng else 1
                return "\n".join(lines[:insert_pos]) + "\n" + mix_content + "\n" + "\n".join(lines[insert_pos:])
            return func_body + "\n" + mix_content
        else:
            return func_body + "\n" + mix_content

    def generate_mixed_wrapper(self, original_code: str, wrapper_type: str = "do") -> str:
        """
        生成混入了辅助路径的代码包装

        Args:
            original_code: 原始代码
            wrapper_type: 包装类型 ("do", "function", "if")

        Returns:
            包装后的代码
        """
        mix_content = self.select_mix_content()
        if not mix_content:
            return original_code

        if wrapper_type == "do":
            return f"do\n{mix_content}\n{original_code}\nend"
        elif wrapper_type == "function":
            func_name = self._random_name("_wrapped")
            return (
                f"local function {func_name}()\n"
                f"{mix_content}\n"
                f"{original_code}\n"
                f"end\n"
                f"{func_name}()"
            )
        elif wrapper_type == "if":
            var_name = self._random_name("_run")
            return (
                f"local {var_name} = false\n"
                f"if not {var_name} then\n"
                f"{original_code}\n"
                f"end\n"
                f"{mix_content}"
            )
        return original_code

    def get_statistics(self) -> dict:
        """获取混入统计"""
        return {
            "enabled": self.config.enabled,
            "mix_probability": self.config.mix_probability,
            "mixed_count": self.mixed_count,
            "config": {
                "prefer_skip_branches": self.config.prefer_skip_branches,
                "prefer_dead_code": self.config.prefer_dead_code,
                "include_redundant_blocks": self.config.include_redundant_blocks,
            }
        }


class RedundantBlockMixer:
    """
    冗余 Block 混入器

    在代码生成阶段添加不影响最终结果的冗余 block
    """

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng
        self._id_counter = [0]
        self.blocks: list[dict] = []

    def _gen_id(self) -> int:
        self._id_counter[0] += 1
        return self._id_counter[0]

    def _random_name(self, prefix: str = "_rb") -> str:
        chars = string.ascii_lowercase + string.digits
        return prefix + "_" + "".join(self.rng.choice(chars) for _ in range(6)) if self.rng else f"{prefix}_{self._gen_id()}"

    def generate_dead_block(self) -> dict:
        """生成死代码 block"""
        block_id = -self._gen_id()
        patterns = [
            "if false then\n    error('unreachable')\nend",
            "repeat\n    break\nuntil false",
            "while false do\n    break\nend",
        ]
        content = self.rng.choice(patterns) if self.rng else patterns[0]
        return {
            "block_id": block_id,
            "type": "dead",
            "content": content,
            "executed": False
        }

    def generate_skip_block(self) -> dict:
        """生成跳过 block"""
        block_id = -self._gen_id()
        var_name = self._random_name("_skip")
        return {
            "block_id": block_id,
            "type": "skip",
            "content": f"local {var_name} = true\nif {var_name} then\n    {var_name} = false\nend",
            "executed": True,
            "always_skips": True
        }

    def generate_nop_block(self) -> dict:
        """生成空操作 block"""
        block_id = -self._gen_id()
        patterns = [
            "do end",
            "(function() end)()",
            "pcall(function() end)",
        ]
        content = self.rng.choice(patterns) if self.rng else "do end"
        return {
            "block_id": block_id,
            "type": "nop",
            "content": content,
            "executed": True,
            "no_effect": True
        }

    def generate_decoy_block(self) -> dict:
        """生成诱饵 block"""
        block_id = -self._gen_id()
        var_x = self._random_name("_x")
        var_y = self._random_name("_y")
        return {
            "block_id": block_id,
            "type": "decoy",
            "content": f"local {var_x}, {var_y} = 0, 0\nlocal _t = {var_x}\n{var_x} = {var_y}\n{var_y} = _t",
            "executed": True,
            "no_effect": True
        }

    def create_redundant_blocks(self, count: int = 2) -> list[dict]:
        """创建多个冗余 block"""
        self.blocks = []
        generators = [
            self.generate_dead_block,
            self.generate_skip_block,
            self.generate_nop_block,
            self.generate_decoy_block,
        ]

        for _ in range(count):
            if self.rng:
                block = self.rng.choice(generators)()
            else:
                block = generators[0]()
            self.blocks.append(block)

        return self.blocks

    def get_blocks_code(self) -> str:
        """获取所有冗余 block 的代码"""
        lines = []
        for block in self.blocks:
            lines.append(f"-- Redundant block {block['block_id']} ({block['type']})")
            lines.append(block["content"])
            lines.append("")
        return "\n".join(lines)

    def inject_into_program(self, program_lines: list[str]) -> list[str]:
        """将冗余 block 注入到程序代码中"""
        if not self.blocks:
            return program_lines

        # 在程序开始处插入
        inject_lines = ["", "-- Injected redundant blocks", self.get_blocks_code()]

        if program_lines:
            # 在 local program = { 之后插入
            for i, line in enumerate(program_lines):
                if "local program = {" in line:
                    program_lines = program_lines[:i+1] + inject_lines + program_lines[i+1:]
                    break
            else:
                # 如果找不到插入点，在开头插入
                program_lines = inject_lines + program_lines

        return program_lines


# ===== 便捷函数 =====


def mix_auxiliary_paths(
    code: str,
    rng: random.Random,
    enabled: bool = True,
    probability: float = 0.25
) -> str:
    """
    便捷函数：混入辅助路径

    Args:
        code: 原始代码
        rng: 随机数生成器
        enabled: 是否启用
        probability: 混入概率

    Returns:
        混入辅助路径后的代码
    """
    config = AuxiliaryPathMixerConfig(enabled=enabled, mix_probability=probability)
    mixer = AuxiliaryPathMixer(rng, config)
    return mixer.mix_into_block(code)


def inject_redundant_blocks_to_code(
    code_lines: list[str],
    rng: random.Random,
    count: int = 2
) -> list[str]:
    """
    便捷函数：将冗余 block 注入到代码行列表

    Args:
        code_lines: 代码行列表
        rng: 随机数生成器
        count: 冗余 block 数量

    Returns:
        注入后的代码行列表
    """
    mixer = RedundantBlockMixer(rng)
    mixer.create_redundant_blocks(count)
    return mixer.inject_into_program(code_lines)


# ===== 代码生成随机化策略系统 =====


class CodeGenerationStrategy(Enum):
    """代码生成策略枚举"""
    # Block 组织方式
    FUNCTION_TABLE = "function_table"      # 函数表方式
    DIRECT_DISPATCH = "direct_dispatch"    # 直接分发方式
    INDEXED_ACCESS = "indexed_access"     # 索引访问方式
    NAMED_BLOCKS = "named_blocks"         # 命名块方式
    CLOSURE_WRAPPER = "closure_wrapper"    # 闭包包装方式

    # 结构组合方式
    FLAT_SEQUENCE = "flat_sequence"        # 扁平顺序
    NESTED_STRUCTURE = "nested_structure"  # 嵌套结构
    GROUPED_BLOCKS = "grouped_blocks"     # 分组块

    # 返回方式
    RETURN_NEXT = "return_next"            # 返回下一个 ID
    CALL_NEXT = "call_next"                # 调用下一个
    YIELD_NEXT = "yield_next"             # 协程方式


class StructureVariant(Enum):
    """结构变体枚举"""
    MINIMAL = "minimal"                    # 最小化结构
    EXPANDED = "expanded"                  # 展开结构
    COMPRESSED = "compressed"              # 压缩结构
    ANNOTATED = "annotated"               # 带注释结构
    WRAPPED = "wrapped"                    # 包装结构


@dataclass
class GenerationStrategyConfig:
    """生成策略配置"""
    block_organization: CodeGenerationStrategy = CodeGenerationStrategy.FUNCTION_TABLE
    structure_type: StructureVariant = StructureVariant.EXPANDED
    return_mechanism: CodeGenerationStrategy = CodeGenerationStrategy.RETURN_NEXT
    enable_comments: bool = False
    enable_metadata: bool = True
    indent_style: str = "standard"  # "standard", "compact", "aligned"
    naming_scheme: str = "random"   # "sequential", "random", "semantic"
    include_structure_hints: bool = False


class BlockOrganizationStrategy:
    """
    Block 组织策略

    定义不同方式组织 block 的逻辑
    """

    @staticmethod
    def function_table_style(rng: random.Random, prefix: str) -> dict:
        """函数表方式"""
        return {
            "type": CodeGenerationStrategy.FUNCTION_TABLE,
            "table_var": f"{prefix}_tbl" if rng else "_tbl",
            "meta_var": f"{prefix}_meta" if rng else "_meta",
            "index_style": "numeric",
            "access_pattern": "table_lookup"
        }

    @staticmethod
    def direct_dispatch_style(rng: random.Random, prefix: str) -> dict:
        """直接分发方式"""
        return {
            "type": CodeGenerationStrategy.DIRECT_DISPATCH,
            "dispatch_var": f"{prefix}_dispatch" if rng else "_dispatch",
            "switch_style": "if_else",
            "index_style": "branch"
        }

    @staticmethod
    def indexed_access_style(rng: random.Random, prefix: str) -> dict:
        """索引访问方式"""
        return {
            "type": CodeGenerationStrategy.INDEXED_ACCESS,
            "array_var": f"{prefix}_arr" if rng else "_arr",
            "access_method": "rawget",
            "fallback": "nil"
        }

    @staticmethod
    def named_blocks_style(rng: random.Random, prefix: str) -> dict:
        """命名块方式"""
        return {
            "type": CodeGenerationStrategy.NAMED_BLOCKS,
            "block_prefix": f"{prefix}_blk" if rng else "_blk",
            "naming": "unique_random" if rng else "sequential",
            "registry_var": f"{prefix}_registry" if rng else "_registry"
        }

    @staticmethod
    def closure_wrapper_style(rng: random.Random, prefix: str) -> dict:
        """闭包包装方式"""
        return {
            "type": CodeGenerationStrategy.CLOSURE_WRAPPER,
            "wrapper_prefix": f"{prefix}_wrap" if rng else "_wrap",
            "closure_scope": "isolated",
            "capture_method": "upvalue"
        }

    @classmethod
    def select_style(cls, rng: random.Random) -> dict:
        """随机选择组织风格"""
        styles = [
            cls.function_table_style,
            cls.indexed_access_style,
            cls.named_blocks_style,
            cls.closure_wrapper_style,
        ]
        return rng.choice(styles)(rng, f"_s{rng.randint(1000, 9999)}")


class StructureVariantStrategy:
    """
    结构变体策略

    定义代码结构的不同变体
    """

    @staticmethod
    def minimal_variant(block: CodeBlock, func_name: str, next_id: int | None) -> list[str]:
        """最小化结构"""
        lines = [f"local function {func_name}()"]
        if block.content.strip():
            lines.append(f"{indent_lua(block.content.strip(), 4)}")
        next_expr = f"return {next_id}" if next_id is not None else "return"
        lines.append(f"    {next_expr}")
        lines.append("end")
        return lines

    @staticmethod
    def expanded_variant(block: CodeBlock, func_name: str, next_id: int | None) -> list[str]:
        """展开结构"""
        lines = [f"local function {func_name}()"]
        if block.content.strip():
            lines.append(indent_lua(block.content.strip(), 4))
        else:
            lines.append("    -- empty block")
        next_expr = f"return {next_id}" if next_id is not None else "return"
        lines.append(f"    {next_expr}")
        lines.append("end")
        return lines

    @staticmethod
    def compressed_variant(block: CodeBlock, func_name: str, next_id: int | None) -> list[str]:
        """压缩结构"""
        content = block.content.strip().replace("\n", ";") if block.content.strip() else ""
        next_expr = f"return {next_id}" if next_id is not None else "return"
        if content:
            return [f"local function {func_name}(){content};{next_expr}end"]
        return [f"local function {func_name}() {next_expr} end"]

    @staticmethod
    def annotated_variant(block: CodeBlock, func_name: str, next_id: int | None) -> list[str]:
        """带注释结构"""
        lines = [
            f"-- Block {block.block_id} ({block.block_type})",
            f"local function {func_name}()"
        ]
        if block.content.strip():
            lines.append(indent_lua(block.content.strip(), 4))
        else:
            lines.append("    -- empty block")
        next_expr = f"return {next_id}" if next_id is not None else "return"
        lines.append(f"    {next_expr}")
        lines.append("end")
        lines.append(f"-- End {func_name}")
        return lines

    @staticmethod
    def wrapped_variant(block: CodeBlock, func_name: str, next_id: int | None) -> list[str]:
        """包装结构"""
        lines = [
            f"do",
            f"    local function {func_name}()"
        ]
        if block.content.strip():
            lines.append(indent_lua(block.content.strip(), 8))
        else:
            lines.append("        -- empty block")
        next_expr = f"return {next_id}" if next_id is not None else "return"
        lines.append(f"        {next_expr}")
        lines.append("    end")
        lines.append(f"end")
        return lines

    @classmethod
    def apply_variant(cls, variant: StructureVariant, block: CodeBlock, func_name: str, next_id: int | None) -> list[str]:
        """应用变体"""
        if variant == StructureVariant.MINIMAL:
            return cls.minimal_variant(block, func_name, next_id)
        elif variant == StructureVariant.EXPANDED:
            return cls.expanded_variant(block, func_name, next_id)
        elif variant == StructureVariant.COMPRESSED:
            return cls.compressed_variant(block, func_name, next_id)
        elif variant == StructureVariant.ANNOTATED:
            return cls.annotated_variant(block, func_name, next_id)
        elif variant == StructureVariant.WRAPPED:
            return cls.wrapped_variant(block, func_name, next_id)
        return cls.expanded_variant(block, func_name, next_id)


class ReturnMechanismStrategy:
    """
    返回机制策略

    定义不同的 block 执行完毕后返回方式
    """

    @staticmethod
    def return_next_style(next_id: int | None) -> str:
        """返回下一个 ID"""
        if next_id is not None:
            return f"return {next_id}"
        return "return"

    @staticmethod
    def call_next_style(func_name: str, program_var: str) -> str:
        """调用下一个函数"""
        return f"local _next = {program_var}[_idx + 1]; if _next then _next() end"

    @staticmethod
    def yield_style() -> str:
        """协程方式"""
        return "coroutine.yield()"


class NamingStrategy:
    """
    命名策略

    定义不同的标识符命名方式
    """

    @staticmethod
    def sequential_name(prefix: str, index: int) -> str:
        """顺序命名"""
        return f"{prefix}_{index}"

    @staticmethod
    def random_name(rng: random.Random, prefix: str) -> str:
        """随机命名"""
        chars = string.ascii_lowercase
        suffix = "".join(rng.choice(chars) for _ in range(6))
        return f"{prefix}_{suffix}"

    @staticmethod
    def semantic_name(block_type: str, index: int) -> str:
        """语义命名"""
        type_map = {
            "statement": "stmt",
            "function": "func",
            "control_flow": "ctrl",
            "assignment": "assign",
            "expression": "expr",
        }
        suffix = type_map.get(block_type, "blk")
        return f"{suffix}_{index}"


class CodeGenerationRandomizer:
    """
    代码生成随机化器

    整合所有策略，提供随机化的代码生成
    """

    def __init__(self, rng: random.Random | None = None, config: GenerationStrategyConfig | None = None):
        self.rng = rng
        self.config = config if config else GenerationStrategyConfig()
        self._name_cache: dict[int, str] = {}
        self._generated_count = 0

    def generate_block_function(self, block: CodeBlock, index: int, next_id: int | None) -> list[str]:
        """生成单个 block 函数"""
        self._generated_count += 1

        # 生成函数名
        if self.config.naming_scheme == "sequential":
            func_name = NamingStrategy.sequential_name("_blk", index)
        elif self.config.naming_scheme == "random" and self.rng:
            func_name = NamingStrategy.random_name(self.rng, "_blk")
        else:
            func_name = NamingStrategy.semantic_name(block.block_type, index)

        self._name_cache[block.block_id] = func_name

        # 根据结构变体生成
        return StructureVariantStrategy.apply_variant(
            self.config.structure_type,
            block,
            func_name,
            next_id
        )

    def generate_program_structure(self, program: BlockProgram) -> dict:
        """生成程序结构"""
        # 根据组织策略生成
        if self.config.block_organization == CodeGenerationStrategy.FUNCTION_TABLE:
            return self._generate_function_table(program)
        elif self.config.block_organization == CodeGenerationStrategy.INDEXED_ACCESS:
            return self._generate_indexed_access(program)
        elif self.config.block_organization == CodeGenerationStrategy.NAMED_BLOCKS:
            return self._generate_named_blocks(program)
        elif self.config.block_organization == CodeGenerationStrategy.CLOSURE_WRAPPER:
            return self._generate_closure_wrapper(program)
        else:
            return self._generate_function_table(program)

    def _generate_function_table(self, program: BlockProgram) -> dict:
        """生成函数表结构"""
        prefix = "_tbl" if not self.rng else f"_s{self.rng.randint(1000, 9999)}"
        return {
            "type": CodeGenerationStrategy.FUNCTION_TABLE,
            "table_var": f"{prefix}_tbl",
            "meta_var": f"{prefix}_meta",
            "style": BlockOrganizationStrategy.function_table_style(self.rng, prefix) if self.rng else {}
        }

    def _generate_indexed_access(self, program: BlockProgram) -> dict:
        """生成索引访问结构"""
        prefix = "_arr" if not self.rng else f"_s{self.rng.randint(1000, 9999)}"
        return {
            "type": CodeGenerationStrategy.INDEXED_ACCESS,
            "array_var": f"{prefix}_arr",
            "access_method": "rawget",
            "style": BlockOrganizationStrategy.indexed_access_style(self.rng, prefix) if self.rng else {}
        }

    def _generate_named_blocks(self, program: BlockProgram) -> dict:
        """生成命名块结构"""
        prefix = "_blk" if not self.rng else f"_s{self.rng.randint(1000, 9999)}"
        return {
            "type": CodeGenerationStrategy.NAMED_BLOCKS,
            "block_prefix": prefix,
            "registry_var": f"{prefix}_registry",
            "style": BlockOrganizationStrategy.named_blocks_style(self.rng, prefix) if self.rng else {}
        }

    def _generate_closure_wrapper(self, program: BlockProgram) -> dict:
        """生成闭包包装结构"""
        prefix = "_wrap" if not self.rng else f"_s{self.rng.randint(1000, 9999)}"
        return {
            "type": CodeGenerationStrategy.CLOSURE_WRAPPER,
            "wrapper_prefix": prefix,
            "style": BlockOrganizationStrategy.closure_wrapper_style(self.rng, prefix) if self.rng else {}
        }

    def generate_program_header(self, structure_info: dict) -> list[str]:
        """生成程序头部"""
        lines = []
        struct_type = structure_info.get("type")

        if struct_type == CodeGenerationStrategy.FUNCTION_TABLE:
            lines.append(f"local {structure_info['table_var']} = {{}}")
            if self.config.enable_metadata:
                lines.append(f"local {structure_info['meta_var']} = {{}}")
        elif struct_type == CodeGenerationStrategy.INDEXED_ACCESS:
            lines.append(f"local {structure_info['array_var']} = {{}}")
        elif struct_type == CodeGenerationStrategy.NAMED_BLOCKS:
            lines.append(f"local {structure_info['registry_var']} = {{}}")
        elif struct_type == CodeGenerationStrategy.CLOSURE_WRAPPER:
            lines.append(f"local {structure_info['wrapper_prefix']}_env = {{}}")

        return lines

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            "config": {
                "block_organization": self.config.block_organization.value,
                "structure_variant": self.config.structure_type.value,
                "naming_scheme": self.config.naming_scheme,
                "enable_metadata": self.config.enable_metadata,
            },
            "generated_blocks": self._generated_count,
            "unique_names": len(self._name_cache)
        }


class RandomizedCodeGenerator:
    """
    随机化代码生成器

    整合所有随机化策略，生成结构多样但语义一致的代码
    """

    def __init__(self, program: BlockProgram, rng: random.Random | None = None):
        self.program = program
        self.rng = rng
        self.config = GenerationStrategyConfig()
        self.randomizer = CodeGenerationRandomizer(rng, self.config)

    def set_strategy(self, config: GenerationStrategyConfig) -> None:
        """设置生成策略"""
        self.config = config
        self.randomizer.config = config

    def randomize_strategy(self) -> GenerationStrategyConfig:
        """随机化策略配置"""
        if not self.rng:
            return self.config

        strategies = list(CodeGenerationStrategy)
        variants = list(StructureVariant)

        self.config = GenerationStrategyConfig(
            block_organization=self.rng.choice(strategies),
            structure_type=self.rng.choice(variants),
            return_mechanism=self.rng.choice(strategies),
            enable_comments=self.rng.random() > 0.5,
            enable_metadata=self.rng.random() > 0.3,
            naming_scheme=self.rng.choice(["sequential", "random", "semantic"]),
        )
        self.randomizer.config = self.config
        return self.config

    def generate(self) -> tuple[str, dict]:
        """
        生成随机化代码

        Returns:
            (generated_code, statistics) 元组
        """
        lines: list[str] = []

        # 生成结构信息
        structure_info = self.randomizer.generate_program_structure(self.program)

        # 生成头部
        header = self.randomizer.generate_program_header(structure_info)
        lines.extend(header)
        lines.append("")

        # 生成各个 block
        for idx, bid in enumerate(self.program.execution_order):
            block = self.program.get_block(bid)
            if block:
                block_lines = self.randomizer.generate_block_function(
                    block, idx + 1, block.next_id
                )
                lines.extend(block_lines)
                lines.append("")

        # 生成程序表
        struct_type = structure_info.get("type")
        if struct_type == CodeGenerationStrategy.FUNCTION_TABLE:
            lines.append(f"for i, fn in ipairs({{")
            for idx in range(len(self.program.execution_order)):
                lines.append(f"    {idx + 1},")
            lines.append(f"}}) do {structure_info['table_var']}[i] = fn end")

        return "\n".join(lines), self.randomizer.get_statistics()

    def generate_multiple_variants(self, count: int = 3) -> list[tuple[str, dict]]:
        """
        生成多个变体

        Args:
            count: 变体数量

        Returns:
            变体列表，每个元素为 (code, stats) 元组
        """
        variants = []

        for _ in range(count):
            self.randomize_strategy()
            code, stats = self.generate()
            variants.append((code, stats))

        return variants


# ===== 便捷函数 =====


def create_randomized_generator(
    program: BlockProgram,
    rng: random.Random,
    strategy: str = "random"
) -> RandomizedCodeGenerator:
    """
    创建随机化代码生成器

    Args:
        program: 目标程序
        rng: 随机数生成器
        strategy: 策略类型 ("random", "minimal", "expanded", "annotated")

    Returns:
        RandomizedCodeGenerator 实例
    """
    generator = RandomizedCodeGenerator(program, rng)

    if strategy == "minimal":
        generator.set_strategy(GenerationStrategyConfig(
            structure_type=StructureVariant.MINIMAL,
            enable_comments=False,
            naming_scheme="sequential"
        ))
    elif strategy == "expanded":
        generator.set_strategy(GenerationStrategyConfig(
            structure_type=StructureVariant.EXPANDED,
            enable_comments=False,
            naming_scheme="sequential"
        ))
    elif strategy == "annotated":
        generator.set_strategy(GenerationStrategyConfig(
            structure_type=StructureVariant.ANNOTATED,
            enable_comments=True,
            naming_scheme="semantic"
        ))
    elif strategy == "random":
        generator.randomize_strategy()

    return generator


def generate_variant_code(
    program: BlockProgram,
    rng: random.Random,
    variant: str = "expanded"
) -> str:
    """
    生成指定变体的代码

    Args:
        program: 目标程序
        rng: 随机数生成器
        variant: 变体类型 ("minimal", "expanded", "compressed", "annotated", "wrapped")

    Returns:
        生成的代码
    """
    variant_map = {
        "minimal": StructureVariant.MINIMAL,
        "expanded": StructureVariant.EXPANDED,
        "compressed": StructureVariant.COMPRESSED,
        "annotated": StructureVariant.ANNOTATED,
        "wrapped": StructureVariant.WRAPPED,
    }

    config = GenerationStrategyConfig(
        structure_type=variant_map.get(variant, StructureVariant.EXPANDED)
    )

    generator = RandomizedCodeGenerator(program, rng)
    generator.set_strategy(config)
    code, _ = generator.generate()
    return code


# ===== 执行路径映射系统 =====


class NextBlockResolverType(Enum):
    """下一个 Block 解析器类型"""
    DIRECT = "direct"              # 直接返回
    TABLE_LOOKUP = "table_lookup"  # 表查找
    OFFSET_CALC = "offset_calc"    # 偏移计算
    XOR_TRANSFORM = "xor_transform" # 异或变换
    STATE_INDIRECT = "state_indirect"  # 状态间接


@dataclass
class NextBlockResolverConfig:
    """下一个 Block 解析器配置"""
    enabled: bool = False
    resolver_type: NextBlockResolverType = NextBlockResolverType.DIRECT
    include_state_var: bool = False
    state_var_prefix: str = "_ns"
    offset_var_prefix: str = "_off"


class NextBlockResolver:
    """
    下一个 Block 解析器

    不直接返回固定 next_id，而是通过映射或计算得到下一个 block
    """

    def __init__(self, program: BlockProgram, rng: random.Random | None = None, config: NextBlockResolverConfig | None = None):
        self.program = program
        self.rng = rng
        self.config = config if config else NextBlockResolverConfig()
        self.next_map: dict[int, int] = {}  # current_id -> actual_next_id
        self.reverse_map: dict[int, int] = {}  # actual_next_id -> virtual_id (for lookup)
        self.xor_key: int = 0
        self._id_counter = [0]
        self._build_maps()

    def _gen_id(self) -> int:
        self._id_counter[0] += 1
        return self._id_counter[0]

    def _build_maps(self) -> None:
        """构建映射表"""
        self.next_map = {}
        self.reverse_map = {}

        # 构建直接映射
        for block in self.program.blocks:
            if block.next_id is not None:
                self.next_map[block.block_id] = block.next_id

        # 构建反向映射
        for curr, nxt in self.next_map.items():
            if nxt not in self.reverse_map:
                self.reverse_map[nxt] = []
            self.reverse_map[nxt].append(curr)

    def build_lookup_table(self) -> dict[int, int]:
        """构建查找表: block_id -> 索引位置"""
        lookup = {}
        for idx, bid in enumerate(self.program.execution_order):
            lookup[bid] = idx + 1  # 1-indexed
        return lookup

    def build_offset_map(self) -> dict[int, int]:
        """构建偏移映射"""
        offset_map = {}
        order = self.program.execution_order

        for i, bid in enumerate(order):
            if i < len(order) - 1:
                offset_map[bid] = order[i + 1]
            else:
                offset_map[bid] = -1  # 结束

        return offset_map

    def set_xor_key(self, key: int) -> None:
        """设置异或密钥"""
        self.xor_key = key

    def generate_resolver_function(self) -> str:
        """生成解析器函数"""
        lines = []

        if self.config.resolver_type == NextBlockResolverType.DIRECT:
            lines = self._generate_direct_resolver()
        elif self.config.resolver_type == NextBlockResolverType.TABLE_LOOKUP:
            lines = self._generate_lookup_resolver()
        elif self.config.resolver_type == NextBlockResolverType.OFFSET_CALC:
            lines = self._generate_offset_resolver()
        elif self.config.resolver_type == NextBlockResolverType.XOR_TRANSFORM:
            lines = self._generate_xor_resolver()
        elif self.config.resolver_type == NextBlockResolverType.STATE_INDIRECT:
            lines = self._generate_state_resolver()

        return "\n".join(lines)

    def _generate_direct_resolver(self) -> list[str]:
        """生成直接解析器"""
        if self.rng:
            func_name = f"_next_{random_lua_identifier(self.rng, 'get')}"
        else:
            func_name = "_next_get"

        lines = [f"local function {func_name}(cur)"]
        lines.append("    return cur")
        lines.append("end")

        return lines

    def _generate_lookup_resolver(self) -> list[str]:
        """生成查找表解析器"""
        if self.rng:
            func_name = f"_next_{random_lua_identifier(self.rng, 'lookup')}"
            map_name = f"_next_{random_lua_identifier(self.rng, 'map')}"
        else:
            func_name = "_next_lookup"
            map_name = "_next_map"

        lines = [f"local {map_name} = {{}}"]
        for curr, nxt in sorted(self.next_map.items()):
            lines.append(f"{map_name}[{curr}] = {nxt}")

        lines.append(f"local function {func_name}(cur)")
        lines.append(f"    return {map_name}[cur] or cur + 1")
        lines.append("end")

        return lines

    def _generate_offset_resolver(self) -> list[str]:
        """生成偏移计算解析器"""
        if self.rng:
            func_name = f"_next_{random_lua_identifier(self.rng, 'offset')}"
            order_name = f"_next_{random_lua_identifier(self.rng, 'order')}"
        else:
            func_name = "_next_offset"
            order_name = "_next_order"

        lines = [f"local {order_name} = {{"]
        for idx, bid in enumerate(self.program.execution_order):
            lines.append(f"    [{idx + 1}] = {bid},")
        lines.append("}")

        lines.append(f"local function {func_name}(cur)")
        lines.append(f"    for i, v in ipairs({order_name}) do")
        lines.append(f"        if v == cur and i < #{order_name} then")
        lines.append(f"            return {order_name}[i + 1]")
        lines.append(f"        end")
        lines.append(f"    end")
        lines.append(f"    return nil")
        lines.append("end")

        return lines

    def _generate_xor_resolver(self) -> list[str]:
        """生成异或变换解析器"""
        if self.rng:
            func_name = f"_next_{random_lua_identifier(self.rng, 'xor')}"
        else:
            func_name = "_next_xor"

        key = self.xor_key if self.xor_key else 0x2A

        lines = [
            f"local _xor_key = {key}",
            f"local function {func_name}(cur)",
            f"    return cur ~ _xor_key",
            f"end"
        ]

        return lines

    def _generate_state_resolver(self) -> list[str]:
        """生成状态间接解析器"""
        if self.rng:
            func_name = f"_next_{random_lua_identifier(self.rng, 'state')}"
            state_name = f"{self.config.state_var_prefix}_{random_lua_identifier(self.rng, 's')}"
            map_name = f"_next_{random_lua_identifier(self.rng, 'map')}"
        else:
            func_name = "_next_state"
            state_name = f"{self.config.state_var_prefix}_0"
            map_name = "_next_map"

        lines = [f"local {state_name} = 0"]
        lines.append(f"local {map_name} = {{}}")

        for curr, nxt in sorted(self.next_map.items()):
            lines.append(f"{map_name}[{curr}] = {nxt}")

        lines.append(f"local function {func_name}(cur)")
        lines.append(f"    {state_name} = ({state_name} + 1) - 1")
        lines.append(f"    return {map_name}[cur] or cur + 1")
        lines.append("end")

        return lines

    def resolve_next(self, current_id: int) -> int | None:
        """
        解析下一个 block ID

        使用配置的解析策略
        """
        if self.config.resolver_type == NextBlockResolverType.DIRECT:
            return self.next_map.get(current_id, current_id + 1 if current_id else 1)

        elif self.config.resolver_type == NextBlockResolverType.TABLE_LOOKUP:
            return self.next_map.get(current_id)

        elif self.config.resolver_type == NextBlockResolverType.OFFSET_CALC:
            order = self.program.execution_order
            if current_id in order:
                idx = order.index(current_id)
                if idx < len(order) - 1:
                    return order[idx + 1]
            return None

        elif self.config.resolver_type == NextBlockResolverType.XOR_TRANSFORM:
            return current_id ^ self.xor_key

        elif self.config.resolver_type == NextBlockResolverType.STATE_INDIRECT:
            return self.next_map.get(current_id)

        return self.next_map.get(current_id)

    def get_resolver_code(self) -> str:
        """获取解析器代码"""
        return self.generate_resolver_function()

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            "enabled": self.config.enabled,
            "resolver_type": self.config.resolver_type.value,
            "total_mappings": len(self.next_map),
            "xor_key": self.xor_key if self.config.resolver_type == NextBlockResolverType.XOR_TRANSFORM else None
        }


class ExecutionPathMapper:
    """
    执行路径映射器

    在代码生成阶段为每个 block 的 next_id 生成映射逻辑
    """

    def __init__(self, program: BlockProgram, rng: random.Random | None = None, config: NextBlockResolverConfig | None = None):
        self.program = program
        self.rng = rng
        self.config = config if config else NextBlockResolverConfig()
        self.resolver = NextBlockResolver(program, rng, config)
        self.block_next_code: dict[int, str] = {}

    def generate_next_code(self, block: CodeBlock) -> str:
        """
        为 block 生成 next 代码

        返回: 用于替换直接 next_id 的代码
        """
        next_id = block.next_id

        if self.config.resolver_type == NextBlockResolverType.DIRECT:
            return str(next_id) if next_id is not None else "nil"

        elif self.config.resolver_type == NextBlockResolverType.TABLE_LOOKUP:
            if self.rng:
                var_name = f"_n{self.rng.randint(100, 999)}"
            else:
                var_name = "_n"
            return f"({self.resolver.generate_resolver_function().split('local function ')[1].split('(')[0]}({block.block_id}) or {next_id})"

        elif self.config.resolver_type == NextBlockResolverType.OFFSET_CALC:
            order = self.program.execution_order
            if block.block_id in order:
                idx = order.index(block.block_id)
                if idx < len(order) - 1:
                    return str(order[idx + 1])
            return "nil"

        elif self.config.resolver_type == NextBlockResolverType.XOR_TRANSFORM:
            return str(block.block_id ^ self.resolver.xor_key)

        elif self.config.resolver_type == NextBlockResolverType.STATE_INDIRECT:
            if self.rng:
                state_var = f"{self.config.state_var_prefix}_{random_lua_identifier(self.rng, 'v')}"
            else:
                state_var = f"{self.config.state_var_prefix}_v"
            return f"(function() {state_var} = ({state_var} + 0) - 0; return {next_id} end)()"

        return str(next_id) if next_id is not None else "nil"

    def generate_block_wrapper(self, block: CodeBlock, func_body: str) -> str:
        """
        为 block 函数生成包装代码

        将直接的 return next_id 替换为通过解析器计算
        """
        next_code = self.generate_next_code(block)

        # 检查函数体是否以 return 结尾
        lines = func_body.strip().split("\n")
        if lines and lines[-1].strip().startswith("return"):
            # 替换最后一行
            lines[-1] = f"    return {next_code}"
            return "\n".join(lines)

        # 否则在末尾添加 return
        return func_body + f"\n    return {next_code}"

    def generate_resolver_header(self) -> str:
        """生成解析器头部代码"""
        return self.resolver.get_resolver_code()

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            "resolver": self.resolver.get_statistics(),
            "blocks_with_mapping": len(self.block_next_code)
        }


# ===== 便捷函数 =====


def apply_next_block_mapping(
    program: BlockProgram,
    rng: random.Random,
    resolver_type: str = "lookup",
    enabled: bool = True
) -> tuple[str, NextBlockResolver]:
    """
    便捷函数：应用 next block 映射

    Args:
        program: 目标程序
        rng: 随机数生成器
        resolver_type: 解析器类型 ("direct", "lookup", "offset", "xor", "state")
        enabled: 是否启用

    Returns:
        (resolver_code, resolver_instance) 元组
    """
    type_map = {
        "direct": NextBlockResolverType.DIRECT,
        "lookup": NextBlockResolverType.TABLE_LOOKUP,
        "offset": NextBlockResolverType.OFFSET_CALC,
        "xor": NextBlockResolverType.XOR_TRANSFORM,
        "state": NextBlockResolverType.STATE_INDIRECT,
    }

    config = NextBlockResolverConfig(
        enabled=enabled,
        resolver_type=type_map.get(resolver_type, NextBlockResolverType.DIRECT)
    )

    mapper = ExecutionPathMapper(program, rng, config)
    return mapper.generate_resolver_header(), mapper.resolver


def wrap_next_with_mapping(
    block: CodeBlock,
    program: BlockProgram,
    rng: random.Random,
    resolver_type: str = "lookup"
) -> str:
    """
    便捷函数：包装 block 的 next 返回

    Args:
        block: 目标 block
        program: 所属程序
        rng: 随机数生成器
        resolver_type: 解析器类型

    Returns:
        映射后的 next 代码
    """
    type_map = {
        "direct": NextBlockResolverType.DIRECT,
        "lookup": NextBlockResolverType.TABLE_LOOKUP,
        "offset": NextBlockResolverType.OFFSET_CALC,
        "xor": NextBlockResolverType.XOR_TRANSFORM,
        "state": NextBlockResolverType.STATE_INDIRECT,
    }

    config = NextBlockResolverConfig(
        enabled=True,
        resolver_type=type_map.get(resolver_type, NextBlockResolverType.DIRECT)
    )

    mapper = ExecutionPathMapper(program, rng, config)
    return mapper.generate_next_code(block)


# ===== 增强随机化代码生成系统 =====


class BlockOrderStrategy(Enum):
    """Block 排序策略"""
    SEQUENTIAL = "sequential"         # 顺序排列
    SHUFFLED = "shuffled"            # 随机打乱
    INTERLEAVED = "interleaved"       # 交错排列
    GROUPED = "grouped"              # 分组排列
    REVERSED_GROUPS = "reversed_groups"  # 反向分组


class ConstantAccessStrategy(Enum):
    """常量访问策略"""
    DIRECT = "direct"                 # 直接表访问
    SEPARATE_GETTERS = "separate_getters"  # 独立 getter
    UNIFIED_GETTER = "unified_getter"  # 统一 getter
    INDEXED_GETTER = "indexed_getter"  # 索引 getter
    CONDITIONAL_GETTER = "conditional_getter"  # 条件 getter
    WRAPPED_GETTER = "wrapped_getter"  # 包装 getter


class BlockConstantAccessStrategy(Enum):
    """
    Block 级常量访问策略

    定义单个 Block 内访问常量池的方式，支持不同 Block 使用不同策略。
    语义等价但形式多样的访问方式。
    """
    # 直接表访问
    DIRECT_TABLE = "direct_table"

    # 标准 getter 函数调用
    GETTER_CALL = "getter_call"

    # 统一入口函数调用
    UNIFIED_CALL = "unified_call"

    # 带索引的 getter 调用
    INDEXED_CALL = "indexed_call"

    # 局部变量缓存访问
    LOCAL_CACHE = "local_cache"

    # 闭包包装访问
    CLOSURE_WRAP = "closure_wrap"

    # 元编程访问（使用 rawget）
    METATABLE_ACCESS = "metatable_access"

    # 多步计算访问（中间变量）
    MULTI_STEP = "multi_step"


class BlockConstantAccessConfig:
    """
    Block 级常量访问配置

    控制 Block 级别常量访问的多样化行为。
    """

    def __init__(
        self,
        rng: random.Random | None = None,
        enable_diversification: bool = True,
        strategy_weights: dict[BlockConstantAccessStrategy, float] | None = None,
        cache_enabled: bool = True,
        cache_size: int = 3,
        local_prefix: str = "_lc",
    ):
        self.rng = rng
        self.enable_diversification = enable_diversification
        self.strategy_weights = strategy_weights or self._default_weights()
        self.cache_enabled = cache_enabled
        self.cache_size = cache_size
        self.local_prefix = local_prefix

        if rng:
            self.local_prefix = random_lua_identifier(rng, local_prefix)

    def _default_weights(self) -> dict[BlockConstantAccessStrategy, float]:
        """默认策略权重"""
        return {
            BlockConstantAccessStrategy.DIRECT_TABLE: 0.20,
            BlockConstantAccessStrategy.GETTER_CALL: 0.25,
            BlockConstantAccessStrategy.UNIFIED_CALL: 0.15,
            BlockConstantAccessStrategy.INDEXED_CALL: 0.15,
            BlockConstantAccessStrategy.LOCAL_CACHE: 0.10,
            BlockConstantAccessStrategy.CLOSURE_WRAP: 0.05,
            BlockConstantAccessStrategy.METATABLE_ACCESS: 0.05,
            BlockConstantAccessStrategy.MULTI_STEP: 0.05,
        }

    def select_strategy(self) -> BlockConstantAccessStrategy:
        """根据权重随机选择策略"""
        if not self.enable_diversification:
            return BlockConstantAccessStrategy.GETTER_CALL

        if not self.rng:
            return BlockConstantAccessStrategy.GETTER_CALL

        strategies = list(self.strategy_weights.keys())
        weights = list(self.strategy_weights.values())

        if sum(weights) != 1.0:
            total = sum(weights)
            weights = [w / total for w in weights]

        return self.rng.choices(strategies, weights=weights, k=1)[0]


@dataclass
class ConstantAccessVariant:
    """
    单个常量的访问变体

    记录一个常量值的不同访问表达式。
    """
    value: Any           # 常量原始值
    value_type: str       # "string", "number", "boolean"
    index: int            # 在常量池中的索引
    pool_type: str        # "S", "N", "B"

    # 不同策略生成的表达式
    direct_expr: str = ""      # 直接表访问
    getter_expr: str = ""      # getter 调用
    unified_expr: str = ""     # 统一函数调用
    indexed_expr: str = ""     # 索引函数调用
    cache_expr: str = ""       # 局部缓存表达式
    closure_expr: str = ""     # 闭包包装表达式
    metatable_expr: str = ""   # 元表访问表达式
    multi_step_expr: str = ""  # 多步计算表达式


class BlockConstantAccessor:
    """
    Block 级常量访问器

    为每个 Block 生成该 Block 专用的常量访问代码和表达式。
    不同 Block 可使用不同策略，保持语义一致。
    """

    def __init__(
        self,
        pool: ConstantPool,
        config: BlockConstantAccessConfig | None = None,
    ):
        self.pool = pool
        self.config = config or BlockConstantAccessConfig()
        self._local_vars: dict[str, str] = {}  # 缓存已生成的局部变量
        self._closure_vars: dict[str, str] = {}  # 缓存闭包变量
        self._generated_header: list[str] = []  # 生成的局部变量声明

    def generate_block_access_code(
        self,
        block: CodeBlock,
        strategy: BlockConstantAccessStrategy | None = None,
    ) -> tuple[str, list[str]]:
        """
        为单个 Block 生成常量访问代码

        Args:
            block: 目标代码块
            strategy: 指定的访问策略，None 时随机选择

        Returns:
            (header_code, expression_mapping) 元组
            - header_code: 需要添加到 block 开头的局部变量声明
            - expression_mapping: 该 block 中使用的常量访问表达式映射
        """
        if strategy is None:
            strategy = self.config.select_strategy()

        header_lines: list[str] = []
        mappings: dict[str, str] = {}

        # 根据策略生成代码
        if strategy == BlockConstantAccessStrategy.DIRECT_TABLE:
            header_lines, mappings = self._generate_direct_table(block)
        elif strategy == BlockConstantAccessStrategy.GETTER_CALL:
            header_lines, mappings = self._generate_getter_call(block)
        elif strategy == BlockConstantAccessStrategy.UNIFIED_CALL:
            header_lines, mappings = self._generate_unified_call(block)
        elif strategy == BlockConstantAccessStrategy.INDEXED_CALL:
            header_lines, mappings = self._generate_indexed_call(block)
        elif strategy == BlockConstantAccessStrategy.LOCAL_CACHE:
            header_lines, mappings = self._generate_local_cache(block)
        elif strategy == BlockConstantAccessStrategy.CLOSURE_WRAP:
            header_lines, mappings = self._generate_closure_wrap(block)
        elif strategy == BlockConstantAccessStrategy.METATABLE_ACCESS:
            header_lines, mappings = self._generate_metatable_access(block)
        elif strategy == BlockConstantAccessStrategy.MULTI_STEP:
            header_lines, mappings = self._generate_multi_step(block)
        else:
            header_lines, mappings = self._generate_getter_call(block)

        return "\n".join(header_lines), mappings

    def _get_pool_prefix(self) -> str:
        """获取常量池前缀"""
        return self.pool.pool_prefix

    def _collect_block_constants(self, block: CodeBlock) -> list[ConstantAccessVariant]:
        """收集 block 中使用的常量"""
        variants: list[ConstantAccessVariant] = []

        for value, idx in self.pool.strings.items():
            v = ConstantAccessVariant(
                value=value,
                value_type="string",
                index=idx,
                pool_type="S",
            )
            self._build_all_expressions(v)
            variants.append(v)

        for value, idx in self.pool.numbers.items():
            v = ConstantAccessVariant(
                value=value,
                value_type="number",
                index=idx,
                pool_type="N",
            )
            self._build_all_expressions(v)
            variants.append(v)

        for value, idx in self.pool.booleans.items():
            v = ConstantAccessVariant(
                value=value,
                value_type="boolean",
                index=idx,
                pool_type="B",
            )
            self._build_all_expressions(v)
            variants.append(v)

        return variants

    def _build_all_expressions(self, variant: ConstantAccessVariant) -> None:
        """为变体构建所有可能的访问表达式"""
        prefix = self._get_pool_prefix()
        idx = variant.index
        pt = variant.pool_type

        # 直接表访问
        variant.direct_expr = f"{prefix}_{pt}[{idx}]"

        # 标准 getter 调用
        variant.getter_expr = f"{prefix}_{pt}get({idx})"

        # 统一函数调用
        variant.unified_expr = f"{prefix}_get('{pt}', {idx})"

        # 索引函数调用（如果存在）
        suffix = random_lua_identifier(self.config.rng, 'get') if self.config.rng else 'get'
        variant.indexed_expr = f"{prefix}_{suffix}('{pt}', {idx})"

        # 局部缓存（需要生成变量）
        var_name = f"{self.config.local_prefix}_{variant.value_type[0]}{idx}"
        variant.cache_expr = var_name

        # 闭包包装
        closure_var = f"_cl{idx}" if self.config.rng is None else random_lua_identifier(self.config.rng, f"_cl{idx}")
        variant.closure_expr = f"{closure_var}()"

        # 元表访问
        variant.metatable_expr = f"rawget({prefix}_{pt}, {idx})"

        # 多步计算
        step_var = f"_s{idx}" if self.config.rng is None else random_lua_identifier(self.config.rng, f"_s{idx}")
        variant.multi_step_expr = step_var

    def _generate_direct_table(self, block: CodeBlock) -> tuple[list[str], dict[str, str]]:
        """生成直接表访问策略"""
        header: list[str] = []
        mappings: dict[str, str] = {}
        prefix = self._get_pool_prefix()

        header.append("-- Direct table access strategy")

        # 直接使用表访问表达式
        for value, idx in self.pool.strings.items():
            mappings[f'"{value}"'] = f"{prefix}_S[{idx}]"

        for value, idx in self.pool.numbers.items():
            mappings[str(value)] = f"{prefix}_N[{idx}]"

        for value, idx in self.pool.booleans.items():
            mappings[str(value).lower()] = f"{prefix}_B[{idx}]"

        return header, mappings

    def _generate_getter_call(self, block: CodeBlock) -> tuple[list[str], dict[str, str]]:
        """生成 getter 调用策略"""
        header: list[str] = []
        mappings: dict[str, str] = {}
        prefix = self._get_pool_prefix()

        header.append("-- Getter call strategy")

        # 使用标准 getter 函数调用
        for value, idx in self.pool.strings.items():
            mappings[f'"{value}"'] = f"{prefix}_Sget({idx})"

        for value, idx in self.pool.numbers.items():
            mappings[str(value)] = f"{prefix}_Nget({idx})"

        for value, idx in self.pool.booleans.items():
            mappings[str(value).lower()] = f"{prefix}_Bget({idx})"

        return header, mappings

    def _generate_unified_call(self, block: CodeBlock) -> tuple[list[str], dict[str, str]]:
        """生成统一函数调用策略"""
        header: list[str] = []
        mappings: dict[str, str] = {}
        prefix = self._get_pool_prefix()

        header.append("-- Unified call strategy")

        # 使用统一入口函数
        for value, idx in self.pool.strings.items():
            mappings[f'"{value}"'] = f"{prefix}_get('S', {idx})"

        for value, idx in self.pool.numbers.items():
            mappings[str(value)] = f"{prefix}_get('N', {idx})"

        for value, idx in self.pool.booleans.items():
            mappings[str(value).lower()] = f"{prefix}_get('B', {idx})"

        return header, mappings

    def _generate_indexed_call(self, block: CodeBlock) -> tuple[list[str], dict[str, str]]:
        """生成索引函数调用策略"""
        header: list[str] = []
        mappings: dict[str, str] = {}
        prefix = self._get_pool_prefix()

        header.append("-- Indexed call strategy")

        suffix = random_lua_identifier(self.config.rng, 'get') if self.config.rng else 'get'

        # 使用带后缀的索引 getter
        for value, idx in self.pool.strings.items():
            mappings[f'"{value}"'] = f"{prefix}_{suffix}('S', {idx})"

        for value, idx in self.pool.numbers.items():
            mappings[str(value)] = f"{prefix}_{suffix}('N', {idx})"

        for value, idx in self.pool.booleans.items():
            mappings[str(value).lower()] = f"{prefix}_{suffix}('B', {idx})"

        return header, mappings

    def _generate_local_cache(self, block: CodeBlock) -> tuple[list[str], dict[str, str]]:
        """生成局部缓存策略"""
        header: list[str] = []
        mappings: dict[str, str] = {}
        prefix = self._get_pool_prefix()

        header.append("-- Local cache strategy")

        for value, idx in list(self.pool.strings.items())[:self.config.cache_size]:
            var_name = f"{self.config.local_prefix}_s{idx}"
            header.append(f"local {var_name} = {prefix}_S[{idx}]")
            mappings[f'"{value}"'] = var_name

        for value, idx in list(self.pool.numbers.items())[:min(self.config.cache_size, 2)]:
            var_name = f"{self.config.local_prefix}_n{idx}"
            header.append(f"local {var_name} = {prefix}_N[{idx}]")
            mappings[str(value)] = var_name

        return header, mappings

    def _generate_closure_wrap(self, block: CodeBlock) -> tuple[list[str], dict[str, str]]:
        """生成闭包包装策略"""
        header: list[str] = []
        mappings: dict[str, str] = {}
        prefix = self._get_pool_prefix()

        header.append("-- Closure wrap strategy")

        for value, idx in list(self.pool.strings.items())[:3]:
            cl_var = random_lua_identifier(self.config.rng, f"_cl{idx}") if self.config.rng else f"_cl{idx}"
            header.append(f"local {cl_var} = function() return {prefix}_S[{idx}] end")
            mappings[f'"{value}"'] = f"{cl_var}()"

        return header, mappings

    def _generate_metatable_access(self, block: CodeBlock) -> tuple[list[str], dict[str, str]]:
        """生成元表访问策略"""
        header: list[str] = []
        mappings: dict[str, str] = {}
        prefix = self._get_pool_prefix()

        header.append("-- Metatable access strategy")

        for value, idx in list(self.pool.strings.items())[:2]:
            mappings[f'"{value}"'] = f"rawget({prefix}_S, {idx})"

        for value, idx in list(self.pool.numbers.items())[:2]:
            mappings[str(value)] = f"rawget({prefix}_N, {idx})"

        return header, mappings

    def _generate_multi_step(self, block: CodeBlock) -> tuple[list[str], dict[str, str]]:
        """生成多步计算策略"""
        header: list[str] = []
        mappings: dict[str, str] = {}
        prefix = self._get_pool_prefix()

        header.append("-- Multi-step strategy")

        for value, idx in list(self.pool.strings.items())[:2]:
            step_var = random_lua_identifier(self.config.rng, f"_s{idx}") if self.config.rng else f"_s{idx}"
            header.append(f"local {step_var} = {prefix}_S[{idx}]")
            mappings[f'"{value}"'] = step_var

        for value, idx in list(self.pool.numbers.items())[:2]:
            step_var = random_lua_identifier(self.config.rng, f"_n{idx}") if self.config.rng else f"_n{idx}"
            header.append(f"local {step_var} = {prefix}_N[{idx}]")
            mappings[str(value)] = step_var

        return header, mappings


class BlockConstantAccessManager:
    """
    Block 级常量访问管理器

    统一管理所有 Block 的常量访问策略，为每个 Block 分配和生成访问代码。
    """

    def __init__(
        self,
        pool: ConstantPool,
        blocks: list[CodeBlock],
        config: BlockConstantAccessConfig | None = None,
    ):
        self.pool = pool
        self.blocks = blocks
        self.config = config or BlockConstantAccessConfig()
        self.accessor = BlockConstantAccessor(pool, self.config)

        # 每个 block 分配的策略
        self.block_strategies: dict[int, BlockConstantAccessStrategy] = {}

        # 每个 block 生成的代码头
        self.block_headers: dict[int, list[str]] = {}

        # 每个 block 的表达式映射
        self.block_mappings: dict[int, dict[str, str]] = {}

        self._assign_strategies()

    def _assign_strategies(self) -> None:
        """为每个 block 分配访问策略"""
        for block in self.blocks:
            strategy = self.config.select_strategy()
            self.block_strategies[block.block_id] = strategy

            header, mappings = self.accessor.generate_block_access_code(block, strategy)
            self.block_headers[block.block_id] = header.split("\n") if header else []
            self.block_mappings[block.block_id] = mappings

    def apply_to_blocks(self) -> None:
        """将访问代码应用到所有 blocks"""
        for block in self.blocks:
            block_id = block.block_id
            header_lines = self.block_headers.get(block_id, [])
            mappings = self.block_mappings.get(block_id, {})

            # 构建头部代码
            if header_lines:
                header_code = "\n".join(header_lines)
                # 注入到 block 内容开头
                if block.content.strip():
                    block.content = header_code + "\n" + block.content
                else:
                    block.content = header_code

            # 替换内容中的常量访问
            for literal, expr in mappings.items():
                block.content = block.content.replace(literal, expr)

    def get_strategy_for_block(self, block_id: int) -> BlockConstantAccessStrategy | None:
        """获取指定 block 的策略"""
        return self.block_strategies.get(block_id)

    def get_statistics(self) -> dict:
        """获取策略分布统计"""
        stats: dict[str, int] = {}
        for strategy in self.block_strategies.values():
            name = strategy.value
            stats[name] = stats.get(name, 0) + 1
        return stats


@dataclass
class CodeGenerationOptions:
    """代码生成选项"""
    # Block 排序
    block_order: BlockOrderStrategy = BlockOrderStrategy.SEQUENTIAL
    enable_order_randomization: bool = True

    # 常量访问
    constant_access: ConstantAccessStrategy = ConstantAccessStrategy.SEPARATE_GETTERS
    enable_constant_randomization: bool = True

    # 结构变体
    enable_structure_variants: bool = True
    variant_probability: float = 0.3

    # 冗余注入
    inject_dead_blocks: bool = False
    dead_block_probability: float = 0.2

    # 元数据
    include_comments: bool = False
    include_metadata: bool = True

    # 命名
    naming_scheme: str = "random"


class BlockOrderRandomizer:
    """
    Block 排序随机化器

    支持多种 block 输出顺序策略
    """

    @staticmethod
    def sequential_order(program: BlockProgram) -> list[int]:
        """顺序排列"""
        return list(program.execution_order)

    @staticmethod
    def shuffled_order(program: BlockProgram, rng: random.Random) -> list[int]:
        """随机打乱"""
        order = list(program.execution_order)
        rng.shuffle(order)
        return order

    @staticmethod
    def interleaved_order(program: BlockProgram, rng: random.Random) -> list[int]:
        """交错排列：首尾交替"""
        order = list(program.execution_order)
        if len(order) <= 2:
            return order

        result = []
        left, right = 0, len(order) - 1
        flip = True

        while left <= right:
            if flip:
                result.append(order[left])
                left += 1
            else:
                result.append(order[right])
                right -= 1
            flip = not flip

        return result

    @staticmethod
    def grouped_order(program: BlockProgram, rng: random.Random) -> list[int]:
        """分组排列：按 block 类型分组"""
        order = list(program.execution_order)

        groups: dict[str, list[int]] = {}
        for bid in order:
            block = program.get_block(bid)
            if block:
                btype = block.block_type or "unknown"
                if btype not in groups:
                    groups[btype] = []
                groups[btype].append(bid)

        result = []
        for bids in groups.values():
            rng.shuffle(bids)
            result.extend(bids)

        return result

    @staticmethod
    def reversed_groups_order(program: BlockProgram, rng: random.Random) -> list[int]:
        """反向分组：大块在前小块在后"""
        order = list(program.execution_order)

        large = []
        small = []
        for bid in order:
            block = program.get_block(bid)
            if block and block.content:
                lines = len(block.content.split("\n"))
                if lines > 3:
                    large.append(bid)
                else:
                    small.append(bid)
            else:
                small.append(bid)

        rng.shuffle(large)
        rng.shuffle(small)
        return large + small

    @classmethod
    def apply_order(cls, program: BlockProgram, rng: random.Random | None, strategy: BlockOrderStrategy) -> list[int]:
        """应用排序策略"""
        if strategy == BlockOrderStrategy.SEQUENTIAL:
            return cls.sequential_order(program)
        elif strategy == BlockOrderStrategy.SHUFFLED:
            return cls.shuffled_order(program, rng) if rng else cls.sequential_order(program)
        elif strategy == BlockOrderStrategy.INTERLEAVED:
            return cls.interleaved_order(program, rng) if rng else cls.sequential_order(program)
        elif strategy == BlockOrderStrategy.GROUPED:
            return cls.grouped_order(program, rng) if rng else cls.sequential_order(program)
        elif strategy == BlockOrderStrategy.REVERSED_GROUPS:
            return cls.reversed_groups_order(program, rng) if rng else cls.sequential_order(program)
        return cls.sequential_order(program)


class ConstantAccessGenerator:
    """
    常量访问生成器

    支持多种常量访问实现方式
    """

    @staticmethod
    def generate_direct_access(pool: ConstantPool) -> str:
        """生成直接访问代码"""
        return pool.generate_pool_table()

    @staticmethod
    def generate_separate_getters(pool: ConstantPool, rng: random.Random | None = None) -> str:
        """生成独立 getter 函数"""
        return pool.generate_pool_table()

    @staticmethod
    def generate_unified_getter(pool: ConstantPool, rng: random.Random | None = None) -> str:
        """生成统一 getter 函数"""
        return pool.generate_unified_pool_table(rng)

    @staticmethod
    def generate_indexed_getter(pool: ConstantPool, rng: random.Random | None = None) -> str:
        """生成索引 getter 函数"""
        lines = []
        prefix = pool.pool_prefix

        lines.append(f"local {prefix}_S = {{")
        for value, idx in sorted(pool.strings.items(), key=lambda x: x[1]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f"    [{idx}] = \"{escaped}\",")
        lines.append("}")

        lines.append(f"local {prefix}_N = {{")
        for value, idx in sorted(pool.numbers.items(), key=lambda x: x[1]):
            lines.append(f"    [{idx}] = {value},")
        lines.append("}")

        lines.append(f"local {prefix}_B = {{")
        for value, idx in sorted(pool.booleans.items(), key=lambda x: x[1]):
            lines.append(f"    [{idx}] = {str(value).lower()},")
        lines.append("}")

        suffix = f"_{random_lua_identifier(rng, 'get')}" if rng else "_get"
        lines.append(f"local function {prefix}{suffix}(k, t)")
        lines.append(f"    t = t or 'N'")
        lines.append(f"    if t == 'S' then return {prefix}_S[k]")
        lines.append(f"    elseif t == 'N' then return {prefix}_N[k]")
        lines.append(f"    elseif t == 'B' then return {prefix}_B[k] end")
        lines.append(f"end")

        return "\n".join(lines)

    @staticmethod
    def generate_conditional_getter(pool: ConstantPool, rng: random.Random | None = None) -> str:
        """生成条件 getter 函数"""
        lines = []
        prefix = pool.pool_prefix

        lines.append(f"local {prefix}_S = {{")
        for value, idx in sorted(pool.strings.items(), key=lambda x: x[1]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f"    [{idx}] = \"{escaped}\",")
        lines.append("}")

        lines.append(f"local {prefix}_N = {{")
        for value, idx in sorted(pool.numbers.items(), key=lambda x: x[1]):
            lines.append(f"    [{idx}] = {value},")
        lines.append("}")

        lines.append(f"local {prefix}_B = {{")
        for value, idx in sorted(pool.booleans.items(), key=lambda x: x[1]):
            lines.append(f"    [{idx}] = {str(value).lower()},")
        lines.append("}")

        suffix = f"_{random_lua_identifier(rng, 'cget')}" if rng else "_cget"
        guard_var = f"_c{rng.randint(100, 999)}" if rng else "_c"
        lines.append(f"local {guard_var} = 1")
        lines.append(f"local function {prefix}{suffix}(k, t)")
        lines.append(f"    {guard_var} = ({guard_var} % 1)")
        lines.append(f"    if t == 'S' then return {prefix}_S[k]")
        lines.append(f"    elseif t == 'N' then return {prefix}_N[k]")
        lines.append(f"    elseif t == 'B' then return {prefix}_B[k] end")
        lines.append(f"end")

        return "\n".join(lines)

    @staticmethod
    def generate_wrapped_getter(pool: ConstantPool, rng: random.Random | None = None) -> str:
        """生成包装 getter 函数"""
        lines = []
        prefix = pool.pool_prefix

        lines.append(f"local {prefix}_S = {{")
        for value, idx in sorted(pool.strings.items(), key=lambda x: x[1]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f"    [{idx}] = \"{escaped}\",")
        lines.append("}")

        lines.append(f"local {prefix}_N = {{")
        for value, idx in sorted(pool.numbers.items(), key=lambda x: x[1]):
            lines.append(f"    [{idx}] = {value},")
        lines.append("}")

        lines.append(f"local {prefix}_B = {{")
        for value, idx in sorted(pool.booleans.items(), key=lambda x: x[1]):
            lines.append(f"    [{idx}] = {str(value).lower()},")
        lines.append("}")

        suffix = f"_{random_lua_identifier(rng, 'wget')}" if rng else "_wget"
        lines.append(f"local function {prefix}{suffix}(k, t)")
        lines.append(f"    do")
        lines.append(f"        local _ = nil")
        lines.append(f"    end")
        lines.append(f"    if t == 'S' then return {prefix}_S[k]")
        lines.append(f"    elseif t == 'N' then return {prefix}_N[k]")
        lines.append(f"    elseif t == 'B' then return {prefix}_B[k] end")
        lines.append(f"end")

        return "\n".join(lines)

    @classmethod
    def generate(cls, pool: ConstantPool, rng: random.Random | None, strategy: ConstantAccessStrategy) -> str:
        """根据策略生成常量访问代码"""
        generators = {
            ConstantAccessStrategy.DIRECT: lambda p, r: cls.generate_direct_access(p),
            ConstantAccessStrategy.SEPARATE_GETTERS: lambda p, r: cls.generate_separate_getters(p, r),
            ConstantAccessStrategy.UNIFIED_GETTER: lambda p, r: cls.generate_unified_getter(p, r),
            ConstantAccessStrategy.INDEXED_GETTER: lambda p, r: cls.generate_indexed_getter(p, r),
            ConstantAccessStrategy.CONDITIONAL_GETTER: lambda p, r: cls.generate_conditional_getter(p, r),
            ConstantAccessStrategy.WRAPPED_GETTER: lambda p, r: cls.generate_wrapped_getter(p, r),
        }

        gen = generators.get(strategy, lambda p, r: cls.generate_separate_getters(p, r))
        return gen(pool, rng)


class UnifiedCodeGenerator:
    """
    统一代码生成器

    整合所有随机化策略，生成结构多样但语义一致的代码
    """

    def __init__(self, program: BlockProgram, rng: random.Random | None = None):
        self.program = program
        self.rng = rng
        self.options = CodeGenerationOptions()
        self.constant_pool = None
        self._generated_order: list[int] = []

    def set_options(self, options: CodeGenerationOptions) -> None:
        """设置生成选项"""
        self.options = options

    def randomize_options(self) -> CodeGenerationOptions:
        """随机化生成选项"""
        if not self.rng:
            return self.options

        orders = list(BlockOrderStrategy)
        access = list(ConstantAccessStrategy)
        naming = ["sequential", "random", "semantic"]

        self.options = CodeGenerationOptions(
            block_order=self.rng.choice(orders) if self.options.enable_order_randomization else self.options.block_order,
            constant_access=self.rng.choice(access) if self.options.enable_constant_randomization else self.options.constant_access,
            enable_structure_variants=self.rng.random() > 0.5 if self.options.enable_structure_variants else False,
            inject_dead_blocks=self.rng.random() > 0.7 if self.options.enable_structure_variants else False,
            include_comments=self.rng.random() > 0.6,
            include_metadata=self.rng.random() > 0.3,
            naming_scheme=self.rng.choice(naming) if self.options.enable_structure_variants else self.options.naming_scheme,
        )
        return self.options

    def _get_block_order(self) -> list[int]:
        """获取 block 排序"""
        return BlockOrderRandomizer.apply_order(
            self.program, self.rng, self.options.block_order
        )

    def _generate_block_function(self, block: CodeBlock, index: int) -> list[str]:
        """生成单个 block 函数"""
        prefix = f"_blk{random_lua_identifier(self.rng, 'f')}" if self.rng else "_blk"

        if self.options.naming_scheme == "sequential":
            func_name = f"{prefix}_{index}"
        elif self.options.naming_scheme == "random":
            func_name = f"{prefix}_{random_lua_identifier(self.rng, '')}"
        else:
            func_name = f"{prefix}_{block.block_type}_{index}"

        lines = [f"local function {func_name}()"]

        if block.content.strip():
            lines.append(indent_lua(block.content.strip(), 4))
        else:
            lines.append("    do end")

        next_id = block.next_id
        if self.options.include_comments:
            lines.append(f"    -- next: {next_id}")

        if next_id is not None:
            lines.append(f"    return {next_id}")
        else:
            lines.append("    return")

        lines.append("end")
        return lines

    def _generate_program_table(self, order: list[int]) -> list[str]:
        """生成程序表"""
        lines = []
        prefix = f"_tbl{random_lua_identifier(self.rng, 't')}" if self.rng else "_tbl"

        lines.append(f"local {prefix} = {{}}")
        lines.append(f"for i, bid in ipairs({{")

        for bid in order:
            lines.append(f"    {bid},")

        lines.append(f"}}) do")
        lines.append(f"    {prefix}[i] = bid")
        lines.append(f"end")

        return lines

    def generate(self, pool: ConstantPool | None = None) -> tuple[str, dict]:
        """
        生成随机化代码

        Args:
            pool: 常量池（可选）

        Returns:
            (generated_code, statistics) 元组
        """
        lines: list[str] = []

        # 头部注释
        if self.options.include_comments:
            lines.append("-- Generated code")
            lines.append("")

        # 获取 block 排序
        order = self._get_block_order()
        self._generated_order = order

        # 生成常量池（如果提供）
        if pool and self.constant_pool is None:
            self.constant_pool = pool
            const_code = ConstantAccessGenerator.generate(
                pool, self.rng, self.options.constant_access
            )
            lines.append(const_code)
            lines.append("")

        # 生成 block 函数
        block_map: dict[int, str] = {}
        for idx, bid in enumerate(order, 1):
            block = self.program.get_block(bid)
            if block:
                block_lines = self._generate_block_function(block, idx)
                block_map[bid] = block_lines[0].split("(")[0].replace("local function ", "").strip()

                if self.options.inject_dead_blocks and self.rng and self.rng.random() < self.options.dead_block_probability:
                    dead = RedundantStructureGenerator(self.rng, RedundantStructureConfig(enabled=True))
                    dead_content, _ = dead.generate_dead_block()
                    lines.append(f"-- dead block {bid}")
                    lines.append(dead_content)
                    lines.append("")

                lines.extend(block_lines)
                lines.append("")

        # 生成程序表
        if self.options.include_metadata:
            table_lines = self._generate_program_table(order)
            lines.extend(table_lines)

        stats = {
            "options": {
                "block_order": self.options.block_order.value,
                "constant_access": self.options.constant_access.value,
                "naming_scheme": self.options.naming_scheme,
                "include_comments": self.options.include_comments,
                "include_metadata": self.options.include_metadata,
            },
            "generated_blocks": len(order),
            "block_order": order,
            "constant_pool": pool.get_statistics() if pool else None
        }

        return "\n".join(lines), stats

    def generate_variants(self, count: int = 3) -> list[tuple[str, dict]]:
        """生成多个变体"""
        variants = []

        for _ in range(count):
            self.randomize_options()
            code, stats = self.generate(self.constant_pool)
            variants.append((code, stats))

        return variants


# ===== 便捷函数 =====


def create_unified_generator(
    program: BlockProgram,
    rng: random.Random,
    enable_randomization: bool = True
) -> UnifiedCodeGenerator:
    """
    创建统一代码生成器

    Args:
        program: 目标程序
        rng: 随机数生成器
        enable_randomization: 是否启用随机化

    Returns:
        UnifiedCodeGenerator 实例
    """
    generator = UnifiedCodeGenerator(program, rng)

    if not enable_randomization:
        generator.options.enable_order_randomization = False
        generator.options.enable_constant_randomization = False
        generator.options.enable_structure_variants = False

    return generator


def generate_randomized_code(
    program: BlockProgram,
    rng: random.Random,
    pool: ConstantPool | None = None,
    options: CodeGenerationOptions | None = None
) -> tuple[str, dict]:
    """
    便捷函数：生成随机化代码

    Args:
        program: 目标程序
        rng: 随机数生成器
        pool: 常量池（可选）
        options: 生成选项（可选）

    Returns:
        (code, statistics) 元组
    """
    generator = UnifiedCodeGenerator(program, rng)

    if options:
        generator.set_options(options)
    else:
        generator.randomize_options()

    return generator.generate(pool)


def demonstrate_randomization(program: BlockProgram, rng: random.Random) -> list[tuple[str, dict]]:
    """
    演示多种随机化变体

    Args:
        program: 目标程序
        rng: 随机数生成器

    Returns:
        变体列表
    """
    generator = UnifiedCodeGenerator(program, rng)

    print("Block 排序策略:")
    for order_type in BlockOrderStrategy:
        order = BlockOrderRandomizer.apply_order(program, rng, order_type)
        print(f"  {order_type.value}: {order}")

    print("\n常量访问策略:")
    for access_type in ConstantAccessStrategy:
        print(f"  {access_type.value}")

    return generator.generate_variants(3)



# ===== 冗余结构增强系统 =====


class RedundantStructureType(Enum):
    """冗余结构类型"""
    DEAD_BLOCK = "dead_block"              # 死代码块
    SKIP_BLOCK = "skip_block"              # 跳过块
    TRAP_BLOCK = "trap_block"              # 陷阱块
    DECOY_BLOCK = "decoy_block"           # 诱饵块
    NOP_BLOCK = "nop_block"               # 空操作块
    GUARD_BLOCK = "guard_block"           # 守卫块
    LOOP_TRAP = "loop_trap"               # 循环陷阱
    BRANCH_TRAP = "branch_trap"           # 分支陷阱


@dataclass
class RedundantStructureConfig:
    """冗余结构配置"""
    enabled: bool = False
    max_structures: int = 5
    inject_probability: float = 0.3
    structure_types: list[RedundantStructureType] | None = None


class DeadCodeStructure:
    """死代码结构生成器"""

    @staticmethod
    def generate_block(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成死代码块"""
        patterns = [
            ("if false then\n    error('unreachable')\nend", "if_false"),
            ("repeat\n    break\nuntil false", "repeat_break"),
            ("while false do\n    break\nend", "while_break"),
            ("do\n    local _d = false\n    if _d then error() end\nend", "local_false"),
        ]

        if rng:
            content, style = rng.choice(patterns)
            if "_d" in content:
                chars = string.ascii_lowercase
                suffix = "".join(rng.choice(chars) for _ in range(4))
                content = content.replace("_d", f"_d{suffix}")
        else:
            content, style = patterns[0]

        return content, {"type": "dead_block", "style": style, "executed": False}

    @staticmethod
    def generate_branch() -> tuple[str, dict]:
        """生成死代码分支"""
        content = "if false then\n    -- never\nelse\n    -- always\nend"
        return content, {"type": "dead_branch", "condition": "false", "executed": False}


class SkipBlockStructure:
    """跳过块结构生成器"""

    @staticmethod
    def generate_block(rng: random.Random | None = None, next_id: int | None = None) -> tuple[str, dict]:
        """生成跳过块"""
        if rng:
            patterns = [
                "do end",
                "(function() end)()",
                "pcall(function() end)",
                "select('#', nil)",
                "next({})",
            ]
            content = rng.choice(patterns)
        else:
            content = "do end"

        info = {"type": "skip_block", "next_id": next_id, "no_effect": True}

        if next_id is not None:
            if rng and rng.random() > 0.5:
                content += f"\nreturn {next_id}"
                info["returns_next"] = True
            else:
                content += "\nreturn"
                info["returns_next"] = True

        return content, info

    @staticmethod
    def generate_guard_skip(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成守卫跳过块"""
        if rng:
            patterns = [
                "local _g = true\nif not _g then\n    error('guard')\nend",
                "local _ok = 1\nif _ok == 0 then\n    _ok = 1\nend",
            ]
            content = rng.choice(patterns)
            content = content.replace("_g", f"_g{rng.randint(100, 999)}")
            content = content.replace("_ok", f"_ok{rng.randint(100, 999)}")
        else:
            content = "local _g = true\nif not _g then\n    error('guard')\nend"

        return content, {"type": "guard_skip", "always_passes": True}


class TrapBlockStructure:
    """陷阱块结构生成器"""

    @staticmethod
    def generate_block(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成陷阱块"""
        if rng:
            patterns = [
                "if nil then\n    error('trap')\nend",
                "if 1 ~= 1 then\n    error('impossible')\nend",
                "assert(true, 'trap')",
                "assert(1 == 1, 'trap')",
            ]
            content = rng.choice(patterns)
        else:
            content = "if nil then\n    error('trap')\nend"

        return content, {"type": "trap_block", "always_passes": True}

    @staticmethod
    def generate_decoy_trap(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成诱饵陷阱"""
        if rng:
            patterns = [
                "local _t = false\nif not _t then\n    _t = not _t\nend",
                "local _s = 0\n_s = _s\nif _s then\n    _s = _s\nend",
            ]
            content = rng.choice(patterns)
            for prefix in ["_t", "_s"]:
                if prefix in content:
                    suffix = "".join(rng.choice(string.ascii_lowercase) for _ in range(4))
                    content = content.replace(prefix, f"{prefix}{suffix}")
        else:
            content = "local _t = false\nif not _t then\n    _t = not _t\nend"

        return content, {"type": "decoy_trap", "no_effect": True}


class ConstantBranchStructure:
    """常量分支结构生成器"""

    @staticmethod
    def generate_always_true(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成始终为 true 的分支"""
        if rng:
            patterns = [
                "if true then\n    -- always\nend",
                "if 1 == 1 then\n    -- always\nend",
                "if 'a' == 'a' then\n    -- always\nend",
            ]
            content = rng.choice(patterns)
        else:
            content = "if true then\n    -- always\nend"

        return content, {"type": "constant_true", "condition_always": True}

    @staticmethod
    def generate_always_false(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成始终为 false 的分支"""
        if rng:
            patterns = [
                "if false then\n    -- never\nend",
                "if 1 ~= 1 then\n    -- never\nend",
                "if nil then\n    -- never\nend",
            ]
            content = rng.choice(patterns)
        else:
            content = "if false then\n    -- never\nend"

        return content, {"type": "constant_false", "condition_always": False}

    @staticmethod
    def generate_conditional_block(
        rng: random.Random | None = None,
        var_name: str | None = None
    ) -> tuple[str, dict]:
        """生成条件块"""
        if var_name is None:
            var_name = "_c" + ("".join(random.Random().choice(string.ascii_lowercase) for _ in range(4)) if rng else "cond")

        if rng:
            patterns = [
                f"local {var_name} = true\nif not {var_name} then\n    {var_name} = true\nend",
                f"local {var_name} = 1\nif {var_name} == 0 then\n    {var_name} = 1\nend",
                f"local {var_name} = nil\nif {var_name} then\n    {var_name} = nil\nend",
            ]
            content = rng.choice(patterns)
        else:
            content = f"local {var_name} = true\nif not {var_name} then\n    {var_name} = true\nend"

        return content, {"type": "conditional_block", "variable": var_name}


class NopBlockStructure:
    """空操作块结构生成器"""

    @staticmethod
    def generate_block(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成空操作块"""
        if rng:
            patterns = [
                "do end",
                "(function() end)()",
                "pcall(function() end)",
                "setmetatable({}, {})",
                "table.concat({})",
            ]
            count = rng.randint(1, 2)
            lines = [rng.choice(patterns) for _ in range(count)]
            content = "\n".join(lines)
        else:
            content = "do end"

        return content, {"type": "nop_block", "no_effect": True}

    @staticmethod
    def generate_self_operation(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成自操作块"""
        if rng:
            var = f"_x{rng.randint(100, 999)}"
            patterns = [
                f"local {var} = 0\n{var} = {var}",
                f"local {var} = nil\n{var} = {var}",
                f"local {var} = {{}}\n{var} = {var}",
            ]
            content = rng.choice(patterns)
        else:
            content = "local _x = 0\n_x = _x"

        return content, {"type": "self_op", "no_effect": True}


class RedundantStructureGenerator:
    """
    冗余结构生成器

    生成不会被执行的 block 或条件恒定的分支
    """

    def __init__(self, rng: random.Random | None = None, config: RedundantStructureConfig | None = None):
        self.rng = rng
        self.config = config if config else RedundantStructureConfig()
        self._id_counter = [0]
        self.generated_structures: list[dict] = []

    def _gen_id(self) -> int:
        self._id_counter[0] += 1
        return self._id_counter[0]

    def generate_structure(
        self,
        struct_type: RedundantStructureType | None = None
    ) -> tuple[str, dict]:
        """
        生成冗余结构

        Args:
            struct_type: 结构类型，None 表示随机选择

        Returns:
            (lua_code, metadata) 元组
        """
        if not self.config.enabled:
            return "", {}

        if struct_type is None:
            if self.config.structure_types:
                struct_type = self.rng.choice(self.config.structure_types) if self.rng else self.config.structure_types[0]
            else:
                types = list(RedundantStructureType)
                struct_type = self.rng.choice(types) if self.rng else types[0]

        generators = {
            RedundantStructureType.DEAD_BLOCK: DeadCodeStructure.generate_block,
            RedundantStructureType.SKIP_BLOCK: lambda rng: SkipBlockStructure.generate_block(rng),
            RedundantStructureType.TRAP_BLOCK: TrapBlockStructure.generate_block,
            RedundantStructureType.DECOY_BLOCK: TrapBlockStructure.generate_decoy_trap,
            RedundantStructureType.NOP_BLOCK: NopBlockStructure.generate_block,
            RedundantStructureType.GUARD_BLOCK: SkipBlockStructure.generate_guard_skip,
            RedundantStructureType.LOOP_TRAP: lambda rng: DeadCodeStructure.generate_block(rng),
            RedundantStructureType.BRANCH_TRAP: ConstantBranchStructure.generate_always_false,
        }

        gen = generators.get(struct_type, DeadCodeStructure.generate_block)
        content, info = gen(self.rng)
        info["structure_id"] = self._gen_id()
        info["structure_type"] = struct_type.value

        self.generated_structures.append(info)
        return content, info

    def generate_dead_block(self) -> tuple[str, dict]:
        """生成死代码块"""
        return self.generate_structure(RedundantStructureType.DEAD_BLOCK)

    def generate_skip_block(self, next_id: int | None = None) -> tuple[str, dict]:
        """生成跳过块"""
        content, info = SkipBlockStructure.generate_block(self.rng, next_id)
        info["structure_id"] = self._gen_id()
        self.generated_structures.append(info)
        return content, info

    def generate_constant_branch(
        self,
        always_true: bool = True
    ) -> tuple[str, dict]:
        """生成常量分支"""
        if always_true:
            content, info = ConstantBranchStructure.generate_always_true(self.rng)
        else:
            content, info = ConstantBranchStructure.generate_always_false(self.rng)
        info["structure_id"] = self._gen_id()
        self.generated_structures.append(info)
        return content, info

    def generate_conditional_block(self) -> tuple[str, dict]:
        """生成条件块"""
        content, info = ConstantBranchStructure.generate_conditional_block(self.rng)
        info["structure_id"] = self._gen_id()
        self.generated_structures.append(info)
        return content, info

    def generate_nop_block(self) -> tuple[str, dict]:
        """生成空操作块"""
        return self.generate_structure(RedundantStructureType.NOP_BLOCK)

    def generate_guard_block(self) -> tuple[str, dict]:
        """生成守卫块"""
        return self.generate_structure(RedundantStructureType.GUARD_BLOCK)

    def generate_multiple_structures(self, count: int | None = None) -> list[tuple[str, dict]]:
        """生成多个冗余结构"""
        if count is None:
            count = self.rng.randint(1, self.config.max_structures) if self.rng else 1

        structures = []
        for _ in range(count):
            if self.rng and self.rng.random() > self.config.inject_probability:
                break
            content, info = self.generate_structure()
            if content:
                structures.append((content, info))

        return structures

    def inject_into_block(self, block_content: str, block_id: int | None = None) -> str:
        """
        将冗余结构注入到 block 内容中

        Args:
            block_content: 原始 block 内容
            block_id: block ID（可选）

        Returns:
            注入后的内容
        """
        if not self.config.enabled:
            return block_content

        if self.rng and self.rng.random() > self.config.inject_probability:
            return block_content

        structure, info = self.generate_structure()
        if not structure:
            return block_content

        if self.rng:
            position = self.rng.randint(0, 2)
        else:
            position = 0

        if position == 0:
            return structure + "\n" + block_content
        elif position == 1:
            lines = block_content.split("\n")
            if len(lines) > 1:
                mid = len(lines) // 2
                return "\n".join(lines[:mid]) + "\n" + structure + "\n" + "\n".join(lines[mid:])
            return block_content + "\n" + structure
        else:
            return block_content + "\n" + structure

    def inject_into_function(self, func_body: str) -> str:
        """将冗余结构注入到函数体中"""
        if not self.config.enabled:
            return func_body

        if self.rng and self.rng.random() > self.config.inject_probability:
            return func_body

        structure, info = self.generate_structure()
        if not structure:
            return func_body

        if self.rng:
            position = self.rng.randint(0, 2)
        else:
            position = 0

        if position == 0:
            return structure + "\n" + func_body
        elif position == 1:
            lines = func_body.split("\n")
            if len(lines) > 2:
                insert_pos = self.rng.randint(1, len(lines) - 1) if self.rng else 1
                return "\n".join(lines[:insert_pos]) + "\n" + structure + "\n" + "\n".join(lines[insert_pos:])
            return func_body + "\n" + structure
        else:
            return func_body + "\n" + structure

    def wrap_in_block(self, next_id: int | None = None) -> CodeBlock:
        """将冗余结构包装为 CodeBlock"""
        content, info = self.generate_structure()
        if not content:
            content = "do end"

        if next_id is not None:
            content += f"\nreturn {next_id}"

        return CodeBlock(
            block_id=-1000 - self._gen_id(),
            content=content,
            block_type="redundant",
            next_id=next_id,
            branches={},
            auxiliary_paths=[],
            dependencies=[],
            metadata={
                "is_redundant": True,
                "redundant_info": info
            }
        )

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            "enabled": self.config.enabled,
            "generated_count": len(self.generated_structures),
            "structures": self.generated_structures
        }


# ===== 便捷函数 =====


def generate_redundant_structure(
    rng: random.Random,
    struct_type: str = "random",
    enabled: bool = True
) -> str:
    """
    便捷函数：生成冗余结构

    Args:
        rng: 随机数生成器
        struct_type: 结构类型 ("dead", "skip", "constant_true", "constant_false", "nop", "random")
        enabled: 是否启用

    Returns:
        生成的 Lua 代码
    """
    config = RedundantStructureConfig(enabled=enabled)
    generator = RedundantStructureGenerator(rng, config)

    type_map = {
        "dead": RedundantStructureType.DEAD_BLOCK,
        "skip": RedundantStructureType.SKIP_BLOCK,
        "constant_true": None,
        "constant_false": None,
        "nop": RedundantStructureType.NOP_BLOCK,
        "random": None,
    }

    if struct_type == "constant_true":
        content, _ = generator.generate_constant_branch(always_true=True)
    elif struct_type == "constant_false":
        content, _ = generator.generate_constant_branch(always_true=False)
    else:
        content, _ = generator.generate_structure(type_map.get(struct_type))

    return content


def inject_redundant_to_block(
    block_content: str,
    rng: random.Random,
    probability: float = 0.3,
    enabled: bool = True
) -> str:
    """
    便捷函数：注入冗余结构到 block

    Args:
        block_content: 原始 block 内容
        rng: 随机数生成器
        probability: 注入概率
        enabled: 是否启用

    Returns:
        注入后的内容
    """
    config = RedundantStructureConfig(
        enabled=enabled,
        inject_probability=probability
    )
    generator = RedundantStructureGenerator(rng, config)
    return generator.inject_into_block(block_content)


def create_redundant_block(
    rng: random.Random,
    struct_type: str = "dead",
    next_id: int | None = None
) -> CodeBlock:
    """
    便捷函数：创建冗余 CodeBlock

    Args:
        rng: 随机数生成器
        struct_type: 结构类型
        next_id: 下一个 block ID

    Returns:
        CodeBlock 实例
    """
    config = RedundantStructureConfig(enabled=True)
    generator = RedundantStructureGenerator(rng, config)
    return generator.wrap_in_block(next_id)


# ===== 增强调度系统 =====


class DispatchStrategy(Enum):
    """调度策略类型"""
    DIRECT = "direct"                  # 直接调度（原有）
    STATE_MACHINE = "state_machine"    # 状态机调度
    KEY_LOOKUP = "key_lookup"         # 键查找调度
    OFFSET_CALC = "offset_calc"        # 偏移计算调度
    INDIRECT = "indirect"              # 间接调度


class DispatchVariant(Enum):
    """
    调度变体类型

    定义不同的调度实现方式，每个变体都保持语义一致但结构不同。
    """
    # 基本循环调度
    BASIC_LOOP = "basic_loop"
    REPEAT_LOOP = "repeat_loop"
    FOR_LOOP = "for_loop"

    # 函数递归调度
    TAIL_RECURSION = "tail_recursion"
    WRAPPER_RECURSION = "wrapper_recursion"

    # 表驱动调度
    TABLE_LOOKUP = "table_lookup"
    META_TABLE = "meta_table"
    INDEX_FUNCTION = "index_function"

    # 状态转移调度
    STATE_TABLE = "state_table"
    TRANSITION_MATRIX = "transition_matrix"

    # 计算调度
    HASH_COMPUTE = "hash_compute"
    XOR_TRANSFORM = "xor_transform"
    BIT_MANIPULATION = "bit_manipulation"

    # 组合调度
    HYBRID_LOOP = "hybrid_loop"
    PIPELINE_STAGE = "pipeline_stage"


class DispatcherVariantConfig:
    """
    调度变体配置

    控制调度器变体的生成参数。
    """

    def __init__(
        self,
        rng: random.Random | None = None,
        enable_diversification: bool = True,
        variant_weights: dict[DispatchVariant, float] | None = None,
        obfuscate_vars: bool = True,
        add_redundant_ops: bool = True,
    ):
        self.rng = rng
        self.enable_diversification = enable_diversification
        self.variant_weights = variant_weights or self._default_weights()
        self.obfuscate_vars = obfuscate_vars
        self.add_redundant_ops = add_redundant_ops

        # 运行时变量名
        self.pc_var = "_pc" if rng is None else random_lua_identifier(rng, "_pc")
        self.tbl_var = "_tbl" if rng is None else random_lua_identifier(rng, "_tbl")
        self.state_var = "_st" if rng is None else random_lua_identifier(rng, "_st")
        self.key_var = "_k" if rng is None else random_lua_identifier(rng, "_k")
        self.cache_var = "_ch" if rng is None else random_lua_identifier(rng, "_ch")

    def _default_weights(self) -> dict[DispatchVariant, float]:
        """默认变体权重"""
        return {
            # 循环类
            DispatchVariant.BASIC_LOOP: 0.15,
            DispatchVariant.REPEAT_LOOP: 0.05,
            DispatchVariant.FOR_LOOP: 0.05,

            # 递归类
            DispatchVariant.TAIL_RECURSION: 0.10,
            DispatchVariant.WRAPPER_RECURSION: 0.05,

            # 表驱动类
            DispatchVariant.TABLE_LOOKUP: 0.15,
            DispatchVariant.META_TABLE: 0.05,
            DispatchVariant.INDEX_FUNCTION: 0.05,

            # 状态转移类
            DispatchVariant.STATE_TABLE: 0.10,
            DispatchVariant.TRANSITION_MATRIX: 0.05,

            # 计算类
            DispatchVariant.HASH_COMPUTE: 0.05,
            DispatchVariant.XOR_TRANSFORM: 0.05,
            DispatchVariant.BIT_MANIPULATION: 0.05,

            # 组合类
            DispatchVariant.HYBRID_LOOP: 0.05,
            DispatchVariant.PIPELINE_STAGE: 0.05,
        }

    def select_variant(self) -> DispatchVariant:
        """根据权重随机选择变体"""
        if not self.enable_diversification:
            return DispatchVariant.BASIC_LOOP

        if not self.rng:
            return DispatchVariant.BASIC_LOOP

        variants = list(self.variant_weights.keys())
        weights = list(self.variant_weights.values())

        if sum(weights) != 1.0:
            total = sum(weights)
            weights = [w / total for w in weights]

        return self.rng.choices(variants, weights=weights, k=1)[0]


class DispatchVariantGenerator:
    """
    调度变体生成器

    根据不同变体类型生成对应的调度代码实现。
    每个变体保持相同的执行语义但使用不同的代码结构。
    """

    def __init__(
        self,
        program: BlockProgram,
        config: DispatcherVariantConfig | None = None,
    ):
        self.program = program
        self.config = config or DispatcherVariantConfig()

    def generate(self, variant: DispatchVariant | None = None) -> str:
        """生成指定变体的调度代码"""
        if variant is None:
            variant = self.config.select_variant()

        generators = {
            # 循环类
            DispatchVariant.BASIC_LOOP: self._generate_basic_loop,
            DispatchVariant.REPEAT_LOOP: self._generate_repeat_loop,
            DispatchVariant.FOR_LOOP: self._generate_for_loop,

            # 递归类
            DispatchVariant.TAIL_RECURSION: self._generate_tail_recursion,
            DispatchVariant.WRAPPER_RECURSION: self._generate_wrapper_recursion,

            # 表驱动类
            DispatchVariant.TABLE_LOOKUP: self._generate_table_lookup,
            DispatchVariant.META_TABLE: self._generate_meta_table,
            DispatchVariant.INDEX_FUNCTION: self._generate_index_function,

            # 状态转移类
            DispatchVariant.STATE_TABLE: self._generate_state_table,
            DispatchVariant.TRANSITION_MATRIX: self._generate_transition_matrix,

            # 计算类
            DispatchVariant.HASH_COMPUTE: self._generate_hash_compute,
            DispatchVariant.XOR_TRANSFORM: self._generate_xor_transform,
            DispatchVariant.BIT_MANIPULATION: self._generate_bit_manipulation,

            # 组合类
            DispatchVariant.HYBRID_LOOP: self._generate_hybrid_loop,
            DispatchVariant.PIPELINE_STAGE: self._generate_pipeline_stage,
        }

        gen = generators.get(variant, self._generate_basic_loop)
        return gen()

    # === 循环类实现 ===

    def _generate_basic_loop(self) -> str:
        """基本 while 循环调度"""
        pc = self.config.pc_var
        tbl = self.config.tbl_var
        st = self.config.state_var

        lines = [f"local {pc} = {self.program.entry_block_id}"]

        if self.config.add_redundant_ops:
            lines.append(f"local {st} = 0")

        lines.append(f"while {pc} do")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if not block then error('Invalid block: '..tostring({pc})) end")
        lines.append(f"    if not block.fn then error('Missing fn: '..tostring({pc})) end")

        if self.config.add_redundant_ops:
            lines.append(f"    {st} = ({st} + 1) - 1")

        lines.append(f"    {pc} = block.fn()")
        lines.append("end")

        return "\n".join(lines)

    def _generate_repeat_loop(self) -> str:
        """Repeat-until 循环调度"""
        pc = self.config.pc_var
        tbl = self.config.tbl_var
        st = self.config.state_var

        lines = [f"local {pc} = {self.program.entry_block_id}"]

        if self.config.add_redundant_ops:
            lines.append(f"local {st} = 0")

        lines.append("repeat")
        lines.append(f"    if not {pc} then break end")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if block and block.fn then")

        if self.config.add_redundant_ops:
            lines.append(f"        {st} = ({st} + 1) % 1")

        lines.append(f"        {pc} = block.fn()")
        lines.append(f"    else {pc} = nil end")
        lines.append(f"until not {pc}")

        return "\n".join(lines)

    def _generate_for_loop(self) -> str:
        """For 循环调度（伪循环）"""
        pc = self.config.pc_var
        tbl = self.config.tbl_var

        order = self.program.execution_order
        count = len(order)

        lines = [f"local {pc} = {self.program.entry_block_id}"]
        lines.append(f"for _ = 1, {count} + 10 do")
        lines.append(f"    if not {pc} then break end")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if not block or not block.fn then break end")
        lines.append(f"    {pc} = block.fn()")
        lines.append("end")

        return "\n".join(lines)

    # === 递归类实现 ===

    def _generate_tail_recursion(self) -> str:
        """尾递归调度"""
        pc = self.config.pc_var
        tbl = self.config.tbl_var
        st = self.config.state_var
        func_name = random_lua_identifier(self.config.rng, "_dispatch") if self.config.rng else "_dispatch"

        lines = [f"local {func_name}"]

        if self.config.add_redundant_ops:
            lines.append(f"local {st} = 0")

        lines.append(f"{func_name} = function({pc})")
        lines.append(f"    if not {pc} then return end")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if not block then return end")
        lines.append(f"    if not block.fn then return end")

        if self.config.add_redundant_ops:
            lines.append(f"    {st} = ({st} + 1) - 1")

        lines.append(f"    {func_name}(block.fn())")
        lines.append("end")

        lines.append(f"{func_name}({self.program.entry_block_id})")

        return "\n".join(lines)

    def _generate_wrapper_recursion(self) -> str:
        """包装器递归调度"""
        pc = self.config.pc_var
        tbl = self.config.tbl_var
        st = self.config.state_var
        cache = self.config.cache_var
        func_name = random_lua_identifier(self.config.rng, "_exec") if self.config.rng else "_exec"

        lines = []

        if self.config.add_redundant_ops:
            lines.append(f"local {st} = 0")

        lines.append(f"local {cache} = nil")
        lines.append(f"local function {func_name}({pc})")
        lines.append(f"    if not {pc} then return end")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if not block then return end")
        lines.append(f"    if not block.fn then return end")

        if self.config.add_redundant_ops:
            lines.append(f"    {st} = ({st} + 1) - 1")

        lines.append(f"    {cache} = block.fn()")
        lines.append(f"    if {cache} then {func_name}({cache}) end")
        lines.append("end")

        lines.append(f"{func_name}({self.program.entry_block_id})")

        return "\n".join(lines)

    # === 表驱动类实现 ===

    def _generate_table_lookup(self) -> str:
        """表查找调度"""
        pc = self.config.pc_var
        tbl = self.config.tbl_var
        mp = f"_mp{random_lua_identifier(self.config.rng, '')}" if self.config.rng else "_mp"

        lines = [f"local {mp} = {{}}"]
        for bid, nxt in sorted(self._build_state_map().items()):
            lines.append(f"{mp}[{bid}] = {nxt}")

        lines.append(f"local {pc} = {self.program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if not block or not block.fn then break end")
        lines.append(f"    local next_id = block.fn()")
        lines.append(f"    {pc} = {mp}[next_id] or next_id")
        lines.append("end")

        return "\n".join(lines)

    def _generate_meta_table(self) -> str:
        """元表调度"""
        pc = self.config.pc_var
        tbl = self.config.tbl_var
        mt = f"_mt{random_lua_identifier(self.config.rng, '')}" if self.config.rng else "_mt"
        st = self.config.state_var

        lines = [f"local {mt} = setmetatable({{}}, {{__index = function(t, k) return rawget(t, k) end}})"]
        lines.append(f"local {st} = 0")

        lines.append(f"local {pc} = {self.program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = {tbl}[{pc}] or {mt}[{pc}]")
        lines.append(f"    if not block or not block.fn then break end")
        lines.append(f"    {st} = ({st} + 1) - 1")
        lines.append(f"    {pc} = block.fn()")
        lines.append("end")

        return "\n".join(lines)

    def _generate_index_function(self) -> str:
        """索引函数调度"""
        pc = self.config.pc_var
        tbl = self.config.tbl_var
        idx = random_lua_identifier(self.config.rng, "_idx") if self.config.rng else "_idx"

        lines = [f"local function {idx}({pc})"]
        lines.append(f"    return {tbl}[{pc}].fn()")
        lines.append("end")

        lines.append(f"local {pc} = {self.program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if not block then break end")
        lines.append(f"    {pc} = {idx}({pc})")
        lines.append("end")

        return "\n".join(lines)

    # === 状态转移类实现 ===

    def _generate_state_table(self) -> str:
        """状态表调度"""
        pc = self.config.pc_var
        tbl = self.config.tbl_var
        st = self.config.state_var
        st_tbl = f"_st{random_lua_identifier(self.config.rng, '')}" if self.config.rng else "_st_tbl"

        lines = [f"local {st} = 0"]
        lines.append(f"local {st_tbl} = {{}}")

        for bid, nxt in sorted(self._build_state_map().items()):
            lines.append(f"{st_tbl}[{bid}] = {nxt}")

        lines.append(f"local {pc} = {self.program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if not block or not block.fn then break end")
        lines.append(f"    {st} = ({st} + 1) - 1")
        lines.append(f"    local result = block.fn()")
        lines.append(f"    {pc} = {st_tbl}[result] or result")
        lines.append("end")

        return "\n".join(lines)

    def _generate_transition_matrix(self) -> str:
        """转移矩阵调度"""
        pc = self.config.pc_var
        tbl = self.config.tbl_var
        mx = f"_mx{random_lua_identifier(self.config.rng, '')}" if self.config.rng else "_mx"

        order = self.program.execution_order
        lines = [f"local {mx} = {{}}"]

        for i, bid in enumerate(order):
            if i < len(order) - 1:
                next_bid = order[i + 1]
                lines.append(f"{mx}[{bid}] = {{{next_bid}}}")

        lines.append(f"local {pc} = {self.program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if not block or not block.fn then break end")
        lines.append(f"    local result = block.fn()")
        lines.append(f"    {pc} = result")
        lines.append("end")

        return "\n".join(lines)

    # === 计算类实现 ===

    def _generate_hash_compute(self) -> str:
        """哈希计算调度"""
        pc = self.config.pc_var
        tbl = self.config.tbl_var
        h = random_lua_identifier(self.config.rng, "_h") if self.config.rng else "_h"
        st = self.config.state_var

        lines = [f"local {st} = 0"]
        lines.append(f"local {h} = 0")

        lines.append(f"local {pc} = {self.program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if not block or not block.fn then break end")
        lines.append(f"    {st} = ({st} + 1) - 1")

        if self.config.add_redundant_ops:
            lines.append(f"    {h} = ({pc} * 31 + {st}) % 1000000")

        lines.append(f"    {pc} = block.fn()")
        lines.append("end")

        return "\n".join(lines)

    def _generate_xor_transform(self) -> str:
        """异或变换调度"""
        pc = self.config.pc_var
        tbl = self.config.tbl_var
        k = self.config.key_var
        st = self.config.state_var

        lines = [f"local {k} = 12345"]
        lines.append(f"local {st} = 0")

        lines.append(f"local {pc} = {self.program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if not block or not block.fn then break end")
        lines.append(f"    {st} = bit.bxor({st}, {k})")
        lines.append(f"    {pc} = block.fn()")
        lines.append("end")

        return "\n".join(lines)

    def _generate_bit_manipulation(self) -> str:
        """位操作调度"""
        pc = self.config.pc_var
        tbl = self.config.tbl_var
        mask = random_lua_identifier(self.config.rng, "_m") if self.config.rng else "_m"

        lines = [f"local {mask} = 0xFFFF"]

        lines.append(f"local {pc} = {self.program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if not block or not block.fn then break end")
        lines.append(f"    {pc} = bit.band(block.fn(), {mask})")
        lines.append("end")

        return "\n".join(lines)

    # === 组合类实现 ===

    def _generate_hybrid_loop(self) -> str:
        """混合循环调度"""
        pc = self.config.pc_var
        tbl = self.config.tbl_var
        st = self.config.state_var
        cache = self.config.cache_var

        lines = [f"local {st} = 0"]
        lines.append(f"local {cache} = nil")

        lines.append(f"local {pc} = {self.program.entry_block_id}")
        lines.append("repeat")
        lines.append(f"    if not {pc} then break end")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if not block or not block.fn then break end")
        lines.append(f"    {st} = ({st} + 1) % 1")
        lines.append(f"    {cache} = block.fn()")
        lines.append(f"    {pc} = {cache}")
        lines.append(f"until not {pc}")

        return "\n".join(lines)

    def _generate_pipeline_stage(self) -> str:
        """流水线阶段调度"""
        pc = self.config.pc_var
        tbl = self.config.tbl_var
        stg = f"_stg{random_lua_identifier(self.config.rng, '')}" if self.config.rng else "_stg"
        st = self.config.state_var

        lines = [f"local {st} = 0"]
        lines.append(f"local {stg} = 1")

        lines.append(f"local {pc} = {self.program.entry_block_id}")
        lines.append("repeat")
        lines.append(f"    if not {pc} then break end")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if not block or not block.fn then break end")
        lines.append(f"    {st} = ({st} + {stg}) - {stg}")
        lines.append(f"    {stg} = {stg} % 100")
        lines.append(f"    {pc} = block.fn()")
        lines.append(f"until not {pc}")

        return "\n".join(lines)

    def _build_state_map(self) -> dict[int, int]:
        """构建状态映射"""
        state_map: dict[int, int] = {}
        for block in self.program.blocks:
            if block.next_id is not None:
                state_map[block.block_id] = block.next_id
        return state_map


class DispatchVariantFactory:
    """
    调度变体工厂

    负责根据配置创建和选择调度器变体。
    """

    def __init__(
        self,
        program: BlockProgram,
        rng: random.Random | None = None,
    ):
        self.program = program
        self.rng = rng
        self.config = DispatcherVariantConfig(rng=rng)
        self.generator = DispatchVariantGenerator(program, self.config)

    def create_config(
        self,
        enable_diversification: bool = True,
        variant_weights: dict[DispatchVariant, float] | None = None,
        obfuscate_vars: bool = True,
    ) -> DispatcherVariantConfig:
        """创建变体配置"""
        return DispatcherVariantConfig(
            rng=self.rng,
            enable_diversification=enable_diversification,
            variant_weights=variant_weights,
            obfuscate_vars=obfuscate_vars,
        )

    def select_and_generate(self, variant: DispatchVariant | None = None) -> str:
        """选择变体并生成代码"""
        if variant is None:
            variant = self.config.select_variant()

        self.generator.config = self.config
        return self.generator.generate(variant)

    def generate_all_variants(self) -> dict[DispatchVariant, str]:
        """生成所有变体的代码"""
        results = {}
        for variant in DispatchVariant:
            self.generator.config = self.config
            results[variant] = self.generator.generate(variant)
        return results

    def get_statistics(self, variant: DispatchVariant | None = None) -> dict:
        """获取统计信息"""
        if variant:
            return {
                "variant": variant.value,
                "total_blocks": len(self.program.blocks),
                "execution_order": len(self.program.execution_order),
            }

        stats = {"total_variants": len(DispatchVariant)}
        for v in DispatchVariant:
            stats[f"variant_{v.value}_available"] = True

        return stats


class DiversifiedDispatcher:
    """
    多样化调度器

    整合调度变体系统，提供统一的调度接口。
    可以随机选择不同实现方式。
    """

    def __init__(
        self,
        program: BlockProgram,
        rng: random.Random | None = None,
    ):
        self.program = program
        self.rng = rng
        self.factory = DispatchVariantFactory(program, rng)
        self.selected_variant: DispatchVariant | None = None
        self._generated_code: str = ""

    def generate(
        self,
        variant: DispatchVariant | None = None,
        enable_diversification: bool = True,
    ) -> str:
        """生成调度代码"""
        if variant is None and enable_diversification:
            variant = self.factory.config.select_variant()

        self.selected_variant = variant
        self._generated_code = self.factory.select_and_generate(variant)
        return self._generated_code

    def generate_with_strategy(
        self,
        strategy: DispatchStrategy,
    ) -> str:
        """根据策略生成调度代码"""
        variant_map = {
            DispatchStrategy.DIRECT: DispatchVariant.BASIC_LOOP,
            DispatchStrategy.STATE_MACHINE: DispatchVariant.STATE_TABLE,
            DispatchStrategy.KEY_LOOKUP: DispatchVariant.TABLE_LOOKUP,
            DispatchStrategy.OFFSET_CALC: DispatchVariant.TRANSITION_MATRIX,
            DispatchStrategy.INDIRECT: DispatchVariant.TAIL_RECURSION,
        }

        variant = variant_map.get(strategy, DispatchVariant.BASIC_LOOP)
        return self.generate(variant=variant, enable_diversification=False)

    def get_generated_code(self) -> str:
        """获取已生成的代码"""
        return self._generated_code

    def get_selected_variant(self) -> DispatchVariant | None:
        """获取选中的变体"""
        return self.selected_variant

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            "selected_variant": self.selected_variant.value if self.selected_variant else None,
            "total_blocks": len(self.program.blocks),
            "execution_order": len(self.program.execution_order),
            "entry_block_id": self.program.entry_block_id,
        }


@dataclass
class DispatcherConfig:
    """调度器配置"""
    strategy: DispatchStrategy = DispatchStrategy.DIRECT
    enable_state_var: bool = True
    enable_key_var: bool = True
    enable_mapping: bool = True
    state_var_name: str = "_st"
    key_var_name: str = "_key"
    mapping_var_name: str = "_mp"


class BlockDispatcher:
    """
    Block 调度器

    封装 block 调度的核心逻辑，支持多种调度策略
    """

    def __init__(self, program: BlockProgram, rng: random.Random | None = None, config: DispatcherConfig | None = None):
        self.program = program
        self.rng = rng
        self.config = config if config else DispatcherConfig()
        self.pc_var = f"_pc{rng.randint(1000, 9999)}" if rng else "_pc"
        self.tbl_var = f"_tbl{rng.randint(1000, 9999)}" if rng else "_tbl"
        self._build_state_map()

    def _build_state_map(self) -> None:
        """构建状态映射表"""
        self.state_map: dict[int, int] = {}
        self.reverse_map: dict[int, list[int]] = {}

        for block in self.program.blocks:
            if block.next_id is not None:
                self.state_map[block.block_id] = block.next_id
                if block.next_id not in self.reverse_map:
                    self.reverse_map[block.next_id] = []
                self.reverse_map[block.next_id].append(block.block_id)

    def generate_base_table(self) -> str:
        """生成基础 block 表"""
        lines = []
        lines.append(f"local {self.tbl_var} = {{}}")

        order = self.program.execution_order
        for idx, bid in enumerate(order):
            lines.append(f"{self.tbl_var}[{idx + 1}] = {bid}")

        return "\n".join(lines)

    def generate_state_machine_dispatcher(self) -> str:
        """生成状态机调度器"""
        lines = []
        pc = self.pc_var
        tbl = self.tbl_var
        st = self.config.state_var_name

        lines.append(f"local {st} = 0")
        lines.append(f"local {pc} = {self.program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if not block then error('Invalid: '..{pc}) end")
        lines.append(f"    if not block.fn then error('No fn: '..{pc}) end")
        lines.append(f"    {st} = ({st} + 1) % 1")
        lines.append(f"    {pc} = block.fn()")
        lines.append("end")

        return "\n".join(lines)

    def generate_key_lookup_dispatcher(self) -> str:
        """生成键查找调度器"""
        lines = []
        pc = self.pc_var
        tbl = self.tbl_var
        key = self.config.key_var_name
        mp = self.config.mapping_var_name

        lines.append(f"local {mp} = {{}}")
        for bid, nxt in sorted(self.state_map.items()):
            lines.append(f"{mp}[{bid}] = {nxt}")

        lines.append(f"local {key} = 0")
        lines.append(f"local {pc} = {self.program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if not block then error('Invalid: '..{pc}) end")
        lines.append(f"    if not block.fn then error('No fn: '..{pc}) end")
        lines.append(f"    {key} = ({key} + 0) - 0")
        lines.append(f"    {pc} = {mp}[block.fn()] or block.fn()")
        lines.append("end")

        return "\n".join(lines)

    def generate_offset_calc_dispatcher(self) -> str:
        """生成偏移计算调度器"""
        lines = []
        pc = self.pc_var
        tbl = self.tbl_var
        off = self.config.mapping_var_name

        order = self.program.execution_order
        lines.append(f"local {off} = {{")
        for idx, bid in enumerate(order):
            next_bid = order[idx + 1] if idx < len(order) - 1 else 0
            lines.append(f"    [{bid}] = {next_bid},")
        lines.append("}")

        lines.append(f"local {pc} = {self.program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if not block then error('Invalid: '..{pc}) end")
        lines.append(f"    if not block.fn then error('No fn: '..{pc}) end")
        lines.append(f"    local raw = block.fn()")
        lines.append(f"    {pc} = {off}[raw] or raw")
        lines.append("end")

        return "\n".join(lines)

    def generate_indirect_dispatcher(self) -> str:
        """生成间接调度器"""
        lines = []
        pc = self.pc_var
        tbl = self.tbl_var
        st = self.config.state_var_name
        key = self.config.key_var_name

        lines.append(f"local {st} = 0")
        lines.append(f"local {key} = 0")
        lines.append(f"local {pc} = {self.program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if not block then error('Invalid: '..{pc}) end")
        lines.append(f"    if not block.fn then error('No fn: '..{pc}) end")
        lines.append(f"    {st} = ({st} + 1) - 1")
        lines.append(f"    {key} = ({key} + 0) % 1")
        lines.append(f"    {pc} = block.fn()")
        lines.append("end")

        return "\n".join(lines)

    def generate_dispatcher(self) -> str:
        """生成调度器代码"""
        if self.config.strategy == DispatchStrategy.DIRECT:
            return self._generate_direct_dispatcher()
        elif self.config.strategy == DispatchStrategy.STATE_MACHINE:
            return self.generate_state_machine_dispatcher()
        elif self.config.strategy == DispatchStrategy.KEY_LOOKUP:
            return self.generate_key_lookup_dispatcher()
        elif self.config.strategy == DispatchStrategy.OFFSET_CALC:
            return self.generate_offset_calc_dispatcher()
        elif self.config.strategy == DispatchStrategy.INDIRECT:
            return self.generate_indirect_dispatcher()
        return self._generate_direct_dispatcher()

    def _generate_direct_dispatcher(self) -> str:
        """生成直接调度器"""
        lines = []
        pc = self.pc_var
        tbl = self.tbl_var

        lines.append(f"local {pc} = {self.program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = {tbl}[{pc}]")
        lines.append(f"    if not block then error('Invalid: '..{pc}) end")
        lines.append(f"    if not block.fn then error('No fn: '..{pc}) end")
        lines.append(f"    {pc} = block.fn()")
        lines.append("end")

        return "\n".join(lines)

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            "strategy": self.config.strategy.value,
            "total_blocks": len(self.program.blocks),
            "state_mappings": len(self.state_map),
            "pc_var": self.pc_var,
            "tbl_var": self.tbl_var,
        }


class UnifiedDispatchSystem:
    """
    统一调度系统

    整合多种调度策略，提供统一的调度接口
    """

    def __init__(self, program: BlockProgram, rng: random.Random | None = None):
        self.program = program
        self.rng = rng
        self.dispatcher: BlockDispatcher | None = None
        self._generated_code: str = ""

    def create_dispatcher(self, config: DispatcherConfig) -> BlockDispatcher:
        """创建调度器"""
        self.dispatcher = BlockDispatcher(self.program, self.rng, config)
        return self.dispatcher

    def generate_complete_program(self, config: DispatcherConfig) -> str:
        """生成完整的程序代码"""
        if self.dispatcher is None:
            self.create_dispatcher(config)

        lines = []

        lines.append("-- Block Table")
        lines.append(self.dispatcher.generate_base_table())
        lines.append("")

        lines.append("-- Block Functions")
        for idx, bid in enumerate(self.program.execution_order):
            block = self.program.get_block(bid)
            if block:
                func_name = f"_fn{idx + 1}"
                lines.append(f"local function {func_name}()")
                if block.content.strip():
                    for ln in block.content.strip().split("\n"):
                        lines.append(f"    {ln}")
                next_id = block.next_id if block.next_id else ""
                lines.append(f"    return {next_id}")
                lines.append("end")
                lines.append(f"{self.dispatcher.tbl_var}[{bid}] = function() return {func_name}() end")
                lines.append("")

        lines.append("-- Dispatcher")
        lines.append(self.dispatcher.generate_dispatcher())

        self._generated_code = "\n".join(lines)
        return self._generated_code

    def generate_with_intermediates(self, config: DispatcherConfig) -> str:
        """生成带中间变量的程序"""
        if self.dispatcher is None:
            self.create_dispatcher(config)

        lines = []

        st = config.state_var_name
        key = config.key_var_name
        mp = config.mapping_var_name

        lines.append(f"local {st} = 0")
        lines.append(f"local {key} = 0")
        lines.append("")

        lines.append("-- Block Table")
        lines.append(self.dispatcher.generate_base_table())
        lines.append("")

        if config.enable_mapping:
            lines.append(f"-- State Mapping")
            lines.append(f"local {mp} = {{}}")
            for bid, nxt in sorted(self.dispatcher.state_map.items()):
                lines.append(f"{mp}[{bid}] = {nxt}")
            lines.append("")

        lines.append("-- Block Functions")
        for idx, bid in enumerate(self.program.execution_order):
            block = self.program.get_block(bid)
            if block:
                func_name = f"_fn{idx + 1}"
                lines.append(f"local function {func_name}()")
                if block.content.strip():
                    for ln in block.content.strip().split("\n"):
                        lines.append(f"    {ln}")
                lines.append(f"    {st} = ({st} + 1) - 1")
                lines.append(f"    {key} = ({key} + 0) - 0")
                next_id = block.next_id if block.next_id else ""
                lines.append(f"    return {next_id}")
                lines.append("end")
                lines.append(f"{self.dispatcher.tbl_var}[{bid}] = function() return {func_name}() end")
                lines.append("")

        lines.append("-- Dispatcher")
        if config.strategy == DispatchStrategy.KEY_LOOKUP:
            lines.append(f"local {self.dispatcher.pc_var} = {self.program.entry_block_id}")
            lines.append(f"while {self.dispatcher.pc_var} do")
            lines.append(f"    local block = {self.dispatcher.tbl_var}[{self.dispatcher.pc_var}]")
            lines.append(f"    if block then")
            lines.append(f"        local raw = block()")
            lines.append(f"        {self.dispatcher.pc_var} = {mp}[raw] or raw")
            lines.append(f"    else break end")
            lines.append("end")
        else:
            lines.append(self.dispatcher.generate_dispatcher())

        self._generated_code = "\n".join(lines)
        return self._generated_code

    def get_generated_code(self) -> str:
        """获取已生成的代码"""
        return self._generated_code

    def get_statistics(self) -> dict:
        """获取统计信息"""
        if self.dispatcher:
            return self.dispatcher.get_statistics()
        return {}


# ===== 便捷函数 =====


def create_dispatcher(
    program: BlockProgram,
    rng: random.Random,
    strategy: str = "direct"
) -> BlockDispatcher:
    """
    创建 Block 调度器

    Args:
        program: 目标程序
        rng: 随机数生成器
        strategy: 调度策略 ("direct", "state", "key", "offset", "indirect")

    Returns:
        BlockDispatcher 实例
    """
    strategy_map = {
        "direct": DispatchStrategy.DIRECT,
        "state": DispatchStrategy.STATE_MACHINE,
        "key": DispatchStrategy.KEY_LOOKUP,
        "offset": DispatchStrategy.OFFSET_CALC,
        "indirect": DispatchStrategy.INDIRECT,
    }

    config = DispatcherConfig(
        strategy=strategy_map.get(strategy, DispatchStrategy.DIRECT)
    )

    return BlockDispatcher(program, rng, config)


def generate_dispatched_program(
    program: BlockProgram,
    rng: random.Random,
    strategy: str = "key"
) -> str:
    """
    生成带调度器的程序

    Args:
        program: 目标程序
        rng: 随机数生成器
        strategy: 调度策略

    Returns:
        生成的 Lua 代码
    """
    strategy_map = {
        "direct": DispatchStrategy.DIRECT,
        "state": DispatchStrategy.STATE_MACHINE,
        "key": DispatchStrategy.KEY_LOOKUP,
        "offset": DispatchStrategy.OFFSET_CALC,
        "indirect": DispatchStrategy.INDIRECT,
    }

    config = DispatcherConfig(
        strategy=strategy_map.get(strategy, DispatchStrategy.KEY_LOOKUP),
        enable_state_var=True,
        enable_key_var=True,
        enable_mapping=True
    )

    system = UnifiedDispatchSystem(program, rng)
    return system.generate_with_intermediates(config)


def demo_dispatch_strategies(program: BlockProgram, rng: random.Random) -> dict[str, str]:
    """
    演示所有调度策略

    Args:
        program: 目标程序
        rng: 随机数生成器

    Returns:
        策略名到代码的映射
    """
    results = {}

    for strategy in DispatchStrategy:
        config = DispatcherConfig(strategy=strategy)
        system = UnifiedDispatchSystem(program, rng)
        code = system.generate_complete_program(config)
        results[strategy.value] = code

    return results
# ===== 增强多样化常量访问系统 =====


class ConstantAccessType(Enum):
    """常量访问类型枚举"""
    # 基础访问
    DIRECT_TABLE = "direct_table"              # 直接表访问
    NAMED_GETTER = "named_getter"              # 命名 getter
    INDEXED_ACCESS = "indexed_access"          # 索引访问

    # 变换访问
    XOR_TRANSFORM = "xor_transform"            # 异或变换
    OFFSET_TRANSFORM = "offset_transform"      # 偏移变换
    REVERSE_TRANSFORM = "reverse_transform"    # 反向变换

    # 包装访问
    CLOSURE_WRAP = "closure_wrap"              # 闭包包装
    METATABLE_WRAP = "metatable_wrap"          # 元表包装
    CONDITIONAL_WRAP = "conditional_wrap"     # 条件包装

    # 组合访问
    STATE_COMBINED = "state_combined"          # 状态组合
    PIPELINE = "pipeline"                      # 管道访问
    CACHED = "cached"                         # 缓存访问


@dataclass
class ConstantAccessConfig:
    """常量访问配置"""
    access_type: ConstantAccessType = ConstantAccessType.NAMED_GETTER
    enable_randomization: bool = True
    pool_prefix: str = "_c"
    xor_key: int = 0x2A
    offset_base: int = 100
    enable_state_var: bool = False
    state_var_name: str = "_cs"


class DiverseConstantGenerator:
    """
    多样化常量生成器

    支持多种常量访问方式，每次生成可选择不同策略
    """

    def __init__(self, pool: ConstantPool, rng: random.Random | None = None, config: ConstantAccessConfig | None = None):
        self.pool = pool
        self.rng = rng
        self.config = config if config else ConstantAccessConfig()
        self._generated_code: str = ""
        self._accessors: dict[str, str] = {}

    def generate(self, access_type: ConstantAccessType | None = None) -> str:
        """
        生成常量访问代码

        Args:
            access_type: 访问类型，None 表示随机选择

        Returns:
            生成的 Lua 代码
        """
        if access_type is None:
            if self.config.enable_randomization and self.rng:
                types = list(ConstantAccessType)
                access_type = self.rng.choice(types)
            else:
                access_type = self.config.access_type

        generators = {
            ConstantAccessType.DIRECT_TABLE: self._gen_direct_table,
            ConstantAccessType.NAMED_GETTER: self._gen_named_getter,
            ConstantAccessType.INDEXED_ACCESS: self._gen_indexed_access,
            ConstantAccessType.XOR_TRANSFORM: self._gen_xor_transform,
            ConstantAccessType.OFFSET_TRANSFORM: self._gen_offset_transform,
            ConstantAccessType.REVERSE_TRANSFORM: self._gen_reverse_transform,
            ConstantAccessType.CLOSURE_WRAP: self._gen_closure_wrap,
            ConstantAccessType.METATABLE_WRAP: self._gen_metatable_wrap,
            ConstantAccessType.CONDITIONAL_WRAP: self._gen_conditional_wrap,
            ConstantAccessType.STATE_COMBINED: self._gen_state_combined,
            ConstantAccessType.PIPELINE: self._gen_pipeline,
            ConstantAccessType.CACHED: self._gen_cached,
        }

        gen = generators.get(access_type, self._gen_named_getter)
        self._generated_code = gen()
        return self._generated_code

    def _gen_direct_table(self) -> str:
        """生成直接表访问代码"""
        lines = []
        prefix = self.config.pool_prefix

        lines.append(f"local {prefix}_S = {{}}")
        for value, idx in sorted(self.pool.strings.items(), key=lambda x: x[1]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f"{prefix}_S[{idx}] = \"{escaped}\"")

        lines.append(f"local {prefix}_N = {{}}")
        for value, idx in sorted(self.pool.numbers.items(), key=lambda x: x[1]):
            lines.append(f"{prefix}_N[{idx}] = {value}")

        lines.append(f"local {prefix}_B = {{}}")
        for value, idx in sorted(self.pool.booleans.items(), key=lambda x: x[1]):
            lines.append(f"{prefix}_B[{idx}] = {str(value).lower()}")

        return "\n".join(lines)

    def _gen_named_getter(self) -> str:
        """生成命名 getter 代码"""
        lines = []
        prefix = self.config.pool_prefix

        lines.append(f"local {prefix}_S = {{}}")
        for value, idx in sorted(self.pool.strings.items(), key=lambda x: x[1]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f"{prefix}_S[{idx}] = \"{escaped}\"")

        lines.append(f"local {prefix}_N = {{}}")
        for value, idx in sorted(self.pool.numbers.items(), key=lambda x: x[1]):
            lines.append(f"{prefix}_N[{idx}] = {value}")

        lines.append(f"local {prefix}_B = {{}}")
        for value, idx in sorted(self.pool.booleans.items(), key=lambda x: x[1]):
            lines.append(f"{prefix}_B[{idx}] = {str(value).lower()}")

        suffix = f"_{random_lua_identifier(self.rng, 'gs')}" if self.rng else "_Sget"
        lines.append(f"local function {prefix}{suffix}(i) return {prefix}_S[i] end")
        suffix = f"_{random_lua_identifier(self.rng, 'gn')}" if self.rng else "_Nget"
        lines.append(f"local function {prefix}{suffix}(i) return {prefix}_N[i] end")
        suffix = f"_{random_lua_identifier(self.rng, 'gb')}" if self.rng else "_Bget"
        lines.append(f"local function {prefix}{suffix}(i) return {prefix}_B[i] end")

        self._accessors = {
            "string": f"{prefix}{suffix}",
            "number": f"{prefix}{suffix}",
            "boolean": f"{prefix}{suffix}",
        }

        return "\n".join(lines)

    def _gen_indexed_access(self) -> str:
        """生成索引访问代码"""
        lines = []
        prefix = self.config.pool_prefix

        lines.append(f"local {prefix}_D = {{}}")
        for value, idx in sorted(self.pool.strings.items(), key=lambda x: x[1]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f"{prefix}_D[{idx}] = \"{escaped}\"")

        for value, idx in sorted(self.pool.numbers.items(), key=lambda x: x[1]):
            lines.append(f"{prefix}_D[{idx + 1000}] = {value}")

        for value, idx in sorted(self.pool.booleans.items(), key=lambda x: x[1]):
            lines.append(f"{prefix}_D[{idx + 2000}] = {str(value).lower()}")

        suffix = f"_{random_lua_identifier(self.rng, 'gid')}" if self.rng else "_id"
        lines.append(f"local function {prefix}{suffix}(k) return {prefix}_D[k] end")

        self._accessors = {"default": f"{prefix}{suffix}"}

        return "\n".join(lines)

    def _gen_xor_transform(self) -> str:
        """生成异或变换访问代码"""
        lines = []
        prefix = self.config.pool_prefix
        key = self.config.xor_key

        lines.append(f"local {prefix}_XKEY = {key}")
        lines.append(f"local {prefix}_S = {{}}")
        for value, idx in sorted(self.pool.strings.items(), key=lambda x: x[1]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            xor_idx = idx ^ key  # Python XOR, generates Lua ~
            lines.append(f"{prefix}_S[{xor_idx}] = \"{escaped}\"")

        lines.append(f"local {prefix}_N = {{}}")
        for value, idx in sorted(self.pool.numbers.items(), key=lambda x: x[1]):
            xor_idx = int(idx) ^ key
            lines.append(f"{prefix}_N[{xor_idx}] = {value}")

        suffix = f"_{random_lua_identifier(self.rng, 'gx')}" if self.rng else "_xget"
        lines.append(f"local function {prefix}{suffix}(i, t)")
        lines.append(f"    if t == 'S' then return {prefix}_S[i ~ {prefix}_XKEY] end")
        lines.append(f"    if t == 'N' then return {prefix}_N[i ~ {prefix}_XKEY] end")
        lines.append(f"end")

        self._accessors = {"xor": f"{prefix}{suffix}"}

        return "\n".join(lines)

    def _gen_offset_transform(self) -> str:
        """生成偏移变换访问代码"""
        lines = []
        prefix = self.config.pool_prefix
        base = self.config.offset_base

        lines.append(f"local {prefix}_BASE = {base}")
        lines.append(f"local {prefix}_S = {{}}")
        for value, idx in sorted(self.pool.strings.items(), key=lambda x: x[1]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            off_idx = idx + base
            lines.append(f"{prefix}_S[{off_idx}] = \"{escaped}\"")

        lines.append(f"local {prefix}_N = {{}}")
        for value, idx in sorted(self.pool.numbers.items(), key=lambda x: x[1]):
            off_idx = int(idx) + base
            lines.append(f"{prefix}_N[{off_idx}] = {value}")

        suffix = f"_{random_lua_identifier(self.rng, 'go')}" if self.rng else "_oget"
        lines.append(f"local function {prefix}{suffix}(i, t)")
        lines.append(f"    if t == 'S' then return {prefix}_S[i + {prefix}_BASE] end")
        lines.append(f"    if t == 'N' then return {prefix}_N[i + {prefix}_BASE] end")
        lines.append(f"end")

        self._accessors = {"offset": f"{prefix}{suffix}"}

        return "\n".join(lines)

    def _gen_reverse_transform(self) -> str:
        """生成反向变换访问代码"""
        lines = []
        prefix = self.config.pool_prefix

        max_idx = max(
            max(self.pool.strings.values(), default=0),
            max(self.pool.numbers.values(), default=0),
            max(self.pool.booleans.values(), default=0)
        )

        lines.append(f"local {prefix}_MAX = {max_idx}")
        lines.append(f"local {prefix}_S = {{}}")
        for value, idx in sorted(self.pool.strings.items(), key=lambda x: x[1]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            rev_idx = max_idx - idx + 1
            lines.append(f"{prefix}_S[{rev_idx}] = \"{escaped}\"")

        lines.append(f"local {prefix}_N = {{}}")
        for value, idx in sorted(self.pool.numbers.items(), key=lambda x: x[1]):
            rev_idx = max_idx - int(idx) + 1
            lines.append(f"{prefix}_N[{rev_idx}] = {value}")

        suffix = f"_{random_lua_identifier(self.rng, 'gr')}" if self.rng else "_rget"
        lines.append(f"local function {prefix}{suffix}(i, t)")
        lines.append(f"    if t == 'S' then return {prefix}_S[{prefix}_MAX - i + 1] end")
        lines.append(f"    if t == 'N' then return {prefix}_N[{prefix}_MAX - i + 1] end")
        lines.append(f"end")

        self._accessors = {"reverse": f"{prefix}{suffix}"}

        return "\n".join(lines)

    def _gen_closure_wrap(self) -> str:
        """生成闭包包装访问代码"""
        lines = []
        prefix = self.config.pool_prefix

        lines.append(f"local {prefix}_S = {{}}")
        for value, idx in sorted(self.pool.strings.items(), key=lambda x: x[1]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f"{prefix}_S[{idx}] = \"{escaped}\"")

        lines.append(f"local {prefix}_N = {{}}")
        for value, idx in sorted(self.pool.numbers.items(), key=lambda x: x[1]):
            lines.append(f"{prefix}_N[{idx}] = {value}")

        lines.append(f"local {prefix}_B = {{}}")
        for value, idx in sorted(self.pool.booleans.items(), key=lambda x: x[1]):
            lines.append(f"{prefix}_B[{idx}] = {str(value).lower()}")

        suffix = f"_{random_lua_identifier(self.rng, 'gc')}" if self.rng else "_cget"
        lines.append(f"local {prefix}_s = {prefix}_S")
        lines.append(f"local {prefix}_n = {prefix}_N")
        lines.append(f"local function {prefix}{suffix}(i, t)")
        lines.append(f"    do local _ = nil end")
        lines.append(f"    if t == 'S' then return {prefix}_s[i] end")
        lines.append(f"    if t == 'N' then return {prefix}_n[i] end")
        lines.append(f"end")

        self._accessors = {"closure": f"{prefix}{suffix}"}

        return "\n".join(lines)

    def _gen_metatable_wrap(self) -> str:
        """生成元表包装访问代码"""
        lines = []
        prefix = self.config.pool_prefix

        lines.append(f"local {prefix}_S = {{}}")
        for value, idx in sorted(self.pool.strings.items(), key=lambda x: x[1]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f"{prefix}_S[{idx}] = \"{escaped}\"")

        lines.append(f"local {prefix}_N = {{}}")
        for value, idx in sorted(self.pool.numbers.items(), key=lambda x: x[1]):
            lines.append(f"{prefix}_N[{idx}] = {value}")

        suffix = f"_{random_lua_identifier(self.rng, 'gm')}" if self.rng else "_mget"
        lines.append(f"setmetatable({prefix}_S, {{__index = function(t, k)")
        lines.append(f"    return rawget(t, k)")
        lines.append(f"end}})")
        lines.append(f"setmetatable({prefix}_N, {{__index = function(t, k)")
        lines.append(f"    return rawget(t, k)")
        lines.append(f"end}})")
        lines.append(f"local function {prefix}{suffix}(i, t)")
        lines.append(f"    if t == 'S' then return {prefix}_S[i] end")
        lines.append(f"    if t == 'N' then return {prefix}_N[i] end")
        lines.append(f"end")

        self._accessors = {"metatable": f"{prefix}{suffix}"}

        return "\n".join(lines)

    def _gen_conditional_wrap(self) -> str:
        """生成条件包装访问代码"""
        lines = []
        prefix = self.config.pool_prefix

        lines.append(f"local {prefix}_S = {{}}")
        for value, idx in sorted(self.pool.strings.items(), key=lambda x: x[1]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f"{prefix}_S[{idx}] = \"{escaped}\"")

        lines.append(f"local {prefix}_N = {{}}")
        for value, idx in sorted(self.pool.numbers.items(), key=lambda x: x[1]):
            lines.append(f"{prefix}_N[{idx}] = {value}")

        guard = f"_g{random.randint(100, 999)}" if self.rng else "_g"
        suffix = f"_{random_lua_identifier(self.rng, 'gcond')}" if self.rng else "_cget"
        lines.append(f"local {guard} = 1")
        lines.append(f"local function {prefix}{suffix}(i, t)")
        lines.append(f"    {guard} = ({guard} % 1)")
        lines.append(f"    if t == 'S' then return {prefix}_S[i] end")
        lines.append(f"    if t == 'N' then return {prefix}_N[i] end")
        lines.append(f"end")

        self._accessors = {"conditional": f"{prefix}{suffix}"}

        return "\n".join(lines)

    def _gen_state_combined(self) -> str:
        """生成状态组合访问代码"""
        lines = []
        prefix = self.config.pool_prefix
        st = self.config.state_var_name

        lines.append(f"local {st} = 0")
        lines.append(f"local {prefix}_S = {{}}")
        for value, idx in sorted(self.pool.strings.items(), key=lambda x: x[1]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f"{prefix}_S[{idx}] = \"{escaped}\"")

        lines.append(f"local {prefix}_N = {{}}")
        for value, idx in sorted(self.pool.numbers.items(), key=lambda x: x[1]):
            lines.append(f"{prefix}_N[{idx}] = {value}")

        suffix = f"_{random_lua_identifier(self.rng, 'gst')}" if self.rng else "_sget"
        lines.append(f"local function {prefix}{suffix}(i, t)")
        lines.append(f"    {st} = ({st} + 1) - 1")
        lines.append(f"    if t == 'S' then return {prefix}_S[i] end")
        lines.append(f"    if t == 'N' then return {prefix}_N[i] end")
        lines.append(f"end")

        self._accessors = {"state": f"{prefix}{suffix}"}

        return "\n".join(lines)

    def _gen_pipeline(self) -> str:
        """生成管道访问代码"""
        lines = []
        prefix = self.config.pool_prefix

        lines.append(f"local {prefix}_S = {{}}")
        for value, idx in sorted(self.pool.strings.items(), key=lambda x: x[1]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f"{prefix}_S[{idx}] = \"{escaped}\"")

        lines.append(f"local {prefix}_N = {{}}")
        for value, idx in sorted(self.pool.numbers.items(), key=lambda x: x[1]):
            lines.append(f"{prefix}_N[{idx}] = {value}")

        suffix = f"_{random_lua_identifier(self.rng, 'gpipe')}" if self.rng else "_pipe"
        helper = f"_{random_lua_identifier(self.rng, 'h')}" if self.rng else "_h"
        lines.append(f"local {prefix}_p = function(v) return v end")
        lines.append(f"local function {helper}(t, k)")
        lines.append(f"    return {prefix}_p")
        lines.append(f"end")
        lines.append(f"local function {prefix}{suffix}(i, t)")
        lines.append(f"    local f = {helper}(t, i)")
        lines.append(f"    if t == 'S' then return f({prefix}_S[i]) end")
        lines.append(f"    if t == 'N' then return f({prefix}_N[i]) end")
        lines.append(f"end")

        self._accessors = {"pipeline": f"{prefix}{suffix}"}

        return "\n".join(lines)

    def _gen_cached(self) -> str:
        """生成缓存访问代码"""
        lines = []
        prefix = self.config.pool_prefix

        lines.append(f"local {prefix}_S = {{}}")
        for value, idx in sorted(self.pool.strings.items(), key=lambda x: x[1]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f"{prefix}_S[{idx}] = \"{escaped}\"")

        lines.append(f"local {prefix}_N = {{}}")
        for value, idx in sorted(self.pool.numbers.items(), key=lambda x: x[1]):
            lines.append(f"{prefix}_N[{idx}] = {value}")

        cache = f"_{random_lua_identifier(self.rng, 'cache')}" if self.rng else "_cache"
        suffix = f"_{random_lua_identifier(self.rng, 'gcache')}" if self.rng else "_cget"
        lines.append(f"local {cache} = {{}}")
        lines.append(f"local function {prefix}{suffix}(i, t)")
        lines.append(f"    local k = t..'_'..tostring(i)")
        lines.append(f"    if not {cache}[k] then")
        lines.append(f"        if t == 'S' then {cache}[k] = {prefix}_S[i] end")
        lines.append(f"        if t == 'N' then {cache}[k] = {prefix}_N[i] end")
        lines.append(f"    end")
        lines.append(f"    return {cache}[k]")
        lines.append(f"end")

        self._accessors = {"cached": f"{prefix}{suffix}"}

        return "\n".join(lines)

    def get_accessors(self) -> dict[str, str]:
        """获取已生成的访问器名称"""
        return self._accessors

    def get_code(self) -> str:
        """获取已生成的代码"""
        return self._generated_code

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            "string_count": len(self.pool.strings),
            "number_count": len(self.pool.numbers),
            "boolean_count": len(self.pool.booleans),
            "accessors": self._accessors,
        }


class UnifiedConstantSystem:
    """
    统一常量系统

    整合多种常量访问策略，提供统一的常量访问接口
    """

    def __init__(self, pool: ConstantPool, rng: random.Random | None = None):
        self.pool = pool
        self.rng = rng
        self.generator = DiverseConstantGenerator(pool, rng)
        self.current_config = ConstantAccessConfig()

    def generate(self, config: ConstantAccessConfig | None = None) -> str:
        """生成常量访问代码"""
        if config:
            self.current_config = config
            self.generator.config = config

        return self.generator.generate(config.access_type if config else None)

    def generate_random(self) -> str:
        """随机生成常量访问代码"""
        if self.rng:
            types = list(ConstantAccessType)
            access_type = self.rng.choice(types)
            return self.generator.generate(access_type)
        return self.generator.generate()

    def generate_variants(self, count: int = 3) -> list[tuple[str, dict]]:
        """生成多个变体"""
        variants = []

        for _ in range(count):
            code = self.generate_random()
            variants.append((code, self.generator.get_statistics()))

        return variants

    def get_accessors(self) -> dict[str, str]:
        """获取访问器"""
        return self.generator.get_accessors()


# ===== 便捷函数 =====


def create_constant_generator(
    pool: ConstantPool,
    rng: random.Random,
    access_type: str = "random"
) -> DiverseConstantGenerator:
    """
    创建常量生成器

    Args:
        pool: 常量池
        rng: 随机数生成器
        access_type: 访问类型 ("direct", "named", "indexed", "xor", "offset", "reverse",
                      "closure", "metatable", "conditional", "state", "pipeline", "cached", "random")

    Returns:
        DiverseConstantGenerator 实例
    """
    type_map = {
        "direct": ConstantAccessType.DIRECT_TABLE,
        "named": ConstantAccessType.NAMED_GETTER,
        "indexed": ConstantAccessType.INDEXED_ACCESS,
        "xor": ConstantAccessType.XOR_TRANSFORM,
        "offset": ConstantAccessType.OFFSET_TRANSFORM,
        "reverse": ConstantAccessType.REVERSE_TRANSFORM,
        "closure": ConstantAccessType.CLOSURE_WRAP,
        "metatable": ConstantAccessType.METATABLE_WRAP,
        "conditional": ConstantAccessType.CONDITIONAL_WRAP,
        "state": ConstantAccessType.STATE_COMBINED,
        "pipeline": ConstantAccessType.PIPELINE,
        "cached": ConstantAccessType.CACHED,
    }

    if access_type == "random":
        config = ConstantAccessConfig(enable_randomization=True)
    else:
        config = ConstantAccessConfig(
            access_type=type_map.get(access_type, ConstantAccessType.NAMED_GETTER),
            enable_randomization=False
        )

    return DiverseConstantGenerator(pool, rng, config)


def generate_constant_access(
    pool: ConstantPool,
    rng: random.Random,
    access_type: str = "random"
) -> str:
    """
    便捷函数：生成常量访问代码

    Args:
        pool: 常量池
        rng: 随机数生成器
        access_type: 访问类型

    Returns:
        生成的 Lua 代码
    """
    generator = create_constant_generator(pool, rng, access_type)
    return generator.generate()


def demo_constant_strategies(pool: ConstantPool, rng: random.Random) -> dict[str, str]:
    """
    演示所有常量访问策略

    Args:
        pool: 常量池
        rng: 随机数生成器

    Returns:
        策略名到代码的映射
    """
    results = {}

    for access_type in ConstantAccessType:
        generator = DiverseConstantGenerator(pool, rng)
        code = generator.generate(access_type)
        results[access_type.value] = code

    return results


# ===== Block 辅助结构增强系统 =====


class AuxiliaryStructureType(Enum):
    """辅助结构类型"""
    # 逻辑块
    DUMMY_ASSIGN = "dummy_assign"           # 虚拟赋值
    IDENTITY_PASS = "identity_pass"          # 恒等传递
    SWAP_TEMP = "swap_temp"                 # 临时交换

    # 条件分支
    ALWAYS_TRUE_BRANCH = "always_true"      # 恒真分支
    ALWAYS_FALSE_BRANCH = "always_false"     # 恒假分支
    NESTED_CONDITION = "nested_condition"    # 嵌套条件
    COMPOUND_CONDITION = "compound_condition"  # 复合条件

    # 结构扩展
    GUARD_WRAPPER = "guard_wrapper"          # 守卫包装
    WRAPPER_BLOCK = "wrapper_block"          # 包装块
    EMPTY_BLOCK = "empty_block"              # 空块
    NOP_SEQUENCE = "nop_sequence"            # NOP 序列

    # 计算块
    IDLE_COMPUTATION = "idle_computation"    # 空闲计算
    REDUNDANT_CALC = "redundant_calc"        # 冗余计算
    SELF_REFERENCE = "self_reference"        # 自引用


@dataclass
class AuxiliaryStructureConfig:
    """辅助结构配置"""
    enabled: bool = True
    max_structures: int = 3
    inject_probability: float = 0.3
    include_type: list[AuxiliaryStructureType] | None = None
    exclude_type: list[AuxiliaryStructureType] | None = None


class LogicBlockGenerator:
    """逻辑块生成器"""

    @staticmethod
    def generate_dummy_assign(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成虚拟赋值块"""
        var = f"_d{rng.randint(1000, 9999)}" if rng else "_dummy"
        patterns = [
            f"local {var} = 0\n{var} = {var}",
            f"local {var} = nil\n{var} = {var}",
            f"local {var} = {{}}\n{var} = {var}",
        ]
        content = patterns[rng.choice(range(len(patterns)))] if rng else patterns[0]
        return content, {"type": "dummy_assign", "variable": var}

    @staticmethod
    def generate_identity_pass(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成恒等传递块"""
        var = f"_p{rng.randint(1000, 9999)}" if rng else "_pass"
        patterns = [
            f"local {var} = 1\n{var} = ({var} + 0) - 0",
            f"local {var} = true\n{var} = not not {var}",
            f"local {var} = 0\n{var} = ({var} * 1) / 1",
        ]
        content = patterns[rng.choice(range(len(patterns)))] if rng else patterns[0]
        return content, {"type": "identity_pass", "variable": var}

    @staticmethod
    def generate_swap_temp(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成临时交换块"""
        a = f"_a{rng.randint(100, 999)}" if rng else "_a"
        b = f"_b{rng.randint(100, 999)}" if rng else "_b"
        patterns = [
            f"local {a}, {b} = 0, 0\nlocal _t = {a}\n{a} = {b}\n{b} = _t",
            f"local {a} = 1\nlocal {b} = {a}\n{a} = {b}",
        ]
        content = patterns[rng.choice(range(len(patterns)))] if rng else patterns[0]
        return content, {"type": "swap_temp", "variables": [a, b]}


class ConditionBranchGenerator:
    """条件分支生成器"""

    @staticmethod
    def generate_always_true(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成恒真分支"""
        patterns = [
            "if true then\n    -- always\nend",
            "if 1 == 1 then\n    -- always\nend",
            "if 'x' == 'x' then\n    -- always\nend",
        ]
        content = patterns[rng.choice(range(len(patterns)))] if rng else patterns[0]
        return content, {"type": "always_true", "condition": "true"}

    @staticmethod
    def generate_always_false(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成恒假分支"""
        patterns = [
            "if false then\n    -- never\nend",
            "if 1 ~= 1 then\n    -- never\nend",
            "if nil then\n    -- never\nend",
        ]
        content = patterns[rng.choice(range(len(patterns)))] if rng else patterns[0]
        return content, {"type": "always_false", "condition": "false"}

    @staticmethod
    def generate_nested_condition(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成嵌套条件"""
        patterns = [
            "if true then\n    if false then\n        -- never\n    end\nend",
            "if 1 == 1 then\n    if nil then\n        -- never\n    end\nend",
        ]
        content = patterns[rng.choice(range(len(patterns)))] if rng else patterns[0]
        return content, {"type": "nested_condition", "depth": 2}

    @staticmethod
    def generate_compound_condition(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成复合条件"""
        var = f"_c{rng.randint(100, 999)}" if rng else "_cond"
        patterns = [
            f"local {var} = true\nif {var} and true then\n    -- compound\nend",
            f"local {var} = 1\nif {var} == 1 or false then\n    -- compound\nend",
        ]
        content = patterns[rng.choice(range(len(patterns)))] if rng else patterns[0]
        return content, {"type": "compound_condition", "variable": var}


class StructureExtensionGenerator:
    """结构扩展生成器"""

    @staticmethod
    def generate_guard_wrapper(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成守卫包装"""
        var = f"_g{rng.randint(100, 999)}" if rng else "_guard"
        content = f"local {var} = true\nif not {var} then\n    error()\nend"
        return content, {"type": "guard_wrapper", "variable": var}

    @staticmethod
    def generate_wrapper_block(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成包装块"""
        patterns = [
            "do\n    local _ = nil\nend",
            "(function() end)()",
            "pcall(function() end)",
        ]
        content = patterns[rng.choice(range(len(patterns)))] if rng else patterns[0]
        return content, {"type": "wrapper_block"}

    @staticmethod
    def generate_empty_block(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成空块"""
        patterns = ["do end", "-- empty", ""]
        content = patterns[rng.choice(range(len(patterns)))] if rng else patterns[0]
        return content, {"type": "empty_block"}

    @staticmethod
    def generate_nop_sequence(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成 NOP 序列"""
        patterns = [
            "do end\ndo end\ndo end",
            "next({})\nnext({})",
            "(function() end)()\n(function() end)()",
        ]
        content = patterns[rng.choice(range(len(patterns)))] if rng else patterns[0]
        return content, {"type": "nop_sequence"}


class ComputationBlockGenerator:
    """计算块生成器"""

    @staticmethod
    def generate_idle_computation(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成空闲计算块"""
        var = f"_x{rng.randint(100, 999)}" if rng else "_idle"
        patterns = [
            f"local {var} = 0\n{var} = ({var} + 1) - 1",
            f"local {var} = 1\n{var} = ({var} * 1) / 1",
            f"local {var} = true\n{var} = not not {var}",
        ]
        content = patterns[rng.choice(range(len(patterns)))] if rng else patterns[0]
        return content, {"type": "idle_computation", "variable": var}

    @staticmethod
    def generate_redundant_calc(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成冗余计算块"""
        var = f"_r{rng.randint(100, 999)}" if rng else "_redundant"
        patterns = [
            f"local {var} = 10\n{var} = {var} + 0\n{var} = {var} - 0",
            f"local {var} = 5\n{var} = {var} * 1\n{var} = {var} / 1",
        ]
        content = patterns[rng.choice(range(len(patterns)))] if rng else patterns[0]
        return content, {"type": "redundant_calc", "variable": var}

    @staticmethod
    def generate_self_reference(rng: random.Random | None = None) -> tuple[str, dict]:
        """生成自引用块"""
        var = f"_s{rng.randint(100, 999)}" if rng else "_self"
        content = f"local {var} = 0\n{var} = {var}"
        return content, {"type": "self_reference", "variable": var}


class AuxiliaryStructureGenerator:
    """辅助结构生成器"""

    def __init__(self, rng: random.Random | None = None, config: AuxiliaryStructureConfig | None = None):
        self.rng = rng
        self.config = config if config else AuxiliaryStructureConfig()
        self.generated_structures: list[dict] = []

    def _get_available_types(self) -> list[AuxiliaryStructureType]:
        types = list(AuxiliaryStructureType)
        if self.config.include_type:
            types = [t for t in types if t in self.config.include_type]
        if self.config.exclude_type:
            types = [t for t in types if t not in self.config.exclude_type]
        return types

    def _create_generators(self) -> dict[AuxiliaryStructureType, callable]:
        return {
            AuxiliaryStructureType.DUMMY_ASSIGN: LogicBlockGenerator.generate_dummy_assign,
            AuxiliaryStructureType.IDENTITY_PASS: LogicBlockGenerator.generate_identity_pass,
            AuxiliaryStructureType.SWAP_TEMP: LogicBlockGenerator.generate_swap_temp,
            AuxiliaryStructureType.ALWAYS_TRUE_BRANCH: ConditionBranchGenerator.generate_always_true,
            AuxiliaryStructureType.ALWAYS_FALSE_BRANCH: ConditionBranchGenerator.generate_always_false,
            AuxiliaryStructureType.NESTED_CONDITION: ConditionBranchGenerator.generate_nested_condition,
            AuxiliaryStructureType.COMPOUND_CONDITION: ConditionBranchGenerator.generate_compound_condition,
            AuxiliaryStructureType.GUARD_WRAPPER: StructureExtensionGenerator.generate_guard_wrapper,
            AuxiliaryStructureType.WRAPPER_BLOCK: StructureExtensionGenerator.generate_wrapper_block,
            AuxiliaryStructureType.EMPTY_BLOCK: StructureExtensionGenerator.generate_empty_block,
            AuxiliaryStructureType.NOP_SEQUENCE: StructureExtensionGenerator.generate_nop_sequence,
            AuxiliaryStructureType.IDLE_COMPUTATION: ComputationBlockGenerator.generate_idle_computation,
            AuxiliaryStructureType.REDUNDANT_CALC: ComputationBlockGenerator.generate_redundant_calc,
            AuxiliaryStructureType.SELF_REFERENCE: ComputationBlockGenerator.generate_self_reference,
        }

    def generate_structure(self, struct_type: AuxiliaryStructureType | None = None) -> tuple[str, dict]:
        if not self.config.enabled:
            return "", {}
        if struct_type is None:
            available = self._get_available_types()
            struct_type = self.rng.choice(available) if self.rng and available else AuxiliaryStructureType.DUMMY_ASSIGN
        generators = self._create_generators()
        gen = generators.get(struct_type, LogicBlockGenerator.generate_dummy_assign)
        content, info = gen(self.rng)
        info["structure_type"] = struct_type.value
        info["id"] = len(self.generated_structures) + 1
        self.generated_structures.append(info)
        return content, info

    def generate_multiple(self, count: int | None = None) -> list[tuple[str, dict]]:
        if count is None:
            count = self.rng.randint(1, self.config.max_structures) if self.rng else 1
        structures = []
        for _ in range(count):
            if self.rng and self.rng.random() > self.config.inject_probability:
                continue
            content, info = self.generate_structure()
            if content:
                structures.append((content, info))
        return structures

    def inject_into_block(self, block_content: str) -> str:
        if not self.config.enabled:
            return block_content
        if self.rng and self.rng.random() > self.config.inject_probability:
            return block_content
        content, info = self.generate_structure()
        if not content:
            return block_content
        position = self.rng.randint(0, 2) if self.rng else 0
        if position == 0:
            return content + "\n" + block_content
        elif position == 1:
            lines = block_content.split("\n")
            if len(lines) > 1:
                mid = len(lines) // 2
                return "\n".join(lines[:mid]) + "\n" + content + "\n" + "\n".join(lines[mid:])
            return block_content + "\n" + content
        else:
            return block_content + "\n" + content

    def create_auxiliary_block(self) -> CodeBlock:
        content, info = self.generate_structure()
        if not content:
            content = "do end"
        block_id = -10000 - len(self.generated_structures)
        return CodeBlock(
            block_id=block_id, content=content, block_type="auxiliary",
            next_id=None, branches={}, auxiliary_paths=[], dependencies=[],
            metadata={"is_auxiliary": True, "auxiliary_info": info}
        )

    def get_statistics(self) -> dict:
        return {
            "enabled": self.config.enabled,
            "generated_count": len(self.generated_structures),
            "structures": self.generated_structures
        }


class BlockMixer:
    """Block 混合器"""

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng

    def mix_blocks_and_auxiliary(
        self, blocks: list[CodeBlock], auxiliary_gen: AuxiliaryStructureGenerator, mix_ratio: float = 0.3
    ) -> list[CodeBlock | tuple[str, dict]]:
        result: list[CodeBlock | tuple[str, dict]] = []
        for block in blocks:
            result.append(block)
            if self.rng and self.rng.random() < mix_ratio:
                auxiliary = auxiliary_gen.generate_structure()
                if auxiliary[0]:
                    result.append(auxiliary)
        return result

    def generate_mixed_output(
        self, blocks: list[CodeBlock], auxiliary_gen: AuxiliaryStructureGenerator, mix_ratio: float = 0.3
    ) -> list[str]:
        mixed = self.mix_blocks_and_auxiliary(blocks, auxiliary_gen, mix_ratio)
        lines = []
        for item in mixed:
            if isinstance(item, CodeBlock):
                lines.append(f"-- Block {item.block_id}")
                lines.append(item.content)
                lines.append("")
            else:
                content, info = item
                lines.append(f"-- Auxiliary ({info.get('type', 'unknown')})")
                lines.append(content)
                lines.append("")
        return lines


def create_auxiliary_generator(rng: random.Random, enabled: bool = True, max_structures: int = 3, probability: float = 0.3) -> AuxiliaryStructureGenerator:
    config = AuxiliaryStructureConfig(enabled=enabled, max_structures=max_structures, inject_probability=probability)
    return AuxiliaryStructureGenerator(rng, config)


def inject_auxiliary_to_block(block_content: str, rng: random.Random, probability: float = 0.3, enabled: bool = True) -> str:
    config = AuxiliaryStructureConfig(enabled=enabled, inject_probability=probability)
    generator = AuxiliaryStructureGenerator(rng, config)
    return generator.inject_into_block(block_content)


def generate_auxiliary_block(rng: random.Random, struct_type: str = "random") -> tuple[str, dict]:
    type_map = {
        "dummy": AuxiliaryStructureType.DUMMY_ASSIGN,
        "identity": AuxiliaryStructureType.IDENTITY_PASS,
        "swap": AuxiliaryStructureType.SWAP_TEMP,
        "true": AuxiliaryStructureType.ALWAYS_TRUE_BRANCH,
        "false": AuxiliaryStructureType.ALWAYS_FALSE_BRANCH,
        "nested": AuxiliaryStructureType.NESTED_CONDITION,
        "compound": AuxiliaryStructureType.COMPOUND_CONDITION,
        "guard": AuxiliaryStructureType.GUARD_WRAPPER,
        "wrapper": AuxiliaryStructureType.WRAPPER_BLOCK,
        "empty": AuxiliaryStructureType.EMPTY_BLOCK,
        "nop": AuxiliaryStructureType.NOP_SEQUENCE,
        "idle": AuxiliaryStructureType.IDLE_COMPUTATION,
        "redundant": AuxiliaryStructureType.REDUNDANT_CALC,
        "self": AuxiliaryStructureType.SELF_REFERENCE,
    }
    config = AuxiliaryStructureConfig(enabled=True)
    generator = AuxiliaryStructureGenerator(rng, config)
    if struct_type == "random":
        return generator.generate_structure()
    return generator.generate_structure(type_map.get(struct_type))


def mix_blocks_with_auxiliary(blocks: list[CodeBlock], rng: random.Random, mix_ratio: float = 0.3) -> list[str]:
    config = AuxiliaryStructureConfig(enabled=True, inject_probability=1.0)
    auxiliary_gen = AuxiliaryStructureGenerator(rng, config)
    mixer = BlockMixer(rng)
    return mixer.generate_mixed_output(blocks, auxiliary_gen, mix_ratio)


# ===== 统一结构随机化系统 =====


class StructureRandomizationMode(Enum):
    """结构随机化模式"""
    MINIMAL = "minimal"               # 最小化结构
    STANDARD = "standard"             # 标准结构
    ENHANCED = "enhanced"            # 增强结构
    OBFUSCATED = "obfuscated"         # 混淆结构
    CUSTOM = "custom"                 # 自定义结构


@dataclass
class StructureRandomizationConfig:
    """结构随机化配置"""
    mode: StructureRandomizationMode = StructureRandomizationMode.STANDARD
    enable_block_organization: bool = True
    enable_dispatcher_randomization: bool = True
    enable_constant_access: bool = True
    enable_auxiliary_structures: bool = False
    enable_naming_variation: bool = True
    enable_code_formatting: bool = False
    block_order_strategy: BlockOrderStrategy | None = None
    dispatch_strategy: DispatchStrategy | None = None
    constant_access_type: ConstantAccessType | None = None
    auxiliary_probability: float = 0.3
    naming_scheme: str = "random"


class BlockOrganizationStrategy(Enum):
    """Block 组织策略"""
    SEQUENTIAL_LAYOUT = "sequential_layout"       # 顺序布局
    TABLE_BASED = "table_based"                 # 表驱动
    FUNCTION_ARRAY = "function_array"            # 函数数组
    DISPATCHER_LOOP = "dispatcher_loop"          # 调度循环
    STATE_MACHINE_LAYOUT = "state_machine"        # 状态机布局
    INLINE_BLOCKS = "inline_blocks"              # 内联块
    SPLIT_LAYOUT = "split_layout"               # 分离布局
    HYBRID_LAYOUT = "hybrid_layout"              # 混合布局


class DispatcherImplementation(Enum):
    """调度器实现方式"""
    WHILE_LOOP = "while_loop"                   # while 循环
    REPEAT_LOOP = "repeat_loop"                 # repeat 循环
    RECURSIVE_CALL = "recursive_call"            # 递归调用
    TAIL_CALL = "tail_call"                     # 尾调用
    GOTO_BASED = "goto_based"                   # goto 跳转
    COROUTINE = "coroutine"                     # 协程
    TABLE_JUMP = "table_jump"                   # 表跳转
    INDEXED_JUMP = "indexed_jump"               # 索引跳转


@dataclass
class CodeGenerationProfile:
    """代码生成配置文件"""
    block_organization: BlockOrganizationStrategy = BlockOrganizationStrategy.TABLE_BASED
    dispatcher_type: DispatcherImplementation = DispatcherImplementation.WHILE_LOOP
    constant_access: ConstantAccessType = ConstantAccessType.NAMED_GETTER
    block_order: BlockOrderStrategy = BlockOrderStrategy.SEQUENTIAL
    include_comments: bool = False
    include_metadata: bool = True
    inject_auxiliary: bool = False
    naming_scheme: str = "random"


class BlockOrganizer:
    """Block 组织器"""

    @staticmethod
    def organize_table_based(program: BlockProgram, rng: random.Random | None) -> list[str]:
        """表驱动组织"""
        lines = []
        prefix = f"_tbl{rng.randint(1000, 9999)}" if rng else "_tbl"

        lines.append(f"local {prefix} = {{}}")
        for idx, bid in enumerate(program.execution_order):
            lines.append(f"{prefix}[{idx + 1}] = {bid}")

        return lines

    @staticmethod
    def organize_function_array(program: BlockProgram, rng: random.Random | None) -> list[str]:
        """函数数组组织"""
        lines = []
        prefix = f"_fn{rng.randint(1000, 9999)}" if rng else "_fn"

        lines.append(f"local {prefix} = {{}}")
        for idx, bid in enumerate(program.execution_order):
            lines.append(f"{prefix}[{idx + 1}] = _blk_{bid}")

        return lines

    @staticmethod
    def organize_dispatcher_loop(program: BlockProgram, rng: random.Random | None) -> list[str]:
        """调度循环组织"""
        lines = []
        pc = f"_pc{rng.randint(1000, 9999)}" if rng else "_pc"

        lines.append(f"local {pc} = {program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = _tbl[{pc}]")
        lines.append(f"    if block then {pc} = block() else break end")
        lines.append("end")

        return lines

    @staticmethod
    def organize_state_machine(program: BlockProgram, rng: random.Random | None) -> list[str]:
        """状态机组织"""
        lines = []
        state = f"_st{rng.randint(1000, 9999)}" if rng else "_st"
        pc = f"_pc{rng.randint(1000, 9999)}" if rng else "_pc"

        lines.append(f"local {state} = 0")
        lines.append(f"local {pc} = {program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    {state} = ({state} + 1) - 1")
        lines.append(f"    local block = _tbl[{pc}]")
        lines.append(f"    if block then {pc} = block() else break end")
        lines.append("end")

        return lines

    @staticmethod
    def organize_inline_blocks(program: BlockProgram, rng: random.Random | None) -> list[str]:
        """内联块组织"""
        lines = []

        for bid in program.execution_order:
            block = program.get_block(bid)
            if block:
                lines.append(f"-- Block {bid}")
                if block.content.strip():
                    lines.append(block.content.strip())

        return lines

    @staticmethod
    def organize_split_layout(program: BlockProgram, rng: random.Random | None) -> list[str]:
        """分离布局组织"""
        lines = []
        prefix = f"_p{rng.randint(1000, 9999)}" if rng else "_p"

        lines.append(f"local {prefix}_data = {{}}")
        lines.append(f"local {prefix}_funcs = {{}}")

        for idx, bid in enumerate(program.execution_order):
            lines.append(f"{prefix}_data[{idx + 1}] = {bid}")

        return lines

    @staticmethod
    def organize_sequential(program: BlockProgram, rng: random.Random | None) -> list[str]:
        """顺序布局"""
        lines = []

        for bid in program.execution_order:
            block = program.get_block(bid)
            if block:
                lines.append(f"local function _blk_{bid}()")
                if block.content.strip():
                    for ln in block.content.strip().split("\n"):
                        lines.append(f"    {ln}")
                lines.append(f"    return {block.next_id if block.next_id else ''}")
                lines.append("end")

        return lines

    @classmethod
    def organize(cls, program: BlockProgram, rng: random.Random | None, strategy: BlockOrganizationStrategy) -> list[str]:
        """组织 blocks"""
        organizers = {
            BlockOrganizationStrategy.SEQUENTIAL_LAYOUT: cls.organize_sequential,
            BlockOrganizationStrategy.TABLE_BASED: cls.organize_table_based,
            BlockOrganizationStrategy.FUNCTION_ARRAY: cls.organize_function_array,
            BlockOrganizationStrategy.DISPATCHER_LOOP: cls.organize_dispatcher_loop,
            BlockOrganizationStrategy.STATE_MACHINE_LAYOUT: cls.organize_state_machine,
            BlockOrganizationStrategy.INLINE_BLOCKS: cls.organize_inline_blocks,
            BlockOrganizationStrategy.SPLIT_LAYOUT: cls.organize_split_layout,
        }

        org = organizers.get(strategy, cls.organize_table_based)
        return org(program, rng)


class DispatcherBuilder:
    """调度器构建器"""

    @staticmethod
    def build_while_loop(program: BlockProgram, rng: random.Random | None) -> list[str]:
        """构建 while 循环调度器"""
        lines = []
        pc = f"_pc{rng.randint(1000, 9999)}" if rng else "_pc"

        lines.append(f"local {pc} = {program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = _tbl[{pc}]")
        lines.append(f"    if block then")
        lines.append(f"        {pc} = block()")
        lines.append(f"    else")
        lines.append(f"        break")
        lines.append(f"    end")
        lines.append("end")

        return lines

    @staticmethod
    def build_repeat_loop(program: BlockProgram, rng: random.Random | None) -> list[str]:
        """构建 repeat 循环调度器"""
        lines = []
        pc = f"_pc{rng.randint(1000, 9999)}" if rng else "_pc"

        lines.append(f"local {pc} = {program.entry_block_id}")
        lines.append(f"repeat")
        lines.append(f"    local block = _tbl[{pc}]")
        lines.append(f"    if block then")
        lines.append(f"        {pc} = block()")
        lines.append(f"    end")
        lines.append(f"until not {pc}")

        return lines

    @staticmethod
    def build_recursive_call(program: BlockProgram, rng: random.Random | None) -> list[str]:
        """构建递归调用调度器"""
        lines = []
        fn = f"_run{rng.randint(1000, 9999)}" if rng else "_run"

        lines.append(f"local function {fn}(pc)")
        lines.append(f"    local block = _tbl[pc]")
        lines.append(f"    if block then")
        lines.append(f"        return {fn}(block())")
        lines.append(f"    end")
        lines.append(f"end")
        lines.append(f"{fn}({program.entry_block_id})")

        return lines

    @staticmethod
    def build_tail_call(program: BlockProgram, rng: random.Random | None) -> list[str]:
        """构建尾调用调度器"""
        lines = []
        fn = f"_step{rng.randint(1000, 9999)}" if rng else "_step"

        lines.append(f"local {fn} = function(pc)")
        lines.append(f"    local block = _tbl[pc]")
        lines.append(f"    if block then return {fn}(block()) end")
        lines.append(f"end")
        lines.append(f"return {fn}({program.entry_block_id})")

        return lines

    @staticmethod
    def build_goto_based(program: BlockProgram, rng: random.Random | None) -> list[str]:
        """构建 goto 跳转调度器"""
        lines = []
        pc = f"_pc{rng.randint(1000, 9999)}" if rng else "_pc"
        label = f"_l{rng.randint(1000, 9999)}" if rng else "_l"

        lines.append(f"local {pc} = {program.entry_block_id}")
        lines.append(f"::{label}::")
        lines.append(f"do")
        lines.append(f"    local block = _tbl[{pc}]")
        lines.append(f"    if block then")
        lines.append(f"        {pc} = block()")
        lines.append(f"        goto {label}")
        lines.append(f"    end")
        lines.append("end")

        return lines

    @staticmethod
    def build_table_jump(program: BlockProgram, rng: random.Random | None) -> list[str]:
        """构建表跳转调度器"""
        lines = []
        pc = f"_pc{rng.randint(1000, 9999)}" if rng else "_pc"
        jmp = f"_jmp{rng.randint(1000, 9999)}" if rng else "_jmp"

        lines.append(f"local {jmp} = {{}}")
        for bid in program.execution_order:
            block = program.get_block(bid)
            if block and block.next_id:
                lines.append(f"{jmp}[{bid}] = {block.next_id}")

        lines.append(f"local {pc} = {program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = _tbl[{pc}]")
        lines.append(f"    if block then")
        lines.append(f"        {pc} = {jmp}[{pc}] or block()")
        lines.append(f"    else break end")
        lines.append("end")

        return lines

    @staticmethod
    def build_indexed_jump(program: BlockProgram, rng: random.Random | None) -> list[str]:
        """构建索引跳转调度器"""
        lines = []
        pc = f"_pc{rng.randint(1000, 9999)}" if rng else "_pc"
        idx = f"_idx{rng.randint(1000, 9999)}" if rng else "_idx"

        order_map = {bid: idx + 1 for idx, bid in enumerate(program.execution_order)}

        lines.append(f"local {idx} = {{}}")
        for bid, i in order_map.items():
            lines.append(f"{idx}[{bid}] = {i}")

        lines.append(f"local {pc} = {program.entry_block_id}")
        lines.append(f"while {pc} do")
        lines.append(f"    local block = _tbl[{pc}]")
        lines.append(f"    if block then")
        lines.append(f"        {pc} = block()")
        lines.append(f"    else break end")
        lines.append("end")

        return lines

    @classmethod
    def build(cls, program: BlockProgram, rng: random.Random | None, dispatcher_type: DispatcherImplementation) -> list[str]:
        """构建调度器"""
        builders = {
            DispatcherImplementation.WHILE_LOOP: cls.build_while_loop,
            DispatcherImplementation.REPEAT_LOOP: cls.build_repeat_loop,
            DispatcherImplementation.RECURSIVE_CALL: cls.build_recursive_call,
            DispatcherImplementation.TAIL_CALL: cls.build_tail_call,
            DispatcherImplementation.GOTO_BASED: cls.build_goto_based,
            DispatcherImplementation.TABLE_JUMP: cls.build_table_jump,
            DispatcherImplementation.INDEXED_JUMP: cls.build_indexed_jump,
        }

        builder = builders.get(dispatcher_type, cls.build_while_loop)
        return builder(program, rng)


class StructureRandomizer:
    """
    结构随机化器

    统一的结构随机化框架，支持多种生成策略
    """

    def __init__(self, program: BlockProgram, rng: random.Random | None = None, config: StructureRandomizationConfig | None = None):
        self.program = program
        self.rng = rng
        self.config = config if config else StructureRandomizationConfig()
        self._profile: CodeGenerationProfile | None = None

    def _create_profile(self) -> CodeGenerationProfile:
        """创建代码生成配置"""
        if self.config.mode == StructureRandomizationMode.MINIMAL:
            return CodeGenerationProfile(
                block_organization=BlockOrganizationStrategy.INLINE_BLOCKS,
                dispatcher_type=DispatcherImplementation.WHILE_LOOP,
                constant_access=ConstantAccessType.DIRECT_TABLE,
                include_comments=False,
                include_metadata=False,
                inject_auxiliary=False,
                naming_scheme="sequential"
            )
        elif self.config.mode == StructureRandomizationMode.STANDARD:
            return CodeGenerationProfile(
                block_organization=BlockOrganizationStrategy.TABLE_BASED,
                dispatcher_type=DispatcherImplementation.WHILE_LOOP,
                constant_access=ConstantAccessType.NAMED_GETTER,
                include_comments=False,
                include_metadata=True,
                inject_auxiliary=False,
                naming_scheme="random"
            )
        elif self.config.mode == StructureRandomizationMode.ENHANCED:
            return CodeGenerationProfile(
                block_organization=BlockOrganizationStrategy.DISPATCHER_LOOP,
                dispatcher_type=DispatcherImplementation.WHILE_LOOP,
                constant_access=ConstantAccessType.NAMED_GETTER,
                include_comments=True,
                include_metadata=True,
                inject_auxiliary=True,
                naming_scheme="random"
            )
        elif self.config.mode == StructureRandomizationMode.OBFUSCATED:
            types = list(BlockOrganizationStrategy)
            disps = list(DispatcherImplementation)
            consts = list(ConstantAccessType)
            orders = list(BlockOrderStrategy)

            return CodeGenerationProfile(
                block_organization=self.rng.choice(types) if self.rng else BlockOrganizationStrategy.SPLIT_LAYOUT,
                dispatcher_type=self.rng.choice(disps) if self.rng else DispatcherImplementation.TAIL_CALL,
                constant_access=self.rng.choice(consts) if self.rng else ConstantAccessType.XOR_TRANSFORM,
                block_order=self.rng.choice(orders) if self.rng else BlockOrderStrategy.SHUFFLED,
                include_comments=False,
                include_metadata=self.rng.random() > 0.5 if self.rng else False,
                inject_auxiliary=self.rng.random() > 0.7 if self.rng else False,
                naming_scheme="random"
            )
        else:
            return CodeGenerationProfile(
                block_organization=self.config.block_order_strategy or BlockOrderStrategy.SEQUENTIAL,
                dispatcher_type=self.config.dispatch_strategy or DispatchStrategy.DIRECT,
                constant_access=self.config.constant_access_type or ConstantAccessType.NAMED_GETTER,
                naming_scheme=self.config.naming_scheme
            )

    def randomize_config(self) -> CodeGenerationProfile:
        """随机化配置"""
        if not self.rng:
            return self._create_profile()

        if self._profile is None:
            self._profile = self._create_profile()

        if self.config.enable_block_organization:
            orgs = list(BlockOrganizationStrategy)
            self._profile.block_organization = self.rng.choice(orgs)

        if self.config.enable_dispatcher_randomization:
            disps = list(DispatcherImplementation)
            self._profile.dispatcher_type = self.rng.choice(disps)

        if self.config.enable_constant_access:
            consts = list(ConstantAccessType)
            self._profile.constant_access = self.rng.choice(consts)

        if self.config.enable_naming_variation:
            schemes = ["random", "sequential", "semantic"]
            self._profile.naming_scheme = self.rng.choice(schemes)

        return self._profile

    def generate_program(self, profile: CodeGenerationProfile | None = None) -> tuple[str, dict]:
        """生成程序"""
        if profile is None:
            profile = self.randomize_config()

        self._profile = profile
        lines = []

        lines.append("-- Block Table")
        table_lines = BlockOrganizer.organize(self.program, self.rng, profile.block_organization)
        lines.extend(table_lines)
        lines.append("")

        lines.append("-- Block Functions")
        block_prefix = f"_blk{self.rng.randint(1000, 9999)}" if self.rng else "_blk"
        for idx, bid in enumerate(BlockOrderRandomizer.apply_order(self.program, self.rng, profile.block_order)):
            block = self.program.get_block(bid)
            if block:
                if profile.naming_scheme == "sequential":
                    func_name = f"{block_prefix}_{idx + 1}"
                else:
                    func_name = f"{block_prefix}_{bid}"

                lines.append(f"local function {func_name}()")
                if block.content.strip():
                    for ln in block.content.strip().split("\n"):
                        lines.append(f"    {ln}")
                next_id = block.next_id if block.next_id else ""
                lines.append(f"    return {next_id}")
                lines.append("end")
                lines.append("")

        lines.append("-- Dispatcher")
        disp_lines = DispatcherBuilder.build(self.program, self.rng, profile.dispatcher_type)
        lines.extend(disp_lines)

        stats = {
            "mode": self.config.mode.value,
            "block_organization": profile.block_organization.value,
            "dispatcher_type": profile.dispatcher_type.value,
            "constant_access": profile.constant_access.value,
            "block_order": profile.block_order.value,
            "naming_scheme": profile.naming_scheme,
            "total_blocks": len(self.program.execution_order),
            "total_lines": len(lines)
        }

        return "\n".join(lines), stats

    def generate_variants(self, count: int = 3) -> list[tuple[str, dict]]:
        """生成多个变体"""
        variants = []
        for _ in range(count):
            profile = self.randomize_config()
            code, stats = self.generate_program(profile)
            variants.append((code, stats))
        return variants

    def get_profile(self) -> CodeGenerationProfile | None:
        """获取当前配置"""
        return self._profile


# ===== 便捷函数 =====


def create_structure_randomizer(
    program: BlockProgram,
    rng: random.Random,
    mode: str = "standard"
) -> StructureRandomizer:
    """创建结构随机化器"""
    mode_map = {
        "minimal": StructureRandomizationMode.MINIMAL,
        "standard": StructureRandomizationMode.STANDARD,
        "enhanced": StructureRandomizationMode.ENHANCED,
        "obfuscated": StructureRandomizationMode.OBFUSCATED,
        "custom": StructureRandomizationMode.CUSTOM,
    }

    config = StructureRandomizationConfig(
        mode=mode_map.get(mode, StructureRandomizationMode.STANDARD)
    )

    return StructureRandomizer(program, rng, config)


def generate_randomized_program(
    program: BlockProgram,
    rng: random.Random,
    mode: str = "standard"
) -> tuple[str, dict]:
    """便捷函数：生成随机化程序"""
    randomizer = create_structure_randomizer(program, rng, mode)
    return randomizer.generate_program()


def demo_structure_variants(program: BlockProgram, rng: random.Random) -> dict[str, tuple[str, dict]]:
    """演示所有结构变体"""
    results = {}

    for mode in StructureRandomizationMode:
        randomizer = StructureRandomizer(program, rng, StructureRandomizationConfig(mode=mode))
        code, stats = randomizer.generate_program()
        results[mode.value] = (code, stats)

    return results


# ===== 统一 Block 调度架构 =====


class JumpTransform(Enum):
    """跳转变换类型"""
    NONE = "none"                        # 无变换
    XOR = "xor"                          # 异或变换
    OFFSET = "offset"                    # 偏移变换
    NEGATE = "negate"                    # 取反变换
    SWAP = "swap"                        # 交换变换
    MODULO = "modulo"                    # 取模变换


@dataclass
class JumpTransformConfig:
    """跳转变换配置"""
    transform_type: JumpTransform = JumpTransform.NONE
    transform_key: int = 0x5A
    offset_base: int = 100
    swap_table: dict[int, int] | None = None


class BlockJumpResolver:
    """
    Block 跳转解析器

    负责将 block 返回的中间值转换为下一个 block ID
    """

    def __init__(self, program: BlockProgram, config: JumpTransformConfig | None = None):
        self.program = program
        self.config = config if config else JumpTransformConfig()
        self._build_resolution_map()

    def _build_resolution_map(self) -> None:
        """构建解析映射表"""
        self.resolution_map: dict[int, int] = {}
        for block in self.program.blocks:
            if block.next_id is not None:
                self.resolution_map[block.block_id] = block.next_id

    def resolve(self, raw_id: int) -> int:
        """
        解析原始 ID

        Args:
            raw_id: block 返回的原始值

        Returns:
            解析后的 block ID
        """
        if self.config.transform_type == JumpTransform.NONE:
            return raw_id
        if self.config.transform_type == JumpTransform.XOR:
            return raw_id ^ self.config.transform_key
        if self.config.transform_type == JumpTransform.OFFSET:
            return raw_id - self.config.offset_base
        if self.config.transform_type == JumpTransform.NEGATE:
            return -raw_id
        if self.config.transform_type == JumpTransform.MODULO:
            return raw_id % max(len(self.program.blocks), 1)
        if self.config.transform_type == JumpTransform.SWAP and self.config.swap_table:
            return self.config.swap_table.get(raw_id, raw_id)
        return raw_id

    def generate_resolution_function(self) -> str:
        """生成解析函数"""
        lines = []

        if self.config.transform_type == JumpTransform.NONE:
            lines.append("local function _resolve(id) return id end")
        elif self.config.transform_type == JumpTransform.XOR:
            lines.append(f"local _xor_key = {self.config.transform_key}")
            lines.append("local function _resolve(id) return id ~ _xor_key end")
        elif self.config.transform_type == JumpTransform.OFFSET:
            lines.append(f"local _offset_base = {self.config.offset_base}")
            lines.append("local function _resolve(id) return id - _offset_base end")
        elif self.config.transform_type == JumpTransform.NEGATE:
            lines.append("local function _resolve(id) return -id end")
        elif self.config.transform_type == JumpTransform.MODULO:
            max_val = max(len(self.program.blocks), 1)
            lines.append(f"local _modulo = {max_val}")
            lines.append("local function _resolve(id) return id % _modulo end")
        elif self.config.transform_type == JumpTransform.SWAP and self.config.swap_table:
            lines.append("local _swap = {")
            for k, v in self.config.swap_table.items():
                lines.append(f"    [{k}] = {v},")
            lines.append("}")
            lines.append("local function _resolve(id) return _swap[id] or id end")

        return "\n".join(lines)


class UnifiedDispatchFunction:
    """
    统一调度函数

    封装所有 block 调度的核心逻辑，提供清晰的调度接口
    """

    def __init__(
        self,
        program: BlockProgram,
        rng: random.Random | None = None,
        transform_config: JumpTransformConfig | None = None
    ):
        self.program = program
        self.rng = rng
        self.transform_config = transform_config if transform_config else JumpTransformConfig()
        self.resolver = BlockJumpResolver(program, self.transform_config)

        pc_var = f"_pc{rng.randint(1000, 9999)}" if rng else "_pc"
        tbl_var = f"_tbl{rng.randint(1000, 9999)}" if rng else "_tbl"
        disp_var = f"_dispatch{rng.randint(1000, 9999)}" if rng else "_dispatch"

        self._pc = pc_var
        self._tbl = tbl_var
        self._dispatch = disp_var

    def generate_block_table(self) -> str:
        """生成 block 表"""
        lines = []
        lines.append(f"local {self._tbl} = {{}}")
        for idx, bid in enumerate(self.program.execution_order):
            block = self.program.get_block(bid)
            if block:
                func_name = f"_fn_{bid}"
                lines.append(f"{self._tbl}[{bid}] = {func_name}")
        return "\n".join(lines)

    def generate_block_functions(self) -> str:
        """生成 block 函数（返回中间值）"""
        lines = []
        for bid in self.program.execution_order:
            block = self.program.get_block(bid)
            if block:
                func_name = f"_fn_{bid}"
                lines.append(f"local function {func_name}()")
                if block.content.strip():
                    for ln in block.content.strip().split("\n"):
                        lines.append(f"    {ln}")
                next_id = block.next_id if block.next_id else "nil"
                lines.append(f"    return {next_id}")
                lines.append("end")
                lines.append("")
        return "\n".join(lines)

    def generate_resolver_function(self) -> str:
        """生成解析函数"""
        return self.resolver.generate_resolution_function()

    def generate_dispatch_function(self) -> str:
        """生成调度函数"""
        lines = []
        lines.append(f"local function {self._dispatch}(pc)")
        lines.append(f"    local block = {self._tbl}[pc]")
        lines.append(f"    if not block then return end")
        lines.append(f"    local raw_id = block()")
        lines.append(f"    return _resolve(raw_id)")
        lines.append("end")
        return "\n".join(lines)

    def generate_executor(self) -> str:
        """生成执行器"""
        lines = []
        lines.append(f"local {self._pc} = {self.program.entry_block_id}")
        lines.append(f"while {self._pc} do")
        lines.append(f"    {self._pc} = {self._dispatch}({self._pc})")
        lines.append("end")
        return "\n".join(lines)

    def generate_complete_program(self) -> str:
        """生成完整的程序"""
        lines = []
        lines.append("-- Block Table")
        lines.append(self.generate_block_table())
        lines.append("")
        lines.append("-- Block Functions")
        lines.append(self.generate_block_functions())
        lines.append("-- Jump Resolver")
        lines.append(self.generate_resolver_function())
        lines.append("")
        lines.append("-- Dispatch Function")
        lines.append(self.generate_dispatch_function())
        lines.append("")
        lines.append("-- Executor")
        lines.append(self.generate_executor())
        return "\n".join(lines)


class ModularDispatchArchitecture:
    """
    模块化调度架构

    将调度逻辑拆分为独立的模块：
    1. Block 函数 - 返回中间值
    2. 跳转解析器 - 将中间值转换为 block ID
    3. 调度函数 - 执行一次跳转
    4. 执行器 - 循环执行调度
    """

    def __init__(
        self,
        program: BlockProgram,
        rng: random.Random | None = None,
        transform: JumpTransform = JumpTransform.NONE,
        transform_key: int = 0x5A,
        offset_base: int = 100
    ):
        self.program = program
        self.rng = rng
        config = JumpTransformConfig(
            transform_type=transform,
            transform_key=transform_key,
            offset_base=offset_base
        )
        if transform == JumpTransform.SWAP:
            config.swap_table = self._generate_swap_table()
        self.dispatch = UnifiedDispatchFunction(program, rng, config)

    def _generate_swap_table(self) -> dict[int, int]:
        """生成交换表"""
        ids = [b.block_id for b in self.program.blocks if b.next_id is not None]
        swap = {}
        for i, bid in enumerate(ids):
            if i + 1 < len(ids):
                swap[bid] = ids[i + 1]
            elif ids:
                swap[bid] = ids[0]
        return swap

    def generate(self) -> str:
        """生成完整程序"""
        return self.dispatch.generate_complete_program()

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_blocks": len(self.program.blocks),
            "transform": self.dispatch.transform_config.transform_type.value,
            "has_resolver": self.dispatch.transform_config.transform_type != JumpTransform.NONE,
        }


def create_dispatch_architecture(
    program: BlockProgram,
    rng: random.Random,
    transform: str = "none"
) -> ModularDispatchArchitecture:
    """创建模块化调度架构"""
    transform_map = {
        "none": JumpTransform.NONE,
        "xor": JumpTransform.XOR,
        "offset": JumpTransform.OFFSET,
        "negate": JumpTransform.NEGATE,
        "swap": JumpTransform.SWAP,
        "modulo": JumpTransform.MODULO,
    }
    transform_type = transform_map.get(transform, JumpTransform.NONE)
    transform_key = rng.randint(1, 255) if rng else 0x5A
    offset_base = rng.randint(50, 200) if rng else 100
    return ModularDispatchArchitecture(
        program=program, rng=rng,
        transform=transform_type,
        transform_key=transform_key,
        offset_base=offset_base
    )


def generate_with_unified_dispatch(
    program: BlockProgram,
    rng: random.Random,
    transform: str = "none"
) -> str:
    """便捷函数：使用统一调度架构生成程序"""
    arch = create_dispatch_architecture(program, rng, transform)
    return arch.generate()


def demo_dispatch_architectures(program: BlockProgram, rng: random.Random) -> dict[str, str]:
    """演示所有调度架构"""
    results = {}
    for transform in JumpTransform:
        arch = create_dispatch_architecture(program, rng, transform.value)
        results[transform.value] = arch.generate()
    return results


# ===== 指令到 Lua Table 的序列化 =====


class InstructionSerializer:
    """
    指令序列化器

    将 Instruction 列表转换为 Lua table 字符串，
    支持跨语言验证和调试。
    """

    # Opcode 到数字 ID 的映射
    OPCODE_TO_ID: dict[str, int] = {
        "nop": 0,
        "declare": 1,
        "init": 2,
        "assign": 3,
        "call": 4,
        "call_assign": 5,
        "return": 6,
        "return_val": 7,
        "jump": 8,
        "jump_if": 9,
        "do": 10,
        "end": 11,
        "if": 12,
        "then": 13,
        "else": 14,
        "elseif": 15,
        "while": 16,
        "for": 17,
        "repeat": 18,
        "until": 19,
        "break": 20,
        "continue": 21,
        "func_def": 22,
        "func_end": 23,
        "expr": 24,
        "error": 25,
        "table_new": 26,
        "table_set": 27,
        "table_get": 28,
        "label": 29,
        "identity": 30,
        "dummy": 31,
        "comment": 32,
        "assert": 33,
    }

    def __init__(self, compact: bool = True, include_metadata: bool = False):
        """
        Args:
            compact: 是否使用紧凑格式（数字 opcode）
            include_metadata: 是否包含元数据
        """
        self.compact = compact
        self.include_metadata = include_metadata

    def opcode_to_id(self, opcode: OpCode) -> int:
        """将 OpCode 转换为数字 ID"""
        return self.OPCODE_TO_ID.get(opcode.value, 99)

    def serialize_value(self, value: Any) -> str:
        """
        序列化单个值

        支持: int, float, str, bool, None, list
        """
        if value is None:
            return "nil"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            # Lua 兼容的浮点数格式
            if value == float('inf'):
                return "math.huge"
            if value == float('-inf'):
                return "-math.huge"
            return str(value)
        if isinstance(value, str):
            # 简单标识符直接使用
            if self._is_simple_identifier(value):
                return value
            # 否则转义为 Lua 字符串
            return self._escape_string(value)
        if isinstance(value, list):
            # 嵌套数组
            items = [self.serialize_value(v) for v in value]
            return "{" + ", ".join(items) + "}"
        # fallback
        return f'"{value}"'

    def _is_simple_identifier(self, s: str) -> bool:
        """检查是否为简单的 Lua 标识符"""
        if not s:
            return False
        if s[0].isdigit():
            return False
        # 允许字母、数字、下划线，不含空格和特殊字符
        import re
        return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', s))

    def _escape_string(self, s: str) -> str:
        """转义字符串为 Lua 格式"""
        # 简单转义
        s = s.replace('\\', '\\\\')
        s = s.replace('"', '\\"')
        s = s.replace('\n', '\\n')
        s = s.replace('\r', '\\r')
        s = s.replace('\t', '\\t')
        return f'"{s}"'

    def serialize_instruction(self, instr: Instruction) -> str:
        """
        序列化单条指令

        格式: {op_id, arg1, arg2, ..., [result=]}
        """
        if self.compact:
            # 紧凑格式: {op_id, arg1, arg2, ...}
            op_id = self.opcode_to_id(instr.op)
            items = [str(op_id)]
            for arg in instr.args:
                items.append(self.serialize_value(arg))
            if instr.result:
                items.append(self.serialize_value(instr.result))
            return "{" + ", ".join(items) + "}"
        else:
            # 带名称格式: {op = "name", args = {...}, result = x}
            op_name = f'"{instr.op.value}"'
            args_str = "{" + ", ".join(self.serialize_value(a) for a in instr.args) + "}"
            result_str = f", result = {self.serialize_value(instr.result)}" if instr.result else ""
            meta_str = ""
            if self.include_metadata and instr.metadata:
                meta_items = [f'"{k}" = {self.serialize_value(v)}' for k, v in instr.metadata.items()]
                meta_str = ", metadata = {" + ", ".join(meta_items) + "}"
            return "{" + op_name + ", args = " + args_str + result_str + meta_str + "}"

    def serialize(
        self,
        instructions: list[Instruction],
        var_name: str = "code"
    ) -> str:
        """
        序列化指令列表为 Lua table 字符串

        Args:
            instructions: 指令列表
            var_name: Lua 变量名

        Returns:
            Lua table 代码字符串
        """
        lines = [f"local {var_name} = {{"] if var_name else ["{"]

        for i, instr in enumerate(instructions):
            # 添加可选的行号注释
            if self.include_metadata and instr.metadata:
                line_no = instr.metadata.get("line")
                comment = f"  -- line {line_no}" if line_no else ""
            else:
                comment = ""
            lines.append(f"    {self.serialize_instruction(instr)},{comment}")

        lines.append("}")
        return "\n".join(lines)

    def serialize_with_meta(
        self,
        instructions: list[Instruction],
        var_name: str = "code"
    ) -> str:
        """序列化并包含额外元数据"""
        self.include_metadata = True
        return self.serialize(instructions, var_name)


def instructions_to_lua_table(
    instructions: list[Instruction],
    var_name: str = "code",
    compact: bool = True,
    include_opcode_map: bool = False
) -> str:
    """
    将指令列表转换为 Lua table 字符串

    Args:
        instructions: 指令列表
        var_name: Lua 变量名
        compact: 是否使用紧凑格式
        include_opcode_map: 是否包含 opcode 映射表

    Returns:
        Lua table 代码字符串

    Example output:
        local code = {
            {2, "x", 10},      -- INIT: local x = 10
            {3, "x", "x+1"},   -- ASSIGN: x = x + 1
            {7, "x"},          -- RETURN_VAL: return x
        }
    """
    serializer = InstructionSerializer(compact=compact, include_metadata=False)
    lua_code = serializer.serialize(instructions, var_name)

    if include_opcode_map:
        meta_lines = [lua_code, ""]
        meta_lines.append("local _opcodes = {")
        for name, id_val in InstructionSerializer.OPCODE_TO_ID.items():
            meta_lines.append(f'    ["{name}"] = {id_val},')
        meta_lines.append("}")
        return "\n".join(meta_lines)

    return lua_code


def instructions_to_lua_snippet(
    instructions: list[Instruction],
    var_name: str = "code"
) -> str:
    """
    将指令列表转换为 Lua snippet（不包含 local 声明）

    Args:
        instructions: 指令列表
        var_name: 变量名（用于生成 _code = {...} 格式）

    Returns:
        Lua snippet 字符串
    """
    serializer = InstructionSerializer(compact=True)
    return serializer.serialize(instructions, var_name)


class LuaTableEmitter:
    """
    Lua Table 发射器

    在代码生成流程中集成指令序列化，
    支持将序列化结果嵌入到最终 Lua 代码中。
    """

    def __init__(
        self,
        serializer: InstructionSerializer | None = None,
        embed_in_code: bool = True
    ):
        self.serializer = serializer or InstructionSerializer()
        self.embed_in_code = embed_in_code
        self._serialized_cache: dict[int, str] = {}

    def emit_instruction_table(
        self,
        instructions: list[Instruction],
        var_name: str = "_instr_table"
    ) -> str:
        """
        发射指令表

        Returns:
            Lua table 代码块
        """
        return self.serializer.serialize(instructions, var_name)

    def emit_with_loader(
        self,
        instructions: list[Instruction],
        func_name: str = "_load_instructions"
    ) -> str:
        """
        发射带加载函数的指令表

        Returns:
            包含加载函数的完整 Lua 代码块
        """
        lines = []
        lines.append(self.emit_instruction_table(instructions))
        lines.append("")
        lines.append(f"local function {func_name}()")
        lines.append(f"    return _instr_table")
        lines.append("end")
        return "\n".join(lines)

    def emit_debug_info(
        self,
        instructions: list[Instruction]
    ) -> str:
        """
        发射带调试信息的指令表

        包含 opcode 映射和行号信息
        """
        self.serializer.include_metadata = True
        lines = []
        lines.append("-- Instruction Table (Debug Mode)")
        lines.append(self.serializer.serialize(instructions, "_debug_code"))
        lines.append("")
        lines.append("local _opcodes = {")
        for name, id_val in InstructionSerializer.OPCODE_TO_ID.items():
            lines.append(f'    ["{name}"] = {id_val},')
        lines.append("}")
        lines.append("")
        lines.append("local function _decode(instr)")
        lines.append("    local op_id = instr[1]")
        lines.append("    for name, id in pairs(_opcodes) do")
        lines.append("        if id == op_id then")
        lines.append('            return name, instr[2], instr[3], instr[4]')
        lines.append("        end")
        lines.append("    end")
        lines.append('    return "unknown"')
        lines.append("end")
        self.serializer.include_metadata = False
        return "\n".join(lines)

    def inject_into_template(
        self,
        instructions: list[Instruction],
        template: str,
        marker: str = "-- INSTRUCTION_TABLE"
    ) -> str:
        """
        将指令表注入到代码模板中

        Args:
            instructions: 指令列表
            template: 代码模板字符串
            marker: 注入标记

        Returns:
            替换后的模板代码
        """
        table_code = self.emit_instruction_table(instructions)
        if marker in template:
            return template.replace(marker, table_code)
        # 如果找不到 marker，追加到开头
        return table_code + "\n\n" + template


def create_table_emitter(
    compact: bool = True,
    include_debug: bool = False
) -> LuaTableEmitter:
    """创建 Lua Table 发射器"""
    serializer = InstructionSerializer(
        compact=compact,
        include_metadata=include_debug
    )
    return LuaTableEmitter(serializer=serializer)


# 便捷函数
def emit_lua_table(
    instructions: list[Instruction],
    var_name: str = "code",
    compact: bool = True
) -> str:
    """便捷函数：发射 Lua table"""
    serializer = InstructionSerializer(compact=compact)
    return serializer.serialize(instructions, var_name)


def emit_lua_table_with_map(
    instructions: list[Instruction],
    var_name: str = "code"
) -> str:
    """便捷函数：发射带 opcode 映射的 Lua table"""
    return instructions_to_lua_table(
        instructions,
        var_name=var_name,
        compact=True,
        include_opcode_map=True
    )


# 示例用法
def demo_instruction_serialization():
    """演示指令序列化"""
    print("=" * 50)
    print("Instruction Serialization Demo")
    print("=" * 50)

    # 创建示例指令
    instructions = [
        Instruction(OpCode.INIT, ["x"], None, "10"),
        Instruction(OpCode.INIT, ["y"], None, "20"),
        Instruction(OpCode.ASSIGN, ["sum"], None, "x + y"),
        Instruction(OpCode.RETURN_VAL, ["sum"]),
    ]

    print("\n[1] Compact format:")
    print(instructions_to_lua_table(instructions))

    print("\n[2] With opcode map:")
    print(instructions_to_lua_table(instructions, include_opcode_map=True))

    print("\n[3] Using LuaTableEmitter:")
    emitter = create_table_emitter(compact=True, include_debug=True)
    print(emitter.emit_debug_info(instructions))

    # 测试 ControlFlowIR 序列化
    print("\n[4] Testing ControlFlowIR serialization:")
    from dataclasses import dataclass, field

    @dataclass
    class SimpleIR:
        blocks: dict[int, list[Instruction]] = field(default_factory=dict)

    ir = SimpleIR()
    ir.blocks[0] = [
        Instruction(OpCode.DECLARE, ["i"]),
        Instruction(OpCode.INIT, ["i"], None, "0"),
    ]
    ir.blocks[1] = [
        Instruction(OpCode.ASSIGN, ["i"], None, "i + 1"),
    ]

    all_instrs = []
    for block_id in sorted(ir.blocks.keys()):
        all_instrs.extend(ir.blocks[block_id])

    print(instructions_to_lua_table(all_instrs, var_name="_ir_code"))

    print("\n" + "=" * 50)
    print("Demo Complete")
    print("=" * 50)


if __name__ == "__main__":
    demo_instruction_serialization()


# ===== Lua 指令解释器生成器 =====


class LuaInterpreterGenerator:
    """
    Lua 指令解释器生成器

    生成可以在 Lua 端执行的指令解释器代码，
    用于验证 instruction 序列的执行逻辑。
    """

    def __init__(
        self,
        include_debug: bool = False,
        pc_starts_at: int = 1  # Lua 数组从 1 开始
    ):
        self.include_debug = include_debug
        self.pc_starts_at = pc_starts_at
        self._opcodes = InstructionSerializer.OPCODE_TO_ID

    def generate_context_table(self, var_name: str = "state") -> str:
        """
        生成执行上下文表

        用于存储局部变量、全局变量、返回值等
        """
        lines = []
        lines.append(f"local {var_name} = {{")
        lines.append("    -- 执行上下文")
        lines.append("    locals = {},     -- 局部变量")
        lines.append("    globals = {},    -- 全局变量")
        lines.append("    stack = {},      -- 值栈（用于函数调用）")
        lines.append("    pc = 1,         -- 程序计数器")
        lines.append("    halted = false,  -- 执行结束标志")
        lines.append("    return_value = nil,")
        lines.append("}")
        lines.append("")
        lines.append(f"local function {var_name}_get(varname)")
        lines.append(f"    if {var_name}.locals[varname] ~= nil then")
        lines.append(f"        return {var_name}.locals[varname]")
        lines.append("    end")
        lines.append(f"    if {var_name}.globals[varname] ~= nil then")
        lines.append(f"        return {var_name}.globals[varname]")
        lines.append("    end")
        lines.append("    return nil")
        lines.append("end")
        lines.append("")
        lines.append(f"local function {var_name}_set(varname, value)")
        lines.append(f"    {var_name}.locals[varname] = value")
        lines.append("end")
        lines.append("")
        lines.append(f"local function {var_name}_push(value)")
        lines.append(f"    table.insert({var_name}.stack, value)")
        lines.append("end")
        lines.append("")
        lines.append(f"local function {var_name}_pop()")
        lines.append(f"    return table.remove({var_name}.stack)")
        lines.append("end")
        return "\n".join(lines)

    def _generate_value_evaluation(self, value: Any) -> str:
        """生成值评估代码"""
        if value is None:
            return "nil"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            # 检查是否为简单标识符
            if value.replace("_", "").replace(" ", "").isalnum():
                # 简单标识符或表达式 - 直接使用
                return value
            # 字符串字面量
            escaped = value.replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped}"'
        return f'"{value}"'

    def generate_handlers(self) -> str:
        """
        生成指令处理器表

        每个 opcode 对应一个 handler 函数
        """
        lines = []
        lines.append("local handlers = {")
        lines.append("    -- opcode: 0 (nop) - 空操作")
        lines.append("    [0] = function(instr, state)")
        lines.append("        return state.pc + 1")
        lines.append("    end,")
        lines.append("")
        lines.append("    -- opcode: 1 (declare) - 声明变量")
        lines.append("    [1] = function(instr, state)")
        lines.append("        local varname = instr[2]")
        lines.append("        state.locals[varname] = nil")
        lines.append("        return state.pc + 1")
        lines.append("    end,")
        lines.append("")
        lines.append("    -- opcode: 2 (init) - 初始化变量")
        lines.append("    [2] = function(instr, state)")
        lines.append("        local varname = instr[2]")
        lines.append("        local value = instr[3]")
        lines.append("        if type(value) == 'string' and value:match('^[a-zA-Z_]') then")
        lines.append("            value = state_get(value) or 0")
        lines.append("        end")
        lines.append("        state_set(varname, value)")
        lines.append("        return state.pc + 1")
        lines.append("    end,")
        lines.append("")
        lines.append("    -- opcode: 3 (assign) - 赋值")
        lines.append("    [3] = function(instr, state)")
        lines.append("        local varname = instr[2]")
        lines.append("        local expr = instr[3]")
        lines.append("        -- 简单表达式求值")
        lines.append("        if type(expr) == 'string' then")
        lines.append("            -- 检查是否为简单变量引用")
        lines.append("            local var_value = state_get(expr)")
        lines.append("            if var_value ~= nil then")
        lines.append("                state_set(varname, var_value)")
        lines.append("            else")
        lines.append("                -- 尝试算术表达式")
        lines.append("                local x = expr:match('^(%w+)%s*%+')")
        lines.append("                if x then")
        lines.append("                    local rest = expr:match('^%w+%s*%+(.+)$')")
        lines.append("                    if rest then")
        lines.append("                        local v1 = state_get(x) or 0")
        lines.append("                        state_set(varname, v1 + tonumber(rest))")
        lines.append("                    end")
        lines.append("                else")
        lines.append("                    state_set(varname, tonumber(expr) or expr)")
        lines.append("                end")
        lines.append("            end")
        lines.append("        else")
        lines.append("            state_set(varname, expr)")
        lines.append("        end")
        lines.append("        return state.pc + 1")
        lines.append("    end,")
        lines.append("")
        lines.append("    -- opcode: 4 (call) - 函数调用")
        lines.append("    [4] = function(instr, state)")
        lines.append("        local funcname = instr[2]")
        lines.append("        local func = state_get(funcname)")
        lines.append("        if type(func) == 'function' then")
        lines.append("            local args = {}")
        lines.append("            for i = 4, #instr do")
        lines.append("                table.insert(args, instr[i])")
        lines.append("            end")
        lines.append("            local ok, result = pcall(func, unpack(args))")
        lines.append("            if ok then state_push(result) end")
        lines.append("        end")
        lines.append("        return state.pc + 1")
        lines.append("    end,")
        lines.append("")
        lines.append("    -- opcode: 5 (call_assign) - 调用赋值")
        lines.append("    [5] = function(instr, state)")
        lines.append("        local varname = instr[2]")
        lines.append("        local result = state_pop()")
        lines.append("        state_set(varname, result)")
        lines.append("        return state.pc + 1")
        lines.append("    end,")
        lines.append("")
        lines.append("    -- opcode: 6 (return) - 返回空")
        lines.append("    [6] = function(instr, state)")
        lines.append("        state.halted = true")
        lines.append("        return nil")
        lines.append("    end,")
        lines.append("")
        lines.append("    -- opcode: 7 (return_val) - 返回值")
        lines.append("    [7] = function(instr, state)")
        lines.append("        local val = instr[2]")
        lines.append("        if type(val) == 'string' then")
        lines.append("            val = state_get(val) or val")
        lines.append("        end")
        lines.append("        state.return_value = val")
        lines.append("        state.halted = true")
        lines.append("        return nil")
        lines.append("    end,")
        lines.append("")
        lines.append("    -- opcode: 8 (jump) - 无条件跳转")
        lines.append("    [8] = function(instr, state)")
        lines.append("        local target = instr[2]")
        lines.append("        if type(target) == 'number' then")
        lines.append("            return target")
        lines.append("        end")
        lines.append("        return state.pc + 1")
        lines.append("    end,")
        lines.append("")
        lines.append("    -- opcode: 9 (jump_if) - 条件跳转")
        lines.append("    [9] = function(instr, state)")
        lines.append("        local cond_expr = instr[2]")
        lines.append("        local target = instr[3]")
        lines.append("        -- 简单条件判断")
        lines.append("        local cond_value = cond_expr")
        lines.append("        if type(cond_expr) == 'string' then")
        lines.append("            cond_value = state_get(cond_expr)")
        lines.append("            if cond_value == nil then")
        lines.append("                -- 尝试解析表达式")
        lines.append("                local var, op, num = cond_expr:match('^(%w+)%s*(<[%=]?)%s*(%d+)$')")
        lines.append("                if var and op then")
        lines.append("                    local v = state_get(var) or 0")
        lines.append("                    local n = tonumber(num)")
        lines.append("                    if op == '<' then cond_value = v < n")
        lines.append("                    elseif op == '<=' then cond_value = v <= n")
        lines.append("                    elseif op == '=' then cond_value = v == n")
        lines.append("                    end")
        lines.append("                end")
        lines.append("            end")
        lines.append("        end")
        lines.append("        if cond_value then")
        lines.append("            return target")
        lines.append("        end")
        lines.append("        return state.pc + 1")
        lines.append("    end,")
        lines.append("")
        lines.append("    -- opcode: 16 (while) - while 循环开始")
        lines.append("    [16] = function(instr, state)")
        lines.append("        return state.pc + 1")
        lines.append("    end,")
        lines.append("")
        lines.append("    -- opcode: 19 (until) - until 条件")
        lines.append("    [19] = function(instr, state)")
        lines.append("        local cond_expr = instr[2]")
        lines.append("        local cond_value = state_get(cond_expr)")
        lines.append("        if cond_value then")
        lines.append("            return state.pc + 1  -- 条件为真，退出循环")
        lines.append("        end")
        lines.append("        return instr[3] or (state.pc - 1)  -- 条件为假，跳回")
        lines.append("    end,")
        lines.append("")
        lines.append("    -- opcode: 20 (break) - 跳出循环")
        lines.append("    [20] = function(instr, state)")
        lines.append("        return instr[2] or nil  -- 跳到指定位置")
        lines.append("    end,")
        lines.append("")
        lines.append("    -- opcode: 24 (expr) - 表达式语句")
        lines.append("    [24] = function(instr, state)")
        lines.append("        -- 执行表达式，丢弃结果")
        lines.append("        return state.pc + 1")
        lines.append("    end,")
        lines.append("")
        lines.append("    -- opcode: 26 (table_new) - 创建表")
        lines.append("    [26] = function(instr, state)")
        lines.append("        state_push({})")
        lines.append("        return state.pc + 1")
        lines.append("    end,")
        lines.append("")
        lines.append("    -- opcode: 27 (table_set) - 设置表元素")
        lines.append("    [27] = function(instr, state)")
        lines.append("        local key = instr[2]")
        lines.append("        local value = instr[3]")
        lines.append("        local tbl = state_pop()")
        lines.append("        if tbl and type(tbl) == 'table' then")
        lines.append("            tbl[key] = value")
        lines.append("        end")
        lines.append("        state_push(tbl)")
        lines.append("        return state.pc + 1")
        lines.append("    end,")
        lines.append("")
        lines.append("    -- opcode: 29 (label) - 标签")
        lines.append("    [29] = function(instr, state)")
        lines.append("        return state.pc + 1")
        lines.append("    end,")
        lines.append("")
        lines.append("    -- 默认处理器")
        lines.append("    default = function(instr, state)")
        lines.append("        if _DEBUG then")
        lines.append("            print('Unknown opcode: ' .. tostring(instr[1]))")
        lines.append("        end")
        lines.append("        return state.pc + 1")
        lines.append("    end,")
        lines.append("}")
        return "\n".join(lines)

    def generate_executor(
        self,
        code_var: str = "code",
        state_var: str = "state",
        result_var: str = "_result"
    ) -> str:
        """
        生成执行器主循环

        核心执行逻辑：
        1. 从 code[pc] 读取指令
        2. 根据 opcode 分发到 handler
        3. handler 返回下一个 pc
        """
        lines = []
        lines.append("local function execute()")
        lines.append("    local pc = " + str(self.pc_starts_at))
        lines.append(f"    local {state_var}_pc_backup = 0")
        lines.append("")
        lines.append("    while pc do")
        lines.append(f"        {state_var}_pc_backup = pc")
        lines.append(f"        local instr = {code_var}[pc]")
        lines.append("")
        lines.append("        if not instr then")
        lines.append("            break  -- 无效指令")
        lines.append("        end")
        lines.append("")
        lines.append("        local op = instr[1]")
        lines.append("        local handler = handlers[op] or handlers.default")
        lines.append(f"        state.pc = pc")
        lines.append(f"        pc = handler(instr, {state_var})")
        lines.append("")
        lines.append(f"        if {state_var}.halted then")
        lines.append("            break")
        lines.append("        end")
        lines.append("")
        lines.append("        -- 安全检查，防止无限循环")
        lines.append("        if pc == " + str(self.pc_starts_at) + " then")
        lines.append("            break  -- 回到开头，可能有问题")
        lines.append("        end")
        lines.append("    end")
        lines.append("")
        lines.append(f"    return {state_var}.return_value")
        lines.append("end")
        lines.append("")
        lines.append(f"local {result_var} = execute()")
        lines.append(f'if _DEBUG then print("Result: " .. tostring({result_var})) end')
        return "\n".join(lines)

    def generate_debug_info(self) -> str:
        """生成调试信息函数"""
        lines = []
        lines.append("-- 调试函数")
        lines.append("local function dump_state(state)")
        lines.append("    print('--- State ---')")
        lines.append("    print('PC: ' .. tostring(state.pc))")
        lines.append("    print('Locals:')")
        lines.append("    for k, v in pairs(state.locals) do")
        lines.append("        print('  ' .. k .. ' = ' .. tostring(v))")
        lines.append("    end")
        lines.append("    print('Stack: ' .. #state.stack .. ' items')")
        lines.append("end")
        lines.append("")
        lines.append("local function dump_instr(instr)")
        lines.append("    local op_names = {")
        for name, id_val in sorted(self._opcodes.items(), key=lambda x: x[1]):
            lines.append(f'        [{id_val}] = "{name}",')
        lines.append("    }")
        lines.append("    local op_name = op_names[instr[1]] or 'unknown'")
        lines.append("    local args = {}")
        lines.append("    for i = 2, #instr do")
        lines.append("        table.insert(args, tostring(instr[i]))")
        lines.append("    end")
        lines.append('    return string.format("[%s] %s", op_name, table.concat(args, ", "))')
        lines.append("end")
        lines.append("")
        lines.append("local function step_execute(code, state)")
        lines.append("    local pc = 1")
        lines.append("    while pc and not state.halted do")
        lines.append("        local instr = code[pc]")
        lines.append("        print('PC=' .. pc .. ': ' .. dump_instr(instr))")
        lines.append("        local op = instr[1]")
        lines.append("        local handler = handlers[op] or handlers.default")
        lines.append("        state.pc = pc")
        lines.append("        pc = handler(instr, state)")
        lines.append("        dump_state(state)")
        lines.append("        print('---')")
        lines.append("    end")
        lines.append("    return state.return_value")
        lines.append("end")
        return "\n".join(lines)

    def generate(
        self,
        instructions: list[Instruction] | None = None,
        include_code: bool = True,
        include_debug: bool = False
    ) -> str:
        """
        生成完整的 Lua 解释器代码

        Args:
            instructions: 指令列表（可选）
            include_code: 是否包含指令数据表
            include_debug: 是否包含调试信息

        Returns:
            完整的 Lua 代码字符串
        """
        lines = []

        # Header
        lines.append("-- =========================================")
        lines.append("-- Lua Instruction Interpreter")
        lines.append("-- Generated by lua_obfuscator")
        lines.append("-- =========================================")
        lines.append("")

        # 调试开关
        lines.append("local _DEBUG = false")
        lines.append("")

        # 快捷函数别名
        lines.append("local state_get = state_get")
        lines.append("local state_set = state_set")
        lines.append("local state_push = state_push")
        lines.append("local state_pop = state_pop")
        lines.append("")

        # 处理器表
        lines.append("-- Instruction Handlers")
        lines.append(self.generate_handlers())
        lines.append("")

        # 调试函数
        if include_debug:
            lines.append(self.generate_debug_info())
            lines.append("")

        # 指令数据
        if include_code and instructions:
            serializer = InstructionSerializer(compact=True)
            lines.append("-- Instruction Code")
            lines.append(serializer.serialize(instructions, "code"))
            lines.append("")

            # 执行上下文
            lines.append(self.generate_context_table("state"))
            lines.append("")

            # 执行器
            lines.append("-- Executor")
            lines.append(self.generate_executor("code", "state", "_result"))
        else:
            # 仅生成骨架
            lines.append("-- Instruction Code (placeholder)")
            lines.append("-- local code = {...}")
            lines.append("")
            lines.append("-- Execution Context")
            lines.append(self.generate_context_table("state"))
            lines.append("")
            lines.append("-- Executor (placeholder)")
            lines.append("-- execute()")

        return "\n".join(lines)


def generate_lua_interpreter(
    instructions: list[Instruction] | None = None,
    include_code: bool = True,
    include_debug: bool = False
) -> str:
    """
    便捷函数：生成 Lua 解释器代码

    Args:
        instructions: 指令列表
        include_code: 是否包含指令数据
        include_debug: 是否包含调试信息

    Returns:
        Lua 代码字符串
    """
    generator = LuaInterpreterGenerator(include_debug=include_debug)
    return generator.generate(instructions, include_code=include_code)


class LuaInterpreterEmitter:
    """
    Lua 解释器发射器

    用于在代码生成流程中集成 Lua 解释器
    """

    def __init__(
        self,
        generator: LuaInterpreterGenerator | None = None
    ):
        self.generator = generator or LuaInterpreterGenerator()

    def emit_interpreter(
        self,
        instructions: list[Instruction],
        standalone: bool = True
    ) -> str:
        """发射解释器代码"""
        return self.generator.generate(
            instructions=instructions,
            include_code=standalone,
            include_debug=True
        )

    def emit_inline_interpreter(
        self,
        instructions: list[Instruction],
        template: str,
        marker: str = "-- INTERPRETER"
    ) -> str:
        """将解释器注入到模板中"""
        interp_code = self.emit_interpreter(instructions, standalone=False)
        if marker in template:
            return template.replace(marker, interp_code)
        return interp_code + "\n\n" + template

    def emit_with_validation(
        self,
        instructions: list[Instruction]
    ) -> str:
        """发射带验证逻辑的解释器"""
        interp = self.generator.generate(instructions, include_code=True)
        validation = """
-- Validation: Compare with expected result
local _EXPECTED = nil  -- Set expected value here
if _EXPECTED and _result ~= _EXPECTED then
    error(string.format("Validation failed: expected %s, got %s",
        tostring(_EXPECTED), tostring(_result)))
end
"""
        return interp + "\n" + validation


def demo_lua_interpreter():
    """演示 Lua 解释器生成"""
    print("=" * 60)
    print("Lua Interpreter Generation Demo")
    print("=" * 60)

    # 示例指令序列
    instructions = [
        Instruction(OpCode.INIT, ["x"], None, "10"),
        Instruction(OpCode.INIT, ["y"], None, "20"),
        Instruction(OpCode.INIT, ["sum"], None, "0"),
        Instruction(OpCode.ASSIGN, ["sum"], None, "x + y"),
        Instruction(OpCode.RETURN_VAL, ["sum"]),
    ]

    print("\n[1] Generated Lua Interpreter (standalone):")
    print("-" * 40)
    lua_code = generate_lua_interpreter(instructions, include_debug=True)
    print(lua_code)

    print("\n" + "=" * 60)
    print("Demo Complete")
    print("=" * 60)


if __name__ == "__main__":
    demo_lua_interpreter()



# ===== 代码生成结构多样性增强模块 =====


class DiversityStrategy(ABC):
    """
    结构多样性策略基类

    定义不同代码生成策略的接口，
    用于在保持语义一致的前提下生成结构多样的代码。
    """

    @abstractmethod
    def select(self, rng: random.Random) -> Any:
        """从多个等价格式中选择一个"""
        pass

    @abstractmethod
    def name(self) -> str:
        """返回策略名称"""
        pass


class DiversityConfig:
    """
    结构多样性配置

    控制各层面的多样性生成选项
    """

    def __init__(
        self,
        enabled: bool = False,
        diversity_level: float = 0.5,
        handler_strategy: str = "random",
        utility_strategy: str = "random",
        naming_strategy: str = "random",
        serialization_strategy: str = "random",
        rng: random.Random | None = None,
    ):
        self.enabled = enabled
        self.diversity_level = diversity_level  # 0.0 ~ 1.0
        self.handler_strategy = handler_strategy
        self.utility_strategy = utility_strategy
        self.naming_strategy = naming_strategy
        self.serialization_strategy = serialization_strategy
        self.rng = rng or random.Random()

    def should_apply(self) -> bool:
        """是否应用多样性策略"""
        return self.enabled and self.rng.random() < self.diversity_level

    def copy_with_seed(self, seed: int) -> 'DiversityConfig':
        """创建带新种子的配置副本"""
        new_config = DiversityConfig(
            enabled=self.enabled,
            diversity_level=self.diversity_level,
            handler_strategy=self.handler_strategy,
            utility_strategy=self.utility_strategy,
            naming_strategy=self.naming_strategy,
            serialization_strategy=self.serialization_strategy,
            rng=random.Random(seed),
        )
        return new_config


class HandlerExpressionStrategy(DiversityStrategy):
    """
    Handler 表达式多样化策略

    为同一操作提供多种等价的 Lua 表达形式
    """

    # 等价的表达式变体
    STRATEGIES = {
        "if_then": [
            "if cond then return target end; return pc + 1",
            "return cond and target or (pc + 1)",
            "if not cond then return pc + 1 end; return target",
            "local r = pc + 1; if cond then r = target end; return r",
        ],
        "nil_check": [
            "if val == nil then return nil end",
            "if not val then return nil end",
            "return val or nil",
        ],
        "type_check": [
            "if type(v) == 'string' then",
            "if type(v) == 'string' then",
            "if tostring(v) == v then",
        ],
        "table_insert": [
            "table.insert(stack, val)",
            "stack[#stack + 1] = val",
        ],
        "table_remove": [
            "return table.remove(stack)",
            "return table.remove(stack, #stack)",
        ],
        "local_assignment": [
            "local x = val",
            "local x; x = val",
        ],
        "return_next": [
            "return pc + 1",
            "do return pc + 1 end",
            "pc = pc + 1; return pc",
        ],
        "halt_return": [
            "return nil",
            "do return nil end",
            "pc = nil; return nil",
        ],
        "and_or_chain": [
            "a and b or c",
            "a and b or c",
            "if a then return b else return c end",
        ],
    }

    def name(self) -> str:
        return "handler_expression"

    def select(self, rng: random.Random, expression_type: str) -> str:
        """选择指定类型的表达变体"""
        variants = self.STRATEGIES.get(expression_type, ["pass"])
        return rng.choice(variants)


class UtilityFunctionStrategy(DiversityStrategy):
    """
    工具函数多样化策略

    生成等价的辅助函数的不同实现方式
    """

    def name(self) -> str:
        return "utility_function"

    def select(self, rng: random.Random) -> str:
        """选择实现风格"""
        return self.select_style(rng)

    def select_style(self, rng: random.Random) -> str:
        """随机选择实现风格"""
        styles = ["default", "compact", "verbose"]
        return rng.choice(styles)

    def generate_get_function(self, rng: random.Random, style: str = "default") -> list[str]:
        """生成 _get 函数的不同实现"""
        if style == "compact":
            return [
                "local function _get(state, name)",
                "    local v = state.locals[name]",
                "    return v ~= nil and v or state.globals[name]",
                "end",
            ]
        elif style == "verbose":
            return [
                "local function _get(state, varname)",
                "    if state.locals[varname] ~= nil then",
                "        return state.locals[varname]",
                "    end",
                "    if state.globals[varname] ~= nil then",
                "        return state.globals[varname]",
                "    end",
                "    return nil",
                "end",
            ]
        else:  # default
            return [
                "local function _get(state, varname)",
                "    if state.locals[varname] ~= nil then",
                "        return state.locals[varname]",
                "    end",
                "    if state.globals[varname] ~= nil then",
                "        return state.globals[varname]",
                "    end",
                "    return nil",
                "end",
            ]

    def generate_push_function(self, rng: random.Random, style: str = "default") -> list[str]:
        """生成 _push 函数的不同实现"""
        if style == "direct":
            return [
                "local function _push(state, value)",
                "    state.stack[#state.stack + 1] = value",
                "end",
            ]
        elif style == "insert":
            return [
                "local function _push(state, value)",
                "    table.insert(state.stack, value)",
                "end",
            ]
        else:  # default
            return [
                "local function _push(state, value)",
                "    table.insert(state.stack, value)",
                "end",
            ]

    def generate_pop_function(self, rng: random.Random, style: str = "default") -> list[str]:
        """生成 _pop 函数的不同实现"""
        if style == "remove":
            return [
                "local function _pop(state)",
                "    return table.remove(state.stack)",
                "end",
            ]
        elif style == "index":
            return [
                "local function _pop(state)",
                "    local v = state.stack[#state.stack]",
                "    state.stack[#state.stack] = nil",
                "    return v",
                "end",
            ]
        else:  # default
            return [
                "local function _pop(state)",
                "    return table.remove(state.stack)",
                "end",
            ]

    def generate_get_function(self, rng: random.Random, style: str = "default") -> list[str]:
        """生成 _get 函数的不同实现"""
        if style == "compact":
            return [
                "local function _get(state, name)",
                "    local v = state.locals[name]",
                "    return v ~= nil and v or state.globals[name]",
                "end",
            ]
        elif style == "verbose":
            return [
                "local function _get(state, varname)",
                "    if state.locals[varname] ~= nil then",
                "        return state.locals[varname]",
                "    end",
                "    if state.globals[varname] ~= nil then",
                "        return state.globals[varname]",
                "    end",
                "    return nil",
                "end",
            ]
        else:  # default
            return [
                "local function _get(state, varname)",
                "    if state.locals[varname] ~= nil then",
                "        return state.locals[varname]",
                "    end",
                "    if state.globals[varname] ~= nil then",
                "        return state.globals[varname]",
                "    end",
                "    return nil",
                "end",
            ]

    def select_style(self, rng: random.Random) -> str:
        """随机选择实现风格"""
        styles = ["default", "compact", "verbose"]
        return rng.choice(styles)


class VariableNamingStrategy(DiversityStrategy):
    """
    变量命名多样化策略

    为内部变量生成不同的命名方案
    """

    # 预设的变量名池
    NAME_POOLS = {
        "default": {
            "state": ["state", "ctx", "env", "vm"],
            "varname": ["varname", "name", "key", "var"],
            "value": ["value", "val", "v", "data"],
            "expr": ["expr", "e", "exp", "code"],
            "cond": ["cond", "c", "test", "pred"],
            "target": ["target", "t", "dest", "addr"],
            "func": ["func", "f", "fn", "cb"],
            "result": ["result", "res", "r", "out"],
            "pc": ["pc", "ip", "ptr", "idx"],
            "stack": ["stack", "stk", "s", "st"],
        },
        "obfuscated": {
            "state": ["_S", "_st", "_0", "_a"],
            "varname": ["_n", "_v", "_1", "_k"],
            "value": ["_x", "_d", "_2", "_z"],
            "expr": ["_e", "_q", "_3", "_m"],
            "cond": ["_c", "_t", "_4", "_f"],
            "target": ["_j", "_p", "_5", "_g"],
            "func": ["_f", "_u", "_6", "_h"],
            "result": ["_r", "_o", "_7", "_w"],
            "pc": ["_i", "_z", "_8", "_y"],
            "stack": ["_s", "_a", "_9", "_b"],
        },
        "mixed": {
            "state": ["st", "_state", "vm_ctx", "env"],
            "varname": ["vn", "_name", "var_key", "n"],
            "value": ["vl", "_val", "data_v", "d"],
            "expr": ["ex", "_expr", "expr_code", "e"],
            "cond": ["ct", "_cond", "test_p", "p"],
            "target": ["tg", "_target", "dest_j", "j"],
            "func": ["fn", "_func", "callback", "cb"],
            "result": ["rs", "_result", "out_val", "o"],
            "pc": ["ip", "_pc", "inst_ptr", "ix"],
            "stack": ["sk", "_stack", "stk_data", "sd"],
        },
    }

    def name(self) -> str:
        return "variable_naming"

    def select(self, rng: random.Random) -> Any:
        """选择一个命名池"""
        pools = list(self.NAME_POOLS.keys())
        return rng.choice(pools)

    def __init__(self):
        self.current_pool = "default"
        self._name_cache = {}  # 缓存已生成的变量名

    def set_pool(self, pool_name: str):
        """设置使用的命名池"""
        if pool_name in self.NAME_POOLS:
            self.current_pool = pool_name
            self._name_cache.clear()

    def get_name(self, var_type: str, rng: random.Random) -> str:
        """获取指定类型的变量名"""
        pool = self.NAME_POOLS.get(self.current_pool, self.NAME_POOLS["default"])
        options = pool.get(var_type, [var_type])
        return rng.choice(options)

    def generate_all_names(self, rng: random.Random, pool_name: str = "default") -> dict[str, str]:
        """生成一套完整的变量名映射"""
        pool = self.NAME_POOLS.get(pool_name, self.NAME_POOLS["default"])
        result = {}
        for var_type, options in pool.items():
            result[var_type] = rng.choice(options)
        return result


class SerializationStrategy(DiversityStrategy):
    """
    序列化多样化策略

    同一指令数据使用不同的序列化格式
    """

    def name(self) -> str:
        return "serialization"

    def select(self, rng: random.Random) -> callable:
        """选择序列化器"""
        return self.select_serializer(rng)

    def serialize_instr_compact(self, instr_data: list, var_name: str, idx: int) -> str:
        """紧凑序列化格式"""
        # {opcode, arg1, arg2, ...}
        return f"{var_name}[{idx}] = {{{', '.join(str(x) for x in instr_data)}}}}}"

    def serialize_instr_expanded(self, instr_data: list, var_name: str, idx: int) -> str:
        """展开的序列化格式"""
        lines = [f"{var_name}[{idx}] = {{"]
        for i, val in enumerate(instr_data):
            lines.append(f"    [{i}] = {val},")
        lines.append("}}")
        return "\n".join(lines)

    def serialize_instr_named(self, instr_data: list, var_name: str, idx: int) -> str:
        """带字段名的序列化格式"""
        names = ["op", "arg1", "arg2", "arg3", "result"]
        parts = []
        for i, val in enumerate(instr_data):
            name = names[i] if i < len(names) else f"f{i}"
            parts.append(f"{name}={val}")
        return f"{var_name}[{idx}] = {{{', '.join(parts)}}}}}"

    def select_serializer(self, rng: random.Random) -> callable:
        """选择序列化器"""
        serializers = [
            self.serialize_instr_compact,
            self.serialize_instr_expanded,
            self.serialize_instr_named,
        ]
        return rng.choice(serializers)


class DispatcherStrategy(DiversityStrategy):
    """
    分发器多样化策略

    生成不同风格的 dispatch 函数
    """

    def name(self) -> str:
        return "dispatcher"

    def select(self, rng: random.Random) -> list[str]:
        """选择一个分发器实现"""
        return self.select_dispatcher(rng)

    def generate_direct_dispatch(self) -> list[str]:
        """直接分发（标准方式）"""
        return [
            "local function dispatch(instr, state, pc)",
            "    local op = instr[1]",
            "    local handler = handlers[op] or handlers.default",
            "    return handler(instr, state, pc)",
            "end",
        ]

    def generate_inline_dispatch(self) -> list[str]:
        """内联分发"""
        return [
            "local function dispatch(instr, state, pc)",
            "    return (handlers[instr[1]] or handlers.default)(instr, state, pc)",
            "end",
        ]

    def generate_safelist_dispatch(self) -> list[str]:
        """安全列表分发"""
        return [
            "local function dispatch(instr, state, pc)",
            "    local h = handlers[instr[1]]",
            "    if h then return h(instr, state, pc) end",
            "    return handlers.default(instr, state, pc)",
            "end",
        ]

    def select_dispatcher(self, rng: random.Random) -> list[str]:
        """选择分发器实现"""
        dispatchers = [
            self.generate_direct_dispatch,
            self.generate_inline_dispatch,
            self.generate_safelist_dispatch,
        ]
        return rng.choice(dispatchers)()


class LoopStructureStrategy(DiversityStrategy):
    """
    循环结构多样化策略

    生成不同风格的执行循环
    """

    def name(self) -> str:
        return "loop_structure"

    def select(self, rng: random.Random) -> callable:
        """选择一个循环生成器"""
        loops = [
            self.generate_while_loop,
            self.generate_repeat_loop,
            self.generate_for_loop,
        ]
        return rng.choice(loops)

    def generate_while_loop(self, code_var: str, state_var: str) -> list[str]:
        """while 循环风格"""
        return [
            f"local function execute({code_var}, {state_var})",
            f"    local pc = 1",
            f"    while pc and not {state_var}.halted do",
            f"        local instr = {code_var}[pc]",
            f"        if not instr then break end",
            f"        pc = dispatch(instr, {state_var}, pc)",
            f"        if not pc then break end",
            f"        if pc < 1 or pc > #{code_var} + 1 then break end",
            f"    end",
            f"    return {state_var}.return_value",
            f"end",
        ]

    def generate_repeat_loop(self, code_var: str, state_var: str) -> list[str]:
        """repeat-until 循环风格"""
        return [
            f"local function execute({code_var}, {state_var})",
            f"    local pc = 1",
            f"    repeat",
            f"        local instr = {code_var}[pc]",
            f"        if not instr then break end",
            f"        pc = dispatch(instr, {state_var}, pc)",
            f"        if not pc or pc < 1 or pc > #{code_var} + 1 then break end",
            f"    until {state_var}.halted",
            f"    return {state_var}.return_value",
            f"end",
        ]

    def generate_for_loop(self, code_var: str, state_var: str) -> list[str]:
        """for 循环风格"""
        return [
            f"local function execute({code_var}, {state_var})",
            f"    local n = #{code_var}",
            f"    local pc = 1",
            f"    for _ = 1, n + 1 do",
            f"        if {state_var}.halted then break end",
            f"        local instr = {code_var}[pc]",
            f"        if not instr then break end",
            f"        local npc = dispatch(instr, {state_var}, pc)",
            f"        if not npc or npc < 1 or npc > n + 1 then break end",
            f"        pc = npc",
            f"    end",
            f"    return {state_var}.return_value",
            f"end",
        ]

    def select_loop(self, rng: random.Random, code_var: str, state_var: str) -> list[str]:
        """选择循环结构"""
        loops = [
            lambda: self.generate_while_loop(code_var, state_var),
            lambda: self.generate_repeat_loop(code_var, state_var),
            lambda: self.generate_for_loop(code_var, state_var),
        ]
        return rng.choice(loops)()


class DiversityOrchestrator:
    """
    多样性生成协调器

    整合所有多样性策略，统一调度生成过程
    """

    def __init__(
        self,
        config: DiversityConfig | None = None,
        rng: random.Random | None = None,
    ):
        self.config = config or DiversityConfig()
        self.rng = rng or self.config.rng

        # 初始化各策略
        self.handler_strategy = HandlerExpressionStrategy()
        self.utility_strategy = UtilityFunctionStrategy()
        self.naming_strategy = VariableNamingStrategy()
        self.serialization_strategy = SerializationStrategy()
        self.dispatcher_strategy = DispatcherStrategy()
        self.loop_strategy = LoopStructureStrategy()

        # 根据配置设置命名池
        self._apply_naming_pool()

    def _apply_naming_pool(self):
        """应用命名策略"""
        pool_map = {
            "default": "default",
            "obfuscated": "obfuscated",
            "random": ["default", "obfuscated", "mixed"],
        }
        pool_name = self.config.naming_strategy
        if pool_name == "random":
            pool_name = self.rng.choice(["default", "obfuscated", "mixed"])
        self.naming_strategy.set_pool(pool_name)

    def should_diversify(self) -> bool:
        """是否启用多样化生成"""
        return self.config.enabled

    def get_handler_variant(self, expression_type: str) -> str:
        """获取 handler 表达变体"""
        if not self.should_diversify():
            return HandlerExpressionStrategy.STRATEGIES.get(expression_type, ["pass"])[0]
        return self.handler_strategy.select(self.rng, expression_type)

    def generate_utility_functions(self) -> str:
        """生成工具函数（带多样性）"""
        style = self.utility_strategy.select_style(self.rng) if self.should_diversify() else "default"
        lines = [
            "-- =========================================",
            "-- Utility Functions for Handlers",
            "-- =========================================",
            "",
        ]

        # _get
        lines.extend(self.utility_strategy.generate_get_function(self.rng, style))
        lines.append("")

        # _set
        lines.append("local function _set(state, varname, value)")
        lines.append("    state.locals[varname] = value")
        lines.append("end")
        lines.append("")

        # _push
        lines.extend(self.utility_strategy.generate_push_function(self.rng, style))
        lines.append("")

        # _pop
        lines.extend(self.utility_strategy.generate_pop_function(self.rng, style))
        lines.append("")

        # _eval_literal
        lines.extend(self._generate_eval_literal(style))
        lines.append("")

        # _eval_expr
        lines.extend(self._generate_eval_expr(style))
        lines.append("")

        # _eval_condition
        lines.extend(self._generate_eval_condition(style))
        lines.append("")

        # _is_truthy
        lines.extend(self._generate_is_truthy(style))

        return "\n".join(lines)

    def _generate_eval_literal(self, style: str) -> list[str]:
        """生成 _eval_literal 函数"""
        if style == "compact":
            return [
                "local function _eval_literal(v)",
                "    if v == nil or v == true or v == false then return v end",
                "    if type(v) == 'number' then return v end",
                "    return tonumber(v) or v",
                "end",
            ]
        else:
            return [
                "local function _eval_literal(val)",
                "    if val == nil then return nil end",
                "    if val == true then return true end",
                "    if val == false then return false end",
                "    if type(val) == 'number' then return val end",
                "    if type(val) == 'string' then",
                "        local n = tonumber(val)",
                "        if n then return n end",
                "    end",
                "    return val",
                "end",
            ]

    def _generate_eval_expr(self, style: str) -> list[str]:
        """生成 _eval_expr 函数"""
        if style == "compact":
            return [
                "local function _eval_expr(st, e)",
                "    if type(e) ~= 'string' then return e end",
                "    local v = _get(st, e)",
                "    if v ~= nil then return v end",
                "    return tonumber(e) or e",
                "end",
            ]
        else:
            return [
                "local function _eval_expr(state, expr)",
                "    if expr == nil then return nil end",
                "    if type(expr) == 'number' then return expr end",
                "    if type(expr) == 'string' then",
                "        local var_value = _get(state, expr)",
                "        if var_value ~= nil then return var_value end",
                "        local n = tonumber(expr)",
                "        if n then return n end",
                "    end",
                "    return expr",
                "end",
            ]

    def _generate_eval_condition(self, style: str) -> list[str]:
        """生成 _eval_condition 函数"""
        if style == "compact":
            return [
                "local function _eval_cond(st, c)",
                "    if c == nil or c == false then return false end",
                "    if c == true then return true end",
                "    if type(c) == 'string' then return _is_truthy(_get(st, c)) end",
                "    return true",
                "end",
            ]
        else:
            return [
                "local function _eval_condition(state, cond)",
                "    if cond == nil then return false end",
                "    if cond == true then return true end",
                "    if cond == false then return false end",
                "    if type(cond) == 'string' then",
                "        local val = _get(state, cond)",
                "        if val ~= nil then return _is_truthy(val) end",
                "    end",
                "    return _is_truthy(cond)",
                "end",
            ]

    def _generate_is_truthy(self, style: str) -> list[str]:
        """生成 _is_truthy 函数"""
        if style == "compact":
            return [
                "local function _is_truthy(v)",
                "    return v ~= nil and v ~= false",
                "end",
            ]
        else:
            return [
                "local function _is_truthy(val)",
                "    if val == nil then return false end",
                "    if val == false then return false end",
                "    return true",
                "end",
            ]

    def generate_dispatcher(self) -> str:
        """生成 dispatcher 函数"""
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Handler Dispatcher")
        lines.append("-- =========================================")
        lines.append("")

        if self.should_diversify():
            dispatcher_code = self.dispatcher_strategy.select_dispatcher(self.rng)
            lines.extend(dispatcher_code)
        else:
            lines.extend(self.dispatcher_strategy.generate_direct_dispatch())

        return "\n".join(lines)

    def generate_executor_loop(
        self,
        code_var: str = "code",
        state_var: str = "state",
        function_name: str = "execute"
    ) -> str:
        """生成执行循环"""
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Executor Loop")
        lines.append("-- =========================================")
        lines.append("")

        if self.should_diversify():
            loop_code = self.loop_strategy.select_loop(self.rng, code_var, state_var)
            lines.extend(loop_code)
        else:
            lines.extend(self.loop_strategy.generate_while_loop(code_var, state_var))

        return "\n".join(lines)

    def serialize_instruction(
        self,
        instr_data: list,
        var_name: str,
        idx: int
    ) -> str:
        """序列化单条指令"""
        if self.should_diversify():
            serializer = self.serialization_strategy.select_serializer(self.rng)
            return serializer(instr_data, var_name, idx)
        else:
            return self.serialization_strategy.serialize_instr_compact(instr_data, var_name, idx)


# ===== Python Handler 到 Lua Handler 的转换 =====


class LuaHandlerGenerator:
    """
    Lua Handler 生成器

    将 Python 指令处理器转换为 Lua 函数，
    实现跨语言执行逻辑迁移。
    """

    # Opcode 到 Lua handler 模板的映射
    HANDLER_TEMPLATES: dict[int, dict[str, str]] = {
        # opcode: (description, arg_pattern, lua_code_template)
        0: {  # nop
            "desc": "空操作",
            "template": """
    [0] = function(instr, state, pc)
        return pc + 1
    end"""
        },
        1: {  # declare
            "desc": "声明变量",
            "template": """
    [1] = function(instr, state, pc)
        local varname = instr[2]
        state.locals[varname] = nil
        return pc + 1
    end"""
        },
        2: {  # init
            "desc": "初始化变量",
            "template": """
    [2] = function(instr, state, pc)
        local varname = instr[2]
        local value = instr[3]
        if type(value) == 'string' and value:match('^[a-zA-Z_]') then
            value = _get(state, value)
        end
        _set(state, varname, value)
        return pc + 1
    end"""
        },
        3: {  # assign
            "desc": "赋值",
            "template": """
    [3] = function(instr, state, pc)
        local varname = instr[2]
        local expr = instr[3]
        local value = _eval_expr(state, expr)
        _set(state, varname, value)
        return pc + 1
    end"""
        },
        4: {  # call
            "desc": "函数调用",
            "template": """
    [4] = function(instr, state, pc)
        local funcname = instr[2]
        local func = _get(state, funcname)
        if type(func) == 'function' then
            local args = {}
            for i = 4, #instr do
                table.insert(args, _eval_literal(instr[i]))
            end
            local ok, result = pcall(func, unpack(args))
            if ok then _push(state, result) end
        end
        return pc + 1
    end"""
        },
        5: {  # call_assign
            "desc": "调用赋值",
            "template": """
    [5] = function(instr, state, pc)
        local varname = instr[2]
        local result = _pop(state)
        _set(state, varname, result)
        return pc + 1
    end"""
        },
        6: {  # return
            "desc": "返回空",
            "template": """
    [6] = function(instr, state, pc)
        state.halted = true
        return nil
    end"""
        },
        7: {  # return_val
            "desc": "返回值",
            "template": """
    [7] = function(instr, state, pc)
        local val = instr[2]
        val = _eval_literal(val)
        state.return_value = val
        state.halted = true
        return nil
    end"""
        },
        8: {  # jump
            "desc": "无条件跳转",
            "template": """
    [8] = function(instr, state, pc)
        local target = instr[2]
        if type(target) == 'number' then
            return target
        end
        return pc + 1
    end"""
        },
        9: {  # jump_if
            "desc": "条件跳转",
            "template": """
    [9] = function(instr, state, pc)
        local cond_expr = instr[2]
        local target = instr[3]
        local cond_value = _eval_condition(state, cond_expr)
        if cond_value then
            return target
        end
        return pc + 1
    end"""
        },
        10: {  # do
            "desc": "代码块开始",
            "template": """
    [10] = function(instr, state, pc)
        return pc + 1
    end"""
        },
        11: {  # end
            "desc": "代码块结束",
            "template": """
    [11] = function(instr, state, pc)
        return pc + 1
    end"""
        },
        12: {  # if
            "desc": "if 条件",
            "template": """
    [12] = function(instr, state, pc)
        local cond = _eval_condition(state, instr[2])
        _set(state, '_cond', cond)
        return pc + 1
    end"""
        },
        16: {  # while
            "desc": "while 循环",
            "template": """
    [16] = function(instr, state, pc)
        local cond = _eval_condition(state, instr[2])
        _set(state, '_loop_cond', cond)
        return pc + 1
    end"""
        },
        17: {  # for
            "desc": "for 循环",
            "template": """
    [17] = function(instr, state, pc)
        -- for 循环初始化
        return pc + 1
    end"""
        },
        18: {  # repeat
            "desc": "repeat 开始",
            "template": """
    [18] = function(instr, state, pc)
        _set(state, '_repeat_active', true)
        return pc + 1
    end"""
        },
        19: {  # until
            "desc": "until 条件",
            "template": """
    [19] = function(instr, state, pc)
        local cond = _eval_condition(state, instr[2])
        if cond then
            _set(state, '_repeat_active', false)
            return pc + 1
        end
        return instr[3] or (pc - 1)
    end"""
        },
        20: {  # break
            "desc": "跳出循环",
            "template": """
    [20] = function(instr, state, pc)
        return instr[2] or nil
    end"""
        },
        21: {  # continue
            "desc": "继续循环",
            "template": """
    [21] = function(instr, state, pc)
        return instr[2] or (pc - 1)
    end"""
        },
        24: {  # expr
            "desc": "表达式语句",
            "template": """
    [24] = function(instr, state, pc)
        local expr = instr[2]
        _eval_expr(state, expr)
        return pc + 1
    end"""
        },
        26: {  # table_new
            "desc": "创建表",
            "template": """
    [26] = function(instr, state, pc)
        _push(state, {})
        return pc + 1
    end"""
        },
        27: {  # table_set
            "desc": "设置表元素",
            "template": """
    [27] = function(instr, state, pc)
        local key = instr[2]
        local value = _eval_literal(instr[3])
        local tbl = _pop(state)
        if tbl and type(tbl) == 'table' then
            tbl[key] = value
        end
        _push(state, tbl)
        return pc + 1
    end"""
        },
        29: {  # label
            "desc": "标签",
            "template": """
    [29] = function(instr, state, pc)
        if instr[2] then
            _set(state, '_labels', instr[2])
        end
        return pc + 1
    end"""
        },
    }

    def __init__(self, include_comments: bool = True):
        self.include_comments = include_comments

    def generate_utility_functions(self) -> str:
        """
        生成辅助函数

        这些函数被各个 handler 调用
        """
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Utility Functions for Handlers")
        lines.append("-- =========================================")
        lines.append("")

        # 变量获取
        lines.append("local function _get(state, varname)")
        lines.append("    if state.locals[varname] ~= nil then")
        lines.append("        return state.locals[varname]")
        lines.append("    end")
        lines.append("    if state.globals[varname] ~= nil then")
        lines.append("        return state.globals[varname]")
        lines.append("    end")
        lines.append("    return nil")
        lines.append("end")
        lines.append("")

        # 变量设置
        lines.append("local function _set(state, varname, value)")
        lines.append("    state.locals[varname] = value")
        lines.append("end")
        lines.append("")

        # 栈操作
        lines.append("local function _push(state, value)")
        lines.append("    table.insert(state.stack, value)")
        lines.append("end")
        lines.append("")
        lines.append("local function _pop(state)")
        lines.append("    return table.remove(state.stack)")
        lines.append("end")
        lines.append("")

        # 字面量求值
        lines.append("local function _eval_literal(val)")
        lines.append("    if val == nil then return nil end")
        lines.append("    if val == true then return true end")
        lines.append("    if val == false then return false end")
        lines.append("    if type(val) == 'number' then return val end")
        lines.append("    if type(val) == 'string' then")
        lines.append("        local n = tonumber(val)")
        lines.append("        if n then return n end")
        lines.append("    end")
        lines.append("    return val")
        lines.append("end")
        lines.append("")

        # 表达式求值
        lines.append("local function _eval_expr(state, expr)")
        lines.append("    if expr == nil then return nil end")
        lines.append("    -- 数字直接返回")
        lines.append("    if type(expr) == 'number' then return expr end")
        lines.append("    -- 字符串表达式")
        lines.append("    if type(expr) == 'string' then")
        lines.append("        -- 检查是否为简单变量引用")
        lines.append("        local var_value = _get(state, expr)")
        lines.append("        if var_value ~= nil then return var_value end")
        lines.append("")
        lines.append("        -- 解析二元表达式: var op value")
        lines.append("        local var, op, right = expr:match('^(%w+)%s*([%+%-%*%/])%s*(.+)$')")
        lines.append("        if var and op then")
        lines.append("            local left_val = _get(state, var) or 0")
        lines.append("            local right_val = tonumber(right) or _get(state, right) or 0")
        lines.append("            if op == '+' then return left_val + right_val end")
        lines.append("            if op == '-' then return left_val - right_val end")
        lines.append("            if op == '*' then return left_val * right_val end")
        lines.append("            if op == '/' then return left_val / right_val end")
        lines.append("        end")
        lines.append("")
        lines.append("        -- 解析简单赋值表达式: var = value")
        lines.append("        local target, src = expr:match('^(%w+)%s*=%s*(.+)$')")
        lines.append("        if target and src then")
        lines.append("            return _eval_expr(state, src)")
        lines.append("        end")
        lines.append("")
        lines.append("        -- 尝试作为数字")
        lines.append("        local n = tonumber(expr)")
        lines.append("        if n then return n end")
        lines.append("    end")
        lines.append("    return expr")
        lines.append("end")
        lines.append("")

        # 条件求值
        lines.append("local function _eval_condition(state, cond)")
        lines.append("    if cond == nil then return false end")
        lines.append("    if cond == true then return true end")
        lines.append("    if cond == false then return false end")
        lines.append("")
        lines.append("    if type(cond) == 'string' then")
        lines.append("        -- 检查是否为真值变量")
        lines.append("        local val = _get(state, cond)")
        lines.append("        if val ~= nil then return _is_truthy(val) end")
        lines.append("")
        lines.append("        -- 解析比较表达式")
        lines.append("        -- 格式: var op value")
        lines.append("        local var, op, num = cond:match('^(%w+)%s*(<[=<>]?)%s*(%d+)$')")
        lines.append("        if var and op then")
        lines.append("            local v = _get(state, var) or 0")
        lines.append("            local n = tonumber(num)")
        lines.append("            if op == '<' then return v < n")
        lines.append("            elseif op == '<=' then return v <= n")
        lines.append("            elseif op == '>' then return v > n")
        lines.append("            elseif op == '>=' then return v >= n")
        lines.append("            elseif op == '==' or op == '=' then return v == n")
        lines.append("            end")
        lines.append("        end")
        lines.append("")
        lines.append("        -- 解析变量比较")
        lines.append("        local left, op, right = cond:match('^(%w+)%s*(<[=<>]?)%s*(%w+)$')")
        lines.append("        if left and op and right then")
        lines.append("            local l = _get(state, left) or 0")
        lines.append("            local r = _get(state, right) or 0")
        lines.append("            if op == '<' then return l < r")
        lines.append("            elseif op == '<=' then return l <= r")
        lines.append("            elseif op == '>' then return l > r")
        lines.append("            elseif op == '>=' then return l >= r")
        lines.append("            elseif op == '==' or op == '=' then return l == r")
        lines.append("            elseif op == '~=' then return l ~= r")
        lines.append("            end")
        lines.append("        end")
        lines.append("    end")
        lines.append("")
        lines.append("    return _is_truthy(cond)")
        lines.append("end")
        lines.append("")

        # 真值判断
        lines.append("local function _is_truthy(val)")
        lines.append("    if val == nil then return false end")
        lines.append("    if val == false then return false end")
        lines.append("    return true")
        lines.append("end")

        return "\n".join(lines)

    def generate_handler(
        self,
        opcode: int,
        template: dict[str, str]
    ) -> str:
        """生成单个 handler"""
        lines = []
        if self.include_comments:
            lines.append(f"    -- opcode: {opcode} ({template['desc']})")
        lines.append(f"    {template['template'].strip()}")
        return "\n".join(lines)

    def generate_all_handlers(self) -> str:
        """生成所有 handler 表"""
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Instruction Handlers")
        lines.append("-- =========================================")
        lines.append("")
        lines.append("local handlers = {")

        for opcode in sorted(self.HANDLER_TEMPLATES.keys()):
            template = self.HANDLER_TEMPLATES[opcode]
            lines.append(self.generate_handler(opcode, template))

        # 默认处理器
        lines.append("")
        lines.append("    -- Default handler for unknown opcodes")
        lines.append("    default = function(instr, state, pc)")
        lines.append("        if _DEBUG then")
        lines.append("            print('Unknown opcode: ' .. tostring(instr[1]))")
        lines.append("        end")
        lines.append("        return pc + 1")
        lines.append("    end,")

        lines.append("}")
        return "\n".join(lines)

    def generate_handler_dispatcher(self) -> str:
        """生成 handler 分发器"""
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Handler Dispatcher")
        lines.append("-- =========================================")
        lines.append("")
        lines.append("local function dispatch(instr, state, pc)")
        lines.append("    local op = instr[1]")
        lines.append("    local handler = handlers[op] or handlers.default")
        lines.append("    return handler(instr, state, pc)")
        lines.append("end")
        return "\n".join(lines)

    def generate_complete_handlers(self) -> str:
        """生成完整的 handler 模块"""
        lines = []
        lines.append(self.generate_utility_functions())
        lines.append("")
        lines.append(self.generate_all_handlers())
        lines.append("")
        lines.append(self.generate_handler_dispatcher())
        return lines

    def generate(
        self,
        include_utility: bool = True,
        include_dispatcher: bool = True
    ) -> str:
        """生成完整的 handler 代码"""
        parts = []
        if include_utility:
            parts.append(self.generate_utility_functions())
        parts.append(self.generate_all_handlers())
        if include_dispatcher:
            parts.append(self.generate_handler_dispatcher())
        return "\n\n".join(parts)


# =============================================================================
# Lua Handler 分层处理架构
# =============================================================================

class HandlerStep:
    """
    Handler 步骤基类

    代表 handler 逻辑中的一个独立步骤，支持组合以构建完整的 handler。
    """

    def __init__(self, name: str):
        self.name = name

    def generate_lua(self, context: 'StepContext') -> str:
        """
        生成 Lua 代码

        Args:
            context: 步骤执行上下文

        Returns:
            Lua 代码字符串
        """
        raise NotImplementedError

    def get_dependencies(self) -> list[str]:
        """获取依赖的其他步骤名称"""
        return []


class StepContext:
    """
    步骤执行上下文

    存储步骤执行过程中需要的共享数据
    """

    def __init__(self, opcode: int, instr_var: str = "instr", state_var: str = "state", pc_var: str = "pc"):
        self.opcode = opcode
        self.instr_var = instr_var
        self.state_var = state_var
        self.pc_var = pc_var
        self.local_vars: dict[str, str] = {}
        self.utility_calls: set[str] = set()
        self.next_pc_expr: str = "pc + 1"

    def add_local(self, name: str, value: str) -> str:
        """添加局部变量，返回变量名"""
        self.local_vars[name] = value
        return name

    def use_utility(self, utility_name: str) -> None:
        """记录使用的工具函数"""
        self.utility_calls.add(utility_name)

    def set_next_pc(self, expr: str) -> None:
        """设置下一 PC 表达式"""
        self.next_pc_expr = expr


class StepComposer:
    """
    步骤组合器

    将多个步骤组合成完整的 handler
    """

    def __init__(self, steps: list[HandlerStep] | None = None):
        self.steps = steps or []

    def add_step(self, step: HandlerStep) -> 'StepComposer':
        """添加步骤"""
        self.steps.append(step)
        return self

    def compose(self, context: StepContext) -> str:
        """组合所有步骤生成 Lua 代码"""
        lines = []

        for step in self.steps:
            step_code = step.generate_lua(context)
            if step_code:
                lines.append(step_code)

        lines.append(f"    return {context.next_pc_expr}")

        return "\n".join(lines)

    def get_all_dependencies(self) -> set[str]:
        """获取所有依赖的工具函数"""
        deps = set()
        for step in self.steps:
            deps.update(step.get_dependencies())
        return deps


# =============================================================================
# 常用步骤类型
# =============================================================================

class ArgExtractStep(HandlerStep):
    """参数提取步骤"""

    def __init__(self, arg_index: int, var_name: str, transform: str | None = None):
        super().__init__("arg_extract")
        self.arg_index = arg_index
        self.var_name = var_name
        self.transform = transform

    def generate_lua(self, context: StepContext) -> str:
        lines = []
        lines.append(f"    local {self.var_name} = {context.instr_var}[{self.arg_index}]")

        if self.transform:
            lines.append(f"    {self.var_name} = {self.transform.format(var=self.var_name, state=context.state_var)}")

        return "\n".join(lines)


class StateGetStep(HandlerStep):
    """状态获取步骤"""

    def __init__(self, varname: str, target_var: str | None = None, use_utility: bool = True):
        super().__init__("state_get")
        self.varname = varname
        self.target_var = target_var or varname
        self.use_utility = use_utility

    def get_dependencies(self) -> list[str]:
        return ["_get"] if self.use_utility else []

    def generate_lua(self, context: StepContext) -> str:
        if self.use_utility:
            context.use_utility("_get")
            return f"    local {self.target_var} = _get({context.state_var}, '{self.varname}')"
        return f"    local {self.target_var} = {context.state_var}.{self.varname}"


class StateSetStep(HandlerStep):
    """状态设置步骤"""

    def __init__(self, varname: str, value_expr: str, use_utility: bool = True):
        super().__init__("state_set")
        self.varname = varname
        self.value_expr = value_expr
        self.use_utility = use_utility

    def get_dependencies(self) -> list[str]:
        return ["_set"] if self.use_utility else []

    def generate_lua(self, context: StepContext) -> str:
        if self.use_utility:
            context.use_utility("_set")
            return f"    _set({context.state_var}, '{self.varname}', {self.value_expr})"
        return f"    {context.state_var}.{self.varname} = {self.value_expr}"


class ExprEvalStep(HandlerStep):
    """表达式求值步骤"""

    def __init__(self, expr: str, target_var: str | None = None):
        super().__init__("expr_eval")
        self.expr = expr
        self.target_var = target_var

    def get_dependencies(self) -> list[str]:
        return ["_eval_expr", "_eval_literal"]

    def generate_lua(self, context: StepContext) -> str:
        context.use_utility("_eval_expr")
        context.use_utility("_eval_literal")

        if self.target_var:
            return f"    local {self.target_var} = _eval_expr({context.state_var}, {self.expr})"
        return f"    _eval_expr({context.state_var}, {self.expr})"


class ConditionEvalStep(HandlerStep):
    """条件求值步骤"""

    def __init__(self, cond: str, target_var: str | None = None):
        super().__init__("condition_eval")
        self.cond = cond
        self.target_var = target_var

    def get_dependencies(self) -> list[str]:
        return ["_eval_condition", "_is_truthy"]

    def generate_lua(self, context: StepContext) -> str:
        context.use_utility("_eval_condition")
        context.use_utility("_is_truthy")

        if self.target_var:
            return f"    local {self.target_var} = _eval_condition({context.state_var}, {self.cond})"
        return f"    _eval_condition({context.state_var}, {self.cond})"


class JumpStep(HandlerStep):
    """跳转步骤"""

    def __init__(self, target_expr: str, condition_var: str | None = None):
        super().__init__("jump")
        self.target_expr = target_expr
        self.condition_var = condition_var

    def generate_lua(self, context: StepContext) -> str:
        if self.condition_var:
            return f"    if {self.condition_var} then return {self.target_expr} end"
        context.set_next_pc(self.target_expr)
        return f"    return {self.target_expr}"


class ConditionalJumpStep(HandlerStep):
    """条件跳转步骤"""

    def __init__(self, cond_expr: str, target_expr: str, fallthrough: str = "pc + 1"):
        super().__init__("conditional_jump")
        self.cond_expr = cond_expr
        self.target_expr = target_expr
        self.fallthrough = fallthrough

    def get_dependencies(self) -> list[str]:
        return ["_eval_condition"]

    def generate_lua(self, context: StepContext) -> str:
        context.use_utility("_eval_condition")
        return f"""    local cond = _eval_condition({context.state_var}, {self.cond_expr})
    if cond then
        return {self.target_expr}
    end
    return {self.fallthrough}"""


class StackPushStep(HandlerStep):
    """栈推入步骤"""

    def __init__(self, value_expr: str):
        super().__init__("stack_push")
        self.value_expr = value_expr

    def get_dependencies(self) -> list[str]:
        return ["_push"]

    def generate_lua(self, context: StepContext) -> str:
        context.use_utility("_push")
        return f"    _push({context.state_var}, {self.value_expr})"


class StackPopStep(HandlerStep):
    """栈弹出步骤"""

    def __init__(self, target_var: str):
        super().__init__("stack_pop")
        self.target_var = target_var

    def get_dependencies(self) -> list[str]:
        return ["_pop"]

    def generate_lua(self, context: StepContext) -> str:
        context.use_utility("_pop")
        return f"    local {self.target_var} = _pop({context.state_var})"


class HaltStep(HandlerStep):
    """停止虚拟机步骤"""

    def __init__(self, return_expr: str | None = None):
        super().__init__("halt")
        self.return_expr = return_expr

    def generate_lua(self, context: StepContext) -> str:
        lines = [f"    {context.state_var}.halted = true"]
        if self.return_expr:
            lines.append(f"    {context.state_var}.return_value = {self.return_expr}")
        lines.append("    return nil")
        return "\n".join(lines)


class NoOpStep(HandlerStep):
    """空操作步骤"""

    def __init__(self):
        super().__init__("nop")

    def generate_lua(self, context: StepContext) -> str:
        return ""


# =============================================================================
# 预定义步骤组合策略
# =============================================================================

class HandlerStrategy(Protocol):
    """Handler 策略协议"""

    def build_steps(self, opcode: int, template_data: dict) -> list[HandlerStep]:
        """构建步骤列表"""
        ...


class SimpleAssignStrategy:
    """简单赋值策略"""

    def build_steps(self, opcode: int, template_data: dict) -> list[HandlerStep]:
        steps = [
            ArgExtractStep(2, "varname"),
            ExprEvalStep("instr[3]", "value"),
            StateSetStep("varname", "value"),
        ]
        return steps


class InitVarStrategy:
    """变量初始化策略"""

    def build_steps(self, opcode: int, template_data: dict) -> list[HandlerStep]:
        steps = [
            ArgExtractStep(2, "varname"),
            ArgExtractStep(3, "value", "_eval_literal({var})"),
            StateSetStep("varname", "value"),
        ]
        return steps


# =============================================================================
# 分层执行模型 (Layered Execution Model)
# 将 handler 逻辑拆分为多个可组合阶段
# =============================================================================

class ExecutionPhase(Enum):
    """执行阶段枚举"""
    PARSE = "parse"       # 参数解析阶段
    PROCESS = "process"   # 数据处理阶段
    COMMIT = "commit"     # 结果提交阶段
    CONTROL = "control"   # 控制流阶段（跳转/停止）


class PhaseResult:
    """
    阶段执行结果

    封装每个阶段的执行结果和状态
    """

    def __init__(
        self,
        success: bool = True,
        data: dict[str, Any] | None = None,
        error: str | None = None
    ):
        self.success = success
        self.data = data or {}
        self.error = error

    def get(self, key: str, default: Any = None) -> Any:
        """获取阶段数据"""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置阶段数据"""
        self.data[key] = value

    @classmethod
    def ok(cls, data: dict[str, Any] | None = None) -> 'PhaseResult':
        """创建成功结果"""
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str) -> 'PhaseResult':
        """创建失败结果"""
        return cls(success=False, error=error)


class ExecutionStep:
    """
    分层执行步骤

    代表 handler 执行过程中的一个原子步骤
    """

    def __init__(
        self,
        name: str,
        phase: ExecutionPhase,
        code_template: str,
        reads: list[str] | None = None,
        writes: list[str] | None = None,
        depends_on: list[str] | None = None
    ):
        self.name = name
        self.phase = phase
        self.code_template = code_template
        self.reads = reads or []
        self.writes = writes or []
        self.depends_on = depends_on or []

    def generate_lua(self, context: 'LayeredExecutionContext') -> str:
        """生成 Lua 代码"""
        return self.code_template.format(
            instr=context.instr_var,
            state=context.state_var,
            pc=context.pc_var,
            **context.intermediate
        )


class LayeredExecutionContext:
    """
    分层执行上下文

    在各阶段之间传递数据
    """

    def __init__(
        self,
        opcode: int,
        instr_var: str = "instr",
        state_var: str = "state",
        pc_var: str = "pc"
    ):
        self.opcode = opcode
        self.instr_var = instr_var
        self.state_var = state_var
        self.pc_var = pc_var

        # 中间状态
        self.intermediate: dict[str, Any] = {}
        self.phase_results: dict[ExecutionPhase, PhaseResult] = {}

        # 当前 PC 偏移
        self.pc_offset = 1
        self.jump_target: int | None = None
        self.should_halt = False
        self.return_value: Any = None

    def set_intermediate(self, key: str, value: Any) -> None:
        """设置中间变量"""
        self.intermediate[key] = value

    def get_intermediate(self, key: str, default: Any = None) -> Any:
        """获取中间变量"""
        return self.intermediate.get(key, default)

    def add_phase_result(self, phase: ExecutionPhase, result: PhaseResult) -> None:
        """记录阶段结果"""
        self.phase_results[phase] = result
        if result.data:
            self.intermediate.update(result.data)

    def get_phase_result(self, phase: ExecutionPhase) -> PhaseResult | None:
        """获取阶段结果"""
        return self.phase_results.get(phase)

    def set_jump(self, target: int) -> None:
        """设置跳转"""
        self.jump_target = target

    def set_halt(self, return_val: Any = None) -> None:
        """设置停止"""
        self.should_halt = True
        self.return_value = return_val

    def get_next_pc_expr(self) -> str:
        """获取下一 PC 表达式"""
        if self.should_halt:
            return "nil"
        if self.jump_target is not None:
            return str(self.jump_target)
        return f"{self.pc_var} + {self.pc_offset}"


# =============================================================================
# 阶段执行器
# =============================================================================

class PhaseExecutor:
    """
    阶段执行器

    管理阶段的执行顺序和数据流
    """

    def __init__(self, steps: list[ExecutionStep] | None = None):
        self.steps = steps or []

    def add_step(self, step: ExecutionStep) -> 'PhaseExecutor':
        """添加步骤"""
        self.steps.append(step)
        return self

    def execute(self, context: LayeredExecutionContext) -> PhaseResult:
        """
        执行所有步骤

        Args:
            context: 执行上下文

        Returns:
            最终结果
        """
        for step in self.steps:
            # 检查依赖是否满足
            deps_met = all(
                context.get_intermediate(dep) is not None
                for dep in step.depends_on
            )
            if not deps_met:
                return PhaseResult.fail(f"Dependencies not met for step: {step.name}")

            # 执行步骤
            code = step.generate_lua(context)

            # 更新中间状态
            if step.writes:
                for var in step.writes:
                    if var in context.intermediate:
                        pass  # 已在 generate_lua 中更新

        return PhaseResult.ok(context.intermediate)

    def generate_lua(self, context: LayeredExecutionContext) -> str:
        """
        生成 Lua 代码

        Args:
            context: 执行上下文

        Returns:
            Lua 代码字符串
        """
        lines = []

        for step in self.steps:
            # 添加阶段注释
            if step.phase != ExecutionPhase.CONTROL:
                lines.append(f"    -- [{step.phase.value.upper()}] {step.name}")

            # 生成代码
            code = step.generate_lua(context)
            for line in code.split("\n"):
                if line.strip():
                    lines.append(f"    {line.strip()}")

        # 添加返回语句
        lines.append(f"    return {context.get_next_pc_expr()}")

        return "\n".join(lines)

    def group_by_phase(self) -> dict[ExecutionPhase, list[ExecutionStep]]:
        """按阶段分组步骤"""
        groups: dict[ExecutionPhase, list[ExecutionStep]] = {
            phase: [] for phase in ExecutionPhase
        }
        for step in self.steps:
            groups[step.phase].append(step)
        return groups

    def generate_layered_lua(self, context: LayeredExecutionContext) -> str:
        """
        生成分层 Lua 代码（按阶段组织）

        Args:
            context: 执行上下文

        Returns:
            Lua 代码字符串
        """
        groups = self.group_by_phase()
        lines = []

        for phase in ExecutionPhase:
            steps = groups[phase]
            if not steps:
                continue

            lines.append(f"    -- === {phase.value.upper()} PHASE ===")

            for step in steps:
                code = step.generate_lua(context)
                for line in code.split("\n"):
                    if line.strip():
                        lines.append(f"    {line.strip()}")

            lines.append("")  # 阶段之间空行

        # 返回语句
        lines.append(f"    return {context.get_next_pc_expr()}")

        return "\n".join(lines)


# =============================================================================
# 预定义分层步骤
# =============================================================================

class LayeredSteps:
    """预定义的分层步骤工厂"""

    @staticmethod
    def parse_varname(index: int = 2) -> ExecutionStep:
        """解析变量名"""
        return ExecutionStep(
            name="parse_varname",
            phase=ExecutionPhase.PARSE,
            code_template="local varname = {instr}[" + str(index) + "]",
            reads=["instr"],
            writes=["varname"],
            depends_on=[]
        )

    @staticmethod
    def parse_value(index: int = 3) -> ExecutionStep:
        """解析值"""
        return ExecutionStep(
            name="parse_value",
            phase=ExecutionPhase.PARSE,
            code_template="local value = {instr}[" + str(index) + "]",
            reads=["instr"],
            writes=["value"],
            depends_on=[]
        )

    @staticmethod
    def parse_literal(index: int = 3) -> ExecutionStep:
        """解析字面量"""
        return ExecutionStep(
            name="parse_literal",
            phase=ExecutionPhase.PARSE,
            code_template="local value = _eval_literal({instr}[" + str(index) + "])",
            reads=["instr"],
            writes=["value"],
            depends_on=[]
        )

    @staticmethod
    def eval_expr(expr: str, target: str) -> ExecutionStep:
        """计算表达式"""
        return ExecutionStep(
            name="eval_expr",
            phase=ExecutionPhase.PROCESS,
            code_template=f"local {target} = {expr}",
            reads=["instr", "state"],
            writes=[target],
            depends_on=["varname"]
        )

    @staticmethod
    def get_from_state(varname: str, target: str) -> ExecutionStep:
        """从状态获取"""
        return ExecutionStep(
            name=f"get_{varname}",
            phase=ExecutionPhase.PROCESS,
            code_template="local {target} = _get({state}, '" + varname + "')",
            reads=["state"],
            writes=[target],
            depends_on=[]
        )

    @staticmethod
    def set_to_state(varname: str, value: str) -> ExecutionStep:
        """设置到状态"""
        return ExecutionStep(
            name=f"set_{varname}",
            phase=ExecutionPhase.COMMIT,
            code_template="_set({state}, '" + varname + "', " + value + ")",
            writes=["state"],
            depends_on=[varname, value]
        )

    @staticmethod
    def compute_binary_op(left: str, op: str, right: str, target: str) -> ExecutionStep:
        """计算二元运算"""
        return ExecutionStep(
            name=f"compute_{op}",
            phase=ExecutionPhase.PROCESS,
            code_template=f"local {target} = {left} {op} {right}",
            reads=[left, right],
            writes=[target],
            depends_on=[left, right]
        )

    @staticmethod
    def jump(target: str) -> ExecutionStep:
        """跳转"""
        return ExecutionStep(
            name="jump",
            phase=ExecutionPhase.CONTROL,
            code_template="-- jump to " + target,
            depends_on=[target]
        )

    @staticmethod
    def conditional_jump(cond: str, target: str) -> ExecutionStep:
        """条件跳转"""
        return ExecutionStep(
            name="conditional_jump",
            phase=ExecutionPhase.CONTROL,
            code_template="if " + cond + " then return " + target + " else return {pc} + 1 end",
            reads=[cond],
            depends_on=[cond]
        )

    @staticmethod
    def halt(return_val: str | None = None) -> ExecutionStep:
        """停止"""
        return ExecutionStep(
            name="halt",
            phase=ExecutionPhase.CONTROL,
            code_template="{state}.halted = true; {state}.return_value = " + (return_val or "nil"),
            writes=["state"],
            depends_on=[]
        )

    @staticmethod
    def nop() -> ExecutionStep:
        """空操作"""
        return ExecutionStep(
            name="nop",
            phase=ExecutionPhase.CONTROL,
            code_template="-- no-op",
            depends_on=[]
        )


# =============================================================================
# 分层策略定义
# =============================================================================

class LayeredStrategy:
    """分层策略基类"""

    name: str = "base"

    def get_phases(self) -> list[ExecutionPhase]:
        """返回使用的阶段列表"""
        return [ExecutionPhase.PARSE, ExecutionPhase.PROCESS, ExecutionPhase.COMMIT]

    def build_steps(self, opcode: int) -> list[ExecutionStep]:
        """构建执行步骤"""
        raise NotImplementedError


class LayeredNopStrategy(LayeredStrategy):
    """分层 NOP 策略"""

    name = "nop"

    def build_steps(self, opcode: int) -> list[ExecutionStep]:
        return [LayeredSteps.nop()]


class LayeredInitStrategy(LayeredStrategy):
    """分层变量初始化策略 (3层: parse -> process -> commit)"""

    name = "init"

    def build_steps(self, opcode: int) -> list[ExecutionStep]:
        return [
            LayeredSteps.parse_varname(2),
            LayeredSteps.parse_literal(3),
            LayeredSteps.set_to_state("varname", "value"),
        ]


class LayeredAssignStrategy(LayeredStrategy):
    """分层赋值策略 (3层)"""

    name = "assign"

    def build_steps(self, opcode: int) -> list[ExecutionStep]:
        return [
            LayeredSteps.parse_varname(2),
            LayeredSteps.parse_value(3),
            LayeredSteps.set_to_state("varname", "value"),
        ]


class LayeredComputeStrategy(LayeredStrategy):
    """分层计算策略 (3层)"""

    name = "compute"

    def build_steps(self, opcode: int) -> list[ExecutionStep]:
        return [
            LayeredSteps.parse_varname(2),
            LayeredSteps.eval_expr("{instr}[3]", "computed"),
            LayeredSteps.set_to_state("varname", "computed"),
        ]


class LayeredJumpStrategy(LayeredStrategy):
    """分层跳转策略"""

    name = "jump"

    def build_steps(self, opcode: int) -> list[ExecutionStep]:
        return [
            LayeredSteps.parse_value(3),
        ]


class LayeredCondJumpStrategy(LayeredStrategy):
    """分层条件跳转策略"""

    name = "cond_jump"

    def get_phases(self) -> list[ExecutionPhase]:
        return [ExecutionPhase.PARSE, ExecutionPhase.PROCESS, ExecutionPhase.CONTROL]

    def build_steps(self, opcode: int) -> list[ExecutionStep]:
        return [
            LayeredSteps.parse_varname(2),
            LayeredSteps.get_from_state("varname", "cond_val"),
            LayeredSteps.parse_value(3),
        ]


class LayeredReturnStrategy(LayeredStrategy):
    """分层返回策略"""

    name = "return"

    def get_phases(self) -> list[ExecutionPhase]:
        return [ExecutionPhase.PARSE, ExecutionPhase.CONTROL]

    def build_steps(self, opcode: int) -> list[ExecutionStep]:
        return [
            LayeredSteps.halt("nil"),
        ]


class LayeredReturnValStrategy(LayeredStrategy):
    """分层返回值策略"""

    name = "return_val"

    def get_phases(self) -> list[ExecutionPhase]:
        return [ExecutionPhase.PARSE, ExecutionPhase.PROCESS, ExecutionPhase.CONTROL]

    def build_steps(self, opcode: int) -> list[ExecutionStep]:
        return [
            LayeredSteps.parse_varname(2),
            LayeredSteps.get_from_state("varname", "ret_val"),
            LayeredSteps.halt("ret_val"),
        ]


class LayeredCallStrategy(LayeredStrategy):
    """分层函数调用策略"""

    name = "call"

    def build_steps(self, opcode: int) -> list[ExecutionStep]:
        return [
            LayeredSteps.parse_varname(2),
            LayeredSteps.get_from_state("funcname", "func"),
        ]


# =============================================================================
# 分层 Handler 生成器 (增强版)
# =============================================================================

class EnhancedLayeredHandlerGenerator:
    """
    增强型分层 Handler 生成器

    使用分层执行模型生成 handler，支持：
    - 多阶段执行 (Parse -> Process -> Commit -> Control)
    - 中间状态传递
    - 不同策略使用不同阶段组合
    """

    STRATEGIES: dict[int, type[LayeredStrategy]] = {
        0: LayeredNopStrategy,           # nop
        1: LayeredAssignStrategy,          # declare
        2: LayeredInitStrategy,           # init
        3: LayeredAssignStrategy,         # assign
        4: LayeredCallStrategy,           # call
        5: LayeredCallStrategy,           # call_assign
        6: LayeredReturnStrategy,        # return
        7: LayeredReturnValStrategy,     # return_val
        8: LayeredJumpStrategy,          # jump
        9: LayeredCondJumpStrategy,      # jump_if
        10: LayeredNopStrategy,          # do
        11: LayeredNopStrategy,          # end
    }

    def __init__(
        self,
        include_comments: bool = True,
        use_layered_structure: bool = True,
        include_phase_separators: bool = True
    ):
        self.include_comments = include_comments
        self.use_layered_structure = use_layered_structure
        self.include_phase_separators = include_phase_separators
        self._custom_strategies: dict[int, LayeredStrategy] = {}

    def register_strategy(self, opcode: int, strategy: LayeredStrategy) -> None:
        """注册自定义策略"""
        self._custom_strategies[opcode] = strategy

    def get_strategy(self, opcode: int) -> LayeredStrategy | None:
        """获取策略"""
        if opcode in self._custom_strategies:
            return self._custom_strategies[opcode]
        strategy_cls = self.STRATEGIES.get(opcode)
        if strategy_cls:
            return strategy_cls()
        return None

    def generate_handler(
        self,
        opcode: int,
        desc: str = "",
        use_layered: bool | None = None
    ) -> str:
        """
        生成单个分层 handler

        Args:
            opcode: 操作码
            desc: 描述
            use_layered: 是否使用分层结构

        Returns:
            Lua 代码字符串
        """
        use_layered = use_layered if use_layered is not None else self.use_layered_structure

        lines = []

        if self.include_comments:
            lines.append(f"    -- opcode: {opcode} ({desc})")

        strategy = self.get_strategy(opcode)
        if not strategy:
            lines.append("    -- No strategy, default to sequential")
            lines.append("    return pc + 1")
            return "\n".join(lines)

        # 构建上下文
        context = LayeredExecutionContext(opcode)

        # 构建执行器
        steps = strategy.build_steps(opcode)
        executor = PhaseExecutor(steps)

        # 生成代码
        if use_layered:
            handler_code = executor.generate_layered_lua(context)
        else:
            handler_code = executor.generate_lua(context)

        lines.append(handler_code)
        return "\n".join(lines)

    def generate_all_handlers(
        self,
        templates: dict[int, dict[str, str]] | None = None,
        use_layered: bool | None = None
    ) -> str:
        """
        生成所有分层 handlers

        Args:
            templates: 模板字典
            use_layered: 是否使用分层结构

        Returns:
            Lua 代码字符串
        """
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Instruction Handlers (Enhanced Layered Model)")
        lines.append("-- =========================================")
        lines.append("")
        lines.append("local handlers = {")

        if templates is None:
            templates = LuaHandlerGenerator.HANDLER_TEMPLATES

        for opcode in sorted(templates.keys()):
            template_data = templates[opcode]
            desc = template_data.get("desc", "")

            handler_code = self.generate_handler(opcode, desc, use_layered)
            lines.append(handler_code)
            lines.append("")  # handler 之间空行

        # 默认处理器
        lines.append("    -- Default handler for unknown opcodes")
        lines.append("    default = function(instr, state, pc)")
        lines.append("        if _DEBUG then")
        lines.append("            print('Unknown opcode: ' .. tostring(instr[1]))")
        lines.append("        end")
        lines.append("        return pc + 1")
        lines.append("    end,")

        lines.append("}")
        return "\n".join(lines)

    def generate_layered_handlers_only(self) -> str:
        """仅生成 handlers（不含 dispatcher）"""
        return self.generate_all_handlers()


# =============================================================================
# 分层执行模块生成器
# =============================================================================

class LayeredExecutionModuleGenerator:
    """
    分层执行模块生成器

    生成包含分层 handlers 和辅助函数的完整模块
    """

    def __init__(
        self,
        handler_gen: EnhancedLayeredHandlerGenerator | None = None,
        include_utility: bool = True,
        include_dispatcher: bool = True
    ):
        self.handler_gen = handler_gen or EnhancedLayeredHandlerGenerator()
        self.include_utility = include_utility
        self.include_dispatcher = include_dispatcher

    def generate_utility_functions(self) -> str:
        """生成工具函数"""
        return LuaHandlerGenerator().generate_utility_functions()

    def generate_handlers(self) -> str:
        """生成 handlers"""
        return self.handler_gen.generate_all_handlers()

    def generate_dispatcher(self) -> str:
        """生成 dispatcher"""
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Dispatcher")
        lines.append("-- =========================================")
        lines.append("")
        lines.append("local function dispatch(instr, state, pc)")
        lines.append("    local op = instr[1]")
        lines.append("    local handler = handlers[op] or handlers.default")
        lines.append("    return handler(instr, state, pc)")
        lines.append("end")
        return "\n".join(lines)

    def generate_module(self) -> str:
        """生成完整模块"""
        parts = []

        if self.include_utility:
            parts.append(self.generate_utility_functions())
            parts.append("")

        parts.append(self.generate_handlers())
        parts.append("")

        if self.include_dispatcher:
            parts.append(self.generate_dispatcher())

        return "\n\n".join(parts)


# =============================================================================
# 便捷函数
# =============================================================================

def generate_layered_handlers(
    use_layered: bool = True,
    include_comments: bool = True
) -> str:
    """
    便捷函数：生成分层 handlers

    Args:
        use_layered: 是否使用分层结构
        include_comments: 是否包含注释

    Returns:
        Lua 代码字符串
    """
    gen = EnhancedLayeredHandlerGenerator(
        include_comments=include_comments,
        use_layered_structure=use_layered
    )
    return gen.generate_all_handlers()


def generate_layered_module(
    include_dispatcher: bool = True
) -> str:
    """
    便捷函数：生成分层执行模块

    Args:
        include_dispatcher: 是否包含 dispatcher

    Returns:
        Lua 代码字符串
    """
    gen = LayeredExecutionModuleGenerator()
    return gen.generate_module()


def demo_layered_execution_model():
    """
    演示分层执行模型
    """
    print("=" * 70)
    print("Layered Execution Model Demo")
    print("=" * 70)

    # 演示分层步骤
    print("\n[1] 分层步骤定义:")
    print("-" * 50)

    context = LayeredExecutionContext(2)
    print(f"Context: opcode={context.opcode}, instr={context.instr_var}, state={context.state_var}")

    # 初始化策略步骤
    init_steps = LayeredInitStrategy().build_steps(2)
    print(f"\nInit Strategy ({len(init_steps)} steps):")
    for step in init_steps:
        print(f"  [{step.phase.value}] {step.name}")

    # 计算策略步骤
    compute_steps = LayeredComputeStrategy().build_steps(3)
    print(f"\nCompute Strategy ({len(compute_steps)} steps):")
    for step in compute_steps:
        print(f"  [{step.phase.value}] {step.name}")

    # 条件跳转策略步骤
    condj_steps = LayeredCondJumpStrategy().build_steps(9)
    print(f"\nConditional Jump Strategy ({len(condj_steps)} steps):")
    for step in condj_steps:
        print(f"  [{step.phase.value}] {step.name}")

    # 演示增强型分层 handler 生成
    print("\n[2] 增强型分层 Handler 生成:")
    print("-" * 50)

    gen = EnhancedLayeredHandlerGenerator(include_comments=True)

    print("\nNOP Handler:")
    nop = gen.generate_handler(0, "nop")
    print(nop)

    print("\nInit Handler (layered):")
    init = gen.generate_handler(2, "init", use_layered=True)
    print(init)

    print("\nInit Handler (sequential):")
    init_seq = gen.generate_handler(2, "init", use_layered=False)
    print(init_seq)

    print("\nAssign Handler (layered):")
    assign = gen.generate_handler(3, "assign", use_layered=True)
    print(assign)

    print("\nReturn Handler (layered):")
    ret = gen.generate_handler(6, "return", use_layered=True)
    print(ret)

    print("\nConditional Jump Handler (layered):")
    condj = gen.generate_handler(9, "jump_if", use_layered=True)
    print(condj)

    # 演示完整模块
    print("\n[3] 完整分层执行模块:")
    print("-" * 50)

    module_gen = LayeredExecutionModuleGenerator()
    module = module_gen.generate_module()
    print(module[:1500] + "..." if len(module) > 1500 else module)

    print("\n" + "=" * 70)
    print("Layered Execution Model Features:")
    print("  - ExecutionPhase: PARSE, PROCESS, COMMIT, CONTROL")
    print("  - ExecutionStep: 原子步骤，可组合")
    print("  - PhaseExecutor: 阶段执行器")
    print("  - LayeredStrategy: 分层策略定义")
    print("  - EnhancedLayeredHandlerGenerator: 增强型生成器")
    print("=" * 70)


if __name__ == "__main__":
    demo_layered_execution_model()


class FunctionCallStrategy:
    """函数调用策略"""

    def build_steps(self, opcode: int, template_data: dict) -> list[HandlerStep]:
        steps = [
            ArgExtractStep(2, "funcname"),
            StateGetStep("funcname", "func", use_utility=True),
        ]
        return steps


class ConditionalJumpStrategy:
    """条件跳转策略"""

    def build_steps(self, opcode: int, template_data: dict) -> list[HandlerStep]:
        steps = [
            ArgExtractStep(2, "cond_expr"),
            ArgExtractStep(3, "target"),
            ConditionalJumpStep("cond_expr", "target"),
        ]
        return steps


class UnconditionalJumpStrategy:
    """无条件跳转策略"""

    def build_steps(self, opcode: int, template_data: dict) -> list[HandlerStep]:
        steps = [
            ArgExtractStep(2, "target"),
            JumpStep("target"),
        ]
        return steps


class ReturnValueStrategy:
    """返回值策略"""

    def build_steps(self, opcode: int, template_data: dict) -> list[HandlerStep]:
        steps = [
            ArgExtractStep(2, "val", "_eval_literal({var})"),
            StateSetStep("return_value", "val"),
            HaltStep(),
        ]
        return steps


class ReturnStrategy:
    """返回策略（无返回值）"""

    def build_steps(self, opcode: int, template_data: dict) -> list[HandlerStep]:
        return [HaltStep()]


class NoOpStrategy:
    """空操作策略"""

    def build_steps(self, opcode: int, template_data: dict) -> list[HandlerStep]:
        return [NoOpStep()]


class StackPopStrategy:
    """栈弹出赋值策略"""

    def build_steps(self, opcode: int, template_data: dict) -> list[HandlerStep]:
        steps = [
            ArgExtractStep(2, "varname"),
            StackPopStep("result"),
            StateSetStep("varname", "result"),
        ]
        return steps


# =============================================================================
# 分层 Handler 生成器
# =============================================================================

class LayeredHandlerGenerator:
    """
    分层 Handler 生成器

    通过组合步骤构建 handler，支持不同的拆分策略。
    保持与原有 LuaHandlerGenerator 的兼容性的同时，
    提供更模块化、可扩展的结构。
    """

    STRATEGIES: dict[int, type[HandlerStrategy]] = {
        0: NoOpStrategy,           # nop
        1: SimpleAssignStrategy,  # declare
        2: InitVarStrategy,       # init
        3: SimpleAssignStrategy,  # assign
        4: FunctionCallStrategy,  # call
        5: StackPopStrategy,      # call_assign
        6: ReturnStrategy,       # return
        7: ReturnValueStrategy,  # return_val
        8: UnconditionalJumpStrategy,  # jump
        9: ConditionalJumpStrategy,    # jump_if
        10: NoOpStrategy,         # do
        11: NoOpStrategy,         # end
    }

    def __init__(self, include_comments: bool = True):
        self.include_comments = include_comments
        self._custom_strategies: dict[int, HandlerStrategy] = {}

    def register_strategy(self, opcode: int, strategy: HandlerStrategy) -> None:
        """注册自定义策略"""
        self._custom_strategies[opcode] = strategy

    def get_strategy(self, opcode: int) -> HandlerStrategy | None:
        """获取策略"""
        if opcode in self._custom_strategies:
            return self._custom_strategies[opcode]
        strategy_cls = self.STRATEGIES.get(opcode)
        if strategy_cls:
            return strategy_cls()
        return None

    def generate_handler(
        self,
        opcode: int,
        desc: str = "",
        use_steps: bool = True,
        template: str | None = None
    ) -> str:
        """
        生成单个 handler

        Args:
            opcode: 操作码
            desc: 描述
            use_steps: 是否使用步骤组合
            template: 可选的模板字符串（用于兼容）

        Returns:
            Lua 代码字符串
        """
        lines = []

        if self.include_comments:
            lines.append(f"    -- opcode: {opcode} ({desc})")

        if not use_steps or template:
            lines.append(f"    {template.strip()}")
            return "\n".join(lines)

        strategy = self.get_strategy(opcode)
        if not strategy:
            lines.append(f"    -- No strategy for opcode {opcode}")
            lines.append("    return pc + 1")
            return "\n".join(lines)

        context = StepContext(opcode)
        steps = strategy.build_steps(opcode, {})
        composer = StepComposer(steps)
        handler_body = composer.compose(context)

        lines.append(handler_body)
        return "\n".join(lines)

    def generate_all_handlers(
        self,
        templates: dict[int, dict[str, str]] | None = None,
        use_layered: bool = True
    ) -> str:
        """
        生成所有 handlers

        Args:
            templates: 模板字典
            use_layered: 是否使用分层方式

        Returns:
            Lua 代码字符串
        """
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Instruction Handlers (Layered)")
        lines.append("-- =========================================")
        lines.append("")
        lines.append("local handlers = {")

        if templates is None:
            templates = LuaHandlerGenerator.HANDLER_TEMPLATES

        for opcode in sorted(templates.keys()):
            template_data = templates[opcode]
            desc = template_data.get("desc", "")
            template = template_data.get("template")

            handler_code = self.generate_handler(
                opcode, desc,
                use_steps=use_layered,
                template=template if not use_layered else None
            )
            lines.append(handler_code)

        # 默认处理器
        lines.append("")
        lines.append("    -- Default handler for unknown opcodes")
        lines.append("    default = function(instr, state, pc)")
        lines.append("        if _DEBUG then")
        lines.append("            print('Unknown opcode: ' .. tostring(instr[1]))")
        lines.append("        end")
        lines.append("        return pc + 1")
        lines.append("    end,")

        lines.append("}")
        return "\n".join(lines)


class HandlerMappingBuilder:
    """
    Handler 映射构建器

    从 Python 指令处理函数映射到 Lua handler
    """

    def __init__(self):
        self._mappings: dict[int, str] = {}

    def add_mapping(self, opcode: int, lua_handler: str) -> 'HandlerMappingBuilder':
        """添加 opcode 到 Lua handler 的映射"""
        self._mappings[opcode] = lua_handler
        return self

    def add_from_template(
        self,
        opcode: int,
        description: str,
        arg_extract: str,
        body: str,
        next_pc: str = "pc + 1"
    ) -> 'HandlerMappingBuilder':
        """
        从模板添加映射

        Args:
            opcode: 操作码
            description: 描述
            arg_extract: 参数提取代码
            body: handler 主体
            next_pc: 下一 PC 表达式
        """
        handler = f"""
    [{opcode}] = function(instr, state, pc)
        {arg_extract}
        {body}
        return {next_pc}
    end"""
        self._mappings[opcode] = handler
        return self

    def build(self) -> str:
        """构建完整的 handler 表"""
        lines = ["local handlers = {"]
        for opcode in sorted(self._mappings.keys()):
            lines.append(f"    -- opcode: {opcode}")
            lines.append(f"    {self._mappings[opcode].strip()}")
        lines.append("}")
        return "\n".join(lines)


def generate_lua_handlers() -> str:
    """
    便捷函数：生成 Lua handlers

    Returns:
        Lua handler 代码字符串
    """
    generator = LuaHandlerGenerator()
    return generator.generate()


def demo_layered_handlers():
    """
    演示分层 Handler 生成
    """
    print("=" * 60)
    print("Layered Handler Generation Demo")
    print("=" * 60)

    gen = LayeredHandlerGenerator(include_comments=True)

    print("\n[1] 简单赋值 Handler (分层方式):")
    print("-" * 40)
    handler = gen.generate_handler(3, "assign", use_steps=True)
    print(handler)

    print("\n[2] 变量初始化 Handler (分层方式):")
    print("-" * 40)
    handler = gen.generate_handler(2, "init", use_steps=True)
    print(handler)

    print("\n[3] 条件跳转 Handler (分层方式):")
    print("-" * 40)
    handler = gen.generate_handler(9, "jump_if", use_steps=True)
    print(handler)

    print("\n[4] 使用模板方式 (兼容旧代码):")
    print("-" * 40)
    handler = gen.generate_handler(0, "nop", use_steps=False, template="""
    [0] = function(instr, state, pc)
        return pc + 1
    end""")
    print(handler)

    print("\n[5] 步骤组合示例:")
    print("-" * 40)
    context = StepContext(99)
    composer = StepComposer([
        ArgExtractStep(2, "varname"),
        ExprEvalStep("instr[3]", "value"),
        StateSetStep("varname", "value"),
    ])
    print(composer.compose(context))

    print("\n[6] 自定义策略示例:")
    print("-" * 40)

    class CustomIncrementStrategy:
        """自定义增量策略"""

        def build_steps(self, opcode, template_data):
            return [
                ArgExtractStep(2, "varname"),
                ArgExtractStep(3, "incr", "_eval_literal({var})"),
                StateGetStep("varname", "old_val"),
                ExprEvalStep("old_val + incr", "new_val"),
                StateSetStep("varname", "new_val"),
            ]

    gen.register_strategy(100, CustomIncrementStrategy())
    handler = gen.generate_handler(100, "custom_increment", use_steps=True)
    print(handler)

    print("\n" + "=" * 60)
    print("Demo Complete")
    print("=" * 60)


if __name__ == "__main__":
    demo_layered_handlers()


# =============================================================================
# PC 更新逻辑分层优化
# =============================================================================

from dataclasses import dataclass
from typing import Literal


@dataclass
class PCUpdate:
    """
    PC 更新结果

    统一表示 handler 返回的 PC 更新信息，
    支持多种更新模式。
    """
    action: Literal["continue", "jump", "halt", "none"]
    offset: int = 1                    # 基础偏移量（用于 continue）
    target: int | None = None          # 跳转目标（用于 jump）
    value: Any = None                   # 可选的返回值

    @classmethod
    def continue_at(cls, offset: int = 1) -> 'PCUpdate':
        """继续执行，偏移指定数量"""
        return cls(action="continue", offset=offset)

    @classmethod
    def jump_to(cls, target: int) -> 'PCUpdate':
        """跳转到目标位置"""
        return cls(action="jump", target=target)

    @classmethod
    def halt(cls, value: Any = None) -> 'PCUpdate':
        """停止执行"""
        return cls(action="halt", value=value)

    @classmethod
    def none(cls) -> 'PCUpdate':
        """无操作（未知 opcode）"""
        return cls(action="none")


class PCUpdateBuilder:
    """
    PC 更新构建器

    提供链式 API 构建 PC 更新结果
    """

    def __init__(self, base_pc: int):
        self.base_pc = base_pc
        self._action: Literal["continue", "jump", "halt", "none"] = "continue"
        self._offset: int = 1
        self._target: int | None = None
        self._value: Any = None

    def then_continue(self, offset: int = 1) -> 'PCUpdateBuilder':
        """继续执行"""
        self._action = "continue"
        self._offset = offset
        return self

    def then_jump(self, target: int) -> 'PCUpdateBuilder':
        """跳转"""
        self._action = "jump"
        self._target = target
        return self

    def then_halt(self, value: Any = None) -> 'PCUpdateBuilder':
        """停止"""
        self._action = "halt"
        self._value = value
        return self

    def build(self) -> PCUpdate:
        """构建 PC 更新结果"""
        return PCUpdate(
            action=self._action,
            offset=self._offset,
            target=self._target,
            value=self._value
        )


class PCOffsetCalculator:
    """
    PC 偏移计算器

    提供统一的偏移计算逻辑，支持条件偏移
    """

    @staticmethod
    def sequential(base_pc: int, offset: int = 1) -> int:
        """顺序执行：基础偏移"""
        return base_pc + offset

    @staticmethod
    def absolute(target: int) -> int:
        """绝对跳转"""
        return target

    @staticmethod
    def relative(base_pc: int, delta: int) -> int:
        """相对跳转"""
        return base_pc + delta

    @staticmethod
    def conditional(
        condition: bool,
        true_pc: int,
        false_pc: int
    ) -> int:
        """条件计算"""
        return true_pc if condition else false_pc


class DispatchState:
    """
    调度中间状态

    在 handler 和执行循环之间传递状态
    """

    def __init__(
        self,
        pc: int,
        halted: bool = False,
        return_value: Any = None
    ):
        self.pc = pc
        self.halted = halted
        self.return_value = return_value
        self._intermediate: dict[str, Any] = {}

    def set_intermediate(self, key: str, value: Any) -> None:
        """设置中间状态"""
        self._intermediate[key] = value

    def get_intermediate(self, key: str, default: Any = None) -> Any:
        """获取中间状态"""
        return self._intermediate.get(key, default)

    def update_from_handler(
        self,
        raw_offset: int,
        target: int | None = None,
        halted: bool = False,
        return_value: Any = None
    ) -> None:
        """
        从 handler 结果更新状态

        Args:
            raw_offset: handler 返回的原始偏移
            target: 跳转目标（可选）
            halted: 是否停止
            return_value: 返回值
        """
        self.halted = halted
        self.return_value = return_value

        if halted:
            self.pc = 0
        elif target is not None:
            self.pc = target
        else:
            self.pc = self.pc + raw_offset

    def compute_next_pc(self, base_offset: int = 1) -> int:
        """
        计算下一条 PC

        Args:
            base_offset: 默认偏移量

        Returns:
            下一条 PC
        """
        if self.halted:
            return 0
        return self.pc + base_offset


def compute_next_pc(
    current_pc: int,
    raw_result: int | None,
    handler_flags: dict[str, bool]
) -> int:
    """
    统一 PC 计算函数

    根据 handler 返回结果计算下一条指令位置

    Args:
        current_pc: 当前 PC
        raw_result: handler 返回的原始结果
        handler_flags: handler 设置的标志
            - halt: 是否停止
            - jump: 是否跳转
            - has_target: 是否有跳转目标

    Returns:
        下一条 PC
    """
    # 停止情况
    if handler_flags.get("halt", False):
        return 0

    # 跳转情况
    if handler_flags.get("jump", False):
        if handler_flags.get("has_target", False) and raw_result is not None:
            return raw_result
        return 0

    # 顺序执行
    if raw_result is not None and isinstance(raw_result, int):
        return current_pc + raw_result

    return current_pc + 1


class UnifiedDispatchCalculator:
    """
    统一调度计算器

    集中管理 PC 计算逻辑
    """

    def __init__(self, code_length: int | None = None):
        self.code_length = code_length
        self._bounds_check = True

    def enable_bounds_check(self, enabled: bool) -> None:
        """启用/禁用边界检查"""
        self._bounds_check = enabled

    def calculate(
        self,
        current_pc: int,
        raw_result: int | None,
        halted: bool = False,
        target: int | None = None
    ) -> int:
        """
        计算下一条 PC

        Args:
            current_pc: 当前 PC
            raw_result: handler 返回结果
            halted: 是否停止
            target: 跳转目标

        Returns:
            下一条 PC
        """
        if halted:
            return 0

        if target is not None:
            next_pc = target
        elif raw_result is not None:
            next_pc = current_pc + raw_result
        else:
            next_pc = current_pc + 1

        if self._bounds_check:
            return self._clamp_pc(next_pc)
        return next_pc

    def _clamp_pc(self, pc: int) -> int:
        """边界限制"""
        if pc < 1:
            return 0
        if self.code_length and pc > self.code_length:
            return self.code_length + 1
        return pc

    def generate_lua_calculator(self) -> str:
        """
        生成 Lua PC 计算函数

        Returns:
            Lua 代码字符串
        """
        return """local function compute_next_pc(pc, result, halted, target)
    -- 停止情况
    if halted then return 0 end

    -- 跳转情况
    if target then
        local next_pc = target
        -- 边界检查
        if next_pc < 1 then return 0 end
        if next_pc > #code + 1 then return #code + 1 end
        return next_pc
    end

    -- 顺序执行
    local offset = result or 1
    local next_pc = pc + offset

    -- 边界检查
    if next_pc < 1 then return 0 end
    if next_pc > #code + 1 then return #code + 1 end
    return next_pc
end"""


class LayeredExecutorGenerator:
    """
    分层执行循环生成器

    使用统一的 PC 计算逻辑生成执行循环
    """

    def __init__(
        self,
        calculator: UnifiedDispatchCalculator | None = None,
        include_bounds_check: bool = True,
        include_debug: bool = False
    ):
        self.calculator = calculator or UnifiedDispatchCalculator()
        self.include_bounds_check = include_bounds_check
        self.include_debug = include_debug

    def generate_executor_loop(
        self,
        code_var: str = "code",
        state_var: str = "state",
        pc_var: str = "pc",
        function_name: str = "execute"
    ) -> str:
        """
        生成执行循环

        Args:
            code_var: 代码表变量名
            state_var: 状态变量名
            pc_var: PC 变量名
            function_name: 函数名

        Returns:
            Lua 代码字符串
        """
        lines = []

        lines.append("-- =========================================")
        lines.append("-- Executor Loop (Layered PC Update)")
        lines.append("-- =========================================")
        lines.append("")

        # 生成 PC 计算函数
        lines.append(self.generate_pc_calculator_function())

        # 生成执行循环
        lines.append("")
        lines.append(f"local function {function_name}({code_var}, {state_var})")
        lines.append(f"    local {pc_var} = 1")

        if self.include_debug:
            lines.append('    if _DEBUG then print("[EXEC] Starting...") end')

        lines.append(f"    while {pc_var} and not {state_var}.halted do")
        lines.append(f"        local instr = {code_var}[{pc_var}]")
        lines.append("        if not instr then break end")

        if self.include_debug:
            lines.append('        if _DEBUG then print("[EXEC] pc=" .. pc .. " op=" .. instr[1]) end')

        # 调用 handler
        lines.append("        local op = instr[1]")
        lines.append("        local handler = handlers[op] or handlers.default")
        lines.append(f"        local result = handler(instr, {state_var}, {pc_var})")

        # 使用统一计算逻辑
        lines.append(f"        {pc_var} = compute_next_pc({pc_var}, result, {state_var}.halted)")

        if self.include_bounds_check:
            lines.append(f"        if {pc_var} < 1 or {pc_var} > #{code_var} + 1 then break end")

        lines.append("    end")

        if self.include_debug:
            lines.append('    if _DEBUG then print("[EXEC] Finished, result=" .. tostring(state.return_value)) end')

        lines.append(f"    return {state_var}.return_value")
        lines.append("end")

        return "\n".join(lines)

    def generate_pc_calculator_function(self) -> str:
        """生成 PC 计算函数"""
        lines = []

        lines.append("-- PC Calculator: Unified next PC computation")
        lines.append("local function compute_next_pc(pc, result, halted)")
        lines.append("    -- Stop case")
        lines.append("    if halted then return 0 end")

        lines.append("")
        lines.append("    -- Handle result")
        lines.append("    local next_pc")
        lines.append("    if type(result) == 'number' then")
        lines.append("        next_pc = pc + result")
        lines.append("    elseif type(result) == 'nil' then")
        lines.append("        next_pc = pc + 1")
        lines.append("    else")
        lines.append("        -- Jump target (direct PC value)")
        lines.append("        next_pc = result or (pc + 1)")
        lines.append("    end")

        if self.include_bounds_check:
            lines.append("")
            lines.append("    -- Bounds check")
            lines.append("    if next_pc < 1 then return 0 end")
            lines.append("    if next_pc > #code + 1 then return #code + 1 end")

        lines.append("    return next_pc")
        lines.append("end")

        return "\n".join(lines)

    def generate_with_intermediate_state(
        self,
        code_var: str = "code",
        state_var: str = "state"
    ) -> str:
        """
        使用中间状态的执行循环

        Args:
            code_var: 代码表变量名
            state_var: 状态变量名

        Returns:
            Lua 代码字符串
        """
        lines = []

        lines.append("-- =========================================")
        lines.append("-- Executor Loop (Intermediate State)")
        lines.append("-- =========================================")
        lines.append("")

        lines.append(self.generate_pc_calculator_function())

        lines.append("")
        lines.append("local function execute(code, state)")
        lines.append("    local pc = 1")
        lines.append("    -- Intermediate state")
        lines.append("    local offset = 1")
        lines.append("    local target = nil")
        lines.append("    local halted = false")

        lines.append("")
        lines.append("    while pc and not halted do")
        lines.append("        local instr = code[pc]")
        lines.append("        if not instr then break end")

        lines.append("")
        lines.append("        -- Execute handler")
        lines.append("        local op = instr[1]")
        lines.append("        local handler = handlers[op] or handlers.default")
        lines.append("        local result = handler(instr, state, pc)")

        lines.append("")
        lines.append("        -- Update intermediate state")
        lines.append("        halted = state.halted")
        lines.append("        target = nil")
        lines.append("        offset = 1")

        lines.append("")
        lines.append("        -- Parse handler result")
        lines.append("        if halted then")
        lines.append("            break")
        lines.append("        elseif type(result) == 'number' then")
        lines.append("            if result < 0 or result > 1000 then")
        lines.append("                -- Treat as jump target")
        lines.append("                target = result")
        lines.append("            else")
        lines.append("                offset = result")
        lines.append("            end")
        lines.append("        end")

        lines.append("")
        lines.append("        -- Compute next PC")
        lines.append("        if target then")
        lines.append("            pc = target")
        lines.append("        else")
        lines.append("            pc = pc + offset")
        lines.append("        end")

        lines.append("")
        lines.append("        -- Bounds check")
        lines.append("        if pc < 1 or pc > #code + 1 then break end")

        lines.append("    end")

        lines.append("")
        lines.append("    return state.return_value")
        lines.append("end")

        return "\n".join(lines)


# =============================================================================
# 代码生成多样化策略
# =============================================================================

import random as random_module
from enum import Enum
from typing import Callable


class ExpressionVariant(Enum):
    """表达式变体枚举"""
    DIRECT = "direct"           # 直接使用
    TEMP_VAR = "temp_var"       # 临时变量
    NESTED = "nested"           # 嵌套表达式
    TABLE_LOOKUP = "table"      # 表查找


class VariableUsage(Enum):
    """变量使用方式"""
    DIRECT = "direct"           # 直接访问 state.locals
    UTILITY_FUNC = "utility"    # 通过工具函数
    CACHED = "cached"           # 缓存到局部变量


class HandlerStructure(Enum):
    """Handler 结构类型"""
    COMPACT = "compact"         # 紧凑单行
    EXPANDED = "expanded"       # 展开多行
    GUARDED = "guarded"         # 带守卫检查
    PIPELINED = "pipelined"     # 流水线式


class InstructionLayout(Enum):
    """指令布局方式"""
    SEQUENTIAL = "sequential"    # 顺序布局
    GROUPED = "grouped"          # 按类型分组
    INTERLEAVED = "interleaved"  # 交错布局
    BLOCK = "block"              # 块布局


# =============================================================================
# 表达式多样化生成器
# =============================================================================

class ExpressionDiversifier:
    """
    表达式多样化生成器

    将同一逻辑的表达式转换为多种等价形式
    """

    def __init__(self, rng: random_module.Random | None = None):
        self.rng = rng or random_module.Random()

    def diversify_assignment(
        self,
        varname: str,
        value_expr: str
    ) -> str:
        """
        多样化赋值表达式

        Args:
            varname: 变量名
            value_expr: 值表达式

        Returns:
            多样化的赋值代码
        """
        variants = [
            lambda: f"state.locals['{varname}'] = {value_expr}",
            lambda: f"({varname}, state.locals['{varname}']) = ({value_expr}, {value_expr})",
            lambda: f"local _v = {value_expr}; state.locals['{varname}'] = _v",
        ]
        return self.rng.choice(variants)()

    def diversify_get(
        self,
        varname: str,
        context_var: str = "state"
    ) -> str:
        """
        多样化变量获取

        Args:
            varname: 变量名
            context_var: 上下文变量名

        Returns:
            多样化的获取代码
        """
        variants = [
            lambda: f"{context_var}.locals['{varname}']",
            lambda: f"_get({context_var}, '{varname}')",
            lambda: f"({context_var}.locals['{varname}'] or {context_var}.globals['{varname}'])",
        ]
        return self.rng.choice(variants)()

    def diversify_condition(
        self,
        cond_expr: str,
        context_var: str = "state"
    ) -> str:
        """
        多样化条件表达式

        Args:
            cond_expr: 条件表达式
            context_var: 上下文变量名

        Returns:
            多样化的条件代码
        """
        variants = [
            lambda: f"_eval_condition({context_var}, '{cond_expr}')",
            lambda: f"(({cond_expr} and true) or false)",
            lambda: f"_is_truthy(_get({context_var}, '{cond_expr}'))",
        ]
        return self.rng.choice(variants)()

    def diversify_binary_op(
        self,
        left: str,
        op: str,
        right: str
    ) -> str:
        """
        多样化二元运算

        Args:
            left: 左操作数
            op: 运算符
            right: 右操作数

        Returns:
            多样化的运算代码
        """
        if op == "+":
            variants = [
                lambda: f"{left} + {right}",
                lambda: f"({left} - (-{right}))",
                lambda: f"(function() local a,b={left},{right};return a+b end)()",
            ]
        elif op == "-":
            variants = [
                lambda: f"{left} - {right}",
                lambda: f"({left} + (-{right}))",
            ]
        elif op == "*":
            variants = [
                lambda: f"{left} * {right}",
                lambda: f"({left} / (1/{right}))",
            ]
        else:
            variants = [lambda: f"{left} {op} {right}"]
        return self.rng.choice(variants)()


# =============================================================================
# 变量使用多样化
# =============================================================================

class VariableUsageDiversifier:
    """
    变量使用方式多样化

    同一变量访问可以用不同方式实现
    """

    def __init__(self, rng: random_module.Random | None = None):
        self.rng = rng or random_module.Random()

    def generate_get(
        self,
        varname: str,
        usage: VariableUsage,
        context_var: str = "state"
    ) -> str:
        """
        生成多样化的变量获取

        Args:
            varname: 变量名
            usage: 使用方式
            context_var: 上下文变量

        Returns:
            Lua 代码
        """
        if usage == VariableUsage.DIRECT:
            return f"{context_var}.locals['{varname}']"
        elif usage == VariableUsage.UTILITY_FUNC:
            return f"_get({context_var}, '{varname}')"
        elif usage == VariableUsage.CACHED:
            return f"(state._cache and state._cache['{varname}']) or {context_var}.locals['{varname}']"
        return f"{context_var}.locals['{varname}']"

    def generate_set(
        self,
        varname: str,
        value: str,
        usage: VariableUsage,
        context_var: str = "state"
    ) -> str:
        """
        生成多样化的变量设置

        Args:
            varname: 变量名
            value: 值
            usage: 使用方式
            context_var: 上下文变量

        Returns:
            Lua 代码
        """
        if usage == VariableUsage.DIRECT:
            return f"{context_var}.locals['{varname}'] = {value}"
        elif usage == VariableUsage.UTILITY_FUNC:
            return f"_set({context_var}, '{varname}', {value})"
        elif usage == VariableUsage.CACHED:
            return f"{context_var}.locals['{varname}'] = {value}; {context_var}._cache = {context_var}._cache or {{}}; {context_var}._cache['{varname}'] = {value}"
        return f"{context_var}.locals['{varname}'] = {value}"

    def select_usage(self) -> VariableUsage:
        """随机选择使用方式"""
        return self.rng.choice(list(VariableUsage))


# =============================================================================
# Handler 结构多样化
# =============================================================================

class HandlerStructureDiversifier:
    """
    Handler 结构多样化

    同一 handler 可以有多种内部结构
    """

    def __init__(self, rng: random_module.Random | None = None):
        self.rng = rng or random_module.Random()
        self.expr_diversifier = ExpressionDiversifier(rng)

    def generate_nop_handler(
        self,
        structure: HandlerStructure
    ) -> str:
        """
        生成多样化的 NOP handler

        Args:
            structure: 结构类型

        Returns:
            Lua 代码
        """
        if structure == HandlerStructure.COMPACT:
            return "function(instr, state, pc) return pc + 1 end"
        elif structure == HandlerStructure.EXPANDED:
            return """function(instr, state, pc)
    return pc + 1
end"""
        elif structure == HandlerStructure.GUARDED:
            return """function(instr, state, pc)
    if instr and state then
        return pc + 1
    end
    return pc
end"""
        elif structure == HandlerStructure.PIPELINED:
            return """function(instr, state, pc)
    local _pc = pc
    local _instr = instr
    local _state = state
    _pc = _pc + 1
    return _pc
end"""
        return "function(instr, state, pc) return pc + 1 end"

    def generate_assign_handler(
        self,
        structure: HandlerStructure,
        varname: str = "x",
        value_expr: str = "42"
    ) -> str:
        """
        生成多样化的赋值 handler

        Args:
            structure: 结构类型
            varname: 变量名
            value_expr: 值表达式

        Returns:
            Lua 代码
        """
        if structure == HandlerStructure.COMPACT:
            return f"function(instr,state,pc) _set(state,'{varname}',{value_expr}) return pc+1 end"
        elif structure == HandlerStructure.EXPANDED:
            return f"""function(instr, state, pc)
    local v = {value_expr}
    _set(state, '{varname}', v)
    return pc + 1
end"""
        elif structure == HandlerStructure.GUARDED:
            return f"""function(instr, state, pc)
    if instr and instr[2] == '{varname}' then
        local val = {value_expr}
        _set(state, '{varname}', val)
    end
    return (pc or 0) + 1
end"""
        elif structure == HandlerStructure.PIPELINED:
            return f"""function(instr, state, pc)
    local _v = {value_expr}
    local _st = state
    _st.locals = _st.locals or {{}}
    _st.locals['{varname}'] = _v
    return pc + 1
end"""
        return f"function(instr, state, pc) _set(state,'{varname}',{value_expr}) return pc+1 end"

    def generate_jump_handler(
        self,
        structure: HandlerStructure,
        target: str = "10"
    ) -> str:
        """
        生成多样化的跳转 handler

        Args:
            structure: 结构类型
            target: 跳转目标

        Returns:
            Lua 代码
        """
        if structure == HandlerStructure.COMPACT:
            return f"function(instr,state,pc) return {target} end"
        elif structure == HandlerStructure.EXPANDED:
            return f"""function(instr, state, pc)
    local t = {target}
    return t
end"""
        elif structure == HandlerStructure.GUARDED:
            return f"""function(instr, state, pc)
    if instr and instr[3] then
        return instr[3]
    end
    return {target}
end"""
        elif structure == HandlerStructure.PIPELINED:
            return f"""function(instr, state, pc)
    local _t = instr and instr[3] or {target}
    return _t
end"""
        return f"function(instr, state, pc) return {target} end"

    def select_structure(self) -> HandlerStructure:
        """随机选择结构类型"""
        return self.rng.choice(list(HandlerStructure))


# =============================================================================
# 指令布局多样化
# =============================================================================

class InstructionLayoutDiversifier:
    """
    指令布局多样化

    指令可以按不同方式组织
    """

    def __init__(self, rng: random_module.Random | None = None):
        self.rng = rng or random_module.Random()

    def layout_sequential(
        self,
        instructions: list[tuple[int, str]]
    ) -> list[tuple[int, str]]:
        """
        顺序布局

        Args:
            instructions: (opcode, code) 对列表

        Returns:
            重新排序后的指令
        """
        return instructions

    def layout_grouped(
        self,
        instructions: list[tuple[int, str]]
    ) -> list[tuple[int, str]]:
        """
        分组布局：按 opcode 类型分组

        Args:
            instructions: (opcode, code) 对列表

        Returns:
            重新排序后的指令
        """
        groups: dict[int, list[tuple[int, str]]] = {}
        for instr in instructions:
            opcode = instr[0]
            if opcode not in groups:
                groups[opcode] = []
            groups[opcode].append(instr)

        result = []
        for opcode in sorted(groups.keys()):
            result.extend(groups[opcode])
        return result

    def layout_interleaved(
        self,
        instructions: list[tuple[int, str]]
    ) -> list[tuple[int, str]]:
        """
        交错布局：交替不同类型的指令

        Args:
            instructions: (opcode, code) 对列表

        Returns:
            重新排序后的指令
        """
        if not instructions:
            return []

        groups: dict[int, list[tuple[int, str]]] = {}
        for instr in instructions:
            opcode = instr[0]
            if opcode not in groups:
                groups[opcode] = []
            groups[opcode].append(instr)

        result = []
        max_len = max(len(g) for g in groups.values()) if groups else 0

        for i in range(max_len):
            for opcode in sorted(groups.keys()):
                if i < len(groups[opcode]):
                    result.append(groups[opcode][i])

        return result

    def layout_by_layout(
        self,
        instructions: list[tuple[int, str]],
        layout: InstructionLayout
    ) -> list[tuple[int, str]]:
        """
        根据布局类型重新排列指令

        Args:
            instructions: 指令列表
            layout: 布局类型

        Returns:
            重新排序后的指令
        """
        if layout == InstructionLayout.SEQUENTIAL:
            return self.layout_sequential(instructions)
        elif layout == InstructionLayout.GROUPED:
            return self.layout_grouped(instructions)
        elif layout == InstructionLayout.INTERLEAVED:
            return self.layout_interleaved(instructions)
        elif layout == InstructionLayout.BLOCK:
            return self.layout_grouped(instructions)  # BLOCK 等同于 GROUPED
        return instructions

    def select_layout(self) -> InstructionLayout:
        """随机选择布局类型"""
        return self.rng.choice(list(InstructionLayout))


# =============================================================================
# 综合策略控制器
# =============================================================================

class GenerationDiversifier:
    """
    综合多样化策略控制器

    整合所有多样化选项，提供统一接口
    """

    def __init__(
        self,
        rng: random_module.Random | None = None,
        expr_variant: ExpressionVariant | None = None,
        var_usage: VariableUsage | None = None,
        handler_struct: HandlerStructure | None = None,
        instr_layout: InstructionLayout | None = None
    ):
        self.rng = rng or random_module.Random()

        # 子多样化器
        self.expr_diversifier = ExpressionDiversifier(rng)
        self.var_diversifier = VariableUsageDiversifier(rng)
        self.handler_diversifier = HandlerStructureDiversifier(rng)
        self.layout_diversifier = InstructionLayoutDiversifier(rng)

        # 配置（None 表示随机选择）
        self.expr_variant = expr_variant
        self.var_usage = var_usage
        self.handler_struct = handler_struct
        self.instr_layout = instr_layout

    def _select_or_use(self, value, choices):
        """选择值：如果配置了则使用，否则随机选择"""
        if value is None:
            return self.rng.choice(list(choices))
        return value

    def diversify_handler(
        self,
        opcode: int,
        base_code: str,
        **kwargs
    ) -> str:
        """
        多样化 handler 代码

        Args:
            opcode: 操作码
            base_code: 基础代码
            **kwargs: 额外参数

        Returns:
            多样化后的代码
        """
        struct = self._select_or_use(self.handler_struct, HandlerStructure)

        if opcode == 0:  # NOP
            return self.handler_diversifier.generate_nop_handler(struct)
        elif opcode in (1, 2, 3):  # DECLARE, INIT, ASSIGN
            varname = kwargs.get("varname", "x")
            value = kwargs.get("value", "42")
            return self.handler_diversifier.generate_assign_handler(struct, varname, value)
        elif opcode in (8, 9):  # JUMP, JUMP_IF
            target = kwargs.get("target", "10")
            return self.handler_diversifier.generate_jump_handler(struct, target)

        return base_code

    def diversify_expression(
        self,
        expr_type: str,
        **kwargs
    ) -> str:
        """
        多样化表达式

        Args:
            expr_type: 表达式类型
            **kwargs: 额外参数

        Returns:
            多样化后的代码
        """
        if expr_type == "assignment":
            return self.expr_diversifier.diversify_assignment(
                kwargs.get("varname", "x"),
                kwargs.get("value", "42")
            )
        elif expr_type == "get":
            return self.expr_diversifier.diversify_get(
                kwargs.get("varname", "x")
            )
        elif expr_type == "condition":
            return self.expr_diversifier.diversify_condition(
                kwargs.get("cond", "x")
            )
        elif expr_type == "binary_op":
            return self.expr_diversifier.diversify_binary_op(
                kwargs.get("left", "a"),
                kwargs.get("op", "+"),
                kwargs.get("right", "b")
            )
        return kwargs.get("default", "nil")

    def diversify_instructions(
        self,
        instructions: list[tuple[int, str]]
    ) -> list[tuple[int, str]]:
        """
        多样化指令布局

        Args:
            instructions: 指令列表

        Returns:
            重新布局后的指令
        """
        layout = self._select_or_use(self.instr_layout, InstructionLayout)
        return self.layout_diversifier.layout_by_layout(instructions, layout)

    def generate_diverse_handlers(
        self,
        templates: dict[int, dict[str, str]]
    ) -> str:
        """
        生成多样化的 handlers 表

        Args:
            templates: handler 模板

        Returns:
            Lua 代码
        """
        lines = []
        lines.append("-- Diverse Handlers (GenerationDiversifier)")
        lines.append("local handlers = {")

        for opcode in sorted(templates.keys()):
            template = templates[opcode]
            desc = template.get("desc", "")

            struct = self._select_or_use(self.handler_struct, HandlerStructure)

            if opcode == 0:
                code = self.handler_diversifier.generate_nop_handler(struct)
            elif opcode == 3:
                code = self.handler_diversifier.generate_assign_handler(struct, "var", "_eval_expr(state, instr[3])")
            elif opcode == 9:
                code = self.handler_diversifier.generate_jump_handler(struct, "instr[3]")
            else:
                code = template.get("template", "function() return pc + 1 end")

            lines.append(f"    -- {opcode}: {desc}")
            lines.append(f"    [{opcode}] = {code.strip()},")

        lines.append("}")
        return "\n".join(lines)

    def get_strategy_summary(self) -> dict:
        """
        获取当前策略摘要

        Returns:
            策略配置字典
        """
        return {
            "expression_variant": self.expr_variant.value if self.expr_variant else "random",
            "variable_usage": self.var_usage.value if self.var_usage else "random",
            "handler_structure": self.handler_struct.value if self.handler_struct else "random",
            "instruction_layout": self.instr_layout.value if self.instr_layout else "random",
        }


def demo_code_diversification():
    """
    演示代码生成多样化
    """
    print("=" * 60)
    print("Code Generation Diversification Demo")
    print("=" * 60)

    rng = random_module.Random(42)

    # 创建多样化器
    diversifier = GenerationDiversifier(rng)

    print("\n[1] 表达式多样化:")
    print("-" * 40)

    print("赋值表达式:")
    for i in range(3):
        expr = diversifier.expr_diversifier.diversify_assignment("x", "42")
        print(f"  变体 {i+1}: {expr}")

    print("\n变量获取:")
    for i in range(3):
        expr = diversifier.expr_diversifier.diversify_get("count")
        print(f"  变体 {i+1}: {expr}")

    print("\n条件表达式:")
    for i in range(3):
        expr = diversifier.expr_diversifier.diversify_condition("x > 0")
        print(f"  变体 {i+1}: {expr}")

    print("\n[2] 变量使用方式多样化:")
    print("-" * 40)

    for usage in VariableUsage:
        get_code = diversifier.var_diversifier.generate_get("x", usage)
        set_code = diversifier.var_diversifier.generate_set("x", "42", usage)
        print(f"  [{usage.value}]")
        print(f"    get:  {get_code}")
        print(f"    set:  {set_code}")

    print("\n[3] Handler 结构多样化:")
    print("-" * 40)

    for struct in HandlerStructure:
        handler = diversifier.handler_diversifier.generate_nop_handler(struct)
        preview = handler.replace("\n", " | ")[:60]
        print(f"  [{struct.value}] {preview}...")

    print("\n[4] 指令布局多样化:")
    print("-" * 40)

    # 创建测试指令
    test_instr = [
        (1, "declare x"), (2, "init x=1"), (1, "declare y"),
        (3, "assign"), (1, "declare z"), (3, "assign"),
        (9, "jump"), (3, "assign"), (0, "nop"),
    ]

    for layout in InstructionLayout:
        rearranged = diversifier.layout_diversifier.layout_by_layout(test_instr, layout)
        opcodes = [str(instr[0]) for instr in rearranged]
        print(f"  [{layout.value}]: {', '.join(opcodes)}")

    print("\n[5] 综合多样化:")
    print("-" * 40)

    # 固定配置
    fixed_diversifier = GenerationDiversifier(
        rng,
        expr_variant=ExpressionVariant.NESTED,
        var_usage=VariableUsage.UTILITY_FUNC,
        handler_struct=HandlerStructure.GUARDED,
        instr_layout=InstructionLayout.GROUPED
    )
    print("固定策略:")
    print(f"  {fixed_diversifier.get_strategy_summary()}")

    handler = fixed_diversifier.diversify_handler(3, "")
    print(f"\n赋值 Handler ({HandlerStructure.GUARDED}):")
    print(handler)

    print("\n[6] 随机策略多次生成:")
    print("-" * 40)

    for i in range(3):
        rng_i = random_module.Random(i)
        div = GenerationDiversifier(rng_i)
        summary = div.get_strategy_summary()
        handler = div.diversify_handler(0, "")
        preview = handler.replace("\n", " | ")[:50]
        print(f"  生成 {i+1}:")
        print(f"    策略: expr={summary['expression_variant']}, struct={summary['handler_structure']}")
        print(f"    NOP:   {preview}...")

    print("\n" + "=" * 60)
    print("Demo Complete")
    print("=" * 60)


if __name__ == "__main__":
    demo_code_diversification()


class InterpreterCodeGenerator:
    """
    完整解释器代码生成器

    整合 instruction table 和 handler 生成
    """

    def __init__(
        self,
        handler_generator: LuaHandlerGenerator | None = None,
        serializer: InstructionSerializer | None = None
    ):
        self.handler_generator = handler_generator or LuaHandlerGenerator()
        self.serializer = serializer or InstructionSerializer(compact=True)

    def generate(
        self,
        instructions: list[Instruction] | None = None,
        state_var: str = "state",
        code_var: str = "code",
        result_var: str = "_result",
        include_debug: bool = False
    ) -> str:
        """
        生成完整的解释器代码

        Args:
            instructions: 指令列表
            state_var: 状态变量名
            code_var: 代码变量名
            result_var: 结果变量名
            include_debug: 是否包含调试信息

        Returns:
            完整的 Lua 代码
        """
        lines = []

        # Header
        lines.append("-- =========================================")
        lines.append("-- Lua Instruction Interpreter")
        lines.append("-- Generated by lua_obfuscator")
        lines.append("-- =========================================")
        lines.append("")
        lines.append("local _DEBUG = " + ("true" if include_debug else "false"))
        lines.append("")

        # Instruction Code (如果提供)
        if instructions:
            lines.append("-- =========================================")
            lines.append("-- Instruction Code")
            lines.append("-- =========================================")
            lines.append(self.serializer.serialize(instructions, code_var))
            lines.append("")

        # Handlers
        lines.append(self.handler_generator.generate())
        lines.append("")

        # Execution State
        lines.append("-- =========================================")
        lines.append("-- Execution State")
        lines.append("-- =========================================")
        lines.append(f"local {state_var} = {{")
        lines.append("    locals = {},")
        lines.append("    globals = {},")
        lines.append("    stack = {},")
        lines.append("    pc = 1,")
        lines.append("    halted = false,")
        lines.append("    return_value = nil,")
        lines.append("}")
        lines.append("")

        # Executor Loop
        lines.append("-- =========================================")
        lines.append("-- Executor Loop")
        lines.append("-- =========================================")
        lines.append(f"local function execute({code_var}, {state_var})")
        lines.append(f"    local {state_var}_pc = 1")
        lines.append(f"    while {state_var}_pc and not {state_var}.halted do")
        lines.append(f"        local instr = {code_var}[{state_var}_pc]")
        lines.append("        if not instr then break end")
        lines.append(f"        {state_var}_pc = dispatch(instr, {state_var}, {state_var}_pc)")
        lines.append("        -- 安全检查")
        lines.append("        if not {state_var}_pc then break end")
        lines.append(f"        if {state_var}_pc < 1 or {state_var}_pc > #{code_var} + 1 then")
        lines.append("            break")
        lines.append("        end")
        lines.append("    end")
        lines.append(f"    return {state_var}.return_value")
        lines.append("end")
        lines.append("")

        # Run
        if instructions:
            lines.append(f"local {result_var} = execute({code_var}, {state_var})")
            lines.append(f'if _DEBUG then print("Result: " .. tostring({result_var})) end')

        return "\n".join(lines)


def generate_interpreter_code(
    instructions: list[Instruction] | None = None,
    include_debug: bool = False
) -> str:
    """
    便捷函数：生成完整解释器代码

    Args:
        instructions: 指令列表
        include_debug: 是否包含调试

    Returns:
        Lua 代码字符串
    """
    generator = InterpreterCodeGenerator()
    return generator.generate(instructions, include_debug=include_debug)


def demo_handler_generation():
    """演示 handler 生成"""
    print("=" * 60)
    print("Lua Handler Generation Demo")
    print("=" * 60)

    print("\n[1] Generated Utility Functions:")
    print("-" * 40)
    gen = LuaHandlerGenerator()
    print(gen.generate_utility_functions())

    print("\n[2] Generated All Handlers:")
    print("-" * 40)
    print(gen.generate_all_handlers())

    print("\n[3] Complete Interpreter:")
    print("-" * 40)
    instructions = [
        Instruction(OpCode.INIT, ["x"], None, "10"),
        Instruction(OpCode.INIT, ["y"], None, "20"),
        Instruction(OpCode.ASSIGN, ["sum"], None, "x + y"),
        Instruction(OpCode.RETURN_VAL, ["sum"]),
    ]
    full_gen = InterpreterCodeGenerator()
    print(full_gen.generate(instructions, include_debug=True))

    print("\n" + "=" * 60)
    print("Demo Complete")
    print("=" * 60)


if __name__ == "__main__":
    demo_handler_generation()


def demo_pc_update_optimization():
    """
    演示 PC 更新逻辑分层优化
    """
    print("=" * 60)
    print("PC Update Logic Optimization Demo")
    print("=" * 60)

    print("\n[1] PCUpdate 数据类演示:")
    print("-" * 40)

    # 不同场景的 PC 更新
    continue_update = PCUpdate.continue_at(1)
    print(f"继续执行: {continue_update}")

    jump_update = PCUpdate.jump_to(10)
    print(f"跳转: {jump_update}")

    halt_update = PCUpdate.halt(42)
    print(f"停止: {halt_update}")

    print("\n[2] PCUpdateBuilder 链式构建:")
    print("-" * 40)

    builder = PCOffsetCalculator()
    result = builder.sequential(5, 2)
    print(f"顺序执行: 当前PC=5, 偏移=2, 下一PC={result}")

    result = builder.absolute(20)
    print(f"绝对跳转: 目标PC={result}")

    result = builder.relative(10, -3)
    print(f"相对跳转: 当前PC=10, 偏移=-3, 下一PC={result}")

    result = builder.conditional(True, 15, 6)
    print(f"条件执行 (True): 下一PC={result}")
    result = builder.conditional(False, 15, 6)
    print(f"条件执行 (False): 下一PC={result}")

    print("\n[3] compute_next_pc 函数演示:")
    print("-" * 40)

    # 顺序执行
    result = compute_next_pc(5, 1, {"halt": False})
    print(f"顺序执行: PC=5, raw=1 -> next={result}")

    # 跳转
    result = compute_next_pc(5, 10, {"jump": True, "has_target": True})
    print(f"跳转: PC=5, raw=10 -> next={result}")

    # 停止
    result = compute_next_pc(5, None, {"halt": True})
    print(f"停止: PC=5, halted=True -> next={result}")

    print("\n[4] DispatchState 中间状态演示:")
    print("-" * 40)

    state = DispatchState(pc=5)
    print(f"初始状态: pc={state.pc}, halted={state.halted}")

    state.set_intermediate("loop_count", 1)
    state.set_intermediate("last_op", "add")
    print(f"设置中间状态: {state._intermediate}")

    state.update_from_handler(raw_offset=2)
    print(f"更新 (offset=2): pc={state.pc}")

    state.update_from_handler(target=10, halted=False)
    print(f"更新 (target=10): pc={state.pc}")

    state.update_from_handler(raw_offset=1, halted=True, return_value=42)
    print(f"更新 (halt): pc={state.pc}, halted={state.halted}, return={state.return_value}")

    print("\n[5] UnifiedDispatchCalculator 演示:")
    print("-" * 40)

    calc = UnifiedDispatchCalculator(code_length=100)

    result = calc.calculate(5, 1)
    print(f"正常顺序: PC=5, result=1 -> {result}")

    result = calc.calculate(5, 1, halted=True)
    print(f"停止: halted=True -> {result}")

    result = calc.calculate(5, None, target=20)
    print(f"跳转: target=20 -> {result}")

    result = calc.calculate(95, 10, target=200)  # 超出边界
    print(f"越界: target=200 -> {result}")

    print("\n[6] LayeredExecutorGenerator 生成结果:")
    print("-" * 40)

    gen = LayeredExecutorGenerator(include_bounds_check=True, include_debug=False)
    print(gen.generate_executor_loop())

    print("\n[7] 使用中间状态的执行循环:")
    print("-" * 40)

    gen = LayeredExecutorGenerator()
    print(gen.generate_with_intermediate_state())

    print("\n" + "=" * 60)
    print("Demo Complete")
    print("=" * 60)


if __name__ == "__main__":
    demo_pc_update_optimization()


# ===== 完整 Lua 程序发射器：整合 IR 和执行逻辑 =====


class LuaProgramEmitter:
    """
    完整的 Lua 程序发射器

    将 instruction 数据、handler 定义、执行器逻辑整合为一个
    完整、可独立运行的 Lua 程序。

    支持结构多样性生成，可在保持语义一致的前提下
    生成不同结构的代码。

    输出结构:
    1. instruction 数据表 (local code = {...})
    2. 执行上下文 (local state = {})
    3. handler table (op -> function)
    4. 执行循环 (pc + dispatch)
    """

    def __init__(
        self,
        serializer: InstructionSerializer | None = None,
        handler_generator: LuaHandlerGenerator | None = None,
        include_comments: bool = True,
        include_debug: bool = False,
        diversity_config: DiversityConfig | None = None,
    ):
        self.serializer = serializer or InstructionSerializer(compact=True)
        self.handler_generator = handler_generator or LuaHandlerGenerator(include_comments=include_comments)
        self.include_comments = include_comments
        self.include_debug = include_debug

        # 多样性配置
        self.diversity_config = diversity_config
        self.diversity_enabled = diversity_config is not None and diversity_config.enabled

        # 初始化多样性协调器
        if self.diversity_enabled:
            self.orchestrator = DiversityOrchestrator(diversity_config)
        else:
            self.orchestrator = None

    # ===== Part 1: Instruction Table 生成 =====

    def emit_instruction_table(
        self,
        instructions: list[Instruction],
        var_name: str = "code"
    ) -> str:
        """
        生成 instruction 数据表

        Args:
            instructions: 指令列表
            var_name: 变量名

        Returns:
            Lua 代码字符串
        """
        if not instructions:
            return f"local {var_name} = {{}}"

        lines = []
        lines.append("-- =========================================")
        lines.append("-- Instruction Table")
        lines.append("-- =========================================")

        serialized = self.serializer.serialize(instructions, var_name)
        lines.append(serialized)

        return "\n".join(lines)

    def emit_instruction_table_from_dict(
        self,
        instruction_dict: dict[int, BlockInstructions],
        var_name: str = "code"
    ) -> str:
        """
        从 BlockInstructions 字典生成 instruction 表

        Args:
            instruction_dict: block_id -> BlockInstructions 映射
            var_name: 变量名

        Returns:
            Lua 代码字符串
        """
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Instruction Table (from BlockInstructions)")
        lines.append("-- =========================================")
        lines.append(f"local {var_name} = {{}}")

        idx = 1
        for bid in sorted(instruction_dict.keys()):
            block_instr = instruction_dict[bid]
            if not block_instr.instructions:
                continue

            lines.append(f"-- Block {bid} ({block_instr.block_type})")
            for instr in block_instr.instructions:
                serialized = self.serializer.serialize_single(instr, f"{var_name}[{idx}]")
                lines.append(serialized)
                idx += 1

        return "\n".join(lines)

    # ===== Part 2: Execution State 生成 =====

    def emit_execution_state(self, var_name: str = "state") -> str:
        """
        生成执行上下文

        Args:
            var_name: 状态变量名

        Returns:
            Lua 代码字符串
        """
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Execution State")
        lines.append("-- =========================================")
        lines.append(f"local {var_name} = {{")
        lines.append("    locals = {},")
        lines.append("    globals = {},")
        lines.append("    stack = {},")
        lines.append("    pc = 1,")
        lines.append("    halted = false,")
        lines.append("    return_value = nil,")
        lines.append("}")

        return "\n".join(lines)

    # ===== Part 3: Handler Table 生成 =====

    def emit_handler_table(self) -> str:
        """
        生成 handler table

        Returns:
            Lua 代码字符串
        """
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Handler Table")
        lines.append("-- =========================================")

        # Utility functions (使用协调器生成多样版本)
        if self.orchestrator and self.orchestrator.should_diversify():
            lines.append(self.orchestrator.generate_utility_functions())
        else:
            lines.append(self.handler_generator.generate_utility_functions())
        lines.append("")

        # Handler table
        lines.append("local handlers = {")

        for opcode in sorted(self.handler_generator.HANDLER_TEMPLATES.keys()):
            template = self.handler_generator.HANDLER_TEMPLATES[opcode]
            if self.include_comments:
                lines.append(f"    -- opcode: {opcode} ({template['desc']})")
            lines.append(f"    {template['template'].strip()},")

        # Default handler
        lines.append("")
        lines.append("    -- Default handler for unknown opcodes")
        lines.append("    default = function(instr, state, pc)")
        lines.append("        if _DEBUG then")
        lines.append("            print('Unknown opcode: ' .. tostring(instr[1]))")
        lines.append("        end")
        lines.append("        return pc + 1")
        lines.append("    end,")

        lines.append("}")

        return "\n".join(lines)

    def emit_dispatcher(self) -> str:
        """
        生成 dispatcher 函数

        Returns:
            Lua 代码字符串
        """
        # 使用协调器生成多样版本
        if self.orchestrator and self.orchestrator.should_diversify():
            return self.orchestrator.generate_dispatcher()

        lines = []
        lines.append("-- =========================================")
        lines.append("-- Dispatcher")
        lines.append("-- =========================================")
        lines.append("")
        lines.append("local function dispatch(instr, state, pc)")
        lines.append("    local op = instr[1]")
        lines.append("    local handler = handlers[op] or handlers.default")
        lines.append("    return handler(instr, state, pc)")
        lines.append("end")

        return "\n".join(lines)

    def emit_handler_module(self) -> str:
        """
        生成完整的 handler 模块

        Returns:
            Lua 代码字符串
        """
        parts = []
        parts.append(self.emit_handler_table())
        parts.append("")
        parts.append(self.emit_dispatcher())
        return "\n\n".join(parts)

    # ===== Part 4: Executor Loop 生成 =====

    def emit_executor_loop(
        self,
        code_var: str = "code",
        state_var: str = "state",
        function_name: str = "execute"
    ) -> str:
        """
        生成执行循环

        Args:
            code_var: 代码变量名
            state_var: 状态变量名
            function_name: 函数名

        Returns:
            Lua 代码字符串
        """
        # 使用协调器生成多样版本
        if self.orchestrator and self.orchestrator.should_diversify():
            return self.orchestrator.generate_executor_loop(code_var, state_var, function_name)

        lines = []
        lines.append("-- =========================================")
        lines.append("-- Executor Loop")
        lines.append("-- =========================================")
        lines.append("")
        lines.append(f"local function {function_name}({code_var}, {state_var})")
        lines.append(f"    local pc = 1")
        lines.append(f"    while pc and not {state_var}.halted do")
        lines.append(f"        local instr = {code_var}[pc]")
        lines.append("        if not instr then break end")
        lines.append(f"        pc = dispatch(instr, {state_var}, pc)")
        lines.append("        -- Safety check")
        lines.append("        if not pc then break end")
        lines.append(f"        if pc < 1 or pc > #{code_var} + 1 then")
        lines.append("            break")
        lines.append("        end")
        lines.append("    end")
        lines.append(f"    return {state_var}.return_value")
        lines.append("end")

        return "\n".join(lines)

    def emit_runner(
        self,
        code_var: str = "code",
        state_var: str = "state",
        result_var: str = "_result",
        execute_func: str = "execute"
    ) -> str:
        """
        生成运行代码

        Args:
            code_var: 代码变量名
            state_var: 状态变量名
            result_var: 结果变量名
            execute_func: 执行函数名

        Returns:
            Lua 代码字符串
        """
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Run")
        lines.append("-- =========================================")
        lines.append("")
        lines.append(f"local {result_var} = {execute_func}({code_var}, {state_var})")

        if self.include_debug:
            lines.append(f'if _DEBUG then print("Result: " .. tostring({result_var})) end')

        return "\n".join(lines)

    # ===== Part 5: 完整程序生成 =====

    def emit_complete_program(
        self,
        instructions: list[Instruction] | None = None,
        code_var: str = "code",
        state_var: str = "state",
        result_var: str = "_result",
        execute_func: str = "execute"
    ) -> str:
        """
        生成完整的 Lua 程序

        按顺序输出:
        1. instruction 数据表
        2. 执行上下文
        3. handler table
        4. dispatcher
        5. 执行循环
        6. 运行代码

        Args:
            instructions: 指令列表
            code_var: 代码变量名
            state_var: 状态变量名
            result_var: 结果变量名
            execute_func: 执行函数名

        Returns:
            完整的 Lua 程序字符串
        """
        parts = []

        # Header
        header = []
        header.append("-- =========================================")
        header.append("-- Lua Instruction Interpreter Program")
        header.append("-- Generated by lua_obfuscator")
        header.append("-- =========================================")
        header.append("")
        header.append(f"local _DEBUG = {'true' if self.include_debug else 'false'}")
        parts.append("\n".join(header))

        # Part 1: Instruction Table
        if instructions:
            parts.append(self.emit_instruction_table(instructions, code_var))

        # Part 2: Execution State
        parts.append(self.emit_execution_state(state_var))

        # Part 3: Handler Module
        parts.append(self.emit_handler_module())

        # Part 4: Executor Loop
        parts.append(self.emit_executor_loop(code_var, state_var, execute_func))

        # Part 5: Runner
        if instructions:
            parts.append(self.emit_runner(code_var, state_var, result_var, execute_func))

        return "\n\n".join(parts)

    def emit_program_from_pipeline_state(
        self,
        state: PipelineState,
        code_var: str = "code",
        state_var: str = "state",
        result_var: str = "_result",
        execute_func: str = "execute"
    ) -> str:
        """
        从 PipelineState 生成完整程序

        使用已处理好的指令数据

        Args:
            state: PipelineState 实例
            code_var: 代码变量名
            state_var: 状态变量名
            result_var: 结果变量名
            execute_func: 执行函数名

        Returns:
            完整的 Lua 程序字符串
        """
        parts = []

        # Header
        header = []
        header.append("-- =========================================")
        header.append("-- Lua Instruction Interpreter Program")
        header.append("-- Generated by lua_obfuscator (Pipeline Mode)")
        header.append("-- =========================================")
        header.append("")
        header.append(f"local _DEBUG = {'true' if self.include_debug else 'false'}")
        parts.append("\n".join(header))

        # Part 1: Instruction Table (from state.instructions)
        if state.instructions:
            parts.append(self.emit_instruction_table_from_dict(state.instructions, code_var))

        # Part 2: Execution State
        parts.append(self.emit_execution_state(state_var))

        # Part 3: Handler Module
        parts.append(self.emit_handler_module())

        # Part 4: Executor Loop
        parts.append(self.emit_executor_loop(code_var, state_var, execute_func))

        # Part 5: Runner
        if state.instructions:
            parts.append(self.emit_runner(code_var, state_var, result_var, execute_func))

        return "\n\n".join(parts)

    # ===== Part 5.5: Runtime Consistency Checks =====

    def emit_consistency_check_module(
        self,
        code_var: str = "code",
        state_var: str = "state",
        handlers_var: str = "handlers",
        pool_var: str | None = None,
        check_on_start: bool = True,
        check_on_execute: bool = True,
        check_interval: int = 50
    ) -> str:
        """
        生成运行时一致性检查模块（轻量级）

        不依赖外部库，仅使用 Lua 内置功能进行校验。

        Args:
            code_var: 代码表变量名
            state_var: 状态变量名
            handlers_var: handlers 表变量名
            pool_var: 常量池变量名（可选）
            check_on_start: 启动时检查
            check_on_execute: 执行时检查
            check_interval: 检查间隔

        Returns:
            Lua 代码字符串
        """
        lines = []

        lines.append("-- =========================================")
        lines.append("-- Runtime Consistency Check Module")
        lines.append("-- =========================================")
        lines.append("")

        # 检查配置
        lines.append("-- Consistency check configuration")
        lines.append(f"local _CHK_ENABLED = true")
        lines.append(f"local _CHK_START = {str(check_on_start).lower()}")
        lines.append(f"local _CHK_EXEC = {str(check_on_execute).lower()}")
        lines.append(f"local _CHK_INTERVAL = {check_interval}")
        lines.append("local _CHK_COUNTER = 0")
        lines.append("")

        # 简单校验和计算
        lines.append("-- Simple checksum calculation (no external libs)")
        lines.append("local function _chk_compute(data)")
        lines.append("    if type(data) ~= 'table' then return 0 end")
        lines.append("    local sum = 0")
        lines.append("    for i = 1, #data do")
        lines.append("        local item = data[i]")
        lines.append("        if type(item) == 'table' then")
        lines.append("            for j = 1, #item do")
        lines.append("                sum = ((sum + j) ~ (item[j] or 0)) & 0xFFFFFFFF")
        lines.append("            end")
        lines.append("        end")
        lines.append("    end")
        lines.append("    return sum")
        lines.append("end")
        lines.append("")

        # Handlers 校验和
        lines.append("-- Handlers checksum calculation")
        lines.append("local function _chk_handlers(tbl)")
        lines.append("    if type(tbl) ~= 'table' then return 0 end")
        lines.append("    local sum = 0")
        lines.append("    local count = 0")
        lines.append("    for k, v in pairs(tbl) do")
        lines.append("        count = count + 1")
        lines.append("        local kh = type(k) == 'number' and k or 0")
        lines.append("        sum = ((sum + kh) ~ (count * 31)) & 0xFFFFFFFF")
        lines.append("    end")
        lines.append("    return sum")
        lines.append("end")
        lines.append("")

        # 常量池校验和（如果提供）
        if pool_var:
            lines.append("-- Constant pool checksum calculation")
            lines.append(f"local function _chk_pool(p)")
            lines.append("    if type(p) ~= 'table' then return 0 end")
            lines.append("    local sum = 0")
            lines.append("    for i = 1, #p do")
            lines.append("        local item = p[i]")
            lines.append("        if type(item) == 'string' then")
            lines.append("            for j = 1, #item do")
            lines.append("                sum = ((sum + string.byte(item, j)) * 33) & 0xFFFFFFFF")
            lines.append("            end")
            lines.append("        elseif type(item) == 'number' then")
            lines.append("            sum = ((sum + item) * 33) & 0xFFFFFFFF")
            lines.append("        end")
            lines.append("    end")
            lines.append("    return sum")
            lines.append("end")
            lines.append("")

        # 存储预期值
        lines.append("-- Expected check values")
        lines.append("local _CHK_EXPECTED = {")
        lines.append(f"    code = _chk_compute({code_var}),")
        lines.append(f"    handlers = _chk_handlers({handlers_var}),")
        if pool_var:
            lines.append(f"    pool = _chk_pool({pool_var}),")
        lines.append("    code_len = #" + code_var + ",")
        lines.append("    handlers_count = 0,")
        lines.append("}")
        lines.append("")

        # 计算 handlers 数量
        lines.append("-- Count handlers")
        lines.append("local _tmp_count = 0")
        lines.append(f"for _ in pairs({handlers_var}) do _tmp_count = _tmp_count + 1 end")
        lines.append("_CHK_EXPECTED.handlers_count = _tmp_count")
        lines.append("")

        # 主检查函数
        lines.append("-- Main consistency check function")
        lines.append("local function _chk_validate()")
        lines.append("    if not _CHK_ENABLED then return true, 'checks disabled' end")
        lines.append("")
        lines.append("    -- Check code table length")
        lines.append(f"    if #{code_var} ~= _CHK_EXPECTED.code_len then")
        lines.append("        return false, 'code length changed: ' .. #{code_var} .. ' vs ' .. _CHK_EXPECTED.code_len")
        lines.append("    end")
        lines.append("")
        lines.append("    -- Check code table checksum")
        lines.append(f"    local code_sum = _chk_compute({code_var})")
        lines.append("    if code_sum ~= _CHK_EXPECTED.code then")
        lines.append("        return false, 'code checksum mismatch'")
        lines.append("    end")
        lines.append("")
        lines.append("    -- Check handlers table")
        lines.append(f"    local h_count = 0")
        lines.append(f"    for _ in pairs({handlers_var}) do h_count = h_count + 1 end")
        lines.append("    if h_count ~= _CHK_EXPECTED.handlers_count then")
        lines.append("        return false, 'handlers count changed'")
        lines.append("    end")
        lines.append(f"    local h_sum = _chk_handlers({handlers_var})")
        lines.append("    if h_sum ~= _CHK_EXPECTED.handlers then")
        lines.append("        return false, 'handlers checksum mismatch'")
        lines.append("    end")

        if pool_var:
            lines.append("")
            lines.append("    -- Check constant pool")
            lines.append(f"    local p_sum = _chk_pool({pool_var})")
            lines.append("    if p_sum ~= _CHK_EXPECTED.pool then")
            lines.append("        return false, 'pool checksum mismatch'")
            lines.append("    end")

        lines.append("")
        lines.append("    return true, 'ok'")
        lines.append("end")
        lines.append("")

        # 运行时检查点
        lines.append("-- Runtime checkpoint function")
        lines.append("local function _chk_checkpoint()")
        lines.append("    _CHK_COUNTER = _CHK_COUNTER + 1")
        lines.append("    if _CHK_COUNTER % _CHK_INTERVAL ~= 0 then return true end")
        lines.append("    local ok, err = _chk_validate()")
        lines.append("    if not ok then")
        lines.append("        if _DEBUG then print('[CHK FAIL] ' .. tostring(err)) end")
        lines.append("        error('[Runtime Check Failed] ' .. tostring(err))")
        lines.append("        return false")
        lines.append("    end")
        lines.append("    return true")
        lines.append("end")
        lines.append("")

        # 启动时检查
        if check_on_start:
            lines.append("-- Initial check at startup")
            lines.append("local _chk_ok, _chk_msg = _chk_validate()")
            lines.append("if not _chk_ok then")
            lines.append("    error('[Initial Check Failed] ' .. tostring(_chk_msg))")
            lines.append("end")
            lines.append("")

        return "\n".join(lines)

    def emit_consistency_guards(
        self,
        code_var: str = "code",
        state_var: str = "state"
    ) -> str:
        """
        生成嵌入式一致性守卫（分散在代码中）

        用于在执行循环中插入轻量级检查

        Args:
            code_var: 代码变量名
            state_var: 状态变量名

        Returns:
            Lua 代码字符串
        """
        lines = []

        lines.append("-- Embedded consistency guards")
        lines.append("")

        # 检查 state 是否有效
        lines.append("local function _chk_state(s)")
        lines.append("    if type(s) ~= 'table' then return false end")
        lines.append("    if s.halted == nil then return false end")
        lines.append("    return true")
        lines.append("end")
        lines.append("")

        # 检查指令格式
        lines.append("local function _chk_instr(instr)")
        lines.append("    if type(instr) ~= 'table' then return false end")
        lines.append("    if type(instr[1]) ~= 'number' then return false end")
        lines.append("    return true")
        lines.append("end")
        lines.append("")

        # 检查 PC 范围
        lines.append("local function _chk_pc(pc, max_pc)")
        lines.append("    if type(pc) ~= 'number' then return false end")
        lines.append("    if pc < 1 or pc > max_pc + 1 then return false end")
        lines.append("    return true")
        lines.append("end")
        lines.append("")

        return "\n".join(lines)

    def emit_executor_with_consistency(
        self,
        code_var: str = "code",
        state_var: str = "state",
        function_name: str = "execute",
        include_guards: bool = True,
        check_interval: int = 50
    ) -> str:
        """
        生成带一致性检查的执行循环

        Args:
            code_var: 代码变量名
            state_var: 状态变量名
            function_name: 函数名
            include_guards: 是否包含守卫检查
            check_interval: 检查间隔

        Returns:
            Lua 代码字符串
        """
        lines = []

        lines.append("-- =========================================")
        lines.append("-- Executor with Consistency Checks")
        lines.append("-- =========================================")
        lines.append("")

        # 包含守卫函数
        lines.append(self.emit_consistency_guards(code_var, state_var))
        lines.append("")

        # 主执行函数
        lines.append(f"local function {function_name}({code_var}, {state_var})")
        lines.append("    -- Validate initial state")
        lines.append("    if not _chk_state(state) then")
        lines.append("        error('[Invalid State] state table corrupted')")
        lines.append("    end")
        lines.append("")
        lines.append("    local pc = 1")
        lines.append(f"    while pc and not {state_var}.halted do")
        lines.append(f"        local instr = {code_var}[pc]")
        lines.append("")
        lines.append("        -- Validate instruction")
        lines.append("        if not _chk_instr(instr) then")
        lines.append("            error('[Invalid Instruction] at pc=' .. tostring(pc))")
        lines.append("        end")
        lines.append("")
        lines.append("        -- Runtime checkpoint")
        lines.append("        _chk_checkpoint()")
        lines.append("")
        lines.append("        -- Execute handler")
        lines.append("        local op = instr[1]")
        lines.append("        local handler = handlers[op] or handlers.default")
        lines.append(f"        pc = handler(instr, {state_var}, pc)")
        lines.append("")
        lines.append("        -- Validate PC after execution")
        lines.append("        if pc and not _chk_pc(pc, #code) then")
        lines.append("            error('[Invalid PC] pc=' .. tostring(pc))")
        lines.append("        end")
        lines.append("")
        lines.append("        -- Validate state after execution")
        lines.append("        if not _chk_state(state) then")
        lines.append("            error('[State Corrupted] after pc=' .. tostring(pc))")
        lines.append("        end")
        lines.append("    end")
        lines.append("")
        lines.append(f"    return {state_var}.return_value")
        lines.append("end")

        return "\n".join(lines)

    # ===== Part 6: Runtime Integrity Validation =====

    def emit_integrity_module(
        self,
        code_var: str = "code",
        state_var: str = "state",
        check_interval: int = 100
    ) -> str:
        """
        生成运行时完整性校验模块

        用于检测代码结构和关键数据是否被意外修改

        Args:
            code_var: 代码变量名
            state_var: 状态变量名
            check_interval: 重复校验间隔（执行多少次指令后检查一次）

        Returns:
            Lua 代码字符串
        """
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Runtime Integrity Validation Module")
        lines.append("-- =========================================")

        # 校验种子值（在生成时嵌入）
        integrity_seed = self._generate_integrity_seed()
        lines.append("")
        lines.append("-- Integrity check seed (do not modify)")
        lines.append(f"local _INT_SEED = {integrity_seed}")
        lines.append(f"local _INT_CHECK_INTERVAL = {check_interval}")
        lines.append("local _INT_EXEC_COUNTER = 0")
        lines.append("")

        # 简单哈希函数（基于 XOR 和移位）
        lines.append("-- Simple hash function for integrity checks")
        lines.append("local function _int_hash(data)")
        lines.append("    if type(data) == 'table' then")
        lines.append("        local h = _INT_SEED")
        lines.append("        for _, v in pairs(data) do")
        lines.append("            local vh = _int_hash(v)")
        lines.append("            h = ((h << 5) | (h >> 27)) ~ vh")
        lines.append("        end")
        lines.append("        return h")
        lines.append("    elseif type(data) == 'string' then")
        lines.append("        local h = _INT_SEED")
        lines.append("        for i = 1, #data do")
        lines.append("            h = ((h << 5) | (h >> 27)) ~ string.byte(data, i)")
        lines.append("        end")
        lines.append("        return h")
        lines.append("    elseif type(data) == 'number' then")
        lines.append("        return (data * 0x9e3779b9) ~ _INT_SEED")
        lines.append("    else")
        lines.append("        return _INT_SEED")
        lines.append("    end")
        lines.append("end")
        lines.append("")

        # 计算表结构的签名
        lines.append("-- Calculate structural signature for a table")
        lines.append("local function _int_table_signature(tbl)")
        lines.append("    if type(tbl) ~= 'table' then return 0 end")
        lines.append("    local sig = 0")
        lines.append("    -- Hash by key-value pair count and types")
        lines.append("    local keys = {}")
        lines.append("    for k, _ in pairs(tbl) do table.insert(keys, k) end")
        lines.append("    table.sort(keys)")
        lines.append("    for _, k in ipairs(keys) do")
        lines.append("        local v = tbl[k]")
        lines.append("        local kh = _int_hash(k)")
        lines.append("        local vh = _int_hash(v)")
        lines.append("        sig = sig ~ ((kh * 31) + vh)")
        lines.append("    end")
        lines.append("    return sig")
        lines.append("end")
        lines.append("")

        # 存储预期的校验值
        lines.append("-- Expected integrity values (set at generation time)")
        lines.append("local _INT_EXPECTED = {")
        lines.append("    code_len = 0,")
        lines.append("    code_sig = 0,")
        lines.append("    handlers_sig = 0,")
        lines.append("}")
        lines.append("")

        # 主校验函数
        lines.append("-- Main integrity validation function")
        lines.append("local function _int_validate()")
        lines.append("    -- Check code table integrity")
        lines.append("    local code_len = #" + code_var)
        lines.append("    if code_len ~= _INT_EXPECTED.code_len then")
        lines.append("        return false, 'code length mismatch: expected ' .. _INT_EXPECTED.code_len .. ', got ' .. code_len")
        lines.append("    end")
        lines.append("")
        lines.append("    local code_sig = _int_table_signature(" + code_var + ")")
        lines.append("    if code_sig ~= _INT_EXPECTED.code_sig then")
        lines.append("        return false, 'code signature mismatch'")
        lines.append("    end")
        lines.append("")
        lines.append("    -- Check handlers table integrity")
        lines.append("    local handlers_sig = _int_table_signature(handlers)")
        lines.append("    if handlers_sig ~= _INT_EXPECTED.handlers_sig then")
        lines.append("        return false, 'handlers signature mismatch'")
        lines.append("    end")
        lines.append("")
        lines.append("    return true")
        lines.append("end")
        lines.append("")

        # 初始化校验值
        lines.append("-- Initialize integrity expected values")
        lines.append("local function _int_init()")
        lines.append("    _INT_EXPECTED.code_len = #" + code_var)
        lines.append("    _INT_EXPECTED.code_sig = _int_table_signature(" + code_var + ")")
        lines.append("    _INT_EXPECTED.handlers_sig = _int_table_signature(handlers)")
        lines.append("end")
        lines.append("")

        # 检查函数（可在循环中调用）
        lines.append("-- Periodic integrity check")
        lines.append("local function _int_check()")
        lines.append("    _INT_EXEC_COUNTER = _INT_EXEC_COUNTER + 1")
        lines.append("    if _INT_EXEC_COUNTER % _INT_CHECK_INTERVAL == 0 then")
        lines.append("        local ok, err = _int_validate()")
        lines.append("        if not ok then")
        lines.append("            error('[Integrity Check Failed] ' .. tostring(err))")
        lines.append("        end")
        lines.append("    end")
        lines.append("end")
        lines.append("")

        # 重置计数器
        lines.append("-- Reset execution counter")
        lines.append("local function _int_reset()")
        lines.append("    _INT_EXEC_COUNTER = 0")
        lines.append("end")

        return "\n".join(lines)

    def _generate_integrity_seed(self) -> int:
        """生成校验种子值"""
        import time
        seed = int(time.time() * 1000) % 0xFFFFFFFF
        return seed

    def emit_integrity_validation_call(self) -> str:
        """
        生成初始化校验的调用代码

        Returns:
            Lua 代码字符串
        """
        return "_int_init()"

    def emit_integrity_check_call(self) -> str:
        """
        生成循环中校验调用的代码片段

        Returns:
            Lua 代码字符串
        """
        return "_int_check()"

    def emit_integrity_guard(
        self,
        code_var: str = "code",
        state_var: str = "state",
        check_interval: int = 100
    ) -> str:
        """
        生成完整的完整性保护模块（包含初始化和检查调用）

        Args:
            code_var: 代码变量名
            state_var: 状态变量名
            check_interval: 检查间隔

        Returns:
            Lua 代码字符串
        """
        parts = []
        parts.append(self.emit_integrity_module(code_var, state_var, check_interval))
        parts.append("")
        parts.append("-- Initialize integrity checks at startup")
        parts.append(self.emit_integrity_validation_call())
        return "\n\n".join(parts)

    # ===== Part 7: Integrated Executor with Integrity Checks =====

    def emit_integrated_executor(
        self,
        code_var: str = "code",
        state_var: str = "state",
        function_name: str = "execute",
        enable_periodic_check: bool = True,
        check_interval: int = 100
    ) -> str:
        """
        生成带完整性校验的执行循环

        Args:
            code_var: 代码变量名
            state_var: 状态变量名
            function_name: 函数名
            enable_periodic_check: 是否启用周期性检查
            check_interval: 检查间隔

        Returns:
            Lua 代码字符串
        """
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Executor Loop (with Integrity Checks)")
        lines.append("-- =========================================")
        lines.append("")
        lines.append(f"local function {function_name}({code_var}, {state_var})")

        if enable_periodic_check:
            lines.append("    -- Initialize integrity values")
            lines.append("    _int_init()")
            lines.append("    _int_reset()")
            lines.append("")

        lines.append(f"    local pc = 1")
        lines.append(f"    while pc and not {state_var}.halted do")
        lines.append(f"        local instr = {code_var}[pc]")
        lines.append("        if not instr then break end")

        if enable_periodic_check:
            lines.append(f"        -- Integrity check during execution")
            lines.append(f"        _int_check()")

        lines.append(f"        pc = dispatch(instr, {state_var}, pc)")
        lines.append("        -- Safety check")
        lines.append("        if not pc then break end")
        lines.append(f"        if pc < 1 or pc > #{code_var} + 1 then")
        lines.append("            break")
        lines.append("        end")
        lines.append("    end")
        lines.append(f"    return {state_var}.return_value")
        lines.append("end")

        return "\n".join(lines)

    def emit_complete_program_with_integrity(
        self,
        instructions: list[Instruction] | None = None,
        code_var: str = "code",
        state_var: str = "state",
        result_var: str = "_result",
        execute_func: str = "execute",
        enable_periodic_check: bool = True,
        check_interval: int = 100
    ) -> str:
        """
        生成带完整性校验的完整 Lua 程序

        Args:
            instructions: 指令列表
            code_var: 代码变量名
            state_var: 状态变量名
            result_var: 结果变量名
            execute_func: 执行函数名
            enable_periodic_check: 是否启用周期性检查
            check_interval: 检查间隔

        Returns:
            完整的 Lua 程序字符串
        """
        parts = []

        # Header
        header = []
        header.append("-- =========================================")
        header.append("-- Lua Instruction Interpreter Program")
        header.append("-- (with Runtime Integrity Validation)")
        header.append("-- Generated by lua_obfuscator")
        header.append("-- =========================================")
        header.append("")
        header.append(f"local _DEBUG = {'true' if self.include_debug else 'false'}")
        header.append(f"local _INTEGRITY_ENABLED = true")
        parts.append("\n".join(header))

        # Part 1: Instruction Table
        if instructions:
            parts.append(self.emit_instruction_table(instructions, code_var))

        # Part 2: Execution State
        parts.append(self.emit_execution_state(state_var))

        # Part 3: Handler Module
        parts.append(self.emit_handler_module())

        # Part 4: Integrity Module (NEW)
        parts.append(self.emit_integrity_module(code_var, state_var, check_interval))

        # Part 5: Executor Loop with Integrity Checks
        parts.append(self.emit_integrated_executor(
            code_var, state_var, execute_func,
            enable_periodic_check, check_interval
        ))

        # Part 6: Runner
        if instructions:
            parts.append(self.emit_runner(code_var, state_var, result_var, execute_func))

        return "\n\n".join(parts)


def emit_lua_program(
    instructions: list[Instruction] | None = None,
    code_var: str = "code",
    state_var: str = "state",
    result_var: str = "_result",
    include_debug: bool = False,
    serializer: InstructionSerializer | None = None,
    handler_generator: LuaHandlerGenerator | None = None,
) -> str:
    """
    便捷函数：发射完整的 Lua 程序

    Args:
        instructions: 指令列表
        code_var: 代码变量名
        state_var: 状态变量名
        result_var: 结果变量名
        include_debug: 是否包含调试信息
        serializer: 自定义序列化器
        handler_generator: 自定义 handler 生成器

    Returns:
        完整的 Lua 程序字符串
    """
    emitter = LuaProgramEmitter(
        serializer=serializer,
        handler_generator=handler_generator,
        include_debug=include_debug,
    )
    return emitter.emit_complete_program(
        instructions=instructions,
        code_var=code_var,
        state_var=state_var,
        result_var=result_var,
    )


def emit_lua_program_from_state(
    state: PipelineState,
    code_var: str = "code",
    state_var: str = "state",
    result_var: str = "_result",
    include_debug: bool = False,
) -> str:
    """
    便捷函数：从 PipelineState 发射完整的 Lua 程序

    Args:
        state: PipelineState 实例
        code_var: 代码变量名
        state_var: 状态变量名
        result_var: 结果变量名
        include_debug: 是否包含调试信息

    Returns:
        完整的 Lua 程序字符串
    """
    emitter = LuaProgramEmitter(include_debug=include_debug)
    return emitter.emit_program_from_pipeline_state(
        state=state,
        code_var=code_var,
        state_var=state_var,
        result_var=result_var,
    )


def emit_lua_program_with_integrity(
    instructions: list[Instruction] | None = None,
    code_var: str = "code",
    state_var: str = "state",
    result_var: str = "_result",
    include_debug: bool = False,
    enable_periodic_check: bool = True,
    check_interval: int = 100,
    serializer: InstructionSerializer | None = None,
    handler_generator: LuaHandlerGenerator | None = None,
) -> str:
    """
    便捷函数：发射带运行时完整性校验的完整 Lua 程序

    Args:
        instructions: 指令列表
        code_var: 代码变量名
        state_var: 状态变量名
        result_var: 结果变量名
        include_debug: 是否包含调试信息
        enable_periodic_check: 是否启用周期性完整性检查
        check_interval: 周期性检查间隔（执行多少次指令后检查一次）
        serializer: 自定义序列化器
        handler_generator: 自定义 handler 生成器

    Returns:
        完整的 Lua 程序字符串（包含完整性校验模块）
    """
    emitter = LuaProgramEmitter(
        serializer=serializer,
        handler_generator=handler_generator,
        include_debug=include_debug,
    )
    return emitter.emit_complete_program_with_integrity(
        instructions=instructions,
        code_var=code_var,
        state_var=state_var,
        result_var=result_var,
        enable_periodic_check=enable_periodic_check,
        check_interval=check_interval,
    )


def emit_integrity_module_only(
    code_var: str = "code",
    state_var: str = "state",
    check_interval: int = 100,
) -> str:
    """
    便捷函数：仅生成完整性校验模块代码

    可用于将完整性校验集成到现有的 Lua 程序中

    Args:
        code_var: 代码变量名
        state_var: 状态变量名
        check_interval: 检查间隔

    Returns:
        完整性校验模块的 Lua 代码
    """
    emitter = LuaProgramEmitter()
    return emitter.emit_integrity_module(code_var, state_var, check_interval)


def emit_diverse_lua_program(
    instructions: list[Instruction] | None = None,
    code_var: str = "code",
    state_var: str = "state",
    result_var: str = "_result",
    include_debug: bool = False,
    diversity_level: float = 0.5,
    seed: int | None = None,
    serializer: InstructionSerializer | None = None,
    handler_generator: LuaHandlerGenerator | None = None,
) -> str:
    """
    便捷函数：发射具有结构多样性的完整 Lua 程序

    每次调用（不同 seed）会生成结构不同但语义一致的代码

    Args:
        instructions: 指令列表
        code_var: 代码变量名
        state_var: 状态变量名
        result_var: 结果变量名
        include_debug: 是否包含调试信息
        diversity_level: 多样性程度 (0.0 ~ 1.0)，越高变化越多
        seed: 随机种子，为 None 则使用时间种子
        serializer: 自定义序列化器
        handler_generator: 自定义 handler 生成器

    Returns:
        完整的 Lua 程序字符串（具有结构多样性）
    """
    import time as time_module

    # 创建多样性配置
    rng = random.Random(seed if seed is not None else int(time_module.time() * 1000) % 1000000)
    diversity_config = DiversityConfig(
        enabled=True,
        diversity_level=diversity_level,
        rng=rng,
    )

    emitter = LuaProgramEmitter(
        serializer=serializer,
        handler_generator=handler_generator,
        include_debug=include_debug,
        diversity_config=diversity_config,
    )
    return emitter.emit_complete_program(
        instructions=instructions,
        code_var=code_var,
        state_var=state_var,
        result_var=result_var,
    )


def create_diversity_config(
    enabled: bool = True,
    diversity_level: float = 0.5,
    handler_strategy: str = "random",
    utility_strategy: str = "random",
    naming_strategy: str = "random",
    serialization_strategy: str = "random",
    seed: int | None = None,
) -> DiversityConfig:
    """
    创建多样性配置

    Args:
        enabled: 是否启用多样性
        diversity_level: 多样性程度 (0.0 ~ 1.0)
        handler_strategy: handler 策略 ("random", "compact", "verbose")
        utility_strategy: 工具函数策略 ("random", "compact", "verbose")
        naming_strategy: 命名策略 ("random", "default", "obfuscated", "mixed")
        serialization_strategy: 序列化策略 ("random", "compact", "expanded", "named")
        seed: 随机种子

    Returns:
        DiversityConfig 实例
    """
    import time as time_module

    rng = random.Random(seed if seed is not None else int(time_module.time() * 1000) % 1000000)
    return DiversityConfig(
        enabled=enabled,
        diversity_level=diversity_level,
        handler_strategy=handler_strategy,
        utility_strategy=utility_strategy,
        naming_strategy=naming_strategy,
        serialization_strategy=serialization_strategy,
        rng=rng,
    )


# ===== 修改 transform_v3 使用常量池发射器 =====

def transform_v3(source: str, watermark: str, use_constant_pool: bool = True) -> str:
    """
    使用完整 Lua 程序发射器的新版本 transform 函数

    将 instruction 数据、handler 定义、执行器逻辑整合为
    一个完整、可独立运行的 Lua 程序，并支持字符串常量池。

    Args:
        source: 源代码
        watermark: 水印
        use_constant_pool: 是否使用字符串常量池

    Returns:
        混淆后的 Lua 代码
    """
    source = strip_leading_bom(source)
    random.seed(int(time.time()))
    rng = create_time_seeded_random()
    profile = ProtectionProfile(rng, watermark)

    randomize_algorithms(profile, rng)
    shuffle_tables(profile, rng)

    # 执行 Pipeline
    state = execute_pipeline(source, profile, rng)

    # 选择发射器
    if use_constant_pool:
        emitter = EnhancedLuaProgramEmitter(
            use_constant_pool=True,
            encoding_strategy="xor_shift",
            include_debug=False,
        )
        full_program = emitter.emit_complete_program_with_pool(
            instructions=None,
            tokens=state.tokens,
            source=source,
        )
    else:
        emitter = LuaProgramEmitter(include_debug=False)
        full_program = emitter.emit_program_from_pipeline_state(state)

    # 添加 API 前导码
    api_plan = apply_api_indirection(state.tokens, profile, rng)

    # 组装最终代码
    return (
        "--[[\n"
        + "Lua Protector Watermark: "
        + sanitize_comment(watermark)
        + "\nGenerated by LuaProgramEmitter\n"
        + "Architecture: instruction_table + handler + executor\n"
        + ("Features: constant_pool + runtime_decode\n" if use_constant_pool else "")
        + "]]\n"
        + build_runtime_prelude(profile)
        + api_plan.prelude
        + "\n"
        + full_program
        + "\n"
    )


def transform_v4(source: str, watermark: str) -> str:
    """
    最新版本的 transform 函数

    使用常量池和增强的发射器。

    Args:
        source: 源代码
        watermark: 水印

    Returns:
        混淆后的 Lua 代码
    """
    return transform_v3(source, watermark, use_constant_pool=True)


# 更新主入口为 v4
def transform(source: str, watermark: str) -> str:
    """
    主入口函数，使用增强的 Lua 程序发射器

    Args:
        source: 源代码
        watermark: 水印

    Returns:
        混淆后的 Lua 代码
    """
    return transform_v4(source, watermark)


def demo_lua_program_emitter():
    """演示 Lua 程序发射器"""
    print("=" * 60)
    print("Lua Program Emitter Demo")
    print("=" * 60)

    # 创建示例指令
    instructions = [
        Instruction(OpCode.INIT, ["x"], None, "10"),
        Instruction(OpCode.INIT, ["y"], None, "20"),
        Instruction(OpCode.ASSIGN, ["sum"], None, "x + y"),
        Instruction(OpCode.RETURN_VAL, ["sum"]),
    ]

    # 创建发射器
    emitter = LuaProgramEmitter(include_debug=True)

    print("\n[1] Instruction Table:")
    print("-" * 40)
    print(emitter.emit_instruction_table(instructions))

    print("\n[2] Execution State:")
    print("-" * 40)
    print(emitter.emit_execution_state())

    print("\n[3] Handler Module:")
    print("-" * 40)
    print(emitter.emit_handler_module())

    print("\n[4] Executor Loop:")
    print("-" * 40)
    print(emitter.emit_executor_loop())

    print("\n[5] Complete Program:")
    print("-" * 40)
    print(emitter.emit_complete_program(instructions))

    print("\n" + "=" * 60)
    print("Demo Complete")
    print("=" * 60)


if __name__ == "__main__":
    demo_lua_program_emitter()


# ===== 字符串常量池与运行时解码系统 =====


import base64
import hashlib
from typing import Callable


class EncodingStrategy:
    """
    编码策略基类

    定义可逆编码/解码接口。
    """
    name: str = "base"

    def encode(self, data: str) -> tuple[str, dict]:
        """编码字符串，返回 (编码结果, 解码参数)"""
        raise NotImplementedError

    def decode(self, encoded: str, params: dict) -> str:
        """解码字符串"""
        raise NotImplementedError


class XORShiftEncoding(EncodingStrategy):
    """
    XOR 字符偏移编码

    将每个字符与一个偏移量进行 XOR 运算。
    """

    name = "xor_shift"

    def __init__(self, key: int | None = None):
        self.key = key or random.randint(1, 255)

    def encode(self, data: str) -> tuple[str, dict]:
        result = []
        for c in data:
            result.append(chr(ord(c) ^ self.key))
        return "".join(result), {"key": self.key}

    def decode(self, encoded: str, params: dict) -> str:
        key = params.get("key", 1)
        result = []
        for c in encoded:
            result.append(chr(ord(c) ^ key))
        return "".join(result)


class SplitJoinEncoding(EncodingStrategy):
    """
    字符串拼接拆分编码

    将字符串拆分为两部分，用分隔符连接。
    """

    name = "split_join"

    def __init__(self, separator: str | None = None):
        self.separator = separator or "#"

    def encode(self, data: str) -> tuple[str, dict]:
        mid = len(data) // 2
        part1 = data[:mid]
        part2 = data[mid:]
        return f"{part1}{self.separator}{part2}", {"sep": self.separator}

    def decode(self, encoded: str, params: dict) -> str:
        sep = params.get("sep", "#")
        parts = encoded.split(sep)
        return "".join(parts)


class CharOffsetEncoding(EncodingStrategy):
    """
    字符偏移编码

    将每个字符的 ASCII 码偏移一定值。
    """

    name = "char_offset"

    def __init__(self, offset: int | None = None):
        self.offset = offset or random.randint(1, 127)

    def encode(self, data: str) -> tuple[str, dict]:
        result = []
        for c in data:
            code = ord(c) + self.offset
            result.append(chr(code % 128))
        return "".join(result), {"offset": self.offset}

    def decode(self, encoded: str, params: dict) -> str:
        offset = params.get("offset", 0)
        result = []
        for c in encoded:
            code = ord(c) - offset
            if code < 0:
                code += 128
            result.append(chr(code))
        return "".join(result)


class Base64Encoding(EncodingStrategy):
    """
    Base64 编码

    使用 Base64 编码字符串。
    """

    name = "base64"

    def encode(self, data: str) -> tuple[str, dict]:
        encoded = base64.b64encode(data.encode()).decode()
        return encoded, {}

    def decode(self, encoded: str, params: dict) -> str:
        return base64.b64decode(encoded.encode()).decode()


class ReverseEncoding(EncodingStrategy):
    """
    字符串反转编码
    """

    name = "reverse"

    def encode(self, data: str) -> tuple[str, dict]:
        return data[::-1], {}

    def decode(self, encoded: str, params: dict) -> str:
        return encoded[::-1]


class EncodingPipeline(EncodingStrategy):
    """
    编码管道

    将多个编码策略组合起来。
    """

    name = "pipeline"

    def __init__(self, strategies: list[EncodingStrategy] | None = None):
        self.strategies = strategies or []

    def add(self, strategy: EncodingStrategy) -> 'EncodingPipeline':
        self.strategies.append(strategy)
        return self

    def encode(self, data: str) -> tuple[str, dict]:
        current = data
        all_params = {}
        for i, strategy in enumerate(self.strategies):
            current, params = strategy.encode(current)
            all_params[strategy.name] = params
        return current, all_params

    def decode(self, encoded: str, params: dict) -> str:
        current = encoded
        for strategy in reversed(self.strategies):
            p = params.get(strategy.name, {})
            current = strategy.decode(current, p)
        return current


class EncodingStrategyFactory:
    """编码策略工厂"""

    _strategies: dict[str, type[EncodingStrategy]] = {
        "xor_shift": XORShiftEncoding,
        "split_join": SplitJoinEncoding,
        "char_offset": CharOffsetEncoding,
        "base64": Base64Encoding,
        "reverse": ReverseEncoding,
    }

    @classmethod
    def register(cls, name: str, strategy_cls: type[EncodingStrategy]) -> None:
        cls._strategies[name] = strategy_cls

    @classmethod
    def create(cls, name: str, **kwargs) -> EncodingStrategy:
        if name == "pipeline":
            return EncodingPipeline()
        if name not in cls._strategies:
            raise ValueError(f"Unknown encoding strategy: {name}")
        return cls._strategies[name](**kwargs)

    @classmethod
    def names(cls) -> list[str]:
        return list(cls._strategies.keys())


# ===== 字符串常量池收集器 =====


@dataclass
class StringEntry:
    """字符串条目"""
    original: str
    encoded: str
    encoding_name: str
    encoding_params: dict
    index: int

    def lua_literal(self) -> str:
        """生成 Lua 字面量"""
        escaped = self.encoded.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
        return f'"{escaped}"'


@dataclass
class StringPool:
    """字符串常量池"""
    entries: list[StringEntry]
    encoding_strategy: EncodingStrategy
    strategy_name: str

    def get(self, original: str) -> StringEntry | None:
        """通过原始字符串查找"""
        for entry in self.entries:
            if entry.original == original:
                return entry
        return None

    def get_by_index(self, index: int) -> StringEntry | None:
        """通过索引查找"""
        for entry in self.entries:
            if entry.index == index:
                return entry
        return None

    def generate_lua_table(self) -> str:
        """生成 Lua table"""
        lines = []
        lines.append("local __STRING_POOL__ = {")
        for entry in self.entries:
            lines.append(f"    [{entry.index}] = {{")
            lines.append(f'        s = {entry.lua_literal()},')
            lines.append(f'        e = "{entry.encoding_name}",')
            lines.append(f"        p = {self._params_to_lua(entry.encoding_params)},")
            lines.append("    },")
        lines.append("}")
        return "\n".join(lines)

    def _params_to_lua(self, params: dict) -> str:
        """将参数字典转换为 Lua 格式"""
        parts = []
        for k, v in params.items():
            if isinstance(v, str):
                parts.append(f'{k} = "{v}"')
            else:
                parts.append(f"{k} = {v}")
        return "{" + ", ".join(parts) + "}"


class StringPoolCollector:
    """
    字符串常量池收集器

    收集源码中的字符串常量，进行编码，并生成常量池。
    """

    def __init__(self, encoding_strategy: EncodingStrategy | None = None):
        self.encoding_strategy = encoding_strategy or XORShiftEncoding()
        self.pool: list[StringEntry] = []
        self._seen: dict[str, int] = {}

    def collect(self, tokens: list[Token]) -> StringPool:
        """
        从 token 列表收集字符串常量

        Args:
            tokens: Token 列表

        Returns:
            StringPool 实例
        """
        for token in tokens:
            if token.type == TokenType.STRING and token.text:
                self._add_string(token.text)

        return StringPool(
            entries=self.pool,
            encoding_strategy=self.encoding_strategy,
            strategy_name=self.encoding_strategy.name,
        )

    def collect_from_source(self, source: str) -> StringPool:
        """
        从源代码收集字符串常量

        Args:
            source: 源代码

        Returns:
            StringPool 实例
        """
        import re
        string_pattern = r'"([^"\\]*(?:\\.[^"\\]*)*)"'
        strings = re.findall(string_pattern, source)

        for s in strings:
            self._add_string(s)

        return StringPool(
            entries=self.pool,
            encoding_strategy=self.encoding_strategy,
            strategy_name=self.encoding_strategy.name,
        )

    def collect_from_instructions(self, instructions: list[Instruction]) -> StringPool:
        """
        从指令列表收集字符串常量

        Args:
            instructions: 指令列表

        Returns:
            StringPool 实例
        """
        for instr in instructions:
            for arg in instr.args:
                if isinstance(arg, str):
                    self._add_string(arg)
            if instr.result and isinstance(instr.result, str):
                self._add_string(instr.result)

        return StringPool(
            entries=self.pool,
            encoding_strategy=self.encoding_strategy,
            strategy_name=self.encoding_strategy.name,
        )

    def _add_string(self, s: str) -> None:
        """添加字符串到池中"""
        if s in self._seen:
            return

        encoded, params = self.encoding_strategy.encode(s)
        entry = StringEntry(
            original=s,
            encoded=encoded,
            encoding_name=self.encoding_strategy.name,
            encoding_params=params,
            index=len(self.pool) + 1,
        )
        self.pool.append(entry)
        self._seen[s] = entry.index

    def get_index(self, original: str) -> int | None:
        """获取字符串的索引"""
        return self._seen.get(original)


# ===== 运行时解码器生成器 =====


class RuntimeDecoderGenerator:
    """
    运行时解码器生成器

    生成 Lua 端的解码函数。
    """

    def __init__(self, encoding_strategy: EncodingStrategy | None = None):
        self.encoding_strategy = encoding_strategy

    def generate_decode_function(self, strategy_name: str = "xor_shift") -> str:
        """
        生成解码函数

        Args:
            strategy_name: 编码策略名称

        Returns:
            Lua 代码字符串
        """
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Runtime Decoder Functions")
        lines.append("-- =========================================")
        lines.append("")

        if strategy_name == "xor_shift":
            lines.append(self._generate_xor_shift_decoder())
        elif strategy_name == "char_offset":
            lines.append(self._generate_char_offset_decoder())
        elif strategy_name == "split_join":
            lines.append(self._generate_split_join_decoder())
        elif strategy_name == "base64":
            lines.append(self._generate_base64_decoder())
        elif strategy_name == "reverse":
            lines.append(self._generate_reverse_decoder())
        elif strategy_name == "pipeline":
            lines.append(self._generate_pipeline_decoder())

        lines.append("")
        lines.append(self._generate_generic_decode())

        return "\n".join(lines)

    def _generate_xor_shift_decoder(self) -> str:
        return """local function __decode_xor_shift__(encoded, params)
    local key = params.key or 1
    local result = {}
    for i = 1, #encoded do
        local c = string.byte(encoded, i)
        c = c ~ key
        result[i] = string.char(c)
    end
    return table.concat(result)
end"""

    def _generate_char_offset_decoder(self) -> str:
        return """local function __decode_char_offset__(encoded, params)
    local offset = params.offset or 0
    local result = {}
    for i = 1, #encoded do
        local c = string.byte(encoded, i) - offset
        if c < 0 then c = c + 128 end
        result[i] = string.char(c)
    end
    return table.concat(result)
end"""

    def _generate_split_join_decoder(self) -> str:
        return """local function __decode_split_join__(encoded, params)
    local sep = params.sep or "#"
    local parts = {}
    for part in string.gmatch(encoded, "[^" .. sep .. "]+") do
        table.insert(parts, part)
    end
    return table.concat(parts)
end"""

    def _generate_base64_decoder(self) -> str:
        return """local function __decode_base64__(encoded, params)
    local b64_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    local function decode_char(c)
        if c == "=" then return 0 end
        for i = 1, #b64_chars do
            if string.sub(b64_chars, i, i) == c then return i - 1 end
        end
        return 0
    end
    
    local result = {}
    local i = 1
    while i <= #encoded do
        local a = decode_char(string.sub(encoded, i, i))
        local b = decode_char(string.sub(encoded, i + 1, i + 1))
        local c = decode_char(string.sub(encoded, i + 2, i + 2))
        local d = decode_char(string.sub(encoded, i + 3, i + 3))
        
        local triplet = a * 2^18 + b * 2^12 + c * 2^6 + d
        table.insert(result, string.char(math.floor(triplet / 2^16)))
        if string.sub(encoded, i + 2, i + 2) ~= "=" then
            table.insert(result, string.char(math.floor(triplet / 2^8) % 256))
        end
        if string.sub(encoded, i + 3, i + 3) ~= "=" then
            table.insert(result, string.char(triplet % 256))
        end
        i = i + 4
    end
    return table.concat(result)
end"""

    def _generate_reverse_decoder(self) -> str:
        return """local function __decode_reverse__(encoded, params)
    local result = {}
    for i = #encoded, 1, -1 do
        table.insert(result, string.sub(encoded, i, i))
    end
    return table.concat(result)
end"""

    def _generate_pipeline_decoder(self) -> str:
        return """local function __decode_pipeline__(encoded, params, strategy_order)
    local current = encoded
    for i = #strategy_order, 1, -1 do
        local name = strategy_order[i]
        local p = params[name] or {}
        if name == "xor_shift" then
            current = __decode_xor_shift__(current, p)
        elseif name == "char_offset" then
            current = __decode_char_offset__(current, p)
        elseif name == "split_join" then
            current = __decode_split_join__(current, p)
        elseif name == "base64" then
            current = __decode_base64__(current, p)
        elseif name == "reverse" then
            current = __decode_reverse__(current, p)
        end
    end
    return current
end"""

    def _generate_generic_decode(self) -> str:
        return """local function __decode__(index)
    local entry = __STRING_POOL__[index]
    if not entry then return "" end
    
    local encoded = entry.s
    local strategy = entry.e
    local params = entry.p
    
    if strategy == "xor_shift" then
        return __decode_xor_shift__(encoded, params)
    elseif strategy == "char_offset" then
        return __decode_char_offset__(encoded, params)
    elseif strategy == "split_join" then
        return __decode_split_join__(encoded, params)
    elseif strategy == "base64" then
        return __decode_base64__(encoded, params)
    elseif strategy == "reverse" then
        return __decode_reverse__(encoded, params)
    elseif strategy == "pipeline" then
        return __decode_pipeline__(encoded, params, {"xor_shift", "char_offset", "split_join", "base64", "reverse"})
    end
    
    return encoded
end"""


class LuaConstantPoolGenerator:
    """
    Lua 常量池生成器

    生成包含常量池和解码函数的 Lua 代码。
    """

    def __init__(
        self,
        string_pool: StringPool | None = None,
        decoder_generator: RuntimeDecoderGenerator | None = None,
    ):
        self.string_pool = string_pool
        self.decoder_generator = decoder_generator or RuntimeDecoderGenerator()

    def generate(self) -> str:
        """生成完整的常量池代码"""
        parts = []

        if self.string_pool:
            parts.append(self.string_pool.generate_lua_table())
            parts.append("")

        parts.append(self.decoder_generator.generate_decode_function(
            self.string_pool.strategy_name if self.string_pool else "xor_shift"
        ))

        return "\n".join(parts)

    def generate_with_reference_function(self) -> str:
        """生成带引用函数的常量池代码"""
        parts = []
        parts.append(self.generate())
        parts.append("")
        parts.append("local function S(index)")
        parts.append("    return __decode__(index)")
        parts.append("end")
        return "\n".join(parts)


# ===== 整合到常量池 =====


class ConstantPoolGenerator:
    """
    完整常量池生成器

    整合字符串池和运行时解码器。
    """

    def __init__(
        self,
        encoding_strategy: EncodingStrategy | None = None,
        strategy_name: str | None = None,
    ):
        if strategy_name:
            self.encoding_strategy = EncodingStrategyFactory.create(strategy_name)
        else:
            self.encoding_strategy = encoding_strategy or XORShiftEncoding()

        self.collector = StringPoolCollector(self.encoding_strategy)
        self.string_pool: StringPool | None = None
        self.pool_generator = LuaConstantPoolGenerator()

    def collect_from_tokens(self, tokens: list[Token]) -> 'ConstantPoolGenerator':
        """从 tokens 收集"""
        self.string_pool = self.collector.collect(tokens)
        self.pool_generator.string_pool = self.string_pool
        return self

    def collect_from_source(self, source: str) -> 'ConstantPoolGenerator':
        """从源代码收集"""
        self.string_pool = self.collector.collect_from_source(source)
        self.pool_generator.string_pool = self.string_pool
        return self

    def collect_from_instructions(self, instructions: list[Instruction]) -> 'ConstantPoolGenerator':
        """从指令收集"""
        self.string_pool = self.collector.collect_from_instructions(instructions)
        self.pool_generator.string_pool = self.string_pool
        return self

    def generate(self, with_reference_function: bool = True) -> str:
        """生成 Lua 代码"""
        if with_reference_function:
            return self.pool_generator.generate_with_reference_function()
        return self.pool_generator.generate()

    def get_reference(self, original: str) -> str | None:
        """
        获取字符串的引用表达式

        Returns:
            Lua 表达式，如 "S(1)"
        """
        if not self.string_pool:
            return None
        idx = self.string_pool.get_index(original)
        if idx is None:
            return None
        return f"S({idx})"


# ===== 扩展 LuaProgramEmitter 支持常量池 =====


class EnhancedLuaProgramEmitter(LuaProgramEmitter):
    """
    增强的 Lua 程序发射器

    在原有基础上增加字符串常量池支持。
    """

    def __init__(
        self,
        use_constant_pool: bool = True,
        encoding_strategy: str = "xor_shift",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.use_constant_pool = use_constant_pool
        self.encoding_strategy_name = encoding_strategy
        self.constant_pool_generator: ConstantPoolGenerator | None = None

    def emit_constant_pool(self) -> str:
        """生成常量池代码"""
        if not self.constant_pool_generator:
            return ""
        return self.constant_pool_generator.generate()

    def emit_complete_program_with_pool(
        self,
        instructions: list[Instruction] | None = None,
        tokens: list[Token] | None = None,
        source: str = "",
        **kwargs
    ) -> str:
        """
        生成包含常量池的完整程序

        Args:
            instructions: 指令列表
            tokens: Token 列表
            source: 源代码

        Returns:
            完整 Lua 程序字符串
        """
        parts = []

        # Header
        header = []
        header.append("-- =========================================")
        header.append("-- Lua Instruction Interpreter with Constant Pool")
        header.append("-- Generated by lua_obfuscator")
        header.append("-- =========================================")
        header.append("")
        header.append(f"local _DEBUG = {'true' if self.include_debug else 'false'}")
        parts.append("\n".join(header))

        # Part 1: Constant Pool
        if self.use_constant_pool:
            self.constant_pool_generator = ConstantPoolGenerator(
                strategy_name=self.encoding_strategy_name
            )
            if tokens:
                self.constant_pool_generator.collect_from_tokens(tokens)
            elif source:
                self.constant_pool_generator.collect_from_source(source)
            elif instructions:
                self.constant_pool_generator.collect_from_instructions(instructions)

            parts.append("-- =========================================")
            parts.append("-- String Constant Pool")
            parts.append("-- =========================================")
            parts.append(self.constant_pool_generator.generate())

        # Part 2: Instruction Table (使用常量池引用)
        if instructions:
            parts.append(self.emit_instruction_table(instructions))

        # Part 3: Execution State
        parts.append(self.emit_execution_state())

        # Part 4: Handler Module
        parts.append(self.emit_handler_module())

        # Part 5: Executor Loop
        parts.append(self.emit_executor_loop())

        # Part 6: Runner
        if instructions:
            parts.append(self.emit_runner())

        return "\n\n".join(parts)


# ===== 便捷函数 =====


def create_constant_pool_generator(
    encoding_strategy: str = "xor_shift",
) -> ConstantPoolGenerator:
    """
    创建常量池生成器

    Args:
        encoding_strategy: 编码策略名称

    Returns:
        ConstantPoolGenerator 实例
    """
    return ConstantPoolGenerator(strategy_name=encoding_strategy)


def encode_strings_for_lua(
    strings: list[str],
    encoding_strategy: str = "xor_shift",
) -> tuple[StringPool, str]:
    """
    编码字符串列表

    Args:
        strings: 字符串列表
        encoding_strategy: 编码策略

    Returns:
        (StringPool, Lua代码)
    """
    generator = ConstantPoolGenerator(strategy_name=encoding_strategy)
    for s in strings:
        idx = len(generator.collector.pool) + 1
        encoded, params = generator.encoding_strategy.encode(s)
        entry = StringEntry(
            original=s,
            encoded=encoded,
            encoding_name=encoding_strategy,
            encoding_params=params,
            index=idx,
        )
        generator.collector.pool.append(entry)
        generator.collector._seen[s] = idx
    generator.string_pool = StringPool(
        entries=generator.collector.pool,
        encoding_strategy=generator.encoding_strategy,
        strategy_name=encoding_strategy,
    )
    return generator.string_pool, generator.generate()


def demo_constant_pool():
    """演示常量池功能"""
    print("=" * 60)
    print("String Constant Pool Demo")
    print("=" * 60)

    # 测试编码策略
    strategies = [
        ("XOR Shift", XORShiftEncoding(42)),
        ("Char Offset", CharOffsetEncoding(5)),
        ("Split Join", SplitJoinEncoding("||")),
        ("Base64", Base64Encoding()),
        ("Reverse", ReverseEncoding()),
    ]

    test_strings = ["Hello", "World", "Lua", "Protection"]

    print("\n[1] Encoding Strategies Test:")
    print("-" * 40)
    for name, strategy in strategies:
        print(f"\n{name}:")
        for s in test_strings[:2]:
            encoded, params = strategy.encode(s)
            decoded = strategy.decode(encoded, params)
            print(f"  '{s}' -> '{encoded}' -> '{decoded}'")
            assert decoded == s, f"Decode failed: {decoded} != {s}"

    # 测试常量池收集器
    print("\n\n[2] Constant Pool Collector:")
    print("-" * 40)

    generator = ConstantPoolGenerator(strategy_name="xor_shift")
    pool, lua_code = encode_strings_for_lua(test_strings, "xor_shift")

    print("\nGenerated Lua Constant Pool:")
    print(lua_code)

    print("\nPool Entries:")
    for entry in pool.entries:
        print(f"  [{entry.index}] '{entry.original}' -> '{entry.encoded}'")

    # 测试完整的发射器
    print("\n\n[3] Enhanced Program Emitter:")
    print("-" * 40)

    emitter = EnhancedLuaProgramEmitter(
        use_constant_pool=True,
        encoding_strategy="xor_shift",
        include_debug=True,
    )

    instructions = [
        Instruction(OpCode.INIT, ["msg"], None, "Hello"),
        Instruction(OpCode.CALL, ["print"], None, "print"),
        Instruction(OpCode.RETURN_VAL, ["msg"]),
    ]

    program = emitter.emit_complete_program_with_pool(
        instructions=instructions,
        source='print("Hello")',
    )

    print("\nGenerated Program:")
    print(program)

    print("\n" + "=" * 60)
    print("Demo Complete")
    print("=" * 60)


if __name__ == "__main__":
    demo_constant_pool()


# ===== Handler 多态实现系统 =====


from abc import ABC, abstractmethod
from typing import Protocol


class HandlerImplementation(ABC):
    """
    Handler 实现基类

    定义同一 opcode 的不同实现方式。
    """

    name: str = "base"
    opcode: int = 0
    description: str = ""

    @abstractmethod
    def generate(self, template: dict[str, str] | None = None) -> str:
        """生成 Lua 代码"""
        raise NotImplementedError

    @abstractmethod
    def get_dependencies(self) -> list[str]:
        """获取依赖的辅助函数"""
        return []


class DirectHandlerImpl(HandlerImplementation):
    """
    直接计算形式

    直接执行计算，无需中间变量。
    """

    name = "direct"

    def generate(self, template: dict[str, str] | None = None) -> str:
        if not template:
            return "    default = function(instr, state, pc) return pc + 1 end"
        return f"    {template['template'].strip()}"

    def get_dependencies(self) -> list[str]:
        return []


class StepwiseHandlerImpl(HandlerImplementation):
    """
    分步计算形式

    使用中间变量分步执行计算。
    """

    name = "stepwise"

    def generate(self, template: dict[str, str] | None = None) -> str:
        if not template:
            return "    default = function(instr, state, pc) return pc + 1 end"

        opcode = template.get("opcode", 0)
        desc = template.get("desc", "")

        lines = [
            f"    [{opcode}] = function(instr, state, pc)",
            "        -- Stepwise implementation",
            "        local _tmp_1",
            "        local _tmp_2",
            "        _tmp_1 = instr[2]",
            "        _tmp_2 = _eval_literal(instr[3])",
            f"        state.locals[_tmp_1] = _tmp_2",
            "        return pc + 1",
            "    end"
        ]
        return "\n".join(lines)

    def get_dependencies(self) -> list[str]:
        return ["_eval_literal"]


class TableAssistedHandlerImpl(HandlerImplementation):
    """
    Table 辅助计算形式

    使用局部 table 进行数据组织。
    """

    name = "table_assisted"

    def generate(self, template: dict[str, str] | None = None) -> str:
        if not template:
            return "    default = function(instr, state, pc) return pc + 1 end"

        opcode = template.get("opcode", 0)

        lines = [
            f"    [{opcode}] = function(instr, state, pc)",
            "        -- Table-assisted implementation",
            "        local _ctx = {",
            "            opcode = instr[1],",
            "            arg1 = instr[2],",
            "            arg2 = instr[3],",
            "            result = nil",
            "        }",
            "        if _ctx.arg2 then",
            "            _ctx.result = _eval_literal(_ctx.arg2)",
            "        end",
            "        state.locals[_ctx.arg1] = _ctx.result",
            "        return pc + 1",
            "    end"
        ]
        return "\n".join(lines)

    def get_dependencies(self) -> list[str]:
        return ["_eval_literal"]


class FunctionComposedHandlerImpl(HandlerImplementation):
    """
    函数组合形式

    拆分为多个局部函数再组合执行。
    """

    name = "function_composed"

    def generate(self, template: dict[str, str] | None = None) -> str:
        if not template:
            return "    default = function(instr, state, pc) return pc + 1 end"

        opcode = template.get("opcode", 0)

        lines = [
            f"    [{opcode}] = function(instr, state, pc)",
            "        -- Function-composed implementation",
            "        local function _extract_arg(n)",
            "            return instr[n]",
            "        end",
            "        local function _resolve(v)",
            "            return _eval_literal(v)",
            "        end",
            "        local function _store(k, v)",
            "            state.locals[k] = v",
            "        end",
            "        local _key = _extract_arg(2)",
            "        local _val = _resolve(_extract_arg(3))",
            "        _store(_key, _val)",
            "        return pc + 1",
            "    end"
        ]
        return "\n".join(lines)

    def get_dependencies(self) -> list[str]:
        return ["_eval_literal"]


class ClosureBasedHandlerImpl(HandlerImplementation):
    """
    闭包形式

    使用闭包捕获状态。
    """

    name = "closure_based"

    def generate(self, template: dict[str, str] | None = None) -> str:
        if not template:
            return "    default = function(instr, state, pc) return pc + 1 end"

        opcode = template.get("opcode", 0)

        lines = [
            f"    [{opcode}] = (function()",
            "        -- Closure-based implementation",
            "        local _cache = {}",
            "        return function(instr, state, pc)",
            "            local op = instr[1]",
            "            if not _cache[op] then",
            "                _cache[op] = function()",
            "                    local k, v = instr[2], _eval_literal(instr[3])",
            "                    state.locals[k] = v",
            "                end",
            "            end",
            "            _cache[op]()",
            "            return pc + 1",
            "        end",
            "    end)()"
        ]
        return "\n".join(lines)

    def get_dependencies(self) -> list[str]:
        return ["_eval_literal"]


class MacroExpandedHandlerImpl(HandlerImplementation):
    """
    宏展开形式

    将操作内联展开，避免函数调用。
    """

    name = "macro_expanded"

    def generate(self, template: dict[str, str] | None = None) -> str:
        if not template:
            return "    default = function(instr, state, pc) return pc + 1 end"

        opcode = template.get("opcode", 0)

        lines = [
            f"    [{opcode}] = function(instr, state, pc)",
            "        -- Macro-expanded implementation",
            "        do",
            "            local _arg1 = instr[2]",
            "            local _raw_val = instr[3]",
            "            local _final_val",
            "            if type(_raw_val) == 'string' then",
            "                local _n = tonumber(_raw_val)",
            "                _final_val = _n or _raw_val",
            "            else",
            "                _final_val = _raw_val",
            "            end",
            "            state.locals[_arg1] = _final_val",
            "        end",
            "        return pc + 1",
            "    end"
        ]
        return "\n".join(lines)

    def get_dependencies(self) -> list[str]:
        return []


# ===== Handler 实现注册表 =====


class HandlerImplRegistry:
    """
    Handler 实现注册表

    管理每种 opcode 的多种实现方式。
    """

    _impls: dict[int, list[type[HandlerImplementation]]] = {}

    @classmethod
    def register(cls, opcode: int, impl_class: type[HandlerImplementation]) -> None:
        if opcode not in cls._impls:
            cls._impls[opcode] = []
        cls._impls[opcode].append(impl_class)

    @classmethod
    def get_implementations(cls, opcode: int) -> list[type[HandlerImplementation]]:
        return cls._impls.get(opcode, [DirectHandlerImpl])

    @classmethod
    def register_all(cls) -> None:
        impls = [
            DirectHandlerImpl,
            StepwiseHandlerImpl,
            TableAssistedHandlerImpl,
            FunctionComposedHandlerImpl,
            ClosureBasedHandlerImpl,
            MacroExpandedHandlerImpl,
        ]
        for opcode in range(50):
            for impl in impls:
                cls.register(opcode, impl)


# 注册默认实现
HandlerImplRegistry.register_all()


# ===== Handler 策略选择器 =====


class HandlerStrategy:
    """
    Handler 生成策略

    决定如何为每个 opcode 选择实现方式。
    """

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()

    def select_implementation(
        self,
        opcode: int,
        context: dict | None = None
    ) -> type[HandlerImplementation]:
        """
        选择实现方式

        Args:
            opcode: 操作码
            context: 上下文信息

        Returns:
            选中的实现类
        """
        raise NotImplementedError


class RandomStrategy(HandlerStrategy):
    """随机选择策略"""

    def select_implementation(
        self,
        opcode: int,
        context: dict | None = None
    ) -> type[HandlerImplementation]:
        impls = HandlerImplRegistry.get_implementations(opcode)
        return self.rng.choice(impls)


class WeightedRandomStrategy(HandlerStrategy):
    """加权随机选择策略"""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        rng: random.Random | None = None
    ):
        super().__init__(rng)
        self.weights = weights or {
            "direct": 0.3,
            "stepwise": 0.2,
            "table_assisted": 0.15,
            "function_composed": 0.15,
            "closure_based": 0.1,
            "macro_expanded": 0.1,
        }

    def select_implementation(
        self,
        opcode: int,
        context: dict | None = None
    ) -> type[HandlerImplementation]:
        impls = HandlerImplRegistry.get_implementations(opcode)
        names = [impl.name for impl in impls]
        weights = [self.weights.get(n, 0.1) for n in names]

        total = sum(weights)
        probs = [w / total for w in weights]

        r = self.rng.random()
        cumsum = 0
        for i, p in enumerate(probs):
            cumsum += p
            if r <= cumsum:
                return impls[i]
        return impls[0]


class OpcodeBasedStrategy(HandlerStrategy):
    """基于 opcode 的选择策略"""

    def select_implementation(
        self,
        opcode: int,
        context: dict | None = None
    ) -> type[HandlerImplementation]:
        impls = HandlerImplRegistry.get_implementations(opcode)

        if opcode in (1, 2, 3):
            return StepwiseHandlerImpl
        elif opcode in (4, 5):
            return FunctionComposedHandlerImpl
        elif opcode in (6, 7):
            return DirectHandlerImpl
        elif opcode in (10, 11):
            return TableAssistedHandlerImpl
        elif opcode in (24, 26, 27):
            return MacroExpandedHandlerImpl
        else:
            idx = opcode % len(impls)
            return impls[idx]


class AlternatingStrategy(HandlerStrategy):
    """交替选择策略"""

    def __init__(self, rng: random.Random | None = None):
        super().__init__(rng)
        self._counter = {}

    def select_implementation(
        self,
        opcode: int,
        context: dict | None = None
    ) -> type[HandlerImplementation]:
        impls = HandlerImplRegistry.get_implementations(opcode)

        if opcode not in self._counter:
            self._counter[opcode] = 0

        idx = self._counter[opcode] % len(impls)
        self._counter[opcode] += 1
        return impls[idx]


class ContextAwareStrategy(HandlerStrategy):
    """上下文感知策略"""

    def select_implementation(
        self,
        opcode: int,
        context: dict | None = None
    ) -> type[HandlerImplementation]:
        impls = HandlerImplRegistry.get_implementations(opcode)
        ctx = context or {}

        if ctx.get("has_dependencies"):
            return DirectHandlerImpl
        if ctx.get("complexity", 0) > 5:
            return FunctionComposedHandlerImpl
        if ctx.get("is_loop"):
            return StepwiseHandlerImpl
        if ctx.get("is_table_op"):
            return TableAssistedHandlerImpl

        idx = opcode % len(impls)
        return impls[idx]


class StrategyFactory:
    """策略工厂"""

    _strategies: dict[str, type[HandlerStrategy]] = {
        "random": RandomStrategy,
        "weighted": WeightedRandomStrategy,
        "opcode_based": OpcodeBasedStrategy,
        "alternating": AlternatingStrategy,
        "context_aware": ContextAwareStrategy,
    }

    @classmethod
    def create(cls, name: str, **kwargs) -> HandlerStrategy:
        if name not in cls._strategies:
            raise ValueError(f"Unknown strategy: {name}")
        return cls._strategies[name](**kwargs)

    @classmethod
    def names(cls) -> list[str]:
        return list(cls._strategies.keys())


# ===== 多态 Handler 生成器 =====


class PolymorphicHandlerGenerator:
    """
    多态 Handler 生成器

    支持为每个 opcode 选择不同实现方式。
    """

    def __init__(
        self,
        strategy: HandlerStrategy | None = None,
        include_comments: bool = True,
        rng: random.Random | None = None
    ):
        self.strategy = strategy or RandomStrategy(rng)
        self.include_comments = include_comments
        self.rng = rng or random.Random()

        self.base_generator = LuaHandlerGenerator(include_comments=False)

    def generate_all(
        self,
        templates: dict[int, dict[str, str]]
    ) -> str:
        """
        生成所有 handler

        Args:
            templates: opcode -> {desc, template}

        Returns:
            Lua 代码
        """
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Polymorphic Handler Implementations")
        lines.append("-- =========================================")
        lines.append("")

        for opcode in sorted(templates.keys()):
            template = templates[opcode]
            impl_class = self.strategy.select_implementation(opcode, template)
            impl = impl_class()

            context = {
                "opcode": opcode,
                "has_dependencies": bool(impl.get_dependencies()),
                "complexity": len(template.get("template", "")),
            }

            if self.include_comments:
                lines.append(f"    -- opcode: {opcode} ({template['desc']}) [using: {impl.name}]")

            handler_code = impl.generate(template)
            lines.append(handler_code)

        lines.append("")
        lines.append(self._generate_default_handler())

        return "\n".join(lines)

    def _generate_default_handler(self) -> str:
        return """    -- Default handler
    default = function(instr, state, pc)
        if _DEBUG then
            print('Unknown opcode: ' .. tostring(instr[1]))
        end
        return pc + 1
    end,
"""

    def generate_with_helper_functions(
        self,
        templates: dict[int, dict[str, str]]
    ) -> str:
        """生成带辅助函数的 handler"""
        all_deps = set()
        for opcode in templates.keys():
            impl_class = self.strategy.select_implementation(opcode)
            impl = impl_class()
            all_deps.update(impl.get_dependencies())

        parts = []

        if all_deps:
            parts.append(self._generate_utility_functions())

        parts.append(self.generate_all(templates))

        return "\n\n".join(parts)

    def _generate_utility_functions(self) -> str:
        return """-- Utility functions for handlers
local function _eval_literal(val)
    if val == nil then return nil end
    if val == true then return true end
    if val == false then return false end
    if type(val) == 'number' then return val end
    if type(val) == 'string' then
        local n = tonumber(val)
        if n then return n end
    end
    return val
end
"""


class HandlerDiversityAnalyzer:
    """
    Handler 多样性分析器

    分析生成代码的多样性。
    """

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()

    def analyze_diversity(
        self,
        code: str,
        templates: dict[int, dict[str, str]]
    ) -> dict:
        """
        分析生成代码的多样性

        Returns:
            多样性统计
        """
        impl_counts = {}

        for opcode in templates.keys():
            impl_class = self.strategy.select_implementation(opcode)
            impl_name = impl_class.name
            impl_counts[impl_name] = impl_counts.get(impl_name, 0) + 1

        total = len(templates)
        diversity_score = len(impl_counts) / 6

        return {
            "total_handlers": total,
            "implementation_counts": impl_counts,
            "unique_implementations": len(impl_counts),
            "diversity_score": diversity_score,
            "distribution": {
                name: count / total
                for name, count in impl_counts.items()
            }
        }


# ===== 整合到 LuaProgramEmitter =====


class PolymorphicLuaProgramEmitter(LuaProgramEmitter):
    """
    多态 Lua 程序发射器

    使用多态 handler 实现。
    """

    def __init__(
        self,
        handler_strategy: str = "weighted",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.handler_strategy_name = handler_strategy
        self.polymorphic_generator: PolymorphicHandlerGenerator | None = None

    def emit_polymorphic_handlers(
        self,
        templates: dict[int, dict[str, str]]
    ) -> str:
        """生成多态 handler"""
        rng = random.Random()
        strategy = StrategyFactory.create(
            self.handler_strategy_name,
            rng=rng
        )

        self.polymorphic_generator = PolymorphicHandlerGenerator(
            strategy=strategy,
            include_comments=self.include_comments,
            rng=rng
        )

        return self.polymorphic_generator.generate_all(templates)

    def emit_complete_polymorphic_program(
        self,
        instructions: list[Instruction] | None = None,
        **kwargs
    ) -> str:
        """生成完整的多态程序"""
        parts = []

        parts.append("-- =========================================")
        parts.append("-- Polymorphic Lua Instruction Interpreter")
        parts.append("-- Generated by lua_obfuscator")
        parts.append("-- =========================================")
        parts.append("")
        parts.append(f"local _DEBUG = {'true' if self.include_debug else 'false'}")
        parts.append("")

        if instructions:
            parts.append(self.emit_instruction_table(instructions))

        parts.append(self.emit_execution_state())

        parts.append("-- =========================================")
        parts.append("-- Polymorphic Handlers")
        parts.append("-- =========================================")
        parts.append("")
        parts.append(self.emit_polymorphic_handlers(
            LuaHandlerGenerator().HANDLER_TEMPLATES
        ))

        parts.append("")
        parts.append(self.emit_dispatcher())

        parts.append("")
        parts.append(self.emit_executor_loop())

        if instructions:
            parts.append(self.emit_runner())

        return "\n\n".join(parts)


# ===== 便捷函数 =====


def create_polymorphic_emitter(
    strategy: str = "weighted",
    include_debug: bool = False
) -> PolymorphicLuaProgramEmitter:
    """创建多态发射器"""
    return PolymorphicLuaProgramEmitter(
        handler_strategy=strategy,
        include_debug=include_debug
    )


def demo_polymorphic_handlers():
    """演示多态 handler 生成"""
    print("=" * 60)
    print("Polymorphic Handler Demo")
    print("=" * 60)

    templates = LuaHandlerGenerator().HANDLER_TEMPLATES

    strategies = [
        ("Random", "random"),
        ("Weighted Random", "weighted"),
        ("Opcode Based", "opcode_based"),
        ("Alternating", "alternating"),
    ]

    for name, strategy_name in strategies:
        print(f"\n{'=' * 40}")
        print(f"Strategy: {name}")
        print("-" * 40)

        emitter = PolymorphicLuaProgramEmitter(
            handler_strategy=strategy_name,
            include_debug=True
        )

        code = emitter.emit_polymorphic_handlers(templates)

        print(code[:1500])
        if len(code) > 1500:
            print("\n... (truncated)")

    print("\n" + "=" * 60)
    print("Demo Complete")
    print("=" * 60)


if __name__ == "__main__":
    demo_polymorphic_handlers()


# ===== 指令紧凑编码系统 =====


class OpCodeEncoding:
    """
    Opcode 编码表

    将字符串 opcode 映射为数值 ID。
    """

    # Opcode -> ID 映射
    OPCODE_TO_ID: dict[str, int] = {
        "nop": 0,
        "declare": 1,
        "init": 2,
        "assign": 3,
        "call": 4,
        "call_assign": 5,
        "return": 6,
        "return_val": 7,
        "jump": 8,
        "jump_if": 9,
        "do": 10,
        "end": 11,
        "if": 12,
        "then": 13,
        "else": 14,
        "elseif": 15,
        "while": 16,
        "for": 17,
        "repeat": 18,
        "until": 19,
        "break": 20,
        "continue": 21,
        "func_def": 22,
        "func_end": 23,
        "expr": 24,
        "error": 25,
        "table_new": 26,
        "table_set": 27,
        "table_get": 28,
        "label": 29,
        "identity": 30,
        "dummy": 31,
        "comment": 32,
        "assert": 33,
    }

    # ID -> Opcode 映射
    ID_TO_OPCODE: dict[int, str] = {v: k for k, v in OPCODE_TO_ID.items()}

    @classmethod
    def encode(cls, opcode: str | OpCode) -> int:
        """将 opcode 字符串转为数值 ID"""
        if isinstance(opcode, OpCode):
            opcode = opcode.value
        return cls.OPCODE_TO_ID.get(opcode, 0)

    @classmethod
    def decode(cls, opcode_id: int) -> str:
        """将数值 ID 转为 opcode 字符串"""
        return cls.ID_TO_OPCODE.get(opcode_id, "nop")


class CompactInstruction:
    """
    紧凑指令格式

    支持多种紧凑编码方案。
    """

    FORMAT_FLAT = "flat"      # {opcode_id, arg1, arg2}
    FORMAT_STREAM = "stream"  # [op, a, b, op, a, b, ...]
    FORMAT_PACKED = "packed"  # 二进制打包

    def __init__(
        self,
        opcode: int,
        args: list = None,
        format_type: str = FORMAT_FLAT
    ):
        self.opcode = opcode
        self.args = args or []
        self.format_type = format_type

    def to_flat(self) -> list:
        """转为扁平格式 {opcode, arg1, arg2}"""
        result = [self.opcode]
        result.extend(self.args[:3])
        return result

    def to_stream_entry(self) -> list:
        """转为流式格式"""
        return self.to_flat()

    def __repr__(self) -> str:
        return f"CompactInstr({self.opcode}, {self.args})"


class CompactEncoder:
    """
    紧凑编码器

    将 Instruction 列表编码为紧凑格式。
    """

    def __init__(
        self,
        constant_pool: dict | None = None,
        use_pool_refs: bool = False
    ):
        self.constant_pool = constant_pool or {}
        self.use_pool_refs = use_pool_refs
        self._pool_index: dict[str, int] = {}

    def encode_instruction(self, instr: Instruction) -> CompactInstruction:
        """编码单条指令"""
        opcode_id = OpCodeEncoding.encode(instr.op)

        args = []
        for arg in instr.args:
            if isinstance(arg, str):
                if self.use_pool_refs and arg in self.constant_pool:
                    ref = self._get_pool_ref(arg)
                    args.append(ref)
                else:
                    args.append(arg)
            else:
                args.append(arg)

        return CompactInstruction(opcode_id, args)

    def _get_pool_ref(self, value: str) -> int:
        """获取常量池引用"""
        if value not in self._pool_index:
            self._pool_index[value] = len(self._pool_index) + 1
        return self._pool_index[value]

    def encode_flat(self, instructions: list[Instruction]) -> list[list]:
        """编码为扁平格式 {opcode, arg1, arg2}"""
        return [self.encode_instruction(i).to_flat() for i in instructions]

    def encode_stream(self, instructions: list[Instruction]) -> list:
        """编码为流式格式 [op, a, b, op, a, b, ...]"""
        result = []
        for instr in instructions:
            entry = self.encode_instruction(instr).to_stream_entry()
            result.extend(entry)
        return result

    def encode_indexed(self, instructions: list[Instruction]) -> dict:
        """编码为索引格式，带元数据"""
        encoded = []
        for i, instr in enumerate(instructions):
            ci = self.encode_instruction(instr)
            encoded.append({
                "i": i + 1,
                "op": ci.opcode,
                "args": ci.args,
                "raw": ci.to_flat()
            })
        return {"instructions": encoded, "metadata": self._get_metadata()}

    def _get_metadata(self) -> dict:
        """获取元数据"""
        return {
            "opcode_count": len(OpCodeEncoding.OPCODE_TO_ID),
            "pool_size": len(self._pool_index),
            "format": "compact_v1"
        }


class CompactSerializer:
    """
    紧凑序列化器

    将编码后的指令序列序列化为 Lua 代码。
    """

    def __init__(
        self,
        encoder: CompactEncoder | None = None,
        var_name: str = "code",
        indent: str = "    "
    ):
        self.encoder = encoder or CompactEncoder()
        self.var_name = var_name
        self.indent = indent

    def serialize_flat(
        self,
        instructions: list[Instruction],
        with_indices: bool = True
    ) -> str:
        """序列化扁平格式"""
        encoded = self.encoder.encode_flat(instructions)

        lines = [f"local {self.var_name} = {{}}"]

        for i, entry in enumerate(encoded):
            if with_indices:
                line = f"{self.indent}[{i + 1}] = {{{entry[0]}, {self._format_arg(entry[1])}, {self._format_arg(entry[2])}}}"
            else:
                line = f"{{{entry[0]}, {self._format_arg(entry[1])}, {self._format_arg(entry[2])}}}"
            lines.append(line)

        return "\n".join(lines)

    def serialize_stream(
        self,
        instructions: list[Instruction],
        items_per_line: int = 6
    ) -> str:
        """序列化流式格式"""
        encoded = self.encoder.encode_stream(instructions)

        lines = [f"local {self.var_name} = {{"]

        for i in range(0, len(encoded), items_per_line):
            chunk = encoded[i:i + items_per_line]
            formatted = [self._format_arg(a) for a in chunk]
            lines.append(f"{self.indent}{', '.join(formatted)},")

        lines.append("}")
        return "\n".join(lines)

    def serialize_compact(self, instructions: list[Instruction]) -> str:
        """序列化紧凑格式（优化行数）"""
        encoded = self.encoder.encode_flat(instructions)

        lines = [f"local {self.var_name} = {{"]

        entries = []
        for entry in encoded:
            entries.append(f"{{{entry[0]},{self._format_arg_compact(entry[1])},{self._format_arg_compact(entry[2])}}}")

        lines.append(self.indent + ", ".join(entries))
        lines.append("}")
        return "\n".join(lines)

    def serialize_minimal(self, instructions: list[Instruction]) -> str:
        """最小化序列化"""
        encoded = self.encoder.encode_stream(instructions)
        formatted = [str(a) for a in encoded]
        return f"local {self.var_name} = {{{','.join(formatted)}}}"


    def _format_arg(self, arg) -> str:
        """格式化参数"""
        if arg is None:
            return "nil"
        if isinstance(arg, bool):
            return "true" if arg else "false"
        if isinstance(arg, (int, float)):
            return str(arg)
        if isinstance(arg, str):
            escaped = arg.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        return str(arg)

    def _format_arg_compact(self, arg) -> str:
        """紧凑格式化参数"""
        if arg is None:
            return "0"
        if isinstance(arg, bool):
            return "1" if arg else "0"
        if isinstance(arg, (int, float)):
            return str(arg)
        if isinstance(arg, str):
            return f'"{arg}"'
        return "0"


# ===== Lua 紧凑解码器 =====


class LuaCompactDecoderGenerator:
    """
    Lua 紧凑解码器生成器

    生成 Lua 端的解码函数。
    """

    def __init__(self, format_type: str = "flat"):
        self.format_type = format_type

    def generate(self) -> str:
        """生成解码器代码"""
        parts = []

        parts.append("-- =========================================")
        parts.append("-- Compact Instruction Decoder")
        parts.append("-- =========================================")
        parts.append("")

        parts.append(self._generate_opcode_table())
        parts.append("")
        parts.append(self._generate_decoder_functions())

        return "\n".join(parts)

    def _generate_opcode_table(self) -> str:
        """生成 opcode 表"""
        lines = []
        lines.append("local __OPCODES__ = {")
        for name, id_val in sorted(OpCodeEncoding.OPCODE_TO_ID.items(), key=lambda x: x[1]):
            lines.append(f"    [{id_val}] = \"{name}\",")
        lines.append("}")
        return "\n".join(lines)

    def _generate_decoder_functions(self) -> str:
        """生成解码函数"""
        return """-- Decode instruction at index
local function __decode_instr__(code, index)
    local raw = code[index]
    if not raw then return nil end
    return {
        opcode = raw[1],
        opname = __OPCODES__[raw[1]] or "nop",
        arg1 = raw[2],
        arg2 = raw[3],
        arg3 = raw[4],
    }
end

-- Decode stream instruction at position
local function __decode_stream__(code, pos)
    local opcode = code[pos]
    if not opcode then return nil end
    return {
        opcode = opcode,
        opname = __OPCODES__[opcode] or "nop",
        arg1 = code[pos + 1],
        arg2 = code[pos + 2],
        pos = pos + 3
    }
end

-- Get opcode name from id
local function __opname__(opcode_id)
    return __OPCODES__[opcode_id] or "nop"
end

-- Get opcode id from name
local __OPCODE_IDS__ = {
    nop = 0, declare = 1, init = 2, assign = 3, call = 4,
    call_assign = 5, return = 6, return_val = 7, jump = 8,
    jump_if = 9, do = 10, end = 11, if = 12, then = 13,
    else = 14, elseif = 15, while = 16, for = 17, repeat = 18,
    until = 19, break = 20, continue = 21, func_def = 22,
    func_end = 23, expr = 24, error = 25, table_new = 26,
    table_set = 27, table_get = 28, label = 29, identity = 30,
    dummy = 31, comment = 32, assert = 33,
}

local function __opcode_id__(name)
    return __OPCODE_IDS__[name] or 0
end"""


class CompactExecutorGenerator:
    """
    紧凑执行器生成器

    生成支持紧凑格式的执行器。
    """

    def __init__(
        self,
        format_type: str = "flat",
        decoder_generator: LuaCompactDecoderGenerator | None = None
    ):
        self.format_type = format_type
        self.decoder = decoder_generator or LuaCompactDecoderGenerator(format_type)

    def generate(self) -> str:
        """生成执行器代码"""
        parts = []

        parts.append("-- =========================================")
        parts.append("-- Compact Executor")
        parts.append("-- =========================================")
        parts.append("")

        parts.append(self.decoder.generate())
        parts.append("")
        parts.append(self._generate_executor())

        return "\n".join(parts)

    def _generate_executor(self) -> str:
        """生成执行循环"""
        if self.format_type == "flat":
            return self._generate_flat_executor()
        elif self.format_type == "stream":
            return self._generate_stream_executor()
        else:
            return self._generate_flat_executor()

    def _generate_flat_executor(self) -> str:
        return """-- Flat format executor
local function __execute_flat__(code, state)
    local pc = 1
    while pc and not state.halted do
        local instr = __decode_instr__(code, pc)
        if not instr then break end

        local op = instr.opcode
        local handler = handlers[op] or handlers.default

        -- Execute handler with decoded instruction
        local next_pc = handler({
            [1] = instr.opcode,
            [2] = instr.arg1,
            [3] = instr.arg2,
            [4] = instr.arg3,
        }, state, pc)

        pc = next_pc or (pc + 1)

        -- Safety check
        if pc < 0 or pc > #code + 1 then break end
    end
    return state.return_value
end

local __execute__ = __execute_flat__"""

    def _generate_stream_executor(self) -> str:
        return """-- Stream format executor
local function __execute_stream__(code, state)
    local pc = 1
    while pc and not state.halted do
        if pc > #code then break end

        local instr = __decode_stream__(code, pc)
        if not instr then break end

        local handler = handlers[instr.opcode] or handlers.default

        local next_pc = handler({
            [1] = instr.opcode,
            [2] = instr.arg1,
            [3] = instr.arg2,
        }, state, pc)

        pc = next_pc or (pc + 3)

        -- Safety check
        if pc < 0 or pc > #code + 1 then break end
    end
    return state.return_value
end

local __execute__ = __execute_stream__"""


class CompactLuaProgramGenerator:
    """
    紧凑 Lua 程序生成器

    整合编码器和解码器生成完整程序。
    """

    def __init__(
        self,
        format_type: str = "flat",
        use_pool_refs: bool = False,
        include_debug: bool = False
    ):
        self.format_type = format_type
        self.use_pool_refs = use_pool_refs
        self.include_debug = include_debug

        self.encoder = CompactEncoder(use_pool_refs=use_pool_refs)
        self.serializer = CompactSerializer(self.encoder)
        self.executor_gen = CompactExecutorGenerator(format_type)

    def generate(
        self,
        instructions: list[Instruction],
        code_var: str = "code",
        state_var: str = "state"
    ) -> str:
        """生成完整程序"""
        parts = []

        parts.append("-- =========================================")
        parts.append("-- Compact Lua Instruction Interpreter")
        parts.append("-- Generated by lua_obfuscator")
        parts.append("-- =========================================")
        parts.append("")
        parts.append(f"local _DEBUG = {'true' if self.include_debug else 'false'}")
        parts.append("")

        parts.append(self._generate_header())
        parts.append("")

        parts.append(self._generate_instruction_section(instructions, code_var))
        parts.append("")

        parts.append(self._generate_state_section(state_var))
        parts.append("")

        parts.append(self.executor_gen.generate())

        return "\n".join(parts)

    def _generate_header(self) -> str:
        return f"""-- Compact Format: {self.format_type}
-- Encoding: opcode_id (integer) + args
-- Opcode count: {len(OpCodeEncoding.OPCODE_TO_ID)}"""

    def _generate_instruction_section(
        self,
        instructions: list[Instruction],
        code_var: str
    ) -> str:
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Compact Instructions")
        lines.append("-- =========================================")

        if self.format_type == "flat":
            lines.append(self.serializer.serialize_compact(instructions))
        elif self.format_type == "stream":
            lines.append(self.serializer.serialize_stream(instructions))
        else:
            lines.append(self.serializer.serialize_compact(instructions))

        return "\n".join(lines)

    def _generate_state_section(self, state_var: str) -> str:
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Execution State")
        lines.append("-- =========================================")
        lines.append(f"local {state_var} = {{")
        lines.append("    locals = {},")
        lines.append("    globals = {},")
        lines.append("    stack = {},")
        lines.append("    pc = 1,")
        lines.append("    halted = false,")
        lines.append("    return_value = nil,")
        lines.append("}")
        return "\n".join(lines)

    def generate_minimal(self, instructions: list[Instruction]) -> str:
        """最小化生成"""
        encoded = self.encoder.encode_flat(instructions)

        parts = []
        parts.append("-- Compact VM")
        parts.append(self.serializer.serialize_minimal(instructions))
        parts.append("local s={l={},g={},p=1,h=false,r=nil}")
        parts.append(self._generate_minimal_executor())
        parts.append("return __run__()")

        return "\n".join(parts)

    def _generate_minimal_executor(self) -> str:
        return """local function __run__()
    local pc=1
    while pc and not s.halted do
        local c=code[pc]
        if not c then break end
        pc=pc+1
    end
    return s.r
end"""


# ===== 紧凑格式发射器 =====


class CompactLuaProgramEmitter(LuaProgramEmitter):
    """
    紧凑 Lua 程序发射器

    使用紧凑编码格式。
    """

    def __init__(
        self,
        format_type: str = "flat",
        use_pool_refs: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.format_type = format_type
        self.use_pool_refs = use_pool_refs
        self.compact_generator: CompactLuaProgramGenerator | None = None

    def emit_compact_instruction_table(
        self,
        instructions: list[Instruction],
        code_var: str = "code"
    ) -> str:
        """生成紧凑指令表"""
        encoder = CompactEncoder(use_pool_refs=self.use_pool_refs)
        serializer = CompactSerializer(encoder, var_name=code_var)

        lines = []
        lines.append("-- =========================================")
        lines.append("-- Compact Instruction Table")
        lines.append(f"-- Format: {self.format_type}")
        lines.append("-- =========================================")

        if self.format_type == "flat":
            lines.append(serializer.serialize_compact(instructions))
        elif self.format_type == "stream":
            lines.append(serializer.serialize_stream(instructions))
        else:
            lines.append(serializer.serialize_compact(instructions))

        return "\n".join(lines)

    def emit_decoder(self) -> str:
        """生成解码器"""
        decoder_gen = LuaCompactDecoderGenerator(self.format_type)
        return decoder_gen.generate()

    def emit_complete_compact_program(
        self,
        instructions: list[Instruction] | None = None,
        **kwargs
    ) -> str:
        """生成完整紧凑程序"""
        parts = []

        parts.append("-- =========================================")
        parts.append("-- Compact Lua Instruction Interpreter")
        parts.append("-- Generated by lua_obfuscator")
        parts.append("-- =========================================")
        parts.append("")
        parts.append(f"local _DEBUG = {'true' if self.include_debug else 'false'}")
        parts.append("")

        if instructions:
            parts.append(self.emit_compact_instruction_table(instructions))

        parts.append(self.emit_execution_state())

        parts.append("")
        parts.append(self.emit_decoder())

        parts.append("")
        parts.append(self.emit_handler_module())

        parts.append("")
        parts.append(self.emit_executor_loop())

        if instructions:
            parts.append(self.emit_runner())

        return "\n".join(parts)


# ===== 便捷函数 =====


def create_compact_encoder(use_pool_refs: bool = False) -> CompactEncoder:
    """创建紧凑编码器"""
    return CompactEncoder(use_pool_refs=use_pool_refs)


def serialize_compact(
    instructions: list[Instruction],
    format_type: str = "flat",
    var_name: str = "code"
) -> str:
    """便捷序列化函数"""
    encoder = CompactEncoder()
    serializer = CompactSerializer(encoder, var_name=var_name)

    if format_type == "stream":
        return serializer.serialize_stream(instructions)
    return serializer.serialize_compact(instructions)


def generate_compact_program(
    instructions: list[Instruction],
    format_type: str = "flat",
    include_handlers: bool = True
) -> str:
    """生成完整紧凑程序"""
    generator = CompactLuaProgramGenerator(
        format_type=format_type,
        include_debug=False
    )
    return generator.generate(instructions)


def demo_consistency_checks():
    """
    演示运行时一致性检查功能（轻量级）
    """
    print("=" * 70)
    print("Runtime Consistency Check Demo (Lightweight)")
    print("=" * 70)

    # 创建发射器
    emitter = LuaProgramEmitter()

    print("\n[1] Consistency Check Module:")
    print("-" * 50)
    check_module = emitter.emit_consistency_check_module(
        code_var="code",
        state_var="state",
        handlers_var="handlers",
        pool_var="pool",
        check_on_start=True,
        check_on_execute=True,
        check_interval=50
    )
    print(check_module)

    print("\n[2] Consistency Guards:")
    print("-" * 50)
    guards = emitter.emit_consistency_guards(
        code_var="code",
        state_var="state"
    )
    print(guards)

    print("\n[3] Executor with Consistency Checks:")
    print("-" * 50)
    executor = emitter.emit_executor_with_consistency(
        code_var="code",
        state_var="state",
        include_guards=True,
        check_interval=10
    )
    print(executor)

    print("\n" + "=" * 70)
    print("Consistency Check Features (Lightweight):")
    print("  - _chk_compute(): Simple checksum for tables")
    print("  - _chk_handlers(): Handlers table checksum")
    print("  - _chk_pool(): Constant pool checksum (optional)")
    print("  - _chk_validate(): Main validation function")
    print("  - _chk_checkpoint(): Periodic runtime checkpoint")
    print("  - _chk_state(): State table validation")
    print("  - _chk_instr(): Instruction format validation")
    print("  - _chk_pc(): PC range validation")
    print("")
    print("No external libraries required!")
    print("=" * 70)


def demo_integrity_validation():
    """演示运行时完整性校验功能"""
    print("=" * 70)
    print("Runtime Integrity Validation Demo")
    print("=" * 70)

    # 示例指令序列
    instructions = [
        Instruction(OpCode.INIT, ["x"], None, "10"),
        Instruction(OpCode.INIT, ["y"], None, "20"),
        Instruction(OpCode.ASSIGN, ["sum"], None, "x + y"),
        Instruction(OpCode.RETURN_VAL, ["sum"]),
    ]

    print("\n[1] Original Instructions:")
    print("-" * 50)
    for i, instr in enumerate(instructions):
        print(f"  [{i}] {instr}")

    # 生成带完整性校验的完整程序
    print("\n[2] Generated Lua Program with Integrity Validation:")
    print("-" * 50)
    lua_code = emit_lua_program_with_integrity(
        instructions=instructions,
        include_debug=True,
        enable_periodic_check=True,
        check_interval=2,  # 每2条指令检查一次
    )
    print(lua_code)

    # 仅生成校验模块（用于集成到现有程序）
    print("\n[3] Integrity Module Only (for integration):")
    print("-" * 50)
    integrity_module = emit_integrity_module_only(
        code_var="code",
        state_var="state",
        check_interval=50,
    )
    print(integrity_module)

    print("\n" + "=" * 70)
    print("Integrity Validation Features:")
    print("  - _int_hash(): Simple hash function for integrity checks")
    print("  - _int_table_signature(): Calculate structural signature")
    print("  - _int_validate(): Main validation (length + signature)")
    print("  - _int_init(): Initialize expected values")
    print("  - _int_check(): Periodic integrity check during execution")
    print("=" * 70)


def demo_diversity_generation():
    """演示结构多样性生成功能"""
    print("=" * 70)
    print("Code Structure Diversity Generation Demo")
    print("=" * 70)

    # 示例指令序列
    instructions = [
        Instruction(OpCode.INIT, ["x"], None, "10"),
        Instruction(OpCode.INIT, ["y"], None, "20"),
        Instruction(OpCode.ASSIGN, ["sum"], None, "x + y"),
        Instruction(OpCode.RETURN_VAL, ["sum"]),
    ]

    print("\n[1] Original Instructions:")
    print("-" * 50)
    for i, instr in enumerate(instructions):
        print(f"  [{i}] {instr}")

    # 生成标准版本
    print("\n[2] Standard Version (no diversification):")
    print("-" * 50)
    standard_code = emit_lua_program(instructions, include_debug=False)
    print(standard_code[:1500] + "...\n")

    # 生成多样性版本 1
    print("\n[3] Diverse Version 1 (seed=1001):")
    print("-" * 50)
    diverse_code_1 = emit_diverse_lua_program(
        instructions,
        include_debug=False,
        diversity_level=0.8,
        seed=1001,
    )
    print(diverse_code_1[:1500] + "...\n")

    # 生成多样性版本 2 (不同 seed)
    print("\n[4] Diverse Version 2 (seed=2002):")
    print("-" * 50)
    diverse_code_2 = emit_diverse_lua_program(
        instructions,
        include_debug=False,
        diversity_level=0.8,
        seed=2002,
    )
    print(diverse_code_2[:1500] + "...\n")

    # 显示差异
    print("\n[5] Structural Differences:")
    print("-" * 50)
    print(f"Standard version length: {len(standard_code)} chars")
    print(f"Diverse version 1 length: {len(diverse_code_1)} chars")
    print(f"Diverse version 2 length: {len(diverse_code_2)} chars")
    print(f"Version 1 != Version 2: {diverse_code_1 != diverse_code_2}")
    print(f"Standard != Version 1: {standard_code != diverse_code_1}")

    print("\n" + "=" * 70)
    print("Diversity Features:")
    print("  - HandlerExpressionStrategy: Multiple expression variants")
    print("  - UtilityFunctionStrategy: Alternative utility implementations")
    print("  - VariableNamingStrategy: Different variable naming pools")
    print("  - SerializationStrategy: Various serialization formats")
    print("  - DispatcherStrategy: Different dispatch patterns")
    print("  - LoopStructureStrategy: Alternative loop structures")
    print("=" * 70)


def demo_compact_encoding():
    """演示紧凑编码"""
    print("=" * 60)
    print("Compact Encoding Demo")
    print("=" * 60)

    instructions = [
        Instruction(OpCode.INIT, ["x"], None, "10"),
        Instruction(OpCode.INIT, ["y"], None, "20"),
        Instruction(OpCode.ASSIGN, ["sum"], None, "x + y"),
        Instruction(OpCode.RETURN_VAL, ["sum"]),
    ]

    print("\n[1] Original Instructions:")
    print("-" * 40)
    for i, instr in enumerate(instructions):
        print(f"  [{i}] {instr}")

    print("\n[2] Opcode Encoding:")
    print("-" * 40)
    for instr in instructions:
        opcode_id = OpCodeEncoding.encode(instr.op)
        print(f"  {instr.op.value} -> {opcode_id}")

    print("\n[3] Flat Format (default):")
    print("-" * 40)
    encoder = CompactEncoder()
    serializer = CompactSerializer(encoder)
    print(serializer.serialize_compact(instructions))

    print("\n[4] Stream Format:")
    print("-" * 40)
    print(serializer.serialize_stream(instructions, items_per_line=9))

    print("\n[5] Minimal Format:")
    print("-" * 40)
    print(serializer.serialize_minimal(instructions))

    print("\n[6] Lua Decoder:")
    print("-" * 40)
    decoder_gen = LuaCompactDecoderGenerator()
    print(decoder_gen.generate())

    print("\n[7] Complete Compact Program:")
    print("-" * 40)
    generator = CompactLuaProgramGenerator(format_type="flat")
    print(generator.generate(instructions))

    print("\n" + "=" * 60)
    print("Demo Complete")
    print("=" * 60)


if __name__ == "__main__":
    demo_compact_encoding()


# ===== 便捷函数 =====


def create_string_fragment_pool(
    rng: random.Random | None = None,
    enable_segmentation: bool = True,
    min_fragment: int = 2,
    max_fragment: int = 8,
) -> StringFragmentPool:
    """
    创建字符串分段存储池

    Args:
        rng: 随机数生成器
        enable_segmentation: 是否启用分段
        min_fragment: 最小片段长度
        max_fragment: 最大片段长度

    Returns:
        StringFragmentPool 实例
    """
    return StringFragmentPool(
        rng=rng,
        enable_segmentation=enable_segmentation,
        min_fragment_length=min_fragment,
        max_fragment_length=max_fragment,
    )


def generate_segmented_strings(
    strings: list[str],
    rng: random.Random | None = None,
    enable_segmentation: bool = True,
) -> tuple[str, dict]:
    """
    生成带分段的字符串常量代码

    Args:
        strings: 字符串列表
        rng: 随机数生成器
        enable_segmentation: 是否启用分段

    Returns:
        (lua_code, statistics) 元组
    """
    pool = create_string_fragment_pool(rng=rng, enable_segmentation=enable_segmentation)

    for s in strings:
        pool.intern_string(s)

    code = pool.generate_lua_pool()
    stats = pool.get_statistics()

    return code, stats


def demo_string_fragmentation():
    """演示字符串分段存储与还原"""
    print("=" * 70)
    print("String Fragmentation & Recovery Demo")
    print("=" * 70)

    # 测试字符串
    test_strings = [
        "HelloWorld",
        "LuaObfuscator",
        "ConstantPool",
        "Fragmentation",
        "RuntimeRecovery",
        "abc",
        "AB",
    ]

    print("\n[1] Original Strings:")
    print("-" * 50)
    for s in test_strings:
        print(f"  \"{s}\" (length: {len(s)})")

    # 创建池
    rng = random.Random(42)
    pool = StringFragmentPool(
        rng=rng,
        enable_segmentation=True,
        min_fragment_length=2,
        max_fragment_length=6,
    )

    print("\n[2] Fragmented Strings:")
    print("-" * 50)
    for s in test_strings:
        idx = pool.intern_string(s)
        fragments = pool.get_fragments(idx)
        strategy = pool.get_strategy(idx)
        print(f"  [{idx}] \"{s}\" -> {fragments} (strategy: {strategy})")

    print("\n[3] Generated Lua Pool Code:")
    print("-" * 50)
    print(pool.generate_lua_pool())

    print("\n[4] Recovery Expressions:")
    print("-" * 50)
    for idx in sorted(pool.idx_to_fragments.keys()):
        expr = pool.generate_recovery_function(idx)
        print(f"  [{idx}] -> {expr}")

    print("\n[5] Statistics:")
    print("-" * 50)
    stats = pool.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n[6] Enhanced String Constants (Complete Module):")
    print("-" * 50)
    esc = EnhancedStringConstants(rng=random.Random(123), enable_segmentation=True)
    for s in test_strings[:4]:
        esc.add_string(s)
    print(esc.generate_lua_code())

    print("\n" + "=" * 70)
    print("Fragmentation Strategies:")
    print("  - concatenation: Simple frag1..frag2..frag3")
    print("  - table_builder: Build table then concat")
    print("  - chunk_mapping: Use mapping table")
    print("  - incremental: Build incrementally")
    print("  - reverse: Reverse concatenation")
    print("=" * 70)


# =============================================================================
# 模块化 Lua 程序生成器
# 整合分散的生成逻辑，提供清晰的模块化输出
# =============================================================================

class LuaProgramGenerator:
    """
    模块化 Lua 程序生成器

    将生成的 Lua 代码按层划分为:
    - 数据层: instruction 数据 (code)、常量池 (const_pool)
    - 解析层: decode / 辅助函数
    - 执行层: handlers (指令处理函数)
    - 调度层: 执行循环 (pc + dispatch)

    提供清晰的模块化输出和统一的整合接口。
    """

    def __init__(
        self,
        serializer: InstructionSerializer | None = None,
        handler_generator: LuaHandlerGenerator | None = None,
        include_comments: bool = True,
        include_debug: bool = False,
        enable_consistency_check: bool = False,
        check_interval: int = 50
    ):
        self.serializer = serializer or InstructionSerializer(compact=True)
        self.handler_generator = handler_generator or LuaHandlerGenerator(include_comments=include_comments)
        self.include_comments = include_comments
        self.include_debug = include_debug
        self.enable_consistency_check = enable_consistency_check
        self.check_interval = check_interval

        # 子发射器
        self._emitter = LuaProgramEmitter(
            serializer=self.serializer,
            handler_generator=self.handler_generator,
            include_comments=include_comments,
            include_debug=include_debug
        )

    # ===== 数据层 =====

    def emit_code(
        self,
        instructions: list[Instruction],
        var_name: str = "code"
    ) -> str:
        """
        [数据层] 生成 instruction 数据表

        Args:
            instructions: 指令列表
            var_name: 变量名

        Returns:
            Lua 代码字符串
        """
        return self._emitter.emit_instruction_table(instructions, var_name)

    def emit_const_pool(
        self,
        constants: list[Any] | None = None,
        var_name: str = "const_pool"
    ) -> str:
        """
        [数据层] 生成常量池

        Args:
            constants: 常量列表
            var_name: 变量名

        Returns:
            Lua 代码字符串
        """
        if not constants:
            return f"local {var_name} = {{}}"

        lines = []
        lines.append("-- =========================================")
        lines.append("-- Constant Pool")
        lines.append("-- =========================================")
        lines.append(f"local {var_name} = {{")

        for i, const in enumerate(constants):
            if isinstance(const, str):
                escaped = const.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'    [{i+1}] = "{escaped}",')
            elif isinstance(const, (int, float)):
                lines.append(f"    [{i+1}] = {const},")
            elif const is None:
                lines.append(f"    [{i+1}] = nil,")
            elif const is True:
                lines.append(f"    [{i+1}] = true,")
            elif const is False:
                lines.append(f"    [{i+1}] = false,")
            else:
                lines.append(f"    [{i+1}] = {repr(const)},")

        lines.append("}")
        return "\n".join(lines)

    # ===== 解析层 =====

    def emit_decode(
        self,
        include_utility: bool = True
    ) -> str:
        """
        [解析层] 生成解码/辅助函数

        Args:
            include_utility: 是否包含工具函数

        Returns:
            Lua 代码字符串
        """
        if include_utility:
            return self.handler_generator.generate_utility_functions()
        return ""

    def emit_helper_functions(
        self,
        helpers: list[str] | None = None
    ) -> str:
        """
        [解析层] 生成自定义辅助函数

        Args:
            helpers: 辅助函数代码列表

        Returns:
            Lua 代码字符串
        """
        if not helpers:
            return ""

        lines = []
        lines.append("-- =========================================")
        lines.append("-- Helper Functions")
        lines.append("-- =========================================")
        lines.append("")
        for h in helpers:
            lines.append(h)
            lines.append("")
        return "\n".join(lines)

    # ===== 执行层 =====

    def emit_handlers(
        self,
        templates: dict[int, dict[str, str]] | None = None,
        use_layered: bool = False
    ) -> str:
        """
        [执行层] 生成 handlers (指令处理函数)

        Args:
            templates: handler 模板字典
            use_layered: 是否使用分层方式生成

        Returns:
            Lua 代码字符串
        """
        if templates is None:
            templates = self.handler_generator.HANDLER_TEMPLATES

        if use_layered:
            layered_gen = LayeredHandlerGenerator(include_comments=self.include_comments)
            return layered_gen.generate_all_handlers(templates, use_layered=True)

        lines = []
        lines.append("-- =========================================")
        lines.append("-- Instruction Handlers")
        lines.append("-- =========================================")
        lines.append("")

        if self.include_comments:
            lines.append(self.handler_generator.generate_utility_functions())
            lines.append("")

        lines.append("local handlers = {")

        for opcode in sorted(templates.keys()):
            template = templates[opcode]
            desc = template.get("desc", "")
            template_code = template.get("template", "")

            if self.include_comments:
                lines.append(f"    -- opcode: {opcode} ({desc})")
            lines.append(f"    {template_code.strip()},")

        lines.append("")
        lines.append("    -- Default handler")
        lines.append("    default = function(instr, state, pc)")
        lines.append("        if _DEBUG then")
        lines.append("            print('Unknown opcode: ' .. tostring(instr[1]))")
        lines.append("        end")
        lines.append("        return pc + 1")
        lines.append("    end,")
        lines.append("}")

        return "\n".join(lines)

    # ===== 调度层 =====

    def emit_dispatch_loop(
        self,
        code_var: str = "code",
        state_var: str = "state",
        function_name: str = "dispatch",
        include_bounds_check: bool = True
    ) -> str:
        """
        [调度层] 生成执行循环

        Args:
            code_var: 代码变量名
            state_var: 状态变量名
            function_name: 函数名
            include_bounds_check: 是否包含边界检查

        Returns:
            Lua 代码字符串
        """
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Execution Loop (Dispatch Layer)")
        lines.append("-- =========================================")
        lines.append("")

        lines.append(f"local function {function_name}({code_var}, {state_var})")
        lines.append(f"    local pc = 1")
        lines.append(f"    while pc and not {state_var}.halted do")
        lines.append(f"        local instr = {code_var}[pc]")
        lines.append("        if not instr then break end")
        lines.append(f"        local op = instr[1]")
        lines.append("        local handler = handlers[op] or handlers.default")
        lines.append(f"        pc = handler(instr, {state_var}, pc)")

        if include_bounds_check:
            lines.append("        if not pc then break end")
            lines.append(f"        if pc < 1 or pc > #{code_var} + 1 then break end")

        lines.append("    end")
        lines.append(f"    return {state_var}.return_value")
        lines.append("end")

        return "\n".join(lines)

    def emit_execute_wrapper(
        self,
        code_var: str = "code",
        state_var: str = "state",
        result_var: str = "_result",
        execute_func: str = "execute"
    ) -> str:
        """
        [调度层] 生成执行包装器

        Args:
            code_var: 代码变量名
            state_var: 状态变量名
            result_var: 结果变量名
            execute_func: 执行函数名

        Returns:
            Lua 代码字符串
        """
        lines = []
        lines.append("-- =========================================")
        lines.append("-- Execute Wrapper")
        lines.append("-- =========================================")
        lines.append("")

        lines.append(f"local function {execute_func}({code_var}, {state_var})")
        lines.append(f"    return {execute_func}_dispatch({code_var}, {state_var})")
        lines.append("end")
        lines.append("")

        lines.append(f"local {result_var} = {execute_func}({code_var}, {state_var})")

        if self.include_debug:
            lines.append(f'if _DEBUG then print("Result: " .. tostring({result_var})) end')

        return "\n".join(lines)

    # ===== 一致性检查 =====

    def emit_consistency_check(
        self,
        code_var: str = "code",
        state_var: str = "state"
    ) -> str:
        """
        [可选] 生成一致性检查模块

        Args:
            code_var: 代码变量名
            state_var: 状态变量名

        Returns:
            Lua 代码字符串
        """
        if not self.enable_consistency_check:
            return ""

        return self._emitter.emit_consistency_check_module(
            code_var=code_var,
            state_var=state_var,
            check_on_start=True,
            check_on_execute=True,
            check_interval=self.check_interval
        )

    # ===== 状态生成 =====

    def emit_state(
        self,
        var_name: str = "state"
    ) -> str:
        """
        [数据层] 生成执行状态

        Args:
            var_name: 状态变量名

        Returns:
            Lua 代码字符串
        """
        return self._emitter.emit_execution_state(var_name)

    # ===== 整合输出 =====

    def emit_lua_program(
        self,
        instructions: list[Instruction] | None = None,
        constants: list[Any] | None = None,
        helper_functions: list[str] | None = None,
        code_var: str = "code",
        state_var: str = "state",
        pool_var: str = "const_pool",
        execute_func: str = "execute",
        result_var: str = "_result",
        include_dispatch: bool = True,
        include_state: bool = True,
        include_execute_wrapper: bool = True,
        include_consistency_check: bool | None = None,
        use_layered_handlers: bool = False
    ) -> str:
        """
        统一整合函数：按层组装完整 Lua 程序

        按顺序输出:
        1. 头部注释和调试开关
        2. [数据层] instruction 数据表 (code)
        3. [数据层] 常量池 (const_pool)
        4. [数据层] 执行状态 (state)
        5. [解析层] 辅助函数
        6. [执行层] handlers
        7. [调度层] dispatch + 执行循环
        8. [可选] 一致性检查

        Args:
            instructions: 指令列表
            constants: 常量列表
            helper_functions: 自定义辅助函数
            code_var: 代码变量名
            state_var: 状态变量名
            pool_var: 常量池变量名
            execute_func: 执行函数名
            result_var: 结果变量名
            include_dispatch: 是否包含 dispatch
            include_state: 是否包含 state
            include_execute_wrapper: 是否包含执行包装
            include_consistency_check: 是否包含一致性检查
            use_layered_handlers: 是否使用分层 handlers

        Returns:
            完整的 Lua 程序字符串
        """
        parts = []

        # === 1. 头部 ===
        header = []
        header.append("--" + "=" * 50)
        header.append("-- Lua Program (Modular Generator)")
        header.append("-- Generated by lua_obfuscator")
        header.append("--" + "=" * 50)
        header.append("")
        header.append(f"local _DEBUG = {'true' if self.include_debug else 'false'}")
        parts.append("\n".join(header))

        # === 2. 数据层: instruction 数据表 ===
        if instructions:
            parts.append(self.emit_code(instructions, code_var))
            parts.append("")

        # === 3. 数据层: 常量池 ===
        if constants:
            parts.append(self.emit_const_pool(constants, pool_var))
            parts.append("")

        # === 4. 数据层: 执行状态 ===
        if include_state:
            parts.append(self.emit_state(state_var))
            parts.append("")

        # === 5. 解析层: 辅助函数 ===
        decode_code = self.emit_decode(include_utility=True)
        if decode_code:
            parts.append(decode_code)
            parts.append("")

        if helper_functions:
            parts.append(self.emit_helper_functions(helper_functions))
            parts.append("")

        # === 6. 执行层: handlers ===
        parts.append(self.emit_handlers(use_layered=use_layered_handlers))
        parts.append("")

        # === 7. 调度层: dispatch + 执行循环 ===
        if include_dispatch:
            parts.append(self.emit_dispatch_loop(
                code_var, state_var,
                function_name=f"{execute_func}_dispatch",
                include_bounds_check=True
            ))
            parts.append("")

            if include_execute_wrapper and instructions:
                parts.append(self.emit_execute_wrapper(
                    code_var, state_var,
                    result_var, execute_func
                ))
                parts.append("")

        # === 8. 可选: 一致性检查 ===
        check = include_consistency_check if include_consistency_check is not None else self.enable_consistency_check
        if check:
            parts.append(self.emit_consistency_check(code_var, state_var))
            parts.append("")

        return "\n\n".join(parts)

    # ===== 便捷方法 =====

    def emit_minimal(self, instructions: list[Instruction]) -> str:
        """
        生成最小化 Lua 程序（仅核心部分）

        Args:
            instructions: 指令列表

        Returns:
            Lua 代码字符串
        """
        return self.emit_lua_program(
            instructions=instructions,
            include_state=True,
            include_execute_wrapper=True,
            include_consistency_check=False
        )

    def emit_full(self, instructions: list[Instruction], constants: list[Any] | None = None) -> str:
        """
        生成完整 Lua 程序（包含所有模块）

        Args:
            instructions: 指令列表
            constants: 常量列表

        Returns:
            Lua 代码字符串
        """
        return self.emit_lua_program(
            instructions=instructions,
            constants=constants,
            include_state=True,
            include_execute_wrapper=True,
            include_consistency_check=self.enable_consistency_check
        )

    def emit_debug(self, instructions: list[Instruction]) -> str:
        """
        生成带调试信息的 Lua 程序

        Args:
            instructions: 指令列表

        Returns:
            Lua 代码字符串
        """
        old_debug = self.include_debug
        self.include_debug = True
        result = self.emit_minimal(instructions)
        self.include_debug = old_debug
        return result

    def emit_layered(self, instructions: list[Instruction]) -> str:
        """
        使用分层架构生成 Lua 程序

        Args:
            instructions: 指令列表

        Returns:
            Lua 代码字符串
        """
        return self.emit_lua_program(
            instructions=instructions,
            use_layered_handlers=True,
            include_consistency_check=False
        )

    def emit_with_checks(self, instructions: list[Instruction]) -> str:
        """
        启用一致性检查生成 Lua 程序

        Args:
            instructions: 指令列表

        Returns:
            Lua 代码字符串
        """
        return self.emit_lua_program(
            instructions=instructions,
            include_consistency_check=True
        )


# =============================================================================
# 便捷函数
# =============================================================================

def emit_lua_program(
    instructions: list[Instruction] | None = None,
    constants: list[Any] | None = None,
    include_debug: bool = False,
    enable_consistency_check: bool = False,
    check_interval: int = 50,
    minimal: bool = False
) -> str:
    """
    便捷函数：生成模块化 Lua 程序

    Args:
        instructions: 指令列表
        constants: 常量列表
        include_debug: 是否包含调试信息
        enable_consistency_check: 是否启用一致性检查
        check_interval: 检查间隔
        minimal: 是否生成最小版本

    Returns:
        Lua 代码字符串
    """
    gen = LuaProgramGenerator(
        include_debug=include_debug,
        enable_consistency_check=enable_consistency_check,
        check_interval=check_interval
    )

    if minimal:
        if instructions:
            return gen.emit_minimal(instructions)
        return ""

    return gen.emit_full(instructions, constants)


def emit_layered_lua_program(instructions: list[Instruction]) -> str:
    """
    便捷函数：使用分层架构生成 Lua 程序

    Args:
        instructions: 指令列表

    Returns:
        Lua 代码字符串
    """
    gen = LuaProgramGenerator()
    return gen.emit_layered(instructions)


def emit_debug_lua_program(instructions: list[Instruction]) -> str:
    """
    便捷函数：生成带调试信息的 Lua 程序

    Args:
        instructions: 指令列表

    Returns:
        Lua 代码字符串
    """
    gen = LuaProgramGenerator(include_debug=True)
    return gen.emit_minimal(instructions)


def emit_checked_lua_program(
    instructions: list[Instruction],
    check_interval: int = 50
) -> str:
    """
    便捷函数：生成带一致性检查的 Lua 程序

    Args:
        instructions: 指令列表
        check_interval: 检查间隔

    Returns:
        Lua 代码字符串
    """
    gen = LuaProgramGenerator(
        enable_consistency_check=True,
        check_interval=check_interval
    )
    return gen.emit_minimal(instructions)


# =============================================================================
# 更新主入口函数
# =============================================================================

def transform_v5(source: str, watermark: str) -> str:
    """
    使用模块化生成器的 transform 函数

    Args:
        source: 源代码
        watermark: 水印

    Returns:
        混淆后的 Lua 代码
    """
    # 注意: 如果需要完整流程，请使用 transform_v3/v4
    # 这里仅演示模块化生成器的使用方式
    # 实际项目中应导入 parser, ir, optimizer, codegen 模块

    # 预留接口 - 实际使用时替换为:
    # from .parser import parse_lua
    # from .ir import build_ir
    # from .optimizer import optimize_ir
    # from .codegen import generate_instructions

    # ast = parse_lua(source)
    # ir = build_ir(ast, watermark=watermark)
    # optimized = optimize_ir(ir)
    # instructions = generate_instructions(optimized)

    # 占位：返回空程序（实际使用时删除此行）
    return "-- Placeholder: Use transform_v3 or transform_v4 for full pipeline"


# 更新主入口
def transform(source: str, watermark: str) -> str:
    """
    主入口函数，使用模块化 Lua 程序生成器

    Args:
        source: 源代码
        watermark: 水印

    Returns:
        混淆后的 Lua 代码
    """
    return transform_v5(source, watermark)


def demo_modular_lua_generator():
    """
    演示模块化 Lua 程序生成器
    """
    print("=" * 70)
    print("Modular Lua Program Generator Demo")
    print("=" * 70)

    # 创建示例指令
    instructions = [
        Instruction(OpCode.INIT, ["x"], None, "10"),
        Instruction(OpCode.INIT, ["y"], None, "20"),
        Instruction(OpCode.ASSIGN, ["sum"], None, "x + y"),
        Instruction(OpCode.RETURN_VAL, ["sum"]),
    ]

    constants = ["Hello", "World", 42, True]

    print("\n[1] 指令列表:")
    print("-" * 50)
    for i, instr in enumerate(instructions):
        print(f"  [{i}] {instr}")

    # === 模块化生成器 ===
    gen = LuaProgramGenerator(include_debug=True)

    print("\n[2] 数据层: emit_code:")
    print("-" * 50)
    print(gen.emit_code(instructions))

    print("\n[3] 数据层: emit_const_pool:")
    print("-" * 50)
    print(gen.emit_const_pool(constants))

    print("\n[4] 解析层: emit_decode:")
    print("-" * 50)
    print(gen.emit_decode()[:500] + "...")

    print("\n[5] 执行层: emit_handlers:")
    print("-" * 50)
    print(gen.emit_handlers()[:600] + "...")

    print("\n[6] 调度层: emit_dispatch_loop:")
    print("-" * 50)
    print(gen.emit_dispatch_loop())

    print("\n[7] 统一整合: emit_lua_program (minimal):")
    print("-" * 50)
    print(gen.emit_minimal(instructions))

    print("\n[8] 统一整合: emit_lua_program (full):")
    print("-" * 50)
    print(gen.emit_full(instructions, constants))

    print("\n[9] 统一整合: emit_lua_program (with checks):")
    print("-" * 50)
    gen_check = LuaProgramGenerator(enable_consistency_check=True, check_interval=10)
    print(gen_check.emit_minimal(instructions))

    print("\n[10] 便捷函数:")
    print("-" * 50)
    print("emit_lua_program():")
    print(emit_lua_program(instructions, constants, minimal=True)[:400] + "...")

    print("\n" + "=" * 70)
    print("Module Structure:")
    print("  [数据层] emit_code()      - instruction 数据表")
    print("  [数据层] emit_const_pool() - 常量池")
    print("  [数据层] emit_state()     - 执行状态")
    print("  [解析层] emit_decode()    - 辅助函数")
    print("  [解析层] emit_helper_functions() - 自定义辅助函数")
    print("  [执行层] emit_handlers()  - 指令处理函数")
    print("  [调度层] emit_dispatch_loop() - 执行循环")
    print("  [调度层] emit_execute_wrapper() - 执行包装")
    print("  [可选] emit_consistency_check() - 一致性检查")
    print("=" * 70)


if __name__ == "__main__":
    demo_modular_lua_generator()


# =============================================================================
# 多策略生成系统 (Polymorphic Code Generation Pipeline)
# 同一输入可产生结构不同但语义一致的 Lua 输出
# =============================================================================

from typing import Protocol, TypeVar, Generic
from abc import ABC, abstractmethod


# =============================================================================
# 策略系统基础架构
# =============================================================================

class StrategyCategory(Enum):
    """策略类别枚举"""
    INSTRUCTION_ENCODING = "instruction_encoding"  # 指令编码策略
    HANDLER_STRUCTURE = "handler_structure"         # Handler 结构策略
    EXPRESSION_VARIATION = "expression_variation"  # 表达式变化策略
    EXECUTION_DISPATCH = "execution_dispatch"      # 执行调度策略
    STATE_MANAGEMENT = "state_management"           # 状态管理策略
    CONTROL_FLOW = "control_flow"                   # 控制流策略


class GenerationContext:
    """
    生成上下文

    在策略之间传递共享信息
    """

    def __init__(
        self,
        rng: random.Random | None = None,
        seed: int | None = None,
        enabled_strategies: set[StrategyCategory] | None = None
    ):
        self.rng = rng or random.Random(seed)
        self.seed = seed
        self.enabled_strategies = enabled_strategies or set(StrategyCategory)

        # 生成的代码数据
        self.instruction_data: list[Instruction] = []
        self.handler_templates: dict[int, dict[str, str]] = {}
        self.utility_functions: list[str] = []
        self.constant_pool: list[Any] = []

        # 统计信息
        self.stats: dict[str, int] = {}

    def is_enabled(self, category: StrategyCategory) -> bool:
        """检查策略类别是否启用"""
        return category in self.enabled_strategies

    def record_choice(self, category: StrategyCategory, choice: str) -> None:
        """记录策略选择"""
        key = category.value
        if key not in self.stats:
            self.stats[key] = {}
        choices = self.stats[key]
        choices[choice] = choices.get(choice, 0) + 1


# =============================================================================
# 统一策略接口
# =============================================================================

T = TypeVar('T')


class CodeGenerationStrategy(ABC, Generic[T]):
    """
    代码生成策略基类

    定义所有策略的通用接口
    """

    category: StrategyCategory

    @abstractmethod
    def apply(self, context: GenerationContext, data: Any = None) -> T:
        """
        应用策略

        Args:
            context: 生成上下文
            data: 输入数据

        Returns:
            策略生成的结果
        """
        pass

    @abstractmethod
    def get_variants(self) -> list[str]:
        """获取所有可用的变体"""
        pass

    @abstractmethod
    def select_variant(self, context: GenerationContext) -> str:
        """选择变体"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称"""
        pass

    def is_active(self, context: GenerationContext) -> bool:
        """检查策略是否激活"""
        return context.is_enabled(self.category)


class CompositeStrategy(CodeGenerationStrategy[Any]):
    """
    组合策略

    将多个策略组合成一个策略
    """

    def __init__(self, strategies: list[CodeGenerationStrategy]):
        self.strategies = strategies

    def apply(self, context: GenerationContext, data: Any = None) -> Any:
        result = data
        for strategy in self.strategies:
            if strategy.is_active(context):
                result = strategy.apply(context, result)
        return result

    def get_variants(self) -> list[str]:
        variants = []
        for s in self.strategies:
            variants.extend(s.get_variants())
        return variants

    def select_variant(self, context: GenerationContext) -> str:
        if self.strategies:
            return self.strategies[0].select_variant(context)
        return "none"

    @property
    def name(self) -> str:
        return "composite"


# =============================================================================
# 指令编码策略
# =============================================================================

class InstructionEncodingStrategy(CodeGenerationStrategy[str]):
    """
    指令编码策略

    决定如何编码和表示指令数据
    """

    category = StrategyCategory.INSTRUCTION_ENCODING

    class Variants(Enum):
        COMPACT = "compact"           # 紧凑格式
        VERBOSE = "verbose"           # 详细格式
        NAMED = "named"               # 命名字段
        INDEXED = "indexed"           # 索引格式
        MAPPED = "mapped"             # 映射格式

    def __init__(self, variant: str = "compact"):
        self._variant = variant

    def apply(self, context: GenerationContext, data: Any = None) -> str:
        """编码指令"""
        instructions = context.instruction_data if hasattr(context, 'instruction_data') else []
        variant = self.select_variant(context)

        if variant == "compact":
            return self._encode_compact(instructions)
        elif variant == "verbose":
            return self._encode_verbose(instructions)
        elif variant == "named":
            return self._encode_named(instructions)
        elif variant == "indexed":
            return self._encode_indexed(instructions)
        elif variant == "mapped":
            return self._encode_mapped(instructions)
        return self._encode_compact(instructions)

    def get_variants(self) -> list[str]:
        return [v.value for v in self.Variants]

    def select_variant(self, context: GenerationContext) -> str:
        if self._variant != "random":
            return self._variant
        return context.rng.choice(self.get_variants())

    @property
    def name(self) -> str:
        return f"instruction_encoding:{self._variant}"

    def _encode_compact(self, instructions: list[Instruction]) -> str:
        """紧凑格式"""
        lines = ["local code = {"]
        for instr in instructions:
            fields = ", ".join(str(f) if f is not None else "nil" for f in instr.fields)
            lines.append(f"    {{{fields}}},")
        lines.append("}")
        return "\n".join(lines)

    def _encode_verbose(self, instructions: list[Instruction]) -> str:
        """详细格式"""
        lines = ["local code = {"]
        for i, instr in enumerate(instructions):
            lines.append(f"    -- [{i}] {instr.op}")
            fields = ", ".join(str(f) if f is not None else "nil" for f in instr.fields)
            lines.append(f"    [{i+1}] = {{{fields}}},")
        lines.append("}")
        return "\n".join(lines)

    def _encode_named(self, instructions: list[Instruction]) -> str:
        """命名字段格式"""
        lines = ["local code = {"]
        for i, instr in enumerate(instructions):
            lines.append(f"    -- [{i}] {instr.op}")
            lines.append(f"    [{i+1}] = {{")
            lines.append(f"        op = {instr.op.value if hasattr(instr.op, 'value') else instr.op},")
            for j, f in enumerate(instr.fields):
                lines.append(f"        f{j+1} = {repr(f)},")
            lines.append(f"    }},")
        lines.append("}")
        return "\n".join(lines)

    def _encode_indexed(self, instructions: list[Instruction]) -> str:
        """索引格式"""
        lines = ["local code = { -- indexed format"]
        for i, instr in enumerate(instructions):
            lines.append(f"    [{i+1}] = {{{', '.join(str(f) for f in instr.fields)}}},")
        lines.append("}")
        return "\n".join(lines)

    def _encode_mapped(self, instructions: list[Instruction]) -> str:
        """映射格式"""
        lines = ["local code = { -- mapped format"]
        for i, instr in enumerate(instructions):
            lines.append(f"    [{i+1}] = {{op={instr.op.value if hasattr(instr.op, 'value') else instr.op},")
            for j, f in enumerate(instr.fields):
                lines.append(f"        [{j+2}] = {repr(f)},")
            lines.append("    },")
        lines.append("}")
        return "\n".join(lines)


# =============================================================================
# Handler 结构策略
# =============================================================================

class HandlerStructureStrategy(CodeGenerationStrategy[str]):
    """
    Handler 结构策略

    决定 handler 的内部结构实现方式
    """

    category = StrategyCategory.HANDLER_STRUCTURE

    class Variants(Enum):
        DIRECT = "direct"             # 直接实现
        STEPWISE = "stepwise"         # 分步实现
        TABLE_ASSISTED = "table"      # 表辅助
        FUNCTION_COMPOSED = "composed" # 函数组合
        CLOSURE_BASED = "closure"     # 闭包实现
        LAYERED = "layered"           # 分层实现

    def __init__(self, variant: str = "direct"):
        self._variant = variant

    def apply(self, context: GenerationContext, data: Any = None) -> str:
        """生成 handler 结构"""
        variant = self.select_variant(context)
        templates = context.handler_templates or LuaHandlerGenerator.HANDLER_TEMPLATES

        if variant == "direct":
            return self._generate_direct(templates)
        elif variant == "stepwise":
            return self._generate_stepwise(templates)
        elif variant == "table":
            return self._generate_table_assisted(templates)
        elif variant == "composed":
            return self._generate_composed(templates)
        elif variant == "closure":
            return self._generate_closure(templates)
        elif variant == "layered":
            return self._generate_layered(templates)
        return self._generate_direct(templates)

    def get_variants(self) -> list[str]:
        return [v.value for v in self.Variants]

    def select_variant(self, context: GenerationContext) -> str:
        if self._variant != "random":
            return self._variant
        return context.rng.choice(self.get_variants())

    @property
    def name(self) -> str:
        return f"handler_structure:{self._variant}"

    def _generate_direct(self, templates: dict) -> str:
        """直接实现"""
        lines = ["local handlers = {"]
        for opcode in sorted(templates.keys()):
            t = templates[opcode]
            lines.append(f"    [{opcode}] = function(instr, state, pc)")
            lines.append(f"        {t['template'].strip()}")
            lines.append("    end,")
        lines.append("}")
        return "\n".join(lines)

    def _generate_stepwise(self, templates: dict) -> str:
        """分步实现"""
        lines = ["-- Stepwise handler generation"]
        lines.append("local function make_handler(template)")
        lines.append("    return function(instr, state, pc)")
        lines.append("        -- [PARSE]")
        lines.append("        -- [PROCESS]")
        lines.append("        -- [COMMIT]")
        lines.append("        return (pc + 1)")
        lines.append("    end")
        lines.append("end")
        lines.append("")
        lines.append("local handlers = {")
        for opcode in sorted(templates.keys()):
            lines.append(f"    [{opcode}] = make_handler('{templates[opcode]['desc']}'),")
        lines.append("}")
        return "\n".join(lines)

    def _generate_table_assisted(self, templates: dict) -> str:
        """表辅助"""
        lines = ["-- Table-assisted handler generation"]
        lines.append("local _HANDLER_TABLE = {")
        for opcode in sorted(templates.keys()):
            t = templates[opcode]
            lines.append(f"    [{opcode}] = {{desc='{t['desc']}', template='{t['template']}'}},")
        lines.append("}")
        lines.append("")
        lines.append("local handlers = {")
        lines.append("    __index = function(t, k)")
        lines.append("        local h = _HANDLER_TABLE[k]")
        lines.append("        if h then return function(i,s,p) return (p+1) end end")
        lines.append("    end")
        lines.append("}")
        return "\n".join(lines)

    def _generate_composed(self, templates: dict) -> str:
        """函数组合"""
        lines = ["-- Function-composed handler generation"]
        lines.append("local function parse(instr) return instr end")
        lines.append("local function process(instr, state) return state end")
        lines.append("local function commit(state) return state end")
        lines.append("")
        lines.append("local function compose(...)")
        lines.append("    local funcs = {...}")
        lines.append("    return function(instr, state, pc)")
        lines.append("        for _, f in ipairs(funcs) do f(instr, state) end")
        lines.append("        return pc + 1")
        lines.append("    end")
        lines.append("end")
        lines.append("")
        lines.append("local handlers = {")
        lines.append("    [0] = compose(parse, commit),")
        lines.append("    [3] = compose(parse, process, commit),")
        lines.append("}")
        return "\n".join(lines)

    def _generate_closure(self, templates: dict) -> str:
        """闭包实现"""
        lines = ["-- Closure-based handler generation"]
        lines.append("local function make_closure(pc_offset)")
        lines.append("    local offset = pc_offset")
        lines.append("    return function(instr, state, pc)")
        lines.append("        return pc + offset")
        lines.append("    end")
        lines.append("end")
        lines.append("")
        lines.append("local handlers = {")
        for opcode in sorted(templates.keys()):
            lines.append(f"    [{opcode}] = make_closure(1),")
        lines.append("}")
        return "\n".join(lines)

    def _generate_layered(self, templates: dict) -> str:
        """分层实现"""
        lines = ["-- Layered handler generation"]
        lines.append("local handlers = {")
        for opcode in sorted(templates.keys()):
            t = templates[opcode]
            lines.append(f"    -- [{opcode}] {t['desc']}")
            lines.append(f"    [{opcode}] = function(instr, state, pc)")
            lines.append("        -- [PARSE] extract arguments")
            lines.append("        -- [PROCESS] apply logic")
            lines.append("        -- [COMMIT] update state")
            lines.append("        -- [CONTROL] determine next pc")
            lines.append("        return pc + 1")
            lines.append("    end,")
        lines.append("}")
        return "\n".join(lines)


# =============================================================================
# 表达式变化策略
# =============================================================================

class ExpressionVariationStrategy(CodeGenerationStrategy[str]):
    """
    表达式变化策略

    为同一表达式提供多种等价写法
    """

    category = StrategyCategory.EXPRESSION_VARIATION

    class Variants(Enum):
        DIRECT = "direct"             # 直接写法
        NESTED = "nested"             # 嵌套写法
        TEMP_VAR = "temp_var"         # 临时变量
        TABLE_LOOKUP = "table"        # 表查找

    # 等价表达式变体
    ASSIGNMENT_VARIANTS = [
        "state.locals['{v}'] = {expr}",
        "local _v = {expr}; state.locals['{v}'] = _v",
        "(state.locals['{v}'], _) = ({expr}, nil)",
    ]

    GET_VARIANTS = [
        "state.locals['{v}']",
        "_get(state, '{v}')",
        "(state.locals['{v}'] or state.globals['{v}'])",
    ]

    CONDITION_VARIANTS = [
        "if {cond} then return {t} end; return {f}",
        "return {cond} and {t} or {f}",
        "if not {cond} then return {f} end; return {t}",
    ]

    def __init__(self, variant: str = "direct"):
        self._variant = variant

    def apply(self, context: GenerationContext, data: Any = None) -> str:
        """生成表达式"""
        variant = self.select_variant(context)
        context.record_choice(self.category, variant)

        if isinstance(data, dict):
            expr_type = data.get("type", "assignment")
            if expr_type == "assignment":
                return self._variate_assignment(data, variant, context)
            elif expr_type == "get":
                return self._variate_get(data, variant, context)
            elif expr_type == "condition":
                return self._variate_condition(data, variant, context)
        return "nil"

    def get_variants(self) -> list[str]:
        return [v.value for v in self.Variants]

    def select_variant(self, context: GenerationContext) -> str:
        if self._variant != "random":
            return self._variant
        return context.rng.choice(self.get_variants())

    @property
    def name(self) -> str:
        return f"expression_variation:{self._variant}"

    def _variate_assignment(self, data: dict, variant: str, context: GenerationContext) -> str:
        """变化赋值表达式"""
        v = data.get("var", "x")
        expr = data.get("expr", "42")

        if variant == "direct":
            return f"state.locals['{v}'] = {expr}"
        elif variant == "nested":
            return f"(function() local __v = {expr}; state.locals['{v}'] = __v; return __v end)()"
        elif variant == "temp_var":
            idx = context.rng.randint(0, len(self.ASSIGNMENT_VARIANTS) - 1)
            return self.ASSIGNMENT_VARIANTS[idx].format(v=v, expr=expr)
        else:
            return f"state.locals['{v}'] = {expr}"

    def _variate_get(self, data: dict, variant: str, context: GenerationContext) -> str:
        """变化获取表达式"""
        v = data.get("var", "x")

        if variant == "direct":
            return f"state.locals['{v}']"
        elif variant == "nested":
            return f"(state.locals['{v}'] or error('var not found'))"
        elif variant == "temp_var":
            idx = context.rng.randint(0, len(self.GET_VARIANTS) - 1)
            return self.GET_VARIANTS[idx].format(v=v)
        else:
            return f"state.locals['{v}']"

    def _variate_condition(self, data: dict, variant: str, context: GenerationContext) -> str:
        """变化条件表达式"""
        cond = data.get("cond", "x > 0")
        t = data.get("true", "target")
        f = data.get("false", "pc + 1")

        if variant == "direct":
            return f"if {cond} then return {t} end; return {f}"
        elif variant == "nested":
            return f"return ({cond} and {t} or {f})"
        elif variant == "temp_var":
            idx = context.rng.randint(0, len(self.CONDITION_VARIANTS) - 1)
            return self.CONDITION_VARIANTS[idx].format(cond=cond, t=t, f=f)
        else:
            return f"if {cond} then return {t} end; return {f}"


# =============================================================================
# 执行调度策略
# =============================================================================

class ExecutionDispatchStrategy(CodeGenerationStrategy[str]):
    """
    执行调度策略

    决定执行循环和调度的实现方式
    """

    category = StrategyCategory.EXECUTION_DISPATCH

    class Variants(Enum):
        WHILE_LOOP = "while_loop"         # while 循环
        REPEAT_LOOP = "repeat_loop"       # repeat 循环
        FOR_LOOP = "for_loop"             # for 循环
        TAIL_CALL = "tail_call"            # 尾调用
        TABLE_DISPATCH = "table_dispatch"  # 表调度

    def __init__(self, variant: str = "while_loop"):
        self._variant = variant

    def apply(self, context: GenerationContext, data: Any = None) -> str:
        """生成执行调度代码"""
        variant = self.select_variant(context)

        if variant == "while_loop":
            return self._generate_while_loop()
        elif variant == "repeat_loop":
            return self._generate_repeat_loop()
        elif variant == "for_loop":
            return self._generate_for_loop()
        elif variant == "tail_call":
            return self._generate_tail_call()
        elif variant == "table_dispatch":
            return self._generate_table_dispatch()
        return self._generate_while_loop()

    def get_variants(self) -> list[str]:
        return [v.value for v in self.Variants]

    def select_variant(self, context: GenerationContext) -> str:
        if self._variant != "random":
            return self._variant
        return context.rng.choice(self.get_variants())

    @property
    def name(self) -> str:
        return f"execution_dispatch:{self._variant}"

    def _generate_while_loop(self) -> str:
        return """local function execute(code, state)
    local pc = 1
    while pc and not state.halted do
        local instr = code[pc]
        if not instr then break end
        local op = instr[1]
        local handler = handlers[op] or handlers.default
        pc = handler(instr, state, pc)
        if pc < 1 or pc > #code + 1 then break end
    end
    return state.return_value
end"""

    def _generate_repeat_loop(self) -> str:
        return """local function execute(code, state)
    local pc = 1
    repeat
        local instr = code[pc]
        if not instr then break end
        local op = instr[1]
        local handler = handlers[op] or handlers.default
        pc = handler(instr, state, pc)
    until state.halted or not pc or pc < 1 or pc > #code + 1
    return state.return_value
end"""

    def _generate_for_loop(self) -> str:
        return """local function execute(code, state)
    local pc = 1
    local max_pc = #code + 1
    for _ in function() end, nil, nil do
        if state.halted or not pc or pc < 1 or pc > max_pc then break end
        local instr = code[pc]
        if not instr then break end
        local op = instr[1]
        local handler = handlers[op] or handlers.default
        pc = handler(instr, state, pc)
    end
    return state.return_value
end"""

    def _generate_tail_call(self) -> str:
        return """local function step(pc, code, state)
    if state.halted then return state.return_value end
    local instr = code[pc]
    if not instr then return state.return_value end
    local op = instr[1]
    local handler = handlers[op] or handlers.default
    return step(handler(instr, state, pc), code, state)
end
local function execute(code, state)
    return step(1, code, state)
end"""

    def _generate_table_dispatch(self) -> str:
        return """local _DISPATCH_TABLE = setmetatable({}, {__index = function() return handlers.default end})
local function execute(code, state)
    local pc = 1
    while pc and not state.halted do
        local instr = code[pc]
        if not instr then break end
        local handler = _DISPATCH_TABLE[instr[1]]
        pc = handler(instr, state, pc)
        if pc < 1 or pc > #code + 1 then break end
    end
    return state.return_value
end"""


# =============================================================================
# 多策略生成管道
# =============================================================================

class PolymorphicCodeGenerator:
    """
    多策略代码生成器

    整合多个策略，按配置或随机选择生成代码
    """

    def __init__(
        self,
        rng: random.Random | None = None,
        seed: int | None = None,
        instruction_encoding: str = "compact",
        handler_structure: str = "direct",
        expression_variation: str = "direct",
        execution_dispatch: str = "while_loop"
    ):
        self.rng = rng or random.Random(seed)
        self.seed = seed

        # 策略配置
        self.config = {
            StrategyCategory.INSTRUCTION_ENCODING: instruction_encoding,
            StrategyCategory.HANDLER_STRUCTURE: handler_structure,
            StrategyCategory.EXPRESSION_VARIATION: expression_variation,
            StrategyCategory.EXECUTION_DISPATCH: execution_dispatch,
        }

        # 策略实例
        self.strategies: dict[StrategyCategory, CodeGenerationStrategy] = {
            StrategyCategory.INSTRUCTION_ENCODING: InstructionEncodingStrategy(instruction_encoding),
            StrategyCategory.HANDLER_STRUCTURE: HandlerStructureStrategy(handler_structure),
            StrategyCategory.EXPRESSION_VARIATION: ExpressionVariationStrategy(expression_variation),
            StrategyCategory.EXECUTION_DISPATCH: ExecutionDispatchStrategy(execution_dispatch),
        }

        # 组合策略
        self.composite = CompositeStrategy(list(self.strategies.values()))

    def create_context(self) -> GenerationContext:
        """创建生成上下文"""
        return GenerationContext(
            rng=self.rng,
            seed=self.seed,
            enabled_strategies=set(self.config.keys())
        )

    def set_strategy(self, category: StrategyCategory, variant: str) -> None:
        """设置策略变体"""
        self.config[category] = variant
        if category == StrategyCategory.INSTRUCTION_ENCODING:
            self.strategies[category] = InstructionEncodingStrategy(variant)
        elif category == StrategyCategory.HANDLER_STRUCTURE:
            self.strategies[category] = HandlerStructureStrategy(variant)
        elif category == StrategyCategory.EXPRESSION_VARIATION:
            self.strategies[category] = ExpressionVariationStrategy(variant)
        elif category == StrategyCategory.EXECUTION_DISPATCH:
            self.strategies[category] = ExecutionDispatchStrategy(variant)

    def randomize_strategies(self) -> None:
        """随机化所有策略"""
        for category in StrategyCategory:
            variants = self.strategies[category].get_variants()
            self.set_strategy(category, self.rng.choice(variants))

    def generate_instruction_table(self, instructions: list[Instruction]) -> str:
        """生成指令表"""
        context = self.create_context()
        context.instruction_data = instructions
        return self.strategies[StrategyCategory.INSTRUCTION_ENCODING].apply(context)

    def generate_handlers(self, templates: dict | None = None) -> str:
        """生成 handlers"""
        context = self.create_context()
        context.handler_templates = templates or LuaHandlerGenerator.HANDLER_TEMPLATES
        return self.strategies[StrategyCategory.HANDLER_STRUCTURE].apply(context)

    def generate_expression(self, expr_type: str, **kwargs) -> str:
        """生成表达式"""
        context = self.create_context()
        data = {"type": expr_type, **kwargs}
        return self.strategies[StrategyCategory.EXPRESSION_VARIATION].apply(context, data)

    def generate_execute_loop(self) -> str:
        """生成执行循环"""
        context = self.create_context()
        return self.strategies[StrategyCategory.EXECUTION_DISPATCH].apply(context)

    def generate_complete_program(
        self,
        instructions: list[Instruction] | None = None
    ) -> str:
        """生成完整程序（使用所有策略）"""
        parts = []

        # 头部
        parts.append("--" + "=" * 50)
        parts.append("-- Polymorphic Code Generator Output")
        parts.append(f"-- Seed: {self.seed or 'random'}")
        parts.append(f"-- Strategies: {self._get_strategy_summary()}")
        parts.append("--" + "=" * 50)
        parts.append("")

        # 调试开关
        parts.append("local _DEBUG = false")
        parts.append("")

        # 指令表
        if instructions:
            parts.append(self.generate_instruction_table(instructions))
            parts.append("")

        # 执行状态
        parts.append("local state = {locals={}, globals={}, pc=1, halted=false, return_value=nil}")
        parts.append("")

        # 工具函数
        parts.append(self._generate_utility_functions())
        parts.append("")

        # Handlers
        parts.append(self.generate_handlers())
        parts.append("")

        # 执行循环
        parts.append(self.generate_execute_loop())
        parts.append("")

        # 运行
        parts.append("local result = execute(code, state)")
        parts.append('if _DEBUG then print("Result: " .. tostring(result)) end')

        return "\n".join(parts)

    def _generate_utility_functions(self) -> str:
        return """-- Utility functions
local function _get(state, varname)
    return state.locals[varname] or state.globals[varname]
end
local function _set(state, varname, value)
    state.locals[varname] = value
end"""

    def _get_strategy_summary(self) -> str:
        return ", ".join(f"{k.value}={v}" for k, v in self.config.items())


# =============================================================================
# 策略工厂
# =============================================================================

class StrategyFactory:
    """
    策略工厂

    根据配置创建策略实例
    """

    @staticmethod
    def create_instruction_encoding_strategy(variant: str = "random") -> InstructionEncodingStrategy:
        return InstructionEncodingStrategy(variant)

    @staticmethod
    def create_handler_structure_strategy(variant: str = "random") -> HandlerStructureStrategy:
        return HandlerStructureStrategy(variant)

    @staticmethod
    def create_expression_variation_strategy(variant: str = "random") -> ExpressionVariationStrategy:
        return ExpressionVariationStrategy(variant)

    @staticmethod
    def create_execution_dispatch_strategy(variant: str = "random") -> ExecutionDispatchStrategy:
        return ExecutionDispatchStrategy(variant)

    @staticmethod
    def create_all_strategies(config: dict | None = None) -> dict[StrategyCategory, CodeGenerationStrategy]:
        """创建所有策略"""
        cfg = config or {}
        return {
            StrategyCategory.INSTRUCTION_ENCODING: StrategyFactory.create_instruction_encoding_strategy(
                cfg.get("instruction_encoding", "random")
            ),
            StrategyCategory.HANDLER_STRUCTURE: StrategyFactory.create_handler_structure_strategy(
                cfg.get("handler_structure", "random")
            ),
            StrategyCategory.EXPRESSION_VARIATION: StrategyFactory.create_expression_variation_strategy(
                cfg.get("expression_variation", "random")
            ),
            StrategyCategory.EXECUTION_DISPATCH: StrategyFactory.create_execution_dispatch_strategy(
                cfg.get("execution_dispatch", "random")
            ),
        }


# =============================================================================
# 便捷函数
# =============================================================================

def create_polymorphic_generator(
    seed: int | None = None,
    **strategy_config
) -> PolymorphicCodeGenerator:
    """
    创建多策略代码生成器

    Args:
        seed: 随机种子（可复现）
        **strategy_config: 策略配置

    Returns:
        生成器实例
    """
    return PolymorphicCodeGenerator(
        seed=seed,
        **strategy_config
    )


def generate_with_random_strategies(
    instructions: list[Instruction] | None = None,
    seed: int | None = None
) -> str:
    """
    使用随机策略生成代码

    Args:
        instructions: 指令列表
        seed: 随机种子

    Returns:
        Lua 代码
    """
    gen = create_polymorphic_generator(seed=seed)
    gen.randomize_strategies()
    return gen.generate_complete_program(instructions)


def demo_polymorphic_code_generation():
    """
    演示多策略代码生成
    """
    print("=" * 70)
    print("Polymorphic Code Generation Pipeline Demo")
    print("=" * 70)

    # 测试指令
    instructions = [
        Instruction(OpCode.INIT, ["x"], None, "10"),
        Instruction(OpCode.INIT, ["y"], None, "20"),
        Instruction(OpCode.ASSIGN, ["sum"], None, "x + y"),
        Instruction(OpCode.RETURN_VAL, ["sum"]),
    ]

    print("\n[1] 固定策略生成:")
    print("-" * 50)

    gen = PolymorphicCodeGenerator(
        seed=42,
        instruction_encoding="compact",
        handler_structure="direct",
        expression_variation="direct",
        execution_dispatch="while_loop"
    )
    print(gen.generate_complete_program(instructions))

    print("\n" + "=" * 70)
    print("\n[2] 不同编码策略对比:")
    print("-" * 50)

    for encoding in ["compact", "verbose", "named"]:
        gen.set_strategy(StrategyCategory.INSTRUCTION_ENCODING, encoding)
        print(f"\n--- {encoding} encoding ---")
        print(gen.generate_instruction_table(instructions))

    print("\n" + "=" * 70)
    print("\n[3] 不同 Handler 结构对比:")
    print("-" * 50)

    for structure in ["direct", "stepwise", "closure"]:
        gen.set_strategy(StrategyCategory.HANDLER_STRUCTURE, structure)
        print(f"\n--- {structure} structure ---")
        print(gen.generate_handlers())

    print("\n" + "=" * 70)
    print("\n[4] 不同执行调度对比:")
    print("-" * 50)

    for dispatch in ["while_loop", "tail_call", "table_dispatch"]:
        gen.set_strategy(StrategyCategory.EXECUTION_DISPATCH, dispatch)
        print(f"\n--- {dispatch} dispatch ---")
        print(gen.generate_execute_loop())

    print("\n" + "=" * 70)
    print("\n[5] 完全随机策略多次生成:")
    print("-" * 50)

    for i in range(3):
        rng = random.Random(i * 100)
        gen = PolymorphicCodeGenerator(seed=i * 100)
        gen.randomize_strategies()
        print(f"\n--- Random generation {i+1} ---")
        print(f"Strategies: {gen._get_strategy_summary()}")
        print(gen.generate_complete_program(instructions))

    print("\n" + "=" * 70)
    print("Polymorphic Code Generation Features:")
    print("  - 4 strategy categories:")
    print("    * INSTRUCTION_ENCODING: compact/verbose/named/indexed/mapped")
    print("    * HANDLER_STRUCTURE: direct/stepwise/table/composed/closure/layered")
    print("    * EXPRESSION_VARIATION: direct/nested/temp_var/table")
    print("    * EXECUTION_DISPATCH: while_loop/repeat_loop/for_loop/tail_call/table_dispatch")
    print("  - Seed-based reproducibility")
    print("  - Strategy composition support")
    print("=" * 70)


if __name__ == "__main__":
    demo_polymorphic_code_generation()


