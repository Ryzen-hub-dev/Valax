from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto


LUA_KEYWORDS = {
    "and",
    "break",
    "do",
    "else",
    "elseif",
    "end",
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
    "until",
    "while",
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
        self.decode_names = [random_lua_identifier(rng, "_dx") for _ in range(3)]
        self.fetch_names = [random_lua_identifier(rng, "_fx") for _ in range(3)]
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
        self.state_multipliers = [17 + (rng.randint(0, 59) * 2) for _ in range(3)]
        self.state_increments = [3 + rng.randint(0, 119) for _ in range(3)]
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
    rng = create_deterministic_random(source, watermark)
    profile = ProtectionProfile(rng, watermark)
    tokens = tokenize(source)
    rewrite_tokens(tokens, profile, rng)
    profile.finalize_pool_layout(rng)

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
    previous = previous_significant(tokens, index - 1)
    next_token = next_significant(tokens, index + 1)
    if previous is not None and (previous.is_symbol(".") or previous.is_symbol(":") or previous.is_keyword("goto")):
        return
    if previous is not None and previous.is_symbol("::"):
        return
    if next_token is not None and next_token.is_symbol("::"):
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
        else:
            out.append(f"  local {profile.mask_name}=(({profile.arg_b}~{profile.state_name})+{profile.arg_b})%256\n")
        out.append(
            f"  local {profile.byte_temp_name}=({profile.hex_pair_name}({profile.arg_a},{profile.index_name})-{profile.mask_name})%256\n"
        )
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
        encoded = (raw_byte + mask) % 256
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


def create_deterministic_random(source: str, watermark: str) -> random.Random:
    seed = 0x9E3779B97F4A7C15
    combined = watermark + "\0" + source
    for char in combined:
        seed ^= ord(char)
        seed = (seed * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return random.Random(seed)


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
