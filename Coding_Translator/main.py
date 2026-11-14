#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coding Translator
=================
Tradutor de lógica computacional + transpilador de código, 100% offline.

  • Aba 1 – Lógica: tradução entre Matemática Discreta / Portas Lógicas / Python / C-C++,
            tabela-verdade, classificação, simplificação (Quine-McCluskey), formas
            canônicas, árvore sintática e equivalência entre fórmulas.
  • Aba 2 – Código: transpilador real (sem API, sem internet) entre
            Python, JavaScript, Java, C#, C/C++ e Rust, baseado em uma
            representação intermediária (IR) com inferência de tipos.

Dependência única: pip install PySide6
"""

import sys
import re
import csv
import ast
import io
import time
import tokenize
import itertools
from pathlib import Path
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPlainTextEdit,
    QPushButton, QLabel, QFileDialog, QMessageBox, QSplitter, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QTextEdit, QAbstractItemView,
)
from PySide6.QtCore import Qt, QTimer, QRunnable, QThreadPool, QObject, Signal, QRect, QSize, QSettings
from PySide6.QtGui import (
    QKeySequence, QShortcut, QFont, QColor, QPainter, QTextFormat, QSyntaxHighlighter,
    QTextCharFormat, QTextCursor,
)

# ============================================================
# 1. CONFIGURAÇÕES E UNIVERSOS LÓGICOS
# ============================================================

APP_NAME = "Coding Translator"
MATH, GATES, PYTHON, CPP = "Matemática Discreta", "Portas Lógicas", "Python", "C/C++"
UNIVERSES = [MATH, GATES, PYTHON, CPP]
AUTO = "Auto-detectar"

OPERATORS = {"AND": 5, "NAND": 5, "XOR": 4, "XNOR": 4, "OR": 3, "NOR": 3, "IMPLIES": 2, "IFF": 1}

ALIASES = {
    "AND": "AND", "E": "AND", "OR": "OR", "OU": "OR", "XOR": "XOR",
    "NAND": "NAND", "NOR": "NOR", "XNOR": "XNOR", "NOT": "NOT", "NAO": "NOT", "NÃO": "NOT",
    "IMPLIES": "IMPLIES", "IMPLICA": "IMPLIES", "IFF": "IFF", "EQUIVALE": "IFF", "SSE": "IFF",
    "TRUE": "TRUE", "VERDADEIRO": "TRUE", "FALSE": "FALSE", "FALSO": "FALSE",
}

SYMBOL_ALIASES = {
    "∧": "AND", "∨": "OR", "⊕": "XOR", "¬": "NOT", "!": "NOT", "~": "NOT",
    "↑": "NAND", "↓": "NOR", "⊙": "XNOR", "→": "IMPLIES", "⇒": "IMPLIES",
    "↔": "IFF", "⇔": "IFF", "&&": "AND", "||": "OR", "^": "XOR",
    "==": "IFF", "=": "IFF", "!=": "XOR", "&": "AND", "|": "OR",
    "->": "IMPLIES", "=>": "IMPLIES", "<->": "IFF", "<=>": "IFF",
}

COMMON_FORMULAS = [
    ("Lei de De Morgan (AND)", "NOT (A AND B) IFF (NOT A OR NOT B)"),
    ("Lei de De Morgan (OR)", "NOT (A OR B) IFF (NOT A AND NOT B)"),
    ("Modus Ponens", "(P AND (P IMPLIES Q)) IMPLIES Q"),
    ("Modus Tollens", "((P IMPLIES Q) AND NOT Q) IMPLIES NOT P"),
    ("Silogismo Hipotético", "((P IMPLIES Q) AND (Q IMPLIES R)) IMPLIES (P IMPLIES R)"),
    ("Contrapositiva", "(P IMPLIES Q) IFF (NOT Q IMPLIES NOT P)"),
    ("Distributiva", "(A AND (B OR C)) IFF ((A AND B) OR (A AND C))"),
    ("Meio-somador (soma)", "A XOR B"),
    ("Multiplexador 2:1", "(S AND B) OR (NOT S AND A)"),
    ("Absorção", "A OR (A AND B)"),
]

MAX_TABLE_VARS = 10   # tabela-verdade / equivalência
MAX_QM_VARS = 8       # Quine-McCluskey

# ============================================================
# 2. ERROS E LEXER LÓGICO
# ============================================================

class LogicError(Exception):
    def __init__(self, msg, column=None):
        super().__init__(msg)
        self.column = column

class LexerError(LogicError): pass
class ParserError(LogicError): pass

@dataclass
class Token:
    type: str
    value: str
    position: int

TOKEN_PATTERN = re.compile(
    r"(?P<SPACE>\s+)|(?P<OP><=>|<->|->|=>|&&|\|\||==|!=|[∧∨⊕¬↑↓⊙→⇒↔⇔!~^=&|])|"
    r"(?P<LPAREN>\()|(?P<RPAREN>\))|(?P<NUMBER>\b[01]\b)|(?P<IDENT>[^\W\d]\w*)",
    re.UNICODE,
)

def tokenize_logic(expression, universe=None):
    """Converte texto em tokens. Em Matemática Discreta, T/F são constantes."""
    tokens, position = [], 0
    while position < len(expression):
        match = TOKEN_PATTERN.match(expression, position)
        if not match:
            raise LexerError(f"Caractere inválido '{expression[position]}' na posição {position + 1}.", position)
        kind, value = match.lastgroup, match.group()
        if kind == "OP":
            tokens.append(Token(SYMBOL_ALIASES[value], value, position))
        elif kind in ("LPAREN", "RPAREN"):
            tokens.append(Token(kind, value, position))
        elif kind == "NUMBER":
            tokens.append(Token("TRUE" if value == "1" else "FALSE", value, position))
        elif kind == "IDENT":
            up = value.upper()
            if universe == MATH and value in ("T", "F"):
                tokens.append(Token("TRUE" if value == "T" else "FALSE", value, position))
            elif up in ALIASES:
                tokens.append(Token(ALIASES[up], value, position))
            else:
                tokens.append(Token("VARIABLE", value, position))
        position = match.end()
    tokens.append(Token("EOF", "", len(expression)))
    return tokens

def detect_universe(text):
    """Heurística para descobrir o universo de origem."""
    if re.search(r"[∧∨⊕¬↑↓⊙→↔⇒⇔]", text):
        return MATH
    if re.search(r"&&|\|\||![A-Za-z(]|\b(true|false)\b", text):
        return CPP
    if re.search(r"\b(and|or|not)\b", text):
        return PYTHON
    return GATES

# ============================================================
# 3. AST E PARSER LÓGICO
# ============================================================

@dataclass
class Node:
    kind: str
    value: object = None
    left: object = None
    right: object = None

def make_variable(name): return Node("VARIABLE", value=name)
def make_constant(value): return Node("CONSTANT", value=value)
def make_unary(operator, operand): return Node("UNARY", value=operator, left=operand)
def make_binary(operator, left, right): return Node("BINARY", value=operator, left=left, right=right)

class LogicParser:
    def __init__(self, tokens):
        self.tokens, self.index = tokens, 0

    @property
    def current(self): return self.tokens[self.index]

    def advance(self):
        token = self.current
        self.index += 1
        return token

    def expect(self, token_type):
        if self.current.type != token_type:
            raise ParserError(f"Esperado '{token_type}' na posição {self.current.position + 1}.", self.current.position)
        return self.advance()

    def parse(self):
        if self.current.type == "EOF":
            raise ParserError("Expressão vazia.", 0)
        result = self.parse_expression()
        if self.current.type != "EOF":
            raise ParserError(f"Token inesperado '{self.current.value}' na posição {self.current.position + 1}.",
                              self.current.position)
        return result

    def parse_expression(self, min_precedence=0):
        left = self.parse_prefix()
        while self.current.type in OPERATORS:
            operator = self.current.type
            precedence = OPERATORS[operator]
            if precedence < min_precedence:
                break
            self.advance()
            next_precedence = precedence if operator == "IMPLIES" else precedence + 1
            left = make_binary(operator, left, self.parse_expression(next_precedence))
        return left

    def parse_prefix(self):
        token = self.current
        if token.type == "NOT":
            self.advance()
            return make_unary("NOT", self.parse_prefix())
        if token.type == "LPAREN":
            self.advance()
            expression = self.parse_expression()
            self.expect("RPAREN")
            return expression
        if token.type == "VARIABLE":
            return make_variable(self.advance().value)
        if token.type in ("TRUE", "FALSE"):
            return make_constant(self.advance().type == "TRUE")
        raise ParserError(f"Expressão inesperada '{token.value or 'fim'}' na posição {token.position + 1}.",
                          token.position)

# ============================================================
# 4. GERADOR, AVALIADOR E ANALISADOR LÓGICO
# ============================================================

SYM = {
    "AND": {MATH: "∧", GATES: "AND", PYTHON: "and", CPP: "&&"},
    "OR": {MATH: "∨", GATES: "OR", PYTHON: "or", CPP: "||"},
    "XOR": {MATH: "⊕", GATES: "XOR", PYTHON: "^", CPP: "^"},
    "NAND": {MATH: "↑", GATES: "NAND"},
    "NOR": {MATH: "↓", GATES: "NOR"},
    "XNOR": {MATH: "⊙", GATES: "XNOR", PYTHON: "==", CPP: "=="},
    "IMPLIES": {MATH: "→", GATES: "IMPLIES"},
    "IFF": {MATH: "↔", GATES: "XNOR", PYTHON: "==", CPP: "=="},
}
NOT_SYM = {MATH: "¬", GATES: "NOT ", PYTHON: "not ", CPP: "!"}
CONST_SYM = {
    MATH: {True: "T", False: "F"}, GATES: {True: "1", False: "0"},
    PYTHON: {True: "True", False: "False"}, CPP: {True: "true", False: "false"},
}

def _render(node, u):
    """Retorna (texto, classe). Classe indica quando parênteses são necessários."""
    if node.kind == "VARIABLE":
        return node.value, "atom"
    if node.kind == "CONSTANT":
        return CONST_SYM[u][node.value], "atom"
    if node.kind == "UNARY":
        text, kind = _render(node.left, u)
        if kind not in ("atom", "unary"):
            text = f"({text})"
        return NOT_SYM[u] + text, ("unary" if u == PYTHON else "atom")
    op, l, r = node.value, node.left, node.right
    if u in (PYTHON, CPP):                      # operadores sem equivalente nativo
        if op == "NAND": return _render(make_unary("NOT", make_binary("AND", l, r)), u)
        if op == "NOR": return _render(make_unary("NOT", make_binary("OR", l, r)), u)
        if op == "IMPLIES": return _render(make_binary("OR", make_unary("NOT", l), r), u)
    lt, lk = _render(l, u)
    rt, rk = _render(r, u)
    if op == "AND":
        allowed, kind = {"atom", "and", "unary"}, "and"
    elif op == "OR":
        allowed, kind = {"atom", "or", "unary"}, "or"
    else:
        allowed, kind = {"atom"}, "other"
    if u != PYTHON:
        allowed = allowed | {"unary"}
    lt = lt if lk in allowed else f"({lt})"
    rt = rt if rk in allowed else f"({rt})"
    return f"{lt} {SYM[op][u]} {rt}", kind

def render_logic(node, universe):
    return _render(node, universe)[0]

def variables_of(node, acc=None):
    acc = [] if acc is None else acc
    if node.kind == "VARIABLE":
        if node.value not in acc:
            acc.append(node.value)
    else:
        if node.left is not None: variables_of(node.left, acc)
        if node.right is not None: variables_of(node.right, acc)
    return acc

def compile_node(node, idx):
    """Compila a AST em uma função rápida f(bits) -> bool."""
    k = node.kind
    if k == "VARIABLE":
        i = idx[node.value]
        return lambda v: v[i]
    if k == "CONSTANT":
        c = node.value
        return lambda v: c
    if k == "UNARY":
        f = compile_node(node.left, idx)
        return lambda v: not f(v)
    f, g, op = compile_node(node.left, idx), compile_node(node.right, idx), node.value
    table = {
        "AND": lambda v: f(v) and g(v), "OR": lambda v: f(v) or g(v),
        "XOR": lambda v: f(v) != g(v), "XNOR": lambda v: f(v) == g(v), "IFF": lambda v: f(v) == g(v),
        "NAND": lambda v: not (f(v) and g(v)), "NOR": lambda v: not (f(v) or g(v)),
        "IMPLIES": lambda v: (not f(v)) or g(v),
    }
    return table[op]

def subexpressions(node):
    """Subexpressões não triviais em pós-ordem (a raiz é sempre a última)."""
    seen, out = set(), []
    def walk(n):
        if n.left is not None: walk(n.left)
        if n.right is not None: walk(n.right)
        if n.kind in ("UNARY", "BINARY"):
            key = render_logic(n, MATH)
            if key not in seen:
                seen.add(key); out.append(n)
    walk(node)
    return out or [node]

@dataclass
class TruthTable:
    variables: list
    labels: list
    rows: list          # [(bits, results)]
    minterms: list
    result_index: int = -1

def truth_table(ast_node, max_vars=MAX_TABLE_VARS):
    names = variables_of(ast_node)
    if len(names) > max_vars:
        raise LogicError(f"Tabela-verdade limitada a {max_vars} variáveis (encontradas {len(names)}).")
    idx = {n: i for i, n in enumerate(names)}
    cols = subexpressions(ast_node)
    fns = [compile_node(c, idx) for c in cols]
    n = len(names)
    rows, minterms = [], []
    for bits in itertools.product((True, False), repeat=n):
        res = tuple(bool(f(bits)) for f in fns)
        rows.append((bits, res))
        if res[-1]:
            minterms.append(sum(1 << (n - 1 - j) for j, b in enumerate(bits) if b))
    return TruthTable(names, [render_logic(c, MATH) for c in cols], rows, sorted(minterms))

# ---------- Quine–McCluskey ----------

def quine_mccluskey(minterms, n):
    """Retorna implicantes como strings sobre {0,1,-} (MSB = primeira variável)."""
    if not minterms:
        return []
    if len(minterms) == 1 << n:
        return ["-" * n]
    terms = {(m, 0) for m in minterms}
    primes = set()
    while terms:
        used, new = set(), set()
        by_mask = {}
        for t in terms:
            by_mask.setdefault(t[1], []).append(t)
        for mask, group in by_mask.items():
            group.sort()
            for a, b in itertools.combinations(group, 2):
                diff = a[0] ^ b[0]
                if diff and diff & (diff - 1) == 0:
                    new.add((a[0] & ~diff, mask | diff))
                    used.add(a); used.add(b)
        primes |= terms - used
        terms = new
    primes = list(primes)
    def covers(p, m): return (m & ~p[1]) == p[0]
    remaining, chosen = set(minterms), []
    for m in list(remaining):                       # implicantes essenciais
        cands = [p for p in primes if covers(p, m)]
        if len(cands) == 1 and cands[0] not in chosen:
            chosen.append(cands[0])
    for p in chosen:
        remaining -= {m for m in remaining if covers(p, m)}
    while remaining:                                # cobertura gulosa
        best = max(primes, key=lambda p: sum(covers(p, m) for m in remaining))
        chosen.append(best)
        remaining -= {m for m in remaining if covers(best, m)}
    out = []
    for v, mask in chosen:
        out.append("".join("-" if (mask >> (n - 1 - j)) & 1 else str((v >> (n - 1 - j)) & 1) for j in range(n)))
    return sorted(out)

def _fold(op, items, empty):
    if not items:
        return make_constant(empty)
    node = items[0]
    for it in items[1:]:
        node = make_binary(op, node, it)
    return node

def sop_node(implicants, names, dual=False):
    """SOP (ou POS, se dual) a partir de implicantes."""
    terms = []
    for imp in implicants:
        lits = []
        for ch, name in zip(imp, names):
            if ch == "-": continue
            positive = (ch == "1") != dual
            lits.append(make_variable(name) if positive else make_unary("NOT", make_variable(name)))
        terms.append(_fold("OR" if dual else "AND", lits, dual is False))
    return _fold("AND" if dual else "OR", terms, dual)

def tree_text(node, prefix="", last=True, root=True):
    labels = {"AND": "∧", "OR": "∨", "XOR": "⊕", "NAND": "↑", "NOR": "↓", "XNOR": "⊙", "IMPLIES": "→", "IFF": "↔", "NOT": "¬"}
    if node.kind == "VARIABLE": label = node.value
    elif node.kind == "CONSTANT": label = "T" if node.value else "F"
    else: label = labels[node.value]
    line = label if root else f"{prefix}{'└─ ' if last else '├─ '}{label}"
    kids = [k for k in (node.left, node.right) if k is not None]
    child_prefix = "" if root else prefix + ("   " if last else "│  ")
    lines = [line]
    for i, k in enumerate(kids):
        lines += tree_text(k, child_prefix, i == len(kids) - 1, False)
    return lines if not root else "\n".join(lines)

@dataclass
class LogicLine:
    number: int
    source: str
    ast: object = None
    error: str = None
    column: int = None
    output: str = ""

@dataclass
class LogicResult:
    lines: list
    translated: str
    errors: list
    detected: str
    analysis: str
    elapsed_ms: float

class LogicEngine:
    @staticmethod
    def translate(expression, source, target):
        if not expression.strip():
            return ""
        ast_node = LogicParser(tokenize_logic(expression, source)).parse()
        return render_logic(ast_node, target)

    @staticmethod
    def parse_line(text, source):
        return LogicParser(tokenize_logic(text, source)).parse()

    @staticmethod
    def process(content, source, target):
        t0 = time.perf_counter()
        lines, outputs, errors, dets = [], [], [], []
        for i, raw in enumerate(content.splitlines(), 1):
            ll = LogicLine(i, raw)
            if raw.strip():
                line_u = detect_universe(raw) if source == AUTO else source
                dets.append(line_u)
                try:
                    ll.ast = LogicEngine.parse_line(raw, line_u)
                    ll.output = render_logic(ll.ast, target)
                except LogicError as e:
                    ll.error, ll.column = str(e), e.column
                    ll.output = f"[ERRO NA LINHA {i}: {e}]"
                    errors.append(f"Linha {i}: {e}")
            outputs.append(ll.output)
            lines.append(ll)
        detected = max(set(dets), key=dets.count) if dets else GATES if source == AUTO else source
        analysis = LogicEngine.analysis_text(lines, target)
        return LogicResult(lines, "\n".join(outputs), errors, detected, analysis,
                           (time.perf_counter() - t0) * 1000)

    @staticmethod
    def analysis_text(lines, target):
        parts, valid = [], [l for l in lines if l.ast is not None]
        for ll in valid:
            names = variables_of(ll.ast)
            parts.append(f"━━ Linha {ll.number} ━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append(f"Fórmula     : {render_logic(ll.ast, target)}")
            parts.append(f"Variáveis   : {', '.join(names) if names else '(nenhuma)'}  [{len(names)}]")
            if len(names) > MAX_TABLE_VARS:
                parts.append(f"(análise completa limitada a {MAX_TABLE_VARS} variáveis)\n")
                continue
            tt = truth_table(ll.ast)
            total, ones = len(tt.rows), len(tt.minterms)
            if ones == total: cls = "TAUTOLOGIA (sempre verdadeira)"
            elif ones == 0: cls = "CONTRADIÇÃO (sempre falsa)"
            else: cls = "CONTINGÊNCIA (depende dos valores)"
            parts.append(f"Classificação: {cls}  — {ones} de {total} linhas verdadeiras")
            if names and 0 < ones < total:
                zeros = sorted(set(range(total)) - set(tt.minterms))
                parts.append(f"Forma canônica: Σ m({', '.join(map(str, tt.minterms))})")
                parts.append(f"                Π M({', '.join(map(str, zeros))})")
                if len(names) <= MAX_QM_VARS:
                    sop = quine_mccluskey(tt.minterms, len(names))
                    pos = quine_mccluskey(zeros, len(names))
                    parts.append(f"Mínima (SOP) : {render_logic(sop_node(sop, names), target)}")
                    parts.append(f"Mínima (POS) : {render_logic(sop_node(pos, names, dual=True), target)}")
            parts.append("Árvore sintática:")
            parts.append("  " + tree_text(ll.ast).replace("\n", "\n  "))
            parts.append("")
        if len(valid) > 1:
            parts.append("━━ Equivalência entre linhas ━━━━━━━━━━━━━━━━━")
            shown = 0
            for a, b in itertools.combinations(valid[:12], 2):
                names = sorted(set(variables_of(a.ast)) | set(variables_of(b.ast)))
                if len(names) > MAX_TABLE_VARS:
                    continue
                idx = {n: i for i, n in enumerate(names)}
                fa, fb = compile_node(a.ast, idx), compile_node(b.ast, idx)
                counter = None
                for bits in itertools.product((True, False), repeat=len(names)):
                    if fa(bits) != fb(bits):
                        counter = bits; break
                if counter is None:
                    parts.append(f"Linha {a.number} ≡ Linha {b.number}   ✔ equivalentes")
                else:
                    ce = ", ".join(f"{n}={int(v)}" for n, v in zip(names, counter))
                    parts.append(f"Linha {a.number} ≢ Linha {b.number}   ✘ contra-exemplo: {ce}")
                shown += 1
            if not shown:
                parts.append("(nenhum par comparável)")
        if not parts:
            parts.append("Digite uma ou mais fórmulas para ver a análise.")
        return "\n".join(parts)

# ============================================================
# 5. TRANSPILADOR DE CÓDIGO – REPRESENTAÇÃO INTERMEDIÁRIA (IR)
# ============================================================

CODE_LANGS = ["Python", "JavaScript", "Java", "C#", "C/C++", "Rust"]
LANG_EXT = {"Python": ".py", "JavaScript": ".js", "Java": ".java", "C#": ".cs", "C/C++": ".cpp", "Rust": ".rs"}
EXT_LANG = {".py": "Python", ".js": "JavaScript", ".mjs": "JavaScript", ".java": "Java", ".cs": "C#",
            ".c": "C/C++", ".cpp": "C/C++", ".cc": "C/C++", ".h": "C/C++", ".hpp": "C/C++", ".rs": "Rust"}
BUILTINS = {"len", "abs", "min", "max", "sqrt", "pow", "floor", "ceil", "int", "float", "str", "input"}


class TranslateError(Exception):
    pass


class Unsupported(Exception):
    pass


class N:
    """Nó genérico da IR (expressões e comandos)."""
    def __init__(self, kind, **kw):
        self.kind = kind
        self.type = None
        self.comments = []
        self.__dict__.update(kw)


class Program:
    def __init__(self):
        self.funcs, self.globals, self.main_body, self.warnings = [], [], [], []
        self.python = False       # origem Python (atribuição cria variável)
        self.hoist = False        # heurística de globais (Python/JS)
        self.run_main = False


def walk_ir(x):
    if isinstance(x, N):
        yield x
        for v in x.__dict__.values():
            if isinstance(v, (N, list, tuple)):
                yield from walk_ir(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from walk_ir(v)


# ---------- utilidades de tipos e literais ----------

def norm(t):
    if not t or t in ("any", "auto"):
        return "int"
    if t.startswith("list:"):
        return "list:" + norm(t[5:])
    return t

def is_list(t): return bool(t) and t.startswith("list:")
def elem_of(t): return t[5:] if is_list(t) else "any"

def unify(a, b):
    if a in (None, "any", "auto"): return b if b else a
    if b in (None, "any", "auto"): return a
    if a == b: return a
    if {a, b} == {"int", "float"}: return "float"
    if {a, b} == {"int", "bool"}: return "int"
    if is_list(a) and is_list(b): return "list:" + unify(a[5:], b[5:])
    return a

def tt(n):
    """Tipo normalizado de um nó (void preservado)."""
    t = n.type
    return "void" if t == "void" else norm(t)

def mk_num(text):
    text = text.replace("_", "")
    if re.match(r"0[xX]", text):
        return N("num", v=str(int(text, 16)), type="int")
    is_float_suffix = bool(re.search(r"[fFdD]$", text))
    text = re.sub(r"(?:[iu](?:8|16|32|64|128|size)|f32|f64|[fFdDlLuU]+)$", "", text)
    if "." in text or "e" in text.lower() or is_float_suffix:
        if "." not in text and "e" not in text.lower():
            text += ".0"
        return N("num", v=text, type="float")
    return N("num", v=text, type="int")

def default_node(t):
    t = norm(t)
    if t == "float": return N("num", v="0.0", type="float")
    if t == "str": return N("str", v="", type="str")
    if t == "bool": return N("bool", v=False, type="bool")
    if is_list(t): return N("list", items=[], type=t)
    return N("num", v="0", type="int")

_ESC = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", '"': '"', "'": "'"}

def unescape(s):
    return re.sub(r"\\(.)", lambda m: _ESC.get(m.group(1), m.group(0)), s, flags=re.S)

def quote(s, q='"'):
    out = (s.replace("\\", "\\\\").replace(q, "\\" + q).replace("\n", "\\n")
            .replace("\t", "\\t").replace("\r", "\\r").replace("\0", "\\0"))
    return q + out + q

def root_name(n):
    while n is not None and n.kind == "index":
        n = n.obj
    return n.v if n is not None and n.kind == "name" else None


# ============================================================
# 6. PARSER PYTHON (usa o módulo ast da biblioteca padrão)
# ============================================================

_PY_BINOPS = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "//", ast.Mod: "%",
              ast.Pow: "**", ast.BitAnd: "&", ast.BitOr: "|", ast.BitXor: "^", ast.LShift: "<<", ast.RShift: ">>"}
_PY_CMP = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">="}
_PY_MATH = {"sqrt": "sqrt", "floor": "floor", "ceil": "ceil", "pow": "pow", "fabs": "abs"}
_PY_UNSUPPORTED_BUILTINS = {"sorted", "sum", "enumerate", "zip", "list", "dict", "set", "tuple", "map",
                            "filter", "round", "reversed", "any", "all", "open", "isinstance", "type", "range"}


class PyParser:
    def __init__(self, code):
        self.code, self.lines = code, code.splitlines()
        self.prog = Program()
        self.prog.python = True
        self.prog.hoist = True
        self.comments, self.ci = self._collect_comments(), 0

    def _collect_comments(self):
        out = []
        try:
            for tok in tokenize.generate_tokens(io.StringIO(self.code).readline):
                if tok.type == tokenize.COMMENT and tok.line.strip().startswith("#"):
                    out.append((tok.start[0], tok.string.lstrip("#").strip()))
        except (tokenize.TokenError, IndentationError, SyntaxError):
            pass
        return out

    def take_comments(self, upto_line):
        res = []
        while self.ci < len(self.comments) and self.comments[self.ci][0] < upto_line:
            res.append(self.comments[self.ci][1])
            self.ci += 1
        return res

    def parse(self):
        try:
            tree = ast.parse(self.code)
        except SyntaxError as e:
            raise TranslateError(f"Erro de sintaxe em Python (linha {e.lineno}): {e.msg}")
        p = self.prog
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                cm = self.take_comments(node.lineno)
                try:
                    f = self.func(node)
                    f.comments = cm
                    p.funcs.append(f)
                except Unsupported as e:
                    p.warnings.append(f"Linha {node.lineno}: {e}")
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                self.take_comments(node.lineno)
            elif isinstance(node, ast.If) and self._is_main_guard(node):
                for s in node.body:
                    p.main_body += self.stmt_safe(s)
            else:
                p.main_body += self.stmt_safe(node)
        return p

    @staticmethod
    def _is_main_guard(n):
        t = n.test
        return (isinstance(t, ast.Compare) and isinstance(t.left, ast.Name) and t.left.id == "__name__")

    # ----- comandos -----
    def stmt_safe(self, node):
        cm = self.take_comments(node.lineno)
        try:
            out = self.stmt(node)
        except Unsupported as e:
            self.prog.warnings.append(f"Linha {node.lineno}: {e}")
            src = self.lines[node.lineno - 1].strip() if node.lineno <= len(self.lines) else ""
            out = [N("comment", lines=[f"TODO (linha {node.lineno}) – não traduzido: {e}", src])]
        if cm:
            if out: out[0].comments = cm + out[0].comments
            else: out = [N("comment", lines=cm)]
        return out

    def body(self, stmts):
        out = []
        for s in stmts:
            out += self.stmt_safe(s)
        return out

    def ann(self, a):
        if isinstance(a, ast.Name):
            return {"int": "int", "float": "float", "str": "str", "bool": "bool"}.get(a.id)
        if isinstance(a, ast.Constant) and a.value is None:
            return "void"
        if isinstance(a, ast.Subscript) and isinstance(a.value, ast.Name) and a.value.id in ("list", "List"):
            e = self.ann(a.slice)
            return "list:" + e if e else None
        return None

    def func(self, n):
        a = n.args
        if a.vararg or a.kwarg or a.kwonlyargs:
            raise Unsupported(f"função '{n.name}' com *args/**kwargs")
        if a.defaults:
            self.prog.warnings.append(f"Função '{n.name}': valores padrão de parâmetros foram ignorados.")
        params = [N("param", name=x.arg, type=self.ann(x.annotation) if x.annotation else None, mutated=False, assigned=False)
                  for x in a.args]
        ret = self.ann(n.returns) if n.returns else None
        return N("func", name=n.name, params=params, ret=ret, body=self.body(n.body))

    def assign(self, target, value, htype=None):
        if isinstance(target, ast.Name):
            return N("assign", target=N("name", v=target.id), op="=", value=self.expr(value), htype=htype)
        if isinstance(target, ast.Subscript):
            return N("assign", target=self.expr(target), op="=", value=self.expr(value), htype=None)
        raise Unsupported("alvo de atribuição não suportado")

    def stmt(self, n):
        if isinstance(n, ast.Assign):
            if len(n.targets) != 1:
                raise Unsupported("atribuição encadeada (a = b = c)")
            t = n.targets[0]
            if isinstance(t, ast.Tuple):
                if (isinstance(n.value, ast.Tuple) and len(t.elts) == len(n.value.elts)
                        and all(isinstance(e, ast.Name) for e in t.elts)):
                    out = [N("assign", target=N("name", v=f"_t{i}"), op="=", value=self.expr(v), htype=None)
                           for i, v in enumerate(n.value.elts)]
                    out += [N("assign", target=N("name", v=e.id), op="=", value=N("name", v=f"_t{i}"), htype=None)
                            for i, e in enumerate(t.elts)]
                    return out
                raise Unsupported("desempacotamento de tuplas")
            return [self.assign(t, n.value)]
        if isinstance(n, ast.AnnAssign):
            ht = self.ann(n.annotation)
            if n.value is None:
                return [N("decl", name=n.target.id, vtype=ht, value=None, mutable=False)]
            return [self.assign(n.target, n.value, ht)]
        if isinstance(n, ast.AugAssign):
            op = _PY_BINOPS.get(type(n.op))
            if op is None: raise Unsupported("operador aumentado não suportado")
            if not isinstance(n.target, (ast.Name, ast.Subscript)): raise Unsupported("alvo de atribuição aumentada")
            if op in ("+", "-", "*", "%"):
                return [N("assign", target=self.expr(n.target), op=op + "=", value=self.expr(n.value), htype=None)]
            val = N("bin", op=op, l=self.expr(n.target), r=self.expr(n.value))
            return [N("assign", target=self.expr(n.target), op="=", value=val, htype=None)]
        if isinstance(n, ast.Expr):
            v = n.value
            if isinstance(v, ast.Constant):
                return []
            if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "print":
                return [self.print_stmt(v)]
            return [N("expr", e=self.expr(v))]
        if isinstance(n, ast.If):
            return [N("if", cond=self.expr(n.test), body=self.body(n.body), orelse=self.body(n.orelse))]
        if isinstance(n, ast.While):
            if n.orelse: self.prog.warnings.append(f"Linha {n.lineno}: 'else' de while ignorado.")
            return [N("while", cond=self.expr(n.test), body=self.body(n.body))]
        if isinstance(n, ast.For):
            if not isinstance(n.target, ast.Name):
                raise Unsupported("for com desempacotamento (ex.: enumerate/zip)")
            it = n.iter
            if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range":
                a = [self.expr(x) for x in it.args]
                if not 1 <= len(a) <= 3: raise Unsupported("range() inválido")
                start, stop = (N("num", v="0", type="int"), a[0]) if len(a) == 1 else (a[0], a[1])
                step = a[2] if len(a) == 3 else None
                return [N("for_range", var=n.target.id, start=start, stop=stop, step=step, body=self.body(n.body))]
            return [N("for_each", var=n.target.id, iter=self.expr(it), body=self.body(n.body))]
        if isinstance(n, ast.Return):
            return [N("ret", value=self.expr(n.value) if n.value else None)]
        if isinstance(n, ast.Break): return [N("brk")]
        if isinstance(n, ast.Continue): return [N("cont")]
        if isinstance(n, ast.Pass): return []
        raise Unsupported(f"comando '{type(n).__name__}' sem suporte")

    def print_stmt(self, v):
        nl, sep = True, " "
        for kw in v.keywords:
            if kw.arg == "end" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                if kw.value.value == "": nl = False
                elif kw.value.value != "\n": raise Unsupported("print(end=...) com valor personalizado")
            elif kw.arg == "sep" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                sep = kw.value.value
            else:
                raise Unsupported(f"print({kw.arg}=...)")
        args = [self.expr(a) for a in v.args]
        if sep != " " and len(args) > 1:
            parts = []
            for i, a in enumerate(args):
                if i: parts.append(sep)
                parts.append(a)
            args = [N("fstr", parts=parts)]
        return N("print", args=args, nl=nl)

    # ----- expressões -----
    def expr(self, n):
        if isinstance(n, ast.Constant):
            v = n.value
            if isinstance(v, bool): return N("bool", v=v, type="bool")
            if isinstance(v, int): return N("num", v=str(v), type="int")
            if isinstance(v, float): return N("num", v=repr(v), type="float")
            if isinstance(v, str): return N("str", v=v, type="str")
            if v is None: return N("null")
            raise Unsupported("literal não suportado")
        if isinstance(n, ast.Name):
            return N("name", v=n.id)
        if isinstance(n, ast.BinOp):
            op = _PY_BINOPS.get(type(n.op))
            if op is None: raise Unsupported("operador binário não suportado")
            if op == "*":
                for a, b in ((n.left, n.right), (n.right, n.left)):
                    if isinstance(a, ast.List) and len(a.elts) == 1:
                        return N("newlist", value=self.expr(a.elts[0]), size=self.expr(b))
            return N("bin", op=op, l=self.expr(n.left), r=self.expr(n.right))
        if isinstance(n, ast.UnaryOp):
            x = self.expr(n.operand)
            if isinstance(n.op, ast.Not): return N("un", op="not", x=x)
            if isinstance(n.op, ast.USub):
                if x.kind == "num" and not x.v.startswith("-"):
                    return N("num", v="-" + x.v, type=x.type)
                return N("un", op="-", x=x)
            if isinstance(n.op, ast.UAdd): return x
            return N("un", op="~", x=x)
        if isinstance(n, ast.BoolOp):
            op = "and" if isinstance(n.op, ast.And) else "or"
            vals = [self.expr(v) for v in n.values]
            node = vals[0]
            for v in vals[1:]:
                node = N("bin", op=op, l=node, r=v)
            return node
        if isinstance(n, ast.Compare):
            parts, left = [], n.left
            for op, right in zip(n.ops, n.comparators):
                o = _PY_CMP.get(type(op))
                if o is None: raise Unsupported("operador 'in'/'is' não suportado")
                parts.append(N("bin", op=o, l=self.expr(left), r=self.expr(right)))
                left = right
            node = parts[0]
            for p in parts[1:]:
                node = N("bin", op="and", l=node, r=p)
            return node
        if isinstance(n, ast.Call): return self.call(n)
        if isinstance(n, ast.Attribute):
            if isinstance(n.value, ast.Name) and n.value.id == "math" and n.attr in ("pi", "e"):
                return N("num", v="3.141592653589793" if n.attr == "pi" else "2.718281828459045", type="float")
            raise Unsupported(f"atributo '.{n.attr}'")
        if isinstance(n, ast.Subscript):
            if isinstance(n.slice, ast.Slice): raise Unsupported("fatiamento (slice)")
            return N("index", obj=self.expr(n.value), idx=self.expr(n.slice))
        if isinstance(n, ast.List):
            return N("list", items=[self.expr(e) for e in n.elts])
        if isinstance(n, ast.JoinedStr):
            parts = []
            for v in n.values:
                if isinstance(v, ast.Constant):
                    parts.append(str(v.value))
                else:
                    e = self.expr(v.value)
                    spec = v.format_spec
                    if spec is not None:
                        s = "".join(str(x.value) for x in spec.values if isinstance(x, ast.Constant))
                        m = re.fullmatch(r"\.(\d+)f", s)
                        if m: e = N("fixed", x=e, digits=int(m.group(1)))
                        else: self.prog.warnings.append(f"Formatação ':{s}' em f-string foi ignorada.")
                    parts.append(e)
            return N("fstr", parts=parts)
        if isinstance(n, ast.IfExp):
            return N("tern", c=self.expr(n.test), a=self.expr(n.body), b=self.expr(n.orelse))
        raise Unsupported(f"expressão '{type(n).__name__}' sem suporte")

    def call(self, n):
        if n.keywords: raise Unsupported("argumentos nomeados")
        args = [self.expr(a) for a in n.args]
        f = n.func
        if isinstance(f, ast.Name):
            if f.id in _PY_UNSUPPORTED_BUILTINS: raise Unsupported(f"função embutida '{f.id}()'")
            if f.id == "print": raise Unsupported("print() dentro de expressão")
            return N("call", f=f.id, args=args)
        if isinstance(f, ast.Attribute):
            if isinstance(f.value, ast.Name) and f.value.id == "math":
                if f.attr in _PY_MATH: return N("call", f=_PY_MATH[f.attr], args=args)
                raise Unsupported(f"math.{f.attr}()")
            if f.attr in ("append", "sort", "upper", "lower"):
                return N("method", obj=self.expr(f.value), name=f.attr, args=args)
            raise Unsupported(f"método '.{f.attr}()'")
        raise Unsupported("chamada de função complexa")


# ============================================================
# 7. PARSER PARA LINGUAGENS DE SINTAXE C (JS, Java, C#, C/C++, Rust)
# ============================================================

CL_TOKEN = re.compile(r'''
 (?P<ws>\s+)
|(?P<lcom>//[^\n]*)
|(?P<bcom>/\*.*?\*/)
|(?P<pre>\#[^\n]*)
|(?P<tpl>`(?:\\.|[^`\\])*`)
|(?P<istr>\$"(?:\\.|[^"\\\n])*")
|(?P<str>"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*')
|(?P<num>0[xX][0-9a-fA-F]+|\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d+)?(?:f32|f64|[fFdD])?|\d[\d_]*[eE][+-]?\d+|\d[\d_]*(?:[iu](?:8|16|32|64|128|size)|f32|f64|[uUlL]+|[fFdD])?)
|(?P<id>[A-Za-z_]\w*)
|(?P<op>\.\.=|\.\.|===|!==|<<=|\+\+|--|->|=>|::|==|!=|<=|>=|&&|\|\||<<|\+=|-=|\*=|/=|%=|[-+*/%=<>!&|^~?:;,.(){}\[\]@])
''', re.X | re.S)


class Tok:
    __slots__ = ("kind", "text", "line", "pos")
    def __init__(self, kind, text, line, pos):
        self.kind, self.text, self.line, self.pos = kind, text, line, pos


def cl_tokenize(code):
    toks, comments, pos, line = [], [], 0, 1
    while pos < len(code):
        m = CL_TOKEN.match(code, pos)
        if not m:
            raise TranslateError(f"Caractere inválido '{code[pos]}' na linha {line}.")
        kind, text = m.lastgroup, m.group()
        if kind == "lcom":
            comments.append((len(toks), [text[2:].strip()]))
        elif kind == "bcom":
            comments.append((len(toks), [ln.strip(" *\t") for ln in text[2:-2].strip().splitlines()]))
        elif kind not in ("ws", "pre"):
            toks.append(Tok(kind, text, line, pos))
        line += text.count("\n")
        pos = m.end()
    toks.append(Tok("eof", "", line, pos))
    return toks, comments


INT_T = {"int", "long", "short", "byte", "sbyte", "uint", "ulong", "ushort", "size_t", "ssize_t", "Integer", "Long",
         "Short", "Byte", "i8", "i16", "i32", "i64", "i128", "isize", "u8", "u16", "u32", "u64", "u128", "usize",
         "int8_t", "int16_t", "int32_t", "int64_t", "uint8_t", "uint16_t", "uint32_t", "uint64_t"}
FLOAT_T = {"float", "double", "Double", "Float", "decimal", "f32", "f64"}
STR_T = {"string", "String", "str", "char", "Character", "Char"}
BOOL_T = {"bool", "boolean", "Boolean"}
LIST_T = {"vector", "List", "ArrayList", "Vec", "list", "LinkedList", "IList", "Array"}
TYPE_MODS = {"const", "static", "final", "readonly", "volatile", "public", "private", "protected", "abstract",
             "virtual", "override", "inline", "extern", "internal", "sealed", "pub", "unsafe", "async"}
NOT_TYPE = {"return", "if", "else", "while", "for", "break", "continue", "new", "throw", "case", "do", "switch",
            "delete", "goto", "typeof", "await", "yield", "let", "function", "fn", "foreach", "in"}
BINPREC = {"||": 1, "&&": 2, "|": 3, "^": 4, "&": 5, "==": 6, "!=": 6, "===": 6, "!==": 6,
           "<": 7, ">": 7, "<=": 7, ">=": 7, "<<": 8, ">>": 8, "+": 9, "-": 9, "*": 10, "/": 10, "%": 10}
ASSIGN_OPS = {"=", "+=", "-=", "*=", "/=", "%="}
LIB_CALLS = {"sqrt": "sqrt", "abs": "abs", "fabs": "abs", "pow": "pow", "floor": "floor", "ceil": "ceil",
             "max": "max", "min": "min", "stoi": "int", "atoi": "int", "stod": "float", "atof": "float",
             "to_string": "str", "parseint": "int", "parsefloat": "float", "parsedouble": "float",
             "valueof": "str", "toint32": "int", "todouble": "float", "tostring": "str"}
BARE_CALLS = set(LIB_CALLS) | {"int", "float", "double", "string", "str", "len", "input", "number", "prompt"}
LIB_ROOTS = {"math", "std", "integer", "double", "long", "float", "convert", "string", "number", "collections", "cmp"}
PRINT_PATHS = {"console.log": (True, "plain"), "System.out.println": (True, "plain"),
               "System.out.print": (False, "plain"), "Console.WriteLine": (True, "cs"),
               "Console.Write": (False, "cs"), "printf": (False, "c"), "System.out.printf": (False, "c"),
               "puts": (True, "plain")}
IDENTITY_METHODS = {"iter", "iter_mut", "into_iter", "clone", "cloned", "to_owned", "as_str", "unwrap", "collect", "begin", "end"}


class CLikeParser:
    def __init__(self, code, lang, shared=None):
        self.lang = lang                       # js | java | cs | cpp | rust
        self.toks, self.comments = cl_tokenize(code)
        self.i = self.ci = self.wrap = 0
        self.code_lines = code.splitlines()
        self.prog = shared or Program()
        self.prog.python = False
        self.prog.hoist = (lang == "js")
        self.turbofish = None

    # ----- utilidades de token -----
    def cur(self): return self.toks[self.i]
    def peek(self, k=1): return self.toks[min(self.i + k, len(self.toks) - 1)]

    def at(self, text):
        t = self.toks[self.i]
        return t.kind in ("op", "id") and t.text == text

    def accept(self, text):
        if self.at(text):
            self.i += 1
            return True
        return False

    def expect(self, text):
        if not self.accept(text):
            t = self.cur()
            raise Unsupported(f"esperado '{text}' na linha {t.line}, encontrado '{t.text or 'fim do arquivo'}'")

    def ident(self):
        t = self.cur()
        if t.kind != "id":
            raise Unsupported(f"identificador esperado na linha {t.line}")
        self.i += 1
        return t.text

    def take_comments(self):
        res = []
        while self.ci < len(self.comments) and self.comments[self.ci][0] <= self.i:
            res += self.comments[self.ci][1]
            self.ci += 1
        return res

    def src_line(self, line):
        return self.code_lines[line - 1].strip() if 0 < line <= len(self.code_lines) else ""

    def match_paren(self, i):
        depth = 0
        while i < len(self.toks) and self.toks[i].kind != "eof":
            if self.toks[i].text == "(" and self.toks[i].kind == "op": depth += 1
            elif self.toks[i].text == ")" and self.toks[i].kind == "op":
                depth -= 1
                if depth == 0: return i
            i += 1
        return i

    def skip_statement(self):
        depth, start = 0, self.i
        while self.cur().kind != "eof":
            t = self.cur()
            if t.kind == "op":
                if t.text in "({[":
                    depth += 1
                elif t.text in ")}]":
                    if depth == 0:
                        return
                    depth -= 1
                    if depth == 0 and t.text == "}":
                        self.i += 1
                        return
                elif t.text == ";" and depth == 0:
                    self.i += 1
                    return
            self.i += 1

    def skip_line_stmt(self):
        line = self.cur().line
        while self.cur().kind != "eof" and not self.at(";") and self.cur().line == line:
            self.i += 1
        self.accept(";")

    # ----- tipos -----
    def map_type(self, base, args, dims):
        if dims:
            t = self.map_type(base, args, 0)
            for _ in range(dims): t = "list:" + t
            return t
        if base in INT_T: return "int"
        if base in FLOAT_T: return "float"
        if base in STR_T: return "str"
        if base in BOOL_T: return "bool"
        if base == "void": return "void"
        if base in ("auto", "var", "let"): return "auto"
        if base in LIST_T: return "list:" + (args[0] if args else "any")
        return "obj:" + base

    def parse_type(self):
        start, L = self.i, self.lang
        if L == "rust":
            while self.at("&") or self.at("&&") or self.at("mut"): self.i += 1
            if self.at("["):
                self.i += 1
                inner = self.parse_type()
                if inner is None: self.i = start; return None
                if self.accept(";"): self.expr()
                if not self.accept("]"): self.i = start; return None
                return "list:" + inner
        while self.cur().kind == "id" and self.cur().text in TYPE_MODS: self.i += 1
        t = self.cur()
        if t.kind != "id" or t.text in NOT_TYPE:
            self.i = start
            return None
        base = t.text
        self.i += 1
        if base in ("unsigned", "signed", "long", "short"):
            while self.cur().kind == "id" and self.cur().text in ("long", "int", "short", "char", "double", "unsigned", "signed"):
                if self.cur().text in ("double", "char"): base = self.cur().text
                self.i += 1
            if base in ("unsigned", "signed", "long", "short"): base = "int"
        while (self.at("::") or self.at(".")) and self.peek().kind == "id":
            base = self.peek().text
            self.i += 2
        args = []
        if self.at("<"):
            self.i += 1
            ok = True
            if not self.at(">"):
                while True:
                    a = self.parse_type()
                    if a is None: ok = False; break
                    args.append(a)
                    if self.accept(","): continue
                    break
            if ok and self.at(">"): self.i += 1
            else: ok = False
            if not ok:
                self.i = start
                return None
        dims = 0
        while self.at("[") and self.peek().text == "]":
            self.i += 2
            dims += 1
        while (self.lang == "cpp" and self.cur().kind == "op" and self.cur().text in ("*", "&", "&&")
               and (self.peek().kind == "id" or self.peek().text in ("*", "&"))):
            self.i += 1
        return self.map_type(base, args, dims)

    def try_decl(self, allow_paren=False):
        save = self.i
        t = self.parse_type()
        if t is None:
            self.i = save
            return None
        c, nx = self.cur(), self.peek()
        ok = {"=", ";", ",", "[", ":"}
        if allow_paren or self.lang == "cpp": ok.add("(")
        if c.kind == "id" and c.text not in NOT_TYPE and nx.text in ok and nx.kind in ("op", "id"):
            return t
        self.i = save
        return None

    # ----- topo do arquivo -----
    def parse(self):
        p = self.prog
        while self.cur().kind != "eof":
            before = self.i
            try:
                self.top_item()
            except Unsupported as e:
                line = self.toks[min(before, len(self.toks) - 1)].line
                p.warnings.append(f"Linha {line}: {e}")
                self.i = before
                self.skip_statement()
                p.main_body.append(N("comment", lines=[f"TODO (linha {line}) – não traduzido: {e}", self.src_line(line)]))
            if self.i == before:
                self.i += 1
        return p

    def top_item(self):
        L, p = self.lang, self.prog
        t = self.cur()
        if t.kind == "op" and t.text == "}" and self.wrap > 0:
            self.i += 1; self.wrap -= 1
            return
        if t.kind == "op" and t.text == ";":
            self.i += 1
            return
        if t.kind == "id" and t.text in ("import", "package", "use", "mod", "extern", "typedef") \
                or (t.kind == "id" and t.text == "using" and self.peek().text != "("):
            self.skip_line_stmt()
            return
        j = self.i
        while self.toks[j].kind == "id" and self.toks[j].text in TYPE_MODS and self.toks[j].text != "async":
            j += 1
        kw = self.toks[j].text if self.toks[j].kind == "id" else ""
        if kw in ("class", "struct", "interface", "enum", "namespace", "impl", "trait"):
            if kw in ("class", "namespace") and L in ("java", "cs", "cpp") or (kw == "namespace"):
                if kw == "class" and L == "cpp":
                    raise Unsupported("classes C++ (orientação a objetos) não são suportadas")
                while not self.at("{") and self.cur().kind != "eof": self.i += 1
                self.expect("{")
                self.wrap += 1
                return
            raise Unsupported(f"'{kw}' (orientação a objetos) não é suportado")
        cm = self.take_comments()
        if L == "js" and kw == "function":
            self.i = j + 1
            name = self.ident()
            params = self.params()
            self.add_func(name, params, None, self.block(), cm)
            return
        if L == "rust" and kw == "fn":
            self.i = j + 1
            name = self.ident()
            params = self.params()
            ret = self.parse_type() if self.accept("->") else "void"
            self.add_func(name, params, ret, self.block(), cm)
            return
        if L in ("java", "cs", "cpp"):
            save = self.i
            t0 = self.try_decl(allow_paren=True)
            if t0 is not None:
                if self.peek().text == "(" and self.toks[self.match_paren(self.i + 1) + 1].text in ("{", "const", "override"):
                    name = self.ident()
                    params = self.params()
                    while self.cur().kind == "id" and self.cur().text in ("const", "override"): self.i += 1
                    self.add_func(name, params, t0, self.block(), cm)
                    return
                decls = self.s_decl(t0)
                for d in decls:
                    d.comments = cm
                    p.globals.append(d)
                return
            self.i = save
        out = self.stmt()
        if cm and out: out[0].comments = cm + out[0].comments
        for s in out:
            if s.kind == "decl" and L in ("rust",):
                p.globals.append(s)
            else:
                p.main_body.append(s)

    def add_func(self, name, params, ret, body, cm):
        if ret == "auto": ret = None
        if name == "Main" and self.lang == "cs": name = "main"
        if name == "main":
            params, ret = [], "void"
            for n in walk_ir(body):
                if n.kind == "ret" and n.value is not None and n.value.kind == "num" and n.value.v == "0":
                    n.value = None
        if (self.lang == "rust" and ret not in (None, "void") and body and body[-1].kind == "expr"
                and getattr(body[-1], "tail", False)):
            body[-1] = N("ret", value=body[-1].e, comments=body[-1].comments)
        self.prog.funcs.append(N("func", name=name, params=params, ret=ret, body=body, comments=cm))

    def params(self):
        self.expect("(")
        out, L = [], self.lang
        while not self.at(")"):
            if self.cur().kind == "eof": raise Unsupported("lista de parâmetros não fechada")
            ptype = None
            if L == "js":
                if self.at("..."): raise Unsupported("parâmetros rest")
                name = self.ident()
                if self.accept("="):
                    self.expr()
                    self.prog.warnings.append(f"Parâmetro '{name}': valor padrão ignorado.")
            elif L == "rust":
                self.accept("mut")
                name = self.ident()
                if name == "self": raise Unsupported("métodos (self) não suportados")
                self.expect(":")
                ptype = self.parse_type()
            else:
                ptype = self.parse_type()
                if ptype is None: raise Unsupported(f"parâmetro inválido na linha {self.cur().line}")
                name = self.ident()
                while self.at("["):
                    self.i += 1
                    while not self.at("]") and self.cur().kind != "eof": self.i += 1
                    self.expect("]")
                    ptype = "list:" + ptype
                if self.accept("="): self.expr()
            if ptype and ptype.startswith("obj:"): raise Unsupported(f"tipo '{ptype[4:]}' não suportado")
            out.append(N("param", name=name, type=None if ptype in (None, "auto") else ptype, mutated=False, assigned=False))
            if not self.accept(","): break
        self.expect(")")
        return out

    # ----- comandos -----
    def stmt(self):
        cm = self.take_comments()
        start = self.i
        try:
            out = self.stmt_inner()
        except Unsupported as e:
            line = self.toks[min(start, len(self.toks) - 1)].line
            self.prog.warnings.append(f"Linha {line}: {e}")
            self.i = start
            self.skip_statement()
            out = [N("comment", lines=[f"TODO (linha {line}) – não traduzido: {e}", self.src_line(line)])]
        if cm:
            if out: out[0].comments = cm + out[0].comments
            else: out = [N("comment", lines=cm)]
        return out

    def body(self):
        return self.block() if self.at("{") else self.stmt()

    def block(self):
        self.expect("{")
        out = []
        while not self.at("}"):
            if self.cur().kind == "eof": raise Unsupported("bloco '{' não fechado")
            out += self.stmt()
        cm = self.take_comments()
        if cm: out.append(N("comment", lines=cm))
        self.i += 1
        return out

    def stmt_inner(self):
        t, L = self.cur(), self.lang
        if t.kind == "op" and t.text == "{": return self.block()
        if t.kind == "op" and t.text == ";":
            self.i += 1
            return []
        if t.kind == "id":
            w = t.text
            if w == "if": return self.s_if()
            if w == "while": return self.s_while()
            if w == "for": return self.s_for()
            if w == "foreach" and L == "cs": return self.s_foreach_cs()
            if w == "return":
                self.i += 1
                v = None if (self.at(";") or self.at("}")) else self.expr()
                self.accept(";")
                return [N("ret", value=v)]
            if w in ("break", "continue"):
                self.i += 1
                self.accept(";")
                return [N("brk" if w == "break" else "cont")]
            if w in ("do", "switch", "try", "throw", "class", "struct", "enum", "goto", "catch", "match"):
                raise Unsupported(f"'{w}' não é suportado")
            if L == "rust":
                if w in ("let", "const", "static"): return self.s_let()
                if w == "loop":
                    self.i += 1
                    return [N("while", cond=N("bool", v=True, type="bool"), body=self.block())]
                if w == "fn": raise Unsupported("funções aninhadas")
            if L == "js":
                if w in ("let", "const", "var"): return self.s_js_decl()
                if w == "function": raise Unsupported("funções aninhadas")
            if L in ("java", "cs", "cpp"):
                d = self.try_decl()
                if d is not None: return self.s_decl(d)
        return self.s_expr()

    def s_let(self):
        self.i += 1
        mut = self.accept("mut")
        name = self.ident()
        vt = self.parse_type() if self.accept(":") else None
        value = self.expr() if self.accept("=") else None
        self.accept(";")
        if vt and vt.startswith("obj:"): raise Unsupported(f"tipo '{vt[4:]}' não suportado")
        if value is None and vt and is_list(vt): value = N("list", items=[])
        return [N("decl", name=name, vtype=None if vt == "auto" else vt, value=value, mutable=mut)]

    def s_js_decl(self):
        self.i += 1
        out = []
        while True:
            name = self.ident()
            value = self.expr() if self.accept("=") else None
            out.append(N("decl", name=name, vtype=None, value=value, mutable=False))
            if not self.accept(","): break
        self.accept(";")
        return out

    def init_expr(self, vt, size):
        if self.at("{"):
            items = self.brace_items()
            if size is not None and len(items) == 1:
                return N("newlist", value=items[0], size=size)
            return N("list", items=items)
        return self.expr()

    def brace_items(self):
        self.expect("{")
        items = []
        while not self.at("}"):
            items.append(self.expr())
            if not self.accept(","): break
        self.expect("}")
        return items

    def s_decl(self, t, need_semi=True):
        out = []
        while True:
            name = self.ident()
            vt, size = t, None
            while self.at("["):
                self.i += 1
                if self.at("]"): self.i += 1
                else:
                    size = self.expr()
                    self.expect("]")
                vt = "list:" + vt
            value = None
            if self.accept("="):
                value = self.init_expr(vt, size)
            elif self.at("(") and self.lang == "cpp":
                args = self.args()
                if is_list(vt):
                    if len(args) == 2: value = N("newlist", value=args[1], size=args[0])
                    elif len(args) == 1: value = N("newlist", value=default_node(elem_of(vt)), size=args[0])
                elif args:
                    value = args[0]
            elif size is not None:
                value = N("newlist", value=default_node(elem_of(vt)), size=size)
            if vt.startswith("obj:"): raise Unsupported(f"tipo '{vt[4:]}' não suportado")
            if value is None and is_list(vt): value = N("list", items=[])
            out.append(N("decl", name=name, vtype=None if vt == "auto" else vt, value=value, mutable=False))
            if not self.accept(","): break
        if need_semi: self.expect(";")
        return out

    def s_if(self):
        self.i += 1
        if self.lang == "rust":
            cond = self.expr()
        else:
            self.expect("(")
            cond = self.expr()
            self.expect(")")
        body, orelse = self.body(), []
        if self.accept("else"):
            orelse = self.s_if() if self.at("if") else self.body()
        return [N("if", cond=cond, body=body, orelse=orelse)]

    def s_while(self):
        self.i += 1
        if self.lang == "rust":
            cond = self.expr()
        else:
            self.expect("(")
            cond = self.expr()
            self.expect(")")
        return [N("while", cond=cond, body=self.body())]

    def s_foreach_cs(self):
        self.i += 1
        self.expect("(")
        t = self.parse_type()
        name = self.ident()
        self.expect("in")
        it = self.expr()
        self.expect(")")
        return [N("for_each", var=name, iter=it, body=self.body())]

    def s_for(self):
        self.i += 1
        L = self.lang
        if L == "rust":
            var = self.ident()
            self.expect("in")
            it = self.expr()
            body = self.block()
            if it.kind == "range": return [self.range_loop(var, it, body)]
            return [N("for_each", var=var, iter=it, body=body)]
        self.expect("(")
        save = self.i
        if L == "js" and self.cur().text in ("const", "let", "var") and self.peek().kind == "id" and self.peek(2).text == "of":
            self.i += 1
            var = self.ident()
            self.i += 1
            it = self.expr()
            self.expect(")")
            return [N("for_each", var=var, iter=it, body=self.body())]
        if L in ("java", "cpp"):
            t = self.try_decl()
            if t is not None and self.peek().text == ":":
                var = self.ident()
                self.i += 1
                it = self.expr()
                self.expect(")")
                return [N("for_each", var=var, iter=it, body=self.body())]
            self.i = save
        init = []
        if not self.at(";"):
            if L == "js" and self.cur().text in ("let", "const", "var"):
                self.i += 1
                init = self.s_decl_js_nosemi()
            else:
                d = self.try_decl() if L != "js" else None
                init = self.s_decl(d, need_semi=False) if d is not None else self.s_expr(need_semi=False)
        self.expect(";")
        cond = N("bool", v=True, type="bool") if self.at(";") else self.expr()
        self.expect(";")
        upd = []
        while not self.at(")"):
            upd += self.s_expr(need_semi=False)
            if not self.accept(","): break
        self.expect(")")
        body = self.body()
        loop = self.try_for_range(init, cond, upd, body)
        if loop is not None: return [loop]
        if any(n.kind == "cont" for n in walk_ir(body)):
            self.prog.warnings.append("Um 'for' com 'continue' foi convertido para 'while'; confira o incremento.")
        return init + [N("while", cond=cond, body=body + upd)]

    def s_decl_js_nosemi(self):
        out = []
        while True:
            name = self.ident()
            value = self.expr() if self.accept("=") else None
            out.append(N("decl", name=name, vtype=None, value=value, mutable=True))
            if not self.accept(","): break
        return out

    @staticmethod
    def _shift(n, delta):
        if n.kind == "num" and n.type == "int":
            return N("num", v=str(int(n.v) + delta), type="int")
        return N("bin", op="+" if delta > 0 else "-", l=n, r=N("num", v=str(abs(delta)), type="int"))

    def range_loop(self, var, r, body):
        stop = self._shift(r.hi, 1) if r.incl else r.hi
        return N("for_range", var=var, start=r.lo, stop=stop, step=r.step, body=body)

    def try_for_range(self, init, cond, upd, body):
        if len(init) != 1 or init[0].kind != "decl" or init[0].value is None or len(upd) != 1:
            return None
        var, u = init[0].name, upd[0]
        if not (cond.kind == "bin" and cond.l.kind == "name" and cond.l.v == var and cond.op in ("<", "<=", ">", ">=")):
            return None
        if not (u.kind == "assign" and u.target.kind == "name" and u.target.v == var and u.op in ("+=", "-=")
                and u.value.kind == "num" and u.value.type == "int"):
            return None
        up = u.op == "+="
        if up != (cond.op in ("<", "<=")): return None
        if cond.op == "<=": stop = self._shift(cond.r, 1)
        elif cond.op == ">=": stop = self._shift(cond.r, -1)
        else: stop = cond.r
        k = u.value.v
        step = None if (up and k == "1") else N("num", v=k if up else "-" + k, type="int")
        return N("for_range", var=var, start=init[0].value, stop=stop, step=step, body=body)

    def s_expr(self, need_semi=True):
        t, L = self.cur(), self.lang
        one = N("num", v="1", type="int")
        if t.kind == "op" and t.text in ("++", "--"):
            self.i += 1
            node = N("assign", target=self.postfix(), op="+=" if t.text == "++" else "-=", value=one, htype=None)
        elif L == "cpp" and (self.at("cout") or (self.at("std") and self.peek(2).text == "cout")):
            node = self.s_cout()
        else:
            e = self.expr()
            c = self.cur()
            if c.kind == "op" and c.text in ASSIGN_OPS:
                if e.kind not in ("name", "index"): raise Unsupported("alvo de atribuição inválido")
                self.i += 1
                v = self.expr()
                if c.text == "/=":
                    node = N("assign", target=e, op="=", value=N("bin", op="cdiv" if L != "js" else "/", l=e, r=v), htype=None)
                else:
                    node = N("assign", target=e, op=c.text, value=v, htype=None)
            elif c.kind == "op" and c.text in ("++", "--"):
                if e.kind not in ("name", "index"): raise Unsupported("alvo de ++/-- inválido")
                self.i += 1
                node = N("assign", target=e, op="+=" if c.text == "++" else "-=", value=one, htype=None)
            elif e.kind == "call" and e.f == "__print":
                node = N("print", args=e.args, nl=e.nl)
            elif e.kind in ("call", "method"):
                node = N("expr", e=e)
            else:
                node = N("expr", e=e)
        if need_semi:
            if not self.accept(";"):
                if L == "rust" and self.at("}"): node.tail = True
                elif L != "js" and node.kind != "print" and not self.at("}"):
                    raise Unsupported(f"esperado ';' na linha {self.cur().line}")
        return [node] if node.kind != "expr" or node.e.kind in ("call", "method") or getattr(node, "tail", False) else []

    def s_cout(self):
        if self.at("std"): self.i += 2
        self.i += 1
        parts, nl = [], False
        while self.at("<<"):
            self.i += 1
            if self.at("endl") or (self.at("std") and self.peek(2).text == "endl"):
                self.i += 3 if self.at("std") else 1
                nl = True
                continue
            e = self.binary(9)
            if e.kind == "call" and e.f in ("setprecision", "setw", "fixed", "boolalpha"):
                raise Unsupported(f"manipulador de saída '{e.f}'")
            if e.kind == "name" and e.v in ("fixed", "boolalpha", "left", "right"):
                raise Unsupported(f"manipulador de saída '{e.v}'")
            parts.append(e)
        if parts and parts[-1].kind == "str" and parts[-1].v.endswith("\n"):
            nl = True
            parts[-1] = N("str", v=parts[-1].v[:-1], type="str")
            if parts[-1].v == "": parts.pop()
        args = [parts[0]] if len(parts) == 1 else [N("fstr", parts=[p.v if p.kind == "str" else p for p in parts])]
        return N("print", args=args if parts else [], nl=nl)

    # ----- expressões -----
    def args(self):
        self.expect("(")
        out = []
        while not self.at(")"):
            out.append(self.expr())
            if not self.accept(","): break
        self.expect(")")
        return out

    def expr(self):
        c = self.binary(1)
        if self.at("?"):
            self.i += 1
            a = self.expr()
            self.expect(":")
            return N("tern", c=c, a=a, b=self.expr())
        if self.lang == "rust" and (self.at("..") or self.at("..=")):
            incl = self.cur().text == "..="
            self.i += 1
            return N("range", lo=c, hi=self.binary(1), incl=incl, step=None)
        return c

    def binop(self):
        t = self.cur()
        if t.kind != "op": return None
        if t.text == ">" and self.peek().text == ">" and self.peek().pos == t.pos + 1:
            return ">>", 2
        if t.text in BINPREC: return t.text, 1
        return None

    def binary(self, minp):
        left = self.unary()
        while True:
            b = self.binop()
            if b is None: break
            op, n = b
            prec = BINPREC[op]
            if prec < minp: break
            self.i += n
            right = self.binary(prec + 1)
            op = {"===": "==", "!==": "!=", "&&": "and", "||": "or"}.get(op, op)
            if op == "/" and self.lang != "js": op = "cdiv"
            left = N("bin", op=op, l=left, r=right)
        return left

    def unary(self):
        t = self.cur()
        if t.kind == "op":
            if t.text in ("!", "-", "+", "~"):
                self.i += 1
                x = self.unary()
                if t.text == "!": return N("un", op="not", x=x)
                if t.text == "-":
                    if x.kind == "num" and not x.v.startswith("-"):
                        return N("num", v="-" + x.v, type=x.type)
                    return N("un", op="-", x=x)
                return x if t.text == "+" else N("un", op="~", x=x)
            if self.lang == "rust" and t.text in ("&", "&&", "*"):
                self.i += 1
                self.accept("mut")
                return self.unary()
            if t.text in ("++", "--"):
                raise Unsupported("++/-- dentro de expressões")
        return self.postfix()

    def postfix(self):
        e = self.primary()
        while True:
            if self.at(".") or (self.at("::") and self.peek().kind == "id"):
                self.i += 1
                e = N("attr", obj=e, name=self.ident())
            elif self.at("::") and self.peek().text == "<":
                self.i += 2
                self.turbofish = self.parse_type()
                self.expect(">")
            elif self.at("("):
                e = self.make_call(e, self.args())
            elif self.at("["):
                self.i += 1
                idx = self.expr()
                self.expect("]")
                if e.kind == "attr": e = self.make_prop(e)
                e = N("index", obj=e, idx=idx)
            elif self.lang == "rust" and self.at("as"):
                self.i += 1
                t = self.parse_type()
                e = N("call", f={"float": "float", "int": "int", "bool": "int"}.get(t, "int"), args=[e])
            else:
                break
        if e.kind == "attr": e = self.make_prop(e)
        return e

    def primary(self):
        t, L = self.cur(), self.lang
        if t.kind == "num":
            self.i += 1
            return mk_num(t.text)
        if t.kind == "str":
            self.i += 1
            return N("str", v=unescape(t.text[1:-1]), type="str")
        if t.kind == "tpl":
            self.i += 1
            return self.interp(t.text[1:-1], "js")
        if t.kind == "istr":
            self.i += 1
            return self.interp(t.text[2:-1], "cs")
        if t.kind == "id":
            w = t.text
            if w in ("true", "false", "True", "False"):
                self.i += 1
                return N("bool", v=w.lower() == "true", type="bool")
            if w in ("null", "nullptr", "NULL", "None", "undefined"):
                self.i += 1
                return N("null")
            if w == "new": return self.p_new()
            if L == "rust" and w == "if": return self.p_rust_if()
            if L == "rust" and self.peek().text == "!" and self.peek(2).text in ("(", "["): return self.p_macro()
            self.i += 1
            return N("name", v=w)
        if t.kind == "op":
            if t.text == "(":
                nx, nx2, nx3 = self.peek(), self.peek(2), self.peek(3)
                if (L in ("java", "cs", "cpp") and nx.kind == "id" and nx.text in ("int", "double", "float", "long", "short")
                        and nx2.text == ")" and (nx3.kind in ("id", "num", "str") or nx3.text == "(")):
                    self.i += 3
                    return N("call", f="float" if nx.text in ("double", "float") else "int", args=[self.unary()])
                self.i += 1
                e = self.expr()
                self.expect(")")
                return e
            if t.text == "[":
                self.i += 1
                items = []
                while not self.at("]"):
                    items.append(self.expr())
                    if not self.accept(","): break
                self.expect("]")
                return N("list", items=items)
            if t.text == "{" and L in ("java", "cpp", "cs"):
                return N("list", items=self.brace_items())
        raise Unsupported(f"expressão inesperada '{t.text or 'fim'}' na linha {t.line}")

    def p_new(self):
        self.i += 1
        t = self.parse_type()
        if t is None: raise Unsupported("'new' com tipo desconhecido")
        if self.at("["):
            self.i += 1
            size = self.expr()
            self.expect("]")
            if self.at("["): raise Unsupported("arrays multidimensionais")
            return N("newlist", value=default_node(t), size=size)
        if is_list(t) and self.at("{"):
            return N("list", items=self.brace_items())
        if is_list(t):
            args = self.args() if self.at("(") else []
            if args and args[0].kind in ("list", "newlist"): return args[0]
            return N("list", items=[])
        raise Unsupported(f"'new {t.replace('obj:', '')}' não suportado")

    def p_rust_if(self):
        self.i += 1
        cond = self.expr()
        self.expect("{"); a = self.expr(); self.expect("}")
        self.expect("else")
        self.expect("{"); b = self.expr(); self.expect("}")
        return N("tern", c=cond, a=a, b=b)

    def p_macro(self):
        name = self.ident()
        self.i += 1                                  # '!'
        close = ")" if self.at("(") else "]"
        self.i += 1
        if name == "vec":
            if self.at(close):
                self.i += 1
                return N("list", items=[])
            first = self.expr()
            if self.accept(";"):
                size = self.expr()
                self.expect(close)
                return N("newlist", value=first, size=size)
            items = [first]
            while self.accept(","):
                if self.at(close): break
                items.append(self.expr())
            self.expect(close)
            return N("list", items=items)
        if name in ("println", "print", "format", "eprintln", "eprint"):
            if self.at(close):
                self.i += 1
                return N("call", f="__print", args=[], nl=name.endswith("ln"))
            fmt = self.cur()
            if fmt.kind != "str": raise Unsupported(f"{name}! requer string literal")
            self.i += 1
            args = []
            while self.accept(","):
                if self.at(close): break
                args.append(self.expr())
            self.expect(close)
            node = self.fmt_to_fstr(unescape(fmt.text[1:-1]), args, "rust")
            if name == "format": return node
            return N("call", f="__print", args=[node], nl=name.endswith("ln"))
        raise Unsupported(f"macro '{name}!' não suportada")

    # ----- interpolação / formatação -----
    def interp(self, raw, style):
        parts, buf, i = [], "", 0
        while i < len(raw):
            c = raw[i]
            if style == "js" and c == "$" and raw[i + 1:i + 2] == "{" or style == "cs" and c == "{" and raw[i + 1:i + 2] != "{":
                j = i + (2 if style == "js" else 1)
                depth, k = 1, j
                while k < len(raw) and depth:
                    depth += (raw[k] == "{") - (raw[k] == "}")
                    k += 1
                inner = raw[j:k - 1]
                spec = None
                if style == "cs" and ":" in inner:
                    inner, spec = inner.rsplit(":", 1)
                if buf: parts.append(unescape(buf)); buf = ""
                sub = CLikeParser(inner, self.lang)
                e = sub.expr()
                if spec:
                    m = re.search(r"\d+", spec)
                    if m and spec[0] in "fF": e = N("fixed", x=e, digits=int(m.group()))
                parts.append(e)
                i = k
                continue
            if style == "cs" and c in "{}" and raw[i + 1:i + 2] == c:
                buf += c; i += 2
                continue
            buf += c
            i += 1
        if buf: parts.append(unescape(buf))
        return N("fstr", parts=parts)

    def fmt_to_fstr(self, fmt, args, style):
        """Converte formatos estilo printf / Rust / .NET em fstr."""
        parts, buf, pos, nxt = [], "", 0, 0
        if style == "c":
            pat = re.compile(r"%(%|n|[-+ 0#]*\d*(?:\.(\d+))?(?:ll|l|h|z)?[diufsc])")
        else:
            pat = re.compile(r"\{\{|\}\}|\{([^{}:]*)(?::([^{}]*))?\}")
        for m in pat.finditer(fmt):
            buf += fmt[pos:m.start()]
            pos = m.end()
            tok = m.group(0)
            if style == "c":
                if m.group(1) == "%": buf += "%"; continue
                if m.group(1) == "n": buf += "\n"; continue
                digits = m.group(2) if tok.endswith("f") else None
                if nxt >= len(args): raise Unsupported("printf com argumentos insuficientes")
                e = args[nxt]; nxt += 1
            else:
                if tok == "{{": buf += "{"; continue
                if tok == "}}": buf += "}"; continue
                name, spec = m.group(1).strip(), m.group(2)
                if name == "":
                    if nxt >= len(args): raise Unsupported("formato com argumentos insuficientes")
                    e = args[nxt]; nxt += 1
                elif name.isdigit():
                    e = args[int(name)]
                else:
                    e = N("name", v=name)
                digits = None
                if spec:
                    d = re.search(r"\.?(\d+)", spec)
                    if d and ("f" in spec.lower() or spec.startswith(".")): digits = d.group(1)
            if buf: parts.append(buf); buf = ""
            parts.append(N("fixed", x=e, digits=int(digits)) if digits else e)
        buf += fmt[pos:]
        if buf: parts.append(buf)
        return N("fstr", parts=parts)

    # ----- chamadas e propriedades -----
    @staticmethod
    def path(n):
        names = []
        while n is not None and n.kind == "attr":
            names.append(n.name)
            n = n.obj
        if n is not None and n.kind == "name":
            names.append(n.v)
            return ".".join(reversed(names))
        return None

    def make_prop(self, e):
        obj = e.obj if e.obj.kind != "attr" else self.make_prop(e.obj)
        nm = e.name
        if nm in ("length", "Length", "Count", "size") and self.path(e) != "Math.length":
            return N("call", f="len", args=[obj])
        if nm == "PI" and self.path(e) in ("Math.PI",):
            return N("num", v="3.141592653589793", type="float")
        raise Unsupported(f"propriedade '{self.path(e) or nm}' sem equivalente")

    def make_call(self, fn, args):
        p = self.path(fn)
        if p:
            key = p[4:] if p.startswith("std.") else p
            if key in PRINT_PATHS:
                nl, style = PRINT_PATHS[key]
                if style == "c" and args:
                    if args[0].kind != "str": raise Unsupported("printf sem string literal de formato")
                    node = self.fmt_to_fstr(args[0].v, args[1:], "c")
                    parts = node.parts
                    if parts and isinstance(parts[-1], str) and parts[-1].endswith("\n"):
                        nl = True
                        parts[-1] = parts[-1][:-1]
                        if parts[-1] == "": parts.pop()
                    args = [node]
                elif style == "cs" and len(args) > 1 and args[0].kind == "str":
                    args = [self.fmt_to_fstr(args[0].v, args[1:], "net")]
                return N("call", f="__print", args=args, nl=nl)
            parts = key.split(".")
            last, root = parts[-1], parts[0].lower()
            if last in ("sort", "Sort") and root in ("collections", "arrays") and args:
                return N("method", obj=args[0], name="sort", args=[])
            if last in ("asList", "of") and root in ("arrays", "list"):
                return N("list", items=args)
            if key == "sort" and len(args) == 2:
                return N("method", obj=args[0], name="sort", args=[])
            if key in ("Vec.new", "ArrayList"): return N("list", items=[])
            if key == "String.new": return N("str", v="", type="str")
            if key == "String.from" and args: return args[0]
            if key in ("int.Parse", "Int32.Parse", "Integer.parseInt"): return N("call", f="int", args=args)
            if key in ("double.Parse", "Double.parseDouble", "float.Parse"): return N("call", f="float", args=args)
            if len(parts) == 1 and last.lower() in BARE_CALLS:
                lw = last.lower()
                mapped = {"double": "float", "string": "str", "number": "float", "prompt": "input"}.get(lw, LIB_CALLS.get(lw, lw))
                return N("call", f=mapped, args=args)
            if len(parts) > 1 and root in LIB_ROOTS and last.lower() in LIB_CALLS:
                if last.lower() in ("max", "min") and root == "collections" and len(args) == 1:
                    return N("call", f=last.lower(), args=args)
                return N("call", f=LIB_CALLS[last.lower()], args=args)
            if len(parts) == 1:
                return N("call", f=last, args=args)
        if fn.kind == "name":
            return N("call", f=fn.v, args=args)
        if fn.kind == "attr":
            obj = fn.obj if fn.obj.kind != "attr" else self.make_prop(fn.obj)
            m, ml = fn.name, fn.name.lower()
            if ml in ("push", "push_back", "add", "append") and len(args) == 1:
                return N("method", obj=obj, name="append", args=args)
            if ml == "tofixed" and len(args) == 1 and args[0].kind == "num":
                return N("fixed", x=obj, digits=int(float(args[0].v)))
            if ml in ("size", "length", "count", "len") and not args:
                return N("call", f="len", args=[obj])
            if ml == "sort": return N("method", obj=obj, name="sort", args=[])
            if ml in ("touppercase", "toupper", "to_uppercase"): return N("method", obj=obj, name="upper", args=[])
            if ml in ("tolowercase", "tolower", "to_lowercase"): return N("method", obj=obj, name="lower", args=[])
            if ml in ("tostring", "to_string"): return N("call", f="str", args=[obj])
            if ml == "equals" and len(args) == 1: return N("bin", op="==", l=obj, r=args[0])
            if ml in ("get", "charat") and len(args) == 1: return N("index", obj=obj, idx=args[0])
            if ml == "sqrt" and not args: return N("call", f="sqrt", args=[obj])
            if ml == "abs" and not args: return N("call", f="abs", args=[obj])
            if ml in ("pow", "powi", "powf") and len(args) == 1: return N("call", f="pow", args=[obj, args[0]])
            if ml in ("floor", "ceil") and not args: return N("call", f=ml, args=[obj])
            if ml in ("min", "max") and len(args) == 1: return N("call", f=ml, args=[obj, args[0]])
            if ml == "step_by" and obj.kind == "range":
                obj.step = args[0]
                return obj
            if ml == "parse":
                return N("call", f="float" if self.turbofish == "float" else "int", args=[obj])
            if ml in IDENTITY_METHODS: return obj
            raise Unsupported(f"método '.{m}()' sem equivalente")
        raise Unsupported("chamada de função complexa")

# ============================================================
# 8. INFERÊNCIA DE TIPOS E ANÁLISE SEMÂNTICA
# ============================================================

def is_const_expr(v):
    if v is None: return False
    if v.kind in ("num", "str", "bool"): return True
    return v.kind == "list" and all(is_const_expr(i) for i in v.items)


def prepare(prog):
    """Normaliza o programa: remove main() solto, promove globais."""
    prog.main_body = [s for s in prog.main_body
                      if not (s.kind == "expr" and s.e.kind == "call" and s.e.f == "main" and not s.e.args)]
    prog.run_main = any(f.name == "main" for f in prog.funcs)
    if prog.hoist:
        used = {n.v for f in prog.funcs for n in walk_ir(f.body) if n.kind == "name"}
        names, keep = {g.name for g in prog.globals}, []
        for s in prog.main_body:
            nm = val = ht = None
            if s.kind == "assign" and s.op == "=" and s.target.kind == "name" and is_const_expr(s.value):
                nm, val, ht = s.target.v, s.value, s.htype
            elif s.kind == "decl" and is_const_expr(s.value):
                nm, val, ht = s.name, s.value, s.vtype
            if nm and nm in used and nm not in names:
                prog.globals.append(N("decl", name=nm, vtype=ht, value=val, mutable=False, comments=s.comments))
                names.add(nm)
            else:
                keep.append(s)
        prog.main_body = keep


class Annotator:
    def __init__(self, prog):
        self.p = prog
        self.funcs = {f.name: f for f in prog.funcs}
        self.hints, self.vt, self.gscope, self.rets, self.ext = {}, {}, {}, [], set()

    def run(self):
        p = self.p
        for f in p.funcs:
            for pa in f.params:
                pa.explicit = pa.type not in (None, "auto")
            f.rexplicit = f.ret not in (None, "auto")
            f.rtype = f.ret if f.rexplicit else None
        for _ in range(3):
            self.one_pass()
        for f in p.funcs:
            for pa in f.params:
                pa.type = norm(pa.type)
            f.rtype = "void" if (f.rtype in (None, "void")) else norm(f.rtype)
        self.scan_param_mut()
        self.finalize()
        for name in sorted(self.ext):
            if name == "input_prompt":
                p.warnings.append("O texto (prompt) de input() só é mantido em Python e JavaScript.")
            else:
                p.warnings.append(f"Função externa '{name}()' não foi reconhecida e foi mantida como está.")

    # ----- inferência -----
    def one_pass(self):
        p = self.p
        for g in p.globals:
            if not hasattr(g, "dt"): g.dt = g.vtype
            vt = self.T(g.value, self.gscope) if g.value is not None else None
            g.vtype = g.dt if g.dt not in (None, "auto") else vt
            if g.dt and is_list(g.dt) and vt and "any" in g.dt: g.vtype = unify(g.dt, vt)
            self.gscope[g.name] = g.vtype
        for f in p.funcs:
            sc = dict(self.gscope)
            sc.update(self.vt.get(f.name, {}))
            for i, pa in enumerate(f.params):
                if not pa.explicit:
                    pa.type = self.hints.get((f.name, i), pa.type)
                sc[pa.name] = pa.type or "any"
            self.rets = []
            self.stmts(f.body, sc)
            if not f.rexplicit:
                t = None
                for r in self.rets: t = unify(t, r)
                f.rtype = t or "void"
            self.vt[f.name] = sc
        sc = dict(self.gscope)
        sc.update(self.vt.get("<main>", {}))
        self.rets = []
        self.stmts(p.main_body, sc)
        self.vt["<main>"] = sc

    def stmts(self, lst, sc):
        for s in lst:
            getattr(self, "s_" + s.kind, lambda *_: None)(s, sc)

    def s_decl(self, s, sc):
        if not hasattr(s, "dt"): s.dt = s.vtype
        vt = self.T(s.value, sc) if s.value is not None else None
        if s.dt not in (None, "auto"):
            t = unify(s.dt, vt) if (is_list(s.dt) and "any" in s.dt and vt) else s.dt
        else:
            t = unify(sc.get(s.name), vt) if vt else sc.get(s.name)
        s.vtype = t
        sc[s.name] = t

    def s_assign(self, s, sc):
        vt = self.T(s.value, sc)
        tg = s.target
        if tg.kind == "name":
            ht = getattr(s, "htype", None)
            sc[tg.v] = ht or unify(sc.get(tg.v), vt)
            tg.type = sc[tg.v]
        else:
            self.T(tg, sc)

    def s_if(self, s, sc):
        self.T(s.cond, sc); self.stmts(s.body, sc); self.stmts(s.orelse, sc)

    def s_while(self, s, sc):
        self.T(s.cond, sc); self.stmts(s.body, sc)

    def s_for_range(self, s, sc):
        for x in (s.start, s.stop, s.step):
            if x is not None: self.T(x, sc)
        sc[s.var] = "int"
        self.stmts(s.body, sc)

    def s_for_each(self, s, sc):
        t = self.T(s.iter, sc)
        sc[s.var] = elem_of(t) if is_list(t) else ("str" if t == "str" else "any")
        self.stmts(s.body, sc)

    def s_ret(self, s, sc):
        if s.value is not None: self.rets.append(self.T(s.value, sc))

    def s_print(self, s, sc):
        for a in s.args: self.T(a, sc)

    def s_expr(self, s, sc):
        self.T(s.e, sc)

    def T(self, n, sc):
        t = getattr(self, "t_" + n.kind)(n, sc)
        n.type = t
        return t

    def t_num(self, n, sc): return n.type
    def t_str(self, n, sc): return "str"
    def t_bool(self, n, sc): return "bool"
    def t_null(self, n, sc): return "any"
    def t_name(self, n, sc): return sc.get(n.v, "any")

    def t_un(self, n, sc):
        t = self.T(n.x, sc)
        return "bool" if n.op == "not" else ("int" if n.op == "~" else t)

    def t_bin(self, n, sc):
        lt, rt, op = self.T(n.l, sc), self.T(n.r, sc), n.op
        if op in ("and", "or", "==", "!=", "<", ">", "<=", ">="):
            n.res = op
            return "bool"
        if op == "cdiv":
            op = "//" if (norm(lt) == "int" and norm(rt) == "int") else "/"
        n.res = op
        if op in ("+", "*") and "str" in (lt, rt): return "str"
        if op == "/": return "float"
        both_int = norm(lt) == "int" and norm(rt) == "int"
        if op == "//": return "int" if both_int else "float"
        if op == "**":
            return "int" if (both_int and n.r.kind == "num" and not n.r.v.startswith("-")) else "float"
        if op in ("&", "|", "^"): return "bool" if lt == rt == "bool" else "int"
        if op in ("<<", ">>"): return "int"
        if "float" in (lt, rt): return "float"
        return "int" if (lt in (None, "any") and rt in (None, "any")) else unify(lt if lt != "bool" else "int", rt if rt != "bool" else "int")

    def t_call(self, n, sc):
        ats = [self.T(a, sc) for a in n.args]
        name = n.f
        if name in self.funcs:
            f = self.funcs[name]
            for i, t in enumerate(ats):
                if i < len(f.params) and not f.params[i].explicit and t not in (None, "any"):
                    self.hints[(name, i)] = unify(self.hints.get((name, i)), t)
            return f.rtype or "any"
        if name == "len": return "int"
        if name == "abs": return ats[0] if ats else "int"
        if name in ("min", "max"):
            if len(ats) == 1 and is_list(ats[0]): return elem_of(ats[0])
            t = None
            for x in ats: t = unify(t, x)
            return t or "int"
        if name in ("sqrt", "pow"): return "float"
        if name in ("floor", "ceil", "int"): return "int"
        if name == "float": return "float"
        if name == "input" and n.args and "input_prompt" not in self.ext:
            self.ext.add("input_prompt")
        if name in ("str", "input"): return "str"
        self.ext.add(name)
        n.ext = True
        return "any"

    def t_method(self, n, sc):
        ot = self.T(n.obj, sc)
        ats = [self.T(a, sc) for a in n.args]
        if n.name == "append":
            if n.obj.kind == "name" and is_list(ot) and ats:
                sc[n.obj.v] = "list:" + unify(elem_of(ot), ats[0])
            return "void"
        if n.name == "sort": return "void"
        return "str"

    def t_index(self, n, sc):
        ot = self.T(n.obj, sc)
        self.T(n.idx, sc)
        return elem_of(ot) if is_list(ot) else ("str" if ot == "str" else "any")

    def t_list(self, n, sc):
        t = None
        for i in n.items: t = unify(t, self.T(i, sc))
        return "list:" + (t or "any")

    def t_newlist(self, n, sc):
        self.T(n.size, sc)
        return "list:" + (self.T(n.value, sc) or "any")

    def t_fstr(self, n, sc):
        for p in n.parts:
            if not isinstance(p, str): self.T(p, sc)
        return "str"

    def t_fixed(self, n, sc):
        self.T(n.x, sc)
        return "str"

    def t_tern(self, n, sc):
        self.T(n.c, sc)
        return unify(self.T(n.a, sc), self.T(n.b, sc))

    def t_range(self, n, sc):
        raise Unsupported("intervalo (range) fora de um laço for")

    # ----- mutabilidade, declarações e hoisting -----
    @staticmethod
    def exprs_of(s):
        k = s.kind
        if k == "decl": return [s.value]
        if k == "assign": return [s.target, s.value]
        if k in ("if", "while"): return [s.cond]
        if k == "for_range": return [s.start, s.stop, s.step]
        if k == "for_each": return [s.iter]
        if k == "ret": return [s.value]
        if k == "print": return list(s.args)
        if k == "expr": return [s.e]
        return []

    def scan_param_mut(self):
        for _ in range(2):
            for f in self.p.funcs:
                names = {pa.name: pa for pa in f.params}
                for n in walk_ir(f.body):
                    if n.kind == "assign":
                        r = root_name(n.target) if n.target.kind == "index" else None
                        if r in names: names[r].mutated = True
                        if n.target.kind == "name" and n.target.v in names: names[n.target.v].assigned = True
                    elif n.kind == "method" and n.name in ("append", "sort"):
                        r = root_name(n.obj)
                        if r in names: names[r].mutated = True
                    elif n.kind == "call" and n.f in self.funcs:
                        callee = self.funcs[n.f]
                        for i, a in enumerate(n.args):
                            if a.kind == "name" and a.v in names and i < len(callee.params) and callee.params[i].mutated:
                                names[a.v].mutated = True

    @staticmethod
    def mark(d, how):
        if d.kind == "decl": d.mutable = True
        elif d.kind == "param":
            if how == "assign": d.assigned = True
            else: d.mutated = True

    def finalize(self):
        p = self.p
        gdecl = {g.name: g for g in p.globals}
        for f in p.funcs:
            declared = {} if p.python else dict(gdecl)
            for pa in f.params: declared[pa.name] = pa
            hoisted = []
            self.fin(f.body, 0, declared, self.vt.get(f.name, {}), hoisted)
            f.body[0:0] = hoisted
        declared = dict(gdecl)
        hoisted = []
        self.fin(p.main_body, 0, declared, self.vt.get("<main>", {}), hoisted)
        p.main_body[0:0] = hoisted
        for g in p.globals:
            g.vtype = norm(g.vtype)

    def fin(self, stmts, depth, declared, sc, hoisted):
        for s in stmts:
            k = s.kind
            if k == "decl":
                s.vtype = norm(s.vtype)
                declared[s.name] = s
            elif k == "assign":
                tg = s.target
                if tg.kind == "name":
                    nm = tg.v
                    if nm not in declared:
                        if self.p.python:
                            t = norm(getattr(s, "htype", None) or sc.get(nm))
                            if depth == 0:
                                s.kind, s.name, s.vtype, s.mutable = "decl", nm, t, False
                                declared[nm] = s
                            else:
                                hd = N("decl", name=nm, vtype=t, value=default_node(t), mutable=True)
                                hoisted.append(hd)
                                declared[nm] = hd
                    else:
                        self.mark(declared[nm], "assign")
                else:
                    r = root_name(tg)
                    if r in declared: self.mark(declared[r], "mut")
            elif k in ("for_range", "for_each"):
                declared.setdefault(s.var, N("loopvar"))
            for e in self.exprs_of(s):
                if e is None: continue
                for n in walk_ir(e):
                    if n.kind == "method" and n.name in ("append", "sort"):
                        r = root_name(n.obj)
                        if r in declared: self.mark(declared[r], "mut")
                    elif n.kind == "call" and n.f in self.funcs:
                        callee = self.funcs[n.f]
                        for i, a in enumerate(n.args):
                            if a.kind == "name" and a.v in declared and i < len(callee.params) and callee.params[i].mutated:
                                self.mark(declared[a.v], "mut")
            for sub in ("body", "orelse"):
                if k in ("if", "while", "for_range", "for_each") and hasattr(s, sub):
                    self.fin(getattr(s, sub), depth + 1, declared, sc, hoisted)


# ============================================================
# 9. EMISSORES (IR -> LINGUAGEM DE DESTINO)
# ============================================================

class Emitter:
    comment = "//"

    def __init__(self, prog):
        self.p, self.out, self.lv = prog, [], 0
        self.funcs = {f.name: f for f in prog.funcs}
        self.uses, self.cur_fn = set(), None

    def w(self, s=""):
        self.out.append("    " * self.lv + s if s else "")

    def cm_lines(self, lines):
        for c in lines:
            self.w(f"{self.comment} {c}".rstrip())

    def stmt(self, s):
        self.cm_lines(s.comments)
        getattr(self, "st_" + s.kind)(s)

    def block(self, stmts):
        for s in stmts: self.stmt(s)

    def sub(self, stmts):
        self.lv += 1
        self.block(stmts)
        self.lv -= 1

    def st_comment(self, s):
        self.cm_lines(s.lines)

    @staticmethod
    def merge_parts(parts):
        out = []
        for p in parts:
            if not isinstance(p, str) and p.kind == "str": p = p.v
            if isinstance(p, str) and out and isinstance(out[-1], str): out[-1] += p
            else: out.append(p)
        return out

    def parts_of(self, n):
        return self.merge_parts(n.parts)

    def print_parts(self, args):
        parts = []
        for i, a in enumerate(args):
            if i: parts.append(" ")
            if a.kind == "fstr": parts.extend(a.parts)
            else: parts.append(a)
        return self.merge_parts(parts)

    def expr(self, n, prec=0):
        return getattr(self, "ex_" + n.kind)(n, prec)

    @staticmethod
    def par(s, p, prec):
        return f"({s})" if p < prec else s

    def args(self, lst):
        return ", ".join(self.expr(a) for a in lst)

    def is_entry(self, f):
        return f.name == "main" and not f.params


# ---------------------------------------------------------------- Python

class PyEmitter(Emitter):
    comment = "#"
    PREC = {"or": 1, "and": 2, "==": 4, "!=": 4, "<": 4, ">": 4, "<=": 4, ">=": 4, "|": 5, "^": 6, "&": 7,
            "<<": 8, ">>": 8, "+": 9, "-": 9, "*": 10, "/": 10, "//": 10, "%": 10, "**": 12}

    def pt(self, t):
        t = norm(t) if t != "void" else t
        if t == "void": return "None"
        if is_list(t): return f"list[{self.pt(t[5:])}]"
        return t

    def ex_num(self, n, prec): return f"({n.v})" if n.v.startswith("-") and prec >= 11 else n.v
    def ex_str(self, n, prec): return quote(n.v)
    def ex_bool(self, n, prec): return "True" if n.v else "False"
    def ex_null(self, n, prec): return "None"
    def ex_name(self, n, prec): return n.v

    def ex_un(self, n, prec):
        if n.op == "not": return self.par("not " + self.expr(n.x, 3), 3, prec)
        return self.par(n.op + self.expr(n.x, 11), 11, prec)

    def ex_bin(self, n, prec):
        op = getattr(n, "res", n.op)
        if op == "+" and tt(n) == "str":      # "texto" + número  ->  str(número)
            ls = self.expr(n.l, 9) if tt(n.l) == "str" else f"str({self.expr(n.l)})"
            rs = self.expr(n.r, 10) if tt(n.r) == "str" else f"str({self.expr(n.r)})"
            return self.par(f"{ls} + {rs}", 9, prec)
        p = self.PREC[op]
        lp, rp = (p + 1, p) if op == "**" else (p, p + 1)
        return self.par(f"{self.expr(n.l, lp)} {op} {self.expr(n.r, rp)}", p, prec)

    def ex_call(self, n, prec):
        f = n.f
        a = [self.expr(x) for x in n.args]
        if f in self.funcs or f not in BUILTINS or f == "__print":
            return f"{f}({', '.join(a)})"
        if f in ("sqrt", "floor", "ceil"):
            self.uses.add("math")
            return f"math.{f}({a[0]})"
        return f"{f}({', '.join(a)})"

    def ex_method(self, n, prec):
        return f"{self.expr(n.obj, 12)}.{n.name}({self.args(n.args)})"

    def ex_index(self, n, prec): return f"{self.expr(n.obj, 12)}[{self.expr(n.idx)}]"
    def ex_list(self, n, prec): return "[" + self.args(n.items) + "]"
    def ex_newlist(self, n, prec): return self.par(f"[{self.expr(n.value)}] * {self.expr(n.size, 11)}", 10, prec)
    def ex_fixed(self, n, prec): return f"format({self.expr(n.x)}, '.{n.digits}f')"
    def ex_tern(self, n, prec): return self.par(f"{self.expr(n.a, 1)} if {self.expr(n.c, 1)} else {self.expr(n.b, 0)}", 0, prec)

    def ex_fstr(self, n, prec):
        pieces, parts = [], self.parts_of(n)
        for p in parts:
            if isinstance(p, str): pieces.append(("lit", p))
            elif p.kind == "fixed": pieces.append(("exp", self.expr(p.x) + f":.{p.digits}f"))
            else: pieces.append(("exp", self.expr(p)))
        q = "'" if any(k == "exp" and '"' in v for k, v in pieces) else '"'
        out = []
        for k, v in pieces:
            out.append(quote(v.replace("{", "{{").replace("}", "}}"), q)[1:-1] if k == "lit" else "{" + v + "}")
        return "f" + q + "".join(out) + q

    # comandos
    def st_decl(self, s):
        self.w(f"{s.name} = {self.expr(s.value) if s.value is not None else 'None'}")

    def st_assign(self, s):
        self.w(f"{self.expr(s.target)} {s.op} {self.expr(s.value)}")

    def st_expr(self, s): self.w(self.expr(s.e))

    def st_print(self, s):
        a = self.args(s.args)
        self.w(f"print({a}{'' if s.nl else (', ' if a else '') + 'end=' + chr(34) * 2})")

    def st_ret(self, s): self.w("return" if s.value is None else f"return {self.expr(s.value)}")
    def st_brk(self, s): self.w("break")
    def st_cont(self, s): self.w("continue")

    def body(self, stmts):
        self.lv += 1
        before = len(self.out)
        self.block(stmts)
        if not any(st.kind != "comment" for st in stmts): self.w("pass")
        self.lv -= 1

    def st_if(self, s):
        kw = "if"
        while True:
            self.w(f"{kw} {self.expr(s.cond)}:")
            self.body(s.body)
            oe = s.orelse
            if len(oe) == 1 and oe[0].kind == "if" and not oe[0].comments:
                s, kw = oe[0], "elif"
                continue
            if oe:
                self.w("else:")
                self.body(oe)
            break

    def st_while(self, s):
        self.w(f"while {self.expr(s.cond)}:")
        self.body(s.body)

    def st_for_range(self, s):
        start, stop = self.expr(s.start), self.expr(s.stop)
        if s.step is not None: a = f"{start}, {stop}, {self.expr(s.step)}"
        elif start != "0": a = f"{start}, {stop}"
        else: a = stop
        self.w(f"for {s.var} in range({a}):")
        self.body(s.body)

    def st_for_each(self, s):
        self.w(f"for {s.var} in {self.expr(s.iter)}:")
        self.body(s.body)

    def func(self, f):
        self.cm_lines(f.comments)
        ps = ", ".join(f"{p.name}: {self.pt(p.type)}" for p in f.params)
        self.w(f"def {f.name}({ps}) -> {self.pt(f.rtype)}:")
        self.body(f.body)

    def generate(self):
        p = self.p
        for g in p.globals: self.stmt(g)
        if p.globals: self.w()
        for f in p.funcs:
            self.func(f)
            self.w(); self.w()
        for s in p.main_body: self.stmt(s)
        if p.run_main:
            if p.main_body: self.w()
            self.w('if __name__ == "__main__":')
            self.w("    main()")
        text = "\n".join(self.out).rstrip() + "\n"
        return ("import math\n\n\n" if "math" in self.uses else "") + text


# ---------------------------------------------------------------- base C-like

class CBase(Emitter):
    PREC = {"or": 1, "and": 2, "|": 3, "^": 4, "&": 5, "==": 6, "!=": 6, "<": 7, ">": 7, "<=": 7, ">=": 7,
            "<<": 8, ">>": 8, "+": 9, "-": 9, "*": 10, "/": 10, "%": 10}
    OPS = {"and": "&&", "or": "||"}
    TRUE, FALSE, NULL = "true", "false", "null"
    CAST_D = "(double) "
    LOOP_T = "int"

    def cond(self, c): return f"({self.expr(c)})"

    def ex_num(self, n, prec): return f"({n.v})" if n.v.startswith("-") and prec >= 11 else n.v
    def ex_str(self, n, prec): return quote(n.v)
    def ex_bool(self, n, prec): return self.TRUE if n.v else self.FALSE
    def ex_null(self, n, prec): return self.NULL
    def ex_name(self, n, prec): return n.v
    def ex_index(self, n, prec): return f"{self.expr(n.obj, 12)}[{self.expr(n.idx)}]"
    def ex_tern(self, n, prec): return self.par(f"{self.expr(n.c, 1)} ? {self.expr(n.a, 0)} : {self.expr(n.b, 0)}", 0, prec)

    def ex_un(self, n, prec):
        op = "!" if n.op == "not" else n.op
        return self.par(op + self.expr(n.x, 11), 11, prec)

    def ex_bin(self, n, prec):
        op = getattr(n, "res", n.op)
        if op == "//": return self.floordiv(n, prec)
        if op == "**": return self.power(n, prec)
        if op == "/": return self.truediv(n, prec)
        if op == "+" and tt(n) == "str": return self.concat(n, prec)
        if op in ("==", "!=") and tt(n.l) == "str" and tt(n.r) == "str": return self.streq(n, op, prec)
        p = self.PREC[op]
        return self.par(f"{self.expr(n.l, p)} {self.OPS.get(op, op)} {self.expr(n.r, p + 1)}", p, prec)

    def truediv(self, n, prec):
        if tt(n.l) == "int" and tt(n.r) == "int":
            s = f"{self.CAST_D}{self.expr(n.l, 11)} / {self.expr(n.r, 11)}"
        else:
            s = f"{self.expr(n.l, 10)} / {self.expr(n.r, 11)}"
        return self.par(s, 10, prec)

    def floordiv(self, n, prec):
        s = f"{self.expr(n.l, 10)} / {self.expr(n.r, 11)}"
        if tt(n.l) == "int" and tt(n.r) == "int": return self.par(s, 10, prec)
        return self.floor_call(s)

    def concat(self, n, prec):
        return self.par(f"{self.expr(n.l, 9)} + {self.expr(n.r, 10)}", 9, prec)

    def streq(self, n, op, prec):
        return self.par(f"{self.expr(n.l, 6)} {op} {self.expr(n.r, 7)}", 6, prec)

    # comandos
    def st_expr(self, s): self.w(self.expr(s.e) + ";")
    def st_brk(self, s): self.w("break;")
    def st_cont(self, s): self.w("continue;")
    def st_print(self, s): self.print_stmt(s)

    def st_ret(self, s):
        self.w("return;" if s.value is None else f"return {self.expr(s.value)};")

    def st_assign(self, s):
        self.w(f"{self.expr(s.target)} {s.op} {self.expr(s.value)};")

    def st_decl(self, s):
        t = self.ty(s.vtype)
        self.w(f"{t} {s.name} = {self.expr(s.value)};" if s.value is not None else f"{t} {s.name};")

    def st_while(self, s):
        self.w(f"while {self.cond(s.cond)} {{")
        self.sub(s.body)
        self.w("}")

    def st_if(self, s):
        head = f"if {self.cond(s.cond)} {{"
        while True:
            self.w(head)
            self.sub(s.body)
            oe = s.orelse
            if len(oe) == 1 and oe[0].kind == "if" and not oe[0].comments:
                s = oe[0]
                head = f"}} else if {self.cond(s.cond)} {{"
                continue
            if oe:
                self.w("} else {")
                self.sub(oe)
            self.w("}")
            break

    def st_for_range(self, s):
        v, start, stop = s.var, self.expr(s.start), self.expr(s.stop)
        step, neg = s.step, False
        if step is None or (step.kind == "num" and step.v == "1"):
            inc = f"{v}++"
        else:
            neg = step.kind == "num" and step.v.startswith("-")
            amount = step.v[1:] if neg else self.expr(step)
            inc = f"{v} {'-=' if neg else '+='} {amount}"
        cmp_ = ">" if neg else "<"
        self.w(f"for ({self.loop_decl(v)} = {start}; {v} {cmp_} {stop}; {inc}) {{")
        self.sub(s.body)
        self.w("}")

    def loop_decl(self, v): return f"{self.LOOP_T} {v}"


# ---------------------------------------------------------------- JavaScript

class JSEmitter(CBase):
    OPS = {"and": "&&", "or": "||", "==": "===", "!=": "!=="}

    def ty(self, t): return "let"
    def loop_decl(self, v): return f"let {v}"
    def truediv(self, n, prec): return self.par(f"{self.expr(n.l, 10)} / {self.expr(n.r, 11)}", 10, prec)
    def floordiv(self, n, prec): return f"Math.floor({self.expr(n.l, 10)} / {self.expr(n.r, 11)})"
    def power(self, n, prec): return f"Math.pow({self.expr(n.l)}, {self.expr(n.r)})"

    def ex_call(self, n, prec):
        f, a = n.f, [self.expr(x) for x in n.args]
        if f in self.funcs or f not in BUILTINS or f == "__print":
            return f"{f}({', '.join(a)})"
        t0 = tt(n.args[0]) if n.args else ""
        if f == "len": return f"{self.expr(n.args[0], 12)}.length"
        if f in ("abs", "sqrt", "pow", "floor", "ceil"): return f"Math.{f}({', '.join(a)})"
        if f in ("min", "max"):
            return f"Math.{f}(...{a[0]})" if len(a) == 1 else f"Math.{f}({', '.join(a)})"
        if f == "int": return f"parseInt({a[0]}, 10)" if t0 == "str" else (f"Math.trunc({a[0]})" if t0 == "float" else a[0])
        if f == "float": return f"parseFloat({a[0]})" if t0 == "str" else a[0]
        if f == "str": return f"String({a[0]})"
        return f"prompt({a[0] if a else chr(34) * 2})"

    def ex_method(self, n, prec):
        o = self.expr(n.obj, 12)
        if n.name == "append": return f"{o}.push({self.args(n.args)})"
        if n.name == "sort":
            return f"{o}.sort((a, b) => a - b)" if elem_of(tt(n.obj)) in ("int", "float") else f"{o}.sort()"
        return f"{o}.{'toUpperCase' if n.name == 'upper' else 'toLowerCase'}()"

    def ex_list(self, n, prec): return "[" + self.args(n.items) + "]"
    def ex_newlist(self, n, prec): return f"new Array({self.expr(n.size)}).fill({self.expr(n.value)})"
    def ex_fixed(self, n, prec): return f"{self.expr(n.x, 12)}.toFixed({n.digits})"

    def ex_fstr(self, n, prec):
        out = []
        for p in self.parts_of(n):
            if isinstance(p, str):
                out.append(p.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${").replace("\n", "\\n").replace("\t", "\\t"))
            else:
                out.append("${" + self.expr(p) + "}")
        return "`" + "".join(out) + "`"

    def print_stmt(self, s):
        if s.nl or not s.args:
            self.w(f"console.log({self.args(s.args)});")
        else:       # sem quebra de linha
            self.w(f"process.stdout.write({self.ex_fstr(N('fstr', parts=self.print_parts(s.args)), 0)});")

    def st_decl(self, s):
        kw = "let" if s.mutable else "const"
        if s.value is None: self.w(f"let {s.name};")
        else: self.w(f"{kw} {s.name} = {self.expr(s.value)};")

    def st_for_each(self, s):
        self.w(f"for (const {s.var} of {self.expr(s.iter)}) {{")
        self.sub(s.body)
        self.w("}")

    def func(self, f):
        self.cm_lines(f.comments)
        self.w(f"function {f.name}({', '.join(p.name for p in f.params)}) {{")
        self.sub(f.body)
        self.w("}")

    def generate(self):
        p = self.p
        for g in p.globals: self.stmt(g)
        if p.globals: self.w()
        for f in p.funcs:
            self.func(f)
            self.w()
        for s in p.main_body: self.stmt(s)
        if p.run_main: self.w("main();")
        return "\n".join(self.out).rstrip() + "\n"


# ---------------------------------------------------------------- Java

class JavaEmitter(CBase):
    def ty(self, t, box=False):
        t = t if t == "void" else norm(t)
        if is_list(t):
            self.uses.add("util")
            return f"ArrayList<{self.ty(t[5:], True)}>"
        return {"int": "Integer" if box else "int", "float": "Double" if box else "double",
                "str": "String", "bool": "Boolean" if box else "boolean", "void": "void"}[t]

    def floor_call(self, s): return f"Math.floor({s})"
    def streq(self, n, op, prec):
        s = f"{self.expr(n.l, 12)}.equals({self.expr(n.r)})"
        return s if op == "==" else self.par("!" + s, 11, prec)

    def power(self, n, prec):
        s = f"Math.pow({self.expr(n.l)}, {self.expr(n.r)})"
        return self.par("(int) " + s, 11, prec) if tt(n) == "int" else s

    def concat_expr(self, parts, prec):
        if not parts: return '""'
        pieces = [quote(p) if isinstance(p, str) else self.expr(p, 10) for p in parts]
        first = parts[0]
        if not (isinstance(first, str) or tt(first) == "str"): pieces.insert(0, '""')
        return pieces[0] if len(pieces) == 1 else self.par(" + ".join(pieces), 9, prec)

    def ex_fstr(self, n, prec): return self.concat_expr(self.parts_of(n), prec)
    def ex_fixed(self, n, prec): return f'String.format("%.{n.digits}f", {self.expr(n.x)})'

    def ex_call(self, n, prec):
        f, a = n.f, [self.expr(x) for x in n.args]
        if f in self.funcs or f not in BUILTINS or f == "__print":
            return f"{f}({', '.join(a)})"
        t0 = tt(n.args[0]) if n.args else ""
        if f == "len":
            return f"{self.expr(n.args[0], 12)}.{'size' if is_list(t0) else 'length'}()"
        if f in ("abs", "sqrt", "pow"): return f"Math.{f}({', '.join(a)})"
        if f in ("floor", "ceil"): return self.par(f"(int) Math.{f}({a[0]})", 11, prec)
        if f in ("min", "max"):
            if len(a) == 1:
                self.uses.add("util")
                return f"Collections.{f}({a[0]})"
            return f"Math.{f}({', '.join(a)})"
        if f == "int":
            if t0 == "str": return f"Integer.parseInt({a[0]})"
            return self.par(f"(int) {self.expr(n.args[0], 11)}", 11, prec) if t0 == "float" else a[0]
        if f == "float":
            if t0 == "str": return f"Double.parseDouble({a[0]})"
            return self.par(f"(double) {self.expr(n.args[0], 11)}", 11, prec) if t0 != "float" else a[0]
        if f == "str": return a[0] if t0 == "str" else f"String.valueOf({a[0]})"
        self.uses.add("util")
        return "new Scanner(System.in).nextLine()"

    def ex_method(self, n, prec):
        o = self.expr(n.obj, 12)
        if n.name == "append": return f"{o}.add({self.args(n.args)})"
        if n.name == "sort":
            self.uses.add("util")
            return f"Collections.sort({self.expr(n.obj)})"
        return f"{o}.{'toUpperCase' if n.name == 'upper' else 'toLowerCase'}()"

    def ex_index(self, n, prec):
        if is_list(tt(n.obj)): return f"{self.expr(n.obj, 12)}.get({self.expr(n.idx)})"
        return f"String.valueOf({self.expr(n.obj, 12)}.charAt({self.expr(n.idx)}))"

    def ex_list(self, n, prec):
        self.uses.add("util")
        t = self.ty(tt(n))
        if not n.items: return "new ArrayList<>()"
        return f"new ArrayList<>(Arrays.asList({self.args(n.items)}))"

    def ex_newlist(self, n, prec):
        self.uses.add("util")
        return f"new ArrayList<>(Collections.nCopies({self.expr(n.size)}, {self.expr(n.value)}))"

    def st_assign(self, s):
        tg = s.target
        if tg.kind == "index" and is_list(tt(tg.obj)):
            o, i = self.expr(tg.obj, 12), self.expr(tg.idx)
            if s.op == "=": val = self.expr(s.value)
            else: val = f"{o}.get({i}) {s.op[0]} {self.expr(s.value, 10)}"
            self.w(f"{o}.set({i}, {val});")
        else:
            super().st_assign(s)

    def print_stmt(self, s):
        fn = "println" if s.nl else "print"
        if not s.args: self.w(f"System.out.{fn}();")
        elif len(s.args) == 1: self.w(f"System.out.{fn}({self.expr(s.args[0])});")
        else:
            self.w(f"System.out.{fn}({self.concat_expr(self.print_parts(s.args), 0)});")

    def st_for_each(self, s):
        t = tt(s.iter)
        if t == "str": self.w(f"for (String {s.var} : {self.expr(s.iter, 12)}.split(\"\")) {{")
        else: self.w(f"for ({self.ty(elem_of(t))} {s.var} : {self.expr(s.iter)}) {{")
        self.sub(s.body)
        self.w("}")

    def func(self, f):
        self.cm_lines(f.comments)
        if self.is_entry(f):
            self.w("public static void main(String[] args) {")
            self.lv += 1
            self.block(self.p.main_body)
            self.lv -= 1
        else:
            ps = ", ".join(f"{self.ty(p.type)} {p.name}" for p in f.params)
            self.w(f"static {self.ty(f.rtype)} {f.name}({ps}) {{")
        self.sub(f.body)
        self.w("}")

    def generate(self):
        p = self.p
        self.lv = 1
        for g in p.globals:
            self.cm_lines(g.comments)
            t = self.ty(g.vtype)
            self.w(f"static {t} {g.name}" + (f" = {self.expr(g.value)};" if g.value is not None else ";"))
        if p.globals: self.w()
        has_entry = any(self.is_entry(f) for f in p.funcs)
        for f in p.funcs:
            self.func(f)
            self.w()
        if not has_entry and p.main_body:
            self.w("public static void main(String[] args) {")
            self.sub(p.main_body)
            self.w("}")
        body = "\n".join(self.out).rstrip()
        head = "import java.util.*;\n\n" if "util" in self.uses else ""
        return f"{head}public class Main {{\n{body}\n}}\n"


# ---------------------------------------------------------------- C#

class CSEmitter(CBase):
    def ty(self, t):
        t = t if t == "void" else norm(t)
        if is_list(t):
            self.uses.add("generic")
            return f"List<{self.ty(t[5:])}>"
        return {"int": "int", "float": "double", "str": "string", "bool": "bool", "void": "void"}[t]

    def floor_call(self, s): return f"Math.Floor({s})"

    def power(self, n, prec):
        s = f"Math.Pow({self.expr(n.l)}, {self.expr(n.r)})"
        return self.par("(int) " + s, 11, prec) if tt(n) == "int" else s

    def concat_expr(self, parts, prec):
        if not parts: return '""'
        pieces = [quote(p) if isinstance(p, str) else self.expr(p, 10) for p in parts]
        first = parts[0]
        if not (isinstance(first, str) or tt(first) == "str"): pieces.insert(0, '""')
        return pieces[0] if len(pieces) == 1 else self.par(" + ".join(pieces), 9, prec)

    def ex_fstr(self, n, prec):
        parts, out = self.parts_of(n), []
        for p in parts:
            if isinstance(p, str):
                out.append(quote(p.replace("{", "{{").replace("}", "}}"))[1:-1])
                continue
            e = self.expr(p.x if p.kind == "fixed" else p)
            if any(c in e for c in '"?:'):
                return self.concat_expr(parts, prec)
            out.append("{" + e + (f":F{p.digits}" if p.kind == "fixed" else "") + "}")
        return '$"' + "".join(out) + '"'

    def ex_fixed(self, n, prec): return f'{self.expr(n.x, 12)}.ToString("F{n.digits}")'

    def ex_call(self, n, prec):
        f, a = n.f, [self.expr(x) for x in n.args]
        if f in self.funcs or f not in BUILTINS or f == "__print":
            return f"{f}({', '.join(a)})"
        t0 = tt(n.args[0]) if n.args else ""
        if f == "len":
            return f"{self.expr(n.args[0], 12)}.{'Count' if is_list(t0) else 'Length'}"
        if f in ("abs", "sqrt", "pow"): return f"Math.{f.capitalize()}({', '.join(a)})"
        if f in ("floor", "ceil"): return self.par(f"(int) Math.{f.capitalize()}({a[0]})", 11, prec)
        if f in ("min", "max"):
            if len(a) == 1:
                self.uses.add("linq")
                return f"{self.expr(n.args[0], 12)}.{f.capitalize()}()"
            return f"Math.{f.capitalize()}({', '.join(a)})"
        if f == "int":
            if t0 == "str": return f"int.Parse({a[0]})"
            return self.par(f"(int) {self.expr(n.args[0], 11)}", 11, prec) if t0 == "float" else a[0]
        if f == "float":
            if t0 == "str": return f"double.Parse({a[0]})"
            return self.par(f"(double) {self.expr(n.args[0], 11)}", 11, prec) if t0 != "float" else a[0]
        if f == "str": return a[0] if t0 == "str" else f"{self.expr(n.args[0], 12)}.ToString()"
        return "Console.ReadLine()"

    def ex_method(self, n, prec):
        o = self.expr(n.obj, 12)
        if n.name == "append": return f"{o}.Add({self.args(n.args)})"
        if n.name == "sort": return f"{o}.Sort()"
        return f"{o}.{'ToUpper' if n.name == 'upper' else 'ToLower'}()"

    def ex_index(self, n, prec):
        s = f"{self.expr(n.obj, 12)}[{self.expr(n.idx)}]"
        return s if is_list(tt(n.obj)) else s + ".ToString()"

    def ex_list(self, n, prec):
        t = self.ty(tt(n))
        return f"new {t}()" if not n.items else f"new {t} {{ {self.args(n.items)} }}"

    def ex_newlist(self, n, prec):
        self.uses.add("linq")
        return f"Enumerable.Repeat({self.expr(n.value)}, {self.expr(n.size)}).ToList()"

    def print_stmt(self, s):
        fn = "WriteLine" if s.nl else "Write"
        if not s.args: self.w(f"Console.{fn}();")
        elif len(s.args) == 1: self.w(f"Console.{fn}({self.expr(s.args[0])});")
        else:
            self.w(f"Console.{fn}({self.concat_expr(self.print_parts(s.args), 0)});")

    def st_for_each(self, s):
        self.w(f"foreach (var {s.var} in {self.expr(s.iter)}) {{")
        self.sub(s.body)
        self.w("}")

    def func(self, f):
        self.cm_lines(f.comments)
        if self.is_entry(f):
            self.w("static void Main() {")
            self.lv += 1
            self.block(self.p.main_body)
            self.lv -= 1
        else:
            ps = ", ".join(f"{self.ty(p.type)} {p.name}" for p in f.params)
            self.w(f"static {self.ty(f.rtype)} {f.name}({ps}) {{")
        self.sub(f.body)
        self.w("}")

    def generate(self):
        p = self.p
        self.lv = 1
        for g in p.globals:
            self.cm_lines(g.comments)
            self.w(f"static {self.ty(g.vtype)} {g.name}" + (f" = {self.expr(g.value)};" if g.value is not None else ";"))
        if p.globals: self.w()
        has_entry = any(self.is_entry(f) for f in p.funcs)
        for f in p.funcs:
            self.func(f)
            self.w()
        if not has_entry and p.main_body:
            self.w("static void Main() {")
            self.sub(p.main_body)
            self.w("}")
        body = "\n".join(self.out).rstrip()
        head = "using System;\n"
        if "generic" in self.uses or "linq" in self.uses: head += "using System.Collections.Generic;\n"
        if "linq" in self.uses: head += "using System.Linq;\n"
        return f"{head}\nclass Program\n{{\n{body}\n}}\n"


# ---------------------------------------------------------------- C / C++

class CppEmitter(CBase):
    NULL = "nullptr"

    def ty(self, t):
        t = t if t == "void" else norm(t)
        if is_list(t):
            self.uses.add("vector")
            return f"vector<{self.ty(t[5:])}>"
        return {"int": "int", "float": "double", "str": "string", "bool": "bool", "void": "void"}[t]

    def floor_call(self, s):
        self.uses.add("cmath")
        return f"floor({s})"

    def power(self, n, prec):
        self.uses.add("cmath")
        s = f"pow({self.expr(n.l)}, {self.expr(n.r)})"
        return self.par("(int) " + s, 11, prec) if tt(n) == "int" else s

    def concat(self, n, prec):
        if n.l.kind == "str": l = f"string({self.expr(n.l)})"
        else: l = self.expr(n.l, 9) if tt(n.l) == "str" else self.as_string(n.l)
        r = self.expr(n.r, 10) if tt(n.r) == "str" else self.as_string(n.r)
        return self.par(f"{l} + {r}", 9, prec)

    def as_string(self, p):
        if isinstance(p, str): return quote(p)
        t = tt(p)
        if p.kind == "fixed" or t == "str": return self.expr(p, 10)
        if t == "bool": return f'string({self.expr(p, 1)} ? "true" : "false")'
        return f"to_string({self.expr(p)})"

    def ex_fstr(self, n, prec):
        parts = self.parts_of(n)
        if not parts: return 'string("")'
        pieces = [self.as_string(p) for p in parts]
        if isinstance(parts[0], str): pieces[0] = f"string({pieces[0]})"
        return pieces[0] if len(pieces) == 1 else self.par(" + ".join(pieces), 9, prec)

    def ex_fixed(self, n, prec):
        self.uses.update(("fixed", "sstream"))
        return f"_fixed({self.expr(n.x)}, {n.digits})"

    def ex_call(self, n, prec):
        f, a = n.f, [self.expr(x) for x in n.args]
        if f in self.funcs or f not in BUILTINS or f == "__print":
            return f"{f}({', '.join(a)})"
        t0 = tt(n.args[0]) if n.args else ""
        if f == "len": return self.par(f"(int) {self.expr(n.args[0], 12)}.size()", 11, prec)
        if f in ("abs", "sqrt", "pow"):
            self.uses.add("cmath")
            return f"{f}({', '.join(a)})"
        if f in ("floor", "ceil"):
            self.uses.add("cmath")
            return self.par(f"(int) {f}({a[0]})", 11, prec)
        if f in ("min", "max"):
            if len(a) == 1:
                self.uses.add("algorithm")
                o = self.expr(n.args[0], 12)
                return self.par(f"*{f}_element({o}.begin(), {o}.end())", 11, prec)
            self.uses.add("algorithm")
            if tt(n.args[0]) != tt(n.args[1]): return f"{f}<double>({', '.join(a)})"
            return f"{f}({', '.join(a)})"
        if f == "int":
            if t0 == "str": return f"stoi({a[0]})"
            return self.par(f"(int) {self.expr(n.args[0], 11)}", 11, prec) if t0 == "float" else a[0]
        if f == "float":
            if t0 == "str": return f"stod({a[0]})"
            return self.par(f"(double) {self.expr(n.args[0], 11)}", 11, prec) if t0 != "float" else a[0]
        if f == "str": return self.as_string(n.args[0])
        self.uses.add("input")
        return "_input()"

    def ex_method(self, n, prec):
        o = self.expr(n.obj, 12)
        if n.name == "append": return f"{o}.push_back({self.args(n.args)})"
        if n.name == "sort":
            self.uses.add("algorithm")
            return f"sort({o}.begin(), {o}.end())"
        self.uses.add("case")
        return f"_{n.name}({self.expr(n.obj)})"

    def ex_index(self, n, prec):
        if is_list(tt(n.obj)): return f"{self.expr(n.obj, 12)}[{self.expr(n.idx)}]"
        return f"string(1, {self.expr(n.obj, 12)}[{self.expr(n.idx)}])"

    def ex_list(self, n, prec):
        t = self.ty(tt(n))
        return f"{t}()" if not n.items else f"{t}{{{self.args(n.items)}}}"

    def ex_newlist(self, n, prec):
        return f"{self.ty(tt(n))}({self.expr(n.size)}, {self.expr(n.value)})"

    def print_stmt(self, s):
        items = self.print_parts(s.args)
        chain = []
        for it in items:
            if isinstance(it, str): chain.append(quote(it))
            elif it.kind == "fixed": chain.append(self.expr(it, 9))
            elif tt(it) == "bool": chain.append(f'({self.expr(it, 1)} ? "true" : "false")')
            else:
                if is_list(tt(it)): self.uses.add("vecprint")
                chain.append(self.expr(it, 9))
        if s.nl: chain.append("endl")
        self.w("cout << " + " << ".join(chain) + ";" if chain else "cout;")

    def st_ret(self, s):
        if self.cur_fn is not None and self.is_entry(self.cur_fn):
            self.w("return 0;")
        else:
            super().st_ret(s)

    def st_for_each(self, s):
        self.w(f"for (auto {s.var} : {self.expr(s.iter)}) {{")
        self.sub(s.body)
        self.w("}")

    def sig(self, f):
        ps = []
        for p in f.params:
            t = self.ty(p.type)
            if is_list(norm(p.type)): t = t + "&" if p.mutated else f"const {t}&"
            ps.append(f"{t} {p.name}")
        return f"{self.ty(f.rtype)} {f.name}({', '.join(ps)})"

    def func(self, f):
        self.cm_lines(f.comments)
        self.cur_fn = f
        if self.is_entry(f):
            self.w("int main() {")
            self.lv += 1
            self.block(self.p.main_body)
            self.lv -= 1
            self.sub(f.body)
            self.lv += 1
            self.w("return 0;")
            self.lv -= 1
        else:
            self.w(self.sig(f) + " {")
            self.sub(f.body)
        self.w("}")
        self.cur_fn = None

    def generate(self):
        p = self.p
        for g in p.globals:
            self.cm_lines(g.comments)
            self.w(f"{self.ty(g.vtype)} {g.name}" + (f" = {self.expr(g.value)};" if g.value is not None else ";"))
        if p.globals: self.w()
        others = [f for f in p.funcs if not self.is_entry(f)]
        if len(others) > 1:
            for f in others: self.w(self.sig(f) + ";")
            self.w()
        has_entry = any(self.is_entry(f) for f in p.funcs)
        for f in p.funcs:
            self.func(f)
            self.w()
        if not has_entry and p.main_body:
            self.w("int main() {")
            self.sub(p.main_body)
            self.lv += 1
            self.w("return 0;")
            self.lv -= 1
            self.w("}")
        body = "\n".join(self.out).rstrip()
        u = self.uses
        inc = ["iostream", "string"]
        if "vector" in u or "vecprint" in u: inc.append("vector")
        if "cmath" in u: inc.append("cmath")
        if "algorithm" in u: inc.append("algorithm")
        if "sstream" in u: inc += ["sstream", "iomanip"]
        if "case" in u: inc.append("cctype")
        head = "".join(f"#include <{i}>\n" for i in inc) + "\nusing namespace std;\n\n"
        helpers = []
        if "input" in u:
            helpers.append("string _input() {\n    string s;\n    getline(cin, s);\n    return s;\n}\n")
        if "fixed" in u:
            helpers.append("string _fixed(double x, int digits) {\n    ostringstream o;\n"
                           "    o << fixed << setprecision(digits) << x;\n    return o.str();\n}\n")
        if "case" in u:
            helpers.append("string _upper(string s) {\n    for (auto& c : s) c = toupper(c);\n    return s;\n}\n")
            helpers.append("string _lower(string s) {\n    for (auto& c : s) c = tolower(c);\n    return s;\n}\n")
        if "vecprint" in u:
            helpers.append("template <typename T>\nostream& operator<<(ostream& os, const vector<T>& v) {\n"
                           "    os << \"[\";\n    for (size_t i = 0; i < v.size(); ++i) {\n"
                           "        if (i) os << \", \";\n        os << v[i];\n    }\n    return os << \"]\";\n}\n")
        return head + ("\n".join(helpers) + "\n" if helpers else "") + body + "\n"


# ---------------------------------------------------------------- Rust

class RustEmitter(Emitter):
    PREC = {"or": 1, "and": 2, "==": 3, "!=": 3, "<": 3, ">": 3, "<=": 3, ">=": 3, "|": 4, "^": 5, "&": 6,
            "<<": 7, ">>": 7, "+": 8, "-": 8, "*": 9, "/": 9, "%": 9}

    def ty(self, t):
        t = t if t == "void" else norm(t)
        if is_list(t): return f"Vec<{self.ty(t[5:])}>"
        return {"int": "i64", "float": "f64", "str": "String", "bool": "bool", "void": "()"}[t]

    def coerce(self, n, want, prec=0):
        """Converte int->f64 quando necessário (Rust não promove tipos)."""
        if want == "float" and tt(n) == "int":
            if n.kind == "num": return n.v + (".0_f64" if prec >= 12 else ".0")
            return f"({self.expr(n, 10)} as f64)"
        if want == "float" and n.kind == "num" and prec >= 12:
            return f"({n.v}_f64)" if n.v.startswith("-") else f"{n.v}_f64"
        return self.expr(n, prec)

    def own(self, n, want=None):
        """Valor que será movido/armazenado: strings literais e nomes viram donos."""
        if want == "float": return self.coerce(n, "float")
        t = tt(n)
        if t == "str" and n.kind in ("str", "name", "index"): return self.expr(n, 12) + ".to_string()"
        if is_list(t) and n.kind == "name": return self.expr(n, 12) + ".clone()"
        return self.expr(n)

    # expressões
    def ex_num(self, n, prec): return f"({n.v})" if n.v.startswith("-") and prec >= 11 else n.v
    def ex_str(self, n, prec): return quote(n.v)
    def ex_bool(self, n, prec): return "true" if n.v else "false"
    def ex_null(self, n, prec): return "None"
    def ex_name(self, n, prec): return n.v

    def ex_un(self, n, prec):
        op = "!" if n.op == "not" else n.op
        return self.par(op + self.expr(n.x, 11), 11, prec)

    def ex_bin(self, n, prec):
        op = getattr(n, "res", n.op)
        lt, rt = tt(n.l), tt(n.r)
        if op == "+" and tt(n) == "str": return self.fmt_macro(self.flatten_concat(n))
        if op == "//":
            if lt == "int" and rt == "int": return self.par(f"{self.expr(n.l, 9)} / {self.expr(n.r, 10)}", 9, prec)
            return f"({self.coerce(n.l, 'float', 9)} / {self.coerce(n.r, 'float', 10)}).floor()"
        if op == "/":
            return self.par(f"{self.coerce(n.l, 'float', 9)} / {self.coerce(n.r, 'float', 10)}", 9, prec)
        if op == "**":
            if tt(n) == "int": return f"({self.expr(n.l, 10)} as i64).pow({self.expr(n.r, 10)} as u32)"
            return f"({self.coerce(n.l, 'float')} as f64).powf({self.coerce(n.r, 'float')})"
        p = self.PREC[op]
        if op in ("==", "!=", "<", ">", "<=", ">=") and {lt, rt} == {"int", "float"}:
            l, r = self.coerce(n.l, "float", p + 1), self.coerce(n.r, "float", p + 1)
        elif tt(n) == "float":
            l, r = self.coerce(n.l, "float", p), self.coerce(n.r, "float", p + 1)
        else:
            l, r = self.expr(n.l, p), self.expr(n.r, p + 1)
        sym = {"and": "&&", "or": "||"}.get(op, op)
        return self.par(f"{l} {sym} {r}", p, prec)

    def flatten_concat(self, n):
        if n.kind == "bin" and getattr(n, "res", n.op) == "+" and tt(n) == "str":
            return self.flatten_concat(n.l) + self.flatten_concat(n.r)
        return [n]

    def fmt_macro(self, parts, name="format"):
        fmt, args = [], []
        for p in parts:
            if isinstance(p, str) or p.kind == "str":
                s = p if isinstance(p, str) else p.v
                fmt.append(s.replace("{", "{{").replace("}", "}}"))
            elif p.kind == "fixed":
                fmt.append("{:." + str(p.digits) + "}")
                args.append(self.coerce(p.x, "float"))
            else:
                fmt.append("{:?}" if is_list(tt(p)) else "{}")
                args.append(self.expr(p))
        text = quote("".join(fmt))
        return f"{name}!({', '.join([text] + args)})"

    def ex_fstr(self, n, prec): return self.fmt_macro(self.parts_of(n))
    def ex_fixed(self, n, prec): return self.fmt_macro([n])
    def ex_tern(self, n, prec): return self.par(f"if {self.expr(n.c)} {{ {self.expr(n.a)} }} else {{ {self.expr(n.b)} }}", 0, prec)

    def ex_list(self, n, prec):
        return "Vec::new()" if not n.items else f"vec![{', '.join(self.own(i) for i in n.items)}]"

    def ex_newlist(self, n, prec):
        return f"vec![{self.own(n.value)}; {self.expr(n.size, 10)} as usize]"

    def idx(self, e):
        if e.kind == "num" and not e.v.startswith("-"): return e.v
        return f"{self.expr(e, 10)} as usize"

    def ex_index(self, n, prec):
        if is_list(tt(n.obj)): return f"{self.expr(n.obj, 12)}[{self.idx(n.idx)}]"
        return f"{self.expr(n.obj, 12)}.chars().nth({self.expr(n.idx, 10)} as usize).unwrap().to_string()"

    def ex_call(self, n, prec):
        f = n.f
        if f in self.funcs and f != "__print":
            callee = self.funcs[f]
            out = []
            for i, a in enumerate(n.args):
                pt = norm(callee.params[i].type) if i < len(callee.params) else None
                if pt == "str":
                    out.append(self.expr(a) if a.kind == "str" else f"&{self.expr(a, 12)}")
                elif pt and is_list(pt):
                    ref_params = {q.name for q in (self.cur_fn.params if self.cur_fn else []) if is_list(norm(q.type))}
                    if a.kind == "name" and a.v in ref_params:
                        out.append(self.expr(a))            # já é uma referência: apenas repassa
                    else:
                        out.append(("&mut " if callee.params[i].mutated else "&") + self.expr(a, 12))
                else:
                    out.append(self.coerce(a, pt) if pt else self.expr(a))
            return f"{f}({', '.join(out)})"
        if f not in BUILTINS or f == "__print":
            return f"{f}({self.args(n.args)})"
        x = n.args[0] if n.args else None
        t0 = tt(x) if x is not None else ""
        if f == "len": return self.par(f"{self.expr(x, 12)}.len() as i64", 10, prec)
        if f == "abs":
            if x.kind == "num": return f"({x.v}_{'f64' if t0 == 'float' else 'i64'}).abs()"
            return f"{self.expr(x, 12)}.abs()"
        if f == "sqrt": return f"{self.coerce(x, 'float', 12)}.sqrt()"
        if f == "pow": return f"{self.coerce(x, 'float', 12)}.powf({self.coerce(n.args[1], 'float')})"
        if f in ("floor", "ceil"): return self.par(f"{self.coerce(x, 'float', 12)}.{f}() as i64", 10, prec)
        if f in ("min", "max"):
            if len(n.args) == 1:
                o = self.expr(x, 12)
                if elem_of(t0) == "float":
                    init, fn = ("f64::INFINITY", "min") if f == "min" else ("f64::NEG_INFINITY", "max")
                    return f"{o}.iter().cloned().fold({init}, f64::{fn})"
                return f"*{o}.iter().{f}().unwrap()"
            if {tt(n.args[0]), tt(n.args[1])} == {"int"}:
                return f"std::cmp::{f}({self.args(n.args)})"
            return f"{self.coerce(n.args[0], 'float', 12)}.{f}({self.coerce(n.args[1], 'float')})"
        if f == "int":
            if t0 == "str": return f"{self.expr(x, 12)}.trim().parse::<i64>().unwrap()"
            return self.par(f"{self.expr(x, 10)} as i64", 10, prec) if t0 in ("float", "bool") else self.expr(x, prec)
        if f == "float":
            if t0 == "str": return f"{self.expr(x, 12)}.trim().parse::<f64>().unwrap()"
            return self.coerce(x, "float", prec)
        if f == "str": return self.expr(x, 12) + ".to_string()"
        return ("{ let mut s = String::new(); std::io::stdin().read_line(&mut s).unwrap(); s.trim().to_string() }")

    def ex_method(self, n, prec):
        o = self.expr(n.obj, 12)
        if n.name == "append": return f"{o}.push({self.own(n.args[0])})"
        if n.name == "sort":
            if elem_of(tt(n.obj)) == "float": return f"{o}.sort_by(|a, b| a.partial_cmp(b).unwrap())"
            return f"{o}.sort()"
        return f"{o}.{'to_uppercase' if n.name == 'upper' else 'to_lowercase'}()"

    # comandos
    def cond(self, c): return self.expr(c)

    def st_expr(self, s): self.w(self.expr(s.e) + ";")
    def st_brk(self, s): self.w("break;")
    def st_cont(self, s): self.w("continue;")

    def st_print(self, s):
        name = "println" if s.nl else "print"
        if not s.args:
            self.w(f"{name}!();")
            return
        self.w(self.fmt_macro(self.print_parts(s.args), name) + ";")

    def st_ret(self, s):
        if s.value is None:
            self.w("return;")
            return
        want = norm(self.cur_fn.rtype) if self.cur_fn is not None and self.cur_fn.rtype != "void" else None
        self.w(f"return {self.own(s.value, want)};")

    def st_decl(self, s):
        t = norm(s.vtype)
        if s.value is None:
            self.w(f"let mut {s.name}: {self.ty(t)};")
            return
        kw = "let mut" if s.mutable else "let"
        self.w(f"{kw} {s.name}: {self.ty(t)} = {self.own(s.value, t if t == 'float' else None)};")

    def st_assign(self, s):
        tg, tgt = s.target, self.expr(s.target)
        t = tt(tg)
        if s.op != "=" and t == "str":
            self.w(f"{tgt} = format!(\"{{}}{{}}\", {tgt}, {self.expr(s.value)});")
        else:
            self.w(f"{tgt} {s.op} {self.own(s.value, 'float' if t == 'float' else None)};")

    def st_while(self, s):
        if s.cond.kind == "bool" and s.cond.v: self.w("loop {")
        else: self.w(f"while {self.cond(s.cond)} {{")
        self.sub(s.body)
        self.w("}")

    def st_if(self, s):
        head = f"if {self.cond(s.cond)} {{"
        while True:
            self.w(head)
            self.sub(s.body)
            oe = s.orelse
            if len(oe) == 1 and oe[0].kind == "if" and not oe[0].comments:
                s = oe[0]
                head = f"}} else if {self.cond(s.cond)} {{"
                continue
            if oe:
                self.w("} else {")
                self.sub(oe)
            self.w("}")
            break

    def st_for_range(self, s):
        start, stop = self.expr(s.start, 7), self.expr(s.stop, 7)
        step = s.step
        if step is None or (step.kind == "num" and step.v == "1"):
            rng = f"{start}..{stop}"
        elif step.kind == "num" and step.v.startswith("-"):
            k = step.v[1:]
            lo = str(int(s.stop.v) + 1) if (s.stop.kind == "num" and s.stop.type == "int") else f"{stop} + 1"
            rng = f"({lo}..={start}).rev()" + ("" if k == "1" else f".step_by({k})")
        else:
            rng = f"({start}..{stop}).step_by({self.expr(step)} as usize)"
        self.w(f"for {s.var} in {rng} {{")
        self.sub(s.body)
        self.w("}")

    def st_for_each(self, s):
        t = tt(s.iter)
        it = self.expr(s.iter, 12)
        src = f"{it}.chars().map(|c| c.to_string())" if t == "str" else f"{it}.iter().cloned()"
        self.w(f"for {s.var} in {src} {{")
        self.sub(s.body)
        self.w("}")

    def sig(self, f):
        ps = []
        for p in f.params:
            t = norm(p.type)
            if t == "str": ty = "&str"
            elif is_list(t): ty = ("&mut " if p.mutated else "&") + self.ty(t)
            else: ty = self.ty(t)
            ps.append(f"{'mut ' if p.assigned and not is_list(t) and t != 'str' else ''}{p.name}: {ty}")
        ret = "" if f.rtype == "void" else f" -> {self.ty(f.rtype)}"
        return f"fn {f.name}({', '.join(ps)}){ret}"

    def func(self, f):
        self.cm_lines(f.comments)
        self.cur_fn = f
        if self.is_entry(f):
            self.w("fn main() {")
            self.lv += 1
            self.block(self.p.main_body)
            self.lv -= 1
        else:
            self.w(self.sig(f) + " {")
        self.sub(f.body)
        self.w("}")
        self.cur_fn = None

    def generate(self):
        p = self.p
        for g in p.globals:
            self.cm_lines(g.comments)
            t = norm(g.vtype)
            if is_list(t):
                self.w(f"// TODO: global '{g.name}' do tipo lista não é suportado como const em Rust")
                continue
            ty = "&str" if t == "str" else self.ty(t)
            self.w(f"const {g.name}: {ty} = {self.expr(g.value) if g.value is not None else '0'};")
        if p.globals: self.w()
        has_entry = any(self.is_entry(f) for f in p.funcs)
        for f in p.funcs:
            self.func(f)
            self.w()
        if not has_entry and p.main_body:
            self.w("fn main() {")
            self.sub(p.main_body)
            self.w("}")
        return "\n".join(self.out).rstrip() + "\n"


# ============================================================
# 10. FACHADA DO TRANSPILADOR
# ============================================================

EMITTERS = {"Python": PyEmitter, "JavaScript": JSEmitter, "Java": JavaEmitter, "C#": CSEmitter,
            "C/C++": CppEmitter, "Rust": RustEmitter}
PARSER_KEY = {"JavaScript": "js", "Java": "java", "C#": "cs", "C/C++": "cpp", "Rust": "rust"}


def detect_code_language(code):
    score = {k: 0 for k in CODE_LANGS}
    rules = {
        "Python": [r"^\s*def \w+\(.*\)\s*(->.*)?:", r"^\s*(elif|except)\b", r"^\s*import \w+\s*$", r"\bprint\(",
                   r":\s*$", r"\bself\b", r"^\s*from \w+ import"],
        "JavaScript": [r"\bfunction\b", r"console\.log", r"\b(let|const|var)\s+\w+", r"=>", r"===", r"\bundefined\b"],
        "Java": [r"System\.out\.print", r"public\s+static\s+void\s+main", r"String\[\]", r"\bimport java\.",
                 r"public\s+class", r"ArrayList<"],
        "C#": [r"Console\.Write", r"using System", r"static\s+void\s+Main", r"\bnamespace\b", r"List<\w+>",
               r"\bstring\s+\w+\s*="],
        "C/C++": [r"#include", r"\bcout\b", r"std::", r"\bint\s+main\s*\(", r"\bprintf\s*\(", r"using namespace",
                  r"vector<"],
        "Rust": [r"\bfn\s+\w+", r"println!", r"\blet\s+mut\b", r"->\s*\w+\s*\{", r"\bVec<", r"\bi32\b|\bi64\b|\bu32\b"],
    }
    for lang, pats in rules.items():
        for pat in pats:
            score[lang] += len(re.findall(pat, code, re.M))
    best = max(score, key=lambda k: score[k])
    return best if score[best] > 0 else "Python"


@dataclass
class CodeResult:
    text: str
    warnings: list
    detected: str
    elapsed_ms: float


class ScriptEngine:
    @staticmethod
    def parse(code, lang):
        if lang == "Python":
            return PyParser(code).parse()
        return CLikeParser(code, PARSER_KEY[lang]).parse()

    @staticmethod
    def translate_script(code, source, target):
        t0 = time.perf_counter()
        if not code.strip():
            return CodeResult("", [], source, 0.0)
        detected = detect_code_language(code) if source == AUTO else source
        try:
            prog = ScriptEngine.parse(code, detected)
            prepare(prog)
            Annotator(prog).run()
            emitter = EMITTERS[target](prog)
            text = emitter.generate()
        except TranslateError:
            raise
        except RecursionError:
            raise TranslateError("Código excessivamente aninhado para ser traduzido.")
        except Exception as e:   # falha inesperada: informa sem derrubar a interface
            raise TranslateError(f"Não foi possível traduzir este código ({type(e).__name__}: {e}).")
        seen, warns = set(), []
        for w in prog.warnings:
            if w not in seen:
                seen.add(w); warns.append(w)
        return CodeResult(text, warns, detected, (time.perf_counter() - t0) * 1000)


# ============================================================
# 11. INTERFACE GRÁFICA
# ============================================================

# ---------- realce de sintaxe ----------

def _fmt(color, bold=False, italic=False):
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold: f.setFontWeight(700)
    if italic: f.setFontItalic(True)
    return f

_KEYWORDS = {
    "Python": "and as assert break class continue def del elif else except finally for from global if import in is "
              "lambda not or pass raise return try while with yield True False None",
    "JavaScript": "async await break case catch class const continue default do else export extends finally for function "
                  "if import in instanceof let new of return static super switch this throw try typeof var void while "
                  "yield true false null undefined",
    "Java": "abstract break case catch class continue default do else enum extends final finally for if implements "
            "import instanceof interface new package private protected public return static super switch this throw "
            "throws try void volatile while true false null",
    "C#": "abstract as base break case catch class const continue default do else enum finally for foreach if in "
          "interface internal is namespace new null override private protected public readonly return static struct "
          "switch this throw try using virtual void while true false",
    "C/C++": "auto break case catch class const continue default do else enum for goto if namespace new nullptr "
             "private protected public return static struct switch template this throw try typedef using virtual "
             "void while true false NULL",
    "Rust": "as break const continue else enum fn for if impl in let loop match mod mut pub ref return self static "
            "struct trait use where while true false",
}
_TYPES = ("int long short byte float double bool boolean char string String str void auto var i8 i16 i32 i64 u8 u16 "
          "u32 u64 f32 f64 usize isize Vec Option List ArrayList vector size_t Integer Double Boolean")


class SyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document, lang="Python"):
        super().__init__(document)
        self.rules = []
        self.set_language(lang)

    def set_language(self, lang):
        if getattr(self, "lang", None) == lang and self.rules:
            return
        self.lang = lang
        R = []
        if lang == "logic":
            words = (r"\b(?:AND|OR|NOT|XOR|NAND|NOR|XNOR|IMPLIES|IFF|E|OU|NAO|NÃO|IMPLICA|EQUIVALE|SSE|and|or|not)\b")
            R.append((r"[()]", _fmt("#8290a5")))
            R.append((r"\b[A-Za-z_]\w*\b", _fmt("#9cc4f5")))
            R.append((words, _fmt("#c586c0", bold=True)))
            R.append((r"[∧∨⊕¬↑↓⊙→⇒↔⇔!~^&|=<>\-]+", _fmt("#eed49f", bold=True)))
            R.append((r"\b(?:[01]|true|false|True|False|verdadeiro|falso|VERDADEIRO|FALSO)\b", _fmt("#f5a97f")))
            R.append((r"\[ERRO[^\]]*\]", _fmt("#ff6b6b", bold=True)))
        else:
            kws = _KEYWORDS.get(lang, "")
            R.append((r"\b[A-Za-z_]\w*(?=\s*\()", _fmt("#8bb4f7")))
            R.append((r"\b(?:" + "|".join(kws.split()) + r")\b", _fmt("#c586c0", bold=True)))
            R.append((r"\b(?:" + "|".join(_TYPES.split()) + r")\b", _fmt("#4ec9b0")))
            R.append((r"\b\d+(?:\.\d+)?\b", _fmt("#f5a97f")))
            if lang in ("C/C++", "C#"): R.append((r"^\s*#\s*\w+.*$", _fmt("#c586c0")))
            R.append((r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'" + ("|`(?:\\\\.|[^`\\\\])*`" if lang == "JavaScript" else ""),
                      _fmt("#a6da95")))
            R.append((r"#.*$" if lang == "Python" else r"//.*$", _fmt("#6c7a89", italic=True)))
        self.rules = [(re.compile(p), f) for p, f in R]
        self.rehighlight()

    def highlightBlock(self, text):
        for rx, fmt in self.rules:
            for m in rx.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


# ---------- editor com numeração de linhas ----------

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_width(), 0)

    def paintEvent(self, event):
        self.editor.paint_line_numbers(event)


def mono_font(size=11):
    f = QFont()
    f.setFamilies(["JetBrains Mono", "Cascadia Code", "Consolas", "Menlo", "DejaVu Sans Mono", "monospace"])
    f.setStyleHint(QFont.StyleHint.Monospace)
    f.setPointSize(size)
    return f


class CodeEditor(QPlainTextEdit):
    fileDropped = Signal(str)

    def __init__(self, read_only=False, lang="Python"):
        super().__init__()
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setFont(mono_font())
        self.setReadOnly(read_only)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self.error_lines = set()
        self.line_area = LineNumberArea(self)
        self.highlighter = SyntaxHighlighter(self.document(), lang)
        self.blockCountChanged.connect(self.update_margin)
        self.updateRequest.connect(self.update_area)
        self.cursorPositionChanged.connect(self.refresh_selections)
        self.update_margin(0)
        self.refresh_selections()

    def line_number_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 16 + self.fontMetrics().horizontalAdvance("9") * max(2, digits)

    def update_margin(self, _=0):
        self.setViewportMargins(self.line_number_width(), 0, 0, 0)

    def update_area(self, rect, dy):
        if dy:
            self.line_area.scroll(0, dy)
        else:
            self.line_area.update(0, rect.y(), self.line_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_margin(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_width(), cr.height()))

    def paint_line_numbers(self, event):
        painter = QPainter(self.line_area)
        painter.fillRect(event.rect(), QColor("#0e1219"))
        block = self.firstVisibleBlock()
        n = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        h = self.fontMetrics().height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#ff6b6b" if (n + 1) in self.error_lines else "#4d5a70"))
                painter.drawText(0, top, self.line_area.width() - 8, h, Qt.AlignmentFlag.AlignRight, str(n + 1))
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            n += 1

    def set_error_lines(self, lines):
        self.error_lines = set(lines)
        self.refresh_selections()
        self.line_area.update()

    def _selection(self, cursor, color):
        sel = QTextEdit.ExtraSelection()
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(color))
        fmt.setProperty(QTextFormat.Property.FullWidthSelection, True)
        sel.format = fmt
        sel.cursor = cursor
        return sel

    def refresh_selections(self):
        sels = []
        for ln in sorted(self.error_lines):
            block = self.document().findBlockByNumber(ln - 1)
            if block.isValid():
                sels.append(self._selection(QTextCursor(block), "#3a1d24"))
        if not self.isReadOnly():
            cur = self.textCursor()
            cur.clearSelection()
            sels.append(self._selection(cur, "#1a2231"))
        self.setExtraSelections(sels)

    # arrastar e soltar arquivos
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()
        else: super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()
        else: super().dragMoveEvent(e)

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            self.fileDropped.emit(e.mimeData().urls()[0].toLocalFile())
            e.acceptProposedAction()
        else:
            super().dropEvent(e)


# ---------- execução em segundo plano ----------

class TaskSignals(QObject):
    done = Signal(int, object)
    failed = Signal(int, str)


class Task(QRunnable):
    def __init__(self, token, fn, *args):
        super().__init__()
        self.token, self.fn, self.args = token, fn, args
        self.signals = TaskSignals()

    def run(self):
        try:
            result = self.fn(*self.args)
        except TranslateError as e:
            self.signals.failed.emit(self.token, str(e))
        except Exception as e:
            self.signals.failed.emit(self.token, f"Erro inesperado: {e}")
        else:
            self.signals.done.emit(self.token, result)


# ---------- janela principal ----------

def section_label(text):
    lab = QLabel(text)
    lab.setObjectName("sectionLabel")
    return lab


class CodingTranslator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1240, 780)
        self.setMinimumSize(940, 620)
        self.pool = QThreadPool.globalInstance()
        self.logic_token = self.code_token = 0
        self.logic_result = None
        self.code_result = None
        self.settings = QSettings("ThiagoVentura", "CodingTranslator")

        self.timer_logic = self._timer(300, self.translate_logic)
        self.timer_code = self._timer(650, self.translate_script)
        self.timer_detect = self._timer(450, self.refresh_detection)
        self.timer_table = self._timer(120, self.refresh_truth_table)

        self.setup_ui()
        self.apply_theme()
        self.setup_shortcuts()
        self.load_settings()
        self.update_logic_placeholders()
        self.refresh_detection()
        self.on_tab_changed()

    def _timer(self, ms, slot):
        t = QTimer(self)
        t.setSingleShot(True)
        t.setInterval(ms)
        t.timeout.connect(slot)
        return t

    # ---------- construção da interface ----------
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setContentsMargins(22, 18, 22, 8)
        main.setSpacing(12)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel("CODING TRANSLATOR")
        title.setObjectName("mainTitle")
        sub = QLabel("Logic Engine & Code Transpiler  ·  100% offline, sem APIs")
        sub.setObjectName("subtitle")
        titles.addWidget(title)
        titles.addWidget(sub)
        header.addLayout(titles)
        header.addStretch()
        self.btn_import = QPushButton("Importar  (Ctrl+O)")
        self.btn_import.setToolTip("Abra um arquivo de texto, CSV ou código-fonte. Você também pode arrastar arquivos para o editor.")
        self.btn_import.clicked.connect(self.import_file)
        self.btn_export = QPushButton("Exportar  (Ctrl+S)")
        self.btn_export.setToolTip("Salve o resultado em arquivo.")
        self.btn_export.clicked.connect(self.export_file)
        header.addWidget(self.btn_import)
        header.addWidget(self.btn_export)
        main.addLayout(header)

        self.tabs = QTabWidget()
        self.tab_logic, self.tab_code = QWidget(), QWidget()
        self.tabs.addTab(self.tab_logic, "1. Lógica Computacional")
        self.tabs.addTab(self.tab_code, "2. Tradutor de Código")
        self.tabs.currentChanged.connect(self.on_tab_changed)
        main.addWidget(self.tabs, 1)
        self.setup_logic_tab()
        self.setup_code_tab()

        footer = QHBoxLayout()
        self.status_label = QLabel("Pronto para processar.")
        self.status_label.setObjectName("statusLabel")
        self.btn_copy = QPushButton("Copiar resultado  (Ctrl+Shift+C)")
        self.btn_copy.clicked.connect(self.copy_result)
        footer.addWidget(self.status_label, 1)
        footer.addWidget(self.btn_copy)
        main.addLayout(footer)

        credit = QLabel("created by Thiago Ventura")
        credit.setObjectName("credit")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main.addWidget(credit)

    def _center(self, *widgets):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 0, 8, 0)
        lay.setSpacing(8)
        lay.addStretch()
        for x in widgets:
            lay.addWidget(x)
        lay.addStretch()
        return w

    def _splitter(self, left, center, right):
        sp = QSplitter(Qt.Orientation.Horizontal)
        sp.setChildrenCollapsible(False)
        for w in (left, center, right): sp.addWidget(w)
        sp.setStretchFactor(0, 1)
        sp.setStretchFactor(1, 0)
        sp.setStretchFactor(2, 1)
        sp.setSizes([470, 150, 470])
        return sp

    def setup_logic_tab(self):
        lay = QVBoxLayout(self.tab_logic)
        lay.setContentsMargins(10, 10, 10, 10)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.combo_source = QComboBox()
        self.combo_source.addItems([AUTO] + UNIVERSES)
        self.combo_source.setToolTip("Em 'Auto-detectar' cada linha é analisada separadamente.")
        self.combo_source.currentIndexChanged.connect(self.on_logic_option_changed)
        self.combo_common = QComboBox()
        self.combo_common.addItem("-- Inserir fórmula rápida --", "")
        for name, formula in COMMON_FORMULAS:
            self.combo_common.addItem(name, formula)
        self.combo_common.activated.connect(self.insert_common_logic)
        self.text_source = CodeEditor(lang="logic")
        self.text_source.fileDropped.connect(self.load_path)
        self.text_source.textChanged.connect(self.on_logic_changed)
        self.text_source.cursorPositionChanged.connect(lambda: self.timer_table.start())
        for w in (section_label("UNIVERSO DE ORIGEM"), self.combo_source, self.combo_common, self.text_source):
            ll.addWidget(w)

        self.btn_translate = QPushButton("TRADUZIR  →")
        self.btn_translate.setObjectName("translateButton")
        self.btn_translate.setToolTip("Ctrl+Enter ou F5")
        self.btn_translate.clicked.connect(self.translate_action)
        self.btn_swap = QPushButton("⇄  Inverter")
        self.btn_swap.clicked.connect(self.swap_action)
        self.btn_clear = QPushButton("Limpar")
        self.btn_clear.clicked.connect(self.clear_fields)
        self.chk_live_logic = QCheckBox("Tempo real")
        self.chk_live_logic.setChecked(True)
        self.chk_live_logic.setToolTip("Traduz automaticamente enquanto você digita.")
        center = self._center(self.btn_translate, self.btn_swap, self.btn_clear, self.chk_live_logic)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        self.combo_target = QComboBox()
        self.combo_target.addItems(UNIVERSES)
        self.combo_target.setCurrentIndex(2)
        self.combo_target.currentIndexChanged.connect(self.on_logic_option_changed)
        self.result_tabs = QTabWidget()
        self.result_tabs.setObjectName("innerTabs")
        self.text_target = CodeEditor(read_only=True, lang="logic")
        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.verticalHeader().setVisible(False)
        self.table_info = QLabel("Digite uma fórmula para ver a tabela-verdade.")
        self.table_info.setObjectName("hint")
        table_box = QWidget()
        tb = QVBoxLayout(table_box)
        tb.setContentsMargins(0, 6, 0, 0)
        tb.addWidget(self.table_info)
        tb.addWidget(self.table, 1)
        self.text_analysis = QPlainTextEdit()
        self.text_analysis.setReadOnly(True)
        self.text_analysis.setFont(mono_font(10))
        self.text_analysis.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.result_tabs.addTab(self.text_target, "Resultado")
        self.result_tabs.addTab(table_box, "Tabela-verdade")
        self.result_tabs.addTab(self.text_analysis, "Análise")
        for w in (section_label("UNIVERSO DE DESTINO"), self.combo_target, self.result_tabs):
            rl.addWidget(w)
        rl.setStretch(2, 1)
        lay.addWidget(self._splitter(left, center, right))

    def setup_code_tab(self):
        lay = QVBoxLayout(self.tab_code)
        lay.setContentsMargins(10, 10, 10, 10)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.combo_code_src = QComboBox()
        self.combo_code_src.addItems([AUTO] + CODE_LANGS)
        self.combo_code_src.currentIndexChanged.connect(self.on_code_option_changed)
        self.lbl_detected = QLabel("")
        self.lbl_detected.setObjectName("hint")
        self.text_code_src = CodeEditor(lang="Python")
        self.text_code_src.setPlaceholderText("Cole o seu código aqui (ou arraste um arquivo).\n\n"
                                              "Suporta funções, variáveis, if/else, while, for, listas, f-strings e print.")
        self.text_code_src.fileDropped.connect(self.load_path)
        self.text_code_src.textChanged.connect(self.on_code_changed)
        for w in (section_label("LINGUAGEM DE ORIGEM"), self.combo_code_src, self.lbl_detected, self.text_code_src):
            ll.addWidget(w)

        self.btn_trans_code = QPushButton("TRADUZIR CÓDIGO  →")
        self.btn_trans_code.setObjectName("translateButton")
        self.btn_trans_code.setToolTip("Ctrl+Enter ou F5")
        self.btn_trans_code.clicked.connect(self.translate_action)
        self.btn_swap_code = QPushButton("⇄  Inverter")
        self.btn_swap_code.clicked.connect(self.swap_action)
        self.btn_clear_code = QPushButton("Limpar")
        self.btn_clear_code.clicked.connect(self.clear_fields)
        self.chk_live_code = QCheckBox("Tempo real")
        self.chk_live_code.setToolTip("Traduz automaticamente após você parar de digitar.")
        center = self._center(self.btn_trans_code, self.btn_swap_code, self.btn_clear_code, self.chk_live_code)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        self.combo_code_tgt = QComboBox()
        self.combo_code_tgt.addItems(CODE_LANGS)
        self.combo_code_tgt.setCurrentIndex(4)
        self.combo_code_tgt.currentIndexChanged.connect(self.on_code_option_changed)
        self.text_code_tgt = CodeEditor(read_only=True, lang="C/C++")
        self.warn_label = section_label("AVISOS")
        self.warn_box = QPlainTextEdit()
        self.warn_box.setObjectName("warnBox")
        self.warn_box.setReadOnly(True)
        self.warn_box.setMaximumHeight(96)
        self.warn_label.hide()
        self.warn_box.hide()
        for w in (section_label("LINGUAGEM DE DESTINO"), self.combo_code_tgt, self.text_code_tgt,
                  self.warn_label, self.warn_box):
            rl.addWidget(w)
        rl.setStretch(2, 1)
        lay.addWidget(self._splitter(left, center, right))

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Return"), self, self.translate_action)
        QShortcut(QKeySequence("Ctrl+Enter"), self, self.translate_action)
        QShortcut(QKeySequence("F5"), self, self.translate_action)
        QShortcut(QKeySequence("Ctrl+O"), self, self.import_file)
        QShortcut(QKeySequence("Ctrl+S"), self, self.export_file)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, self.copy_result)
        QShortcut(QKeySequence("Ctrl+L"), self, self.clear_fields)
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self.tabs.setCurrentIndex(0))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self.tabs.setCurrentIndex(1))

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #11151d; color: #e5eaf2; font-family: 'Segoe UI', 'Inter', 'Ubuntu', sans-serif; font-size: 12px; }
            QLabel { background: transparent; }
            QLabel#mainTitle { color: #ffffff; font-size: 24px; font-weight: 800; letter-spacing: 3px; }
            QLabel#subtitle { color: #7d8aa0; font-size: 11px; }
            QLabel#sectionLabel { color: #7fa9e8; font-size: 10px; font-weight: bold; letter-spacing: 1.5px; padding-top: 2px; }
            QLabel#hint { color: #7d8aa0; font-size: 11px; }
            QLabel#statusLabel { color: #9aa7bb; }
            QLabel#credit { color: #3d485b; font-size: 9px; letter-spacing: 1px; padding: 0 0 2px 0; }
            QTabWidget::pane { border: 1px solid #2b3647; border-radius: 6px; top: -1px; background-color: #11151d; }
            QTabBar::tab { background-color: #19212d; border: 1px solid #2b3647; padding: 9px 20px; margin-right: 3px; border-top-left-radius: 6px; border-top-right-radius: 6px; color: #9aa7bb; }
            QTabBar::tab:hover { background-color: #212c3b; color: #e5eaf2; }
            QTabBar::tab:selected { background-color: #2864b5; color: white; font-weight: bold; border-color: #2864b5; }
            QTabWidget#innerTabs::pane { border-radius: 6px; }
            QTabWidget#innerTabs QTabBar::tab { padding: 6px 14px; }
            QComboBox { background-color: #19212d; border: 1px solid #2b3647; border-radius: 6px; padding: 8px 10px; min-height: 20px; }
            QComboBox:hover { border-color: #3d5a85; }
            QComboBox QAbstractItemView { background-color: #19212d; selection-background-color: #2864b5; border: 1px solid #2b3647; outline: none; }
            QPlainTextEdit, QTextEdit { background-color: #151b26; border: 1px solid #2b3647; border-radius: 8px; padding: 6px; selection-background-color: #2f5f9e; }
            QPlainTextEdit:focus { border-color: #2864b5; }
            QPlainTextEdit#warnBox { background-color: #241d17; border: 1px solid #5c4524; color: #f0c987; font-size: 11px; }
            QPushButton { background-color: #222d3c; border: 1px solid #33445b; border-radius: 6px; padding: 9px 14px; font-weight: 600; }
            QPushButton:hover { background-color: #2f405a; border-color: #46618a; }
            QPushButton:pressed { background-color: #1b2533; }
            QPushButton#translateButton { background-color: #2864b5; border: none; font-weight: bold; padding: 13px 12px; }
            QPushButton#translateButton:hover { background-color: #3a7bd5; }
            QPushButton#translateButton:pressed { background-color: #1f5299; }
            QCheckBox { spacing: 8px; color: #9aa7bb; }
            QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #3a4a62; border-radius: 4px; background: #19212d; }
            QCheckBox::indicator:checked { background: #2864b5; border-color: #2864b5; }
            QTableWidget { background-color: #151b26; alternate-background-color: #171e2b; border: 1px solid #2b3647; border-radius: 8px; gridline-color: #232d3d; }
            QHeaderView::section { background-color: #1d2635; color: #9cc4f5; border: none; border-right: 1px solid #2b3647; border-bottom: 1px solid #2b3647; padding: 6px 8px; font-weight: bold; }
            QSplitter::handle { background-color: #11151d; }
            QScrollBar:vertical { background: #11151d; width: 11px; margin: 0; }
            QScrollBar::handle:vertical { background: #2f3b4f; border-radius: 5px; min-height: 28px; }
            QScrollBar::handle:vertical:hover { background: #41526e; }
            QScrollBar:horizontal { background: #11151d; height: 11px; margin: 0; }
            QScrollBar::handle:horizontal { background: #2f3b4f; border-radius: 5px; min-width: 28px; }
            QScrollBar::handle:horizontal:hover { background: #41526e; }
            QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
            QToolTip { background-color: #1d2635; color: #e5eaf2; border: 1px solid #33445b; padding: 4px; }
        """)

    # ---------- utilidades de interface ----------
    def set_status(self, text, error=False):
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: #ff6b6b;" if error else "color: #9aa7bb;")

    def on_tab_changed(self, _=0):
        logic = self.tabs.currentIndex() == 0
        self.btn_copy.setText("Copiar resultado  (Ctrl+Shift+C)")
        self.set_status("Pronto para processar.")
        (self.text_source if logic else self.text_code_src).setFocus()

    def update_logic_placeholders(self):
        ex = {MATH: "¬A ∧ B", GATES: "NOT A AND B", PYTHON: "not A and B", CPP: "!A && B"}.get(
            self.combo_source.currentText(), "NOT A AND B   ou   ¬A ∧ B   ou   !A && B")
        self.text_source.setPlaceholderText(
            f"Digite uma fórmula por linha...\n\nExemplo:\n{ex}\n\nOperadores: AND OR NOT XOR NAND NOR XNOR IMPLIES IFF\n"
            "Símbolos: ∧ ∨ ¬ ⊕ → ↔ && || ! ^ -> <->")

    def insert_common_logic(self, index):
        if index > 0:
            formula = self.combo_common.itemData(index)
            cur = self.text_source.toPlainText()
            self.text_source.setPlainText(cur.rstrip("\n") + "\n" + formula if cur.strip() else formula)
            self.combo_common.setCurrentIndex(0)

    # ---------- eventos de edição ----------
    def on_logic_changed(self):
        if self.chk_live_logic.isChecked(): self.timer_logic.start()

    def on_logic_option_changed(self):
        self.update_logic_placeholders()
        if self.text_source.toPlainText().strip() and self.chk_live_logic.isChecked():
            self.timer_logic.start()

    def on_code_changed(self):
        self.timer_detect.start()
        if self.chk_live_code.isChecked(): self.timer_code.start()

    def on_code_option_changed(self):
        self.refresh_detection()
        if self.text_code_src.toPlainText().strip() and self.chk_live_code.isChecked():
            self.timer_code.start()

    def refresh_detection(self):
        text = self.text_code_src.toPlainText()
        sel = self.combo_code_src.currentText()
        if sel == AUTO:
            lang = detect_code_language(text) if text.strip() else None
            self.lbl_detected.setText(f"Detectado: {lang}" if lang else "Linguagem será detectada automaticamente.")
            self.text_code_src.highlighter.set_language(lang or "Python")
        else:
            self.lbl_detected.setText("")
            self.text_code_src.highlighter.set_language(sel)
        self.text_code_tgt.highlighter.set_language(self.combo_code_tgt.currentText())

    # ---------- ações principais ----------
    def translate_action(self):
        if self.tabs.currentIndex() == 0: self.translate_logic()
        else: self.translate_script()

    def _start(self, kind, fn, *args):
        if kind == "logic":
            self.logic_token += 1
            token, done, failed = self.logic_token, self.on_logic_done, self.on_logic_failed
        else:
            self.code_token += 1
            token, done, failed = self.code_token, self.on_code_done, self.on_code_failed
        task = Task(token, fn, *args)
        task.signals.done.connect(done)
        task.signals.failed.connect(failed)
        self.set_status("Processando…")
        self.pool.start(task)

    # --- lógica ---
    def translate_logic(self):
        content = self.text_source.toPlainText()
        if not content.strip():
            self.clear_logic_outputs()
            self.set_status("Pronto para processar.")
            return
        self._start("logic", LogicEngine.process, content, self.combo_source.currentText(),
                    self.combo_target.currentText())

    def on_logic_done(self, token, res):
        if token != self.logic_token: return
        self.logic_result = res
        self.text_target.setPlainText(res.translated)
        self.text_analysis.setPlainText(res.analysis)
        self.text_source.set_error_lines([l.number for l in res.lines if l.error])
        self.refresh_truth_table()
        n_ok = sum(1 for l in res.lines if l.ast is not None)
        info = f"Origem: {res.detected}  ·  " if self.combo_source.currentText() == AUTO else ""
        if res.errors:
            self.set_status(f"{info}{len(res.errors)} erro(s) · {n_ok} fórmula(s) traduzida(s) · primeiro: {res.errors[0]}", True)
        else:
            self.set_status(f"{info}{n_ok} fórmula(s) traduzida(s) em {res.elapsed_ms:.0f} ms.")

    def on_logic_failed(self, token, msg):
        if token == self.logic_token: self.set_status(msg, True)

    def clear_logic_outputs(self):
        self.logic_result = None
        self.text_target.clear()
        self.text_analysis.clear()
        self.text_source.set_error_lines([])
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.table_info.setText("Digite uma fórmula para ver a tabela-verdade.")

    def current_logic_line(self):
        res = self.logic_result
        if res is None: return None
        by_number = {l.number: l for l in res.lines}
        ll = by_number.get(self.text_source.textCursor().blockNumber() + 1)
        if ll is not None and ll.ast is not None: return ll
        return next((l for l in res.lines if l.ast is not None), None)

    def refresh_truth_table(self):
        ll = self.current_logic_line()
        self.table.setUpdatesEnabled(False)
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        if ll is None:
            self.table_info.setText("Nenhuma fórmula válida para exibir." if self.logic_result else
                                    "Digite uma fórmula para ver a tabela-verdade.")
            self.table.setUpdatesEnabled(True)
            return
        try:
            tt_ = truth_table(ll.ast)
        except LogicError as e:
            self.table_info.setText(str(e))
            self.table.setUpdatesEnabled(True)
            return
        headers = tt_.variables + tt_.labels
        nv = len(tt_.variables)
        self.table.setColumnCount(len(headers))
        self.table.setRowCount(len(tt_.rows))
        self.table.setHorizontalHeaderLabels(headers)
        ok, bad = QColor("#7ee787"), QColor("#ff7b72")
        last = len(headers) - 1
        for r, (bits, res) in enumerate(tt_.rows):
            for c, val in enumerate(list(bits) + list(res)):
                item = QTableWidgetItem("1" if val else "0")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                item.setForeground(ok if val else bad)
                if c == last:
                    item.setBackground(QColor("#1d3326" if val else "#35202a"))
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                self.table.setItem(r, c, item)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        total, ones = len(tt_.rows), len(tt_.minterms)
        kind = "tautologia" if ones == total else "contradição" if ones == 0 else "contingência"
        self.table_info.setText(f"Linha {ll.number}: {len(tt_.variables)} variável(is), {total} combinações — {kind} ({ones} verdadeiras)")
        self.table.setUpdatesEnabled(True)

    # --- código ---
    def translate_script(self):
        content = self.text_code_src.toPlainText()
        if not content.strip():
            self.text_code_tgt.clear()
            self.show_warnings([])
            self.set_status("Pronto para processar.")
            return
        self.refresh_detection()
        self._start("code", ScriptEngine.translate_script, content, self.combo_code_src.currentText(),
                    self.combo_code_tgt.currentText())

    def on_code_done(self, token, res):
        if token != self.code_token: return
        self.code_result = res
        self.text_code_tgt.highlighter.set_language(self.combo_code_tgt.currentText())
        self.text_code_tgt.setPlainText(res.text)
        self.show_warnings(res.warnings)
        extra = f"  ·  {len(res.warnings)} aviso(s)" if res.warnings else ""
        self.set_status(f"{res.detected} → {self.combo_code_tgt.currentText()} concluído em {res.elapsed_ms:.0f} ms{extra}.")

    def on_code_failed(self, token, msg):
        if token != self.code_token: return
        self.text_code_tgt.setPlainText("// " + msg)
        self.show_warnings([])
        self.set_status(msg, True)

    def show_warnings(self, warnings):
        has = bool(warnings)
        self.warn_label.setText(f"AVISOS ({len(warnings)})")
        self.warn_label.setVisible(has)
        self.warn_box.setVisible(has)
        self.warn_box.setPlainText("\n".join("• " + w for w in warnings))

    # ---------- inverter / limpar / copiar ----------
    def swap_action(self):
        if self.tabs.currentIndex() == 0: self.swap_logic()
        else: self.swap_code()

    def swap_logic(self):
        res = self.logic_result
        src, tgt = self.combo_source.currentText(), self.combo_target.currentText()
        if src == AUTO: src = res.detected if res else GATES
        if res is None:
            return
        text = "\n".join(l.source if l.error else l.output for l in res.lines)
        self.combo_source.blockSignals(True)
        self.combo_target.blockSignals(True)
        self.combo_source.setCurrentText(tgt)
        self.combo_target.setCurrentText(src)
        self.combo_source.blockSignals(False)
        self.combo_target.blockSignals(False)
        self.text_source.setPlainText(text)
        self.update_logic_placeholders()
        self.translate_logic()

    def swap_code(self):
        res = self.code_result
        if res is None or not res.text.strip(): return
        src = self.combo_code_src.currentText()
        if src == AUTO: src = res.detected
        tgt = self.combo_code_tgt.currentText()
        self.combo_code_src.blockSignals(True)
        self.combo_code_tgt.blockSignals(True)
        self.combo_code_src.setCurrentText(tgt)
        self.combo_code_tgt.setCurrentText(src)
        self.combo_code_src.blockSignals(False)
        self.combo_code_tgt.blockSignals(False)
        self.text_code_src.setPlainText(res.text)
        self.text_code_tgt.clear()
        self.refresh_detection()
        self.translate_script()

    def clear_fields(self):
        if self.tabs.currentIndex() == 0:
            self.text_source.clear()
            self.clear_logic_outputs()
        else:
            self.text_code_src.clear()
            self.text_code_tgt.clear()
            self.code_result = None
            self.show_warnings([])
        self.set_status("Campos limpos.")

    def copy_result(self):
        txt = self.text_target.toPlainText() if self.tabs.currentIndex() == 0 else self.text_code_tgt.toPlainText()
        if txt.strip():
            QApplication.clipboard().setText(txt)
            self.set_status("Resultado copiado para a área de transferência.")

    # ---------- arquivos ----------
    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Importar", "",
            "Todos os suportados (*.txt *.csv *.py *.js *.java *.cs *.c *.cpp *.h *.rs);;Texto (*.txt);;CSV (*.csv);;Código (*.py *.js *.java *.cs *.c *.cpp *.h *.rs);;Todos (*)")
        if path: self.load_path(path)

    def load_path(self, path):
        try:
            p = Path(path)
            with open(p, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
                if p.suffix.lower() == ".csv" and self.tabs.currentIndex() == 0:
                    content = "\n".join(row[0] for row in csv.reader(f) if row)
                else:
                    content = f.read().replace("\r\n", "\n")
        except OSError as e:
            QMessageBox.warning(self, APP_NAME, f"Não foi possível abrir o arquivo:\n{e}")
            return
        if self.tabs.currentIndex() == 0:
            self.text_source.setPlainText(content)
        else:
            lang = EXT_LANG.get(p.suffix.lower())
            if lang: self.combo_code_src.setCurrentText(lang)
            self.text_code_src.setPlainText(content)
        self.set_status(f"Arquivo carregado: {p.name}")

    def export_file(self):
        try:
            if self.tabs.currentIndex() == 0: self.export_logic()
            else: self.export_code()
        except OSError as e:
            QMessageBox.warning(self, APP_NAME, f"Não foi possível salvar o arquivo:\n{e}")

    def export_logic(self):
        res = self.logic_result
        if res is None or not res.translated.strip(): return
        path, flt = QFileDialog.getSaveFileName(
            self, "Exportar", "resultado.txt",
            "Texto (*.txt);;CSV entrada/saída (*.csv);;CSV tabela-verdade (*.csv)")
        if not path: return
        if "tabela" in flt:
            ll = self.current_logic_line()
            if ll is None: return
            tt_ = truth_table(ll.ast)
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(tt_.variables + tt_.labels)
                for bits, r in tt_.rows:
                    w.writerow([int(b) for b in bits] + [int(b) for b in r])
        elif path.lower().endswith(".csv") or "entrada" in flt:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(["linha", "entrada", "saida"])
                for l in res.lines:
                    if l.source.strip(): w.writerow([l.number, l.source, l.output])
        else:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(res.translated)
        self.set_status(f"Exportado: {Path(path).name}")

    def export_code(self):
        txt = self.text_code_tgt.toPlainText()
        if not txt.strip(): return
        lang = self.combo_code_tgt.currentText()
        ext = LANG_EXT[lang]
        name = "Main.java" if lang == "Java" else f"translated{ext}"
        path, _ = QFileDialog.getSaveFileName(self, "Exportar", name, f"{lang} (*{ext});;Texto (*.txt)")
        if not path: return
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt if txt.endswith("\n") else txt + "\n")
        self.set_status(f"Exportado: {Path(path).name}")

    # ---------- preferências ----------
    def load_settings(self):
        try:
            geo = self.settings.value("geometry")
            if geo: self.restoreGeometry(geo)
            for key, combo in (("logic_src", self.combo_source), ("logic_tgt", self.combo_target),
                               ("code_src", self.combo_code_src), ("code_tgt", self.combo_code_tgt)):
                val = self.settings.value(key)
                if val and combo.findText(str(val)) >= 0: combo.setCurrentText(str(val))
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            self.settings.setValue("geometry", self.saveGeometry())
            for key, combo in (("logic_src", self.combo_source), ("logic_tgt", self.combo_target),
                               ("code_src", self.combo_code_src), ("code_tgt", self.combo_code_tgt)):
                self.settings.setValue(key, combo.currentText())
        except Exception:
            pass
        self.pool.waitForDone(1500)
        super().closeEvent(event)


# ============================================================
# 12. EXECUÇÃO
# ============================================================

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    # É obrigatório manter a instância em uma variável (window)
    # para que o Python não a apague da memória imediatamente.
    window = CodingTranslator()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
