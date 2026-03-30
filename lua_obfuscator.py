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
    tokens = tokenize(source)
    rewrite_tokens(tokens, profile, rng)
    api_plan = apply_api_indirection(tokens, profile, rng)
    shuffle_tables(profile, rng)

    body_parts: list[str] = []
    previous: Token | None = None
    for token in tokens:
        if token.type in (TokenType.COMMENT, TokenType.WHITESPACE):
            continue
        if previous is not None and needs_space(previous, token):
            body_parts.append(" ")
        body_parts.append(token.rendered())
        previous = token

    return (
        "--[[\n"
        + "Lua Protector Watermark: "
        + sanitize_comment(watermark)
        + "\nGenerated by Python transformer\n"
        + "Protection profile: pooled literals + randomized runtime + lexer-aware minification\n"
        + "]]\n"
        + build_runtime_prelude(profile)
        + api_plan.prelude
        + "".join(body_parts)
        + "\n"
    )


def tokenize(source: str) -> list[Token]:
    tokenizer = Tokenizer(source)
    tokens: list[Token] = []
    while tokenizer.has_more():
        tokens.append(tokenizer.next_token())
    return tokens


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
