#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regex Translator
================
Tradutor bidirecional entre Linguagem Natural e Expressões Regulares (Regex), 100% offline.
Possui detecção automática, realce de sintaxe e processamento em segundo plano.

Dependência única: pip install PySide6
"""

import sys
import re
import time
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
    QPushButton, QLabel, QSplitter, QPlainTextEdit, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QTimer, QRunnable, QThreadPool, QObject, Signal, QRect
from PySide6.QtGui import (
    QKeySequence, QShortcut, QFont, QColor, QPainter, QTextFormat, 
    QSyntaxHighlighter, QTextCharFormat, QTextCursor
)

# ============================================================
# 1. CONFIGURAÇÕES E CONSTANTES
# ============================================================

APP_NAME = "Regex Translator"
AUTO = "Auto-detectar"
REGEX = "Regex"
NATURAL = "Linguagem Natural"
LANGUAGES = [REGEX, NATURAL]

# Dicionários de mapeamento heurístico
REGEX_TO_NATURAL = {
    r"\^": "Início da linha",
    r"\$": "Fim da linha",
    r"\\d": "um dígito numérico",
    r"\\w": "um caractere alfanumérico",
    r"\\s": "um espaço em branco",
    r"\.\*": "qualquer texto (opcional)",
    r"\.": "qualquer caractere",
    r"\[a-zA-Z\]": "qualquer letra",
    r"\[a-z\]": "uma letra minúscula",
    r"\[A-Z\]": "uma letra maiúscula",
    r"\[0-9\]": "um número de 0 a 9",
    r"\+": "uma ou mais vezes",
    r"\*": "zero ou mais vezes",
    r"\?": "opcionalmente",
}

NATURAL_TO_REGEX = {
    r"\binicio da linha\b|\bcomeca com\b|\bcomeça com\b": "^",
    r"\bfim da linha\b|\btermina com\b": "$",
    r"\bum digito\b|\bum dígito\b|\bnumero\b|\bnúmero\b": r"\d",
    r"\bletra\b": r"[a-zA-Z]",
    r"\balfanumerico\b|\balfanumérico\b": r"\w",
    r"\bespaco\b|\bespaço\b": r"\s",
    r"\bqualquer caractere\b": ".",
    r"\bqualquer coisa\b|\bqualquer texto\b": ".*",
    r"\buma ou mais vezes\b|\bpelo menos um\b": "+",
    r"\bzero ou mais vezes\b": "*",
    r"\bopcional\b|\bopcionalmente\b": "?",
}

# ============================================================
# 2. MOTOR DE TRADUÇÃO
# ============================================================

class TranslationResult:
    def __init__(self, text, detected, elapsed_ms):
        self.text = text
        self.detected = detected
        self.elapsed_ms = elapsed_ms

class RegexEngine:
    @staticmethod
    def detect_language(text):
        """Detecta se o texto de entrada é Regex ou Linguagem Natural."""
        # Se contiver barras invertidas, âncoras ou quantificadores não-literais, assumimos Regex
        if re.search(r'[\^\$\\\{\}\[\]\|\+\*]', text):
            return REGEX
        return NATURAL

    @staticmethod
    def translate_to_natural(regex_text):
        """Converte Regex para uma descrição em português."""
        output = regex_text
        for pattern, replacement in REGEX_TO_NATURAL.items():
            output = re.sub(pattern, f" [{replacement}] ", output)
        
        # Limpeza simples de espaços duplicados
        output = re.sub(r'\s+', ' ', output).strip()
        return output

    @staticmethod
    def translate_to_regex(natural_text):
        """Converte linguagem natural simples para Regex."""
        output = natural_text.lower()
        for pattern, replacement in NATURAL_TO_REGEX.items():
            output = re.sub(pattern, replacement, output)
        
        # Remove conectivos e pontuações comuns de linguagem natural
        output = re.sub(r'\b(um|uma|de|para|que|o|a)\b', '', output)
        output = re.sub(r'\s+', '', output)
        return output

    @staticmethod
    def process(content, source, target):
        t0 = time.perf_counter()
        
        if not content.strip():
            return TranslationResult("", source, 0.0)

        detected = RegexEngine.detect_language(content) if source == AUTO else source
        
        lines = content.splitlines()
        translated_lines = []
        
        for line in lines:
            if not line.strip():
                translated_lines.append("")
                continue
                
            if target == NATURAL:
                # Se for para natural, trata como se a entrada fosse Regex
                translated_lines.append(RegexEngine.translate_to_natural(line))
            else:
                # Se for para Regex, trata como se a entrada fosse Natural
                translated_lines.append(RegexEngine.translate_to_regex(line))

        result_text = "\n".join(translated_lines)
        elapsed = (time.perf_counter() - t0) * 1000
        
        return TranslationResult(result_text, detected, elapsed)


# ============================================================
# 3. COMPONENTES DE INTERFACE (EDITOR E SYNTAX)
# ============================================================

def get_mono_font(size=12):
    font = QFont()
    font.setFamilies(["Fira Code", "JetBrains Mono", "Consolas", "monospace"])
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPointSize(size)
    return font

def format_color(color_hex, bold=False):
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color_hex))
    if bold:
        fmt.setFontWeight(QFont.Weight.Bold)
    return fmt

class RegexSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = [
            (re.compile(r"[\^\$]"), format_color("#ff79c6", bold=True)),        # Âncoras (Rosa)
            (re.compile(r"\\[dwsDWS]"), format_color("#8be9fd")),                # Metacaracteres (Ciano)
            (re.compile(r"\[.*?\]"), format_color("#f1fa8c")),                   # Classes (Amarelo)
            (re.compile(r"[\+\*\?]|\{\d+(,\d+)?\}"), format_color("#50fa7b")),   # Quantificadores (Verde)
            (re.compile(r"\(.*?\)"), format_color("#bd93f9")),                   # Grupos (Roxo)
        ]

    def highlightBlock(self, text):
        for rx, fmt in self.rules:
            for m in rx.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)

class EditorArea(QPlainTextEdit):
    def __init__(self, read_only=False, is_regex=False):
        super().__init__()
        self.setFont(get_mono_font())
        self.setReadOnly(read_only)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        if is_regex:
            self.highlighter = RegexSyntaxHighlighter(self.document())


# ============================================================
# 4. EXECUÇÃO EM BACKGROUND E JANELA PRINCIPAL
# ============================================================

class TaskSignals(QObject):
    done = Signal(object)
    failed = Signal(str)

class TranslationTask(QRunnable):
    def __init__(self, fn, *args):
        super().__init__()
        self.fn = fn
        self.args = args
        self.signals = TaskSignals()

    def run(self):
        try:
            result = self.fn(*self.args)
            self.signals.done.emit(result)
        except Exception as e:
            self.signals.failed.emit(str(e))

class RegexTranslatorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1100, 650)
        self.pool = QThreadPool.globalInstance()
        
        self.timer_translate = QTimer()
        self.timer_translate.setSingleShot(True)
        self.timer_translate.setInterval(400)
        self.timer_translate.timeout.connect(self.run_translation)

        self.setup_ui()
        self.apply_theme()
        self.setup_shortcuts()
        self.update_placeholders()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header
        header = QHBoxLayout()
        title = QLabel("REGEX TRANSLATOR")
        title.setObjectName("mainTitle")
        header.addWidget(title)
        header.addStretch()
        
        self.btn_swap = QPushButton("⇄ Inverter")
        self.btn_swap.clicked.connect(self.swap_languages)
        self.btn_clear = QPushButton("Limpar")
        self.btn_clear.clicked.connect(self.clear_fields)
        header.addWidget(self.btn_swap)
        header.addWidget(self.btn_clear)
        main_layout.addLayout(header)

        # Divisão Principal (Esquerda: Entrada, Direita: Saída)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Painel de Entrada
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.combo_source = QComboBox()
        self.combo_source.addItems([AUTO] + LANGUAGES)
        self.combo_source.currentIndexChanged.connect(self.on_source_changed)
        
        self.lbl_detected = QLabel("")
        self.lbl_detected.setObjectName("hintLabel")
        
        self.text_in = EditorArea(is_regex=True)
        self.text_in.textChanged.connect(self.timer_translate.start)
        
        left_layout.addWidget(QLabel("DE:"))
        left_layout.addWidget(self.combo_source)
        left_layout.addWidget(self.lbl_detected)
        left_layout.addWidget(self.text_in, 1)

        # Painel de Saída
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.combo_target = QComboBox()
        self.combo_target.addItems(LANGUAGES)
        self.combo_target.setCurrentIndex(1) # Default: Natural
        self.combo_target.currentIndexChanged.connect(self.run_translation)
        
        self.text_out = EditorArea(read_only=True, is_regex=True)
        
        right_layout.addWidget(QLabel("PARA:"))
        right_layout.addWidget(self.combo_target)
        right_layout.addWidget(QLabel(" ")) # Espaçador alinhado
        right_layout.addWidget(self.text_out, 1)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([550, 550])
        main_layout.addWidget(splitter, 1)

        # Footer
        self.lbl_status = QLabel("Pronto.")
        self.lbl_status.setObjectName("statusLabel")
        main_layout.addWidget(self.lbl_status)

    def apply_theme(self):
        # Tema moderno "Dracula/Cyberpunk"
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #282a36; color: #f8f8f2; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
            QLabel { background: transparent; font-weight: bold; color: #bd93f9; }
            QLabel#mainTitle { color: #50fa7b; font-size: 24px; font-weight: 900; letter-spacing: 2px; }
            QLabel#hintLabel, QLabel#statusLabel { color: #6272a4; font-weight: normal; font-size: 12px; }
            QComboBox { background-color: #44475a; border: 1px solid #6272a4; border-radius: 5px; padding: 6px 12px; color: #f8f8f2; }
            QComboBox:hover { border-color: #bd93f9; }
            QComboBox::drop-down { border: none; }
            QPlainTextEdit { background-color: #1e1f29; border: 1px solid #44475a; border-radius: 8px; padding: 10px; color: #f8f8f2; }
            QPlainTextEdit:focus { border-color: #bd93f9; }
            QPushButton { background-color: #44475a; border: none; border-radius: 5px; padding: 8px 16px; font-weight: bold; color: #f8f8f2; }
            QPushButton:hover { background-color: #6272a4; }
            QPushButton:pressed { background-color: #bd93f9; color: #282a36; }
            QSplitter::handle { background-color: #282a36; width: 10px; }
        """)

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+L"), self, self.clear_fields)

    def update_placeholders(self):
        if self.combo_source.currentText() == REGEX:
            self.text_in.setPlaceholderText("Digite sua Regex aqui...\nExemplo: ^\\d{3}-\\d{4}$")
        else:
            self.text_in.setPlaceholderText("Descreva o padrão em português...\nExemplo: começa com um dígito")

    def on_source_changed(self):
        self.update_placeholders()
        self.run_translation()

    def swap_languages(self):
        src = self.combo_source.currentText()
        tgt = self.combo_target.currentText()
        
        if src == AUTO:
            src = REGEX if tgt == NATURAL else NATURAL

        self.combo_source.blockSignals(True)
        self.combo_target.blockSignals(True)
        
        self.combo_source.setCurrentText(tgt)
        self.combo_target.setCurrentText(src)
        
        self.combo_source.blockSignals(False)
        self.combo_target.blockSignals(False)
        
        current_out = self.text_out.toPlainText()
        self.text_in.setPlainText(current_out)
        self.update_placeholders()

    def clear_fields(self):
        self.text_in.clear()
        self.text_out.clear()
        self.lbl_detected.clear()
        self.lbl_status.setText("Campos limpos.")

    def run_translation(self):
        content = self.text_in.toPlainText()
        if not content.strip():
            self.text_out.clear()
            self.lbl_detected.clear()
            self.lbl_status.setText("Pronto.")
            return

        self.lbl_status.setText("Processando...")
        task = TranslationTask(
            RegexEngine.process, 
            content, 
            self.combo_source.currentText(), 
            self.combo_target.currentText()
        )
        task.signals.done.connect(self.on_translation_done)
        task.signals.failed.connect(lambda e: self.lbl_status.setText(f"Erro: {e}"))
        self.pool.start(task)

    def on_translation_done(self, result):
        self.text_out.setPlainText(result.text)
        
        if self.combo_source.currentText() == AUTO:
            self.lbl_detected.setText(f"Detectado automaticamente: {result.detected}")
        else:
            self.lbl_detected.clear()
            
        self.lbl_status.setText(f"Traduzido em {result.elapsed_ms:.1f} ms.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RegexTranslatorApp()
    window.show()
    sys.exit(app.exec())
