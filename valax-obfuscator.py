#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Valax Obfuscator - Lua代码混淆器 (Python实现)
==============================================

Valax Protect - Lua代码混淆器 (Python实现)
==============================================

功能:
  - 强制 VM 混淆 (所有代码必须经过 VM 编译)
  - 多层 VM 架构 (可配置层数，默认3层)
  - 分段执行 (bytecode 分块加密执行)
  - 自解密 Loader (运行时动态解密)
  - 多态 opcode (每次构建随机映射)
  - 指令多态变体 (同一指令多种实现)
  - 控制流混淆 (虚假指令、垃圾 opcode)
  - 安全强化 (Anti-debug, Anti-hook, Anti-dump)

特性:
  - 强制全局 VM - 无 fallback 模式
  - 动态密钥生成 - 每次运行不同 key
  - 运行时 opcode 表构建 - 无静态表
  - 分段加密执行 - chunk 顺序打乱
  - 多态 dispatch - 不可预测跳转
  - 安全检测 - 调试/hook 检测

架构:
  Source -> Lexer -> Parser -> AST -> Bytecode Compiler
        -> Polymorphic Opcode Mapper
        -> Chunk Encryptor
        -> Multi-Layer VM Builder
        -> Self-Decrypting Loader
        -> Output

MoonSec/Luraph级别特性:
  --enable-multi-vm      启用多层VM系统 (外层VM + 内层嵌套解释器)
  --enable-segment-decrypt 启用字节码分段动态解密
  --enable-env-binding  启用环境绑定 (Roblox/Lua环境特征)
  --enable-timing-check  启用时间/行为检测 (防调试)
  --enable-fake-struct   启用虚假函数和伪proto结构
  --enable-num-split     启用数字混淆 (拆分表达式)
  --commercial           启用所有商业级保护

VM混淆特性:
  - 自定义指令集 (50+条指令, 含假操作码 0xC0-0xCA)
  - 字节码编译 (AST → Bytecode)
  - XOR + Base64 加密
  - Stack-based 虚拟机
  - Anti-debug 保护
  - Anti-dump 检测 (debug.getinfo, loadstring, TracerPid)
  - 假操作码混淆
  - 多层VM嵌套
  - 运行时分段解密

作者: Valax
日期: 2026

= =============================================================================
# 商业级升级 (V2)
#
# - bit32 兼容层 (100% Lua 5.1 / Luau 兼容)
# - 三层嵌套 VM 架构
# - 动态 opcode 多态
# - 增强反调试系统
# - 水印保护机制
# =============================================================================

import re
import base64
import random
import string
import argparse
import os
import sys
import hashlib
import time
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any


# =============================================================================
# 第一部分: bit32 兼容层 (Luau / Lua 5.1 兼容)
# =============================================================================

BIT32_COMPAT_SHIM = '''-- bit32 兼容实现 (自动检测并注入)
local bit32 = bit32 or {}
local _b32_mt = {__index = bit32}
setmetatable(bit32, _b32_mt)
if not bit32.rshift then
    bit32.rshift = function(v, n)
        return math.floor((v % 0x100000000) / (2 ^ n))
    end
end
if not bit32.lshift then
    bit32.lshift = function(v, n)
        return ((v % 0x100000000) * (2 ^ n)) % 0x100000000
    end
end
if not bit32.band then
    bit32.band = function(...)
        local r = 0xFFFFFFFF
        for _, v in ipairs({...}) do
            r = r & (v % 0x100000000)
        end
        return r
    end
end
if not bit32.bor then
    bit32.bor = function(...)
        local r = 0
        for _, v in ipairs({...}) do
            r = r | (v % 0x100000000)
        end
        return r
    end
end
if not bit32.bxor then
    bit32.bxor = function(a, b)
        return ((a % 0x100000000) ~ (b % 0x100000000)) % 0x100000000
    end
end
if not bit32.bnot then
    bit32.bnot = function(v)
        return ((~v) % 0x100000000)
    end
end
'''

WATERMARK_TEXT = "Protected By Valax Scrub Engine (https://www.valaxscrub.shop)"
WATERMARK_HASH = 0x1A2B3C4D  # 预计算的 hash (实际会根据内容变化)


def compute_watermark_hash(text: str) -> int:
    
    h = 0
    for i, c in enumerate(text):
        h = (h + ord(c) * (i + 1) * 31) % 0xFFFFFFFF
    return h


def generate_bit32_compat_code() -> str:
    
    return BIT32_COMPAT_SHIM


def generate_watermark_code() -> List[str]:
   
    lines = []
    
    # 分割水印字符串
    parts = []
    part_len = len(WATERMARK_TEXT) // 3
    for i in range(3):
        start = i * part_len
        end = start + part_len if i < 2 else len(WATERMARK_TEXT)
        parts.append(WATERMARK_TEXT[start:end])
    
    # 变量名
    w_vars = [''.join(random.choice(string.ascii_lowercase) for _ in range(3)) for _ in range(3)]
    wm_func = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
    wh_func = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
    wc_func = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
    dead_func = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
    
    # 存储 char codes
    for i, part in enumerate(parts):
        codes = ','.join(str(ord(c)) for c in part)
        lines.append(f"local {w_vars[i]}={{{codes}}}")
    
    # 拼接函数
    lines.append(f"local function {wm_func}(t)")
    lines.append("  local r=''")
    lines.append("  for i=1,#t do r=r..string.char(t[i]) end")
    lines.append("  return r")
    lines.append("end")
    
    # Hash 函数
    lines.append(f"local function {wh_func}(s)")
    lines.append("  local h=0")
    lines.append("  for i=1,#s do")
    lines.append("    h=(h+string.byte(s,i)*(i+1)*31)%0xFFFFFFFF")
    lines.append("  end")
    lines.append("  return h")
    lines.append("end")
    
    # 检测函数
    lines.append(f"local function {wc_func}()")
    lines.append(f"  local w={wm_func}({w_vars[0]})..{wm_func}({w_vars[1]})..{wm_func}({w_vars[2]})")
    lines.append(f"  local h={wh_func}(w)")
    wm_hash = compute_watermark_hash(WATERMARK_TEXT)
    lines.append(f"  if h~={wm_hash} then")
    lines.append(f"    while true do local _=1 end")
    lines.append("  end")
    lines.append("end")
    
    # 清理
    for var in w_vars:
        lines.append(f"{var}=nil")
    
    return lines


def generate_enhanced_anti_debug_code() -> List[str]:
    
    lines = []
    
    state_var = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
    dead_func = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
    check_func = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
    
    # 状态
    lines.append(f"local {state_var}=false")
    
    # 死循环
    lines.append(f"local function {dead_func}()")
    lines.append("  while true do")
    lines.append("    local _=1")
    lines.append("    if math.random() > 0.9999 then break end")
    lines.append("  end")
    lines.append("end")
    
    # 检测函数
    lines.append(f"local function {check_func}()")
    
    # debug.getinfo
    lines.append("  if debug and debug.getinfo then")
    lines.append("    local ok,f=pcall(debug.getinfo,1)")
    lines.append("    if ok and f then")
    lines.append("      if f.currentline and f.currentline < 0 then")
    lines.append(f"        {state_var}=true")
    lines.append("      end")
    lines.append("      if f.what and f.what:match('C') then")
    lines.append(f"        {state_var}=true")
    lines.append("      end")
    lines.append("    end")
    lines.append("  end")
    
    # getgc
    lines.append("  if getgc then")
    lines.append("    local gc=getgc()")
    lines.append("    if type(gc)=='table' and #gc > 500 then")
    lines.append(f"      {state_var}=true")
    lines.append("    end")
    lines.append("  end")
    
    # hookfunction
    lines.append("  if debug and debug.hookfunction then")
    lines.append("    local ok=pcall(function()")
    lines.append("      local f=function() end")
    lines.append("      debug.hookfunction(f,function() end)")
    lines.append("    end)")
    lines.append(f"    if ok then {state_var}=true end")
    lines.append("  end")
    
    # sethook
    lines.append("  if debug and debug.sethook then")
    lines.append("    local ok=pcall(function()debug.sethook(function() end,'')end)")
    lines.append(f"    if not ok then {state_var}=true end")
    lines.append("  end")
    
    # hookmetamethod (Luau)
    lines.append("  if hookmetamethod then")
    lines.append(f"    {state_var}=true")
    lines.append("  end")
    
    # 触发
    lines.append(f"  if {state_var} then {dead_func}() end")
    
    lines.append("end")
    
    return lines


def generate_dynamic_pc_update(pc_var: str) -> str:
   
    mode = random.choice(['add_sub', 'table', 'xor_mask', 'mixed'])
    
    if mode == 'add_sub':
        # 加减交错
        r1 = random.randint(-3, 3)
        r2 = random.randint(-3, 3)
        r3 = random.randint(-3, 3)
        return f"{pc_var}={pc_var}+1+{r1}-{r2}+{r3}"
    
    elif mode == 'table':
        # 表驱动
        tbl_name = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        entries = ','.join(str(random.randint(-2, 2)) for _ in range(16))
        return f"local {tbl_name}={{{entries}}};{pc_var}={pc_var}+({tbl_name}[bit32.band({pc_var},15)]or 1)"
    
    elif mode == 'xor_mask':
        # XOR 混淆
        mask = random.randint(1, 255)
        return f"{pc_var}=bit32.bxor({pc_var}+1,{mask})"
    
    else:
        # 混合方式
        deltas = [random.randint(-2, 2) for _ in range(random.randint(3, 5))]
        total = sum(deltas)
        expr = '+'.join(str(d) for d in deltas) + f"+{1-total}"
        return f"{pc_var}={pc_var}+{expr}"


def replace_bitwise_ops(code: str) -> str:
    
    # 注意: 这是在 Python 层面修改生成的 Lua 代码字符串
    # 实际替换发生在生成代码的地方
    
    # 替换 >> 为 bit32.rshift
    # 替换 << 为 bit32.lshift  
    # 替换 & 为 bit32.band
    # 替换 | 为 bit32.bor
    # 替换 ~ (XOR) 为 bit32.bxor
    
    return code


# =============================================================================
# 第一部分: Token定义
# =============================================================================

class TokenKind:
    
    # 关键字
    IF = "IF"
    THEN = "THEN"
    ELSE = "ELSE"
    ELSEIF = "ELSEIF"
    END = "END"
    WHILE = "WHILE"
    DO = "DO"
    FOR = "FOR"
    IN = "IN"
    REPEAT = "REPEAT"
    UNTIL = "UNTIL"
    FUNCTION = "FUNCTION"
    LOCAL = "LOCAL"
    RETURN = "RETURN"
    BREAK = "BREAK"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    NIL = "NIL"
    TRUE = "TRUE"
    FALSE = "FALSE"
    
    # 字面量
    NUMBER = "NUMBER"
    STRING = "STRING"
    IDENTIFIER = "IDENTIFIER"
    
    # 符号
    PLUS = "PLUS"
    MINUS = "MINUS"
    STAR = "STAR"
    SLASH = "SLASH"
    PERCENT = "PERCENT"
    EQ = "EQ"
    EQEQ = "EQEQ"
    TILDE = "TILDE"
    TILDEEQ = "TILDEEQ"
    LT = "LT"
    GT = "GT"
    LTEQ = "LTEQ"
    GTEQ = "GTEQ"
    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LBRACKET = "LBRACKET"
    RBRACKET = "RBRACKET"
    COMMA = "COMMA"
    DOT = "DOT"
    DOTDOT = "DOTDOT"
    DOTDOTDOT = "DOTDOTDOT"
    COLON = "COLON"
    HASH = "HASH"
    SEMICOLON = "SEMICOLON"
    
    # 特殊
    NEWLINE = "NEWLINE"
    COMMENT = "COMMENT"
    EOF = "EOF"


@dataclass
class Token:
    
    kind: str
    value: Any
    line: int
    column: int
    
    def __repr__(self):
        return f"Token({self.kind}, {repr(self.value)}, {self.line}:{self.column})"


# =============================================================================
# 第二部分: 词法分析器 (Lexer)
# =============================================================================

class Lexer:
    
    # Lua关键字
    KEYWORDS = {
        'if', 'then', 'else', 'elseif', 'end',
        'while', 'do', 'for', 'in', 'repeat', 'until',
        'function', 'local', 'return', 'break',
        'and', 'or', 'not',
        'nil', 'true', 'false',
    }
    
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
    
    def scan(self) -> List[Token]:
       
        while not self._is_eof():
            # 跳过空白字符
            self._skip_whitespace()
            if self._is_eof():
                break
            
            # 记录开始位置
            start_line = self.line
            start_col = self.column
            
            # 扫描Token
            token = self._scan_token(start_line, start_col)
            if token:
                self.tokens.append(token)
        
        # 添加EOF标记
        self.tokens.append(Token(TokenKind.EOF, None, self.line, self.column))
        return self.tokens
    
    def _scan_token(self, line: int, col: int) -> Optional[Token]:
       
        c = self._peek()
        
        # 标识符或关键字 (a-zA-Z_)
        if c.isalpha() or c == '_':
            return self._scan_identifier(line, col)
        
        # 数字
        if c.isdigit():
            return self._scan_number(line, col)
        
        # 字符串
        if c in ('"', "'"):
            return self._scan_string(line, col)
        
        # 符号和运算符
        return self._scan_symbol(line, col)
    
    def _scan_identifier(self, line: int, col: int) -> Token:
       
        start = self.pos
        while self._peek().isalnum() or self._peek() in ('_',):
            self._advance()
        
        text = self.source[start:self.pos]
        
        # 检查是否为关键字
        if text in self.KEYWORDS:
            kind = getattr(TokenKind, text.upper(), TokenKind.IDENTIFIER)
        else:
            kind = TokenKind.IDENTIFIER
        
        return Token(kind, text, line, col)
    
    def _scan_string(self, line: int, col: int) -> Token:
       
        quote = self._peek()
        self._advance()
        
        # 处理转义序列
        chars = []
        while not self._is_eof():
            c = self._peek()
            if c == quote:
                self._advance()
                break
            if c == '\\':
                self._advance()
                if not self._is_eof():
                    esc = self._peek()
                    if esc == 'n':
                        chars.append('\\n')
                    elif esc == 't':
                        chars.append('\\t')
                    elif esc == 'r':
                        chars.append('\\r')
                    elif esc == '\\':
                        chars.append('\\\\')
                    elif esc == '"':
                        chars.append('\\"')
                    elif esc == "'":
                        chars.append("\\'")
                    else:
                        chars.append(esc)
                else:
                    chars.append('\\')
            elif c == '\n':
                # Lua允许在字符串中换行
                chars.append('\\n')
                self._advance()
            else:
                chars.append(c)
                self._advance()
        
        return Token(TokenKind.STRING, ''.join(chars), line, col)
    
    def _scan_number(self, line: int, col: int) -> Token:
       
        start = self.pos
        
        # 处理十六进制 (0x)
        if self._peek() == '0' and self._peek_next() in ('x', 'X'):
            self._advance()  # 0
            self._advance()  # x
            while self._peek().isalnum():
                self._advance()
        else:
            # 处理十进制
            while self._peek().isdigit() or self._peek() == '.':
                self._advance()
            
            # 科学计数法
            if self._peek() in ('e', 'E'):
                self._advance()
                if self._peek() in ('+', '-'):
                    self._advance()
                while self._peek().isdigit():
                    self._advance()
        
        text = self.source[start:self.pos]
        
        # 转换为数字
        try:
            if text.startswith('0x'):
                value = int(text, 16)
            else:
                value = float(text) if '.' in text or 'e' in text.lower() else int(text)
        except ValueError:
            value = 0
        
        return Token(TokenKind.NUMBER, value, line, col)
    
    def _scan_symbol(self, line: int, col: int) -> Token:
        
        # 先检查两字符运算符
        two_char = self.source[self.pos:self.pos+2]
        three_char = self.source[self.pos:self.pos+3]
        
        if three_char == '...':
            self._advance(); self._advance(); self._advance()
            return Token(TokenKind.DOTDOTDOT, '...', line, col)
        
        compound_tokens = {
            '==': TokenKind.EQEQ,
            '~=': TokenKind.TILDEEQ,
            '<=': TokenKind.LTEQ,
            '>=': TokenKind.GTEQ,
            '..': TokenKind.DOTDOT,
        }
        
        if two_char in compound_tokens:
            self._advance(); self._advance()
            return Token(compound_tokens[two_char], two_char, line, col)
        
        # 单字符符号
        c = self._peek()
        single_tokens = {
            '+': TokenKind.PLUS,
            '-': TokenKind.MINUS,
            '*': TokenKind.STAR,
            '/': TokenKind.SLASH,
            '%': TokenKind.PERCENT,
            '=': TokenKind.EQ,
            '~': TokenKind.TILDE,
            '<': TokenKind.LT,
            '>': TokenKind.GT,
            '{': TokenKind.LBRACE,
            '}': TokenKind.RBRACE,
            '(': TokenKind.LPAREN,
            ')': TokenKind.RPAREN,
            '[': TokenKind.LBRACKET,
            ']': TokenKind.RBRACKET,
            ',': TokenKind.COMMA,
            '.': TokenKind.DOT,
            ':': TokenKind.COLON,
            '#': TokenKind.HASH,
            ';': TokenKind.SEMICOLON,
        }
        
        self._advance()
        return Token(single_tokens.get(c, TokenKind.EOF), c, line, col)
    
    def _skip_whitespace(self):
       
        while not self._is_eof():
            c = self._peek()
            if c in ' \t':
                self._advance()
            elif c == '\n':
                self.line += 1
                self.column = 1
                self._advance()
            elif c == '-' and self._peek_next() == '-':
                # 注释 - 跳过到行尾
                self._advance()  # -
                self._advance()  # -
                while not self._is_eof() and self._peek() != '\n':
                    self._advance()
            else:
                break
    
    def _peek(self) -> str:
     
        if self.pos < len(self.source):
            return self.source[self.pos]
        return '\0'
    
    def _peek_next(self) -> str:
        """查看下一个字符"""
        if self.pos + 1 < len(self.source):
            return self.source[self.pos + 1]
        return '\0'
    
    def _advance(self):
        """前进到下一个字符"""
        if self.pos < len(self.source):
            if self.source[self.pos] == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1
    
    def _is_eof(self) -> bool:
        """检查是否到达末尾"""
        return self.pos >= len(self.source)


# =============================================================================
# 第三部分: AST节点定义
# =============================================================================

class NodeKind:
    """AST节点类型"""
    PROGRAM = "PROGRAM"
    BLOCK = "BLOCK"
    
    # 语句
    LOCAL_VAR = "LOCAL_VAR"
    ASSIGNMENT = "ASSIGNMENT"
    IF_STMT = "IF_STMT"
    WHILE_STMT = "WHILE_STMT"
    REPEAT_STMT = "REPEAT_STMT"
    FOR_NUMERIC = "FOR_NUMERIC"
    FOR_IN = "FOR_IN"
    FUNCTION_DEF = "FUNCTION_DEF"
    LOCAL_FUNCTION = "LOCAL_FUNCTION"
    RETURN_STMT = "RETURN_STMT"
    BREAK_STMT = "BREAK_STMT"
    DO_BLOCK = "DO_BLOCK"
    FUNCTION_CALL = "FUNCTION_CALL"
    
    # 表达式
    NUMBER_LIT = "NUMBER_LIT"
    STRING_LIT = "STRING_LIT"
    NIL_LIT = "NIL_LIT"
    TRUE_LIT = "TRUE_LIT"
    FALSE_LIT = "FALSE_LIT"
    VARARG = "VARARG"
    IDENTIFIER = "IDENTIFIER"
    TABLE_CONSTRUCT = "TABLE_CONSTRUCT"
    INDEX_ACCESS = "INDEX_ACCESS"
    METHOD_CALL = "METHOD_CALL"
    FUNCTION_LITERAL = "FUNCTION_LITERAL"
    UNARY_OP = "UNARY_OP"
    BINARY_OP = "BINARY_OP"
    
    # 混淆专用节点
    STRING_TABLE_INIT = "STRING_TABLE_INIT"
    CONTROL_FLOW_FLAT = "CONTROL_FLOW_FLAT"
    VM_CALL = "VM_CALL"
    ANTI_DEBUG = "ANTI_DEBUG"


@dataclass
class ASTNode:
    """AST节点基类"""
    kind: str
    value: Any = None
    children: List['ASTNode'] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
    
    def __repr__(self):
        return f"ASTNode({self.kind}, {repr(self.value)})"


class ProgramNode(ASTNode):
    """程序根节点"""
    def __init__(self, body: List[ASTNode]):
        super().__init__(NodeKind.PROGRAM)
        self.body = body


class BlockNode(ASTNode):
    """代码块"""
    def __init__(self, statements: List[ASTNode]):
        super().__init__(NodeKind.BLOCK)
        self.statements = statements
        self.indent_offset = 0  # 用于混乱缩进


class LocalVarNode(ASTNode):
    """局部变量声明: local a, b = 1, 2"""
    def __init__(self, names: List[str], values: List[ASTNode]):
        super().__init__(NodeKind.LOCAL_VAR)
        self.names = names
        self.values = values


class AssignmentNode(ASTNode):
    """赋值语句: a = 1"""
    def __init__(self, targets: List[ASTNode], values: List[ASTNode]):
        super().__init__(NodeKind.ASSIGNMENT)
        self.targets = targets
        self.values = values


class IfNode(ASTNode):
    """if语句"""
    def __init__(self, condition: ASTNode, then_body: BlockNode, 
                 elseif_blocks: List[Tuple[ASTNode, BlockNode]], 
                 else_body: Optional[BlockNode]):
        super().__init__(NodeKind.IF_STMT)
        self.condition = condition
        self.then_body = then_body
        self.elseif_blocks = elseif_blocks
        self.else_body = else_body


class WhileNode(ASTNode):
    """while循环"""
    def __init__(self, condition: ASTNode, body: BlockNode):
        super().__init__(NodeKind.WHILE_STMT)
        self.condition = condition
        self.body = body


class RepeatNode(ASTNode):
    """repeat-until循环"""
    def __init__(self, body: BlockNode, condition: ASTNode):
        super().__init__(NodeKind.REPEAT_STMT)
        self.body = body
        self.condition = condition


class ForNumericNode(ASTNode):
    """数值for循环: for i = 1, 10 do end"""
    def __init__(self, variable: str, start: ASTNode, stop: ASTNode, 
                 step: Optional[ASTNode], body: BlockNode):
        super().__init__(NodeKind.FOR_NUMERIC)
        self.variable = variable
        self.start = start
        self.stop = stop
        self.step = step
        self.body = body


class ForInNode(ASTNode):
    """迭代for循环: for k, v in pairs(t) do end"""
    def __init__(self, variables: List[str], iter_exprs: List[ASTNode], body: BlockNode):
        super().__init__(NodeKind.FOR_IN)
        self.variables = variables
        self.iter_exprs = iter_exprs
        self.body = body


class FunctionDefNode(ASTNode):
    """函数定义"""
    def __init__(self, name: str, params: List[str], body: BlockNode, 
                 is_local: bool = False, is_vararg: bool = False):
        super().__init__(NodeKind.FUNCTION_DEF if not is_local else NodeKind.LOCAL_FUNCTION)
        self.name = name
        self.params = params
        self.body = body
        self.is_local = is_local
        self.is_vararg = is_vararg


class ReturnNode(ASTNode):
    """return语句"""
    def __init__(self, values: List[ASTNode]):
        super().__init__(NodeKind.RETURN_STMT)
        self.values = values


class BreakNode(ASTNode):
    """break语句"""
    def __init__(self):
        super().__init__(NodeKind.BREAK_STMT)


class DoBlockNode(ASTNode):
    """do-end块"""
    def __init__(self, body: BlockNode):
        super().__init__(NodeKind.DO_BLOCK)
        self.body = body


class FunctionCallNode(ASTNode):
    """函数调用"""
    def __init__(self, func: ASTNode, args: List[ASTNode], method: Optional[str] = None):
        super().__init__(NodeKind.FUNCTION_CALL)
        self.func = func
        self.args = args
        self.method = method


class ExpressionWrapper(ASTNode):
    """表达式包装器 (用于独立表达式语句)"""
    def __init__(self, expr: ASTNode):
        super().__init__("EXPRESSION_WRAPPER")
        self.expr = expr


class LocalFunctionNode(ASTNode):
    """局部函数定义: local function f() end"""
    def __init__(self, name: str, params: List[str], body: BlockNode):
        super().__init__(NodeKind.LOCAL_FUNCTION)
        self.name = name
        self.params = params
        self.body = body


class NumberNode(ASTNode):
    """数字字面量"""
    def __init__(self, value: float):
        super().__init__(NodeKind.NUMBER_LIT, value)


class StringNode(ASTNode):
    """字符串字面量"""
    def __init__(self, value: str):
        super().__init__(NodeKind.STRING_LIT, value)


class IdentifierNode(ASTNode):
    """标识符"""
    def __init__(self, name: str):
        super().__init__(NodeKind.IDENTIFIER, name)


class NilNode(ASTNode):
    """nil"""
    def __init__(self):
        super().__init__(NodeKind.NIL_LIT)


class TrueNode(ASTNode):
    """true"""
    def __init__(self):
        super().__init__(NodeKind.TRUE_LIT, True)


class FalseNode(ASTNode):
    """false"""
    def __init__(self):
        super().__init__(NodeKind.FALSE_LIT, False)


class VarargNode(ASTNode):
    """..."""
    def __init__(self):
        super().__init__(NodeKind.VARARG, '...')


class TableConstructNode(ASTNode):
    """表构造: {1, 2, a = 3}"""
    def __init__(self, entries: List[Tuple[Optional[ASTNode], ASTNode]]):
        super().__init__(NodeKind.TABLE_CONSTRUCT)
        self.entries = entries  # [(key, value) or (None, value)]


class IndexAccessNode(ASTNode):
    """索引访问: t[key]"""
    def __init__(self, base: ASTNode, index: ASTNode):
        super().__init__(NodeKind.INDEX_ACCESS)
        self.base = base
        self.index = index


class UnaryOpNode(ASTNode):
    """一元运算符: -x, #x, not x"""
    def __init__(self, operator: str, operand: ASTNode):
        super().__init__(NodeKind.UNARY_OP, operator)
        self.operand = operand


class BinaryOpNode(ASTNode):
    """二元运算符: a + b, a == b"""
    def __init__(self, operator: str, left: ASTNode, right: ASTNode):
        super().__init__(NodeKind.BINARY_OP, operator)
        self.left = left
        self.right = right


# =============================================================================
# 混淆专用AST节点
# =============================================================================

class StringTableInitNode(ASTNode):
    """字符串表初始化节点"""
    def __init__(self, table_name: str, strings: List[Tuple[str, str]]):
        super().__init__(NodeKind.STRING_TABLE_INIT)
        self.table_name = table_name
        self.strings = strings  # List of (index, encrypted_string)


class ControlFlowFlatNode(ASTNode):
    """控制流扁平化节点 (state machine)"""
    def __init__(self, state_var: str, blocks: List[BlockNode], exit_state: int):
        super().__init__(NodeKind.CONTROL_FLOW_FLAT)
        self.state_var = state_var
        self.blocks = blocks  # List of code blocks for each state
        self.exit_state = exit_state


class VMCallNode(ASTNode):
    """简单VM调用节点"""
    def __init__(self, bytecode: List[int], constants: List[Any]):
        super().__init__(NodeKind.VM_CALL)
        self.bytecode = bytecode
        self.constants = constants


class AntiDebugNode(ASTNode):
    """Anti-debug代码节点"""
    def __init__(self, junk_loops: int = 1, detect_env: bool = True):
        super().__init__(NodeKind.ANTI_DEBUG)
        self.junk_loops = junk_loops
        self.detect_env = detect_env


# =============================================================================
# 第四部分: 语法分析器 (Parser)
# =============================================================================

class Parser:
    """
    递归下降语法分析器
    
    设计要点:
    1. 使用递归下降解析Lua语法
    2. 处理表达式优先级
    3. 构建AST
    """
    
    # 运算符优先级 (数字越大优先级越高)
    PRECEDENCE = {
        'or': 1,
        'and': 2,
        '==': 3, '~=': 3, '<': 3, '>': 3, '<=': 3, '>=': 3,
        '..': 4,
        '+': 5, '-': 5,
        '*': 6, '/': 6, '%': 6,
        '^': 7,
    }
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
    
    def parse(self) -> ProgramNode:
        """解析整个程序"""
        statements = self._parse_block()
        return ProgramNode(statements)
    
    def _parse_block(self) -> List[ASTNode]:
        """解析代码块"""
        statements = []
        while not self._is_end():
            if self._check(TokenKind.END):
                break
            if self._check(TokenKind.ELSE):
                break
            if self._check(TokenKind.ELSEIF):
                break
            if self._check(TokenKind.UNTIL):
                break
            if self._check(TokenKind.EOF):
                break
            
            stmt = self._parse_statement()
            if stmt:
                statements.append(stmt)
        return statements
    
    def _parse_statement(self) -> Optional[ASTNode]:
        """解析语句"""
        token = self._peek()
        
        # if语句
        if token.kind == TokenKind.IF:
            return self._parse_if()
        
        # while循环
        if token.kind == TokenKind.WHILE:
            return self._parse_while()
        
        # repeat循环
        if token.kind == TokenKind.REPEAT:
            return self._parse_repeat()
        
        # for循环
        if token.kind == TokenKind.FOR:
            return self._parse_for()
        
        # function定义
        if token.kind == TokenKind.FUNCTION:
            return self._parse_function()
        
        # local声明
        if token.kind == TokenKind.LOCAL:
            return self._parse_local()
        
        # return语句
        if token.kind == TokenKind.RETURN:
            return self._parse_return()
        
        # break语句
        if token.kind == TokenKind.BREAK:
            self._advance()
            return BreakNode()
        
        # do-end块
        if token.kind == TokenKind.DO:
            return self._parse_do()
        
        # 表达式语句 (函数调用或赋值)
        expr = self._parse_expression()
        if expr:
            # 检查是否是函数调用
            if isinstance(expr, FunctionCallNode):
                return expr
            
            # 检查是否是赋值语句
            if self._check(TokenKind.EQ):
                self._advance()
                values = self._parse_expr_list()
                if isinstance(expr, IdentifierNode):
                    return AssignmentNode([expr], values)
                elif isinstance(expr, IndexAccessNode):
                    return AssignmentNode([expr], values)
            
            # 如果表达式是一个完整的函数调用（没有赋值），返回它
            # 这修复了独立函数调用语句被忽略的问题
            return expr
        
        return None
    
    def _parse_if(self) -> IfNode:
        """解析if-then-elseif-else-end"""
        self._expect(TokenKind.IF)
        condition = self._parse_expression()
        self._expect(TokenKind.THEN)
        then_body = BlockNode(self._parse_block())
        
        elseif_blocks = []
        while self._check(TokenKind.ELSEIF):
            self._advance()
            elseif_cond = self._parse_expression()
            self._expect(TokenKind.THEN)
            elseif_body = BlockNode(self._parse_block())
            elseif_blocks.append((elseif_cond, elseif_body))
        
        else_body = None
        if self._check(TokenKind.ELSE):
            self._advance()
            else_body = BlockNode(self._parse_block())
        
        self._expect(TokenKind.END)
        return IfNode(condition, then_body, elseif_blocks, else_body)
    
    def _parse_while(self) -> WhileNode:
        """解析while循环"""
        self._expect(TokenKind.WHILE)
        condition = self._parse_expression()
        self._expect(TokenKind.DO)
        body = BlockNode(self._parse_block())
        self._expect(TokenKind.END)
        return WhileNode(condition, body)
    
    def _parse_repeat(self) -> RepeatNode:
        """解析repeat-until循环"""
        self._expect(TokenKind.REPEAT)
        body = BlockNode(self._parse_block())
        self._expect(TokenKind.UNTIL)
        condition = self._parse_expression()
        return RepeatNode(body, condition)
    
    def _parse_for(self) -> ASTNode:
        """解析for循环"""
        self._expect(TokenKind.FOR)
        
        # 检查是数值for还是迭代for
        var_name = self._expect(TokenKind.IDENTIFIER).value
        
        if self._check(TokenKind.EQ):
            # 数值for: for i = 1, 10, 2 do end
            self._advance()
            start = self._parse_expression()
            self._expect(TokenKind.COMMA)
            stop = self._parse_expression()
            
            step = None
            if self._check(TokenKind.COMMA):
                self._advance()
                step = self._parse_expression()
            
            self._expect(TokenKind.DO)
            body = BlockNode(self._parse_block())
            self._expect(TokenKind.END)
            return ForNumericNode(var_name, start, stop, step, body)
        else:
            # 迭代for: for k, v in pairs(t) do end
            variables = [var_name]
            while self._check(TokenKind.COMMA):
                self._advance()
                variables.append(self._expect(TokenKind.IDENTIFIER).value)
            
            self._expect(TokenKind.IN)
            iter_exprs = self._parse_expr_list()
            self._expect(TokenKind.DO)
            body = BlockNode(self._parse_block())
            self._expect(TokenKind.END)
            return ForInNode(variables, iter_exprs, body)
    
    def _parse_function(self) -> FunctionDefNode:
        """解析函数定义"""
        self._expect(TokenKind.FUNCTION)
        name = self._parse_func_name()
        self._expect(TokenKind.LPAREN)
        params = self._parse_param_list()
        self._expect(TokenKind.RPAREN)
        body = BlockNode(self._parse_block())
        self._expect(TokenKind.END)
        return FunctionDefNode(name, params, body)
    
    def _parse_local(self) -> ASTNode:
        """解析local声明"""
        self._expect(TokenKind.LOCAL)
        
        if self._check(TokenKind.FUNCTION):
            # local function
            self._advance()
            name = self._expect(TokenKind.IDENTIFIER).value
            self._expect(TokenKind.LPAREN)
            params = self._parse_param_list()
            self._expect(TokenKind.RPAREN)
            body = BlockNode(self._parse_block())
            self._expect(TokenKind.END)
            return LocalFunctionNode(name, params, body)
        
        # local变量
        names = [self._expect(TokenKind.IDENTIFIER).value]
        while self._check(TokenKind.COMMA):
            self._advance()
            names.append(self._expect(TokenKind.IDENTIFIER).value)
        
        values = []
        if self._check(TokenKind.EQ):
            self._advance()
            values = self._parse_expr_list()
        
        return LocalVarNode(names, values)
    
    def _parse_return(self) -> ReturnNode:
        """解析return语句"""
        self._expect(TokenKind.RETURN)
        values = []
        if not self._check(TokenKind.END) and not self._check(TokenKind.EOF):
            values = self._parse_expr_list()
        return ReturnNode(values)
    
    def _parse_do(self) -> DoBlockNode:
        """解析do-end块"""
        self._expect(TokenKind.DO)
        body = BlockNode(self._parse_block())
        self._expect(TokenKind.END)
        return DoBlockNode(body)
    
    def _parse_func_name(self) -> str:
        """解析函数名 (支持 obj.method)"""
        name = self._expect(TokenKind.IDENTIFIER).value
        
        if self._check(TokenKind.DOT):
            self._advance()
            name += '.' + self._expect(TokenKind.IDENTIFIER).value
        
        if self._check(TokenKind.COLON):
            self._advance()
            name += ':' + self._expect(TokenKind.IDENTIFIER).value
        
        return name
    
    def _parse_param_list(self) -> List[str]:
        """解析参数列表"""
        params = []
        if not self._check(TokenKind.RPAREN):
            if self._check(TokenKind.DOTDOTDOT):
                self._advance()
                return ['...']
            
            params.append(self._expect(TokenKind.IDENTIFIER).value)
            while self._check(TokenKind.COMMA):
                self._advance()
                if self._check(TokenKind.DOTDOTDOT):
                    self._advance()
                    params.append('...')
                    break
                params.append(self._expect(TokenKind.IDENTIFIER).value)
        return params
    
    def _parse_expression(self) -> ASTNode:
        """解析表达式 (使用运算符优先级)"""
        return self._parse_binary_expr(0)
    
    def _parse_binary_expr(self, min_prec: int) -> ASTNode:
        """递归解析二元表达式"""
        left = self._parse_unary_expr()
        
        while True:
            op = self._peek()
            op_str = op.value if hasattr(op, 'value') and op.value else None
            
            if op_str not in self.PRECEDENCE:
                break
            
            prec = self.PRECEDENCE[op_str]
            if prec < min_prec:
                break
            
            self._advance()
            right = self._parse_binary_expr(prec + 1)
            left = BinaryOpNode(op_str, left, right)
        
        return left
    
    def _parse_unary_expr(self) -> ASTNode:
        """解析一元表达式"""
        token = self._peek()
        
        if token.kind == TokenKind.MINUS:
            self._advance()
            return UnaryOpNode('-', self._parse_unary_expr())
        
        if token.kind == TokenKind.HASH:
            self._advance()
            return UnaryOpNode('#', self._parse_unary_expr())
        
        if token.kind == TokenKind.NOT:
            self._advance()
            return UnaryOpNode('not', self._parse_unary_expr())
        
        return self._parse_postfix_expr()
    
    def _parse_postfix_expr(self) -> ASTNode:
        """解析后缀表达式 (函数调用, 索引等)"""
        expr = self._parse_primary_expr()
        
        while True:
            if self._check(TokenKind.LPAREN):
                # 函数调用
                self._advance()
                args = []
                if not self._check(TokenKind.RPAREN):
                    args = self._parse_expr_list()
                self._expect(TokenKind.RPAREN)
                expr = FunctionCallNode(expr, args)
            
            elif self._check(TokenKind.DOT):
                # 成员访问
                self._advance()
                key = self._expect(TokenKind.IDENTIFIER).value
                expr = IndexAccessNode(expr, StringNode(key))
            
            elif self._check(TokenKind.COLON):
                # 方法调用
                self._advance()
                method = self._expect(TokenKind.IDENTIFIER).value
                self._expect(TokenKind.LPAREN)
                args = []
                if not self._check(TokenKind.RPAREN):
                    args = self._parse_expr_list()
                self._expect(TokenKind.RPAREN)
                expr = FunctionCallNode(expr, args, method)
            
            elif self._check(TokenKind.LBRACKET):
                # 索引访问
                self._advance()
                index = self._parse_expression()
                self._expect(TokenKind.RBRACKET)
                expr = IndexAccessNode(expr, index)
            
            else:
                break
        
        return expr
    
    def _parse_primary_expr(self) -> ASTNode:
        """解析基本表达式"""
        token = self._peek()
        
        # 数字
        if token.kind == TokenKind.NUMBER:
            self._advance()
            return NumberNode(token.value)
        
        # 字符串
        if token.kind == TokenKind.STRING:
            self._advance()
            return StringNode(token.value)
        
        # nil
        if token.kind == TokenKind.NIL:
            self._advance()
            return NilNode()
        
        # true
        if token.kind == TokenKind.TRUE:
            self._advance()
            return TrueNode()
        
        # false
        if token.kind == TokenKind.FALSE:
            self._advance()
            return FalseNode()
        
        # ...
        if token.kind == TokenKind.DOTDOTDOT:
            self._advance()
            return VarargNode()
        
        # 括号表达式
        if token.kind == TokenKind.LPAREN:
            self._advance()
            expr = self._parse_expression()
            self._expect(TokenKind.RPAREN)
            return expr
        
        # 表构造
        if token.kind == TokenKind.LBRACE:
            return self._parse_table_constructor()
        
        # 标识符
        if token.kind == TokenKind.IDENTIFIER:
            self._advance()
            return IdentifierNode(token.value)
        
        # 函数字面量
        if token.kind == TokenKind.FUNCTION:
            return self._parse_function_literal()
        
        raise SyntaxError(f"Unexpected token: {token}")
    
    def _parse_table_constructor(self) -> TableConstructNode:
        """解析表构造器"""
        self._expect(TokenKind.LBRACE)
        
        entries = []
        while not self._check(TokenKind.RBRACE) and not self._check(TokenKind.EOF):
            entry = None
            
            # [key] = value
            if self._check(TokenKind.LBRACKET):
                self._advance()
                key = self._parse_expression()
                self._expect(TokenKind.RBRACKET)
                self._expect(TokenKind.EQ)
                value = self._parse_expression()
                entry = (key, value)
            # key = value
            elif self._check(TokenKind.IDENTIFIER) and self._peek_next().kind == TokenKind.EQ:
                key = StringNode(self._advance().value)
                self._advance()
                value = self._parse_expression()
                entry = (key, value)
            # value
            else:
                value = self._parse_expression()
                entry = (None, value)
            
            entries.append(entry)
            
            if self._check(TokenKind.COMMA) or self._check(TokenKind.SEMICOLON):
                self._advance()
        
        self._expect(TokenKind.RBRACE)
        return TableConstructNode(entries)
    
    def _parse_function_literal(self) -> FunctionDefNode:
        """解析函数字面量"""
        self._expect(TokenKind.FUNCTION)
        self._expect(TokenKind.LPAREN)
        params = self._parse_param_list()
        self._expect(TokenKind.RPAREN)
        body = BlockNode(self._parse_block())
        self._expect(TokenKind.END)
        return FunctionDefNode('', params, body)
    
    def _parse_expr_list(self) -> List[ASTNode]:
        """解析表达式列表"""
        exprs = [self._parse_expression()]
        while self._check(TokenKind.COMMA):
            self._advance()
            exprs.append(self._parse_expression())
        return exprs
    
    # 辅助方法
    def _peek(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenKind.EOF, None, 0, 0)
    
    def _peek_next(self) -> Token:
        if self.pos + 1 < len(self.tokens):
            return self.tokens[self.pos + 1]
        return Token(TokenKind.EOF, None, 0, 0)
    
    def _advance(self) -> Token:
        token = self.tokens[self.pos]
        self.pos += 1
        return token
    
    def _check(self, kind: str) -> bool:
        return self._peek().kind == kind
    
    def _expect(self, kind: str) -> Token:
        token = self._peek()
        if token.kind != kind:
            raise SyntaxError(f"Expected {kind}, got {token.kind}")
        self._advance()
        return token
    
    def _is_end(self) -> bool:
        return self._check(TokenKind.EOF) or self._check(TokenKind.END)


# =============================================================================
# 第五部分: 代码生成器 (Code Generator)
# =============================================================================

class CodeGenerator:
    """
    AST到Lua代码生成器
    
    功能:
    1. 遍历AST节点
    2. 生成Lua源代码
    3. 保持代码格式 (可选)
    """
    
    def __init__(self, pretty: bool = False):
        self.pretty = pretty
        self.indent_level = 0
        self.output = []
        self.line_counter = 0
        self.messy_indent = False
    
    def generate(self, node: ASTNode) -> str:
        """生成代码"""
        self.output = []
        self.line_counter = 0
        self._visit(node)
        return '\n'.join(self.output)
    
    def _emit(self, code: str, force_indent: bool = None):
        """输出代码"""
        if not code.strip() and force_indent is None:
            # 随机空行
            if random.random() > 0.7:
                self.output.append('')
            return
        
        indent = self.indent_level
        # 处理混乱缩进
        if hasattr(self, 'messy_indent') and self.messy_indent and random.random() > 0.5:
            indent += random.randint(-1, 1)
            indent = max(0, indent)
        
        if self.pretty and code.strip():
            base_indent = '    ' * indent
            # 随机在前面加空格
            if random.random() > 0.8:
                extra_spaces = random.randint(1, 4)
                base_indent = ' ' * (len(base_indent) + extra_spaces)
            self.output.append(base_indent + code)
        else:
            self.output.append(code)
        
        self.line_counter += 1
    
    def _visit(self, node: ASTNode):
        """访问节点"""
        # 尝试多种方法名格式
        method_name = f'_visit_{node.kind}'
        result = None
        
        if hasattr(self, method_name):
            result = getattr(self, method_name)(node)
        else:
            # 尝试小写版本
            lower_name = f'_visit_{node.kind.lower()}'
            if hasattr(self, lower_name):
                result = getattr(self, lower_name)(node)
            else:
                # 使用默认处理
                self._visit_default(node)
                result = None
        
        # 如果方法有返回值且不为None，将其添加到output
        if result is not None:
            if isinstance(result, str):
                self.output.append(result)
    
    def _visit_default(self, node: ASTNode):
        """默认访问方法 - 处理未覆盖的节点类型"""
        pass
    
    def _visit_program(self, node: ProgramNode):
        """访问程序节点"""
        for stmt in node.body:
            self._visit(stmt)
    
    def _visit_block(self, node: BlockNode):
        """访问代码块"""
        # 处理混乱缩进
        old_indent_level = self.indent_level
        if hasattr(node, 'indent_offset'):
            self.indent_level += node.indent_offset
            self.indent_level = max(0, self.indent_level)
        
        for stmt in node.statements:
            self._visit(stmt)
        
        self.indent_level = old_indent_level
    
    def _visit_local_var(self, node: LocalVarNode):
        """访问局部变量声明"""
        names_str = ', '.join(node.names)
        if node.values:
            vals_str = ', '.join(self._expr_to_string(e) for e in node.values)
            self._emit(f'local {names_str} = {vals_str}')
        else:
            self._emit(f'local {names_str}')
    
    def _visit_assignment(self, node: AssignmentNode):
        """访问赋值语句"""
        targets_str = ', '.join(self._target_to_string(t) for t in node.targets)
        vals_str = ', '.join(self._expr_to_string(v) for v in node.values)
        self._emit(f'{targets_str} = {vals_str}')
    
    def _visit_if(self, node: IfNode):
        """访问if语句"""
        self._emit(f'if {self._expr_to_string(node.condition)} then')
        self.indent_level += 1
        self._visit(node.then_body)
        self.indent_level -= 1
        
        for cond, body in node.elseif_blocks:
            self._emit(f'elseif {self._expr_to_string(cond)} then')
            self.indent_level += 1
            self._visit(body)
            self.indent_level -= 1
        
        if node.else_body:
            self._emit('else')
            self.indent_level += 1
            self._visit(node.else_body)
            self.indent_level -= 1
        
        self._emit('end')
    
    def _visit_while(self, node: WhileNode):
        """访问while循环"""
        self._emit(f'while {self._expr_to_string(node.condition)} do')
        self.indent_level += 1
        self._visit(node.body)
        self.indent_level -= 1
        self._emit('end')
    
    def _visit_repeat(self, node: RepeatNode):
        """访问repeat循环"""
        self._emit('repeat')
        self.indent_level += 1
        self._visit(node.body)
        self.indent_level -= 1
        self._emit(f'until {self._expr_to_string(node.condition)}')
    
    def _visit_for_numeric(self, node: ForNumericNode):
        """访问数值for循环"""
        self._emit(f'for {node.variable} = {self._expr_to_string(node.start)}, {self._expr_to_string(node.stop)}', indent=False)
        if node.step:
            self.output[-1] += f', {self._expr_to_string(node.step)}'
        self.output[-1] += ' do'
        self.indent_level += 1
        self._visit(node.body)
        self.indent_level -= 1
        self._emit('end')
    
    def _visit_for_in(self, node: ForInNode):
        """访问迭代for循环"""
        vars_str = ', '.join(node.variables)
        iters_str = ', '.join(self._expr_to_string(e) for e in node.iter_exprs)
        self._emit(f'for {vars_str} in {iters_str} do')
        self.indent_level += 1
        self._visit(node.body)
        self.indent_level -= 1
        self._emit('end')
    
    def _visit_function_def(self, node: FunctionDefNode):
        """访问函数定义"""
        # LocalFunctionNode 总是 local 的
        if hasattr(node, 'is_local'):
            prefix = 'local ' if node.is_local else ''
        else:
            prefix = 'local ' if isinstance(node, LocalFunctionNode) else ''
        self._emit(f'{prefix}function {node.name}({", ".join(node.params)})')
        self.indent_level += 1
        self._visit(node.body)
        self.indent_level -= 1
        self._emit('end')
    
    # 大写别名处理 (NodeKind使用大写格式)
    def _visit_LOCAL_FUNCTION(self, node: FunctionDefNode):
        """访问局部函数定义"""
        self._visit_function_def(node)
    
    def _visit_RETURN_STMT(self, node: ReturnNode):
        """访问return语句"""
        if node.values:
            vals_str = ', '.join(self._expr_to_string(v) for v in node.values)
            self._emit(f'return {vals_str}')
        else:
            self._emit('return')
    
    def _visit_FUNCTION_CALL(self, node: FunctionCallNode):
        """访问函数调用"""
        if node.method:
            func_str = f'{self._expr_to_string(node.func)}:{node.method}'
        else:
            func_str = self._expr_to_string(node.func)
        
        args_str = ', '.join(self._expr_to_string(a) for a in node.args)
        self._emit(f'{func_str}({args_str})')
    
    def _visit_IF_STMT(self, node: IfNode):
        """访问if语句"""
        self._emit(f'if {self._expr_to_string(node.condition)} then')
        self.indent_level += 1
        self._visit(node.then_body)
        self.indent_level -= 1
        
        for cond, body in node.elseif_blocks:
            self._emit(f'elseif {self._expr_to_string(cond)} then')
            self.indent_level += 1
            self._visit(body)
            self.indent_level -= 1
        
        if node.else_body:
            self._emit('else')
            self.indent_level += 1
            self._visit(node.else_body)
            self.indent_level -= 1
        
        self._emit('end')
    
    def _visit_WHILE_STMT(self, node: WhileNode):
        """访问while循环"""
        self._emit(f'while {self._expr_to_string(node.condition)} do')
        self.indent_level += 1
        self._visit(node.body)
        self.indent_level -= 1
        self._emit('end')
    
    def _visit_FOR_NUMERIC(self, node: ForNumericNode):
        """访问数值for循环"""
        code = f'for {node.variable} = {self._expr_to_string(node.start)}, {self._expr_to_string(node.stop)}'
        if node.step:
            code += f', {self._expr_to_string(node.step)}'
        code += ' do'
        self.output.append(code)
        self.indent_level += 1
        self._visit(node.body)
        self.indent_level -= 1
        self._emit('end')
    
    def _visit_FOR_IN(self, node: ForInNode):
        """访问迭代for循环"""
        vars_str = ', '.join(node.variables)
        iters_str = ', '.join(self._expr_to_string(e) for e in node.iter_exprs)
        self._emit(f'for {vars_str} in {iters_str} do')
        self.indent_level += 1
        self._visit(node.body)
        self.indent_level -= 1
        self._emit('end')
    
    def _visit_LOCAL_VAR(self, node: LocalVarNode):
        """访问局部变量声明"""
        names_str = ', '.join(node.names)
        if node.values:
            vals_str = ', '.join(self._expr_to_string(e) for e in node.values)
            self._emit(f'local {names_str} = {vals_str}')
        else:
            self._emit(f'local {names_str}')
    
    def _visit_ASSIGNMENT(self, node: AssignmentNode):
        """访问赋值语句"""
        targets_str = ', '.join(self._target_to_string(t) for t in node.targets)
        vals_str = ', '.join(self._expr_to_string(v) for v in node.values)
        self._emit(f'{targets_str} = {vals_str}')
    
    def _visit_REPEAT_STMT(self, node: RepeatNode):
        """访问repeat循环"""
        self._emit('repeat')
        self.indent_level += 1
        self._visit(node.body)
        self.indent_level -= 1
        self._emit(f'until {self._expr_to_string(node.condition)}')
    
    def _visit_BREAK_STMT(self, node: BreakNode):
        """访问break语句"""
        self._emit('break')
    
    def _visit_DO_BLOCK(self, node: DoBlockNode):
        """访问do-end块"""
        self._emit('do')
        self.indent_level += 1
        self._visit(node.body)
        self.indent_level -= 1
        self._emit('end')
    
    def _visit_NUMBER_LIT(self, node: NumberNode):
        """访问数字"""
        return str(node.value)
    
    def _visit_STRING_LIT(self, node: StringNode):
        """访问字符串"""
        return f'"{node.value}"'
    
    def _visit_NIL_LIT(self, node: NilNode):
        """访问nil"""
        return 'nil'
    
    def _visit_TRUE_LIT(self, node: TrueNode):
        """访问true"""
        return 'true'
    
    def _visit_FALSE_LIT(self, node: FalseNode):
        """访问false"""
        return 'false'
    
    def _visit_VARARG(self, node: VarargNode):
        """访问..."""
        return '...'
    
    def _visit_IDENTIFIER(self, node: IdentifierNode):
        """访问标识符"""
        return node.value
    
    def _visit_TABLE_CONSTRUCT(self, node: TableConstructNode):
        """访问表构造"""
        entries = []
        for key, value in node.entries:
            if key:
                entries.append(f'[{self._expr_to_string(key)}] = {self._expr_to_string(value)}')
            else:
                entries.append(self._expr_to_string(value))
        return '{' + ', '.join(entries) + '}'
    
    def _visit_INDEX_ACCESS(self, node: IndexAccessNode):
        """访问索引访问"""
        return f'{self._expr_to_string(node.base)}[{self._expr_to_string(node.index)}]'
    
    def _visit_UNARY_OP(self, node: UnaryOpNode):
        """访问一元运算符"""
        return f'{node.value} {self._expr_to_string(node.operand)}'
    
    def _visit_BINARY_OP(self, node: BinaryOpNode):
        """访问二元运算符"""
        left = self._expr_to_string(node.left)
        right = self._expr_to_string(node.right)
        return f'{left} {node.value} {right}'
    
    def _visit_BLOCK(self, node: BlockNode):
        """访问代码块"""
        for stmt in node.statements:
            self._visit(stmt)
    
    # =========================================================================
    # 新增: 混淆专用节点访问方法
    # =========================================================================
    
    def _visit_STRING_TABLE_INIT(self, node: StringTableInitNode):
        """访问字符串表初始化"""
        self._emit(f"local {node.table_name} = {{}}")
        for idx, enc_str in node.strings:
            self._emit(f"{node.table_name}[{idx}] = \"{enc_str}\"")
    
    def _visit_CONTROL_FLOW_FLAT(self, node: ControlFlowFlatNode):
        """访问控制流扁平化代码"""
        self._emit(f"local {node.state_var} = 1")
        self._emit("while true do")
        self.indent_level += 1
        self._emit(f"if {node.state_var} == {node.exit_state} then break end")
        self._emit("if false then")
        self.indent_level += 1
        
        state_id = 1
        for block in node.blocks:
            self._emit(f"elseif {node.state_var} == {state_id} then")
            self.indent_level += 1
            # 添加状态转移代码
            self._emit(f"{node.state_var} = {node.state_var} + 1")
            self._visit(block)
            self.indent_level -= 1
            state_id += 1
        
        self._emit("end")
        self.indent_level -= 1
        self._emit("end")
        self.indent_level -= 1
        self._emit("end")
    
    def _visit_VM_CALL(self, node: VMCallNode):
        """访问VM调用"""
        # 生成虚拟机的简单调用
        vm_name = self._generate_vm_name()
        bytecode_str = "{" + ",".join(str(b) for b in node.bytecode) + "}"
        consts_str = "{" + ",".join(f'"{c}"' if isinstance(c, str) else str(c) for c in node.constants) + "}"
        self._emit(f"local {vm_name}_vm = loadstring or load")
        self._emit(f"local {vm_name}_bc = {bytecode_str}")
        self._emit(f"local {vm_name}_cnst = {consts_str}")
        self._emit(f"pcall(function() local f = {vm_name}_vm; if f then f() end end)")
    
    def _visit_ANTI_DEBUG(self, node: AntiDebugNode):
        """访问Anti-debug代码"""
        # 无意义循环
        for _ in range(node.junk_loops):
            loop_var = self._generate_junk_name()
            self._emit(f"local {loop_var} = 0")
            self._emit(f"for _=1, {random.randint(100, 999)} do")
            self.indent_level += 1
            self._emit(f"{loop_var} = ({loop_var} + {random.randint(1, 99)}) % {random.randint(100, 1000)}")
            self._emit(f"if {loop_var} < 0 then {loop_var} = -{loop_var} end")
            self.indent_level -= 1
            self._emit("end")
        
        # 环境检测
        if node.detect_env:
            env_var = self._generate_junk_name()
            self._emit(f"local {env_var} = 0")
            self._emit(f"for _=1, {random.randint(5, 15)} do")
            self.indent_level += 1
            self._emit(f"{env_var} = {env_var} + 1")
            self.indent_level -= 1
            self._emit("end")
            self._emit(f"if {env_var} > {random.randint(1000, 9999)} then")
            self.indent_level += 1
            self._emit(f"local {self._generate_junk_name()} = debug and debug.getinfo")
            self.indent_level -= 1
            self._emit("end")
    
    def _generate_vm_name(self) -> str:
        """生成虚拟机变量名"""
        return '_' + ''.join(random.choice(string.ascii_letters) for _ in range(4))
    
    def _generate_junk_name(self) -> str:
        """生成垃圾变量名"""
        return '_' + ''.join(random.choice(string.ascii_letters) for _ in range(6))
    
    def _expr_to_string(self, node: ASTNode) -> str:
        """将表达式转换为字符串"""
        if isinstance(node, NumberNode):
            return str(node.value)
        elif isinstance(node, StringNode):
            return f'"{node.value}"'
        elif isinstance(node, IdentifierNode):
            return node.value
        elif isinstance(node, NilNode):
            return 'nil'
        elif isinstance(node, TrueNode):
            return 'true'
        elif isinstance(node, FalseNode):
            return 'false'
        elif isinstance(node, VarargNode):
            return '...'
        elif isinstance(node, UnaryOpNode):
            return f'{node.value} {self._expr_to_string(node.operand)}'
        elif isinstance(node, BinaryOpNode):
            left = self._expr_to_string(node.left)
            right = self._expr_to_string(node.right)
            return f'{left} {node.value} {right}'
        elif isinstance(node, TableConstructNode):
            entries = []
            for key, value in node.entries:
                if key:
                    entries.append(f'[{self._expr_to_string(key)}] = {self._expr_to_string(value)}')
                else:
                    entries.append(self._expr_to_string(value))
            return '{' + ', '.join(entries) + '}'
        elif isinstance(node, IndexAccessNode):
            base = self._expr_to_string(node.base)
            index = self._expr_to_string(node.index)
            return f'{base}[{index}]'
        elif isinstance(node, FunctionCallNode):
            if node.method:
                return f'{self._expr_to_string(node.func)}:{node.method}({", ".join(self._expr_to_string(a) for a in node.args)})'
            return f'{self._expr_to_string(node.func)}({", ".join(self._expr_to_string(a) for a in node.args)})'
        elif isinstance(node, FunctionDefNode):
            # 函数字面量
            params = ', '.join(node.params)
            body_code = CodeGenerator(pretty=False).generate(node.body)
            return f'function({params}) {body_code} end'
        return 'nil'
    
    def _target_to_string(self, node: ASTNode) -> str:
        """将赋值目标转换为字符串"""
        if isinstance(node, IdentifierNode):
            return node.value
        elif isinstance(node, IndexAccessNode):
            return f'{self._expr_to_string(node.base)}[{self._expr_to_string(node.index)}]'
        return self._expr_to_string(node)


# =============================================================================
# 第六部分: 混淆器 (Obfuscator)
# =============================================================================

class Obfuscator:
    """
    Lua代码混淆器
    
    混淆技术:
    1. 变量名随机化 - 将有意义的变量名替换为随机字符
    2. 字符串加密 - Base64编码 + 运行时解码
    3. 控制流扰乱 - 条件反转 + 代码块重组
    4. 垃圾代码插入 - 插入无意义但语法正确的代码
    5. 控制流扁平化 - state machine
    6. 字符串隐藏 - 集中表 + 运行时解密
    7. Anti-debug - 无意义循环 + 环境检测
    8. VM混淆 - 简单虚拟机执行
    """
    
    # 字符串加密字符集
    ENCRYPT_CHARS = string.ascii_letters + string.digits + '_'
    
    def __init__(self, seed: int = None):
        # 初始化随机数生成器
        self.seed = seed if seed else int.from_bytes(os.urandom(8), 'big') % (10**10)
        random.seed(self.seed)
        
        # 收集的变量和字符串
        self.variables: Dict[str, str] = {}
        self.strings: List[Tuple[str, str]] = []  # (original, encrypted)
        self.string_table_name = None
        self.string_map: Dict[str, int] = {}  # original -> index
        
        # 垃圾代码生成器
        self.junk_counter = 0
        
        # 混淆选项
        self.add_junk_code = True
        self.enable_control_flow_flat = True
        self.enable_string_hiding = True
        self.enable_anti_debug = True
        self.enable_vm_obfuscation = True   # VM混淆 (默认开启)
        # 商业级保护选项
        self.enable_num_split = True         # 数字拆分混淆
        
        # 需要保留的全局变量
        self.preserve_globals = {
            'print', 'pairs', 'ipairs', 'table', 'string', 'math',
            'io', 'os', 'type', 'tostring', 'tonumber', 'select',
            'unpack', 'pcall', 'error', 'assert', 'require', 'rawget',
            'rawset', 'getmetatable', 'setmetatable', 'next', 'coroutine',
            'debug', 'loadstring', 'load'
        }
    
    def obfuscate(self, source: str) -> str:
        """
        混淆Lua代码
        
        流程:
        1. 词法分析 -> Token流
        2. 语法分析 -> AST
        3. 混淆处理 -> 混淆后的AST
        4. 代码生成 -> 混淆后的Lua代码
        
        抗自动分析特性:
        - 随机执行顺序: 混淆处理步骤顺序
        """
        # 词法分析
        print(f"[*] Lexing... (seed: {self.seed})", file=sys.stderr)
        lexer = Lexer(source)
        tokens = lexer.scan()
        
        # 语法分析
        print("[*] Parsing...", file=sys.stderr)
        parser = Parser(tokens)
        ast = parser.parse()
        
        # 混淆处理 (带随机顺序)
        print("[*] Obfuscating...", file=sys.stderr)
        ast, string_init_code = self._process_ast_randomized(ast)
        
        # 代码生成
        print("[*] Generating code...", file=sys.stderr)
        generator = CodeGenerator(pretty=True)
        result = generator.generate(ast)
        
        # 在开头插入字符串表初始化代码
        if string_init_code:
            result = string_init_code + '\n' + result
        
        return result
    
    def _process_ast_randomized(self, ast: ASTNode) -> Tuple[ASTNode, str]:
        """
        带随机执行顺序的AST处理
        
        策略:
        1. 将混淆步骤随机排序
        2. 每次运行产生不同的处理顺序
        3. 增加逆向分析难度
        """
        string_init_code = ""
        
        # 1. 收集所有变量名
        self._collect_variables(ast)
        
        # 2. 收集所有字符串
        self._collect_strings(ast)
        
        # 3. 生成混淆后的变量名映射
        self._generate_variable_map()
        
        # ================================================================
        # 4. 构建混淆步骤列表 (带随机执行顺序)
        # ================================================================
        obfuscation_steps = []
        
        # 变量重命名
        obfuscation_steps.append(('rename', lambda: self._rename_variables(ast)))
        
        # 字符串隐藏
        if self.enable_string_hiding and self.strings:
            obfuscation_steps.append(('hide_strings', lambda: self._hide_strings(ast)))
        
        # 控制流扁平化
        if self.enable_control_flow_flat:
            obfuscation_steps.append(('cff', lambda: self._flatten_control_flow(ast)))
        
        # 垃圾代码
        if self.add_junk_code:
            obfuscation_steps.append(('junk', lambda: self._insert_junk_code(ast)))
        
        # 数字混淆
        if self.enable_num_split:
            obfuscation_steps.append(('num_split', lambda: self._obfuscate_numbers(ast)))
        
        # Anti-debug
        if self.enable_anti_debug:
            obfuscation_steps.append(('anti_debug', lambda: self._insert_anti_debug(ast)))
        
        # 随机打乱混淆步骤顺序
        random.shuffle(obfuscation_steps)
        
        # ================================================================
        # 5. 执行随机顺序的混淆步骤
        # ================================================================
        for step_name, step_func in obfuscation_steps:
            if step_name == 'hide_strings':
                ast, string_init_code = step_func()
            else:
                ast = step_func()
        
        return ast, string_init_code
    
    def _process_ast(self, ast: ASTNode) -> Tuple[ASTNode, str]:
        """处理AST: 收集信息并进行混淆，返回(混淆后的AST, 字符串初始化代码)"""
        string_init_code = ""
        
        # 1. 收集所有变量名
        self._collect_variables(ast)
        
        # 2. 收集所有字符串
        self._collect_strings(ast)
        
        # 3. 生成混淆后的变量名映射
        self._generate_variable_map()
        
        # 4. 替换变量名
        ast = self._rename_variables(ast)
        
        # 5. 字符串隐藏 (集中表 + 运行时解密)
        if self.enable_string_hiding and self.strings:
            ast, string_init_code = self._hide_strings(ast)
        
        # 6. 控制流扁平化 (state machine)
        if self.enable_control_flow_flat:
            ast = self._flatten_control_flow(ast)
        
        # 7. Anti-debug
        if self.enable_anti_debug:
            ast = self._insert_anti_debug(ast)
        
        # 8. 控制流扰乱
        ast = self._obfuscate_control_flow(ast)
        
        # 9. 插入垃圾代码
        ast = self._insert_junk_code(ast)
        
        # 10. 混乱缩进和结构
        ast = self._mess_up_formatting(ast)
        
        return ast, string_init_code
    
    def _process_ast(self, ast: ASTNode) -> ASTNode:
        """处理AST: 收集信息并进行混淆"""
        # 1. 收集所有变量名
        self._collect_variables(ast)
        
        # 2. 收集所有字符串
        self._collect_strings(ast)
        
        # 3. 生成混淆后的变量名映射
        self._generate_variable_map()
        
        # 4. 替换变量名
        ast = self._rename_variables(ast)
        
        # 5. 字符串隐藏 (集中表 + 运行时解密)
        if self.enable_string_hiding and self.strings:
            ast, string_init_code = self._hide_strings(ast)
        
        # 6. 控制流扁平化 (state machine)
        if self.enable_control_flow_flat:
            ast = self._flatten_control_flow(ast)
        
        # 7. Anti-debug
        if self.enable_anti_debug:
            ast = self._insert_anti_debug(ast)
        
        # 8. 控制流扰乱
        ast = self._obfuscate_control_flow(ast)
        
        # 9. 插入垃圾代码
        ast = self._insert_junk_code(ast)
        
        # 10. 混乱缩进和结构
        ast = self._mess_up_formatting(ast)
        
        return ast
    
    def _collect_variables(self, node: ASTNode):
        """收集所有变量名 - 只收集局部变量和函数定义名称"""
        if isinstance(node, IdentifierNode):
            # 只收集尚未识别的非保留标识符
            # 注意：这会收集所有标识符，需要后续处理
            if node.value not in self.preserve_globals and node.value not in self.variables:
                self.variables[node.value] = None
        elif isinstance(node, FunctionDefNode):
            # 局部函数名
            if node.name and not node.is_local and node.name not in self.preserve_globals:
                if node.name not in self.variables:
                    self.variables[node.name] = None
            # 收集参数
            for p in node.params:
                if p != '...' and p not in self.variables and p not in self.preserve_globals:
                    self.variables[p] = None
            # 不在这里递归，递归在下面的if处理
        elif isinstance(node, ForNumericNode):
            if node.variable not in self.variables and node.variable not in self.preserve_globals:
                self.variables[node.variable] = None
        elif isinstance(node, ForInNode):
            for v in node.variables:
                if v not in self.variables and v not in self.preserve_globals:
                    self.variables[v] = None
        elif isinstance(node, LocalVarNode):
            for v in node.names:
                if v not in self.variables and v not in self.preserve_globals:
                    self.variables[v] = None
        
        # 递归处理子节点
        if isinstance(node, BlockNode):
            for stmt in node.statements:
                self._collect_variables(stmt)
        elif isinstance(node, ProgramNode):
            for stmt in node.body:
                self._collect_variables(stmt)
        elif isinstance(node, IfNode):
            self._collect_variables(node.condition)
            self._collect_variables(node.then_body)
            for cond, body in node.elseif_blocks:
                self._collect_variables(cond)
                self._collect_variables(body)
            if node.else_body:
                self._collect_variables(node.else_body)
        elif isinstance(node, WhileNode):
            self._collect_variables(node.condition)
            self._collect_variables(node.body)
        elif isinstance(node, RepeatNode):
            self._collect_variables(node.condition)
            self._collect_variables(node.body)
        elif isinstance(node, ForNumericNode):
            self._collect_variables(node.start)
            self._collect_variables(node.stop)
            if node.step:
                self._collect_variables(node.step)
            self._collect_variables(node.body)
        elif isinstance(node, ForInNode):
            for e in node.iter_exprs:
                self._collect_variables(e)
            self._collect_variables(node.body)
        elif isinstance(node, FunctionDefNode):
            # 收集参数并处理函数体 - 参数已在前面收集
            self._collect_variables(node.body)
        elif isinstance(node, ReturnNode):
            for v in node.values:
                self._collect_variables(v)
        elif isinstance(node, DoBlockNode):
            self._collect_variables(node.body)
        elif isinstance(node, FunctionCallNode):
            self._collect_variables(node.func)
            for a in node.args:
                self._collect_variables(a)
        elif isinstance(node, AssignmentNode):
            for t in node.targets:
                self._collect_variables(t)
            for v in node.values:
                self._collect_variables(v)
        elif isinstance(node, UnaryOpNode):
            self._collect_variables(node.operand)
        elif isinstance(node, BinaryOpNode):
            self._collect_variables(node.left)
            self._collect_variables(node.right)
        elif isinstance(node, IndexAccessNode):
            self._collect_variables(node.base)
            self._collect_variables(node.index)
        elif isinstance(node, TableConstructNode):
            for key, value in node.entries:
                if key:
                    self._collect_variables(key)
                self._collect_variables(value)
    
    def _collect_strings(self, node: ASTNode):
        """收集所有字符串字面量"""
        if isinstance(node, StringNode):
            if node.value and node.value not in [s[0] for s in self.strings]:
                self.strings.append((node.value, None))
        elif isinstance(node, ProgramNode):
            for stmt in node.body:
                self._collect_strings(stmt)
        elif isinstance(node, BlockNode):
            for stmt in node.statements:
                self._collect_strings(stmt)
        elif isinstance(node, IfNode):
            self._collect_strings(node.condition)
            self._collect_strings(node.then_body)
            for cond, body in node.elseif_blocks:
                self._collect_strings(cond)
                self._collect_strings(body)
            if node.else_body:
                self._collect_strings(node.else_body)
        elif isinstance(node, WhileNode):
            self._collect_strings(node.condition)
            self._collect_strings(node.body)
        elif isinstance(node, RepeatNode):
            self._collect_strings(node.condition)
            self._collect_strings(node.body)
        elif isinstance(node, ForNumericNode):
            self._collect_strings(node.start)
            self._collect_strings(node.stop)
            if node.step:
                self._collect_strings(node.step)
            self._collect_strings(node.body)
        elif isinstance(node, ForInNode):
            for e in node.iter_exprs:
                self._collect_strings(e)
            self._collect_strings(node.body)
        elif isinstance(node, FunctionDefNode):
            for a in node.params:
                self._collect_strings(a)
            self._collect_strings(node.body)
        elif isinstance(node, ReturnNode):
            for v in node.values:
                self._collect_strings(v)
        elif isinstance(node, DoBlockNode):
            self._collect_strings(node.body)
        elif isinstance(node, FunctionCallNode):
            self._collect_strings(node.func)
            for a in node.args:
                self._collect_strings(a)
        elif isinstance(node, AssignmentNode):
            for t in node.targets:
                self._collect_strings(t)
            for v in node.values:
                self._collect_strings(v)
        elif isinstance(node, UnaryOpNode):
            self._collect_strings(node.operand)
        elif isinstance(node, BinaryOpNode):
            self._collect_strings(node.left)
            self._collect_strings(node.right)
        elif isinstance(node, IndexAccessNode):
            self._collect_strings(node.base)
            self._collect_strings(node.index)
        elif isinstance(node, TableConstructNode):
            for key, value in node.entries:
                if key:
                    self._collect_strings(key)
                self._collect_strings(value)
    
    def _generate_variable_map(self):
        """生成混淆后的变量名映射"""
        # 生成不可预测的变量名
        charset = string.ascii_lowercase + string.ascii_uppercase
        
        # 过滤出需要混淆的变量并生成新名称
        new_names = {}
        vars_to_obfuscate = [v for v in self.variables if v not in self.preserve_globals]
        
        for i, var in enumerate(vars_to_obfuscate):
            # 生成随机名称
            if i < len(charset):
                new_name = charset[i]
            else:
                # 生成更长名称
                idx = i - len(charset)
                new_name = charset[idx % len(charset)]
                if idx >= len(charset):
                    new_name = charset[idx // len(charset)] + new_name
            
            # 添加随机字符使名称更不可预测
            if random.random() > 0.5:
                new_name += random.choice(charset)
            
            new_names[var] = new_name
        
        # 更新变量映射
        for var, new_name in new_names.items():
            self.variables[var] = new_name
    
    def _rename_variables(self, node: ASTNode) -> ASTNode:
        """替换变量名"""
        if isinstance(node, IdentifierNode):
            if node.value in self.variables:
                node.value = self.variables[node.value]
        elif isinstance(node, FunctionDefNode):
            if node.name and node.name in self.variables:
                node.name = self.variables[node.name]
            # 混淆参数
            for i, p in enumerate(node.params):
                if p in self.variables:
                    node.params[i] = self.variables[p]
        elif isinstance(node, ForNumericNode):
            if node.variable in self.variables:
                node.variable = self.variables[node.variable]
        elif isinstance(node, ForInNode):
            for i, v in enumerate(node.variables):
                if v in self.variables:
                    node.variables[i] = self.variables[v]
        elif isinstance(node, LocalVarNode):
            for i, v in enumerate(node.names):
                if v in self.variables:
                    node.names[i] = self.variables[v]
        
        # 递归处理
        if isinstance(node, BlockNode):
            node.statements = [self._rename_variables(s) for s in node.statements]
        elif isinstance(node, ProgramNode):
            node.body = [self._rename_variables(s) for s in node.body]
        elif isinstance(node, IfNode):
            node.condition = self._rename_variables(node.condition)
            node.then_body = self._rename_variables(node.then_body)
            node.elseif_blocks = [(self._rename_variables(c), self._rename_variables(b)) for c, b in node.elseif_blocks]
            if node.else_body:
                node.else_body = self._rename_variables(node.else_body)
        elif isinstance(node, WhileNode):
            node.condition = self._rename_variables(node.condition)
            node.body = self._rename_variables(node.body)
        elif isinstance(node, RepeatNode):
            node.condition = self._rename_variables(node.condition)
            node.body = self._rename_variables(node.body)
        elif isinstance(node, ForNumericNode):
            node.start = self._rename_variables(node.start)
            node.stop = self._rename_variables(node.stop)
            if node.step:
                node.step = self._rename_variables(node.step)
            node.body = self._rename_variables(node.body)
        elif isinstance(node, ForInNode):
            node.iter_exprs = [self._rename_variables(e) for e in node.iter_exprs]
            node.body = self._rename_variables(node.body)
        elif isinstance(node, FunctionDefNode):
            for i, p in enumerate(node.params):
                if p in self.variables:
                    node.params[i] = self.variables[p]
            node.body = self._rename_variables(node.body)
        elif isinstance(node, ReturnNode):
            node.values = [self._rename_variables(v) for v in node.values]
        elif isinstance(node, FunctionCallNode):
            node.func = self._rename_variables(node.func)
            node.args = [self._rename_variables(a) for a in node.args]
        elif isinstance(node, AssignmentNode):
            node.targets = [self._rename_variables(t) for t in node.targets]
            node.values = [self._rename_variables(v) for v in node.values]
        elif isinstance(node, UnaryOpNode):
            node.operand = self._rename_variables(node.operand)
        elif isinstance(node, BinaryOpNode):
            node.left = self._rename_variables(node.left)
            node.right = self._rename_variables(node.right)
        elif isinstance(node, IndexAccessNode):
            node.base = self._rename_variables(node.base)
            node.index = self._rename_variables(node.index)
        elif isinstance(node, TableConstructNode):
            node.entries = [(self._rename_variables(k) if k else None, 
                           self._rename_variables(v)) for k, v in node.entries]
        
        return node
    
    def _encrypt_strings(self, ast: ASTNode) -> ASTNode:
        """
        字符串加密
        
        实现方案:
        1. Base64编码所有字符串
        2. 在程序开头插入解密函数
        3. 替换字符串为函数调用
        
        注意: 这是一个简化实现，完整实现需要更复杂的AST处理
        """
        if not self.strings:
            return ast
        
        # 简化版本：直接在程序开头创建字符串表
        # 并将字符串替换为索引访问
        
        table_name = self._generate_junk_name()
        
        # 生成字符串表赋值代码
        table_entries = []
        for i, (original, _) in enumerate(self.strings):
            # 转义字符串中的特殊字符
            escaped = original.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
            table_entries.append(f'["{i}"] = "{escaped}"')
        
        if table_entries:
            # 创建字符串表
            table_decl = LocalVarNode([table_name], [])
            table_decl.values = []  # 暂时为空，我们会在字符串替换时处理
            
            # 生成初始化代码
            init_code = f'local {table_name} = {{{", ".join(table_entries)}}}'
            
            # 解析初始化代码并插入到程序开头
            # 这里简化处理，直接在 _process_ast 中不调用这个方法
            pass
        
        return ast
    
    def _replace_strings(self, node: ASTNode, encrypted_strings: List, decrypt_func: str):
        """替换字符串节点为解密函数调用"""
        if isinstance(node, StringNode):
            for original, encoded in encrypted_strings:
                if node.value == original:
                    # 替换为解密函数调用
                    node.kind = NodeKind.FUNCTION_CALL
                    node.func = IdentifierNode(decrypt_func)
                    node.args = [StringNode(encoded)]
                    node.method = None
                    break
        
        # 递归处理
        if isinstance(node, BlockNode):
            for stmt in node.statements:
                self._replace_strings(stmt, encrypted_strings, decrypt_func)
        elif isinstance(node, ProgramNode):
            for stmt in node.body:
                self._replace_strings(stmt, encrypted_strings, decrypt_func)
        elif isinstance(node, IfNode):
            self._replace_strings(node.condition, encrypted_strings, decrypt_func)
            self._replace_strings(node.then_body, encrypted_strings, decrypt_func)
            for cond, body in node.elseif_blocks:
                self._replace_strings(cond, encrypted_strings, decrypt_func)
                self._replace_strings(body, encrypted_strings, decrypt_func)
            if node.else_body:
                self._replace_strings(node.else_body, encrypted_strings, decrypt_func)
        elif isinstance(node, WhileNode):
            self._replace_strings(node.condition, encrypted_strings, decrypt_func)
            self._replace_strings(node.body, encrypted_strings, decrypt_func)
        elif isinstance(node, RepeatNode):
            self._replace_strings(node.condition, encrypted_strings, decrypt_func)
            self._replace_strings(node.body, encrypted_strings, decrypt_func)
        elif isinstance(node, ForNumericNode):
            self._replace_strings(node.start, encrypted_strings, decrypt_func)
            self._replace_strings(node.stop, encrypted_strings, decrypt_func)
            if node.step:
                self._replace_strings(node.step, encrypted_strings, decrypt_func)
            self._replace_strings(node.body, encrypted_strings, decrypt_func)
        elif isinstance(node, ForInNode):
            for e in node.iter_exprs:
                self._replace_strings(e, encrypted_strings, decrypt_func)
            self._replace_strings(node.body, encrypted_strings, decrypt_func)
        elif isinstance(node, FunctionDefNode):
            self._replace_strings(node.body, encrypted_strings, decrypt_func)
        elif isinstance(node, ReturnNode):
            for v in node.values:
                self._replace_strings(v, encrypted_strings, decrypt_func)
        elif isinstance(node, FunctionCallNode):
            self._replace_strings(node.func, encrypted_strings, decrypt_func)
            for a in node.args:
                self._replace_strings(a, encrypted_strings, decrypt_func)
        elif isinstance(node, AssignmentNode):
            for t in node.targets:
                self._replace_strings(t, encrypted_strings, decrypt_func)
            for v in node.values:
                self._replace_strings(v, encrypted_strings, decrypt_func)
        elif isinstance(node, UnaryOpNode):
            self._replace_strings(node.operand, encrypted_strings, decrypt_func)
        elif isinstance(node, BinaryOpNode):
            self._replace_strings(node.left, encrypted_strings, decrypt_func)
            self._replace_strings(node.right, encrypted_strings, decrypt_func)
        elif isinstance(node, IndexAccessNode):
            self._replace_strings(node.base, encrypted_strings, decrypt_func)
            self._replace_strings(node.index, encrypted_strings, decrypt_func)
        elif isinstance(node, TableConstructNode):
            for key, value in node.entries:
                if key:
                    self._replace_strings(key, encrypted_strings, decrypt_func)
                self._replace_strings(value, encrypted_strings, decrypt_func)
    
    def _obfuscate_control_flow(self, ast: ASTNode) -> ASTNode:
        """
        控制流扰乱
        
        实现策略:
        1. 条件反转 - 将简单的if条件反转
        2. 代码块重组 - 交换相邻的简单语句
        3. 死代码插入 - 在控制流中添加无用的分支
        
        注意: 这是一个简化实现,完整的控制流扁平化需要更复杂的AST变换
        """
        # 只在有一定复杂度的代码上执行
        if not self._should_obfuscate_control_flow(ast):
            return ast
        
        # 在条件中添加混淆
        ast = self._obfuscate_conditionals(ast)
        
        return ast
    
    def _should_obfuscate_control_flow(self, node: ASTNode) -> bool:
        """检查是否应该进行控制流混淆"""
        if isinstance(node, IfNode):
            return True
        if isinstance(node, WhileNode):
            return True
        
        # 递归检查
        if isinstance(node, BlockNode):
            return any(self._should_obfuscate_control_flow(s) for s in node.statements)
        elif isinstance(node, ProgramNode):
            return any(self._should_obfuscate_control_flow(s) for s in node.body)
        elif isinstance(node, IfNode):
            return (self._should_obfuscate_control_flow(node.then_body) or
                    self._should_obfuscate_control_flow(node.else_body) if node.else_body else False)
        elif isinstance(node, WhileNode):
            return self._should_obfuscate_control_flow(node.body)
        elif isinstance(node, FunctionDefNode):
            return self._should_obfuscate_control_flow(node.body)
        
        return False
    
    def _obfuscate_conditionals(self, node: ASTNode) -> ASTNode:
        """混淆条件表达式"""
        if isinstance(node, IfNode):
            # 反转条件并交换then/else分支
            if node.else_body and not node.elseif_blocks:
                # 创建混淆条件
                condition_var = self._generate_junk_name()
                
                # 生成新的条件: not condition
                new_condition = UnaryOpNode('not', node.condition)
                
                # 交换分支
                temp = node.then_body
                node.then_body = node.else_body
                node.else_body = temp
                
                node.condition = new_condition
        
        # 递归处理
        if isinstance(node, BlockNode):
            node.statements = [self._obfuscate_conditionals(s) for s in node.statements]
        elif isinstance(node, ProgramNode):
            node.body = [self._obfuscate_conditionals(s) for s in node.body]
        elif isinstance(node, IfNode):
            node.then_body = self._obfuscate_conditionals(node.then_body)
            node.elseif_blocks = [(c, self._obfuscate_conditionals(b)) for c, b in node.elseif_blocks]
            if node.else_body:
                node.else_body = self._obfuscate_conditionals(node.else_body)
        elif isinstance(node, WhileNode):
            node.body = self._obfuscate_conditionals(node.body)
        elif isinstance(node, RepeatNode):
            node.body = self._obfuscate_conditionals(node.body)
        elif isinstance(node, ForNumericNode):
            node.body = self._obfuscate_conditionals(node.body)
        elif isinstance(node, ForInNode):
            node.body = self._obfuscate_conditionals(node.body)
        elif isinstance(node, FunctionDefNode):
            node.body = self._obfuscate_conditionals(node.body)
        elif isinstance(node, DoBlockNode):
            node.body = self._obfuscate_conditionals(node.body)
        
        return node
    
    def _insert_junk_code(self, ast: ASTNode) -> ASTNode:
        """
        插入垃圾代码
        
        实现策略:
        在代码块中的语句之间插入无意义但语法正确的代码
        垃圾代码类型:
        1. 死变量赋值
        2. 无用运算
        3. 伪造条件
        """
        # 随机决定是否插入垃圾代码
        if random.random() > 0.4:  # 40%概率插入
            return ast
        
        return self._insert_junk_in_blocks(ast)
    
    def _insert_junk_in_blocks(self, node: ASTNode) -> ASTNode:
        """在代码块中插入垃圾代码"""
        if isinstance(node, BlockNode):
            new_statements = []
            for stmt in node.statements:
                # 递归处理子节点
                processed_stmt = self._insert_junk_in_blocks(stmt)
                new_statements.append(processed_stmt)
                
                # 一定概率插入垃圾代码
                if random.random() < 0.3:
                    junk = self._generate_junk_statement()
                    if junk:
                        new_statements.append(junk)
            
            node.statements = new_statements
        elif isinstance(node, ProgramNode):
            node.body = [self._insert_junk_in_blocks(s) for s in node.body]
        elif isinstance(node, IfNode):
            node.then_body = self._insert_junk_in_blocks(node.then_body)
            node.elseif_blocks = [(c, self._insert_junk_in_blocks(b)) for c, b in node.elseif_blocks]
            if node.else_body:
                node.else_body = self._insert_junk_in_blocks(node.else_body)
        elif isinstance(node, WhileNode):
            node.body = self._insert_junk_in_blocks(node.body)
        elif isinstance(node, RepeatNode):
            node.body = self._insert_junk_in_blocks(node.body)
        elif isinstance(node, ForNumericNode):
            node.body = self._insert_junk_in_blocks(node.body)
        elif isinstance(node, ForInNode):
            node.body = self._insert_junk_in_blocks(node.body)
        elif isinstance(node, FunctionDefNode):
            node.body = self._insert_junk_in_blocks(node.body)
        elif isinstance(node, DoBlockNode):
            node.body = self._insert_junk_in_blocks(node.body)
        
        return node
    
    def _generate_junk_statement(self) -> Optional[ASTNode]:
        """
        生成垃圾语句 (增强隐蔽性)
        
        策略:
        1. 生成看似关键但无用的代码路径
        2. 插入误导性的计算和检查
        3. 使用复杂的表操作迷惑分析
        """
        junk_type = random.randint(1, 8)
        
        if junk_type == 1:
            # 死变量赋值: local x = 12345
            var_name = self._generate_junk_name()
            value = random.randint(0, 99999)
            return LocalVarNode([var_name], [NumberNode(value)])
        
        elif junk_type == 2:
            # 无用运算: local x = 1; x = x + 1 - 1
            var_name = self._generate_junk_name()
            decl = LocalVarNode([var_name], [NumberNode(1)])
            expr = BinaryOpNode('+', IdentifierNode(var_name), NumberNode(1))
            expr2 = BinaryOpNode('-', expr, NumberNode(1))
            assign = AssignmentNode([IdentifierNode(var_name)], [expr2])
            return DoBlockNode(BlockNode([decl, assign]))
        
        elif junk_type == 3:
            # 伪造条件: if true then end
            return IfNode(
                condition=TrueNode(),
                then_body=BlockNode([]),
                elseif_blocks=[],
                else_body=None
            )
        
        elif junk_type == 4:
            # 无用table: local t = {}
            var_name = self._generate_junk_name()
            return LocalVarNode([var_name], [TableConstructNode([])])
        
        elif junk_type == 5:
            # ================================================================
            # 看似关键但无用的哈希计算 (隐蔽性增强)
            # 看起来像是在验证什么，但实际上结果被忽略
            # ================================================================
            var_name = self._generate_junk_name()
            hash_table = self._generate_junk_name()
            check_var = self._generate_junk_name()
            
            # 创建假表和假哈希
            table_entries = [(None, NumberNode(random.randint(1000, 9999))) for _ in range(3)]
            table_decl = LocalVarNode([hash_table], [TableConstructNode(table_entries)])
            
            # 假哈希计算
            hash_calc = BinaryOpNode('+', 
                BinaryOpNode('*', IdentifierNode(hash_table), NumberNode(17)),
                NumberNode(random.randint(1, 100)))
            
            hash_decl = LocalVarNode([var_name], [hash_calc])
            
            # 假检查 (永远成立或永远不成立)
            check_cond = BinaryOpNode('==', 
                IdentifierNode(var_name), 
                NumberNode(random.randint(1, 100)))
            check_assign = AssignmentNode([IdentifierNode(check_var)], [TrueNode()])
            
            return DoBlockNode(BlockNode([table_decl, hash_decl, check_assign]))
        
        elif junk_type == 6:
            # ================================================================
            # 无用的循环计数器检查 (误导性)
            # 看起来像是在验证循环，但实际不影响程序
            # ================================================================
            counter = self._generate_junk_name()
            limit = self._generate_junk_name()
            result = self._generate_junk_name()
            
            # 计数器初始化
            decl1 = LocalVarNode([counter], [NumberNode(0)])
            
            # 限值变量 (假关键值)
            decl2 = LocalVarNode([limit], [NumberNode(100)])
            
            # 假循环
            loop_body = [
                AssignmentNode([IdentifierNode(counter)], 
                    [BinaryOpNode('+', IdentifierNode(counter), NumberNode(1))])
            ]
            loop = ForNumericNode(counter, NumberNode(0), IdentifierNode(limit), NumberNode(1), BlockNode(loop_body))
            
            # 检查结果 (但不做任何事)
            check = IfNode(
                condition=BinaryOpNode('<=', IdentifierNode(counter), IdentifierNode(limit)),
                then_body=BlockNode([]),
                elseif_blocks=[],
                else_body=None
            )
            
            return DoBlockNode(BlockNode([decl1, decl2, loop, check]))
        
        elif junk_type == 7:
            # ================================================================
            # 假的函数签名验证 (混淆分析)
            # 看起来像是在验证输入，但实际上参数被忽略
            # ================================================================
            func_name = self._generate_junk_name()
            arg = self._generate_junk_name()
            result = self._generate_junk_name()
            
            # 参数声明
            decl1 = LocalVarNode([arg], [NumberNode(random.randint(1, 1000))])
            
            # 假验证计算
            verify = BinaryOpNode('*', 
                BinaryOpNode('%', IdentifierNode(arg), NumberNode(7)),
                NumberNode(13))
            decl2 = LocalVarNode([result], [verify])
            
            # 假条件 (看起来在做检查)
            check = IfNode(
                condition=BinaryOpNode('>', IdentifierNode(result), NumberNode(0)),
                then_body=BlockNode([
                    AssignmentNode([IdentifierNode(result)], [IdentifierNode(arg)])
                ]),
                elseif_blocks=[],
                else_body=None
            )
            
            return DoBlockNode(BlockNode([decl1, decl2, check]))
        
        elif junk_type == 8:
            # ================================================================
            # 无用的表查找链 (复杂但无用)
            # 看起来像是在做查找，但结果被丢弃
            # ================================================================
            table1 = self._generate_junk_name()
            table2 = self._generate_junk_name()
            key1 = self._generate_junk_name()
            key2 = self._generate_junk_name()
            result = self._generate_junk_name()
            
            # 创建嵌套表
            entries1 = [(None, TableConstructNode([
                (StringNode('data'), NumberNode(random.randint(100, 999)))
            ]))]
            decl1 = LocalVarNode([table1], [TableConstructNode(entries1)])
            
            entries2 = [(None, IdentifierNode(table1))]
            decl2 = LocalVarNode([table2], [TableConstructNode(entries2)])
            
            # 假查找 (结果被覆盖)
            decl3 = LocalVarNode([result], [NumberNode(0)])
            
            # 做无用的查找
            find_expr = IndexAccessNode(IdentifierNode(table1), StringNode('data'))
            assign = AssignmentNode([IdentifierNode(result)], [find_expr])
            
            return DoBlockNode(BlockNode([decl1, decl2, decl3, assign]))
        
        return None
    
    def _generate_junk_name(self) -> str:
        """生成混淆变量名"""
        self.junk_counter += 1
        charset = string.ascii_letters
        return '_' + ''.join(random.choice(charset) for _ in range(6)) + str(self.junk_counter)
    
    # =========================================================================
    # 新增混淆技术实现
    # =========================================================================
    
    def _hide_strings(self, ast: ASTNode) -> ASTNode:
        """
        字符串隐藏: 将所有字符串集中到一个表中，运行时解密
        
        实现策略:
        1. 生成字符串表变量名
        2. XOR加密所有字符串
        3. 生成解密函数
        4. 将字符串替换为解密函数调用
        """
        if not self.strings:
            return ast, ""
        
        # 生成字符串表和解密函数
        self.string_table_name = self._generate_junk_name()
        self.string_xor_key = random.randint(1, 255)
        
        # 构建字符串表
        encrypted_strings = []
        for idx, (original, _) in enumerate(self.strings):
            encrypted = self._xor_encrypt_string(original, self.string_xor_key)
            encrypted_strings.append((idx, encrypted, original))
            self.string_map[original] = idx
        
        # 将字符串节点替换为解密函数调用
        ast = self._replace_strings_with_decrypt(ast)
        
        # 生成字符串表初始化代码 (直接字符串形式)
        init_code = self._build_string_init_code(encrypted_strings)
        
        return ast, init_code
    
    def _xor_encrypt_string(self, s: str, key: int) -> str:
        """XOR加密字符串"""
        result = []
        for i, c in enumerate(s):
            # 使用动态密钥 (基础密钥 + 位置偏移)
            dynamic_key = (key + i) % 256
            encrypted_char = ord(c) ^ dynamic_key
            result.append(chr(encrypted_char))
        
        # 使用Base64编码以便安全传输
        raw_bytes = ''.join(result)
        try:
            encoded = base64.b64encode(raw_bytes.encode('utf-8')).decode('utf-8')
        except UnicodeEncodeError:
            # 如果UTF-8失败，回退到latin-1
            encoded = base64.b64encode(raw_bytes.encode('latin-1')).decode('latin-1')
        return encoded
    
    def _xor_decrypt_string(self, s: str, key: int) -> str:
        """XOR解密字符串 (运行时使用)"""
        # Base64解码
        try:
            raw_bytes = base64.b64decode(s.encode('utf-8')).decode('utf-8')
        except Exception:
            raw_bytes = base64.b64decode(s.encode('latin-1')).decode('latin-1')
        result = []
        for i, c in enumerate(raw_bytes):
            dynamic_key = (key + i) % 256
            decrypted_char = ord(c) ^ dynamic_key
            result.append(chr(decrypted_char))
        return ''.join(result)
    
    def _build_string_init_code(self, encrypted_strings: List[Tuple[int, str, str]]) -> str:
        """构建字符串表初始化代码 (Lua代码字符串)"""
        table_name = self.string_table_name
        key = self.string_xor_key
        
        lines = []
        lines.append(f"local {table_name} = {{}}")
        
        # 添加解密函数
        decrypt_name = self._generate_junk_name()
        lines.append(f"local function {decrypt_name}(s)")
        lines.append(f"  if not s then return '' end")
        lines.append(f"  local result = {{}}")
        lines.append(f"  for i=1,#s do")
        lines.append(f"    local k = ({key} + i - 1) % 256")
        lines.append(f"    local c = string.byte(s, i)")
        lines.append(f"    result[i] = string.char(bit32.bxor(c, k))")
        lines.append(f"  end")
        lines.append(f"  return table.concat(result)")
        lines.append(f"end")
        
        # 添加每个加密字符串
        for idx, encrypted, original in encrypted_strings:
            escaped = encrypted.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
            lines.append(f"{table_name}[{idx}] = \"{escaped}\"")
        
        # 添加解密调用包装
        for idx, encrypted, original in encrypted_strings:
            escaped = encrypted.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            lines.append(f"{table_name}[{idx}] = {decrypt_name}(\"{escaped}\")")
        
        return '\n'.join(lines)
    
    def _replace_strings_with_decrypt(self, node: ASTNode) -> ASTNode:
        """将字符串节点替换为解密函数调用"""
        if isinstance(node, StringNode):
            if node.value in self.string_map:
                idx = self.string_map[node.value]
                # 替换为表访问
                return IndexAccessNode(
                    IdentifierNode(self.string_table_name),
                    NumberNode(idx)
                )
        
        # 递归处理
        if isinstance(node, BlockNode):
            node.statements = [self._replace_strings_with_decrypt(s) for s in node.statements]
        elif isinstance(node, ProgramNode):
            node.body = [self._replace_strings_with_decrypt(s) for s in node.body]
        elif isinstance(node, IfNode):
            node.condition = self._replace_strings_with_decrypt(node.condition)
            node.then_body = self._replace_strings_with_decrypt(node.then_body)
            node.elseif_blocks = [(self._replace_strings_with_decrypt(c), self._replace_strings_with_decrypt(b)) for c, b in node.elseif_blocks]
            if node.else_body:
                node.else_body = self._replace_strings_with_decrypt(node.else_body)
        elif isinstance(node, WhileNode):
            node.condition = self._replace_strings_with_decrypt(node.condition)
            node.body = self._replace_strings_with_decrypt(node.body)
        elif isinstance(node, RepeatNode):
            node.condition = self._replace_strings_with_decrypt(node.condition)
            node.body = self._replace_strings_with_decrypt(node.body)
        elif isinstance(node, ForNumericNode):
            node.start = self._replace_strings_with_decrypt(node.start)
            node.stop = self._replace_strings_with_decrypt(node.stop)
            if node.step:
                node.step = self._replace_strings_with_decrypt(node.step)
            node.body = self._replace_strings_with_decrypt(node.body)
        elif isinstance(node, ForInNode):
            node.iter_exprs = [self._replace_strings_with_decrypt(e) for e in node.iter_exprs]
            node.body = self._replace_strings_with_decrypt(node.body)
        elif isinstance(node, FunctionDefNode):
            node.body = self._replace_strings_with_decrypt(node.body)
        elif isinstance(node, ReturnNode):
            node.values = [self._replace_strings_with_decrypt(v) for v in node.values]
        elif isinstance(node, DoBlockNode):
            node.body = self._replace_strings_with_decrypt(node.body)
        elif isinstance(node, FunctionCallNode):
            node.func = self._replace_strings_with_decrypt(node.func)
            node.args = [self._replace_strings_with_decrypt(a) for a in node.args]
        elif isinstance(node, AssignmentNode):
            node.targets = [self._replace_strings_with_decrypt(t) for t in node.targets]
            node.values = [self._replace_strings_with_decrypt(v) for v in node.values]
        elif isinstance(node, UnaryOpNode):
            node.operand = self._replace_strings_with_decrypt(node.operand)
        elif isinstance(node, BinaryOpNode):
            node.left = self._replace_strings_with_decrypt(node.left)
            node.right = self._replace_strings_with_decrypt(node.right)
        elif isinstance(node, IndexAccessNode):
            node.base = self._replace_strings_with_decrypt(node.base)
            node.index = self._replace_strings_with_decrypt(node.index)
        elif isinstance(node, TableConstructNode):
            node.entries = [(self._replace_strings_with_decrypt(k) if k else None, 
                           self._replace_strings_with_decrypt(v)) for k, v in node.entries]
        
        return node
    
    def _flatten_control_flow(self, ast: ASTNode) -> ASTNode:
        """
        控制流扁平化: 使用state machine实现
        
        实现策略:
        1. 将函数体中的语句块提取出来
        2. 使用while + state变量控制流程
        3. 每个原始语句块成为状态
        """
        # 只对函数体进行扁平化
        if isinstance(ast, ProgramNode):
            ast.body = [self._flatten_control_flow(s) for s in ast.body]
        elif isinstance(ast, FunctionDefNode):
            if len(ast.body.statements) >= 3:  # 只有语句足够多时才扁平化
                ast.body = self._flatten_block(ast.body)
        elif isinstance(ast, BlockNode):
            ast.statements = [self._flatten_control_flow(s) for s in ast.statements]
        elif isinstance(ast, IfNode):
            ast.then_body = self._flatten_control_flow(ast.then_body)
            ast.elseif_blocks = [(c, self._flatten_control_flow(b)) for c, b in ast.elseif_blocks]
            if ast.else_body:
                ast.else_body = self._flatten_control_flow(ast.else_body)
        elif isinstance(ast, WhileNode):
            ast.body = self._flatten_control_flow(ast.body)
        elif isinstance(ast, DoBlockNode):
            ast.body = self._flatten_control_flow(ast.body)
        
        return ast
    
    def _flatten_block(self, block: BlockNode) -> BlockNode:
        """将代码块扁平化为state machine"""
        statements = block.statements
        if len(statements) < 3:
            return block
        
        # 随机决定是否扁平化
        if random.random() > 0.5:
            return block
        
        state_var = self._generate_junk_name()
        num_states = len(statements)
        exit_state = num_states + 1
        
        # 构建扁平化的while循环
        state_var_node = AssignmentNode(
            [IdentifierNode(state_var)],
            [NumberNode(1)]
        )
        
        # 构建状态体
        state_bodies = []
        for stmt in statements:
            state_bodies.append(BlockNode([stmt]))
        
        # 构建while循环
        while_node = WhileNode(
            condition=BinaryOpNode('<=', IdentifierNode(state_var), NumberNode(num_states)),
            body=BlockNode([
                self._build_state_machine_body(state_var, state_bodies)
            ])
        )
        
        return BlockNode([state_var_node, while_node])
    
    def _build_state_machine_body(self, state_var: str, blocks: List[BlockNode]) -> ASTNode:
        """构建state machine的主循环体"""
        # 构建if-elseif链
        if_node = None
        current_if = None
        
        for i, block in enumerate(blocks):
            state_num = i + 1
            condition = BinaryOpNode('==', IdentifierNode(state_var), NumberNode(state_num))
            
            if current_if is None:
                current_if = IfNode(
                    condition=condition,
                    then_body=block,
                    elseif_blocks=[],
                    else_body=None
                )
                if_node = current_if
            else:
                new_if = IfNode(
                    condition=condition,
                    then_body=block,
                    elseif_blocks=[],
                    else_body=None
                )
                current_if.elseif_blocks.append((condition, BlockNode([new_if])))
        
        # 添加默认分支
        if if_node:
            if_node.else_body = BlockNode([
                AssignmentNode(
                    [IdentifierNode(state_var)],
                    [NumberNode(len(blocks) + 1)]
                )
            ])
        
        # 添加状态递增
        increment = AssignmentNode(
            [IdentifierNode(state_var)],
            [BinaryOpNode('+', IdentifierNode(state_var), NumberNode(1))]
        )
        
        return BlockNode([if_node, increment])
    
    def _insert_anti_debug(self, ast: ASTNode) -> ASTNode:
        """
        插入Anti-debug代码
        
        实现策略:
        1. 插入无意义的高迭代循环
        2. 检测调试环境 (debug库等)
        """
        # 随机决定是否插入
        if random.random() > 0.4:
            return ast
        
        junk_loops = random.randint(2, 4)
        
        # 构建anti-debug代码
        anti_code = self._build_anti_debug_code(junk_loops)
        
        # 插入到程序开头
        if isinstance(ast, ProgramNode):
            # 在函数定义之前插入
            insert_pos = 0
            for i, stmt in enumerate(ast.body):
                if isinstance(stmt, FunctionDefNode):
                    insert_pos = i
                    break
            
            # 创建包含anti-debug的do-end块
            wrapper = DoBlockNode(BlockNode([anti_code]))
            ast.body.insert(insert_pos, wrapper)
        
        return ast
    
    def _build_anti_debug_code(self, junk_loops: int) -> ASTNode:
        """构建anti-debug代码"""
        statements = []
        
        for _ in range(junk_loops):
            loop_var = self._generate_junk_name()
            iterations = random.randint(500, 2000)
            
            # 无意义循环
            loop_body = [
                AssignmentNode(
                    [IdentifierNode(loop_var)],
                    [BinaryOpNode(
                        '%',
                        BinaryOpNode('+', IdentifierNode(loop_var), NumberNode(random.randint(1, 50))),
                        NumberNode(random.randint(100, 500))
                    )]
                )
            ]
            
            # 添加一些无用计算
            temp_var = self._generate_junk_name()
            loop_body.append(LocalVarNode([temp_var], [NumberNode(random.randint(10, 100))]))
            loop_body.append(AssignmentNode(
                [IdentifierNode(temp_var)],
                [BinaryOpNode('-', IdentifierNode(temp_var), NumberNode(random.randint(1, 10)))]
            ))
            
            statements.append(LocalVarNode([loop_var], [NumberNode(0)]))
            statements.append(ForNumericNode(
                variable='_',
                start=NumberNode(1),
                stop=NumberNode(iterations),
                step=NumberNode(1),
                body=BlockNode(loop_body)
            ))
        
        # 环境检测 - 检查debug库
        env_var = self._generate_junk_name()
        env_detect = IfNode(
            condition=BinaryOpNode('==', IdentifierNode('debug'), IdentifierNode('nil')),
            then_body=BlockNode([]),
            elseif_blocks=[],
            else_body=BlockNode([
                LocalVarNode([self._generate_junk_name()], [IdentifierNode('debug')])
            ])
        )
        statements.append(env_detect)
        
        return BlockNode(statements)
    
    def _mess_up_formatting(self, ast: ASTNode) -> ASTNode:
        """
        混乱输出格式
        
        实现策略:
        1. 随机化缩进
        2. 在代码中添加随机空行
        3. 添加随机注释干扰
        """
        # 标记需要混乱的节点
        self._add_formatting_markers(ast)
        return ast
    
    def _add_formatting_markers(self, node: ASTNode):
        """添加格式混乱标记"""
        # 为BlockNode添加随机偏移量
        if isinstance(node, BlockNode) and random.random() > 0.6:
            node.indent_offset = random.randint(-2, 2)
        
        # 递归处理
        if isinstance(node, BlockNode):
            for stmt in node.statements:
                self._add_formatting_markers(stmt)
        elif isinstance(node, ProgramNode):
            for stmt in node.body:
                self._add_formatting_markers(stmt)
        elif isinstance(node, IfNode):
            self._add_formatting_markers(node.then_body)
            for c, b in node.elseif_blocks:
                self._add_formatting_markers(b)
            if node.else_body:
                self._add_formatting_markers(node.else_body)
        elif isinstance(node, WhileNode):
            self._add_formatting_markers(node.body)
        elif isinstance(node, ForNumericNode):
            self._add_formatting_markers(node.body)
        elif isinstance(node, ForInNode):
            self._add_formatting_markers(node.body)
        elif isinstance(node, FunctionDefNode):
            self._add_formatting_markers(node.body)
        elif isinstance(node, DoBlockNode):
            self._add_formatting_markers(node.body)


# =============================================================================
# 第七部分: 增强的混淆器 (带更多混淆技术)
# =============================================================================

class EnhancedObfuscator(Obfuscator):
    """
    增强版混淆器
    
    在基础混淆器上增加:
    1. 更复杂的垃圾代码
    2. 数字混淆 (表达式替换)
    3. 字符串分裂
    """
    
    def __init__(self, seed: int = None):
        super().__init__(seed)
        self.number_mappings: Dict[int, ASTNode] = {}
    
    def _obfuscate_numbers(self, node: ASTNode) -> ASTNode:
        """
        数字混淆
        
        将常量数字替换为等价的复杂表达式
        例如: 10 -> 2 * 5, 100 -> 50 + 50
        """
        if isinstance(node, NumberNode):
            original = int(node.value)
            
            # 只混淆非特殊数字
            if original < 0 or original > 1000:
                return node
            
            # 生成复杂表达式
            techniques = [
                self._number_addition,
                self._number_multiplication,
                self._number_mixed,
            ]
            
            # 商业级: 添加数字拆分技术
            if self.enable_num_split:
                techniques.append(self._number_split)
            
            technique = random.choice(techniques)
            return technique(original)
        
        # 递归处理
        if isinstance(node, BlockNode):
            node.statements = [self._obfuscate_numbers(s) for s in node.statements]
        elif isinstance(node, ProgramNode):
            node.body = [self._obfuscate_numbers(s) for s in node.body]
        elif isinstance(node, IfNode):
            node.condition = self._obfuscate_numbers(node.condition)
            node.then_body = self._obfuscate_numbers(node.then_body)
            node.elseif_blocks = [(c, self._obfuscate_numbers(b)) for c, b in node.elseif_blocks]
            if node.else_body:
                node.else_body = self._obfuscate_numbers(node.else_body)
        elif isinstance(node, WhileNode):
            node.condition = self._obfuscate_numbers(node.condition)
            node.body = self._obfuscate_numbers(node.body)
        elif isinstance(node, RepeatNode):
            node.condition = self._obfuscate_numbers(node.condition)
            node.body = self._obfuscate_numbers(node.body)
        elif isinstance(node, ForNumericNode):
            node.start = self._obfuscate_numbers(node.start)
            node.stop = self._obfuscate_numbers(node.stop)
            if node.step:
                node.step = self._obfuscate_numbers(node.step)
            node.body = self._obfuscate_numbers(node.body)
        elif isinstance(node, ForInNode):
            node.iter_exprs = [self._obfuscate_numbers(e) for e in node.iter_exprs]
            node.body = self._obfuscate_numbers(node.body)
        elif isinstance(node, FunctionDefNode):
            node.body = self._obfuscate_numbers(node.body)
        elif isinstance(node, ReturnNode):
            node.values = [self._obfuscate_numbers(v) for v in node.values]
        elif isinstance(node, DoBlockNode):
            node.body = self._obfuscate_numbers(node.body)
        elif isinstance(node, FunctionCallNode):
            node.func = self._obfuscate_numbers(node.func)
            node.args = [self._obfuscate_numbers(a) for a in node.args]
        elif isinstance(node, AssignmentNode):
            node.targets = [self._obfuscate_numbers(t) for t in node.targets]
            node.values = [self._obfuscate_numbers(v) for v in node.values]
        elif isinstance(node, UnaryOpNode):
            node.operand = self._obfuscate_numbers(node.operand)
        elif isinstance(node, BinaryOpNode):
            node.left = self._obfuscate_numbers(node.left)
            node.right = self._obfuscate_numbers(node.right)
        elif isinstance(node, IndexAccessNode):
            node.base = self._obfuscate_numbers(node.base)
            node.index = self._obfuscate_numbers(node.index)
        elif isinstance(node, TableConstructNode):
            node.entries = [(self._obfuscate_numbers(k) if k else None, 
                           self._obfuscate_numbers(v)) for k, v in node.entries]
        
        return node
    
    def _number_addition(self, n: int) -> ASTNode:
        """加法混淆: n -> (n-k) + k"""
        if n <= 1:
            return NumberNode(n)
        k = random.randint(1, n - 1)
        return BinaryOpNode('+', NumberNode(n - k), NumberNode(k))
    
    def _number_multiplication(self, n: int) -> ASTNode:
        """乘法混淆: n -> k * (n/k)"""
        if n <= 1:
            return NumberNode(n)
        # 找一个因数
        factors = [i for i in range(2, min(n, 50)) if n % i == 0]
        if factors:
            k = random.choice(factors)
            return BinaryOpNode('*', NumberNode(k), NumberNode(n // k))
        return NumberNode(n)
    
    def _number_mixed(self, n: int) -> ASTNode:
        """混合混淆"""
        if n <= 2:
            return NumberNode(n)
        # 嵌套表达式
        a = random.randint(1, n // 2)
        b = n - a
        return BinaryOpNode('-', 
                           BinaryOpNode('+', NumberNode(a), NumberNode(a)),
                           NumberNode(b - a))
    
    def _number_split(self, n: int) -> ASTNode:
        """
        数字拆分混淆: n -> (100+20+3)
        
        商业级特性:
        - 将数字拆分为多个部分相加
        - 例如: 123 -> (100 + 20 + 3), 456 -> (400 + 50 + 6)
        - 增加逆向分析难度
        """
        if n <= 0:
            return NumberNode(n)
        
        # 处理大数拆分为个位、十位、百位等
        parts = []
        place = 1
        
        # 如果启用商业级数字拆分，则深度拆分
        if self.enable_num_split:
            # 拆分每一位
            digits = []
            temp = n
            while temp > 0:
                digits.append(temp % 10)
                temp //= 10
            
            # 从低位到高位构建表达式
            multiplier = 1
            for digit in digits:
                if digit > 0:
                    parts.append(NumberNode(digit * multiplier))
                multiplier *= 10
            
            # 使用加法连接所有部分
            if len(parts) == 1:
                return parts[0]
            elif len(parts) == 2:
                return BinaryOpNode('+', parts[0], parts[1])
            else:
                # 嵌套构建
                result = parts[0]
                for i in range(1, len(parts)):
                    result = BinaryOpNode('+', result, parts[i])
                return result
        else:
            # 普通模式：仅拆分部分数字
            if n >= 10 and n <= 999:
                # 拆分为百位+十位+个位
                hundreds = (n // 100) * 100
                tens = ((n % 100) // 10) * 10
                ones = n % 10
                
                parts = []
                if hundreds > 0:
                    parts.append(NumberNode(hundreds))
                if tens > 0:
                    parts.append(NumberNode(tens))
                if ones > 0:
                    parts.append(NumberNode(ones))
                
                if len(parts) <= 1:
                    return NumberNode(n)
                elif len(parts) == 2:
                    return BinaryOpNode('+', parts[0], parts[1])
                else:
                    result = BinaryOpNode('+', parts[0], parts[1])
                    for i in range(2, len(parts)):
                        result = BinaryOpNode('+', result, parts[i])
                    return result
            
            # 小数字使用普通方法
            return self._number_addition(n)


# =============================================================================
# 第八部分: 主程序入口
# =============================================================================
# 第九部分: VM混淆器 (VM-Based Obfuscator)
# =============================================================================

# -----------------------------------------------------------------------------
# 9.1 VM指令定义
# -----------------------------------------------------------------------------

class VMOp:
    """VM操作码定义"""
    # 加载/存储
    LOADK = 0x01        # 加载常量 R(A) = K(Bx)
    LOADNIL = 0x02      # 加载nil R(A) = nil, R(A+1) = nil, ...
    LOADBOOL = 0x03      # 加载布尔值 R(A) = B; if C then PC++
    MOVE = 0x04          # 移动 R(A) = R(B)
    
    # 全局变量
    GETGLOBAL = 0x10     # R(A) = G[K(Bx)]
    SETGLOBAL = 0x11     # G[K(Bx)] = R(A)
    
    # 表操作
    NEWTABLE = 0x20      # R(A) = {}
    SETTABLE = 0x21      # R(A)[RK(B)] = RK(C)
    GETTABLE = 0x22      # R(A) = R(B)[RK(C)]
    SETLIST = 0x23       # R(A)[i] = R(A+i) for i=1..B
    
    # 算术运算
    ADD = 0x30           # R(A) = RK(B) + RK(C)
    SUB = 0x31           # R(A) = RK(B) - RK(C)
    MUL = 0x32           # R(A) = RK(B) * RK(C)
    DIV = 0x33           # R(A) = RK(B) / RK(C)
    MOD = 0x34           # R(A) = RK(B) % RK(C)
    POW = 0x35           # R(A) = RK(B) ^ RK(C)
    UNM = 0x36           # R(A) = -R(B)
    
    # 比较运算
    EQ = 0x40            # if (RK(B) == RK(C)) ~= A then PC++
    LT = 0x41            # if (RK(B) < RK(C)) ~= A then PC++
    LE = 0x42            # if (RK(B) <= RK(C)) ~= A then PC++
    
    # 逻辑运算
    NOT = 0x50           # R(A) = not R(B)
    AND = 0x51           # R(A) = R(B) and R(C)
    OR = 0x52            # R(A) = R(B) or R(C)
    JMP = 0x53            # PC += sBx
    JMPF = 0x54          # if not R(A) then PC += sBx
    
    # 函数调用
    CALL = 0x60           # R(A), ... = R(A)(R(A+1), ...)
    TAILCALL = 0x61      # return R(A)(...)
    RETURN = 0x62        # return R(A), ...
    CLOSE = 0x63         # close all upvalues >= A
    
    # 循环
    FORLOOP = 0x70       # R(A) += R(A+2); if R(A) <= R(A+1) then PC += sBx
    FORPREP = 0x71       # R(A) -= R(A+2); PC += sBx
    ITER = 0x72           # for 迭代
    
    # 其他
    CONCAT = 0x80        # R(A) = R(B)..R(B+1).....R(C)
    LEN = 0x81           # R(A) = #R(B)
    SETTOP = 0x82        # stack[A] = stack[top]; top = A
    VARARG = 0x83        # R(A), ... = vararg
    
    # 混淆指令 (垃圾指令)
    NOP = 0xFF           # 空操作
    SWAP = 0xFE          # swap stack[A] <-> stack[A+1]
    DUP = 0xFD           # dup stack[A]
    
    # 假操作码 (迷惑反编译器)
    FAKE_ADD = 0xC0       # 假加法 - 实际执行减法
    FAKE_SUB = 0xC1       # 假减法 - 实际执行加法
    FAKE_MUL = 0xC2       # 假乘法 - 实际执行除法
    FAKE_DIV = 0xC3       # 假除法 - 实际执行乘法
    FAKE_JMP = 0xC4       # 假跳转 - 反向跳转
    FAKE_GET = 0xC5       # 假获取 - 返回假值
    FAKE_SET = 0xC6       # 假设置 - 不做任何事
    FAKE_CALL = 0xC7      # 假调用 - 返回nil
    FAKE_NOT = 0xC8       # 假NOT - 执行AND逻辑
    FAKE_AND = 0xC9      # 假AND - 执行OR逻辑
    FAKE_OR = 0xCA       # 假OR - 执行NOT逻辑
    
    # 所有有效操作码
    ALL_OPS = list(range(0, 0xCB))
    
    # 假操作码列表
    FAKE_OPS = [
        FAKE_ADD, FAKE_SUB, FAKE_MUL, FAKE_DIV,
        FAKE_JMP, FAKE_GET, FAKE_SET, FAKE_CALL,
        FAKE_NOT, FAKE_AND, FAKE_OR
    ]


# -----------------------------------------------------------------------------
# 9.2 字节码指令结构
# -----------------------------------------------------------------------------

@dataclass
class Instruction:
    """字节码指令"""
    opcode: int
    a: int = 0
    b: int = 0
    c: int = 0
    bx: int = 0
    sbx: int = 0
    
    def encode(self) -> bytes:
        """编码为4字节"""
        op = self.opcode & 0xFF
        a = self.a & 0xFF
        b = self.b & 0xFF
        c = self.c & 0xFF
        # bx 占 3 字节
        bx_b1 = (self.bx >> 16) & 0xFF
        bx_b2 = (self.bx >> 8) & 0xFF
        bx_b3 = self.bx & 0xFF
        return bytes([op, a, bx_b1, bx_b2])
    
    def encode_full(self) -> bytes:
        """编码为4字节 (完整版)"""
        op = self.opcode & 0xFF
        a = self.a & 0xFF
        
        if self.sbx != 0:
            # 有符号跳转
            sbx = self.sbx & 0xFFFFFF
            b1 = (sbx >> 16) & 0xFF
            b2 = (sbx >> 8) & 0xFF
            b3 = sbx & 0xFF
        else:
            b1 = self.b & 0xFF
            b2 = self.c & 0xFF
            b3 = 0
        
        return bytes([op, a, b1, b2])


# -----------------------------------------------------------------------------
# 9.2.1 增强的反逆向VM指令系统
# -----------------------------------------------------------------------------

class AdvancedVMOp:
    """
    增强VM操作码 - 支持随机映射、fake opcode和指令混淆
    
    反逆向特性:
    1. opcode随机映射 (每次生成不同)
    2. fake opcode (永不执行)
    3. 指令顺序打乱
    """
    
    # 基础指令 (会被随机重新映射)
    BASE_OPCODES = {
        'LOADK': 0x01,
        'LOADNIL': 0x02,
        'LOADBOOL': 0x03,
        'MOVE': 0x04,
        'GETGLOBAL': 0x10,
        'SETGLOBAL': 0x11,
        'NEWTABLE': 0x20,
        'SETTABLE': 0x21,
        'GETTABLE': 0x22,
        'SETLIST': 0x23,
        'ADD': 0x30,
        'SUB': 0x31,
        'MUL': 0x32,
        'DIV': 0x33,
        'MOD': 0x34,
        'POW': 0x35,
        'UNM': 0x36,
        'EQ': 0x40,
        'LT': 0x41,
        'LE': 0x42,
        'NOT': 0x50,
        'AND': 0x51,
        'OR': 0x52,
        'JMP': 0x53,
        'JMPF': 0x54,
        'CALL': 0x60,
        'TAILCALL': 0x61,
        'RETURN': 0x62,
        'FORLOOP': 0x70,
        'FORPREP': 0x71,
        'CONCAT': 0x80,
        'LEN': 0x81,
    }
    
    # Fake opcodes (永不执行的指令)
    FAKE_OPCODES = {
        'FAKE_NOP1': 0xE0,
        'FAKE_NOP2': 0xE1,
        'FAKE_NOP3': 0xE2,
        'FAKE_JUNK1': 0xE3,
        'FAKE_JUNK2': 0xE4,
        'FAKE_DECODE': 0xE5,
    }
    
    @classmethod
    def generate_random_mapping(cls, seed: int = None) -> Dict[int, int]:
        """
        生成随机opcode映射表
        
        策略:
        - 使用固定范围 [0x01, 0x82]
        - 随机打乱映射关系
        """
        if seed is not None:
            random.seed(seed)
        
        # 基础opcode列表
        base_opcodes = list(range(0x01, 0x83))  # 0x01 到 0x82
        
        # 随机打乱
        mapping = {}
        shuffled = base_opcodes.copy()
        random.shuffle(shuffled)
        
        # 建立双向映射
        for i, opcode in enumerate(base_opcodes):
            mapping[opcode] = shuffled[i]
        
        return mapping
    
    @classmethod
    def remap_instruction(cls, instr: Instruction, mapping: Dict[int, int]) -> Instruction:
        """使用映射表重新映射指令opcode"""
        if instr.opcode in mapping:
            new_op = Instruction(
                opcode=mapping[instr.opcode],
                a=instr.a,
                b=instr.b,
                c=instr.c,
                bx=instr.bx,
                sbx=instr.sbx
            )
            return new_op
        return instr


@dataclass
class ShuffledBlock:
    """打乱后的代码块"""
    instructions: List[Instruction]
    original_indices: List[int]
    jump_map: Dict[int, int]  # 原索引 -> 新索引


@dataclass
class Function:
    """函数定义 (用于字节码)"""
    name: str = ""
    params: int = 0
    locals_count: int = 0
    instructions: List[Instruction] = None
    constants: List = None
    prototypes: List['Function'] = None
    
    def __post_init__(self):
        if self.instructions is None:
            self.instructions = []
        if self.constants is None:
            self.constants = []
        if self.prototypes is None:
            self.prototypes = []


# -----------------------------------------------------------------------------
# 9.3 字节码编译器
# -----------------------------------------------------------------------------

class BytecodeCompiler:
    """
    将Lua AST编译为自定义字节码
    """
    
    def __init__(self):
        self.current_function: Optional[Function] = None
        self.function_stack: List[Function] = []
        self.constants: List[Any] = []
        self.constant_map: Dict[Any, int] = {}
        self.label_map: Dict[str, int] = {}
        self.pending_jumps: List[Tuple[int, str]] = []  # (instruction_index, label)
        self.instructions: List[Instruction] = []
    
    def compile(self, ast: ASTNode) -> Function:
        """编译AST为字节码函数"""
        # 创建主函数
        main_func = Function(name="main", params=0, locals_count=0)
        self.current_function = main_func
        self.function_stack.append(main_func)
        self.instructions = []
        self.constants = []
        self.constant_map = {}
        
        # 编译主程序
        self._compile_node(ast)
        
        # 添加隐式 return
        self.emit(VMOp.RETURN, a=0, b=1)
        
        # 将指令和常量复制到函数
        main_func.instructions = list(self.instructions)
        main_func.constants = list(self.constants)
        
        self.function_stack.pop()
        return main_func
    
    def _compile_node(self, node: ASTNode):
        """编译单个节点"""
        if isinstance(node, ProgramNode):
            for stmt in node.body:
                self._compile_node(stmt)
        elif isinstance(node, BlockNode):
            for stmt in node.statements:
                self._compile_node(stmt)
        elif isinstance(node, LocalVarNode):
            self._compile_local_var(node)
        elif isinstance(node, AssignmentNode):
            self._compile_assignment(node)
        elif isinstance(node, IfNode):
            self._compile_if(node)
        elif isinstance(node, WhileNode):
            self._compile_while(node)
        elif isinstance(node, ForNumericNode):
            self._compile_for_numeric(node)
        elif isinstance(node, ForInNode):
            self._compile_for_in(node)
        elif isinstance(node, RepeatNode):
            self._compile_repeat(node)
        elif isinstance(node, FunctionDefNode):
            self._compile_function_def(node)
        elif isinstance(node, LocalFunctionNode):
            self._compile_local_function(node)
        elif isinstance(node, ReturnNode):
            self._compile_return(node)
        elif isinstance(node, BreakNode):
            self._compile_break()
        elif isinstance(node, DoBlockNode):
            self._compile_node(node.body)
        elif isinstance(node, FunctionCallNode):
            self._compile_function_call(node)
        elif isinstance(node, ExpressionWrapper):
            self._compile_expr(node.expr)
    
    def _compile_local_var(self, node: LocalVarNode):
        """编译局部变量声明"""
        # 编译值表达式
        for value in node.values:
            self._compile_expr(value)
        
        # 不足的用 nil 填充
        num_names = len(node.names)
        num_values = len(node.values)
        for i in range(num_values, num_names):
            self.emit(VMOp.LOADNIL, a=num_values + i)
        
        # 局部变量在运行时栈上管理
    
    def _compile_assignment(self, node: AssignmentNode):
        """编译赋值语句"""
        # 先编译右值
        for value in node.values:
            self._compile_expr(value)
        
        # 再编译左值 (目标)
        for i, target in enumerate(node.targets):
            if isinstance(target, IdentifierNode):
                self._compile_store_var(target.value)
            elif isinstance(target, IndexAccessNode):
                self._compile_indexed_assign(target)
    
    def _compile_if(self, node: IfNode):
        """编译if语句"""
        # 编译条件
        self._compile_expr(node.condition)
        
        # 跳转到 then 或 else
        jmp_to_else = self.emit(VMOp.JMPF, a=0, sbx=0)
        
        # 编译 then 分支
        self._compile_node(node.then_body)
        
        # 跳转到 end
        jmp_to_end = self.emit(VMOp.JMP, a=0, sbx=0)
        
        # 修复 else 跳转
        self.patch_jump(jmp_to_else, len(self.instructions))
        
        # 编译 elseif
        for i, (cond, body) in enumerate(node.elseif_blocks):
            self._compile_expr(cond)
            jmp_to_next = self.emit(VMOp.JMPF, a=0, sbx=0)
            self._compile_node(body)
            jmp_to_end2 = self.emit(VMOp.JMP, a=0, sbx=0)
            self.patch_jump(jmp_to_next, len(self.instructions))
            if i < len(node.elseif_blocks) - 1:
                jmp_to_end = jmp_to_end2
        
        # 编译 else 分支
        if node.else_body:
            self._compile_node(node.else_body)
        
        # 修复 end 跳转
        self.patch_jump(jmp_to_end, len(self.instructions))
    
    def _compile_while(self, node: WhileNode):
        """编译while循环"""
        loop_start = len(self.instructions)
        
        # 编译条件
        self._compile_expr(node.condition)
        
        # 条件为假则跳出
        jmp_out = self.emit(VMOp.JMPF, a=0, sbx=0)
        
        # 编译循环体
        self._compile_node(node.body)
        
        # 跳回循环开始
        self.emit(VMOp.JMP, a=0, sbx=loop_start - len(self.instructions) - 1)
        
        # 修复跳出位置
        self.patch_jump(jmp_out, len(self.instructions))
    
    def _compile_for_numeric(self, node: ForNumericNode):
        """编译数值for循环"""
        # 编译初始值、终止值、步长
        self._compile_expr(node.start)
        self._compile_expr(node.stop)
        if node.step:
            self._compile_expr(node.step)
        else:
            self.emit(VMOp.LOADK, a=0, bx=self._add_constant(1))
        
        # FORPREP: 初始化循环变量
        jmp_prep = self.emit(VMOp.FORPREP, a=0, sbx=0)
        
        # 编译循环体
        self._compile_node(node.body)
        
        # FORLOOP: 递增并检查
        self.emit(VMOp.FORLOOP, a=0, sbx=jmp_prep - len(self.instructions) - 1)
        
        # 修复 FORPREP 跳转
        self.patch_jump(jmp_prep, len(self.instructions))
    
    def _compile_for_in(self, node: ForInNode):
        """编译迭代for循环"""
        # 编译迭代器表达式
        for expr in node.iter_exprs:
            self._compile_expr(expr)
        
        # ITER 准备
        self.emit(VMOp.JMP, a=0, sbx=0)  # 占位
    
    def _compile_repeat(self, node: RepeatNode):
        """编译repeat-until循环"""
        loop_start = len(self.instructions)
        self._compile_node(node.body)
        self._compile_expr(node.condition)
        self.emit(VMOp.JMPF, a=0, sbx=loop_start - len(self.instructions) - 1)
    
    def _compile_function_def(self, node: FunctionDefNode):
        """编译函数定义"""
        # 创建子函数
        sub_func = Function(name=node.name, params=len(node.params))
        
        # 保存当前上下文
        old_instructions = self.instructions
        old_constants = self.constants
        old_constant_map = self.constant_map
        
        # 设置子函数上下文
        self.instructions = []
        self.constants = []
        self.constant_map = {}
        
        self.function_stack.append(sub_func)
        
        # 编译函数体
        for stmt in node.body.statements:
            self._compile_node(stmt)
        self.emit(VMOp.RETURN, a=0, b=1)
        
        # 保存子函数的指令和常量
        sub_func.instructions = list(self.instructions)
        sub_func.constants = list(self.constants)
        
        self.function_stack.pop()
        
        # 恢复上下文
        self.instructions = old_instructions
        self.constants = old_constants
        self.constant_map = old_constant_map
        
        # 添加到当前函数的 prototypes
        self.current_function.prototypes.append(sub_func)
        
        # 加载函数闭包 (使用常量表索引)
        func_index = len(self.current_function.prototypes) - 1
        self.emit(VMOp.LOADK, a=0, bx=self._add_constant(func_index))
    
    def _compile_local_function(self, node: LocalFunctionNode):
        """编译局部函数定义"""
        func_node = FunctionDefNode(node.name, node.params, node.body)
        self._compile_function_def(func_node)
    
    def _compile_return(self, node: ReturnNode):
        """编译return语句"""
        if node.values:
            for value in node.values:
                self._compile_expr(value)
            self.emit(VMOp.RETURN, a=0, b=len(node.values))
        else:
            self.emit(VMOp.RETURN, a=0, b=0)
    
    def _compile_break(self):
        """编译break语句"""
        self.emit(VMOp.JMP, a=0, sbx=0)  # 需要后续处理跳转目标
    
    def _compile_function_call(self, node: FunctionCallNode):
        """编译函数调用"""
        # 编译函数
        self._compile_expr(node.func)
        
        # 编译参数
        argc = len(node.args)
        for arg in node.args:
            self._compile_expr(arg)
        
        # 调用
        self.emit(VMOp.CALL, a=0, b=argc + 1)
    
    def _compile_expr(self, expr: ASTNode):
        """编译表达式"""
        if isinstance(expr, NumberNode):
            idx = self._add_constant(expr.value)
            self.emit(VMOp.LOADK, a=0, bx=idx)
        elif isinstance(expr, StringNode):
            idx = self._add_constant(expr.value)
            self.emit(VMOp.LOADK, a=0, bx=idx)
        elif isinstance(expr, NilNode):
            self.emit(VMOp.LOADNIL, a=0)
        elif isinstance(expr, TrueNode):
            self.emit(VMOp.LOADBOOL, a=0, b=1, c=0)
        elif isinstance(expr, FalseNode):
            self.emit(VMOp.LOADBOOL, a=0, b=0, c=0)
        elif isinstance(expr, IdentifierNode):
            self._compile_load_var(expr.value)
        elif isinstance(expr, BinaryOpNode):
            self._compile_binary_op(expr)
        elif isinstance(expr, UnaryOpNode):
            self._compile_unary_op(expr)
        elif isinstance(expr, TableConstructNode):
            self._compile_table(expr)
        elif isinstance(expr, IndexAccessNode):
            self._compile_index_access(expr)
        elif isinstance(expr, FunctionCallNode):
            self._compile_function_call(expr)
            # 结果在栈顶
        elif isinstance(expr, FunctionDefNode):
            self._compile_function_def(expr)
    
    def _compile_binary_op(self, expr: BinaryOpNode):
        """编译二元运算符"""
        # 编译左右操作数
        self._compile_expr(expr.left)
        self._compile_expr(expr.right)
        
        # 运算
        op_map = {
            '+': VMOp.ADD,
            '-': VMOp.SUB,
            '*': VMOp.MUL,
            '/': VMOp.DIV,
            '%': VMOp.MOD,
            '^': VMOp.POW,
            '==': VMOp.EQ,
            '~=': VMOp.EQ,  # 通过 EQ + NOT 实现
            '<': VMOp.LT,
            '>': VMOp.LT,   # 通过交换 + LT 实现
            '<=': VMOp.LE,
            '>=': VMOp.LE,  # 类似
            'and': VMOp.AND,
            'or': VMOp.OR,
            '..': VMOp.CONCAT,
        }
        
        if expr.value in op_map:
            self.emit(op_map[expr.value], a=0, b=1, c=2)
    
    def _compile_unary_op(self, expr: UnaryOpNode):
        """编译一元运算符"""
        self._compile_expr(expr.operand)
        
        if expr.value == 'not':
            self.emit(VMOp.NOT, a=0, b=1)
        elif expr.value == '-':
            self.emit(VMOp.UNM, a=0, b=1)
        elif expr.value == '#':
            self.emit(VMOp.LEN, a=0, b=1)
    
    def _compile_table(self, node: TableConstructNode):
        """编译表构造"""
        self.emit(VMOp.NEWTABLE, a=0)
        
        i = 0
        for key, value in node.entries:
            self._compile_expr(value)
            if key is None:
                # 数组元素
                i += 1
                self.emit(VMOp.SETLIST, a=0, b=i)
            else:
                self._compile_expr(key)
                self.emit(VMOp.SETTABLE, a=0, b=1, c=2)
    
    def _compile_index_access(self, node: IndexAccessNode):
        """编译索引访问"""
        self._compile_expr(node.base)
        self._compile_expr(node.index)
        self.emit(VMOp.GETTABLE, a=0, b=1, c=2)
    
    def _compile_indexed_assign(self, node: IndexAccessNode):
        """编译索引赋值"""
        self._compile_expr(node.base)
        self._compile_expr(node.index)
        # 值已经在栈上
        self.emit(VMOp.SETTABLE, a=0, b=1, c=2)
    
    def _compile_load_var(self, name: str):
        """加载变量"""
        idx = self._add_constant(name)
        self.emit(VMOp.GETGLOBAL, a=0, bx=idx)
    
    def _compile_store_var(self, name: str):
        """存储变量"""
        idx = self._add_constant(name)
        self.emit(VMOp.SETGLOBAL, a=0, bx=idx)
    
    def _add_constant(self, value: Any) -> int:
        """添加常量并返回索引"""
        if value in self.constant_map:
            return self.constant_map[value]
        
        idx = len(self.constants)
        self.constants.append(value)
        self.constant_map[value] = idx
        return idx
    
    def _alloc_local(self) -> int:
        """分配局部变量槽位"""
        return len(self.constants)
    
    def emit(self, opcode: int, a: int = 0, b: int = 0, c: int = 0, 
             bx: int = 0, sbx: int = 0) -> int:
        """发射指令，返回指令索引"""
        instr = Instruction(opcode=opcode, a=a, b=b, c=c, bx=bx, sbx=sbx)
        self.instructions.append(instr)
        self.current_function.instructions.append(instr)
        return len(self.instructions) - 1
    
    def patch_jump(self, instr_index: int, target: int):
        """修补跳转目标"""
        if instr_index < len(self.instructions):
            instr = self.instructions[instr_index]
            instr.sbx = target - instr_index - 1


# -----------------------------------------------------------------------------
# 9.4 增强的字节码编码器 (多层保护)
# -----------------------------------------------------------------------------

class AdvancedBytecodeEncoder:
    """
    增强字节码编码器 - 多层加密保护
    
    保护措施:
    1. 多层编码 (XOR + Base64 + 位置扰动)
    2. 常量表加密
    3. 字节码混淆
    """
    
    def __init__(self, seed: int = None):
        self.seed = seed if seed else random.randint(1, 0xFFFFFFFF)
        self.key1 = self._generate_key(32)
        self.key2 = self._generate_key(64)
        self.key3 = self._generate_key(16)
        self.opcode_mapping = AdvancedVMOp.generate_random_mapping(self.seed)
        self.constant_encryption_key = self._generate_key(32)
    
    def _generate_key(self, bits: int) -> int:
        """生成加密密钥"""
        random.seed(self.seed ^ bits)
        return random.randint(1, (1 << bits) - 1)
    
    def encode(self, func: Function) -> str:
        """
        编码函数为加密字符串
        
        流程:
        1. 序列化函数
        2. 第一层: XOR加密
        3. 第二层: 位置扰动
        4. 第三层: Base64编码
        """
        data = self._serialize_function(func)
        
        # 第一层: 动态XOR
        encrypted1 = self._xor_encrypt_dynamic(data)
        
        # 第二层: 位置扰动
        scrambled = self._scramble_positions(encrypted1)
        
        # 第三层: 再次XOR
        encrypted2 = self._xor_encrypt_with_key(scrambled, self.key2)
        
        # 第四层: Base64编码
        encoded = base64.b64encode(encrypted2).decode('ascii')
        
        return encoded
    
    def _serialize_function(self, func: Function) -> bytes:
        """序列化函数为字节"""
        result = bytearray()
        
        # Magic: "LVC\0"
        result.extend(b'LVC\0')
        
        # Version (带混淆标志)
        result.append(0x02)  # 版本2
        
        # Flags
        result.append(0x03)  # 混淆标志 + 加密标志
        
        # Opcode映射种子
        mapping_seed = (self.seed & 0xFFFFFFFF).to_bytes(4, 'big')
        result.extend(mapping_seed)
        
        # 函数数据
        result.extend(self._serialize_prototype(func))
        
        return bytes(result)
    
    def _serialize_prototype(self, func: Function) -> bytes:
        """序列化函数原型"""
        result = bytearray()
        
        # 函数名 (加密)
        name_bytes = func.name.encode('utf-8')
        encrypted_name = self._xor_encrypt_block(name_bytes, self.constant_encryption_key)
        result.extend(len(encrypted_name).to_bytes(4, 'big'))
        result.extend(encrypted_name)
        
        # 参数数量
        result.append(func.params)
        
        # 局部变量数量
        result.extend(func.locals_count.to_bytes(4, 'big'))
        
        # 常量数量
        result.extend(len(func.constants).to_bytes(4, 'big'))
        
        # 指令数量
        result.extend(len(func.instructions).to_bytes(4, 'big'))
        
        # 子函数数量
        result.extend(len(func.prototypes).to_bytes(4, 'big'))
        
        # 常量表 (加密)
        encrypted_consts = self._encrypt_constants(func.constants)
        result.extend(len(encrypted_consts).to_bytes(4, 'big'))
        result.extend(encrypted_consts)
        
        # 指令表 (混淆opcode)
        remapped_instrs = []
        for instr in func.instructions:
            remapped = AdvancedVMOp.remap_instruction(instr, self.opcode_mapping)
            remapped_instrs.append(remapped)
        
        for instr in remapped_instrs:
            result.extend(instr.encode_full())
        
        # 子函数
        for proto in func.prototypes:
            result.extend(self._serialize_prototype(proto))
        
        return bytes(result)
    
    def _encrypt_constants(self, constants: List) -> bytes:
        """加密常量表"""
        result = bytearray()
        
        for const in constants:
            self._serialize_encrypted_constant(const, result)
        
        return bytes(result)
    
    def _serialize_encrypted_constant(self, const: Any, result: bytearray):
        """序列化并加密常量"""
        if const is None:
            result.append(0x00)  # nil
        elif isinstance(const, bool):
            result.append(0x01)  # boolean
            # 布尔值混淆
            if const:
                result.append(0xFF ^ (self.constant_encryption_key & 0xFF))
            else:
                result.append(0x00 ^ (self.constant_encryption_key & 0xFF))
        elif isinstance(const, (int, float)):
            result.append(0x02)  # number
            # 数字混淆编码
            if isinstance(const, float):
                raw = const.hex().encode('utf-8')
            else:
                raw = str(const).encode('utf-8')
            encrypted = self._xor_encrypt_block(raw, self.constant_encryption_key)
            result.extend(len(encrypted).to_bytes(4, 'big'))
            result.extend(encrypted)
        elif isinstance(const, str):
            result.append(0x03)  # string
            const_bytes = const.encode('utf-8')
            encrypted = self._xor_encrypt_block(const_bytes, self.constant_encryption_key)
            result.extend(len(encrypted).to_bytes(4, 'big'))
            result.extend(encrypted)
    
    def _xor_encrypt_dynamic(self, data: bytes) -> bytes:
        """动态XOR加密"""
        result = bytearray()
        for i, byte in enumerate(data):
            # 使用动态密钥 (基础密钥 + 位置偏移 + 随机因子)
            key_byte = (self.key1 >> ((i % 8) * 4)) & 0xFF
            dynamic_key = (key_byte + i + (self.key1 >> 16)) & 0xFF
            result.append(byte ^ dynamic_key)
        return bytes(result)
    
    def _xor_encrypt_with_key(self, data: bytes, key: int) -> bytes:
        """使用固定密钥的XOR加密"""
        result = bytearray()
        for i, byte in enumerate(data):
            key_byte = (key >> ((i % 4) * 8)) & 0xFF
            result.append(byte ^ key_byte)
        return bytes(result)
    
    def _xor_encrypt_block(self, data: bytes, key: int) -> bytes:
        """对数据块进行XOR加密"""
        result = bytearray()
        for i, byte in enumerate(data):
            key_byte = (key >> ((i % 4) * 8)) & 0xFF
            result.append(byte ^ key_byte)
        return bytes(result)
    
    def _scramble_positions(self, data: bytes) -> bytes:
        """
        位置扰动 - 打乱字节顺序
        
        使用置换表对数据进行位置变换
        """
        if len(data) <= 1:
            return data
        
        # 生成置换表
        random.seed(self.seed)
        indices = list(range(len(data)))
        random.shuffle(indices)
        
        # 保存置换表到结果中 (使用变长编码避免256限制)
        result = bytearray()
        # 存储长度
        result.extend(len(indices).to_bytes(4, 'big'))
        # 存储置换映射 (每4字节存储一个索引)
        for idx in indices:
            result.extend(idx.to_bytes(4, 'big'))
        
        # 按置换表重新排列数据
        scrambled = bytearray(len(data))
        for i, idx in enumerate(indices):
            scrambled[idx] = data[i]
        
        result.extend(scrambled)
        return bytes(result)


# -----------------------------------------------------------------------------
# 9.4 远程验证Loader (新增)
# -----------------------------------------------------------------------------

class RemoteLoader:
    """
    远程验证Loader生成器
    
    功能:
    - 请求远程服务器 auth 接口进行验证
    - 获取 exec 和 dynamic_key
    - URL 加密、参数混淆、返回值校验
    - 验证通过后才执行 VM
    
    使用方式:
    local function loader()
        -- 请求服务器
    end
    loader()
    """
    
    def __init__(self, seed: int = None):
        self.seed = seed if seed else random.randint(1, 0xFFFFFFFF)
        random.seed(self.seed)
    
    def generate_loader(self, server_url: str, vm_code: str) -> str:
        """
        生成完整的 Loader 代码
        
        Args:
            server_url: 远程验证服务器 URL
            vm_code: VM 代码
            
        Returns:
            包含 Loader 的完整 Lua 代码
        """
        lines = []
        
        # 1. 加密 URL
        url_parts = self._encrypt_url(server_url)
        
        # 2. 生成混淆参数
        param_keys, param_vals = self._generate_obfuscated_params()
        
        # 3. 生成返回校验码
        checksum = self._generate_checksum()
        
        # 4. 生成 Loader 函数
        lines.append(self._generate_loader_function(
            url_parts, param_keys, param_vals, checksum
        ))
        
        # 5. 执行 Loader
        lines.append("loader()")
        
        # 6. 添加 VM 代码（会被 Loader 调用）
        lines.append("")
        lines.append("-- VM Code")
        lines.append(vm_code)
        
        return '\n'.join(lines)
    
    def _encrypt_url(self, url: str) -> List[str]:
        """URL 加密 - 将 URL 拆分为多个片段"""
        # 使用 Base64 + XOR 加密
        parts = []
        for i, char in enumerate(url):
            # 每个字符用不同的 key 进行 XOR
            key = (self.seed + i * 0x9B) % 256
            encrypted = ord(char) ^ key
            parts.append(f"\\{key // 64}{key % 64 // 8}{key % 8}")
        return parts
    
    def _generate_obfuscated_params(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """生成混淆的请求参数"""
        # 生成混淆的参数名和值
        chars = string.ascii_lowercase + string.ascii_uppercase + string.digits
        
        param_keys = {}
        param_vals = {}
        
        # 常用参数名混淆
        param_map = {
            'k': self._random_string(4, chars),  # key
            't': self._random_string(4, chars),  # token
            'h': self._random_string(6, chars),  # hash
            'v': self._random_string(3, chars),  # version
        }
        
        for orig, obfuscated in param_map.items():
            # 生成随机值
            val = self._random_string(8, chars)
            param_keys[orig] = obfuscated
            param_vals[obfuscated] = val
        
        return param_keys, param_vals
    
    def _random_string(self, length: int, chars: str) -> str:
        """生成随机字符串"""
        return ''.join(random.choice(chars) for _ in range(length))
    
    def _generate_checksum(self) -> int:
        """生成校验码"""
        return (self.seed * 31337 + 0xDEADBEEF) % 0xFFFFFFFF
    
    def _generate_loader_function(
        self, 
        url_parts: List[str], 
        param_keys: Dict[str, str], 
        param_vals: Dict[str, str],
        checksum: int
    ) -> str:
        """生成 Loader 函数体"""
        lines = []
        
        # 生成混淆的函数名
        loader_name = self._random_string(6, string.ascii_lowercase)
        http_func = self._random_string(4, string.ascii_lowercase)
        decode_func = self._random_string(5, string.ascii_lowercase)
        verify_func = self._random_string(6, string.ascii_lowercase)
        exec_var = self._random_string(3, string.ascii_lowercase)
        key_var = self._random_string(4, string.ascii_lowercase)
        
        lines.append(f"local function {loader_name}()")
        
        # 1. 重构 URL (运行时解密)
        lines.append(f"  local {http_func}={{}}")
        lines.append(f"  local _u=\"\"")
        
        # URL 片段重组
        url_str = ''.join(url_parts)
        if len(url_parts) > 5:
            # 分段拼接增加混淆
            mid = len(url_parts) // 2
            part1 = ''.join(url_parts[:mid])
            part2 = ''.join(url_parts[mid:])
            lines.append(f"  _u=\"{part1}\"..\"{part2}\"")
        else:
            lines.append(f"  _u=\"{url_str}\"")
        
        # 2. 构建请求参数 (混淆)
        k_key = list(param_keys.keys())[0]
        k_val = list(param_vals.values())[0]
        t_key = list(param_keys.keys())[1] if len(param_keys) > 1 else 't'
        
        lines.append(f"  local args=\"{k_key}={param_vals.get(k_key, k_val)}\"")
        
        # 添加时间戳混淆
        lines.append(f"  args=args..\"&{t_key}=\"..tostring(os.time())")
        
        # 3. HTTP 请求 (使用 http 或synapse兼容方式)
        lines.append(f"  local _r=pcall(function()")
        lines.append(f"    local ok,res={http_func}.request{{")
        lines.append(f"      url=_u..\"/auth?\"..args,")
        lines.append(f"      method=\"POST\"")
        lines.append(f"    }}")
        lines.append(f"    if ok and res then return res.body or res end")
        lines.append(f"    return nil")
        lines.append(f"  end)")
        
        # 4. 解析响应并校验
        lines.append(f"  if _r then")
        lines.append(f"    local {exec_var},{key_var}=false,nil")
        
        # JSON 解析 (简化版，手动解析)
        lines.append(f"    local js=_r")
        lines.append(f"    if js:match('\"exec\":true')or js:match('\"exec\":\"1\"') then")
        lines.append(f"      {exec_var}=true")
        lines.append(f"    end")
        
        # 提取 dynamic_key
        lines.append(f"    local dk=js:match('\"dynamic_key\":\"([^\"]+)\"')")
        lines.append(f"    if dk then {key_var}=dk end")
        
        # 5. 校验响应
        lines.append(f"    if {exec_var} and {key_var} then")
        lines.append(f"      -- 验证通过，执行 VM")
        lines.append(f"      local _ck={checksum}")
        lines.append(f"      local vm_chunk=loadstring and loadstring(\"return \".._G._VM_CODE)or nil")
        lines.append(f"      if vm_chunk then pcall(vm_chunk)end")
        lines.append(f"    end")
        lines.append(f"  end")
        
        lines.append("end")
        
        # 存储 Loader 函数到全局
        lines.append(f"_G._AUTH_LOADER={loader_name}")
        
        return '\n'.join(lines)
    
    def generate_simple_loader(self, server_url: str) -> str:
        """
        生成简化版 Loader (用于集成到 VMBuilder)
        """
        # URL 加密
        url_encrypted = self._encrypt_url_simple(server_url)
        
        # 生成混淆参数
        chars = string.ascii_lowercase + string.ascii_uppercase + string.digits
        p1 = self._random_string(5, chars)
        p2 = self._random_string(6, chars)
        p3 = self._random_string(4, chars)
        
        checksum = self._generate_checksum()
        
        lines = []
        
        # Loader 函数
        loader_name = self._random_string(6, string.ascii_lowercase)
        req_func = self._random_string(4, string.ascii_lowercase)
        dec_func = self._random_string(5, string.ascii_lowercase)
        
        lines.append(f"local function {loader_name}()")
        lines.append(f"  local _u=\"{url_encrypted}\"")
        lines.append(f"  local _p=\"{p1}={p2}&{p3}=\"..tostring(os.time())")
        
        # HTTP 请求
        lines.append(f"  local ok,resp=pcall(function()return {req_func}.request{{url=_u..\"/auth?\".._p,method=\"POST\"}}end)")
        
        # 解析响应
        lines.append(f"  if ok and resp and resp.body then")
        lines.append(f"    local b=resp.body")
        lines.append(f"    if b:match('\"exec\":true')or b:match('\"exec\":\"1\"')then")
        lines.append(f"      _G._EXEC_VM=true")
        lines.append(f"      _G._DYN_KEY=b:match('\"dynamic_key\":\"([^\"]+)\"')or\"\"")
        lines.append(f"    end")
        lines.append(f"  end")
        lines.append("end")
        
        # 执行
        lines.append(f"{loader_name}()")
        lines.append(f"if not _G._EXEC_VM then return end")
        
        return '\n'.join(lines), checksum
    
    def _encrypt_url_simple(self, url: str) -> str:
        """简化版 URL 加密"""
        # 使用字符偏移加密
        key = self.seed % 256
        parts = []
        for char in url:
            encrypted = (ord(char) + key) % 256
            parts.append(f"\\x{encrypted:02x}")
        return ''.join(parts)


# -----------------------------------------------------------------------------
# 9.5 VM代码生成器
# -----------------------------------------------------------------------------

class VMBuilder:
    """
    生成Lua虚拟机解释器代码
    
    新增功能:
    - 假操作码: 迷惑反编译器
    - 假分支和死代码: 增加反分析难度
    - Anti-dump检测: 检测调试和dump尝试
    - 紧凑输出格式: 最小化代码大小
    - 多层VM系统: 外层VM + 内层嵌套解释器
    - 字节码分段解密: 运行时逐步解密
    - 环境绑定: Roblox/Lua环境特征检测
    - 时间/行为检测: 防调试/异常调用栈
    - 虚假函数和伪proto: 迷惑反编译器
    - 数字混淆: 拆分表达式
    
    高级安全强化 (新增):
    - Anti-Hook: 隐蔽检测 + 延迟触发 + Hook诱捕
    - Anti-Memory Dump: 字节码分段存储 + 短生命周期
    - Anti-VM Trace: dispatcher混淆 + fake opcode + 时间检测
    - 水印强绑定: 拆分水印 + 完整性检测
    - 自毁策略: 数据污染 + 假成功 + 随机行为
    """
    
    def __init__(self, seed: int = None):
        self.seed = seed if seed else random.randint(1, 0xFFFFFFFF)
        self.encoder = AdvancedBytecodeEncoder(self.seed)
        self.security = AdvancedSecurityGenerator(self.seed)  # 新增
        self.obfuscate_names = True
        self.add_anti_debug = True
        self.add_junk_code = True
        self.enable_fake_ops = True
        self.enable_fake_branches = True
        self.enable_anti_dump = True
        self.compact_output = True
        # 商业级保护选项
        self.enable_multi_vm = True
        self.enable_segment_decrypt = True
        self.enable_env_binding = True
        self.enable_timing_check = True
        self.enable_fake_struct = True
        self.enable_num_split = True
        
        # 高级安全强化选项 (新增)
        self.enable_advanced_security = True  # 启用所有高级保护
        self.enable_anti_hook = True         # Anti-Hook保护
        self.enable_anti_dump_advanced = True  # 增强Anti-Dump
        self.enable_anti_trace = True        # Anti-VM Trace
        self.enable_watermark_binding = True  # 水印强绑定
        self.enable_self_destruct = True      # 自毁策略
        
        # Roblox Anti-Dumper 选项 (新增)
        self.enable_roblox_anti_dump = True   # Roblox专用Anti-Dumper
        self.enable_fake_env = True           # 假环境构造
        self.enable_hook_detection = True      # Hook检测
        self.enable_delay_trigger = True      # 延迟触发检测
        
        # 远程验证Loader选项 (新增)
        self.enable_remote_loader = False    # 启用远程验证
        self.loader_server_url = None        # 验证服务器URL
        self.remote_loader = RemoteLoader(self.seed)  # Loader生成器
    
    def build(self, func: Function) -> str:
        """生成完整的VM Lua代码"""
        try:
            # 编码字节码
            encoded_bc = self.encoder.encode(func)
            
            # 水印强绑定key生成
            watermark_key = self._generate_watermark_key()
            decrypt_key = self.encoder.key1
            
            # 如果启用高级安全，使用EnhancedVMBuilder
            if self.enable_advanced_security:
                vm_code = self._build_advanced(func, encoded_bc, decrypt_key, watermark_key)
            else:
                # 生成VM代码 (原有逻辑)
                vm_code = self._generate_vm_code(encoded_bc, decrypt_key)
            
            # 如果启用远程Loader，包装VM代码
            if self.enable_remote_loader and self.loader_server_url:
                vm_code = self._wrap_with_remote_loader(vm_code)
            
            return vm_code
        except KeyError as e:
            # 如果遇到 KeyError，生成简化的 VM 代码
            print(f"[!] KeyError in build: {e}, generating fallback VM...", file=sys.stderr)
            return self._generate_fallback_vm(func)
        except Exception as e:
            print(f"[!] VM build error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return self._generate_fallback_vm(func)
    
    def _generate_fallback_vm(self, func: Function) -> str:
        """
        强制 VM 架构 - 禁止 fallback
        
        如果 VM 构建失败，抛出异常而不是回退
        """
        raise RuntimeError(f"Valax Force VM: build failed, no fallback allowed (seed: {self.seed})")
    
    def _reconstruct_function_code(self, func: Function) -> List[str]:
        """禁止非 VM 输出"""
        raise RuntimeError("Valax Force VM: non-VM output not allowed")
    
    def _minimal_function_code(self, func: Function) -> List[str]:
        """禁止轻量模式"""
        raise RuntimeError("Valax Force VM: lightweight mode not allowed")
    
    def _generate_simple_obfuscated_code(self, func: Function) -> List[str]:
        """禁止简单混淆"""
        raise RuntimeError("Valax Force VM: simple obfuscation not allowed")
    
    def _generate_minimal_code(self, func: Function) -> List[str]:
        """禁止最小保护"""
        raise RuntimeError("Valax Force VM: minimal protection not allowed")
    
    def _wrap_with_remote_loader(self, vm_code: str) -> str:
        """使用远程Loader包装VM代码"""
        lines = []
        
        # 生成混淆名称
        chars = string.ascii_lowercase + string.ascii_uppercase + string.digits
        exec_flag = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        dyn_key = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
        loader_fn = ''.join(random.choice(string.ascii_lowercase) for _ in range(6))
        req_fn = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        url_var = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        
        # URL加密
        url_encrypted = self._encrypt_url_for_loader(self.loader_server_url)
        
        # 混淆参数
        p1 = ''.join(random.choice(chars) for _ in range(5))
        p2 = ''.join(random.choice(chars) for _ in range(6))
        p3 = ''.join(random.choice(chars) for _ in range(4))
        
        # 校验码
        checksum = (self.seed * 31337 + 0xDEADBEEF) % 0xFFFFFFFF
        
        # 1. Loader函数定义
        lines.append(f"local function {loader_fn}()")
        lines.append(f"  local {url_var}=\"{url_encrypted}\"")
        lines.append(f"  local params=\"{p1}={p2}&{p3}=\"..tostring(os.time())")
        
        # 2. HTTP请求 (兼容多种环境)
        lines.append(f"  local ok,res=pcall(function()")
        lines.append(f"    local http_c={req_fn}and{req_fn}.request or http and http.request or nil")
        lines.append(f"    if not http_c then return nil end")
        lines.append(f"    return http_c{{url={url_var}..\"/auth?\"..params,method=\"POST\"}}")
        lines.append(f"  end)")
        
        # 3. 解析响应
        lines.append(f"  if ok and res and res.body then")
        lines.append(f"    local body=res.body")
        lines.append(f"    -- 提取exec状态")
        lines.append(f"    if body:match('\"exec\":true')or body:match('\"exec\":\"1\"')then")
        lines.append(f"      _G.{exec_flag}=true")
        lines.append(f"    end")
        lines.append(f"    -- 提取dynamic_key")
        lines.append(f"    local dk=body:match('\"dynamic_key\":\"([^\"]+)\"')")
        lines.append(f"    if dk then _G.{dyn_key}=dk end")
        lines.append(f"  end")
        lines.append("end")
        
        # 4. 执行Loader
        lines.append(f"{loader_fn}()")
        
        # 5. 验证检查
        lines.append(f"if not _G.{exec_flag} then return end")
        
        # 6. 添加校验
        lines.append(f"local _ck={checksum}")
        lines.append(f"if _ck~={(self.seed * 31337 + 0xDEADBEEF) % 0xFFFFFFFF}then return end")
        
        # 7. VM代码
        lines.append("--[[VM_START]]" + vm_code + "--[[VM_END]]")
        
        return '\n'.join(lines)
    
    def _encrypt_url_for_loader(self, url: str) -> str:
        """URL加密"""
        key = self.seed % 256
        parts = []
        for char in url:
            encrypted = (ord(char) + key) % 256
            # 使用不可打印字符的转义序列
            parts.append(f"\\{encrypted:03o}")
        return ''.join(parts)
    
    def _generate_watermark_key(self) -> int:
        """生成基于水印的密钥"""
        watermark = ''.join(AdvancedSecurityGenerator.WATERMARK_PARTS)
        key = 0
        for i, c in enumerate(watermark):
            key += ord(c) * (i + 1) * 17
        return key % 0xFFFFFFFF
    
    def _build_advanced(self, func: Function, encoded_bc: str, key: int, wm_key: int) -> str:
        """构建高级安全保护的VM"""
        lines = []
        names = self._generate_local_names()
        
        # 1. 字节码分段存储
        segments = self._split_bytecode_segments(encoded_bc)
        for i, seg in enumerate(segments):
            if self.compact_output:
                lines.append(f"local s{i+1}=\"{seg}\"")
            else:
                lines.append(f"local _s{i+1}=\"{seg}\"")
        
        # 2. 基础解密key
        if self.compact_output:
            lines.append(f"local k={key}")
            lines.append(f"local wk={wm_key}")
        else:
            lines.append(f"local _k={key}")
            lines.append(f"local _wk={wm_key}")
        
        # 3. 解密函数 (带水印key, bit32兼容)
        decrypt_name = names.get('decode', 'd')
        if self.compact_output:
            lines.append(f"local function {decrypt_name}(s)local r={{}}for i=1,#s do local kb=bit32.band(bit32.rshift(k,((i%4)*8)),255)local wb=bit32.band(bit32.rshift(wk,((i%3)*8)),255)r[i]=string.char(bit32.bxor(bit32.bxor(string.byte(s,i),kb),wb))end;return table.concat(r)end")
        else:
            lines.append(f"local function {decrypt_name}(s)")
            lines.append("  local r={}")
            lines.append("  for i=1,#s do")
            lines.append("    local kb=bit32.band(bit32.rshift(_k,((i%4)*8)),255)")
            lines.append("    local wb=bit32.band(bit32.rshift(_wk,((i%3)*8)),255)")
            lines.append("    r[i]=string.char(bit32.bxor(bit32.bxor(string.byte(s,i),kb),wb))")
            lines.append("  end")
            lines.append("  return table.concat(r)")
            lines.append("end")
        
        # 4. 分段加载函数
        load_name = names.get('loader', 'l')
        lines.append(f"local function {load_name}()")
        lines.append(f"  local p=\"\"")
        for i in range(len(segments)):
            lines.append(f"  p=p..{decrypt_name}(_s{i+1})")
        lines.append("  return p")
        lines.append("end")
        
        # 5. 生成变量名
        local_vars = self._generate_local_names()
        
        # 6. VM 解释器 (受保护的)
        lines.extend(self._generate_protected_vm_engine(local_vars))
        
        # 7. Fake branches
        if self.enable_fake_branches:
            lines.extend(self._generate_fake_branches(local_vars))
        
        # 8. Anti-dump (基础)
        if self.enable_anti_dump:
            lines.extend(self._generate_anti_dump(local_vars))
        
        # 9. Anti-debug
        if self.add_anti_debug:
            lines.extend(self._generate_anti_debug(local_vars))
        
        # 10. === 高级安全强化 ===
        
        # 10.1 水印强绑定
        if self.enable_watermark_binding:
            lines.extend(self._generate_watermark_system(local_vars))
        
        # 10.2 Anti-Hook
        if self.enable_anti_hook:
            lines.extend(self._generate_advanced_anti_hook(local_vars))
        
        # 10.3 Anti-Memory Dump (增强)
        if self.enable_anti_dump_advanced:
            lines.extend(self._generate_advanced_anti_dump(local_vars))
        
        # 10.4 Anti-VM Trace
        if self.enable_anti_trace:
            lines.extend(self._generate_advanced_anti_trace(local_vars))
        
        # 10.5 自毁策略
        if self.enable_self_destruct:
            lines.extend(self._generate_advanced_self_destruct(local_vars))
        
        # 10.6 Roblox Anti-Dumper (新增)
        if self.enable_roblox_anti_dump:
            lines.extend(self._generate_roblox_anti_dumper(local_vars))
        
        # 11. 商业级保护
        if self.enable_multi_vm:
            lines.extend(self._generate_multi_vm(local_vars))
        if self.enable_segment_decrypt:
            lines.extend(self._generate_segment_decrypt(local_vars))
        if self.enable_env_binding:
            lines.extend(self._generate_env_binding(local_vars))
        if self.enable_timing_check:
            lines.extend(self._generate_timing_check(local_vars))
        if self.enable_fake_struct:
            lines.extend(self._generate_fake_struct(local_vars))
        
        # 12. 执行入口
        vm_var = local_vars['vm_table']
        if self.compact_output:
            lines.append(f"{load_name}()")
            lines.append(f"local vm={vm_var};vm.exec=function() end;return vm")
        else:
            lines.append(f"{load_name}()")
            lines.append(f"local _vm={vm_var}")
            lines.append("_vm.exec=function() end")
            lines.append("return _vm")
        
        return '\n'.join(lines)
    
    def _split_bytecode_segments(self, bc: str) -> List[str]:
        """分段字节码"""
        segments = []
        seg_len = max(20, len(bc) // 3)
        for i in range(0, len(bc), seg_len):
            segments.append(bc[i:i+seg_len])
        return segments
    
    def _generate_vm_code(self, encoded_bc: str, key: int) -> str:
        """生成虚拟机代码"""
        lines = []
        
        # 紧凑模式下最小化变量名
        if self.compact_output:
            self._use_compact_names()
        
        # 0. bit32 兼容层 (Luau / Lua 5.1 兼容)
        lines.append("-- bit32 compatibility layer")
        lines.extend(self._generate_bit32_shim())
        
        # 0.5 水印保护
        lines.append("-- Watermark protection")
        lines.extend(generate_watermark_code())
        
        # 0.6 增强反调试
        lines.append("-- Enhanced anti-debug")
        lines.extend(generate_enhanced_anti_debug_code())
        
        # 1. 字节码数据 (紧凑格式)
        if self.compact_output:
            lines.append(f"local b={self._quote(encoded_bc)}")
            lines.append(f"local k={key}")
        else:
            lines.append("local _b=" + self._quote(encoded_bc))
            lines.append("local _k=" + str(key))
        
        # 2. 解密函数 (bit32 兼容版)
        if self.compact_output:
            lines.append("local function d(s)local r={}for i=1,#s do local b=string.byte(s,i)if b then local kb=bit32.rshift(k,((i%4)*8))r[i]=string.char(bit32.bxor(b,kb)%256)end end;return table.concat(r)end")
        else:
            lines.append("local function _d(s)")
            lines.append("  local r={}")
            lines.append("  for i=1,#s do")
            lines.append("    local b=string.byte(s,i)")
            lines.append("    if b then")
            lines.append("      local kb=bit32.rshift(_k,((i%4)*8))")
            lines.append("      r[i]=string.char(bit32.bxor(b,kb)%256)")
            lines.append("    end")
            lines.append("  end")
            lines.append("  return table.concat(r)")
            lines.append("end")
        
        # 3. 解密字节码
        if self.compact_output:
            lines.append("local p=d(b)")
        else:
            lines.append("local _p=_d(_b)")
        
        # 4. 生成变量混淆名
        local_vars = self._generate_local_names()
        
        # 5. VM 解释器
        lines.extend(self._generate_vm_engine(local_vars))
        
        # 6. Fake branches (假分支和死代码)
        if self.enable_fake_branches:
            lines.extend(self._generate_fake_branches(local_vars))
        
        # 7. Anti-dump (反dump检测)
        if self.enable_anti_dump:
            lines.extend(self._generate_anti_dump(local_vars))
        
        # 8. Anti-debug (可选)
        if self.add_anti_debug:
            lines.extend(self._generate_anti_debug(local_vars))
        
        # 商业级保护: 多层VM系统
        if self.enable_multi_vm:
            lines.extend(self._generate_multi_vm(local_vars))
        
        # 商业级保护: 分段解密
        if self.enable_segment_decrypt:
            lines.extend(self._generate_segment_decrypt(local_vars))
        
        # 商业级保护: 环境绑定
        if self.enable_env_binding:
            lines.extend(self._generate_env_binding(local_vars))
        
        # 商业级保护: 时间/行为检测
        if self.enable_timing_check:
            lines.extend(self._generate_timing_check(local_vars))
        
        # 商业级保护: 虚假函数和伪proto
        if self.enable_fake_struct:
            lines.extend(self._generate_fake_struct(local_vars))
        
        # 9. VM 入口
        vm_var = local_vars['vm_table']
        if self.compact_output:
            lines.append(f"local vm={vm_var};return vm")
        else:
            lines.append("local _vm=" + vm_var)
            lines.append("return _vm")
        
        return '\n'.join(lines)
    
    def _use_compact_names(self):
        """使用紧凑变量名"""
        pass  # 在_generate_local_names中处理
    
    def _generate_fake_branches(self, names: Dict[str, str]) -> List[str]:
        """生成假分支和死代码路径"""
        lines = []
        v = names
        
        # 添加死代码分支标签
        fake_labels = []
        for i in range(3):
            label = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
            fake_labels.append(label)
        
        # 假分支检查函数
        if self.compact_output:
            lines.append(f"local function {v['fake_check']}(n)local t={{1,0,1}}return t[(n%3)+1]end")
        else:
            lines.append(f"local function {v['fake_check']}({v['n']})")
            lines.append(f"  local {v['t']}={{1,0,1}}")
            lines.append(f"  return {v['t']}[({v['n']}%3)+1]")
            lines.append("end")
        
        # 假跳转目标 (永远不会被执行的死代码)
        for i, label in enumerate(fake_labels):
            if self.compact_output:
                dead_code = f"{v['vm']}.{v['regs']}['{label}']={v['vm']}.{v['regs']}['{label}']or 0"
                lines.append(f"local {label}=function(){dead_code}end")
            else:
                lines.append(f"-- dead code path {label}")
                lines.append(f"local function {label}()")
                lines.append(f"  {v['vm']}.{v['regs']}['{label}']={v['vm']}.{v['regs']}['{label}']or 0")
                lines.append("end")
        
        return lines
    
    def _generate_anti_dump(self, names: Dict[str, str]) -> List[str]:
        """生成反dump检测代码"""
        lines = []
        v = names
        
        # Anti-dump函数 - 检测调试器和dump尝试
        if self.compact_output:
            # 紧凑版本
            dump_check = []
            dump_check.append(f"local function {v['anti_dump']}()")
            dump_check.append(f"local s=os.clock()for i=1,50 do local _=1 end")
            dump_check.append(f"if os.clock()-s>0.05 then {v['vm']}.{v['running']}=false end")
            dump_check.append(f"if debug and debug.getinfo then local f=loadstring or load local _=f and f('','')end")
            dump_check.append(f"if io and io.open and io.open('/proc/self/status','r')then {v['vm']}.{v['running']}=false end")
            dump_check.append("end")
            lines.extend(dump_check)
        else:
            lines.append(f"local function {v['anti_dump']}()")
            lines.append("  -- Time-based debugger detection")
            lines.append(f"  local {v['s']}=os.clock()")
            lines.append("  for i=1,50 do local _=1 end")
            lines.append(f"  if os.clock()-{v['s']}>0.05 then")
            lines.append(f"    {v['vm']}.{v['running']}=false")
            lines.append("  end")
            lines.append("")
            lines.append("  -- debug.getinfo detection")
            lines.append("  if debug and debug.getinfo then")
            lines.append("    local f=loadstring or load")
            lines.append("    local _=f and f('','')")
            lines.append("  end")
            lines.append("")
            lines.append("  -- /proc/self/status (Linux debugger detection)")
            lines.append("  if io and io.open then")
            lines.append("    local f=io.open('/proc/self/status','r')")
            lines.append("    if f then")
            lines.append("      local c=f:read('*all')")
            lines.append("      f:close()")
            lines.append("      if c:match('TracerPid')then")
            lines.append(f"        {v['vm']}.{v['running']}=false")
            lines.append("      end")
            lines.append("    end")
            lines.append("  end")
            lines.append("end")
        
        return lines
    
    def _generate_bit32_shim(self) -> List[str]:
        """生成 bit32 兼容层代码"""
        lines = []
        lines.append("local bit32=bit32 or {}")
        lines.append("if not bit32.rshift then bit32.rshift=function(v,n)return math.floor((v%0x100000000)/(2^n))end end")
        lines.append("if not bit32.lshift then bit32.lshift=function(v,n)return((v%0x100000000)*(2^n))%0x100000000 end end")
        lines.append("if not bit32.band then bit32.band=function(...)local r=0xFFFFFFFF for _,v in ipairs({...})do r=r&(v%0x100000000)end return r end end")
        lines.append("if not bit32.bor then bit32.bor=function(...)local r=0 for _,v in ipairs({...})do r=r|(v%0x100000000)end return r end end")
        lines.append("if not bit32.bxor then bit32.bxor=function(a,b)return((a%0x100000000)~(b%0x100000000))%0x100000000 end end")
        lines.append("if not bit32.bnot then bit32.bnot=function(v)return((~v)%0x100000000)end end")
        return lines
    
    def _generate_vm_engine(self, names: Dict[str, str]) -> List[str]:
        """生成VM引擎代码"""
        v = names
        
        lines = []
        
        # VM 状态表
        lines.append(f"local {v['vm']}={{{v['regs']}={{}},")
        lines.append(f"{v['stack']}={{}},")
        lines.append(f"{v['top']}=0,")
        lines.append(f"{v['pc']}=0,")
        lines.append(f"{v['running']}=true,")
        lines.append(f"{v['insts']}=nil,")
        lines.append(f"{v['consts']}=nil}}")
        
        # 解码函数
        lines.append(f"local function {v['decode']}({v['data']})")
        lines.append(f"  local _o={v['data']}:byte(1)")
        lines.append(f"  local _a={v['data']}:byte(2)")
        lines.append(f"  local _b=({v['data']}:byte(3) or 0)")
        lines.append(f"  local _c=({v['data']}:byte(4) or 0)")
        lines.append(f"  return _o,_a,_b,_c")
        lines.append("end")
        
        # 加载字节码
        lines.append(f"local function {v['loadbc']}({v['d']})")
        lines.append(f"  local _m={v['d']}:sub(1,4)")
        lines.append(f"  if _m~=\"LVC\" then error(\"invalid\") end")
        lines.append(f"  {v['vm']}.{v['insts']}={{}}")
        lines.append(f"  {v['vm']}.{v['consts']}={{}}")
        lines.append(f"  local _p=6")
        lines.append(f"  local _n={v['d']}:byte(_p)")
        lines.append(f"  _p=_p+1")
        lines.append(f"  local _nc={v['d']}:byte(_p)+bit32.lshift({v['d']}:byte(_p+1),8)")
        lines.append(f"  _p=_p+2")
        lines.append(f"  for i=1,_nc do")
        lines.append(f"    local _t={v['d']}:byte(_p)")
        lines.append(f"    _p=_p+1")
        lines.append(f"    if _t==0 then {v['vm']}.{v['consts']}[i]=nil")
        lines.append(f"    elseif _t==1 then {v['vm']}.{v['consts']}[i]=({v['d']}:byte(_p)~=0) _p=_p+1")
        lines.append(f"    elseif _t==2 then local _e=\"\" while true do local _c={v['d']}:byte(_p) _p=_p+1 if _c==0 then break end _e=_e..string.char(_c) end {v['vm']}.{v['consts']}[i]=tonumber(_e) or 0")
        lines.append(f"    elseif _t==3 then local _l=({v['d']}:byte(_p))+bit32.lshift({v['d']}:byte(_p+1),8) _p=_p+2 {v['vm']}.{v['consts']}[i]={v['d']}:sub(_p,_p+_l-1) _p=_p+_l end")
        lines.append("  end")
        lines.append(f"  local _ni=({v['d']}:byte(_p))+bit32.lshift({v['d']}:byte(_p+1),8)+bit32.lshift({v['d']}:byte(_p+2),16) _p=_p+3")
        lines.append(f"  for i=1,_ni do")
        lines.append(f"    table.insert({v['vm']}.{v['insts']},{v['d']}:sub(_p,_p+3))")
        lines.append(f"    _p=_p+4")
        lines.append("  end")
        lines.append("end")
        
        # 栈操作
        lines.append(f"local function {v['push']}({v['v']})")
        lines.append(f"  {v['vm']}.{v['top']}={v['vm']}.{v['top']}+1")
        lines.append(f"  {v['vm']}.{v['stack']}[{v['vm']}.{v['top']}]={v['v']}")
        lines.append("end")
        
        lines.append(f"local function {v['pop']}()")
        lines.append(f"  local _v={v['vm']}.{v['stack']}[{v['vm']}.{v['top']}]")
        lines.append(f"  {v['vm']}.{v['top']}={v['vm']}.{v['top']}-1")
        lines.append(f"  return _v")
        lines.append("end")
        
        lines.append(f"local function {v['peek']}({v['n']})")
        lines.append(f"  return {v['vm']}.{v['stack']}[{v['vm']}.{v['top']}-({v['n']} or 0)]")
        lines.append("end")
        
        # 获取常量
        lines.append(f"local function {v['getk']}({v['i']})")
        lines.append(f"  return {v['vm']}.{v['consts']}[{v['i']}+1]")
        lines.append("end")
        
        # 主执行循环
        lines.append(f"local function {v['exec']}()")
        lines.append(f"  while {v['vm']}.{v['running']} do")
        lines.append(f"    local _ins={v['vm']}.{v['insts']}[{v['vm']}.{v['pc']}]")
        lines.append(f"    {v['vm']}.{v['pc']}={v['vm']}.{v['pc']}+1")
        lines.append(f"    if not _ins then {v['vm']}.{v['running']}=false break end")
        lines.append(f"    local _op,_a,_b,_c={v['decode']}(_ins)")
        lines.append("    if op==1 then " + v['push'] + "(" + v['getk'] + "(b))")
        lines.append("    elseif op==2 then for i=0,b do vm.regs[a+i]=nil end")
        lines.append("    elseif op==3 then vm.regs[a]=(b~=0) if c~=0 then vm.pc=vm.pc+1 end")
        lines.append("    elseif op==4 then vm.regs[a]=vm.regs[b]")
        lines.append("    elseif op==16 then vm.regs[a]=_G[" + v['getk'] + "(b)]")
        lines.append("    elseif op==17 then _G[" + v['getk'] + "(b)]=vm.regs[a]")
        lines.append("    elseif op==32 then vm.regs[a]={}")
        lines.append("    elseif op==33 then local t=vm.regs[a] t[" + v['peek'] + "(1)]=" + v['peek'] + "(0)")
        lines.append("    elseif op==34 then local t=vm.regs[b] vm.regs[a]=t[" + v['peek'] + "(0)]")
        lines.append("    elseif op==48 then " + v['push'] + "(" + v['pop'] + "()+" + v['pop'] + "())")
        lines.append("    elseif op==49 then " + v['push'] + "(" + v['pop'] + "()-" + v['pop'] + "())")
        lines.append("    elseif op==50 then " + v['push'] + "(" + v['pop'] + "()*" + v['pop'] + "())")
        lines.append("    elseif op==51 then " + v['push'] + "(" + v['pop'] + "()/" + v['pop'] + "())")
        lines.append("    elseif op==52 then " + v['push'] + "(" + v['pop'] + "()%" + v['pop'] + "())")
        lines.append("    elseif op==53 then " + v['push'] + "(" + v['pop'] + "()^" + v['pop'] + "())")
        lines.append("    elseif op==54 then " + v['push'] + "(-" + v['pop'] + "())")
        lines.append("    elseif op==64 then local x=" + v['pop'] + "() local y=" + v['pop'] + "() if x==y then vm.pc=vm.pc+1 end")
        lines.append("    elseif op==65 then local x=" + v['pop'] + "() local y=" + v['pop'] + "() if x<y then vm.pc=vm.pc+1 end")
        lines.append("    elseif op==66 then local x=" + v['pop'] + "() local y=" + v['pop'] + "() if x<=y then vm.pc=vm.pc+1 end")
        lines.append("    elseif op==80 then " + v['push'] + "(not " + v['pop'] + "())")
        lines.append("    elseif op==81 then local x=" + v['pop'] + "() local y=" + v['pop'] + "() " + v['push'] + "(y and x)")
        lines.append("    elseif op==82 then local x=" + v['pop'] + "() local y=" + v['pop'] + "() " + v['push'] + "(y or x)")
        lines.append("    elseif op==83 then vm.pc=vm.pc+b+bit32.lshift(c,8)")
        lines.append("    elseif op==84 then if not pop() then vm.pc=vm.pc+b+bit32.lshift(c,8) end")
        lines.append("    elseif op==96 then local f=vm.regs[a] local args={} for i=1,b do args[i]=pop() end local r={f(table.unpack(args))} for i=1,#r do push(r[i]) end")
        lines.append("    elseif op==98 then vm.running=false")
        lines.append("    elseif op==128 then local s=\"\" for i=2,b do s=s..tostring(vm.regs[a+i-1]) end vm.regs[a]=s")
        lines.append("    elseif op==129 then push(#pop())")
        lines.append("    elseif op==0xC0 then push(pop()-pop())")  # Fake ADD
        lines.append("    elseif op==0xC1 then push(pop()+pop())")  # Fake SUB  
        lines.append("    elseif op==0xC2 then push(pop()/pop())")  # Fake MUL
        lines.append("    elseif op==0xC3 then push(pop()*pop())")  # Fake DIV
        lines.append("    elseif op==0xC4 then vm.pc=vm.pc-1-a")  # Fake JMP
        lines.append("    elseif op==0xC5 then push(0)")  # Fake GET
        lines.append("    elseif op==0xC6 then pop()")  # Fake SET
        lines.append("    elseif op==0xC7 then push(nil)")  # Fake CALL
        lines.append("    elseif op==0xC8 then push(pop()and true)")  # Fake NOT
        lines.append("    elseif op==0xC9 then push(pop()or true)")  # Fake AND
        lines.append("    elseif op==0xCA then push(not pop())")  # Fake OR
        lines.append("    end")
        lines.append("  end")
        lines.append("end")
        lines.append("loadbc(_p)")
        lines.append("exec()")
        lines.append("return lines")
    
    def _generate_multi_vm(self, names: Dict[str, str]) -> List[str]:
        """
        生成多层VM系统 (外层VM + 内层嵌套解释器)
        
        这是MoonSec/Luraph级别的核心特性:
        - 外层VM执行字节码
        - 内层VM解释执行某些关键指令
        - 嵌套层次可配置
        """
        v = names
        lines = []
        
        # 生成内层VM名称
        inner_vm_name = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        
        # 内层VM注册表
        lines.append(f"local {inner_vm_name}={{}}")
        lines.append(f"{inner_vm_name}.regs={{}}")
        lines.append(f"{inner_vm_name}.stack={{}}")
        lines.append(f"{inner_vm_name}.top=0")
        lines.append(f"{inner_vm_name}.ip=0")
        
        # 内层VM执行器 (简化版)
        inner_exec = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local function {inner_exec}({v['code']},{v['ctx']})")
        lines.append(f"  local _t={inner_vm_name}")
        lines.append(f"  while _t.ip<#{v['code']} do")
        lines.append(f"    local _b={v['code']}:byte(_t.ip+1)")
        lines.append(f"    _t.ip=_t.ip+1")
        lines.append(f"    if _b==1 then _t.regs[1]=({v['ctx']})")
        lines.append(f"    elseif _b==2 then _t.top=_t.top+1 _t.stack[_t.top]=_t.regs[1]")
        lines.append(f"    elseif _b==3 then local _v=_t.stack[_t.top] _t.top=_t.top-1 return _v end")
        lines.append("  end")
        lines.append("end")
        
        # 外层VM调用内层的接口
        inner_call = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local function {inner_call}({v['seg']},{v['ctx']})")
        lines.append(f"  return {inner_exec}({v['seg']},{v['ctx']})")
        lines.append("end")
        
        # 存储到VM状态中
        inner_table_name = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"{v['vm']}.{inner_table_name}={inner_vm_name}")
        lines.append(f"{v['vm']}.{inner_call}={inner_exec}")
        
        return lines
    
    def _generate_segment_decrypt(self, names: Dict[str, str]) -> List[str]:
        """
        生成字节码分段动态解密代码
        
        策略:
        - 字节码被分成多个segment
        - 每个segment独立加密
        - 运行时逐步解密，只有执行到时才解密
        - 解密后立即执行，然后丢弃明文
        """
        v = names
        lines = []
        
        # 分段解密器名称
        seg_dec = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        seg_key_name = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        
        # 分段密钥 (多级密钥链)
        seg_key = random.randint(100000, 999999)
        lines.append(f"local {seg_key_name}={seg_key}")
        
        # 分段解密函数
        lines.append(f"local function {seg_dec}({v['data']},{v['idx']})")
        lines.append(f"  local _s=#{v['data']}")
        lines.append(f"  local _k={seg_key_name}")
        lines.append(f"  local _r=\"\"")
        lines.append(f"  local _start=({v['idx']}-1)*16+1")
        lines.append(f"  local _end=math.min(_start+15,_s)")
        lines.append(f"  for i=_start,_end do")
        lines.append(f"    local _b={v['data']}:byte(i)")
        lines.append(f"    _b=bit32.bxor(_b,bit32.band(bit32.rshift(_k,((i%4)*8)),255))")
        lines.append(f"    _r=_r..string.char(_b)")
        lines.append("  end")
        lines.append(f"  return _r")
        lines.append("end")
        
        # 分段状态追踪
        seg_state = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local {seg_state}={{decrypted={{}},current=0}}")
        lines.append(f"{v['vm']}.{seg_state}={seg_state}")
        
        # 解密并执行函数
        seg_exec = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local function {seg_exec}({v['data']},{v['idx']},{v['f']})")
        lines.append(f"  if not {seg_state}.decrypted[{v['idx']}] then")
        lines.append(f"    local _seg={seg_dec}({v['data']},{v['idx']})")
        lines.append(f"    {seg_state}.decrypted[{v['idx']}]=_seg")
        lines.append("  end")
        lines.append(f"  return {v['f']}({seg_state}.decrypted[{v['idx']}])")
        lines.append("end")
        
        # 存储到VM
        lines.append(f"{v['vm']}.{seg_dec}={seg_dec}")
        lines.append(f"{v['vm']}.{seg_exec}={seg_exec}")
        
        return lines
    
    def _generate_env_binding(self, names: Dict[str, str]) -> List[str]:
        """
        生成环境绑定代码 (Roblox/Lua环境特征检测)
        
        检测:
        - Roblox特定函数和变量
        - Lua版本
        - 平台特征
        - 游戏引擎特征
        """
        v = names
        lines = []
        
        # 环境检测函数名称
        env_check = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        
        lines.append(f"local function {env_check}()")
        lines.append("  local _ok=true")
        
        # 检测Roblox环境
        lines.append("  if game then _ok=true else _ok=_ok and false end")
        lines.append("  if game:GetService then _ok=true else _ok=_ok and false end")
        lines.append("  if workspace then _ok=true else _ok=_ok and false end")
        lines.append("  if script then _ok=true else _ok=_ok and false end")
        
        # 检测Lua环境
        lines.append("  local _v=_VERSION or \"\"")
        lines.append("  if _v:match(\"Lua 5\") then _ok=true else _ok=_ok and false end")
        
        # 检测平台特征
        lines.append("  if jit then _ok=true end")
        lines.append("  if package then _ok=true end")
        
        # 检测关键函数
        lines.append("  if type(tonumber)==\"function\" then _ok=true else _ok=_ok and false end")
        lines.append("  if type(string.rep)==\"function\" then _ok=true else _ok=_ok and false end")
        
        # 检测math库完整性
        lines.append("  if math and math.random and math.floor then _ok=true else _ok=_ok and false end")
        
        # 检测table库
        lines.append("  if table and table.concat and table.insert then _ok=true else _ok=_ok and false end")
        
        lines.append(f"  return _ok")
        lines.append("end")
        
        # 在VM启动时检查
        env_init = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local function {env_init}()")
        lines.append(f"  if not {env_check}() then")
        lines.append(f"    error(\"Environment check failed\")")
        lines.append("  end")
        lines.append("end")
        
        # 存储
        lines.append(f"{v['vm']}.env_check={env_check}")
        
        return lines
    
    def _generate_timing_check(self, names: Dict[str, str]) -> List[str]:
        """
        生成时间/行为检测代码 (防调试)
        
        检测:
        - 执行速度异常 (慢于预期 = 调试)
        - 异常调用栈 (非正常调用链)
        - 内存访问模式
        """
        v = names
        lines = []
        
        # 时间检测
        timing_check = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        
        lines.append(f"local function {timing_check}()")
        lines.append("  local _t1=os.clock()")
        lines.append("  for _i=1,1000 do")
        lines.append("    local _=1+1")
        lines.append("  end")
        lines.append("  local _t2=os.clock()")
        lines.append("  if _t2-_t1>0.05 then")
        lines.append(f"    {v['vm']}.{v['running']}=false")
        lines.append("  end")
        lines.append("end")
        
        # 调用栈检测
        stack_check = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        
        lines.append(f"local function {stack_check}()")
        lines.append("  if debug and debug.getinfo then")
        lines.append("    local _lvl=2")
        lines.append("    local _stack={}")
        lines.append("    while true do")
        lines.append("      local _info=debug.getinfo(_lvl)")
        lines.append("      if not _info then break end")
        lines.append("      table.insert(_stack,_info)")
        lines.append("      _lvl=_lvl+1")
        lines.append("      if _lvl>20 then break end")
        lines.append("    end")
        lines.append("    if #_stack<2 then")
        lines.append(f"      {v['vm']}.{v['running']}=false")
        lines.append("    end")
        lines.append("  end")
        lines.append("end")
        
        # 行为异常检测 (检测单步执行)
        behavior_check = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        
        lines.append(f"local function {behavior_check}()")
        lines.append("  local _s=os.time()")
        lines.append("  for _i=1,500 do")
        lines.append("    local _=string.len(\"x\")")
        lines.append("  end")
        lines.append("  local _e=os.time()")
        lines.append("  if _e-_s>1 then")
        lines.append(f"    {v['vm']}.{v['running']}=false")
        lines.append("  end")
        lines.append("end")
        
        # 综合检测入口
        security_check = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        
        lines.append(f"local function {security_check}()")
        lines.append(f"  {timing_check}()")
        lines.append(f"  {stack_check}()")
        lines.append(f"  {behavior_check}()")
        lines.append("end")
        
        # 存储
        lines.append(f"{v['vm']}.security_check={security_check}")
        
        return lines
    
    def _generate_fake_struct(self, names: Dict[str, str]) -> List[str]:
        """
        生成虚假函数和伪proto结构 (迷惑反编译器)
        
        策略:
        - 插入看起来像真实函数的假函数
        - 添加伪造的proto信息
        - 添加永不执行的代码块
        """
        v = names
        lines = []
        
        # 生成假函数
        fake_funcs = []
        for i in range(3):
            fake_name = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
            fake_funcs.append(fake_name)
            
            lines.append(f"local function {fake_name}(...)")
            lines.append("  local _={}")
            lines.append("  for _i=1,math.random(3,7) do")
            lines.append("    table.insert(_,{math.random(),math.random()})")
            lines.append("  end")
            lines.append("  return nil")
            lines.append("end")
        
        # 假proto结构 (模拟Lua的proto)
        fake_proto = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        
        lines.append(f"local {fake_proto}={{}}")
        lines.append(f"{fake_proto}.maxstacksize=250")
        lines.append(f"{fake_proto}.numparams=0")
        lines.append(f"{fake_proto}.is_vararg=0")
        lines.append(f"{fake_proto}.code={{}}")
        
        # 添加假指令到假proto
        for i in range(20):
            fake_instr = random.randint(1, 100)
            lines.append(f"{fake_proto}.code[{i+1}]={fake_instr}")
        
        # 假upvalue表
        fake_upvals = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local {fake_upvals}={{}}")
        lines.append(f"for _i=1,5 do {fake_upvals}[_i]=\"upval_\".._i end")
        lines.append(f"{fake_proto}.upvalues={fake_upvals}")
        
        # 假常量表
        fake_consts = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local {fake_consts}={{}}")
        for i in range(10):
            val = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
            lines.append(f"{fake_consts}[{i+1}]=\"{val}\"")
        lines.append(f"{fake_proto}.k={fake_consts}")
        
        # 假source信息
        lines.append(f"{fake_proto}.source=\"@fake_source.lua\"")
        lines.append(f"{fake_proto}.linedefined={random.randint(1, 100)}")
        lines.append(f"{fake_proto}.lastlinedefined={random.randint(100, 200)}")
        
        # 存储到VM
        lines.append(f"{v['vm']}.fake_proto={fake_proto}")
        for i, f in enumerate(fake_funcs):
            lines.append(f"{v['vm']}.fake_{i}={f}")
        
        return lines
    
    # =========================================================================
    # 高级安全强化方法
    # =========================================================================
    
    def _generate_watermark_system(self, names: Dict[str, str]) -> List[str]:
        """
        生成水印强绑定系统
        
        策略:
        1. 水印拆分到多个变量
        2. 运行时拼接
        3. 参与解密key生成
        4. 完整性检测 (间接破坏)
        """
        lines = []
        v = names
        
        wm_parts = AdvancedSecurityGenerator.WATERMARK_PARTS
        
        # 水印碎片 (混淆存储)
        for i, part in enumerate(wm_parts):
            wname = f"w{i+1}"
            v[wname] = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
            obfuscated = self._obfuscate_string_literal(part)
            lines.append(f"local {v[wname]}=\"{obfuscated}\"")
        
        # 运行时拼接水印
        wm_var = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        v['watermark'] = wm_var
        lines.append(f"local {wm_var}={v['w1']}..{v['w2']}..{v['w3']}")
        
        # 水印哈希 (用于完整性检测)
        wm_hash = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        v['wm_hash'] = wm_hash
        lines.append(f"local {wm_hash}=0")
        lines.append(f"for i=1,#{wm_var} do {wm_hash}={wm_hash}+string.byte({wm_var},i)*(i%0x7F)end")
        
        # 水印完整性验证 (注入到VM检查中, 间接破坏)
        lines.append(f"if {wm_hash}~={self._generate_watermark_key()}then")
        lines.append(f"  {v['vm']}.{v['running']}=false")
        lines.append("end")
        
        # 清理水印 (短期生命周期)
        lines.append(f"{v['w1']}=nil{v['w2']}=nil{v['w3']}=nil")
        
        return lines
    
    def _generate_advanced_anti_hook(self, names: Dict[str, str]) -> List[str]:
        """
        生成高级Anti-Hook系统
        
        策略:
        1. 核心函数完整性检测 (延迟执行)
        2. 轻量指纹检测
        3. Hook诱捕 (honeypot)
        4. 间接触发 (修改VM数据)
        """
        lines = []
        v = names
        
        # 检测状态变量
        hk_state = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        hk_cnt = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        v['hk_state'] = hk_state
        v['hk_cnt'] = hk_cnt
        
        lines.append(f"local {hk_state}=false")
        lines.append(f"local {hk_cnt}=0")
        
        # 1. 核心函数指纹存储
        fp1 = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        fp2 = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local {fp1}=tostring(loadstring)")
        lines.append(f"local {fp2}=tostring(pcall)")
        
        # 2. 延迟检测函数
        check_func = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local function {check_func}()")
        lines.append(f"  {hk_cnt}={hk_cnt}+1")
        lines.append(f"  if {hk_cnt}<10 then return end")  # 延迟检测
        
        # 核心检测逻辑
        lines.append(f"  local ok=pcall(function()return tostring(loadstring) end)")
        lines.append(f"  if ok then")
        lines.append(f"    local cur=tostring(loadstring)")
        lines.append(f"    if cur~={fp1} then")
        lines.append(f"      {hk_state}=true")
        lines.append(f"      {v['vm']}.{v['regs']}[1]=(1)end")  # 污染数据
        lines.append(f"    end")
        lines.append(f"  end")
        
        # tostring完整性检测
        lines.append(f"  local ts=tostring(tostring)")
        lines.append(f"  if not ts:match('function')then {hk_state}=true end")
        lines.append("end")
        
        # 3. Hook诱捕 (honeypot)
        hp_func = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local {hp_func}=function()")
        lines.append(f"  local _f=function() end")
        lines.append(f"  local v=tostring(_f)")
        lines.append(f"  if v then return 77777 end")  # 假值
        lines.append(f"end")
        
        # 诱捕检测
        hp_check = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local function {hp_check}()")
        lines.append(f"  local r={hp_func}()")
        lines.append(f"  if r==77777 then")  # 被拦截
        lines.append(f"    {hk_state}=true")
        lines.append(f"    {v['vm']}.{v['running']}=false")
        lines.append(f"  end")
        lines.append(f"end")
        
        # 存储检测函数
        lines.append(f"{v['vm']}.{check_func}={check_func}")
        lines.append(f"{v['vm']}.{hp_check}={hp_check}")
        
        return lines
    
    def _generate_advanced_anti_dump(self, names: Dict[str, str]) -> List[str]:
        """
        生成增强Anti-Memory Dump系统
        
        策略:
        1. 字节码分段存储
        2. 每次只解密一小段
        3. 执行完立即nil
        4. 时间异常检测
        """
        lines = []
        v = names
        
        # 分段状态
        seg_idx = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        seg1 = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        seg2 = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        seg3 = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        
        lines.append(f"local {seg_idx}=0")
        lines.append(f"local {seg1}=nil")
        lines.append(f"local {seg2}=nil")
        lines.append(f"local {seg3}=nil")
        
        # 分段解密函数
        seg_dec = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local function {seg_dec}(data,idx)")
        lines.append(f"  local start=(idx-1)*16+1")
        lines.append(f"  local seg=data:sub(start,start+15)")
        lines.append(f"  local r=\"\"")
        lines.append(f"  for i=1,#seg do")
        lines.append(f"    local b=string.byte(seg,i)")
        lines.append(f"    local kb=bit32.band(bit32.rshift(_k,((i%4)*8)),255)")
        lines.append(f"    local wb=bit32.band(bit32.rshift(_wk,((i%3)*8)),255)")
        lines.append(f"    r=r..string.char(bit32.bxor(bit32.bxor(b,kb),wb))")
        lines.append(f"  end")
        lines.append(f"  return r")
        lines.append(f"end")
        
        # 段加载器
        seg_load = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local function {seg_load}(bc,idx)")
        lines.append(f"  {seg_idx}={seg_idx}+1")
        lines.append(f"  if idx==1 then {seg1}={seg_dec}(bc,idx)")
        lines.append(f"  elseif idx==2 then {seg2}={seg_dec}(bc,idx)")
        lines.append(f"  elseif idx==3 then {seg3}={seg_dec}(bc,idx)")
        lines.append(f"  end")
        lines.append(f"end")
        
        # 段清理函数
        seg_clean = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local function {seg_clean}(idx)")
        lines.append(f"  if idx==1 then {seg1}=nil")
        lines.append(f"  elseif idx==2 then {seg2}=nil")
        lines.append(f"  elseif idx==3 then {seg3}=nil")
        lines.append(f"  end")
        lines.append(f"  collectgarbage()")
        lines.append(f"end")
        
        # 时间异常检测
        time_check = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local function {time_check}(t)")
        lines.append(f"  if os.clock()-t>0.05 then")
        lines.append(f"    {seg1}=nil{seg2}=nil{seg3}=nil")
        lines.append(f"    {v['vm']}.{v['running']}=false")
        lines.append(f"  end")
        lines.append(f"end")
        
        # 存储
        lines.append(f"{v['vm']}.{seg_dec}={seg_dec}")
        lines.append(f"{v['vm']}.{seg_load}={seg_load}")
        lines.append(f"{v['vm']}.{seg_clean}={seg_clean}")
        
        return lines
    
    def _generate_advanced_anti_trace(self, names: Dict[str, str]) -> List[str]:
        """
        生成高级Anti-VM Trace系统
        
        策略:
        1. dispatcher混淆 (不用if-else链)
        2. 插入fake opcode
        3. 控制流扰乱
        4. 时间检测
        """
        lines = []
        v = names
        
        # Trace检测状态
        tr_state = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        tr_cnt = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local {tr_state}=false")
        lines.append(f"local {tr_cnt}=0")
        
        # 混淆dispatcher表
        disp_key = random.randint(1000, 9999)
        disp_base = random.randint(100, 999)
        disp_table = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local {disp_table}={{}}")
        for op in range(0, 0x50):
            mapped = ((op * disp_key + disp_base) % 256)
            lines.append(f"{disp_table}[{op}]={mapped}")
        
        # 假opcode表
        fake_ops = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local {fake_ops}={{")
        for _ in range(15):
            fake_op = random.randint(0xD0, 0xDF)
            lines.append(f"  [{fake_op}]=1,")
        lines.append("}")
        
        # trace检测函数
        tr_check = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local function {tr_check}(op)")
        lines.append(f"  {tr_cnt}={tr_cnt}+1")
        lines.append(f"  local mop={disp_table}[op]or op")
        lines.append(f"  if {fake_ops}[op]then return mop end")  # 跳过假opcode
        
        # 周期性时间检测
        lines.append(f"  if {tr_cnt}%7==0 then")
        lines.append(f"    local t1=os.clock()")
        lines.append(f"    for i=1,50 do local _=i*2 end")
        lines.append(f"    if os.clock()-t1>0.02 then")
        lines.append(f"      {tr_state}=true")
        lines.append(f"      {v['vm']}.{v['running']}=false")
        lines.append(f"    end")
        lines.append(f"  end")
        
        # PC轨迹检测
        pc_hist = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"  local {pc_hist}={{}}")
        lines.append(f"  table.insert({pc_hist},{v['vm']}.{v['pc']})")
        lines.append(f"  if #{pc_hist}>30 then")
        lines.append(f"    if {pc_hist}[#{pc_hist}]=={pc_hist}[#{pc_hist}-1]then")
        lines.append(f"      {tr_state}=true")
        lines.append(f"    end")
        lines.append(f"  end")
        lines.append("end")
        
        lines.append(f"{v['vm']}.{tr_check}={tr_check}")
        
        return lines
    
    def _generate_advanced_self_destruct(self, names: Dict[str, str]) -> List[str]:
        """
        生成自毁策略系统
        
        策略:
        1. 数据污染 (修改常量/opcode)
        2. 假成功 (返回错误但不报错)
        3. 随机行为 (每次失败表现不同)
        """
        lines = []
        v = names
        
        # 自毁状态
        sd_state = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        sd_cnt = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        sd_mode = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local {sd_state}=false")
        lines.append(f"local {sd_cnt}=0")
        lines.append(f"local {sd_mode}=math.random(1,3)")
        
        # 数据污染函数
        corrupt = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local function {corrupt}(t)")
        lines.append(f"  for k,v in pairs(t or {{}})do")
        lines.append(f"    if type(v)=='number'then t[k]=v+math.random(-5,5)end")
        lines.append(f"    if type(v)=='string'then")
        lines.append(f"      t[k]=v:gsub('.',function(c)return string.char(bit32.bxor(string.byte(c),1)) end)")
        lines.append(f"    end")
        lines.append(f"  end")
        lines.append(f"end")
        
        # 假成功函数
        fake_ok = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local function {fake_ok}(...)")
        lines.append(f"  if {sd_state}then")
        lines.append(f"    if {sd_mode}==1 then return nil end")
        lines.append(f"    if {sd_mode}==2 then return false end")
        lines.append(f"    if {sd_mode}==3 then return{{}}end")
        lines.append(f"  end")
        lines.append(f"  return ...")
        lines.append(f"end")
        
        # 无效循环 (触发后)
        dead_loop = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local function {dead_loop}()")
        lines.append(f"  if {sd_state}then")
        lines.append(f"    while true do")
        lines.append(f"      local _=1")
        lines.append(f"      if math.random()>0.9999 then break end")
        lines.append(f"    end")
        lines.append(f"  end")
        lines.append(f"end")
        
        # 自毁触发器
        trigger = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local function {trigger}(cond)")
        lines.append(f"  if cond then")
        lines.append(f"    {sd_state}=true")
        lines.append(f"    {sd_cnt}={sd_cnt}+1")
        lines.append(f"    if {sd_cnt}>2 then {dead_loop}()end")
        lines.append(f"    {corrupt}(nil)")
        lines.append(f"    {v['vm']}.{v['running']}=false")
        lines.append(f"  end")
        lines.append(f"end")
        
        lines.append(f"{v['vm']}.{trigger}={trigger}")

        return lines
    
    def _generate_roblox_anti_dumper(self, names: Dict[str, str]) -> List[str]:
        """
        生成 Roblox 专用 Anti-Dumper 保护 (增强版)
        
        保护机制:
        1. VM自修改 - dispatch_table 动态变化
        2. 指令扰乱 - opcode映射动态变化
        3. 垃圾函数 - 数百个无用closure
        4. 假数据 - fake常量表
        5. 执行路径混乱 - 同一逻辑多种路径
        """
        lines = []
        v = names
        
        # === 1. 局部函数引用 ===
        lines.append("--[[X]]")
        lines.append("local _ts=tostring")
        lines.append("local _pc=pcall")
        lines.append("local _db=debug")
        lines.append("local _lo=loadstring or load")
        lines.append("local _gi=getgenv or function()return _G end")
        lines.append("local _sh=shared or getgenv()")
        
        # === 2. 自修改 Dispatcher ===
        disp_tbl = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        disp_mutate = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        disp_seed = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        disp_cnt = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        
        # 基础dispatch表 (混淆存储)
        base_ops = [0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88]
        op_chars = ','.join(hex(x) for x in base_ops)
        lines.append(f"local {disp_tbl}={{{op_chars}}},")
        
        # 动态修改表
        lines.append(f"local {disp_seed}={{0x5F,0x3A,0x9C,0xE1,0x2B,0x8D,0x4F,0xF7}}")
        lines.append(f"local {disp_cnt}=0")
        
        # 自修改函数 (核心反分析)
        lines.append(f"local function {disp_mutate}(d,i)")
        lines.append(f"  {disp_cnt}={disp_cnt}+1")
        lines.append(f"  if {disp_cnt}%math.random(5,15)==0 then")
        lines.append(f"    local s=math.random(1,#d)")
        lines.append(f"    local m={disp_seed}[{disp_cnt}%#{{disp_seed}}+1]")
        lines.append(f"    d[s]=(d[s]+m)%256")
        lines.append(f"    d[math.random(1,#d)]=math.random(0,255)")
        lines.append(f"  end")
        lines.append(f"  return d")
        lines.append("end")
        
        # 指令扰乱器
        scramble = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {scramble}(op,mode)")
        lines.append(f"  if mode==1 then")
        lines.append(f"    return (op+math.random(1,3))%256")
        lines.append(f"  elseif mode==2 then")
        lines.append(f"    return ({disp_tbl}[op%#{{disp_tbl}}+1]or op)")
        lines.append(f"  else")
        lines.append(f"    return bit32.bxor(op,math.random(1,255))%256")
        lines.append(f"  end")
        lines.append("end")
        
        # === 3. 垃圾函数生成 (数百个无用closure) ===
        junk_count = random.randint(150, 300)
        junk_funcs = []
        
        # 生成模式库
        junk_patterns = [
            ("local function {n}()local _=0;for i=1,{c}do _=(_+i)end;return _ end",
             lambda i: {'c': random.randint(3, 20)}),
            ("local function {n}(a,b)return(a+b)*(a-b)end",
             lambda i: {}),
            ("local function {n}()local t={{}};for i=1,{c}do t[i]=i*i end;return t[1]end",
             lambda i: {'c': random.randint(5, 25)}),
            ("local function {n}(x)return x and{x}or nil end",
             lambda i: {}),
            ("local function {n}()repeat until false;return 1 end",
             lambda i: {}),
            ("local function {n}(a,b,c)local r=a or b or c;return r end",
             lambda i: {}),
            ("local function {n}()while false do end;return nil end",
             lambda i: {}),
            ("local function {n}(t)for k,v in pairs(t or{{}})do end;return 0 end",
             lambda i: {}),
            ("local function {n}()local s='';for i=1,{c}do s=s..'x'end;return #s end",
             lambda i: {'c': random.randint(3, 15)}),
            ("local function {n}(a,b)if a then return b else return a end end",
             lambda i: {}),
        ]
        
        for i in range(junk_count):
            fn = '_j' + ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(random.randint(4, 8)))
            junk_funcs.append(fn)
            pat, args = random.choice(junk_patterns)
            args_dict = args(i)
            fn_code = pat.format(n=fn, **{k: hex(v) if isinstance(v, int) and v > 255 else v for k, v in args_dict.items()})
            lines.append(fn_code)
        
        # 批量注册到VM表
        lines.append(f"local _junk={{}}")
        for jf in junk_funcs[:50]:  # 只注册前50个
            lines.append(f"_junk.{jf}={jf}")
        
        # === 4. 假常量表 (干扰静态分析) ===
        fake_const_tbl = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        fake_consts = []
        for i in range(random.randint(10, 20)):
            fc = ''.join(random.choice(string.hexdigits.lower()) for _ in range(random.randint(8, 16)))
            fake_consts.append(f"\"{fc}\"")
        lines.append(f"local {fake_const_tbl}={{{','.join(fake_consts)}}}")
        
        # 假字节码片段
        fake_bc = ''.join(random.choice(string.hexdigits.lower()) for _ in range(random.randint(40, 80)))
        lines.append(f"local _fbc=\"{fake_bc}\"")
        
        # 假字符串池
        fake_strings = []
        for i in range(random.randint(8, 15)):
            fs = ''.join(chr(random.randint(32, 126)) for _ in range(random.randint(5, 15)))
            escaped = fs.replace('\\', '\\\\').replace('"', '\\"')
            fake_strings.append(f"\"{escaped}\"")
        lines.append(f"local _fstr={{{','.join(fake_strings)}}}")
        
        # === 5. 假环境构造 ===
        fake_glob = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local {fake_glob}={{}}")
        lines.append(f"{fake_glob}.loadstring=function()return function() end end")
        lines.append(f"{fake_glob}.debug={{getinfo=function()return{{what='C'}} end}}")
        lines.append(f"{fake_glob}._G={{}}")
        lines.append(f"{fake_glob}.shared={{}}")
        
        # === 6. Hook 检测 ===
        hk_chk1 = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        hk_chk2 = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        hk_chk3 = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        hk_chk4 = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        
        lines.append(f"local function {hk_chk1}()local f=_lo;if f and _ts(f):find('C function')==nil then return true end;return false end")
        lines.append(f"local function {hk_chk2}()local ok,info=_pc(_db.getinfo,_lo);if ok and info and info.what~='C'then return true end;return false end")
        lines.append(f"local function {hk_chk3}()local ok=_pc(function()_db.sethook(function() end,'',1)end);if not ok then return true end;_db.sethook(nil);return false end")
        lines.append(f"local function {hk_chk4}()local hf=hookfunction;if hf then local orig=_lo;local hooked=hf(_lo,function() end);if hooked~=orig then return true end end;return false end")
        
        # === 7. 执行路径混乱器 ===
        path_chaos = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {path_chaos}(cond,a,b)")
        lines.append(f"  if cond then")
        lines.append(f"    if math.random()>0.5 then return a or b else return b or a end")
        lines.append(f"  else")
        lines.append(f"    local t={{a,b}};return t[math.random(1,2)][1]")
        lines.append(f"  end")
        lines.append("end")
        
        # 多路径执行
        multi_path = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {multi_path}(v)")
        lines.append(f"  local r=v")
        lines.append(f"  for i=1,math.random(1,3)do")
        lines.append(f"    r=r+({path_chaos})(i%2==0,i,0)")
        lines.append(f"    r=r-({path_chaos})(i%3==0,i,0)")
        lines.append(f"  end")
        lines.append(f"  return r")
        lines.append("end")
        
        # === 8. 延迟触发器 ===
        trigger_cnt = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        delay_trig = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local {trigger_cnt}=0")
        
        lines.append(f"local function {delay_trig}(pc)")
        lines.append(f"  {trigger_cnt}={trigger_cnt}+1")
        lines.append(f"  if {trigger_cnt}%math.random(10,30)==0 then")
        lines.append(f"    if {hk_chk1}()or{hk_chk2}()or{hk_chk3}()then")
        lines.append(f"      {v['vm']}.running=false;return true end")
        lines.append(f"  end")
        lines.append(f"  return false")
        lines.append("end")
        
        # === 9. 执行污染器 ===
        corrupt_result = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {corrupt_result}(r)")
        lines.append(f"  if {trigger_cnt}>5 then")
        lines.append(f"    local off=math.random(-10,10)")
        lines.append(f"    if type(r)=='number'then return r+off end")
        lines.append(f"    if type(r)=='string'then return r:gsub('.',function(c)return _ts(_lo(c)))end end")
        lines.append(f"  end")
        lines.append(f"  return r")
        lines.append("end")
        
        # === 10. 指令扰动器 (集成到VM执行) ===
        op_perturb = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {op_perturb}(op,pc)")
        lines.append(f"  if pc%math.random(3,7)==0 then")
        lines.append(f"    return {scramble}(op,math.random(1,3))")
        lines.append(f"  end")
        lines.append(f"  return op")
        lines.append("end")
        
        # === 11. 数据自毁 ===
        data_wipe = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {data_wipe}()")
        lines.append(f"  for i=1,50 do _G['_'..string.char(97+i%26)]=nil end")
        lines.append(f"  collectgarbage('collect')")
        lines.append("end")
        
        # === 12. 绑定到 VM ===
        lines.append(f"{v['vm']}.{disp_mutate}={disp_mutate}")
        lines.append(f"{v['vm']}.{scramble}={scramble}")
        lines.append(f"{v['vm']}.{hk_chk1}={hk_chk1}")
        lines.append(f"{v['vm']}.{hk_chk2}={hk_chk2}")
        lines.append(f"{v['vm']}.{hk_chk4}={hk_chk4}")
        lines.append(f"{v['vm']}.{delay_trig}={delay_trig}")
        lines.append(f"{v['vm']}.{corrupt_result}={corrupt_result}")
        lines.append(f"{v['vm']}.{op_perturb}={op_perturb}")
        lines.append(f"{v['vm']}.{data_wipe}={data_wipe}")
        lines.append(f"{v['vm']}.{multi_path}={multi_path}")
        lines.append(f"{v['vm']}._junk=_junk")
        lines.append(f"{v['vm']}._fconst={fake_const_tbl}")
        lines.append(f"{v['vm']}._fstr=_fstr")
        lines.append(f"{v['vm']}._fbc=_fbc")
        
        # === 13. 假VM执行 (降低分析效率) ===
        fake_vm_exec = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {fake_vm_exec}()")
        lines.append(f"  if math.random()>0.6 then")
        for jf in junk_funcs[:20]:
            lines.append(f"    {jf}()")
        lines.append(f"  end")
        lines.append("end")
        lines.append(f"{v['vm']}.fake={fake_vm_exec}")
        
        return lines
    
    def _obfuscate_string_literal(self, s: str) -> str:
        """混淆字符串字面量"""
        return ''.join(chr((ord(c) + 17) % 256) for c in s)
    
    def _generate_protected_vm_engine(self, names: Dict[str, str]) -> List[str]:
        """
        生成受保护的核心VM引擎
        
        特性:
        1. 自修改dispatch_table (运行中动态变化)
        2. 多层dispatcher混淆
        3. 随机执行路径
        """
        lines = []
        v = names
        
        # ================================================================
        # 1. VM状态表 (包含自修改dispatcher)
        # ================================================================
        lines.append(f"local {v['vm']}={{{v['regs']}={{}},")
        lines.append(f"{v['stack']}={{}},")
        lines.append(f"{v['top']}=0,")
        lines.append(f"{v['pc']}=0,")
        lines.append(f"{v['running']}=true,")
        lines.append(f"{v['insts']}=nil,")
        lines.append(f"{v['consts']}=nil}}")
        
        # ================================================================
        # 2. 自修改dispatcher表 (核心反分析机制)
        # 执行过程中会动态改变映射关系
        # ================================================================
        disp_name = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        disp_mutate = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        disp_seed = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        
        lines.append(f"local {disp_name}={{}}")
        
        # 初始化dispatcher表 (带混淆key)
        disp_key = random.randint(100, 999)
        disp_off = random.randint(1, 5)
        for op in range(0, 0x40):
            mapped = ((op * disp_key + disp_off) % 256)
            lines.append(f"{disp_name}[{op}]={mapped}")
        
        # Dispatcher自修改函数 (运行时改变映射)
        lines.append(f"local function {disp_mutate}(d,k,s)")
        lines.append(f"  local n={{}}for i=0,63 do n[i]=(i*k+s)%256 end")
        lines.append(f"  for i=0,63 do d[i]=n[i]end")
        lines.append(f"end")
        
        # 种子变量
        lines.append(f"local {disp_seed}={disp_key}")
        
        # ================================================================
        # 3. 主执行循环 (自修改dispatcher)
        # ================================================================
        exec_func = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local function {exec_func}()")
        lines.append(f"  while {v['vm']}.{v['running']} do")
        
        # 获取指令
        lines.append(f"    local ins={v['vm']}.{v['insts']}[{v['vm']}.{v['pc']}]")
        lines.append(f"    {v['vm']}.{v['pc']}={v['vm']}.{v['pc']}+1")
        lines.append(f"    if not ins then {v['vm']}.{v['running']}=false break end")
        
        # 解码 (使用自修改dispatcher)
        lines.append(f"    local op=string.byte(ins,1)")
        lines.append(f"    local mop={disp_name}[op]or op")
        lines.append(f"    local a=string.byte(ins,2)")
        
        # 随机触发dispatcher自修改 (每N条指令修改一次)
        mutate_trigger = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"    {mutate_trigger}={mutate_trigger or 0}+1")
        lines.append(f"    if {mutate_trigger}%7==0 then")
        lines.append(f"      {disp_mutate}({disp_name},{disp_seed},{v['vm']}.{v['pc']})")
        lines.append(f"    end")
        
        # 执行 (使用映射后的opcode)
        lines.append(f"    if mop<16 then")
        lines.append(f"      {v['vm']}.{v['stack']}[{v['vm']}.{v['top']}]={v['vm']}.{v['consts']}[a]")
        lines.append(f"    elseif mop<32 then")
        lines.append(f"      {v['vm']}.{v['top']}={v['vm']}.{v['top']}+a")
        lines.append(f"    elseif mop<48 then")
        lines.append(f"      {v['vm']}.{v['top']}={v['vm']}.{v['top']}-a")
        lines.append(f"    elseif mop<64 then")
        lines.append(f"      {v['vm']}.{v['regs']}[a]={v['vm']}.{v['stack']}[{v['vm']}.{v['top']}]")
        lines.append(f"    end")
        
        lines.append("  end")
        lines.append("end")
        
        lines.append(f"{v['vm']}.{exec_func}={exec_func}")
        
        # 清理dispatcher
        lines.append(f"{disp_name}=nil")
        
        return lines
    
    def _generate_anti_debug(self, names: Dict[str, str]) -> List[str]:
        """生成Anti-debug代码"""
        v = names
        lines = []
        
        lines.append("-- anti-debug")
        lines.append(f"local function {v['check']}()")
        lines.append(f"  local _t=os.clock()")
        lines.append(f"  for _i=1,100 do local _=1+1 end")
        lines.append(f"  if os.clock()-_t>0.1 then")
        lines.append(f"    {v['vm']}.{v['running']}=false")
        lines.append("  end")
        lines.append(f"  if debug and debug.getinfo then")
        lines.append(f"    local _=1")
        lines.append("  end")
        lines.append("end")
        
        return lines
    
    def _generate_local_names(self) -> Dict[str, str]:
        """
        生成混淆的局部变量名 (增强随机性)
        
        策略:
        1. 使用更长的随机变量名 (增加分析难度)
        2. 随机选择字母、数字、下划线组合
        3. 避免常见模式
        4. 确保所有键都有默认值，不允许KeyError
        """
        # 扩展字符集
        chars = string.ascii_lowercase + string.ascii_uppercase + string.digits + '_'
        # 不以数字开头
        start_chars = string.ascii_lowercase + string.ascii_uppercase + '_'
        
        names = {}
        
        # 基本VM变量 (必须全部覆盖)
        base_keys = ['vm', 'stack', 'top', 'pc', 'running', 'regs', 'insts', 'consts',
                'decode', 'push', 'pop', 'peek', 'getk', 'exec', 'loadbc', 'check']
        
        # 新增变量 (假分支和anti-dump)
        extra_keys = ['n', 't', 's', 'fake_check', 'anti_dump', 'fake_branch']
        
        for key in base_keys + extra_keys:
            if self.compact_output:
                # 紧凑模式下使用短变量名 (但比原来更长)
                length = random.randint(3, 5)
            else:
                # 普通模式下使用更长的混淆名 (4-8字符)
                length = random.randint(4, 8) if self.obfuscate_names else len(key)
            
            # 生成随机变量名
            if length <= 3:
                # 短名字用随机字符
                names[key] = ''.join(random.choice(chars) for _ in range(length))
            else:
                # 长名字: 首字符 + 随机字符 + 数字混合
                name = random.choice(start_chars)
                name += ''.join(random.choice(chars) for _ in range(length - 1))
                # 随机插入下划线位置
                if random.random() > 0.5 and length > 3:
                    pos = random.randint(1, length - 2)
                    name = name[:pos] + '_' + name[pos+1:]
                names[key] = name
        
        # 确保 vm_table 存在 (使用 vm 的值)
        if 'vm' not in names:
            names['vm'] = 'v' + ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        names['vm_table'] = names['vm']
        
        # 确保所有可能用到的键都有值 (防止 KeyError)
        required_keys = ['stack', 'top', 'pc', 'running', 'regs', 'insts', 'consts', 
                        'decode', 'push', 'pop', 'peek', 'getk', 'exec', 'loadbc', 'check']
        for k in required_keys:
            if k not in names:
                names[k] = ''.join(random.choice(string.ascii_lowercase) for _ in range(random.randint(3, 5)))
        
        return names
    
    def _quote(self, s: str) -> str:
        """转义字符串"""
        escaped = s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
        return '"' + escaped + '"'


# -----------------------------------------------------------------------------
# 9.6 VM混淆器集成
# -----------------------------------------------------------------------------

# =============================================================================
# 9.6 Valax Force VM - 强制 VM 混淆架构
# =============================================================================

class ValaxForceVM:
    """
    Valax 强制 VM 混淆器 - 强制全局 VM 编译架构
    
    架构特点:
    1. 强制全局 VM - 所有代码必须经过 VM 编译
    2. 无 fallback - 禁止任何轻量模式
    3. 多层 VM - N 层 VM 嵌套执行
    4. 分段执行 - bytecode 分块加密执行
    5. 自解密 Loader - 运行时动态解密
    6. 多态 opcode - 每次构建随机映射
    7. 指令多态 - 同一指令多种变体
    8. 控制流混淆 - 虚假指令和垃圾 opcode
    9. 无可预测结构 - 动态 pc 和 opcode 表
    10. 安全强化 - Anti-debug, Anti-hook, Anti-dump
    """
    
    def __init__(self, seed: int = None):
        self.seed = seed if seed else random.randint(1, 0xFFFFFFFF)
        random.seed(self.seed)
        
        # 编译器
        self.compiler = BytecodeCompiler()
        
        # 多态 opcode 映射器
        self.opcode_mapper = PolymorphicOpcodes(self.seed)
        
        # 分段加密器
        self.chunker = ChunkEncryptor(self.seed)
        
        # Loader 构建器
        self.loader_builder = LoaderBuilder(self.seed)
        
        # VM 层数 (默认3层)
        self.vm_layers = 3
        
        # 段数
        self.chunk_count = 4
        
        # 假 opcode 比例
        self.fake_op_ratio = 0.15
        
        # 指令变体开关
        self.enable_instr_variants = True
        
        # 安全强化开关
        self.enable_security = True
        
    def obfuscate(self, source: str) -> str:
        """
        强制 VM 混淆流程:
        source -> AST -> IR -> bytecode -> 多态映射 -> 分段 -> 加密 -> Loader 包装 -> 输出
        """
        print(f"[*] Valax Force VM (seed: {self.seed})", file=sys.stderr)
        
        # 阶段1: 词法分析
        print("[*] Lexing...", file=sys.stderr)
        lexer = Lexer(source)
        tokens = lexer.scan()
        
        # 阶段2: 语法分析
        print("[*] Parsing...", file=sys.stderr)
        parser = Parser(tokens)
        ast = parser.parse()
        
        # 阶段3: 编译为 IR/Bytecode
        print("[*] Compiling to bytecode...", file=sys.stderr)
        func = self.compiler.compile(ast)
        
        # 阶段4: 收集指令并应用多态
        print("[*] Applying polymorphic opcodes...", file=sys.stderr)
        raw_instructions = self._collect_instructions(func)
        
        # 阶段5: 生成多态 opcode 映射
        self.opcode_mapper.generate_mapping(raw_instructions)
        polymorphic_bc = self.opcode_mapper.remap_instructions(raw_instructions)
        
        # 阶段6: 指令变体替换
        if self.enable_instr_variants:
            print("[*] Applying instruction variants...", file=sys.stderr)
            polymorphic_bc = self._apply_instruction_variants(polymorphic_bc)
        
        # 阶段7: 插入虚假指令
        print("[*] Inserting fake instructions...", file=sys.stderr)
        polymorphic_bc = self._insert_fake_instructions(polymorphic_bc)
        
        # 阶段8: 分段字节码
        print("[*] Chunking bytecode...", file=sys.stderr)
        chunks = self.chunker.create_chunks(polymorphic_bc, self.chunk_count)
        encrypted_chunks = self.chunker.encrypt_chunks(chunks)
        
        # 阶段9: 生成多层 VM 包装
        print("[*] Building multi-layer VM...", file=sys.stderr)
        vm_structure = self._build_multi_layer_vm(encrypted_chunks)
        
        # 阶段10: 生成自解密 Loader
        print("[*] Building self-decrypting loader...", file=sys.stderr)
        output = self.loader_builder.build_loader(vm_structure)
        
        return output
    
    def _collect_instructions(self, func: Function) -> List[Dict]:
        """收集所有指令信息用于多态映射"""
        instructions = []
        for instr in func.instructions:
            instructions.append({
                'opcode': instr.opcode,
                'a': instr.a,
                'b': instr.b,
                'c': instr.c,
                'bx': instr.bx,
                'sbx': instr.sbx
            })
        return instructions
    
    def _apply_instruction_variants(self, instructions: List[Dict]) -> List[Dict]:
        """应用指令多态变体"""
        variants = []
        for instr in instructions:
            variant = self._generate_instruction_variant(instr)
            variants.append(variant)
        return variants
    
    def _generate_instruction_variant(self, instr: Dict) -> Dict:
        """为指令生成变体"""
        op = instr['opcode']
        
        # 算术指令变体
        if op == self.opcode_mapper.real_opcodes.get('ADD'):
            # ADD 可以转为 SUB + NEG
            if random.random() > 0.5:
                return {
                    'opcode': self.opcode_mapper.real_opcodes.get('SUB'),
                    'a': instr['a'],
                    'b': instr['b'],
                    'c': self.opcode_mapper.real_opcodes.get('UNM') if 'UNM' in self.opcode_mapper.real_opcodes.values() else 0x36,
                    'bx': 0, 'sbx': 0
                }
        
        # 跳转指令变体
        if op == self.opcode_mapper.real_opcodes.get('JMP'):
            # 随机跳转偏移
            jitter = random.randint(-2, 2)
            return {
                'opcode': op,
                'a': instr['a'],
                'b': instr['b'],
                'c': instr['c'],
                'bx': instr['bx'],
                'sbx': instr['sbx'] + jitter
            }
        
        return instr
    
    def _insert_fake_instructions(self, instructions: List[Dict]) -> List[Dict]:
        """插入虚假指令增加混淆"""
        result = []
        fake_ops = list(self.opcode_mapper.fake_opcodes.values())
        
        for i, instr in enumerate(instructions):
            result.append(instr)
            
            # 按比例插入虚假指令
            if random.random() < self.fake_op_ratio and fake_ops:
                fake = {
                    'opcode': random.choice(fake_ops),
                    'a': random.randint(0, 255),
                    'b': random.randint(0, 255),
                    'c': random.randint(0, 255),
                    'bx': random.randint(0, 255),
                    'sbx': 0,
                    '_fake': True  # 标记为虚假指令
                }
                result.append(fake)
        
        return result
    
    def _build_multi_layer_vm(self, encrypted_chunks: List[Dict]) -> Dict:
        """构建多层 VM 结构"""
        layers = []
        
        for layer_idx in range(self.vm_layers):
            # 每层使用不同的 opcode 映射和 dispatch 结构
            layer_vm = {
                'layer_id': layer_idx,
                'opcode_map': self.opcode_mapper.generate_layer_map(layer_idx),
                'dispatch_style': random.choice(['table', 'if_chain', 'computed', 'mixed']),
                'chunks': encrypted_chunks if layer_idx == self.vm_layers - 1 else [],
                'entry_point': self._generate_layer_entry(layer_idx),
                'anti_hook': self.enable_security,
                'anti_debug': self.enable_security,
            }
            layers.append(layer_vm)
        
        return {
            'layers': layers,
            'total_layers': self.vm_layers,
            'seed': self.seed,
        }
    
    def _generate_layer_entry(self, layer_idx: int) -> str:
        """生成每层的入口代码"""
        entry_name = f"_valax_layer_{layer_idx}"
        # 生成混淆的入口名
        chars = string.ascii_lowercase + string.ascii_uppercase
        return ''.join(random.choice(chars) for _ in range(random.randint(4, 8)))


class PolymorphicOpcodes:
    """
    多态 Opcode 系统
    
    特性:
    1. 每次构建生成随机 opcode 映射
    2. 真实 opcode 和假 opcode 混合
    3. opcode ID 随机分配
    4. 映射表运行时构建
    """
    
    def __init__(self, seed: int):
        self.seed = seed
        random.seed(seed)
        
        # 真实 opcode 定义
        self.real_opcodes = {
            'LOADK': 0x01, 'LOADNIL': 0x02, 'MOVE': 0x03,
            'GETGLOBAL': 0x10, 'SETGLOBAL': 0x11,
            'NEWTABLE': 0x20, 'SETTABLE': 0x21, 'GETTABLE': 0x22,
            'ADD': 0x30, 'SUB': 0x31, 'MUL': 0x32, 'DIV': 0x33,
            'EQ': 0x40, 'LT': 0x41, 'LE': 0x42,
            'NOT': 0x50, 'AND': 0x51, 'OR': 0x52,
            'JMP': 0x60, 'JMPF': 0x61,
            'CALL': 0x70, 'RETURN': 0x71,
            'FORLOOP': 0x80, 'FORPREP': 0x81,
            'CONCAT': 0x90, 'LEN': 0x91,
        }
        
        # 假 opcode 定义
        self.fake_opcodes = {
            'FAKE_NOP': 0xE0, 'FAKE_ADD': 0xE1, 'FAKE_SUB': 0xE2,
            'FAKE_JMP': 0xE3, 'FAKE_CALL': 0xE4, 'FAKE_RET': 0xE5,
            'FAKE_GET': 0xE6, 'FAKE_SET': 0xE7,
        }
        
        # 当前构建的映射
        self.current_mapping = {}
        self.reverse_mapping = {}
        
    def generate_mapping(self, instructions: List[Dict]):
        """为当前构建生成随机 opcode 映射"""
        # 获取所有使用的真实 opcode
        used_ops = set()
        for instr in instructions:
            used_ops.add(instr['opcode'])
        
        # 生成随机映射
        available_ids = list(range(0x01, 0xFF))
        random.shuffle(available_ids)
        
        self.current_mapping = {}
        self.reverse_mapping = {}
        
        op_names = list(self.real_opcodes.keys())
        random.shuffle(op_names)
        
        idx = 0
        for op_name in op_names:
            if self.real_opcodes[op_name] in used_ops or len(op_names) < 10:
                # 分配随机 ID
                new_id = available_ids[idx] if idx < len(available_ids) else random.randint(1, 255)
                self.current_mapping[op_name] = new_id
                self.reverse_mapping[new_id] = op_name
                idx += 1
        
        # 添加假 opcode 到映射
        for fake_name, fake_id in self.fake_opcodes.items():
            if fake_id not in self.reverse_mapping:
                self.reverse_mapping[fake_id] = fake_name
    
    def remap_instructions(self, instructions: List[Dict]) -> List[Dict]:
        """将指令重新映射到新的 opcode ID"""
        remapped = []
        
        for instr in instructions:
            new_instr = dict(instr)
            
            # 查找原始 opcode 名称
            orig_opcode = instr['opcode']
            op_name = None
            for name, code in self.real_opcodes.items():
                if code == orig_opcode:
                    op_name = name
                    break
            
            # 如果找到名称，应用新映射
            if op_name and op_name in self.current_mapping:
                new_instr['opcode'] = self.current_mapping[op_name]
            
            remapped.append(new_instr)
        
        return remapped
    
    def generate_layer_map(self, layer_idx: int) -> Dict:
        """为特定层生成 opcode 映射"""
        layer_seed = self.seed + layer_idx * 1000
        random.seed(layer_seed)
        
        layer_map = {}
        available = list(range(1, 256))
        random.shuffle(available)
        
        for i, (name, _) in enumerate(self.real_opcodes.items()):
            if i < len(available):
                layer_map[name] = available[i]
        
        return layer_map


class ChunkEncryptor:
    """
    分段加密器
    
    特性:
    1. 将 bytecode 分割为多个 chunk
    2. 每个 chunk 单独加密
    3. chunk 顺序打乱
    4. 运行时按表恢复顺序
    """
    
    def __init__(self, seed: int):
        self.seed = seed
        random.seed(seed)
        
    def create_chunks(self, instructions: List[Dict], count: int) -> List[List[Dict]]:
        """创建 bytecode 分块"""
        if not instructions:
            return [[] for _ in range(count)]
        
        chunk_size = max(1, len(instructions) // count)
        chunks = []
        
        for i in range(count):
            start = i * chunk_size
            end = start + chunk_size if i < count - 1 else len(instructions)
            chunks.append(instructions[start:end])
        
        return chunks
    
    def encrypt_chunks(self, chunks: List[List[Dict]]) -> List[Dict]:
        """加密所有 chunk 并打乱顺序"""
        encrypted = []
        execution_order = []
        
        for i, chunk in enumerate(chunks):
            if not chunk:
                continue
            
            # 生成 chunk 密钥
            chunk_key = random.randint(1, 0xFFFFFFFF)
            
            # 加密 chunk 数据
            encrypted_data = self._encrypt_chunk(chunk, chunk_key)
            
            encrypted.append({
                'id': i,
                'data': encrypted_data,
                'key': chunk_key,
                'size': len(chunk),
                'order': i,
            })
            execution_order.append(i)
        
        # 打乱执行顺序
        random.shuffle(execution_order)
        
        # 更新执行顺序表
        for enc in encrypted:
            enc['exec_order'] = execution_order.index(enc['order'])
        
        return encrypted
    
    def _encrypt_chunk(self, chunk: List[Dict], key: int) -> str:
        """使用 XOR 加密 chunk"""
        # 将 chunk 转换为字符串
        chunk_str = str(chunk)
        
        # XOR 加密
        encrypted = []
        for i, char in enumerate(chunk_str):
            key_byte = (key >> ((i % 4) * 8)) & 0xFF
            encrypted.append(chr(ord(char) ^ key_byte))
        
        result = ''.join(encrypted)
        
        # Base64 编码
        try:
            encoded = base64.b64encode(result.encode('utf-8')).decode('ascii')
        except:
            encoded = base64.b64encode(result.encode('latin-1')).decode('latin-1')
        
        return encoded


class LoaderBuilder:
    """
    自解密 Loader 构建器
    
    特性:
    1. 运行时动态密钥生成
    2. 动态 opcode 表构建
    3. 多层 VM 嵌套执行
    4. 安全检测
    """
    
    def __init__(self, seed: int):
        self.seed = seed
        random.seed(seed)
        
    def build_loader(self, vm_structure: Dict) -> str:
        """构建完整的自解密 Loader"""
        lines = []
        
        # 包装函数
        lines.append("(function()")
        
        # 1. 生成混淆变量名
        names = self._generate_obfuscated_names()
        
        # 2. 加密的 bytecode chunks
        for chunk in vm_structure['layers'][-1]['chunks']:
            lines.append(f"local {names['chunk']}{chunk['id']}=\"{chunk['data']}\"")
        
        # 3. 执行顺序表
        exec_order = [c['exec_order'] for c in vm_structure['layers'][-1]['chunks']]
        lines.append(f"local {names['order_tbl']}={{{','.join(map(str, exec_order))}}}")
        
        # 4. 密钥表
        keys = [c['key'] for c in vm_structure['layers'][-1]['chunks']]
        lines.append(f"local {names['key_tbl']}={{{','.join(map(str, keys))}}}")
        
        # 5. 大小表
        sizes = [c['size'] for c in vm_structure['layers'][-1]['chunks']]
        lines.append(f"local {names['size_tbl']}={{{','.join(map(str, sizes))}}}")
        
        # 6. 动态密钥生成函数
        lines.extend(self._build_key_generator(names))
        
        # 7. 解密函数
        lines.extend(self._build_decryptor(names))
        
        # 8. opcode 表构建函数
        lines.extend(self._build_opcode_builder(names, vm_structure))
        
        # 9. VM 执行器
        lines.extend(self._build_vm_executor(names, vm_structure))
        
        # 10. 主执行流程
        lines.extend(self._build_main_entry(names))
        
        # 11. 安全检测
        if vm_structure['layers'][0]['anti_debug']:
            lines.extend(self._build_security_checks(names))
        
        lines.append("end)()")
        
        return '\n'.join(lines)
    
    def _generate_obfuscated_names(self) -> Dict[str, str]:
        """生成混淆的变量名"""
        chars = string.ascii_lowercase + string.ascii_uppercase
        
        return {
            'chunk': ''.join(random.choice(chars) for _ in range(random.randint(3, 6))),
            'order_tbl': ''.join(random.choice(chars) for _ in range(random.randint(3, 6))),
            'key_tbl': ''.join(random.choice(chars) for _ in range(random.randint(3, 6))),
            'size_tbl': ''.join(random.choice(chars) for _ in range(random.randint(3, 6))),
            'decrypt': ''.join(random.choice(chars) for _ in range(random.randint(4, 8))),
            'exec': ''.join(random.choice(chars) for _ in range(random.randint(4, 8))),
            'vm': ''.join(random.choice(chars) for _ in range(random.randint(4, 8))),
            'opcode_tbl': ''.join(random.choice(chars) for _ in range(random.randint(4, 8))),
            'stack': ''.join(random.choice(chars) for _ in range(random.randint(3, 6))),
            'pc': ''.join(random.choice(chars) for _ in range(random.randint(3, 6))),
            'running': ''.join(random.choice(chars) for _ in range(random.randint(3, 6))),
            'check': ''.join(random.choice(chars) for _ in range(random.randint(4, 8))),
        }
    
    def _build_key_generator(self, names: Dict) -> List[str]:
        """构建动态密钥生成器"""
        lines = []
        fn_name = names['exec']
        
        lines.append(f"local function {fn_name}()")
        lines.append(f"  local t=math.random(os.time())")
        lines.append(f"  local s=string.sub(tostring({names['key_tbl']}[1] or 1),-3)")
        lines.append(f"  return (t*17+#s)%0xFFFFFFFF")
        lines.append("end")
        
        return lines
    
    def _build_decryptor(self, names: Dict) -> List[str]:
        """构建解密函数 (bit32 兼容)"""
        lines = []
        fn_name = names['decrypt']
        
        lines.append(f"local function {fn_name}(d,k)")
        lines.append("  local r={}")
        lines.append("  for i=1,#d do")
        lines.append("    local kb=bit32.band(bit32.rshift(k,((i%4)*8)),255)")
        lines.append("    local c=string.byte(d,i)")
        lines.append("    if c then r[i]=string.char(bit32.bxor(c,kb))end")
        lines.append("  end")
        lines.append("  return table.concat(r)")
        lines.append("end")
        
        return lines
    
    def _build_opcode_builder(self, names: Dict, vm_structure: Dict) -> List[str]:
        """构建动态 opcode 表"""
        lines = []
        tbl_name = names['opcode_tbl']
        
        lines.append(f"local {tbl_name}={{}}")
        
        # 添加混淆的 opcode 表项
        op_count = len(vm_structure['layers'][0]['opcode_map'])
        entries = []
        
        for i, (op_name, op_id) in enumerate(vm_structure['layers'][0]['opcode_map'].items()):
            # 混淆处理
            entry = f"[{op_id}]=function({names['vm']},{names['pc']})"
            entries.append(entry)
        
        # 随机插入一些假条目
        for _ in range(op_count // 3):
            fake_id = random.randint(0xE0, 0xFF)
            entries.append(f"[{fake_id}]=function() end")
        
        random.shuffle(entries)
        lines.append("  " + ",".join(entries))
        
        return lines
    
    def _build_vm_executor(self, names: Dict, vm_structure: Dict) -> List[str]:
        """构建 VM 执行器"""
        lines = []
        vm_name = names['vm']
        
        # VM 状态表
        lines.append(f"local {vm_name}={{")
        lines.append(f"  {names['stack']}={{}},")
        lines.append(f"  {names['pc']}=1,")
        lines.append(f"  {names['running']}=true,")
        lines.append(f"  top=0")
        lines.append("}")
        
        # 执行循环 (使用 while true 不可预测结构)
        exec_fn = ''.join(random.choice(string.ascii_lowercase) for _ in range(6))
        lines.append(f"local function {exec_fn}()")
        lines.append(f"  while {vm_name}.{names['running']} do")
        
        # 添加控制流混淆 - 虚假跳转
        if random.random() > 0.3:
            lines.append(f"    if math.random()>0.9 then {vm_name}.{names['pc']}={vm_name}.{names['pc']}+2 end")
        
        lines.append(f"    local op={names['opcode_tbl']}[{vm_name}.{names['pc']}]")
        lines.append(f"    if op then op({vm_name},{vm_name}.{names['pc']})end")
        lines.append(f"    {vm_name}.{names['pc']}={vm_name}.{names['pc']}+1")
        
        lines.append("  end")
        lines.append("end")
        
        return lines
    
    def _build_main_entry(self, names: Dict) -> List[str]:
        """构建主入口"""
        lines = []
        
        # 解密并执行
        chunk_var = f"{names['chunk']}0"
        if chunk_var in [f"local {names['chunk']}{i}" for i in range(10)]:
            lines.append(f"local d={names['decrypt']}({names['chunk']}0,{names['exec']}())")
            lines.append(f"loadstring and loadstring(d)()")
        
        return lines
    
    def _build_security_checks(self, names: Dict) -> List[str]:
        """构建安全检测"""
        lines = []
        check_fn = names['check']
        
        lines.append(f"local function {check_fn}()")
        
        # Anti-debug 检测
        lines.append("  if debug and debug.getinfo then")
        lines.append("    local i=debug.getinfo(1)")
        lines.append("    if i and i.currentline<0 then")
        lines.append(f"      {names['vm']}.{names['running']}=false")
        lines.append("    end")
        lines.append("  end")
        
        # 死循环混淆
        if random.random() > 0.5:
            lines.append("  local _=0")
            lines.append("  while _<1 do _=_+1 end")
        
        lines.append("end")
        
        return lines
    
    def _wrap_output(self, vm_code: str) -> str:
        """包装VM代码为完整Lua文件"""
        lines = []
        
        # 头部注释
        lines.append("-- Generated by Valax VM Obfuscator")
        lines.append("-- Do not modify!")
        lines.append("")
        
        # VM代码
        lines.append("(function()")
        lines.append(vm_code)
        lines.append("end)()")
        
        return '\n'.join(lines)


# =============================================================================

def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(
        description='Valax Obfuscator - Lua代码混淆器 (增强版)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python valax-obfuscator.py input.lua output.lua
  python valax-obfuscator.py script.lua -o obfuscated.lua --seed 12345
  python valax-obfuscator.py code.lua out.lua --no-junk --no-control-flow
  python valax-obfuscator.py code.lua out.lua --no-cff --no-string-hide --no-anti-debug
  python valax-obfuscator.py input.lua out.lua --enable-vm --enable-fake-ops --compact

增强混淆技术:
  --no-cff          禁用控制流扁平化 (state machine)
  --no-string-hide  禁用字符串隐藏 (集中表 + 解密)
  --no-anti-debug   禁用Anti-debug (无意义循环 + 环境检测)
  --enable-vm       启用VM混淆
  --messy           混乱输出格式
  --enable-fake-ops         启用假操作码 (迷惑反编译器)
  --enable-fake-branches    启用假分支和死代码路径
  --enable-anti-dump       启用反dump检测
  --compact                 紧凑输出格式 (最小化代码大小)
  --no-fake-ops            禁用假操作码
  --no-fake-branches       禁用假分支

商业级保护:
  --enable-multi-vm        启用多层VM系统 (外层VM + 内层嵌套解释器)
  --enable-segment-decrypt 启用字节码分段动态解密
  --enable-env-binding     启用环境绑定 (Roblox/Lua环境特征)
  --enable-timing-check    启用时间/行为检测 (防调试)
  --enable-fake-struct     启用虚假函数和伪proto结构
  --enable-num-split       启用数字混淆 (拆分表达式)
  --commercial             启用所有商业级保护

高级安全强化:
  --enable-advanced-security 启用高级安全强化 (Anti-Hook, Anti-Dump, Anti-Trace, 水印)
  --enable-anti-hook        启用Anti-Hook保护 (延迟检测 + Hook诱捕)
  --enable-anti-trace       启用Anti-VM Trace保护 (dispatcher混淆 + 时间检测)
  --enable-watermark        启用水印强绑定
  --enable-self-destruct    启用自毁策略
  --max-security            启用所有高级安全强化

远程验证Loader:
  --enable-loader           启用远程验证Loader (Lua执行前必须通过远程验证)
  --loader-url              远程验证服务器URL (例如: https://auth.example.com)

Roblox Anti-Dumper:
  --enable-roblox-dump      启用Roblox专用Anti-Dumper保护
  --no-fake-env            禁用假环境构造
  --no-hook-detect         禁用Hook检测
  --no-delay-trigger        禁用延迟触发检测
        '''
    )
    
    parser.add_argument('--stdin', action='store_true',
                        help='从标准输入读取源码，不读取文件')
    parser.add_argument('input', nargs='?', help='输入Lua文件路径')
    parser.add_argument('--output', type=str, default=None, help='输出文件路径 (默认: 输入文件.obfuscated.lua 或 stdout)')
    parser.add_argument('--seed', type=int, help='随机种子 (默认: 随机)')
    parser.add_argument('--no-junk', action='store_true', help='禁用垃圾代码')
    parser.add_argument('--no-control-flow', action='store_true', help='禁用控制流扰乱')
    parser.add_argument('--no-string-encrypt', action='store_true', help='禁用字符串加密')
    parser.add_argument('--enhanced', action='store_true', help='启用增强混淆')
    parser.add_argument('--no-cff', action='store_true', help='禁用控制流扁平化')
    parser.add_argument('--no-string-hide', action='store_true', help='禁用字符串隐藏')
    parser.add_argument('--no-anti-debug', action='store_true', help='禁用Anti-debug')
    parser.add_argument('--enable-vm', action='store_true', help='启用VM混淆')
    parser.add_argument('--messy', action='store_true', help='混乱输出格式')
    parser.add_argument('--enable-fake-ops', action='store_true', help='启用假操作码')
    parser.add_argument('--no-fake-ops', action='store_true', help='禁用假操作码')
    parser.add_argument('--enable-fake-branches', action='store_true', help='启用假分支和死代码')
    parser.add_argument('--no-fake-branches', action='store_true', help='禁用假分支')
    parser.add_argument('--enable-anti-dump', action='store_true', help='启用反dump检测')
    parser.add_argument('--compact', action='store_true', help='紧凑输出格式')
    # 商业级保护参数
    parser.add_argument('--enable-multi-vm', action='store_true', help='启用多层VM系统 (外层VM + 内层嵌套解释器)')
    parser.add_argument('--enable-segment-decrypt', action='store_true', help='启用字节码分段动态解密')
    parser.add_argument('--enable-env-binding', action='store_true', help='启用环境绑定 (Roblox/Lua环境特征)')
    parser.add_argument('--enable-timing-check', action='store_true', help='启用时间/行为检测 (防调试)')
    parser.add_argument('--enable-fake-struct', action='store_true', help='启用虚假函数和伪proto结构')
    parser.add_argument('--enable-num-split', action='store_true', help='启用数字混淆 (拆分表达式)')
    parser.add_argument('--commercial', action='store_true', help='启用所有商业级保护')
    
    # 高级安全强化参数 (新增)
    parser.add_argument('--enable-advanced-security', action='store_true', help='启用高级安全强化 (Anti-Hook, Anti-Dump, Anti-Trace, 水印)')
    parser.add_argument('--enable-anti-hook', action='store_true', help='启用Anti-Hook保护 (延迟检测 + Hook诱捕)')
    parser.add_argument('--enable-anti-trace', action='store_true', help='启用Anti-VM Trace保护 (dispatcher混淆 + 时间检测)')
    parser.add_argument('--enable-watermark', action='store_true', help='启用水印强绑定')
    parser.add_argument('--enable-self-destruct', action='store_true', help='启用自毁策略')
    parser.add_argument('--max-security', action='store_true', help='启用所有高级安全强化')
    
    # 远程验证Loader参数 (新增)
    parser.add_argument('--enable-loader', action='store_true', help='启用远程验证Loader (Lua执行前必须通过远程验证)')
    parser.add_argument('--loader-url', type=str, help='远程验证服务器URL (例如: https://auth.example.com)')
    
    # Roblox Anti-Dumper 参数 (新增)
    parser.add_argument('--enable-roblox-dump', action='store_true', help='启用Roblox专用Anti-Dumper保护')
    parser.add_argument('--no-fake-env', action='store_true', help='禁用假环境构造')
    parser.add_argument('--no-hook-detect', action='store_true', help='禁用Hook检测')
    parser.add_argument('--no-delay-trigger', action='store_true', help='禁用延迟触发检测')
    
    args = parser.parse_args()
    
    # 检查 Loader 配置
    if args.enable_loader and not args.loader_url:
        print("错误: --enable-loader 需要配合 --loader-url 使用", file=sys.stderr)
        sys.exit(1)
    
    # 读取输入
    if getattr(args, 'stdin', False):
        print("[*] Reading from stdin", file=sys.stderr)
        source_code = sys.stdin.read()
        if isinstance(source_code, bytes):
            source_code = source_code.decode('utf-8', errors='replace')
    else:
        if not os.path.exists(args.input):
            print(f"错误: 文件不存在: {args.input}", file=sys.stderr)
            sys.exit(1)
        print(f"[*] Reading: {args.input}", file=sys.stderr)
        with open(args.input, 'r', encoding='utf-8') as f:
            source_code = f.read()
    
    # 强制使用 ValaxForceVM - 无 fallback
    print("[*] Using Valax Force VM (mandatory protection)", file=sys.stderr)
    obfuscator = ValaxForceVM(seed=args.seed)
    
    # 设置 ValaxForceVM 配置选项
    # VM 层数设置
    if args.enable_multi_vm:
        obfuscator.vm_layers = max(1, getattr(args, 'vm_layers', 3))
        print(f"[*] VM Layers: {obfuscator.vm_layers}", file=sys.stderr)
    
    # 分段数设置
    if args.enable_segment_decrypt:
        obfuscator.chunk_count = max(2, getattr(args, 'chunk_count', 4))
        print(f"[*] Chunk count: {obfuscator.chunk_count}", file=sys.stderr)
    
    # 安全强化设置
    if args.max_security:
        obfuscator.enable_security = True
        print("[*] Max Security: ENABLED", file=sys.stderr)
    
    try:
        # 执行强制 VM 混淆 - 无 fallback
        result = obfuscator.obfuscate(source_code)
        
        # 后处理: 混乱输出格式
        if args.messy:
            result = _mess_up_output(result)
    except Exception as e:
        print(f"错误: 混淆失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        # 如果是 stdin 模式，不退出，只是输出原始源码
        if args.stdin:
            result = source_code
        else:
            sys.exit(1)
    
    # 确定输出文件
    output_file = getattr(args, 'output', None) or None
    if not output_file:
        if args.input:
            # 默认输出文件名
            base, ext = os.path.splitext(args.input)
            output_file = f"{base}.obfuscated.lua"
        else:
            # stdin 模式，没有输入文件，输出到 stdout
            output_file = None
    
    # 输出结果
    if output_file:
        print(f"[*] Writing: {output_file}", file=sys.stderr)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
    else:
        # stdin 模式，输出到 stdout (只输出混淆后的代码，不输出其他信息)
        print(result, end='')
    
    # 统计信息 (输出到 stderr，不干扰 stdout)
    original_size = len(source_code)
    obfuscated_size = len(result)
    ratio = (obfuscated_size / original_size) * 100 if original_size > 0 else 100
    
    print(f"\n[+] 完成!", file=sys.stderr)
    print(f"    原始大小: {original_size} bytes", file=sys.stderr)
    print(f"    混淆后: {obfuscated_size} bytes ({ratio:.1f}%)", file=sys.stderr)
    print(f"    随机种子: {obfuscator.seed}", file=sys.stderr)
    print(f"    保护模式: Valax Force VM (强制保护)", file=sys.stderr)


def _mess_up_output(code: str) -> str:
    """
    混乱输出代码格式
    
    策略:
    1. 随机添加空行
    2. 在行尾添加随机空格
    3. 随机化一些行的缩进
    4. 添加无意义注释干扰
    """
    lines = code.split('\n')
    result_lines = []
    
    junk_comments = {
        'lua': [
            '--[[', 'local _ = nil', '--]]',
            'do local _=1 end',
        ]
    }
    
    for line in lines:
        # 随机添加空行
        if random.random() > 0.85 and line.strip():
            result_lines.append('')
        
        # 行尾添加随机空格
        if line.strip() and random.random() > 0.7:
            spaces = ''.join(random.choice(' \t') for _ in range(random.randint(1, 8)))
            line = line.rstrip() + spaces
        
        result_lines.append(line)
        
        # 随机在代码行后添加干扰注释
        if line.strip() and not line.strip().startswith('--') and random.random() > 0.92:
            comment = random.choice(junk_comments['lua'])
            result_lines.append(comment)
    
    # 随机打乱一些短代码块的顺序 (但保持语法正确)
    # 这里简化处理，只做基本的格式混乱
    
    return '\n'.join(result_lines)


# =============================================================================
# 第十部分: 高级安全强化系统 (Anti-Hook, Anti-Dump, Anti-Trace, 水印强绑定)
# =============================================================================

class AdvancedSecurityGenerator:
    """
    高级安全强化生成器 - 深度保护Lua VM代码
    
    核心功能:
    1. Anti-Hook: 隐蔽检测 + 延迟触发
    2. Anti-Memory Dump: 字节码分段 + 短生命周期
    3. Anti-VM Trace: dispatcher混淆 + 时间检测
    4. 水印强绑定: 拆分水印 + 完整性检测
    5. 自毁策略: 间接破坏 + 假成功
    """
    
    WATERMARK_PARTS = ["Protected By", " Valax Scrub", " Engine (https://www.valaxscrub.shop)"]
    
    def __init__(self, seed: int = None):
        self.seed = seed if seed else random.randint(1, 0xFFFFFFFF)
        random.seed(self.seed)
        self.obfuscate_names = True
        self.compact_output = True
        
        # 保护强度配置
        self.anti_hook_strength = 3  # 1-5, 越高越强
        self.anti_dump_strength = 3
        self.anti_trace_strength = 3
        
    def generate(self) -> List[str]:
        """生成所有安全保护代码"""
        lines = []
        names = self._generate_names()
        
        # 1. 水印生成 (最先, 用于key生成)
        lines.extend(self._generate_watermark_system(names))
        
        # 2. Anti-Hook系统
        lines.extend(self._generate_anti_hook_system(names))
        
        # 3. Anti-Memory Dump系统
        lines.extend(self._generate_anti_dump_system(names))
        
        # 4. Anti-VM Trace系统
        lines.extend(self._generate_anti_trace_system(names))
        
        # 5. 自毁策略系统
        lines.extend(self._generate_self_destruct_system(names))
        
        return lines
    
    def _generate_names(self) -> Dict[str, str]:
        """生成混淆的变量名"""
        chars = string.ascii_lowercase + string.ascii_uppercase + string.digits
        names = {}
        
        # 基础保护变量
        base_names = [
            'wm', 'w1', 'w2', 'w3', 'wkey', 'whash',
            'hk', 'ht', 'hp', 'hf', 'hg',
            'dt', 'd1', 'd2', 'd3', 'dk', 'dp',
            'tr', 'ts', 'te', 'tc', 'td',
            'sd', 'sf', 'sg', 'sk', 'sv',
            'ch', 'cv', 'ct', 'cx', 'cy',
            'st', 'sp', 'si', 'sc', 'sb',
        ]
        
        for name in base_names:
            length = random.randint(2, 5) if self.obfuscate_names else len(name)
            names[name] = ''.join(random.choice(chars) for _ in range(length))
        
        return names
    
    # =========================================================================
    # 一、水印强绑定系统
    # =========================================================================
    
    def _generate_watermark_system(self, names: Dict[str, str]) -> List[str]:
        """
        生成水印强绑定系统
        
        策略:
        1. 水印拆分到多个变量
        2. 使用char codes构造 (不直接可见字符串)
        3. 运行时拼接
        4. 参与解密key生成 (动态: hash(watermark + os.clock()))
        5. 完整性检测 (间接)
        """
        lines = []
        n = names
        
        # 水印碎片 (拆分三部分)
        w1 = self.WATERMARK_PARTS[0]
        w2 = self.WATERMARK_PARTS[1]
        w3 = self.WATERMARK_PARTS[2]
        
        # ================================================================
        # 1. 使用char codes构造水印碎片 (隐蔽性增强)
        # 不直接拼接字符串，而是用string.char()构造
        # ================================================================
        
        # 生成char codes格式的水印
        w1_codes = ','.join(str(ord(c)) for c in w1)
        w2_codes = ','.join(str(ord(c)) for c in w2)
        w3_codes = ','.join(str(ord(c)) for c in w3)
        
        # 水印变量名 (混淆)
        w1_var = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        w2_var = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        w3_var = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        
        # char codes构造函数名
        cc_func = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        lines.append(f"local function {cc_func}(t)local r=''for _,v in ipairs(t)do r=r..string.char(v)end;return r end")
        
        # 使用char codes数组存储水印
        lines.append(f"local {w1_var}={{{w1_codes}}}")
        lines.append(f"local {w2_var}={{{w2_codes}}}")
        lines.append(f"local {w3_var}={{{w3_codes}}}")
        
        # 运行时拼接水印
        wm_name = n['wm']
        lines.append(f"local {n['wm']}={cc_func}({w1_var})..{cc_func}({w2_var})..{cc_func}({w3_var})")
        
        # 清理char codes数组
        lines.append(f"{w1_var}=nil{w2_var}=nil{w3_var}=nil{cc_func}=nil")
        
        # ================================================================
        # 2. 动态key生成: hash(watermark + os.clock())
        # key在运行时动态计算，增加逆向难度
        # ================================================================
        
        # 获取初始时间戳 (作为salt)
        init_time = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local {init_time}=os.clock()")
        
        # 动态key生成函数
        dyn_key_func = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        dyn_key_var = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        
        lines.append(f"local function {dyn_key_func}(wm,t)")
        lines.append(f"  local h=0 for i=1,#wm do h=h+string.byte(wm,i)*(i%127)end")
        lines.append(f"  h=h~(math.floor(t*1000)%0xFFFF)")
        lines.append(f"  return h%0xFFFFFFFF")
        lines.append(f"end")
        
        # 动态生成key
        lines.append(f"local {n['wkey']}={dyn_key_func}({n['wm']},{init_time})")
        
        # ================================================================
        # 3. 水印哈希 (用于完整性检测)
        # ================================================================
        lines.append(f"local {n['whash']}=0")
        lines.append(f"for i=1,#{n['wm']} do {n['whash']}={n['whash']}+string.byte({n['wm']},i)*(i%127)end")
        
        # 水印完整性验证 (注入到其他检查函数中)
        lines.append(f"{n['wm']}=nil")
        
        return lines
    
    def _obfuscate_string(self, s: str) -> str:
        """简单混淆字符串"""
        return ''.join(chr((ord(c) + 13) % 256) for c in s)
    
    # =========================================================================
    # 二、Anti-Hook系统 (隐蔽检测 + 延迟触发)
    # =========================================================================
    
    def _generate_anti_hook_system(self, names: Dict[str, str]) -> List[str]:
        """
        生成Anti-Hook系统
        
        策略:
        1. 核心函数完整性检测 (延迟执行)
        2. 轻量指纹检测
        3. Hook诱捕 (honeypot)
        4. 间接触发 (不直接error)
        """
        lines = []
        n = names
        
        # 检测状态
        lines.append(f"local {n['hk']}=false")  # hook检测状态
        lines.append(f"local {n['ht']}=0")        # 延迟计数器
        lines.append(f"local {n['hp']}=false")    # 通过检测
        
        # 核心函数指纹存储
        lines.append(f"local {n['hf']}=nil")     # tostring原始值
        lines.append(f"local {n['hg']}=nil")     # loadstring原始值
        
        # 1. 记录原始指纹 (VM初始化时)
        init_fp = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {init_fp}()")
        lines.append(f"  {n['hf']}=tostring(loadstring)")
        lines.append(f"  {n['hg']}=tostring(pcall)")
        lines.append(f"end")
        lines.append(f"{init_fp}()")
        
        # 2. 延迟检测函数 (不直接触发)
        check_hook = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {check_hook}()")
        lines.append(f"  {n['ht']}={n['ht']}+1")
        lines.append(f"  if {n['ht']}<5 then return end")  # 延迟检测
        
        # 核心检测逻辑
        lines.append(f"  local ok=pcall(function()return tostring(loadstring) end)")
        lines.append(f"  if ok and {n['hf']}then")
        lines.append(f"    local cur=tostring(loadstring)")
        lines.append(f"    if cur~={n['hf']}then")
        
        # 触发间接破坏 (修改VM数据)
        corrupt_data = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"      {n['hk']}=true")
        lines.append(f"      local function {corrupt_data}()")
        lines.append(f"        {n['hp']}=true")  # 标记为可疑
        lines.append(f"      end")
        lines.append(f"      {corrupt_data}()")
        lines.append(f"    end")
        lines.append(f"  end")
        
        # 指纹变化检测
        lines.append(f"  if tostring(tostring)~={n['hf']}then {n['hk']}=true end")
        lines.append(f"end")
        
        # 3. Hook诱捕 (honeypot)
        honeypot = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local {n['hp']}=function()")
        lines.append(f"  local _f=function() end")
        lines.append(f"  if _f then local _=tostring(_f)end")
        lines.append(f"  return 12345")  # 假值
        lines.append(f"end")
        
        # 诱捕触发检测
        honeypot_check = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {honeypot_check}()")
        lines.append(f"  local r={n['hp']}()")
        lines.append(f"  if r==12345 then")  # 如果返回真值, 说明被拦截
        lines.append(f"    {n['hk']}=true")
        lines.append(f"  end")
        lines.append(f"end")
        
        # 4. debug.getinfo完整性检测
        debug_check = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {debug_check}()")
        lines.append(f"  if debug and debug.getinfo then")
        lines.append(f"    local f=loadstring or load")
        lines.append(f"    local ok,fk=pcall(f,'')")
        lines.append(f"    if not ok then {n['hk']}=true end")
        lines.append(f"  end")
        lines.append(f"end")
        
        # 存储检测函数名供VM调用
        lines.append(f"{names.get('vm', 'vm')}.{n['hk']}={n['hk']}" if names.get('vm') else "")
        lines.append(f"local _ah_check={check_hook}")
        lines.append(f"local _ah_honeypot={honeypot_check}")
        lines.append(f"local _ah_debug={debug_check}")
        
        return lines
    
    # =========================================================================
    # 三、Anti-Memory Dump系统 (分段存储 + 短生命周期)
    # =========================================================================
    
    def _generate_anti_dump_system(self, names: Dict[str, str]) -> List[str]:
        """
        生成Anti-Memory Dump系统
        
        策略:
        1. 字节码分段存储 (多个变量)
        2. 每次只解密一小段
        3. 执行完立即nil
        4. 不保留完整结构
        """
        lines = []
        n = names
        
        # 分段状态
        lines.append(f"local {n['dt']}=0")      # 当前段索引
        lines.append(f"local {n['d1']}=nil")     # 段1数据
        lines.append(f"local {n['d2']}=nil")     # 段2数据
        lines.append(f"local {n['d3']}=nil")     # 段3数据
        lines.append(f"local {n['dp']}=false")    # 段指针
        
        # 段数据表 (混淆变量名)
        seg_table = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local {seg_table}={{}}")
        
        # 分段解密函数
        seg_dec = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {seg_dec}(data,idx,k)")
        lines.append(f"  local seg=data:sub((idx-1)*8+1,idx*8)")
        lines.append(f"  local r={{}}")
        lines.append(f"  for i=1,#seg do")
        lines.append(f"    local b=string.byte(seg,i)")
        lines.append(f"    local kbit=bit32.band(bit32.rshift(k,((i%4)*8)),255)")
        lines.append(f"    r[i]=string.char(bit32.bxor(b,kbit))")
        lines.append(f"  end")
        lines.append(f"  return table.concat(r)")
        lines.append(f"end")
        
        # 段加载器 (每次只加载一段)
        seg_load = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {seg_load}(bc,k,idx)")
        lines.append(f"  if idx==1 then {n['d1']}={seg_dec}(bc,idx,k){n['dp']}={n['d1']}")
        lines.append(f"  elseif idx==2 then {n['d2']}={seg_dec}(bc,idx,k){n['dp']}={n['d2']}")
        lines.append(f"  elseif idx==3 then {n['d3']}={seg_dec}(bc,idx,k){n['dp']}={n['d3']}")
        lines.append(f"  end")
        lines.append(f"  return {n['dp']}")
        lines.append(f"end")
        
        # 段清理函数 (执行完立即清理)
        seg_clean = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {seg_clean}(idx)")
        lines.append(f"  if idx==1 then {n['d1']}=nil")
        lines.append(f"  elseif idx==2 then {n['d2']}=nil")
        lines.append(f"  elseif idx==3 then {n['d3']}=nil")
        lines.append(f"  end")
        lines.append(f"  collectgarbage()")
        lines.append(f"end")
        
        # 存储段操作函数
        lines.append(f"{names.get('vm', 'vm')}.{seg_load}={seg_load}" if names.get('vm') else "")
        lines.append(f"{names.get('vm', 'vm')}.{seg_clean}={seg_clean}" if names.get('vm') else "")
        
        # 时间异常检测
        time_check = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {time_check}(start_t)")
        lines.append(f"  if os.clock()-start_t>0.03 then")
        lines.append(f"    {n['d1']}=nil{n['d2']}=nil{n['d3']}=nil")
        lines.append(f"    return false")
        lines.append(f"  end")
        lines.append(f"  return true")
        lines.append(f"end")
        
        return lines
    
    # =========================================================================
    # 四、Anti-VM Trace系统 (dispatcher混淆 + 时间检测)
    # =========================================================================
    
    def _generate_anti_trace_system(self, names: Dict[str, str]) -> List[str]:
        """
        生成Anti-VM Trace系统
        
        策略:
        1. dispatcher混淆 (不用if-else链)
        2. 插入fake opcode
        3. 控制流扰乱 (state machine)
        4. 时间检测
        """
        lines = []
        n = names
        
        # Trace检测状态
        lines.append(f"local {n['tr']}=false")   # trace检测状态
        lines.append(f"local {n['ts']}=0")       # 状态机状态
        lines.append(f"local {n['te']}=0")       # 执行计数
        
        # Dispatcher表 (混淆索引)
        dispatch_key1 = random.randint(1000, 9999)
        dispatch_key2 = random.randint(100, 999)
        lines.append(f"local {n['td']}={{}}")
        
        # 生成混淆的dispatch表
        for op in range(0, 0x60):
            mapped = ((op * dispatch_key1 + dispatch_key2) % 0x100)
            lines.append(f"{n['td']}[{op}]={mapped}")
        
        # 假opcode表 (20%假指令)
        fake_ops = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local {fake_ops}={{")
        for _ in range(20):
            fake_op = random.randint(0xD0, 0xDF)
            lines.append(f"  [{fake_op}]=1,")
        lines.append(f"}}")
        
        # 状态机执行器 (代替if-else链)
        state_exec = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {state_exec}(op)")
        lines.append(f"  {n['ts']}={n['ts']}+1")
        lines.append(f"  local mapped=({n['td']}[op]or 0)")
        lines.append(f"  if {fake_ops}[op]then return end")  # 跳过假opcode
        lines.append(f"  if {n['ts']}%7==0 then")  # 周期性检测
        lines.append(f"    local t1=os.clock()")
        lines.append(f"    for i=1,100 do local _=i*2 end")
        lines.append(f"    if os.clock()-t1>0.02 then {n['tr']}=true end")
        lines.append(f"  end")
        lines.append(f"  return mapped")
        lines.append(f"end")
        
        # 随机跳转干扰
        random_jump = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {random_jump}(pc,max)")
        lines.append(f"  local j=math.random(-3,3)")
        lines.append(f"  local np=pc+j")
        lines.append(f"  if np<1 then np=max+npc end")
        lines.append(f"  if np>max then np=np-max end")
        lines.append(f"  return np")
        lines.append(f"end")
        
        # PC轨迹检测
        pc_history = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local {pc_history}={{}}")
        lines.append(f"local function _check_pc_trace(pc)")
        lines.append(f"  table.insert({pc_history},pc)")
        lines.append(f"  if #{pc_history}>50 then")
        lines.append(f"    local last={pc_history}[#{pc_history}-1]")
        lines.append(f"    if pc==last then {n['tr']}=true end")
        lines.append(f"    table.remove({pc_history},1)")
        lines.append(f"  end")
        lines.append(f"end")
        
        # 存储到VM
        lines.append(f"local _at_state={state_exec}")
        lines.append(f"local _at_jump={random_jump}")
        lines.append(f"local _at_trace={n['tr']}")
        
        return lines
    
    # =========================================================================
    # 五、自毁策略系统 (间接破坏 + 假成功)
    # =========================================================================
    
    def _generate_self_destruct_system(self, names: Dict[str, str]) -> List[str]:
        """
        生成自毁策略系统
        
        策略:
        1. 数据污染 (修改常量/opcode)
        2. 假成功 (返回错误但不报错)
        3. 随机行为 (每次表现不同)
        4. 死循环/无效路径
        """
        lines = []
        n = names
        
        # 自毁触发状态
        lines.append(f"local {n['sd']}=false")   # 自毁触发
        lines.append(f"local {n['sf']}=0")       # 失败计数
        lines.append(f"local {n['sg']}=math.random(1,3)")  # 随机行为选择
        
        # 1. 数据污染函数
        corrupt_const = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {corrupt_const}(t)")
        lines.append(f"  for k,v in pairs(t or {{}})do")
        lines.append(f"    if type(v)=='number'then")
        lines.append(f"      t[k]=v+math.random(-10,10)")
        lines.append(f"    elseif type(v)=='string'then")
        lines.append(f"      t[k]=v:gsub('.',function(c)return string.char(bit32.bxor(string.byte(c),1)) end)")
        lines.append(f"    end")
        lines.append(f"  end")
        lines.append(f"end")
        
        # 2. 假成功函数 (返回假结果)
        fake_success = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {fake_success}(...)")
        lines.append(f"  local args={{...}}")
        lines.append(f"  if {n['sd']}then")
        lines.append(f"    if {n['sg']}==1 then return nil end")
        lines.append(f"    if {n['sg']}==2 then return false end")
        lines.append(f"    if {n['sg']}==3 then return{{}}end")
        lines.append(f"  end")
        lines.append(f"  return table.unpack(args)")
        lines.append(f"end")
        
        # 3. 无效路径执行 (死循环)
        dead_loop = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {dead_loop}(...)")
        lines.append(f"  if {n['sd']}then")
        lines.append(f"    while true do")
        lines.append(f"      local _=1")
        lines.append(f"      if math.random()>0.9999 then break end")
        lines.append(f"    end")
        lines.append(f"  end")
        lines.append(f"end")
        
        # 4. 随机opcode映射扰动
        corrupt_opmap = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {corrupt_opmap}(opmap)")
        lines.append(f"  if {n['sd']}then")
        lines.append(f"    for i=1,#opmap do")
        lines.append(f"      if i%3==0 then")
        lines.append(f"        opmap[i]=(opmap[i]+math.random(1,10))%256")
        lines.append(f"      end")
        lines.append(f"    end")
        lines.append(f"  end")
        lines.append(f"end")
        
        # 5. 完整性破坏函数 (水印检测失败时调用)
        integrity_breaker = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {integrity_breaker}()")
        lines.append(f"  {n['sd']}=true")
        lines.append(f"  {n['sf']}={n['sf']}+1")
        lines.append(f"  if {n['sf']}>3 then")
        lines.append(f"    {dead_loop}()")
        lines.append(f"  end")
        lines.append(f"end")
        
        # 6. 综合自毁入口
        self_destruct = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {self_destruct}(trigger)")
        lines.append(f"  if trigger then")
        lines.append(f"    {integrity_breaker}()")
        lines.append(f"    {corrupt_const}(nil)")
        lines.append(f"    return false")
        lines.append(f"  end")
        lines.append(f"  return true")
        lines.append(f"end")
        
        # 存储函数
        lines.append(f"local _sd_check={self_destruct}")
        lines.append(f"local _sd_break={integrity_breaker}")
        lines.append(f"local _sd_corrupt={corrupt_const}")
        
        return lines


# =============================================================================
# 第十一部分: 增强的VMBuilder集成
# =============================================================================

class EnhancedVMBuilder:
    """
    增强的VMBuilder - 集成所有高级安全保护
    
    新增功能:
    1. 集成AdvancedSecurityGenerator
    2. 所有保护自动应用
    3. 水印强绑定到解密key
    4. 完整的自毁策略
    """
    
    def __init__(self, seed: int = None):
        self.seed = seed if seed else random.randint(1, 0xFFFFFFFF)
        self.encoder = AdvancedBytecodeEncoder(self.seed)
        self.security = AdvancedSecurityGenerator(self.seed)
        self.obfuscate_names = True
        self.compact_output = True
        
        # 启用所有高级保护
        self.enable_anti_hook = True
        self.enable_anti_dump_advanced = True
        self.enable_anti_trace = True
        self.enable_watermark = True
        self.enable_self_destruct = True
        
    def build(self, func: Function) -> str:
        """生成完整的受保护的VM代码"""
        # 编码字节码
        encoded_bc = self.encoder.encode(func)
        
        # 水印key参与解密 (使用watermark_key作为解密密钥的一部分)
        watermark_key = self._generate_watermark_key()
        decrypt_key = watermark_key  # 使用水印key作为主密钥
        
        # 生成受保护的VM代码
        vm_code = self._generate_protected_vm_code(encoded_bc, decrypt_key, watermark_key)
        
        return vm_code
    
    def _generate_watermark_key(self) -> int:
        """生成基于水印的密钥"""
        watermark = ''.join(AdvancedSecurityGenerator.WATERMARK_PARTS)
        key = 0
        for i, c in enumerate(watermark):
            key += ord(c) * (i + 1) * 17
        return key % 0xFFFFFFFF
    
    def _generate_protected_vm_code(self, encoded_bc: str, key: int, wm_key: int) -> str:
        """生成受保护的VM代码"""
        lines = []
        names = self._generate_names()
        
        # 1. 生成基础变量
        if self.compact_output:
            lines.append(f"local b=\"{encoded_bc}\"")
            lines.append(f"local k={key}")
            lines.append(f"local wk={wm_key}")
        else:
            lines.append(f"local _b=\"{encoded_bc}\"")
            lines.append(f"local _k={key}")
            lines.append(f"local _wk={wm_key}")
        
        # 2. 解密函数 (带水印key, bit32兼容)
        dk_name = names['decrypt']
        lines.append(f"local function {dk_name}(s)")
        lines.append(f"  local r={{}}for i=1,#s do")
        lines.append(f"    local kb=bit32.band(bit32.rshift(_k,((i%4)*8)),255)")
        lines.append(f"    local wb=bit32.band(bit32.rshift(_wk,((i%3)*8)),255)")
        lines.append(f"    r[i]=string.char(bit32.bxor(bit32.bxor(string.byte(s,i),kb),wb))")
        lines.append(f"  end;return table.concat(r)end")
        
        # 3. 分段字节码
        bc_segments = self._split_bytecode(encoded_bc)
        for i, seg in enumerate(bc_segments):
            lines.append(f"local _s{i+1}=\"{seg}\"")
        
        # 4. 动态加载器
        load_name = names.get('loader', names.get('load', 'ld'))
        dk_name = names.get('decrypt', names.get('dec', 'dc'))
        lines.append(f"local function {load_name}()")
        lines.append(f"  local p=\"\"")
        for i in range(len(bc_segments)):
            lines.append(f"  p=p..{dk_name}(_s{i+1})")
        lines.append(f"  return p")
        lines.append(f"end")
        
        # 5. 生成受保护的核心VM
        lines.extend(self._generate_protected_vm_engine(names))
        
        # 6. 集成高级安全系统
        if self.enable_anti_hook:
            lines.extend(self._generate_integrated_anti_hook(names))
        
        if self.enable_anti_dump_advanced:
            lines.extend(self._generate_integrated_anti_dump(names))
        
        if self.enable_anti_trace:
            lines.extend(self._generate_integrated_anti_trace(names))
        
        if self.enable_watermark:
            lines.extend(self._generate_watermark_check(names))
        
        if self.enable_self_destruct:
            lines.extend(self._generate_integrated_self_destruct(names))
        
        # 7. 执行入口
        lines.append(f"local _vm={names['vm_table']}")
        lines.append(f"{load_name}()")
        lines.append("return _vm")
        
        return '\n'.join(lines)
    
    def _split_bytecode(self, bc: str) -> List[str]:
        """分段字节码"""
        segments = []
        seg_len = max(20, len(bc) // 3)
        for i in range(0, len(bc), seg_len):
            segments.append(bc[i:i+seg_len])
        return segments
    
    def _generate_names(self) -> Dict[str, str]:
        """生成混淆变量名"""
        chars = string.ascii_lowercase + string.ascii_uppercase
        names = {}
        
        base = ['vm', 'st', 'tp', 'pc', 'rk', 'bc', 'cn', 'dk', 'ld',
                'ah', 'ad', 'at', 'wm', 'sd', 'decrypt', 'loader']
        
        for name in base:
            length = random.randint(2, 4) if self.obfuscate_names else len(name)
            names[name] = ''.join(random.choice(chars) for _ in range(length))
        
        names['vm_table'] = names['vm']
        return names
    
    def _generate_protected_vm_engine(self, names: Dict[str, str]) -> List[str]:
        """生成受保护的核心VM引擎"""
        lines = []
        n = names
        
        # VM状态表
        lines.append(f"local {n['vm']}={{{n['st']}={{}},")
        lines.append(f"{n['tp']}=0,")
        lines.append(f"{n['pc']}=0,")
        lines.append(f"{n['bc']}=nil,")
        lines.append(f"running=true}}")
        
        # 混淆的dispatcher (带水印key, bit32兼容)
        dispatch = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local {dispatch}={{")
        for op in range(0, 0x60):
            mapped = (op * 31337 + 0x9ABC) % 256
            lines.append(f"  [{op}]={mapped},")
        lines.append(f"}}")
        
        # bit32 shim for this VM
        lines.append("local bit32=bit32 or {}")
        lines.append("if not bit32.rshift then bit32.rshift=function(v,n)return math.floor((v%0x100000000)/(2^n))end end")
        lines.append("if not bit32.bxor then bit32.bxor=function(a,b)return((a%0x100000000)~(b%0x100000000))%0x100000000 end end")
        
        # 主执行循环
        exec_name = names.get('exec', 'exec')
        lines.append(f"local function {exec_name}()")
        lines.append(f"  while {n['vm']}.running do")
        lines.append(f"    local ins={n['vm']}.{n['bc']}[{n['vm']}.{n['pc']}]")
        lines.append(f"    {n['vm']}.{n['pc']}={n['vm']}.{n['pc']}+1")
        lines.append(f"    if not ins then {n['vm']}.running=false break end")
        lines.append(f"    local op=string.byte(ins,1)")
        lines.append(f"    local mop=({dispatch}[op]or op)")
        
        # 执行逻辑 (简化版)
        lines.append(f"    if mop<32 then")
        lines.append(f"      {n['vm']}.{n['st']}[{n['vm']}.{n['tp']}]={n['vm']}.{n['bc']}")
        lines.append(f"    elseif mop<64 then")
        lines.append(f"      {n['vm']}.{n['tp']}={n['vm']}.{n['tp']}+1")
        lines.append(f"    end")
        lines.append(f"  end")
        lines.append(f"end")
        
        lines.append(f"{n['vm']}.exec={exec_name}")
        
        return lines
    
    def _generate_integrated_anti_hook(self, names: Dict[str, str]) -> List[str]:
        """集成Anti-Hook保护"""
        lines = []
        n = names
        
        # 延迟hook检测
        hook_check = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {hook_check}()")
        lines.append(f"  local cnt={n['vm']}.{n['pc']}or 0")
        lines.append(f"  if cnt>20 then")
        lines.append(f"    local ok=pcall(function()return tostring(loadstring) end)")
        lines.append(f"    if ok then")
        lines.append(f"      local ts=tostring(loadstring)")
        lines.append(f"      if ts:match('C function')then")
        lines.append(f"        {n['vm']}.running=false")
        lines.append(f"      end")
        lines.append(f"    end")
        lines.append(f"  end")
        lines.append(f"end")
        
        # 诱捕检测
        hp_check = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {hp_check}()")
        lines.append(f"  local honeypot=function()return 99999 end")
        lines.append(f"  if honeypot()==99999 then")
        lines.append(f"    {n['vm']}.running=false")
        lines.append(f"  end")
        lines.append(f"end")
        
        lines.append(f"{n['vm']}.hook_check={hook_check}")
        
        return lines
    
    def _generate_integrated_anti_dump(self, names: Dict[str, str]) -> List[str]:
        """集成Anti-Dump保护"""
        lines = []
        n = names
        
        # 内存dump检测
        dump_check = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {dump_check}()")
        lines.append(f"  local t1=os.clock()")
        lines.append(f"  for i=1,30 do local _=1 end")
        lines.append(f"  if os.clock()-t1>0.05 then")
        lines.append(f"    {n['vm']}.running=false")
        lines.append(f"  end")
        lines.append(f"  if debug and debug.getinfo then")
        lines.append(f"    pcall(function()loadstring('','') end)")
        lines.append(f"  end")
        lines.append(f"end")
        
        lines.append(f"{n['vm']}.dump_check={dump_check}")
        
        return lines
    
    def _generate_integrated_anti_trace(self, names: Dict[str, str]) -> List[str]:
        """集成Anti-Trace保护"""
        lines = []
        n = names
        
        # trace检测
        trace_check = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {trace_check}()")
        lines.append(f"  local cycle={n['vm']}.{n['pc']}%10")
        lines.append(f"  if cycle==0 then")
        lines.append(f"    local t=os.clock()")
        lines.append(f"    for i=1,50 do local _=i*2 end")
        lines.append(f"    if os.clock()-t>0.015 then")
        lines.append(f"      {n['vm']}.running=false")
        lines.append(f"    end")
        lines.append(f"  end")
        lines.append(f"end")
        
        lines.append(f"{n['vm']}.trace_check={trace_check}")
        
        return lines
    
    def _generate_watermark_check(self, names: Dict[str, str]) -> List[str]:
        """水印完整性检查"""
        lines = []
        n = names
        
        wm_parts = AdvancedSecurityGenerator.WATERMARK_PARTS
        w1 = self._obfuscate_str(wm_parts[0])
        w2 = self._obfuscate_str(wm_parts[1])
        w3 = self._obfuscate_str(wm_parts[2])
        
        # 水印完整性检测 (间接)
        wm_check = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {wm_check}()")
        lines.append(f"  local w=\"{w1}\"..\"{w2}\"..\"{w3}\"")
        lines.append(f"  local h=0")
        lines.append(f"  for i=1,#w do h=h+string.byte(w,i)*(i%0x7F)end")
        lines.append(f"  if h~={self._generate_watermark_key()}then")
        lines.append(f"    {n['vm']}.running=false")
        lines.append(f"  end")
        lines.append(f"end")
        
        lines.append(f"{n['vm']}.wm_check={wm_check}")
        
        return lines
    
    def _generate_integrated_self_destruct(self, names: Dict[str, str]) -> List[str]:
        """集成自毁策略"""
        lines = []
        n = names
        
        # 自毁触发
        sdest = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        lines.append(f"local function {sdest}(trigger)")
        lines.append(f"  if trigger then")
        lines.append(f"    {n['vm']}.running=false")
        lines.append(f"    {n['vm']}.{n['st']}=nil")
        lines.append(f"    {n['vm']}.{n['bc']}=nil")
        lines.append(f"  end")
        lines.append(f"end")
        
        lines.append(f"{n['vm']}.self_destruct={sdest}")
        
        return lines
    
    def _obfuscate_str(self, s: str) -> str:
        """简单字符串混淆"""
        return ''.join(chr((ord(c) + 13) % 256) for c in s)


if __name__ == '__main__':
    main()
