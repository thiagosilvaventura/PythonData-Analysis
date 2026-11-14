import sys
import re
import csv
from pathlib import Path
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QComboBox, QTextEdit, QPushButton,
    QLabel, QFileDialog, QMessageBox, QSplitter,
    QFrame, QStatusBar, QTabWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut

# ============================================================
# 1. CONFIGURAÇÕES E UNIVERSOS LÓGICOS
# ============================================================

UNIVERSES = ["Matemática Discreta", "Portas Lógicas", "Python", "C/C++"]

OPERATORS = {"AND": 5, "NAND": 5, "XOR": 4, "XNOR": 4, "OR": 3, "NOR": 3, "IMPLIES": 2, "IFF": 1}

ALIASES = {
    "AND": "AND", "E": "AND", "OR": "OR", "OU": "OR", "XOR": "XOR",
    "NAND": "NAND", "NOR": "NOR", "XNOR": "XNOR", "NOT": "NOT", "NAO": "NOT",
    "IMPLIES": "IMPLIES", "IMPLICA": "IMPLIES", "IFF": "IFF", "EQUIVALE": "IFF",
    "TRUE": "TRUE", "VERDADEIRO": "TRUE", "FALSE": "FALSE", "FALSO": "FALSE"
}

SYMBOL_ALIASES = {
    "∧": "AND", "∨": "OR", "⊕": "XOR", "¬": "NOT", "!": "NOT", "~": "NOT",
    "↑": "NAND", "↓": "NOR", "⊙": "XNOR", "→": "IMPLIES", "⇒": "IMPLIES",
    "↔": "IFF", "⇔": "IFF", "&&": "AND", "||": "OR", "^": "XOR",
    "==": "IFF", "=": "IFF", "!=": "XOR"
}

# ============================================================
# 2. ERROS E LEXER LÓGICO
# ============================================================

class LogicError(Exception): pass
class LexerError(LogicError): pass
class ParserError(LogicError): pass

@dataclass
class Token:
    type: str
    value: str
    position: int

TOKEN_PATTERN = re.compile(
    r"(?P<SPACE>\s+)|(?P<OP>&&|\|\||==|!=|[∧∨⊕¬↑↓⊙→⇒↔⇔!~^=])|"
    r"(?P<LPAREN>\()|(?P<RPAREN>\))|(?P<NUMBER>\b[01]\b)|(?P<IDENT>[^\W\d]\w*)",
    re.UNICODE
)

def normalize_identifier(value):
    return value.upper()

def tokenize(expression):
    tokens = []
    position = 0
    while position < len(expression):
        match = TOKEN_PATTERN.match(expression, position)
        if not match:
            raise LexerError(f"Caractere inválido '{expression[position]}' na posição {position + 1}.")
        kind = match.lastgroup
        value = match.group()
        if kind != "SPACE":
            if kind == "OP":
                token_type = SYMBOL_ALIASES.get(value)
                if token_type is None:
                    raise LexerError(f"Operador não reconhecido: {value}")
                tokens.append(Token(token_type, value, position))
            elif kind in ("LPAREN", "RPAREN"):
                tokens.append(Token(kind, value, position))
            elif kind == "NUMBER":
                tokens.append(Token("TRUE" if value == "1" else "FALSE", value, position))
            elif kind == "IDENT":
                normalized = normalize_identifier(value)
                if normalized in ALIASES:
                    tokens.append(Token(ALIASES[normalized], value, position))
                else:
                    tokens.append(Token("VARIABLE", value, position))
        position = match.end()
    tokens.append(Token("EOF", "", len(expression)))
    return tokens

# ============================================================
# 3. AST E PARSER LÓGICO
# ============================================================

@dataclass
class Node:
    kind: str
    value: str = None
    left: object = None
    right: object = None

def make_variable(name): return Node("VARIABLE", value=name)
def make_constant(value): return Node("CONSTANT", value=value)
def make_unary(operator, operand): return Node("UNARY", value=operator, left=operand)
def make_binary(operator, left, right): return Node("BINARY", value=operator, left=left, right=right)

class LogicParser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.index = 0

    @property
    def current(self): return self.tokens[self.index]

    def advance(self):
        token = self.current
        self.index += 1
        return token

    def expect(self, token_type):
        if self.current.type != token_type:
            raise ParserError(f"Esperado '{token_type}' na posição {self.current.position + 1}.")
        return self.advance()

    def parse(self):
        if self.current.type == "EOF": raise ParserError("Expressão vazia.")
        result = self.parse_expression()
        if self.current.type != "EOF":
            raise ParserError(f"Token inesperado '{self.current.value}' na posição {self.current.position + 1}.")
        return result

    def parse_expression(self, min_precedence=0):
        left = self.parse_prefix()
        while self.current.type in OPERATORS:
            operator = self.current.type
            precedence = OPERATORS[operator]
            if precedence < min_precedence: break
            self.advance()
            next_precedence = precedence if operator == "IMPLIES" else precedence + 1
            right = self.parse_expression(next_precedence)
            left = make_binary(operator, left, right)
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
        raise ParserError(f"Expressão inesperada '{token.value}' na posição {token.position + 1}.")

# ============================================================
# 4. GERADOR DE CÓDIGO LÓGICO E MOTOR
# ============================================================

def render_operator(operator, universe):
    operators = {
        "AND": {"Matemática Discreta": "∧", "Portas Lógicas": "AND", "Python": "and", "C/C++": "&&"},
        "OR": {"Matemática Discreta": "∨", "Portas Lógicas": "OR", "Python": "or", "C/C++": "||"},
        "XOR": {"Matemática Discreta": "⊕", "Portas Lógicas": "XOR", "Python": "^", "C/C++": "^"},
        "NAND": {"Matemática Discreta": "↑", "Portas Lógicas": "NAND", "Python": None, "C/C++": None},
        "NOR": {"Matemática Discreta": "↓", "Portas Lógicas": "NOR", "Python": None, "C/C++": None},
        "XNOR": {"Matemática Discreta": "⊙", "Portas Lógicas": "XNOR", "Python": None, "C/C++": None},
        "IMPLIES": {"Matemática Discreta": "→", "Portas Lógicas": "IMPLIES", "Python": None, "C/C++": None},
        "IFF": {"Matemática Discreta": "↔", "Portas Lógicas": "XNOR", "Python": "==", "C/C++": "=="}
    }
    return operators[operator][universe]

def render_expression(node, universe):
    if node.kind == "VARIABLE": return node.value
    if node.kind == "CONSTANT":
        values = {
            "Matemática Discreta": {True: "T", False: "F"}, "Portas Lógicas": {True: "1", False: "0"},
            "Python": {True: "True", False: "False"}, "C/C++": {True: "true", False: "false"}
        }
        return values[universe][node.value]
    if node.kind == "UNARY":
        operand = render_expression(node.left, universe)
        symbols = {"Matemática Discreta": "¬", "Portas Lógicas": "NOT", "Python": "not", "C/C++": "!"}
        sym = symbols[universe]
        if universe == "Python": return f"not ({operand})"
        if universe == "C/C++": return f"!({operand})"
        return f"{sym}({operand})"
    if node.kind == "BINARY":
        op, left, right = node.value, render_expression(node.left, universe), render_expression(node.right, universe)
        if op == "NAND": return f"(not ({left} and {right}))" if universe == "Python" else f"(!({left} && {right}))" if universe == "C/C++" else f"({left} ↑ {right})"
        if op == "NOR": return f"(not ({left} or {right}))" if universe == "Python" else f"(!({left} || {right}))" if universe == "C/C++" else f"({left} ↓ {right})"
        if op == "XNOR": return f"({left} == {right})" if universe in ("Python", "C/C++") else f"({left} ⊙ {right})"
        if op == "IMPLIES": return f"((not ({left})) or ({right}))" if universe == "Python" else f"((!({left})) || ({right}))" if universe == "C/C++" else f"({left} → {right})"
        return f"({left} {render_operator(op, universe)} {right})"
    raise LogicError("Tipo de nó desconhecido.")

class LogicEngine:
    @staticmethod
    def translate(expression, source, target):
        if not expression.strip(): return ""
        ast = LogicParser(tokenize(expression)).parse()
        return render_expression(ast, target)

    @staticmethod
    def process_text(content, source, target):
        results, errors = [], []
        for i, line in enumerate(content.splitlines(), 1):
            if not line.strip():
                results.append("")
                continue
            try:
                results.append(LogicEngine.translate(line, source, target))
            except LogicError as e:
                results.append(f"[ERRO NA LINHA {i}: {e}]")
                errors.append(f"Linha {i}: {e}")
        return "\n".join(results), errors

# ============================================================
# 5. MOTOR DE TRADUÇÃO DE SCRIPTS (IA PREPARADA)
# ============================================================

class ScriptEngine:
    @staticmethod
    def translate_script(code, source_lang, target_lang):
        """
        Para funcionar de verdade, você precisará instalar uma biblioteca como 'openai' ou 'google-generativeai'
        e inserir sua chave de API aqui. Sem isso, linguagens complexas não podem ser traduzidas.
        """
        # Exemplo de onde a chamada de API entraria:
        # import google.generativeai as genai
        # genai.configure(api_key="SUA_CHAVE_AQUI")
        # model = genai.GenerativeModel('gemini-pro')
        # response = model.generate_content(f"Translate this {source_lang} code to {target_lang}:\n\n{code}")
        # return response.text
        
        mensagem_stub = (
            f"// --- AVISO DO SISTEMA ---\n"
            f"// Para traduzir scripts reais de {source_lang} para {target_lang},\n"
            f"// é necessário conectar uma API de IA (ex: OpenAI, Gemini, Claude).\n"
            f"// \n"
            f"// A lógica discreta funciona offline via matemática (Aba 1),\n"
            f"// mas a tradução de código (Aba 2) exige redes neurais para\n"
            f"// entender o contexto, bibliotecas e a estrutura do código.\n\n"
            f"// Vá até a Seção 5 do arquivo logic_dic.py para configurar a sua API."
        )
        return mensagem_stub

# ============================================================
# 6. INTERFACE GRÁFICA COM ABAS
# ============================================================

class LogicTranslator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Omni Translator | Logic & Scripts")
        self.resize(1150, 720)
        self.setMinimumSize(850, 550)

        self.setup_ui()
        self.apply_theme()
        self.setup_shortcuts()
        self.update_logic_placeholders()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(22, 20, 22, 14)
        main_layout.setSpacing(14)

        # Cabeçalho
        header = QHBoxLayout()
        title_layout = QVBoxLayout()
        title = QLabel("OMNI TRANSLATOR")
        title.setObjectName("mainTitle")
        subtitle = QLabel("Logic Engine & Code Transpiler")
        subtitle.setObjectName("subtitle")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header.addLayout(title_layout)
        header.addStretch()

        self.btn_import = QPushButton("Importar (Ctrl+O)")
        self.btn_import.clicked.connect(self.import_file)
        self.btn_export = QPushButton("Exportar (Ctrl+S)")
        self.btn_export.clicked.connect(self.export_file)
        header.addWidget(self.btn_import)
        header.addWidget(self.btn_export)
        main_layout.addLayout(header)

        # Abas
        self.tabs = QTabWidget()
        self.tab_logic = QWidget()
        self.tab_scripts = QWidget()
        self.tabs.addTab(self.tab_logic, "1. Lógica Computacional")
        self.tabs.addTab(self.tab_scripts, "2. Tradutor de Scripts (Requer IA)")
        main_layout.addWidget(self.tabs, 1)

        self.setup_logic_tab()
        self.setup_script_tab()

        # Rodapé
        footer = QHBoxLayout()
        self.status_label = QLabel("Pronto para processar.")
        self.status_label.setObjectName("statusLabel")
        self.btn_copy = QPushButton("Copiar resultado")
        self.btn_copy.clicked.connect(self.copy_result)
        footer.addWidget(self.status_label)
        footer.addStretch()
        footer.addWidget(self.btn_copy)
        main_layout.addLayout(footer)

        self.setStatusBar(QStatusBar())

    def setup_logic_tab(self):
        layout = QVBoxLayout(self.tab_logic)
        panels = QSplitter(Qt.Orientation.Horizontal)
        panels.setChildrenCollapsible(False)

        # Origem
        source_widget = QWidget()
        source_layout = QVBoxLayout(source_widget)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_label = QLabel("UNIVERSO DE ORIGEM")
        source_label.setObjectName("sectionLabel")
        self.combo_source = QComboBox()
        self.combo_source.addItems(UNIVERSES)
        self.combo_source.currentIndexChanged.connect(self.update_logic_placeholders)
        
        self.combo_common = QComboBox()
        self.combo_common.addItem("-- Inserir fórmula rápida --", "")
        self.combo_common.addItem("Lei de De Morgan (AND)", "NOT (A AND B) IFF (NOT A OR NOT B)")
        self.combo_common.addItem("Modus Ponens", "(P AND (P IMPLIES Q)) IMPLIES Q")
        self.combo_common.activated.connect(self.insert_common_logic)
        
        self.text_source = QTextEdit()
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.combo_source)
        source_layout.addWidget(self.combo_common)
        source_layout.addWidget(self.text_source)

        # Centro
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(8, 0, 8, 0)
        center_layout.addStretch()
        self.btn_translate = QPushButton("TRADUZIR  →")
        self.btn_translate.setObjectName("translateButton")
        self.btn_translate.clicked.connect(self.translate_action)
        self.btn_swap = QPushButton("⇄  Inverter")
        self.btn_swap.clicked.connect(self.swap_universes)
        self.btn_clear = QPushButton("Limpar")
        self.btn_clear.clicked.connect(self.clear_fields)
        center_layout.addWidget(self.btn_translate)
        center_layout.addWidget(self.btn_swap)
        center_layout.addWidget(self.btn_clear)
        center_layout.addStretch()

        # Destino
        target_widget = QWidget()
        target_layout = QVBoxLayout(target_widget)
        target_layout.setContentsMargins(0, 0, 0, 0)
        target_label = QLabel("UNIVERSO DE DESTINO")
        target_label.setObjectName("sectionLabel")
        self.combo_target = QComboBox()
        self.combo_target.addItems(UNIVERSES)
        self.combo_target.setCurrentIndex(2)
        self.text_target = QTextEdit()
        self.text_target.setReadOnly(True)
        target_layout.addWidget(target_label)
        target_layout.addWidget(self.combo_target)
        target_layout.addWidget(self.text_target)

        panels.addWidget(source_widget)
        panels.addWidget(center_widget)
        panels.addWidget(target_widget)
        panels.setSizes([450, 150, 450])
        layout.addWidget(panels)

    def setup_script_tab(self):
        layout = QVBoxLayout(self.tab_scripts)
        panels = QSplitter(Qt.Orientation.Horizontal)
        panels.setChildrenCollapsible(False)
        langs = ["Python", "C/C++", "JavaScript", "Java", "C#", "Rust"]

        # Origem Scripts
        src_widget = QWidget()
        src_layout = QVBoxLayout(src_widget)
        src_layout.setContentsMargins(0, 0, 0, 0)
        src_label = QLabel("LINGUAGEM DE ORIGEM")
        src_label.setObjectName("sectionLabel")
        self.combo_script_src = QComboBox()
        self.combo_script_src.addItems(langs)
        self.text_script_src = QTextEdit()
        self.text_script_src.setPlaceholderText("Cole o seu script inteiro aqui (ex: import sys...)")
        src_layout.addWidget(src_label)
        src_layout.addWidget(self.combo_script_src)
        src_layout.addWidget(self.text_script_src)

        # Centro Scripts
        ctr_widget = QWidget()
        ctr_layout = QVBoxLayout(ctr_widget)
        ctr_layout.setContentsMargins(8, 0, 8, 0)
        ctr_layout.addStretch()
        self.btn_trans_script = QPushButton("TRADUZIR CÓDIGO →")
        self.btn_trans_script.setObjectName("translateButton")
        self.btn_trans_script.clicked.connect(self.translate_action)
        ctr_layout.addWidget(self.btn_trans_script)
        ctr_layout.addStretch()

        # Destino Scripts
        tgt_widget = QWidget()
        tgt_layout = QVBoxLayout(tgt_widget)
        tgt_layout.setContentsMargins(0, 0, 0, 0)
        tgt_label = QLabel("LINGUAGEM DE DESTINO")
        tgt_label.setObjectName("sectionLabel")
        self.combo_script_tgt = QComboBox()
        self.combo_script_tgt.addItems(langs)
        self.combo_script_tgt.setCurrentIndex(1)
        self.text_script_tgt = QTextEdit()
        self.text_script_tgt.setReadOnly(True)
        tgt_layout.addWidget(tgt_label)
        tgt_layout.addWidget(self.combo_script_tgt)
        tgt_layout.addWidget(self.text_script_tgt)

        panels.addWidget(src_widget)
        panels.addWidget(ctr_widget)
        panels.addWidget(tgt_widget)
        panels.setSizes([450, 150, 450])
        layout.addWidget(panels)

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Return"), self, self.translate_action)
        QShortcut(QKeySequence("Ctrl+O"), self, self.import_file)
        QShortcut(QKeySequence("Ctrl+S"), self, self.export_file)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, self.copy_result)

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #11151d; color: #e5eaf2; font-family: 'Segoe UI'; font-size: 12px; }
            QLabel#mainTitle { color: #ffffff; font-size: 23px; font-weight: 800; letter-spacing: 2px; }
            QLabel#subtitle { color: #8290a5; font-size: 11px; }
            QLabel#sectionLabel { color: #7fa9e8; font-size: 10px; font-weight: bold; letter-spacing: 1.5px; }
            QTabWidget::pane { border: 1px solid #303c4e; border-radius: 4px; top: -1px; background-color: #11151d;}
            QTabBar::tab { background-color: #1b2330; border: 1px solid #303c4e; padding: 8px 16px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background-color: #2864b5; color: white; font-weight: bold; border-color: #2864b5; }
            QComboBox { background-color: #1b2330; border: 1px solid #303c4e; border-radius: 6px; padding: 9px; min-height: 22px; }
            QTextEdit { background-color: #171e29; border: 1px solid #303c4e; border-radius: 8px; padding: 12px; font-family: 'Consolas', monospace; font-size: 14px; }
            QPushButton { background-color: #252f3e; border: 1px solid #354358; border-radius: 6px; padding: 9px 13px; font-weight: 600; }
            QPushButton:hover { background-color: #34445b; }
            QPushButton#translateButton { background-color: #2864b5; border: none; font-weight: bold; padding: 13px 12px; }
            QPushButton#translateButton:hover { background-color: #367bd5; }
        """)

    def update_logic_placeholders(self):
        ex = {"Matemática Discreta": "¬A ∧ B", "Portas Lógicas": "NOT A AND B", "Python": "not A and B", "C/C++": "!A && B"}.get(self.combo_source.currentText(), "A AND B")
        self.text_source.setPlaceholderText(f"Digite uma expressão lógica...\n\nExemplo:\n{ex}")

    def insert_common_logic(self, index):
        if index > 0:
            logic_str = self.combo_common.itemData(index)
            curr = self.text_source.toPlainText()
            self.text_source.setPlainText(curr + "\n" + logic_str if curr.strip() else logic_str)
            self.combo_common.setCurrentIndex(0)

    def translate_action(self):
        """Identifica qual aba está aberta para executar o motor correto."""
        if self.tabs.currentIndex() == 0:
            self.translate_logic()
        else:
            self.translate_script()

    def translate_logic(self):
        content = self.text_source.toPlainText()
        if not content.strip(): return
        res, errs = LogicEngine.process_text(content, self.combo_source.currentText(), self.combo_target.currentText())
        if errs:
            html = res.replace("[ERRO", "<span style='color: #ff6b6b;'>[ERRO").replace("]", "]</span>").replace("\n", "<br>")
            self.text_target.setHtml(f"<div>{html}</div>")
            self.status_label.setText(f"{len(errs)} erro(s) lógico(s).")
        else:
            self.text_target.setPlainText(res)
            self.status_label.setText("Tradução lógica concluída.")

    def translate_script(self):
        content = self.text_script_src.toPlainText()
        if not content.strip(): return
        self.text_script_tgt.setPlainText("Processando script com IA...")
        
        res = ScriptEngine.translate_script(
            content, 
            self.combo_script_src.currentText(), 
            self.combo_script_tgt.currentText()
        )
        self.text_script_tgt.setPlainText(res)
        self.status_label.setText("Tradução de script finalizada.")

    def swap_universes(self):
        if self.tabs.currentIndex() == 0:
            s_idx, t_idx = self.combo_source.currentIndex(), self.combo_target.currentIndex()
            limpo = "\n".join([ln for ln in self.text_target.toPlainText().splitlines() if not ln.startswith("[ERRO")])
            self.combo_source.setCurrentIndex(t_idx)
            self.combo_target.setCurrentIndex(s_idx)
            self.text_source.setPlainText(limpo)
            self.text_target.clear()

    def clear_fields(self):
        if self.tabs.currentIndex() == 0:
            self.text_source.clear(); self.text_target.clear()
        else:
            self.text_script_src.clear(); self.text_script_tgt.clear()

    def copy_result(self):
        txt = self.text_target.toPlainText() if self.tabs.currentIndex() == 0 else self.text_script_tgt.toPlainText()
        if txt.strip(): QApplication.clipboard().setText(txt)

    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar", "", "Texto (*.txt);;CSV (*.csv);;Todos (*)")
        if path:
            with open(path, "r", encoding="utf-8-sig") as f:
                content = "\n".join(row[0] for row in csv.reader(f) if row) if path.endswith(".csv") else f.read()
            (self.text_source if self.tabs.currentIndex() == 0 else self.text_script_src).setPlainText(content)

    def export_file(self):
        txt = self.text_target.toPlainText() if self.tabs.currentIndex() == 0 else self.text_script_tgt.toPlainText()
        if not txt.strip(): return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar", "export.txt", "Texto (*.txt);;CSV (*.csv)")
        if path:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(txt)

# ============================================================
# 7. EXECUÇÃO
# ============================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    LogicTranslator().show()
    sys.exit(app.exec())
