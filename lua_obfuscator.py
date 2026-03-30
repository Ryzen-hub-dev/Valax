from __future__ import annotations

import random
import string
import time
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
    source = strip_leading_bom(source)
    random.seed(int(time.time()))
    rng = create_time_seeded_random()
    profile = ProtectionProfile(rng, watermark)

    randomize_algorithms(profile, rng)
    shuffle_tables(profile, rng)

    program_wrapper, constant_pool_code, dispatcher_code, _ = build_block_program(
        source,
        profile,
        rng,
        randomize_order=False,
        execution_mode="sequential",
        use_constant_pool=True,
        use_auxiliary_paths=False
    )

    api_plan = apply_api_indirection(tokenize(source), profile, rng)

    return (
        "--[[\n"
        + "Lua Protector Watermark: "
        + sanitize_comment(watermark)
        + "\nGenerated by Python transformer\n"
        + "Protection profile: pooled literals + randomized runtime + lexer-aware minification\n"
        + "Multi-stage block generation architecture\n"
        + "Features: constant pool + branch support + block randomization + auxiliary paths\n"
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
    """生成代码块执行调度器"""

    def __init__(self, profile: ProtectionProfile, rng: random.Random):
        self.profile = profile
        self.rng = rng
        self.pc_name = random_lua_identifier(rng, "_pc")
        self.tbl_name = random_lua_identifier(rng, "_tbl")
        self.entry_name = random_lua_identifier(rng, "_entry")

    def generate_dispatcher(self, program: BlockProgram, mode: str = "sequential") -> str:
        """生成执行调度器代码"""
        if mode == "sequential":
            return self._generate_sequential_dispatcher(program)
        elif mode == "random":
            return self._generate_random_dispatcher(program)
        elif mode == "indexed":
            return self._generate_indexed_dispatcher(program)
        else:
            return self._generate_sequential_dispatcher(program)

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





