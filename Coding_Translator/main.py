
import sys
import re
import csv
from pathlib import Path
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QComboBox, QTextEdit, QPushButton,
    QLabel, QFileDialog, QMessageBox, QSplitter,
    QFrame, QStatusBar
)
from PySide6.QtCore import Qt


# ============================================================
# 1. CONFIGURAÇÕES E UNIVERSOS LÓGICOS
# ============================================================

UNIVERSES = [
    "Matemática Discreta",
    "Portas Lógicas",
    "Python",
    "C/C++"
]

# Operadores internos independentes da linguagem.
OPERATORS = {
    "AND": 5,
    "NAND": 5,
    "XOR": 4,
    "XNOR": 4,
    "OR": 3,
    "NOR": 3,
    "IMPLIES": 2,
    "IFF": 1
}

ALIASES = {
    "AND": "AND",
    "E": "AND",
    "OR": "OR",
    "OU": "OR",
    "XOR": "XOR",
    "NAND": "NAND",
    "NOR": "NOR",
    "XNOR": "XNOR",
    "NOT": "NOT",
    "NAO": "NOT",
    "IMPLIES": "IMPLIES",
    "IMPLICA": "IMPLIES",
    "IFF": "IFF",
    "EQUIVALE": "IFF",
    "TRUE": "TRUE",
    "VERDADEIRO": "TRUE",
    "FALSE": "FALSE",
    "FALSO": "FALSE"
}

SYMBOL_ALIASES = {
    "∧": "AND",
    "∨": "OR",
    "⊕": "XOR",
    "¬": "NOT",
    "!": "NOT",
    "~": "NOT",
    "↑": "NAND",
    "↓": "NOR",
    "⊙": "XNOR",
    "→": "IMPLIES",
    "⇒": "IMPLIES",
    "↔": "IFF",
    "⇔": "IFF",
    "&&": "AND",
    "||": "OR",
    "^": "XOR",
    "==": "IFF",
    "=": "IFF",
    "!=": "XOR"
}


# ============================================================
# 2. ERROS CONTROLADOS
# ============================================================

class LogicError(Exception):
    """Erro de processamento lógico."""
    pass


class LexerError(LogicError):
    pass


class ParserError(LogicError):
    pass


# ============================================================
# 3. TOKENIZAÇÃO — LEXER
# ============================================================

@dataclass
class Token:
    type: str
    value: str
    position: int


TOKEN_PATTERN = re.compile(
    r"(?P<SPACE>\s+)"
    r"|(?P<OP>&&|\|\||==|!=|[∧∨⊕¬↑↓⊙→⇒↔⇔!~^=])"
    r"|(?P<LPAREN>\()"
    r"|(?P<RPAREN>\))"
    r"|(?P<NUMBER>\b[01]\b)"
    r"|(?P<IDENT>[^\W\d]\w*)",
    re.UNICODE
)


def normalize_identifier(value):
    """
    Normaliza palavras reservadas sem alterar
    o nome das variáveis na saída.
    """
    return value.upper()


def tokenize(expression):
    tokens = []
    position = 0

    while position < len(expression):

        match = TOKEN_PATTERN.match(expression, position)

        if not match:
            raise LexerError(
                f"Caractere inválido '{expression[position]}' "
                f"na posição {position + 1}."
            )

        kind = match.lastgroup
        value = match.group()

        if kind != "SPACE":

            if kind == "OP":
                token_type = SYMBOL_ALIASES.get(value)

                if token_type is None:
                    raise LexerError(
                        f"Operador não reconhecido: {value}"
                    )

                tokens.append(
                    Token(token_type, value, position)
                )

            elif kind == "LPAREN":
                tokens.append(
                    Token("LPAREN", value, position)
                )

            elif kind == "RPAREN":
                tokens.append(
                    Token("RPAREN", value, position)
                )

            elif kind == "NUMBER":
                token_type = "TRUE" if value == "1" else "FALSE"

                tokens.append(
                    Token(token_type, value, position)
                )

            elif kind == "IDENT":

                normalized = normalize_identifier(value)

                if normalized in ALIASES:
                    token_type = ALIASES[normalized]

                    tokens.append(
                        Token(token_type, value, position)
                    )

                else:
                    tokens.append(
                        Token("VARIABLE", value, position)
                    )

        position = match.end()

    tokens.append(
        Token("EOF", "", len(expression))
    )

    return tokens


# ============================================================
# 4. ÁRVORE SINTÁTICA — AST
# ============================================================

@dataclass
class Node:
    kind: str
    value: str = None
    left: object = None
    right: object = None


def make_variable(name):
    return Node("VARIABLE", value=name)


def make_constant(value):
    return Node("CONSTANT", value=value)


def make_unary(operator, operand):
    return Node(
        "UNARY",
        value=operator,
        left=operand
    )


def make_binary(operator, left, right):
    return Node(
        "BINARY",
        value=operator,
        left=left,
        right=right
    )


# ============================================================
# 5. PARSER — PRECEDÊNCIA E ASSOCIATIVIDADE
# ============================================================

class LogicParser:

    def __init__(self, tokens):
        self.tokens = tokens
        self.index = 0

    @property
    def current(self):
        return self.tokens[self.index]

    def advance(self):
        token = self.current
        self.index += 1
        return token

    def expect(self, token_type):

        if self.current.type != token_type:
            raise ParserError(
                f"Esperado '{token_type}', encontrado "
                f"'{self.current.value or 'fim da expressão'}' "
                f"na posição {self.current.position + 1}."
            )

        return self.advance()

    def parse(self):
        if self.current.type == "EOF":
            raise ParserError("Expressão vazia.")

        result = self.parse_expression()

        if self.current.type != "EOF":
            raise ParserError(
                f"Token inesperado '{self.current.value}' "
                f"na posição {self.current.position + 1}."
            )

        return result

    def parse_expression(self, min_precedence=0):

        left = self.parse_prefix()

        while self.current.type in OPERATORS:

            operator = self.current.type
            precedence = OPERATORS[operator]

            if precedence < min_precedence:
                break

            self.advance()

            # Implicação é associativa à direita.
            if operator == "IMPLIES":
                next_precedence = precedence
            else:
                next_precedence = precedence + 1

            right = self.parse_expression(next_precedence)

            left = make_binary(operator, left, right)

        return left

    def parse_prefix(self):

        token = self.current

        if token.type == "NOT":
            self.advance()
            operand = self.parse_prefix()
            return make_unary("NOT", operand)

        if token.type == "LPAREN":
            self.advance()

            expression = self.parse_expression()

            self.expect("RPAREN")

            return expression

        if token.type == "VARIABLE":
            self.advance()
            return make_variable(token.value)

        if token.type == "TRUE":
            self.advance()
            return make_constant(True)

        if token.type == "FALSE":
            self.advance()
            return make_constant(False)

        raise ParserError(
            f"Expressão inesperada '{token.value or 'fim da expressão'}' "
            f"na posição {token.position + 1}."
        )


# ============================================================
# 6. GERADOR DE EXPRESSÕES — CODE GENERATOR
# ============================================================

def render_operator(operator, universe):

    # Operadores binários convencionais.

    operators = {
        "AND": {
            "Matemática Discreta": "∧",
            "Portas Lógicas": "AND",
            "Python": "and",
            "C/C++": "&&"
        },

        "OR": {
            "Matemática Discreta": "∨",
            "Portas Lógicas": "OR",
            "Python": "or",
            "C/C++": "||"
        },

        "XOR": {
            "Matemática Discreta": "⊕",
            "Portas Lógicas": "XOR",
            "Python": "^",
            "C/C++": "^"
        },

        "NAND": {
            "Matemática Discreta": "↑",
            "Portas Lógicas": "NAND",
            "Python": None,
            "C/C++": None
        },

        "NOR": {
            "Matemática Discreta": "↓",
            "Portas Lógicas": "NOR",
            "Python": None,
            "C/C++": None
        },

        "XNOR": {
            "Matemática Discreta": "⊙",
            "Portas Lógicas": "XNOR",
            "Python": None,
            "C/C++": None
        },

        "IMPLIES": {
            "Matemática Discreta": "→",
            "Portas Lógicas": "IMPLIES",
            "Python": None,
            "C/C++": None
        },

        "IFF": {
            "Matemática Discreta": "↔",
            "Portas Lógicas": "XNOR",
            "Python": "==",
            "C/C++": "=="
        }
    }

    return operators[operator][universe]


def render_expression(node, universe):

    if node.kind == "VARIABLE":
        return node.value

    if node.kind == "CONSTANT":

        values = {
            "Matemática Discreta": {
                True: "T",
                False: "F"
            },

            "Portas Lógicas": {
                True: "1",
                False: "0"
            },

            "Python": {
                True: "True",
                False: "False"
            },

            "C/C++": {
                True: "true",
                False: "false"
            }
        }

        return values[universe][node.value]

    if node.kind == "UNARY":

        operand = render_expression(node.left, universe)

        symbols = {
            "Matemática Discreta": "¬",
            "Portas Lógicas": "NOT",
            "Python": "not",
            "C/C++": "!"
        }

        symbol = symbols[universe]

        if universe == "Python":
            return f"not ({operand})"

        if universe == "C/C++":
            return f"!({operand})"

        return f"{symbol}({operand})"

    if node.kind == "BINARY":

        operator = node.value

        left = render_expression(node.left, universe)
        right = render_expression(node.right, universe)

        # Expansões semânticas para operadores compostos.

        if operator == "NAND":

            if universe == "Python":
                return f"(not ({left} and {right}))"

            if universe == "C/C++":
                return f"(!({left} && {right}))"

        if operator == "NOR":

            if universe == "Python":
                return f"(not ({left} or {right}))"

            if universe == "C/C++":
                return f"(!({left} || {right}))"

        if operator == "XNOR":

            if universe == "Python":
                return f"({left} == {right})"

            if universe == "C/C++":
                return f"({left} == {right})"

        if operator == "IMPLIES":

            if universe == "Python":
                return f"((not ({left})) or ({right}))"

            if universe == "C/C++":
                return f"((!({left})) || ({right}))"

        symbol = render_operator(operator, universe)

        return f"({left} {symbol} {right})"

    raise LogicError("Tipo de nó desconhecido.")


# ============================================================
# 7. MOTOR DE TRADUÇÃO
# ============================================================

class LogicEngine:

    @staticmethod
    def translate(expression, source, target):

        if source not in UNIVERSES:
            raise LogicError("Universo de origem inválido.")

        if target not in UNIVERSES:
            raise LogicError("Universo de destino inválido.")

        if not expression.strip():
            return ""

        tokens = tokenize(expression)

        parser = LogicParser(tokens)

        ast = parser.parse()

        return render_expression(ast, target)

    @staticmethod
    def process_text(content, source, target):

        results = []
        errors = []

        lines = content.splitlines()

        for line_number, line in enumerate(lines, start=1):

            if not line.strip():
                results.append("")
                continue

            try:
                translated = LogicEngine.translate(
                    line,
                    source,
                    target
                )

                results.append(translated)

            except LogicError as error:

                results.append(
                    f"[ERRO NA LINHA {line_number}: {error}]"
                )

                errors.append(
                    f"Linha {line_number}: {error}"
                )

        return "\n".join(results), errors


# ============================================================
# 8. INTERFACE GRÁFICA
# ============================================================

class LogicTranslator(QMainWindow):

    def __init__(self):
        super().__init__()

        self.engine = LogicEngine()

        self.setWindowTitle(
            "Logic Translator | Computational Logic"
        )

        self.resize(1150, 720)
        self.setMinimumSize(850, 550)

        self.setup_ui()
        self.apply_theme()

    # --------------------------------------------------------
    # INTERFACE
    # --------------------------------------------------------

    def setup_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(22, 20, 22, 14)
        main_layout.setSpacing(14)

        # Cabeçalho.

        header = QHBoxLayout()

        title_layout = QVBoxLayout()

        title = QLabel("LOGIC TRANSLATOR")
        title.setObjectName("mainTitle")

        subtitle = QLabel(
            "Computational Logic Translation Engine"
        )
        subtitle.setObjectName("subtitle")

        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)

        header.addLayout(title_layout)
        header.addStretch()

        self.btn_import = QPushButton("Importar")
        self.btn_import.clicked.connect(self.import_file)

        self.btn_export = QPushButton("Exportar")
        self.btn_export.clicked.connect(self.export_file)

        header.addWidget(self.btn_import)
        header.addWidget(self.btn_export)

        main_layout.addLayout(header)

        # Linha divisória.

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")

        main_layout.addWidget(separator)

        # Painéis de tradução.

        panels = QSplitter(Qt.Orientation.Horizontal)
        panels.setChildrenCollapsible(False)

        # Origem.

        source_widget = QWidget()
        source_layout = QVBoxLayout(source_widget)
        source_layout.setContentsMargins(0, 0, 0, 0)

        source_label = QLabel("SOURCE LANGUAGE")
        source_label.setObjectName("sectionLabel")

        self.combo_source = QComboBox()
        self.combo_source.addItems(UNIVERSES)

        self.text_source = QTextEdit()
        self.text_source.setPlaceholderText(
            "Digite uma expressão lógica...\n\n"
            "Exemplo:\n"
            "NOT A AND B OR C"
        )

        source_layout.addWidget(source_label)
        source_layout.addWidget(self.combo_source)
        source_layout.addWidget(self.text_source)

        # Centro.

        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)

        center_layout.setContentsMargins(8, 0, 8, 0)

        center_layout.addStretch()

        self.btn_translate = QPushButton("TRADUZIR  →")
        self.btn_translate.setObjectName("translateButton")
        self.btn_translate.clicked.connect(self.translate_logic)

        self.btn_swap = QPushButton("⇄  Inverter")
        self.btn_swap.clicked.connect(self.swap_universes)

        self.btn_clear = QPushButton("Limpar")
        self.btn_clear.clicked.connect(self.clear_fields)

        self.btn_example = QPushButton("Exemplo")
        self.btn_example.clicked.connect(self.load_example)

        center_layout.addWidget(self.btn_translate)
        center_layout.addWidget(self.btn_swap)
        center_layout.addWidget(self.btn_example)
        center_layout.addWidget(self.btn_clear)

        center_layout.addStretch()

        # Destino.

        target_widget = QWidget()
        target_layout = QVBoxLayout(target_widget)

        target_layout.setContentsMargins(0, 0, 0, 0)

        target_label = QLabel("TARGET LANGUAGE")
        target_label.setObjectName("sectionLabel")

        self.combo_target = QComboBox()
        self.combo_target.addItems(UNIVERSES)
        self.combo_target.setCurrentIndex(2)

        self.text_target = QTextEdit()
        self.text_target.setReadOnly(True)
        self.text_target.setPlaceholderText(
            "O resultado da tradução aparecerá aqui..."
        )

        target_layout.addWidget(target_label)
        target_layout.addWidget(self.combo_target)
        target_layout.addWidget(self.text_target)

        # Montagem.

        panels.addWidget(source_widget)
        panels.addWidget(center_widget)
        panels.addWidget(target_widget)

        panels.setSizes([450, 150, 450])

        main_layout.addWidget(panels, 1)

        # Rodapé.

        footer = QHBoxLayout()

        self.status_label = QLabel(
            "Pronto para processar expressões."
        )
        self.status_label.setObjectName("statusLabel")

        self.btn_copy = QPushButton("Copiar resultado")
        self.btn_copy.clicked.connect(self.copy_result)

        footer.addWidget(self.status_label)
        footer.addStretch()
        footer.addWidget(self.btn_copy)

        main_layout.addLayout(footer)

        # Barra de status.

        self.setStatusBar(QStatusBar())

    # --------------------------------------------------------
    # TEMA VISUAL
    # --------------------------------------------------------

    def apply_theme(self):

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #11151d;
                color: #e5eaf2;
                font-family: 'Segoe UI';
                font-size: 12px;
            }

            QLabel#mainTitle {
                color: #ffffff;
                font-size: 23px;
                font-weight: 800;
                letter-spacing: 2px;
            }

            QLabel#subtitle {
                color: #8290a5;
                font-size: 11px;
            }

            QLabel#sectionLabel {
                color: #7fa9e8;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1.5px;
            }

            QLabel#statusLabel {
                color: #92a0b5;
                font-size: 11px;
            }

            QComboBox {
                background-color: #1b2330;
                border: 1px solid #303c4e;
                border-radius: 6px;
                padding: 9px;
                color: #ffffff;
                min-height: 22px;
            }

            QComboBox:hover {
                border-color: #4d82d2;
            }

            QComboBox QAbstractItemView {
                background-color: #1b2330;
                color: white;
                selection-background-color: #315d9b;
            }

            QTextEdit {
                background-color: #171e29;
                border: 1px solid #303c4e;
                border-radius: 8px;
                padding: 12px;
                color: #e7edf6;
                font-family: 'Consolas', monospace;
                font-size: 14px;
                selection-background-color: #315d9b;
            }

            QTextEdit:focus {
                border: 1px solid #477bc2;
            }

            QPushButton {
                background-color: #252f3e;
                border: 1px solid #354358;
                border-radius: 6px;
                padding: 9px 13px;
                color: #e7edf6;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: #34445b;
                border-color: #527db7;
            }

            QPushButton:pressed {
                background-color: #1b2533;
            }

            QPushButton#translateButton {
                background-color: #2864b5;
                border: none;
                color: white;
                font-weight: bold;
                padding: 13px 12px;
            }

            QPushButton#translateButton:hover {
                background-color: #367bd5;
            }

            QFrame#separator {
                color: #303c4e;
            }

            QSplitter::handle {
                background-color: #263243;
                width: 3px;
            }

            QStatusBar {
                background-color: #11151d;
                color: #8290a5;
            }
        """)

    # --------------------------------------------------------
    # TRADUÇÃO
    # --------------------------------------------------------

    def translate_logic(self):

        source = self.combo_source.currentText()
        target = self.combo_target.currentText()

        content = self.text_source.toPlainText()

        if not content.strip():

            self.status_label.setText(
                "Nenhuma expressão informada."
            )

            return

        result, errors = LogicEngine.process_text(
            content,
            source,
            target
        )

        self.text_target.setPlainText(result)

        if errors:

            self.status_label.setText(
                f"Processamento concluído com {len(errors)} erro(s)."
            )

            self.statusBar().showMessage(
                "Existem expressões que precisam de correção.",
                5000
            )

        else:

            self.status_label.setText(
                "Tradução concluída com sucesso."
            )

            self.statusBar().showMessage(
                "Expressões processadas corretamente.",
                5000
            )

    # --------------------------------------------------------
    # INVERSÃO DOS UNIVERSOS
    # --------------------------------------------------------

    def swap_universes(self):

        source_index = self.combo_source.currentIndex()
        target_index = self.combo_target.currentIndex()

        translated_text = self.text_target.toPlainText()

        self.combo_source.setCurrentIndex(target_index)
        self.combo_target.setCurrentIndex(source_index)

        self.text_source.setPlainText(translated_text)
        self.text_target.clear()

        self.status_label.setText(
            "Universos invertidos."
        )

    # --------------------------------------------------------
    # LIMPAR
    # --------------------------------------------------------

    def clear_fields(self):

        self.text_source.clear()
        self.text_target.clear()

        self.status_label.setText(
            "Campos limpos."
        )

    # --------------------------------------------------------
    # EXEMPLO
    # --------------------------------------------------------

    def load_example(self):

        examples = {
            "Matemática Discreta":
                "¬A ∧ B ∨ C",

            "Portas Lógicas":
                "NOT A AND B OR C",

            "Python":
                "not A and B or C",

            "C/C++":
                "!A && B || C"
        }

        source = self.combo_source.currentText()

        self.text_source.setPlainText(
            examples.get(source, "NOT A AND B OR C")
        )

        self.text_target.clear()

        self.status_label.setText(
            "Exemplo carregado."
        )

    # --------------------------------------------------------
    # COPIAR RESULTADO
    # --------------------------------------------------------

    def copy_result(self):

        result = self.text_target.toPlainText()

        if not result.strip():

            self.status_label.setText(
                "Não existe resultado para copiar."
            )

            return

        QApplication.clipboard().setText(result)

        self.status_label.setText(
            "Resultado copiado para a área de transferência."
        )

    # --------------------------------------------------------
    # IMPORTAÇÃO
    # --------------------------------------------------------

    def import_file(self):

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Importar expressões",
            "",
            "Arquivos de texto (*.txt);;"
            "Arquivos CSV (*.csv);;"
            "Todos os arquivos (*)"
        )

        if not file_path:
            return

        try:

            path = Path(file_path)

            with path.open(
                "r",
                encoding="utf-8-sig",
                newline=""
            ) as file:

                if path.suffix.lower() == ".csv":

                    reader = csv.reader(file)

                    content = "\n".join(
                        row[0]
                        for row in reader
                        if row and row[0].strip()
                    )

                else:
                    content = file.read()

            self.text_source.setPlainText(content)

            self.status_label.setText(
                f"Arquivo importado: {path.name}"
            )

        except (OSError, UnicodeError, csv.Error) as error:

            QMessageBox.critical(
                self,
                "Erro de importação",
                f"Não foi possível importar o arquivo:\n{error}"
            )

    # --------------------------------------------------------
    # EXPORTAÇÃO
    # --------------------------------------------------------

    def export_file(self):

        content = self.text_target.toPlainText()

        if not content.strip():

            QMessageBox.warning(
                self,
                "Exportação",
                "Não existe tradução para exportar."
            )

            return

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Exportar tradução",
            "logic_translation.csv",
            "CSV (*.csv);;Texto (*.txt)"
        )

        if not file_path:
            return

        path = Path(file_path)

        if not path.suffix:

            path = path.with_suffix(
                ".csv" if "CSV" in selected_filter else ".txt"
            )

        try:

            with path.open(
                "w",
                encoding="utf-8-sig",
                newline=""
            ) as file:

                if path.suffix.lower() == ".csv":

                    writer = csv.writer(file)

                    writer.writerow([
                        "Origem",
                        "Destino",
                        "Expressão original",
                        "Expressão traduzida"
                    ])

                    source_lines = self.text_source.toPlainText().splitlines()
                    target_lines = content.splitlines()

                    for index, translated in enumerate(target_lines):

                        original = (
                            source_lines[index]
                            if index < len(source_lines)
                            else ""
                        )

                        writer.writerow([
                            self.combo_source.currentText(),
                            self.combo_target.currentText(),
                            original,
                            translated
                        ])

                else:

                    file.write(
                        f"ORIGEM: {self.combo_source.currentText()}\n"
                    )

                    file.write(
                        f"DESTINO: {self.combo_target.currentText()}\n\n"
                    )

                    file.write(content)

            self.status_label.setText(
                f"Arquivo exportado: {path.name}"
            )

            QMessageBox.information(
                self,
                "Exportação concluída",
                "Arquivo exportado com sucesso."
            )

        except (OSError, csv.Error) as error:

            QMessageBox.critical(
                self,
                "Erro de exportação",
                f"Não foi possível salvar o arquivo:\n{error}"
            )


# ============================================================
# 9. EXECUÇÃO
# ============================================================

def main():

    app = QApplication(sys.argv)

    app.setStyle("Fusion")

    window = LogicTranslator()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
