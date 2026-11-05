#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulador de Xadrez — Análise e Rastros (v3.0)  |  Chess Simulator — Analysis & Traces
================================================
Dependências:  pip install pygame python-chess      (o módulo importado é `chess`)

Uso:
    python Main.py                         # interface gráfica
    python Main.py --batch 200 --white-level 1 --black-level 3 --seed 7
    python Main.py --batch 50 --full       # batch + pasta completa por partida
    python Main.py --report                # estatísticas agregadas de todas as partidas já salvas
    python Main.py --batch 100 --random    # auto-jogo aleatório: partidas NUNCA repetidas (registro persistente)
    python Main.py --lang en               # idioma inicial (alternável na interface ou com a tecla L)

Saídas (pasta ./exports por padrão):
    partidas/<id>_<N>plies/   summary.json, moves.csv, pieces.csv, traces.json,
                              heatmaps.csv, partida.pgn, trace.png, heat_*.png, material.png
    dataset/                  games_log.csv, moves_all.csv, pieces_all.csv  (acumulam partidas FINALIZADAS)
    batches/                  resumo estatístico de cada execução --batch
    DICIONARIO_DE_DADOS.md    descrição de todas as colunas
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import platform
import random
import secrets
import statistics
import sys
import threading
import time
import traceback
import uuid
from collections import Counter
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import chess
import chess.pgn
import pygame

APP_VERSION = "3.0"
SCHEMA_VERSION = 3

# ============================================================
# Configuração
# ============================================================
BOARD_SIZE = 640
MENU_WIDTH = 340
WIDTH = BOARD_SIZE + MENU_WIDTH
HEIGHT = BOARD_SIZE
SQ_SIZE = BOARD_SIZE // 8
FPS = 60
PC_DELAY_S = 0.30            # pausa "humana" antes do PC jogar (não bloqueia a UI)
ENGINE_TIME_LIMIT_S = 2.5    # limite de tempo por lance do PC (GUI)

# ---- Tema neon fantasmagórico (edite aqui para ajustar toda a paleta) ----
COLOR_VOID = (8, 6, 18)
COLOR_LIGHT = (38, 30, 74)          # casas "claras": violeta profundo
COLOR_DARK = (18, 14, 40)           # casas "escuras": quase preto azulado
COLOR_GRID = (62, 42, 130)
COLOR_HIGHLIGHT = (0, 255, 230)     # ciano neon (seleção / destaque)
COLOR_LAST_MOVE = (150, 90, 255)    # violeta neon
COLOR_MENU = (10, 8, 22)
COLOR_PANEL = (18, 14, 38)
COLOR_BTN = (24, 18, 52)
COLOR_BTN_HOVER = (40, 30, 84)
COLOR_BORDER = (120, 70, 230)
COLOR_TEXT = (205, 225, 255)        # branco fantasma
COLOR_MUTED = (130, 125, 190)
COLOR_LEGAL = (0, 255, 230)
COLOR_CHECK = (255, 50, 90)
COLOR_ERROR = (255, 80, 110)
COLOR_MAGENTA = (255, 50, 200)
COLOR_COORD = (110, 95, 210)

MODE_KEYS = ["white", "black", "both", "cpu", "auto"]
N_LEVELS = 4                  # níveis 0..3 (profundidade de busca)
AUTO_NEXT_DELAY_S = 3.0       # pausa entre partidas no auto-jogo
AUTO_MAX_PLIES = 600

FILTER_KEYS = ["brancas", "pretas", "peões", "cavalos", "bispos", "torres", "rainhas", "reis"]
TYPE_FILTER = {
    chess.PAWN: "peões", chess.KNIGHT: "cavalos", chess.BISHOP: "bispos",
    chess.ROOK: "torres", chess.QUEEN: "rainhas", chess.KING: "reis",
}
CHECKBOXES = [{"key": k, "x": BOARD_SIZE + (20 if i % 2 == 0 else 180), "y": 238 + 24 * (i // 2)}
              for i, k in enumerate(FILTER_KEYS)]

_MX = BOARD_SIZE
BUTTONS = {
    "mode": pygame.Rect(_MX + 20, 12, MENU_WIDTH - 40, 32),
    "level": pygame.Rect(_MX + 20, 50, 216, 32),
    "lang": pygame.Rect(_MX + 242, 50, 78, 32),
    "undo": pygame.Rect(_MX + 20, 88, 96, 32),
    "restart": pygame.Rect(_MX + 122, 88, 96, 32),
    "flip": pygame.Rect(_MX + 224, 88, 96, 32),
    "export": pygame.Rect(_MX + 20, 338, MENU_WIDTH - 40, 36),
}
NAME_TO_PT = {chess.piece_name(_pt): _pt for _pt in range(1, 7)}
PIECE_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
FILLED_GLYPH = {chess.KING: "♚", chess.QUEEN: "♛", chess.ROOK: "♜",
                chess.BISHOP: "♝", chess.KNIGHT: "♞", chess.PAWN: "♟"}
FALLBACK_LETTER = {chess.KING: "K", chess.QUEEN: "Q", chess.ROOK: "R",
                   chess.BISHOP: "B", chess.KNIGHT: "N", chess.PAWN: "P"}

# Cores dos rastros: brancas = ciano/verde neon, pretas = magenta/vermelho neon
TRACE_COLORS = {
    (True, chess.PAWN): (120, 255, 200), (True, chess.KNIGHT): (0, 255, 150),
    (True, chess.BISHOP): (0, 225, 255), (True, chess.ROOK): (90, 190, 255),
    (True, chess.QUEEN): (190, 255, 80), (True, chess.KING): (235, 255, 255),
    (False, chess.PAWN): (255, 140, 220), (False, chess.KNIGHT): (255, 40, 160),
    (False, chess.BISHOP): (190, 70, 255), (False, chess.ROOK): (255, 90, 90),
    (False, chess.QUEEN): (255, 50, 230), (False, chess.KING): (255, 20, 60),
}
TRACE_WIDTH = {chess.PAWN: 3, chess.KNIGHT: 4, chess.BISHOP: 4,
               chess.ROOK: 4, chess.QUEEN: 5, chess.KING: 4}



# ============================================================
# Idiomas / Languages (PT <-> EN)
# ============================================================
LANG = "pt"
STR = {
    "pt": {
        "mode_label": "Modo: {}", "level_label": "Nível do PC: {}", "level_shuffled": "Níveis: sorteados por jogo",
        "undo": "Desfazer", "restart": "Reiniciar", "flip": "Girar", "export": "Exportar análise completa",
        "mode_0": "Brancas (vs PC)", "mode_1": "Pretas (vs PC)", "mode_2": "Ambos os lados",
        "mode_3": "PC vs PC", "mode_4": "Auto-jogo aleatório",
        "level_0": "Aleatório", "level_1": "Fácil", "level_2": "Médio", "level_3": "Difícil",
        "turn_white": "Vez: Brancas", "turn_black": "Vez: Pretas", "check": "(XEQUE!)",
        "thinking": "pensando", "paused": "pausado",
        "status_move": "Lance {}   Material: {:+d}", "auto_status": "Auto #{}  únicas: {}  lance {}",
        "cap_w": "Br capturaram: {}", "cap_b": "Pr capturaram: {}",
        "filters": "Filtros de Exportação:", "history": "Histórico:",
        "f_brancas": "Brancas (Ciano)", "f_pretas": "Pretas (Magenta)", "f_peões": "Peões",
        "f_cavalos": "Cavalos", "f_bispos": "Bispos", "f_torres": "Torres", "f_rainhas": "Rainhas", "f_reis": "Reis",
        "win_white": "Brancas vencem", "win_black": "Pretas vencem", "win_draw": "Empate", "win_none": "Fim de jogo",
        "term_checkmate": "Xeque-mate", "term_stalemate": "Afogamento",
        "term_insufficient_material": "Material insuficiente", "term_seventyfive_moves": "Regra dos 75 lances",
        "term_fivefold_repetition": "Repetição (5x)", "term_fifty_moves": "Regra dos 50 lances",
        "term_threefold_repetition": "Repetição (3x)", "term_max_plies": "Limite de lances",
        "saved": "Salvo: {}", "export_err": "Erro ao exportar: {}", "auto_next": "Próxima partida em {}s",
        "caption": "Simulador de Xadrez — U desfazer · R reiniciar · F girar · E exportar · P pausar auto · L idioma · Esc",
        "trace_legend": "Ciano = brancas | Magenta = pretas | circulo = origem | seta = destino | X = captura",
        "heat_title": "Mapa de calor: {}", "heat_max": "máx", "batch_heat": "Batch {} partidas: {}",
        "map_destinations": "destinos", "map_traffic": "tráfego", "map_captures": "capturas",
        "map_control_white": "controle (brancas)", "map_control_black": "controle (pretas)",
        "mat_title1": "Balanço de material (brancas - pretas)",
        "mat_title2": "Lances legais por lance (ramificação)",
        "mat_axis": "Eixo X: lance (ply) 1..{}  |  ciano = brancas, magenta = pretas",
        "no_moves": "Sem lances para exibir",
        "batch_start": "Batch {}: {} partidas | brancas nível {} vs pretas nível {} | seed base {}",
        "batch_random": "Batch {}: {} partidas ALEATÓRIAS ÚNICAS (níveis, semente e ruído sorteados por jogo)",
        "no_games": "Nenhuma partida concluída.", "data_in": "Dados em: {}",
        "stats_title": "=== Estatísticas agregadas ({} partidas) ===",
        "wins_white": "Vitórias brancas", "wins_black": "Vitórias pretas", "draws": "Empates",
        "terminations": "Términos:", "metric": "métrica", "mean": "média", "median": "mediana",
        "stdev": "desvio", "min": "mín", "max": "máx",
        "report_none": "Nada encontrado em {}. Finalize partidas ou use --batch primeiro.",
        "report_head": "{} partidas em {}", "r_white": "Brancas", "r_black": "Pretas", "r_draw": "Empates",
        "unique_known": "Partidas únicas registradas: {}",
        "auto_params": "Br: nível {}  Pr: nível {}  ruído {:.0%}",
    },
    "en": {
        "mode_label": "Mode: {}", "level_label": "PC level: {}", "level_shuffled": "Levels: shuffled per game",
        "undo": "Undo", "restart": "Restart", "flip": "Flip", "export": "Export full analysis",
        "mode_0": "White (vs PC)", "mode_1": "Black (vs PC)", "mode_2": "Both sides",
        "mode_3": "PC vs PC", "mode_4": "Random self-play",
        "level_0": "Random", "level_1": "Easy", "level_2": "Medium", "level_3": "Hard",
        "turn_white": "Turn: White", "turn_black": "Turn: Black", "check": "(CHECK!)",
        "thinking": "thinking", "paused": "paused",
        "status_move": "Move {}   Material: {:+d}", "auto_status": "Auto #{}  unique: {}  move {}",
        "cap_w": "White captured: {}", "cap_b": "Black captured: {}",
        "filters": "Export Filters:", "history": "History:",
        "f_brancas": "White (Cyan)", "f_pretas": "Black (Magenta)", "f_peões": "Pawns",
        "f_cavalos": "Knights", "f_bispos": "Bishops", "f_torres": "Rooks", "f_rainhas": "Queens", "f_reis": "Kings",
        "win_white": "White wins", "win_black": "Black wins", "win_draw": "Draw", "win_none": "Game over",
        "term_checkmate": "Checkmate", "term_stalemate": "Stalemate",
        "term_insufficient_material": "Insufficient material", "term_seventyfive_moves": "75-move rule",
        "term_fivefold_repetition": "Fivefold repetition", "term_fifty_moves": "50-move rule",
        "term_threefold_repetition": "Threefold repetition", "term_max_plies": "Move limit reached",
        "saved": "Saved: {}", "export_err": "Export error: {}", "auto_next": "Next game in {}s",
        "caption": "Chess Simulator — U undo · R restart · F flip · E export · P pause auto · L language · Esc",
        "trace_legend": "Cyan = white | Magenta = black | circle = origin | arrow = destination | X = capture",
        "heat_title": "Heatmap: {}", "heat_max": "max", "batch_heat": "Batch {} games: {}",
        "map_destinations": "destinations", "map_traffic": "traffic", "map_captures": "captures",
        "map_control_white": "control (white)", "map_control_black": "control (black)",
        "mat_title1": "Material balance (white - black)",
        "mat_title2": "Legal moves per move (branching factor)",
        "mat_axis": "X axis: move (ply) 1..{}  |  cyan = white, magenta = black",
        "no_moves": "No moves to display",
        "batch_start": "Batch {}: {} games | white level {} vs black level {} | base seed {}",
        "batch_random": "Batch {}: {} UNIQUE RANDOM games (levels, seed and noise drawn per game)",
        "no_games": "No finished games.", "data_in": "Data in: {}",
        "stats_title": "=== Aggregate statistics ({} games) ===",
        "wins_white": "White wins", "wins_black": "Black wins", "draws": "Draws",
        "terminations": "Terminations:", "metric": "metric", "mean": "mean", "median": "median",
        "stdev": "stdev", "min": "min", "max": "max",
        "report_none": "Nothing found at {}. Finish games or run --batch first.",
        "report_head": "{} games in {}", "r_white": "White", "r_black": "Black", "r_draw": "Draws",
        "unique_known": "Unique games on record: {}",
        "auto_params": "White: lvl {}  Black: lvl {}  noise {:.0%}",
    },
}


def tr(key, *args):
    s = STR.get(LANG, STR["pt"]).get(key) or STR["pt"].get(key, key)
    return s.format(*args) if args else s


def set_lang(lang):
    global LANG
    LANG = lang if lang in STR else "pt"


def load_settings(out_root):
    try:
        return json.loads((Path(out_root) / "settings.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_settings(out_root, data):
    try:
        Path(out_root).mkdir(parents=True, exist_ok=True)
        write_json(Path(out_root) / "settings.json", data)
    except Exception:
        traceback.print_exc()


# ============================================================
# Utilidades de tabuleiro / matemática
# ============================================================
def piece_name_en(pt):
    return chess.piece_name(pt)


def material(board, color):
    return sum(PIECE_VALUES[pt] * len(board.pieces(pt, color)) for pt in PIECE_VALUES)


def nonpawn_material(board):
    return sum(PIECE_VALUES[pt] * (len(board.pieces(pt, chess.WHITE)) + len(board.pieces(pt, chess.BLACK)))
               for pt in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN))


def squares_between(a, b):
    """Casas intermediárias (exclusivas) entre duas casas alinhadas; [] se não alinhadas."""
    fa, ra, fb, rb = chess.square_file(a), chess.square_rank(a), chess.square_file(b), chess.square_rank(b)
    df, dr = fb - fa, rb - ra
    if not (df == 0 or dr == 0 or abs(df) == abs(dr)):
        return []
    sf, sr = (df > 0) - (df < 0), (dr > 0) - (dr < 0)
    n = max(abs(df), abs(dr))
    return [chess.square(fa + sf * k, ra + sr * k) for k in range(1, n)]


def wilson_interval(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    a = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - a) / d, (c + a) / d)


def describe(values):
    vals = [float(v) for v in values if v is not None and v != ""]
    if not vals:
        return {"n": 0}
    out = {"n": len(vals), "mean": statistics.fmean(vals), "median": statistics.median(vals),
           "min": min(vals), "max": max(vals), "stdev": statistics.stdev(vals) if len(vals) > 1 else 0.0}
    if len(vals) >= 4:
        q = statistics.quantiles(vals, n=4)
        out["p25"], out["p75"] = q[0], q[2]
    return out


def mean_or_none(values):
    vals = [v for v in values if v is not None]
    return round(statistics.fmean(vals), 4) if vals else None


def top_squares(values, k=5):
    ranked = sorted(range(64), key=lambda s: values[s], reverse=True)[:k]
    return [{"square": chess.square_name(s), "value": values[s]} for s in ranked if values[s] > 0]


# ============================================================
# Motor do PC (assíncrono, com limite de tempo)
# ============================================================
class _Timeout(Exception):
    pass


class Engine:
    """Negamax alfa-beta com aprofundamento iterativo. nível 0 = aleatório; 1..3 = profundidade.
    `epsilon` = probabilidade de jogar um lance aleatório (ruído) em cada jogada;
    `forbidden` = lances proibidos (usado para nunca repetir uma partida inteira)."""
    MATE = 100000
    CP = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
          chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0}

    def __init__(self, level=1, rng=None, time_limit=ENGINE_TIME_LIMIT_S, epsilon=0.0):
        self.level = max(0, min(3, int(level)))
        self.rng = rng or random.Random()
        self.time_limit = time_limit
        self.epsilon = epsilon
        self.deadline = 0.0
        self._nodes = 0

    def choose(self, board, forbidden=None):
        legal = list(board.legal_moves)
        if not legal:
            return None
        allowed = [m for m in legal if not forbidden or m not in forbidden] or legal
        if self.level == 0 or (self.epsilon and self.rng.random() < self.epsilon):
            return self.rng.choice(allowed)
        allowed_set = set(allowed)
        work = board.copy(stack=False)
        self.deadline = time.monotonic() + self.time_limit
        self._nodes = 0
        best = None
        for depth in range(1, self.level + 1):
            try:
                mv = self._root(work, depth, allowed_set)
            except _Timeout:
                break
            if mv is not None:
                best = mv
        return best if best in allowed_set else self.rng.choice(allowed)

    def _ordered(self, board):
        moves = list(board.legal_moves)
        self.rng.shuffle(moves)

        def key(m):
            s = 0
            if board.is_capture(m):
                victim = board.piece_at(m.to_square)
                s += 10 * (self.CP[victim.piece_type] if victim else 100) - self.CP[board.piece_type_at(m.from_square)]
            if m.promotion:
                s += 800
            return s
        moves.sort(key=key, reverse=True)
        return moves

    def _root(self, board, depth, allowed):
        alpha, beta = -math.inf, math.inf
        best, best_score = None, -math.inf
        for m in self._ordered(board):
            if m not in allowed:
                continue
            board.push(m)
            try:
                score = -self._search(board, depth - 1, -beta, -alpha, 1)
            finally:
                board.pop()
            if score > best_score:
                best_score, best = score, m
            alpha = max(alpha, score)
        return best

    def _search(self, board, depth, alpha, beta, ply):
        if (self._nodes & 255) == 0 and time.monotonic() > self.deadline:
            raise _Timeout()
        self._nodes += 1
        if depth == 0:
            return self._eval(board)
        moves = self._ordered(board)
        if not moves:
            return -self.MATE + ply if board.is_check() else 0
        best = -math.inf
        for m in moves:
            board.push(m)
            try:
                score = -self._search(board, depth - 1, -beta, -alpha, ply + 1)
            finally:
                board.pop()
            if score > best:
                best = score
            alpha = max(alpha, score)
            if alpha >= beta:
                break
        return best

    def _eval(self, board):
        total = 0
        for sq, p in board.piece_map().items():
            v = self.CP[p.piece_type]
            f, r = chess.square_file(sq), chess.square_rank(sq)
            if p.piece_type == chess.PAWN:
                v += 6 * (r if p.color == chess.WHITE else 7 - r)
            elif p.piece_type != chess.KING:
                v += int(3 * (7 - (abs(f - 3.5) + abs(r - 3.5))))
            total += v if p.color == chess.WHITE else -v
        return total if board.turn == chess.WHITE else -total


class EngineWorker:
    """Executa o motor em thread para não congelar a interface."""

    def __init__(self):
        self.lock = threading.Lock()
        self.token = 0
        self.busy = False
        self.result = None
        self.start_ply = 0

    def start(self, board, level, seed, forbidden=None, epsilon=0.0, time_limit=ENGINE_TIME_LIMIT_S):
        self.cancel()
        snapshot = board.copy(stack=False)
        self.start_ply = ply = len(board.move_stack)
        forbidden = set(forbidden or ())
        with self.lock:
            token = self.token
            self.busy = True

        def run():
            try:
                eng = Engine(level, random.Random(f"{seed}-{ply}"), time_limit, epsilon)
                mv = eng.choose(snapshot, forbidden)
            except Exception:
                traceback.print_exc()
                legal = list(snapshot.legal_moves)
                mv = random.choice(legal) if legal else None
            with self.lock:
                if token == self.token:
                    self.result = mv

        threading.Thread(target=run, daemon=True).start()

    def cancel(self):
        with self.lock:
            self.token += 1
            self.busy = False
            self.result = None

    def poll(self):
        with self.lock:
            if self.busy and self.result is not None:
                mv, self.result, self.busy = self.result, None, False
                return mv
        return None


# ============================================================
# Registro de partidas únicas (garante que nenhuma partida se repita)
# ============================================================
class GameRegistry:
    """Guarda o hash SHA-1 da sequência completa de lances (UCI) de cada partida já jogada.
    Um lance que completaria uma sequência idêntica a uma partida registrada é proibido
    (se houver alternativa). Como o registro é persistente, a garantia vale entre execuções."""

    def __init__(self, path):
        self.path = Path(path)
        self.seen = set()
        try:
            if self.path.exists():
                self.seen = {ln.strip() for ln in self.path.read_text(encoding="utf-8").splitlines() if ln.strip()}
        except Exception:
            traceback.print_exc()

    @staticmethod
    def digest(ucis):
        return hashlib.sha1(" ".join(ucis).encode("utf-8")).hexdigest()

    def forbidden(self, board):
        """Lances legais que reproduziriam, até aqui, uma partida completa já registrada."""
        if not self.seen:
            return set()
        base = " ".join(m.uci() for m in board.move_stack)
        h = hashlib.sha1(base.encode("utf-8"))
        out = set()
        for m in board.legal_moves:
            h2 = h.copy()
            h2.update((" " + m.uci() if base else m.uci()).encode("utf-8"))
            if h2.hexdigest() in self.seen:
                out.add(m)
        return out

    def add(self, board):
        d = self.digest([m.uci() for m in board.move_stack])
        if d in self.seen:
            return False
        self.seen.add(d)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(d + "\n")
        except Exception:
            traceback.print_exc()
        return True


def randomize_session(sess):
    """Sorteia semente (criptográfica), nível de cada lado e ruído para uma partida do modo aleatório."""
    sysrand = random.SystemRandom()
    sess.seed = secrets.randbits(62)
    sess.levels = {chess.WHITE: sysrand.choice((0, 0, 1, 1, 2, 2, 3)),
                   chess.BLACK: sysrand.choice((0, 0, 1, 1, 2, 2, 3))}
    sess.epsilon = round(sysrand.uniform(0.05, 0.30), 3)
    sess.random_mode = True


def pick_move(sess, registry, move_time):
    """Escolha síncrona de lance (modo batch), respeitando unicidade e ruído da sessão."""
    ply = len(sess.board.move_stack)
    forb = registry.forbidden(sess.board) if registry else set()
    eng = Engine(sess.levels[sess.board.turn], random.Random(f"{sess.seed}-{ply}"), move_time, sess.epsilon)
    return eng.choose(sess.board, forb)


# ============================================================
# Sessão de jogo (mantém todas as listas sincronizadas)
# ============================================================
class GameSession:
    def __init__(self, mode_key="white", levels=None, seed=None):
        self.mode_key = mode_key
        self.levels = levels or {chess.WHITE: 2, chess.BLACK: 2}
        self.seed = seed if seed is not None else random.randrange(1 << 30)
        self.epsilon = 0.0
        self.random_mode = False
        self.reset()

    def reset(self):
        self.board = chess.Board()
        self.san, self.times, self.controllers, self.cap_log = [], [], [], []
        self.last_move = None
        self.turn_started = time.monotonic()
        self.started_at = dt.datetime.now()
        self.game_id = f"{self.started_at:%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:4]}"
        self.undo_count = 0
        self.aggregated = False
        self.outcome = None
        self.forced_termination = None

    def push(self, move, controller):
        b = self.board
        victim = None
        if b.is_capture(move):
            victim = chess.PAWN if b.is_en_passant(move) else b.piece_type_at(move.to_square)
        self.cap_log.append((b.turn, victim))
        self.san.append(b.san(move))
        self.times.append(time.monotonic() - self.turn_started)
        self.controllers.append(controller)
        b.push(move)
        self.last_move = move
        self.turn_started = time.monotonic()
        self.outcome = b.outcome(claim_draw=True)

    def pop(self):
        if not self.board.move_stack:
            return
        self.board.pop()
        for lst in (self.san, self.times, self.controllers, self.cap_log):
            lst.pop()
        self.last_move = self.board.peek() if self.board.move_stack else None
        self.turn_started = time.monotonic()
        self.outcome = self.board.outcome(claim_draw=True)

    def is_over(self):
        return self.outcome is not None or self.forced_termination is not None

    def result_info(self):
        if self.outcome is not None:
            term = self.outcome.termination.name.lower()
            winner = {True: "white", False: "black", None: "draw"}[self.outcome.winner]
            return self.outcome.result(), term, winner
        if self.forced_termination:
            return "*", self.forced_termination, ""
        return "*", "in_progress", ""

    def controller_of(self, color):
        if self.mode_key == "both":
            return "humano"
        if self.mode_key in ("cpu", "auto"):
            return "pc"
        return "humano" if (self.mode_key == "white") == (color == chess.WHITE) else "pc"

    def meta(self):
        now = dt.datetime.now()
        result, term, winner = self.result_info()
        return {
            "game_id": self.game_id, "started_at": self.started_at.isoformat(timespec="seconds"),
            "exported_at": now.isoformat(timespec="seconds"),
            "duration_s": round((now - self.started_at).total_seconds(), 2),
            "mode": self.mode_key,
            "white_controller": self.controller_of(chess.WHITE), "black_controller": self.controller_of(chess.BLACK),
            "white_level": self.levels[chess.WHITE] if self.controller_of(chess.WHITE) == "pc" else None,
            "black_level": self.levels[chess.BLACK] if self.controller_of(chess.BLACK) == "pc" else None,
            "seed": self.seed, "epsilon": self.epsilon, "random_mode": int(self.random_mode),
            "undo_count": self.undo_count,
            "result": result, "termination": term, "winner": winner,
            "finished": self.is_over(),
        }


# ============================================================
# Rastreamento individual de peças
# ============================================================
class PieceTracker:
    """Acompanha cada peça (identificada pela casa inicial) ao longo da partida."""

    def __init__(self):
        self.pieces, self.sq_to_id, self.ply = {}, {}, 0
        for sq, p in chess.Board().piece_map().items():
            self.pieces[sq] = {
                "id": sq, "color": p.color, "type": p.piece_type, "final_type": p.piece_type,
                "path": [sq], "path_plies": [0],
                "captured_at": None, "captured_ply": None, "captured_by": None,
                "captures_made": 0, "promoted_ply": None,
            }
            self.sq_to_id[sq] = sq

    def track_move(self, board_before, move):
        self.ply += 1
        from_sq, to_sq = move.from_square, move.to_square
        mover_id = self.sq_to_id.get(from_sq)

        captured_sq = to_sq
        if board_before.is_en_passant(move):
            captured_sq = to_sq - 8 if board_before.turn == chess.WHITE else to_sq + 8
        victim_id = self.sq_to_id.get(captured_sq)
        if victim_id is not None and victim_id != mover_id:
            v = self.pieces[victim_id]
            v["captured_at"], v["captured_ply"], v["captured_by"] = captured_sq, self.ply, mover_id
            del self.sq_to_id[captured_sq]
            if mover_id is not None:
                self.pieces[mover_id]["captures_made"] += 1

        if board_before.is_castling(move):
            rook = {chess.G1: (chess.H1, chess.F1), chess.C1: (chess.A1, chess.D1),
                    chess.G8: (chess.H8, chess.F8), chess.C8: (chess.A8, chess.D8)}.get(to_sq)
            if rook and rook[0] in self.sq_to_id:
                rid = self.sq_to_id.pop(rook[0])
                self.pieces[rid]["path"].append(rook[1])
                self.pieces[rid]["path_plies"].append(self.ply)
                self.sq_to_id[rook[1]] = rid

        if mover_id is not None:
            self.sq_to_id.pop(from_sq, None)
            p = self.pieces[mover_id]
            p["path"].append(to_sq)
            p["path_plies"].append(self.ply)
            self.sq_to_id[to_sq] = mover_id
            if move.promotion:
                p["final_type"], p["promoted_ply"] = move.promotion, self.ply


# ============================================================
# Análise estatística da partida
# ============================================================
HEAT_KEYS = ["destinations", "traffic", "captures", "occupancy_white", "occupancy_black",
             "control_white", "control_black"]

MOVE_FIELDS = ["game_id", "ply", "move_number", "color", "controller", "san", "uci", "piece", "from", "to",
               "capture", "captured_piece", "en_passant", "castling", "promotion", "check", "checkmate",
               "legal_moves_before", "opp_mobility_after", "material_white", "material_black",
               "material_balance", "nonpawn_material", "phase", "halfmove_clock", "time_s", "fen_after"]

PIECE_FIELDS = ["game_id", "label", "start_square", "color", "type", "final_type", "promoted", "moves",
                "dist_euclid", "dist_manhattan", "unique_squares", "revisits", "captures_made", "captured",
                "captured_at", "captured_ply", "captured_by", "first_move_ply", "last_move_ply",
                "lifetime_plies", "activity_ratio", "final_square", "path", "path_plies"]

GAME_FIELDS = [
    "game_id", "started_at", "exported_at", "duration_s", "mode", "white_controller", "black_controller",
    "white_level", "black_level", "seed", "epsilon", "random_mode", "undo_count", "result", "winner", "termination", "finished",
    "plies", "full_moves", "white_captures", "black_captures", "white_material_captured",
    "black_material_captured", "white_checks", "black_checks", "white_castle_ply", "black_castle_ply",
    "promotions", "en_passants", "recaptures", "first_capture_ply", "first_check_ply",
    "first_promotion_ply", "endgame_start_ply", "final_material_balance", "max_adv_white", "max_adv_black",
    "lead_changes", "avg_branching", "white_avg_branching", "black_avg_branching",
    "white_avg_time_s", "black_avg_time_s", "max_quiet_streak", "opening_san", "final_fen",
]


def _phase(ply, npm):
    if ply <= 20:
        return "opening"
    return "endgame" if npm <= 26 else "middlegame"


def analyze_game(moves, controllers=None, times=None, game_id=""):
    board = chess.Board()
    tracker = PieceTracker()
    heat = {k: [0] * 64 for k in HEAT_KEYS}
    rows, max_quiet = [], 0

    for i, mv in enumerate(moves):
        ply, color = i + 1, board.turn
        piece = board.piece_at(mv.from_square)
        is_ep, is_castle, is_cap = board.is_en_passant(mv), board.is_castling(mv), board.is_capture(mv)
        cap_pt = chess.PAWN if is_ep else (board.piece_type_at(mv.to_square) if is_cap else None)
        cap_sq = (mv.to_square - 8 if color == chess.WHITE else mv.to_square + 8) if is_ep else mv.to_square
        legal_before = board.legal_moves.count()
        san = board.san(mv)
        tracker.track_move(board, mv)

        heat["destinations"][mv.to_square] += 1
        heat["traffic"][mv.to_square] += 1
        if piece.piece_type != chess.KNIGHT:
            for s in squares_between(mv.from_square, mv.to_square):
                heat["traffic"][s] += 1
        if is_cap:
            heat["captures"][cap_sq] += 1

        board.push(mv)
        gives_check, mate = board.is_check(), board.is_checkmate()
        wm, bm = material(board, chess.WHITE), material(board, chess.BLACK)
        npm = nonpawn_material(board)
        max_quiet = max(max_quiet, board.halfmove_clock)

        for sq, p in board.piece_map().items():
            side = "white" if p.color == chess.WHITE else "black"
            heat["occupancy_" + side][sq] += 1
            for t in board.attacks(sq):
                heat["control_" + side][t] += 1

        t = times[i] if times and i < len(times) else None
        rows.append({
            "game_id": game_id, "ply": ply, "move_number": (ply + 1) // 2,
            "color": "white" if color == chess.WHITE else "black",
            "controller": controllers[i] if controllers and i < len(controllers) else "",
            "san": san, "uci": mv.uci(), "piece": piece_name_en(piece.piece_type),
            "from": chess.square_name(mv.from_square), "to": chess.square_name(mv.to_square),
            "capture": int(is_cap), "captured_piece": piece_name_en(cap_pt) if cap_pt else "",
            "en_passant": int(is_ep), "castling": int(is_castle),
            "promotion": piece_name_en(mv.promotion) if mv.promotion else "",
            "check": int(gives_check), "checkmate": int(mate),
            "legal_moves_before": legal_before, "opp_mobility_after": board.legal_moves.count(),
            "material_white": wm, "material_black": bm, "material_balance": wm - bm,
            "nonpawn_material": npm, "phase": _phase(ply, npm), "halfmove_clock": board.halfmove_clock,
            "time_s": round(t, 3) if t is not None else "", "fen_after": board.fen(),
        })

    total_plies = len(moves)
    pieces = []
    for p in tracker.pieces.values():
        path, plies_at = p["path"], p["path_plies"]
        names = [chess.square_name(s) for s in path]
        steps = list(zip(path, path[1:]))
        d_e = sum(math.hypot(chess.square_file(b) - chess.square_file(a),
                             chess.square_rank(b) - chess.square_rank(a)) for a, b in steps)
        d_m = sum(abs(chess.square_file(b) - chess.square_file(a)) +
                  abs(chess.square_rank(b) - chess.square_rank(a)) for a, b in steps)
        uniq = len(set(path))
        life = (p["captured_ply"] - 1) if p["captured_ply"] else total_plies
        own_turns = (life + 1) // 2 if p["color"] == chess.WHITE else life // 2
        cap_by = tracker.pieces[p["captured_by"]] if p["captured_by"] is not None else None
        pieces.append({
            "game_id": game_id,
            "label": f"{FALLBACK_LETTER[p['type']]}{chess.square_name(p['id'])}",
            "start_square": chess.square_name(p["id"]),
            "color": "white" if p["color"] == chess.WHITE else "black",
            "type": piece_name_en(p["type"]), "final_type": piece_name_en(p["final_type"]),
            "promoted": int(p["promoted_ply"] is not None), "moves": len(steps),
            "dist_euclid": round(d_e, 3), "dist_manhattan": d_m,
            "unique_squares": uniq, "revisits": max(0, len(steps) - (uniq - 1)),
            "captures_made": p["captures_made"], "captured": int(p["captured_at"] is not None),
            "captured_at": chess.square_name(p["captured_at"]) if p["captured_at"] is not None else None,
            "captured_ply": p["captured_ply"],
            "captured_by": f"{FALLBACK_LETTER[cap_by['type']]}{chess.square_name(cap_by['id'])}" if cap_by else None,
            "first_move_ply": plies_at[1] if len(plies_at) > 1 else None,
            "last_move_ply": plies_at[-1] if len(plies_at) > 1 else None,
            "lifetime_plies": life,
            "activity_ratio": round(len(steps) / own_turns, 4) if own_turns else 0.0,
            "final_square": None if p["captured_at"] is not None else names[-1],
            "path": names, "path_plies": plies_at,
            "_color_bool": p["color"], "_type_int": p["type"],
        })
    return {"moves": rows, "pieces": pieces, "heat": heat, "final_board": board, "max_quiet": max_quiet}


def build_summary(sess, an, filters):
    meta = sess.meta()
    rows, pieces = an["moves"], an["pieces"]
    n = len(rows)
    summary = {"schema_version": SCHEMA_VERSION, "app_version": APP_VERSION,
               "environment": {"python": platform.python_version(), "pygame": pygame.version.ver,
                               "python_chess": getattr(chess, "__version__", "?"), "platform": platform.platform()},
               "meta": meta, "export_filters": dict(filters), "plies": n, "full_moves": (n + 1) // 2,
               "final_fen": an["final_board"].fen()}

    sides = {}
    for side in ("white", "black"):
        r = [x for x in rows if x["color"] == side]
        ts = [x["time_s"] for x in r if x["time_s"] != ""]
        castle = [x["ply"] for x in r if x["castling"]]
        sides[side] = {
            "moves": len(r),
            "captures": sum(x["capture"] for x in r),
            "material_captured": sum(PIECE_VALUES[NAME_TO_PT[x["captured_piece"]]]
                                     for x in r if x["captured_piece"]),
            "checks_given": sum(x["check"] for x in r),
            "castle_ply": castle[0] if castle else None,
            "promotions": sum(1 for x in r if x["promotion"]),
            "en_passants": sum(x["en_passant"] for x in r),
            "avg_branching": mean_or_none([x["legal_moves_before"] for x in r]),
            "avg_opp_mobility_after": mean_or_none([x["opp_mobility_after"] for x in r]),
            "time_s": describe(ts),
            "pieces_lost": sum(1 for p in pieces if p["color"] == side and p["captured"]),
        }
    summary["sides"] = sides

    bal = [x["material_balance"] for x in rows]
    nz = [b for b in bal if b != 0]
    lead_changes = sum(1 for a, b in zip(nz, nz[1:]) if (a > 0) != (b > 0))
    summary["material"] = {
        "final_balance_white_minus_black": bal[-1] if bal else 0,
        "max_advantage_white": max([0] + bal), "max_advantage_black": max([0] + [-b for b in bal]),
        "lead_changes": lead_changes, "series": bal,
    }

    first = lambda pred: next((x["ply"] for x in rows if pred(x)), None)
    recaptures = sum(1 for a, b in zip(rows, rows[1:]) if a["capture"] and b["capture"] and a["to"] == b["to"])
    summary["timeline"] = {
        "first_capture_ply": first(lambda x: x["capture"]), "first_check_ply": first(lambda x: x["check"]),
        "first_promotion_ply": first(lambda x: x["promotion"]),
        "endgame_start_ply": first(lambda x: x["phase"] == "endgame"),
        "recaptures": recaptures, "max_quiet_streak_plies": an["max_quiet"],
        "opening_san": " ".join(sess.san[:6]),
    }

    phases = {}
    for ph in ("opening", "middlegame", "endgame"):
        r = [x for x in rows if x["phase"] == ph]
        phases[ph] = {"plies": len(r), "captures": sum(x["capture"] for x in r),
                      "checks": sum(x["check"] for x in r),
                      "avg_branching": mean_or_none([x["legal_moves_before"] for x in r])}
    summary["phases"] = phases

    by_type = {}
    for color in ("white", "black"):
        for pt in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING):
            grp = [p for p in pieces if p["color"] == color and p["_type_int"] == pt]
            by_type[f"{color}_{piece_name_en(pt)}"] = {
                "count": len(grp), "avg_moves": mean_or_none([p["moves"] for p in grp]),
                "total_dist_euclid": round(sum(p["dist_euclid"] for p in grp), 3),
                "captures_made": sum(p["captures_made"] for p in grp),
                "lost": sum(p["captured"] for p in grp),
                "survival_rate": round(1 - sum(p["captured"] for p in grp) / len(grp), 4),
                "never_moved": sum(1 for p in grp if p["moves"] == 0),
                "avg_activity_ratio": mean_or_none([p["activity_ratio"] for p in grp]),
            }
    summary["piece_stats"] = by_type
    summary["hotspots"] = {k: top_squares(an["heat"][k]) for k in ("destinations", "traffic", "captures")}
    return summary


def summary_to_game_row(summary):
    m, s, tl = summary["meta"], summary["sides"], summary["timeline"]
    mat = summary["material"]
    row = {k: m.get(k) for k in GAME_FIELDS if k in m}
    row.update({
        "plies": summary["plies"], "full_moves": summary["full_moves"],
        "white_captures": s["white"]["captures"], "black_captures": s["black"]["captures"],
        "white_material_captured": s["white"]["material_captured"],
        "black_material_captured": s["black"]["material_captured"],
        "white_checks": s["white"]["checks_given"], "black_checks": s["black"]["checks_given"],
        "white_castle_ply": s["white"]["castle_ply"], "black_castle_ply": s["black"]["castle_ply"],
        "promotions": s["white"]["promotions"] + s["black"]["promotions"],
        "en_passants": s["white"]["en_passants"] + s["black"]["en_passants"],
        "recaptures": tl["recaptures"], "first_capture_ply": tl["first_capture_ply"],
        "first_check_ply": tl["first_check_ply"], "first_promotion_ply": tl["first_promotion_ply"],
        "endgame_start_ply": tl["endgame_start_ply"],
        "final_material_balance": mat["final_balance_white_minus_black"],
        "max_adv_white": mat["max_advantage_white"], "max_adv_black": mat["max_advantage_black"],
        "lead_changes": mat["lead_changes"],
        "white_avg_branching": s["white"]["avg_branching"], "black_avg_branching": s["black"]["avg_branching"],
        "white_avg_time_s": s["white"]["time_s"].get("mean"), "black_avg_time_s": s["black"]["time_s"].get("mean"),
        "max_quiet_streak": tl["max_quiet_streak_plies"], "opening_san": tl["opening_san"],
        "final_fen": summary["final_fen"],
    })
    br = [b for b in (s["white"]["avg_branching"], s["black"]["avg_branching"]) if b is not None]
    row["avg_branching"] = round(statistics.fmean(br), 4) if br else None
    return row


# ============================================================
# Escrita de arquivos (atômica + CSV incremental robusto)
# ============================================================
def _atomic_write_text(path, text):
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path, data):
    _atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False, default=str))


def write_csv(path, rows, fields, append=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if append and path.exists():
        with open(path, "r", encoding="utf-8", newline="") as f:
            header = next(csv.reader(f), None)
        if header != fields:  # esquema mudou: preserva o arquivo antigo em vez de corromper
            path.rename(path.with_name(f"{path.stem}.old_{dt.datetime.now():%Y%m%d%H%M%S}{path.suffix}"))
    new_file = not (append and path.exists())
    mode = "a" if append and not new_file else "w"
    with open(path, mode, encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if new_file:
            w.writeheader()
        w.writerows(rows)


def _csv_piece_row(p):
    q = dict(p)
    q["path"] = "-".join(p["path"])
    q["path_plies"] = "-".join(str(x) for x in p["path_plies"])
    return q


def write_pgn(path, sess):
    meta = sess.meta()
    game = chess.pgn.Game()
    game.headers.update({
        "Event": "Simulador de Xadrez", "Site": "Local", "Date": sess.started_at.strftime("%Y.%m.%d"),
        "Round": "-", "White": "Humano" if meta["white_controller"] == "humano" else f"PC (nível {meta['white_level']})",
        "Black": "Humano" if meta["black_controller"] == "humano" else f"PC (nível {meta['black_level']})",
        "Result": meta["result"], "Termination": meta["termination"], "GameId": sess.game_id,
    })
    node = game
    for mv, t in zip(sess.board.move_stack, sess.times):
        node = node.add_variation(mv)
        node.comment = f"{t:.2f}s"
    with open(path, "w", encoding="utf-8") as f:
        print(game, file=f, end="\n\n")


# ============================================================
# Imagens de saída (funcionam sem janela) — tema neon
# ============================================================
def _font(size):
    return pygame.font.Font(None, size)


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def heat_color(t):
    """Escala fantasmagórica: violeta escuro -> roxo -> magenta -> ciano neon."""
    t = max(0.0, min(1.0, t))
    stops = [(30, 10, 90), (140, 40, 220), (255, 50, 190), (60, 255, 235)]
    x = t * (len(stops) - 1)
    i = min(int(x), len(stops) - 2)
    return _lerp(stops[i], stops[i + 1], x - i)


def with_alpha(surface, alpha):
    s = surface.copy()
    s.fill((255, 255, 255, max(0, min(255, alpha))), special_flags=pygame.BLEND_RGBA_MULT)
    return s


def glow_rect(screen, rect, color, width=2, spread=7, radius=6):
    """Retângulo com brilho neon (várias camadas translúcidas ao redor)."""
    layer = pygame.Surface((rect.w + spread * 2, rect.h + spread * 2), pygame.SRCALPHA)
    for i in range(spread, 0, -1):
        a = int(70 * (1 - i / (spread + 1))) + 6
        pygame.draw.rect(layer, (*color, a), pygame.Rect(spread - i, spread - i, rect.w + 2 * i, rect.h + 2 * i),
                         2, border_radius=radius + i)
    pygame.draw.rect(layer, (*color, 255), pygame.Rect(spread, spread, rect.w, rect.h), width, border_radius=radius)
    screen.blit(layer, (rect.x - spread, rect.y - spread))


def glow_circle(screen, center, r, color, spread=8):
    layer = pygame.Surface(((r + spread) * 2, (r + spread) * 2), pygame.SRCALPHA)
    c = (r + spread, r + spread)
    for i in range(spread, 0, -1):
        pygame.draw.circle(layer, (*color, int(60 * (1 - i / (spread + 1))) + 6), c, r + i)
    pygame.draw.circle(layer, (*color, 255), c, r)
    screen.blit(layer, (center[0] - c[0], center[1] - c[1]))


def fit_text(font, text, max_w):
    if font.size(text)[0] <= max_w:
        return text
    while text and font.size(text + "...")[0] > max_w:
        text = text[:-1]
    return text + "..."


def draw_base_board(size=BOARD_SIZE, coords=True):
    surf, sq = pygame.Surface((size, size)), size // 8
    f = _font(18)
    for row in range(8):
        for col in range(8):
            rect = pygame.Rect(col * sq, row * sq, sq, sq)
            pygame.draw.rect(surf, COLOR_LIGHT if (row + col) % 2 == 0 else COLOR_DARK, rect)
            pygame.draw.rect(surf, COLOR_GRID, rect, 1)
            if coords:
                if col == 0:
                    surf.blit(f.render(str(8 - row), True, COLOR_COORD), (col * sq + 3, row * sq + 2))
                if row == 7:
                    lab = f.render("abcdefgh"[col], True, COLOR_COORD)
                    surf.blit(lab, (col * sq + sq - lab.get_width() - 4, row * sq + sq - lab.get_height() - 2))
    return surf


def _sq_center(sq):
    return (chess.square_file(sq) * SQ_SIZE + SQ_SIZE // 2, (7 - chess.square_rank(sq)) * SQ_SIZE + SQ_SIZE // 2)


def render_trace_png(pieces, path, subtitle=""):
    base = draw_base_board()
    layer = pygame.Surface((BOARD_SIZE, BOARD_SIZE), pygame.SRCALPHA)
    for p in pieces:
        if len(p["path"]) < 2:
            continue
        col = TRACE_COLORS[(p["_color_bool"], p["_type_int"])]
        w = TRACE_WIDTH[p["_type_int"]]
        pts = [_sq_center(chess.parse_square(s)) for s in p["path"]]
        pygame.draw.lines(layer, (*col, 45), False, pts, w + 10)    # brilho externo
        pygame.draw.lines(layer, (*col, 90), False, pts, w + 5)     # brilho interno
        pygame.draw.lines(layer, (*col, 235), False, pts, w)        # núcleo
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        ang = math.atan2(y1 - y0, x1 - x0)
        head = [(x1, y1)] + [(x1 - 14 * math.cos(ang + s), y1 - 14 * math.sin(ang + s)) for s in (0.45, -0.45)]
        pygame.draw.polygon(layer, (*col, 240), head)
        pygame.draw.circle(layer, (*col, 70), pts[0], 12)
        pygame.draw.circle(layer, (*col, 255), pts[0], 6)
        pygame.draw.circle(layer, COLOR_VOID, pts[0], 6, 2)
        if p["captured_at"]:
            cx, cy = _sq_center(chess.parse_square(p["captured_at"]))
            for a, b in (((-12, -12), (12, 12)), ((12, -12), (-12, 12))):
                pygame.draw.line(layer, (*col, 70), (cx + a[0], cy + a[1]), (cx + b[0], cy + b[1]), 12)
                pygame.draw.line(layer, (*col, 255), (cx + a[0], cy + a[1]), (cx + b[0], cy + b[1]), 5)
    base.blit(layer, (0, 0))
    out = pygame.Surface((BOARD_SIZE, BOARD_SIZE + 44))
    out.fill(COLOR_VOID)
    out.blit(base, (0, 0))
    out.blit(_font(22).render(tr("trace_legend"), True, COLOR_TEXT), (10, BOARD_SIZE + 6))
    if subtitle:
        out.blit(_font(20).render(subtitle, True, COLOR_MUTED), (10, BOARD_SIZE + 26))
    pygame.image.save(out, str(path))


def render_heatmap_png(values, title, path):
    base = draw_base_board(coords=True)
    mx = max(values) if max(values) > 0 else 1
    f = _font(24)
    for sq in chess.SQUARES:
        v = values[sq]
        if v <= 0:
            continue
        t = v / mx
        rect = pygame.Rect(*[c - SQ_SIZE // 2 for c in _sq_center(sq)], SQ_SIZE, SQ_SIZE)
        ov = pygame.Surface((SQ_SIZE, SQ_SIZE), pygame.SRCALPHA)
        ov.fill((*heat_color(t), int(80 + 160 * t)))
        base.blit(ov, rect.topleft)
        lab = f.render(str(v), True, (240, 245, 255) if t < 0.85 else (10, 10, 30))
        base.blit(lab, lab.get_rect(center=rect.center))
    out = pygame.Surface((BOARD_SIZE, BOARD_SIZE + 60))
    out.fill(COLOR_VOID)
    out.blit(base, (0, 0))
    out.blit(_font(26).render(f"{title}  ({tr('heat_max')} = {mx})", True, COLOR_TEXT), (10, BOARD_SIZE + 6))
    for i in range(300):
        pygame.draw.line(out, heat_color(i / 299), (10 + i, BOARD_SIZE + 36), (10 + i, BOARD_SIZE + 50))
    out.blit(_font(18).render("0", True, COLOR_MUTED), (316, BOARD_SIZE + 36))
    out.blit(_font(18).render(tr("heat_max"), True, COLOR_MUTED), (340, BOARD_SIZE + 36))
    pygame.image.save(out, str(path))


def render_material_png(rows, path):
    W, H = 900, 560
    surf = pygame.Surface((W, H))
    surf.fill(COLOR_VOID)
    f, fs = _font(26), _font(18)
    n = len(rows)
    if n == 0:
        surf.blit(f.render(tr("no_moves"), True, COLOR_TEXT), (20, 20))
        pygame.image.save(surf, str(path))
        return

    def panel(rect, title):
        pygame.draw.rect(surf, COLOR_PANEL, rect)
        pygame.draw.rect(surf, COLOR_BORDER, rect, 1)
        surf.blit(f.render(title, True, COLOR_HIGHLIGHT), (rect.x, rect.y - 26))

    def xpos(rect, i):
        return rect.x + (rect.w * i / (n - 1) if n > 1 else rect.w / 2)

    r1, r2 = pygame.Rect(70, 50, 800, 210), pygame.Rect(70, 320, 800, 190)
    panel(r1, tr("mat_title1"))
    lim = max(3, max(abs(r["material_balance"]) for r in rows))
    zero_y = r1.centery
    pygame.draw.line(surf, COLOR_COORD, (r1.x, zero_y), (r1.right, zero_y), 1)
    bw = max(1, int(r1.w / n) - 1)
    for i, r in enumerate(rows):
        h = int(r["material_balance"] / lim * (r1.h / 2 - 6))
        color = TRACE_COLORS[(True, chess.BISHOP)] if h >= 0 else COLOR_MAGENTA
        pygame.draw.rect(surf, color, pygame.Rect(int(xpos(r1, i)) - bw // 2, zero_y - max(h, 0), bw, abs(h) or 1))
    surf.blit(fs.render(f"+{lim}", True, COLOR_MUTED), (20, r1.y))
    surf.blit(fs.render(f"-{lim}", True, COLOR_MUTED), (20, r1.bottom - 16))

    panel(r2, tr("mat_title2"))
    mb = max(r["legal_moves_before"] for r in rows) or 1
    for side, col in (("white", TRACE_COLORS[(True, chess.BISHOP)]), ("black", COLOR_MAGENTA)):
        pts = [(xpos(r2, i), r2.bottom - 6 - r["legal_moves_before"] / mb * (r2.h - 12))
               for i, r in enumerate(rows) if r["color"] == side]
        if len(pts) >= 2:
            pygame.draw.lines(surf, (*col,), False, pts, 2)
        elif pts:
            pygame.draw.circle(surf, col, pts[0], 3)
    surf.blit(fs.render(str(mb), True, COLOR_MUTED), (30, r2.y))
    surf.blit(fs.render(tr("mat_axis", n), True, COLOR_MUTED), (70, H - 28))
    pygame.image.save(surf, str(path))


# ============================================================
# Exportação
# ============================================================
DICT_PT = """# Dicionário de dados

Arquivos em UTF-8. Casas em notação algébrica (e4). `ply` = meio-lance (1 = primeiro lance das brancas).
Valores categóricos são sempre em inglês (independentes do idioma da interface): white/black,
opening/middlegame/endgame, humano/pc. `game_id` liga `moves.csv`, `pieces.csv` e `games_log.csv`.

## dataset/games_log.csv (uma linha por partida finalizada)
Metadados (modo, níveis do PC, seed, `epsilon` = ruído aleatório do PC, `random_mode`, desfazeres), resultado,
término e métricas: capturas, material capturado, xeques, roque, promoções, en passant, recapturas,
1ª captura/xeque, início do final, balanço de material, vantagem máxima, trocas de liderança,
ramificação média, tempo médio por lance, maior sequência sem captura/avanço de peão, abertura e FEN final.

## moves.csv / dataset/moves_all.csv (uma linha por lance)
`legal_moves_before` = lances legais disponíveis (ramificação). `opp_mobility_after` = lances legais do
adversário depois do lance. `material_*` em peões (P1 N3 B3 R5 Q9). `phase`: opening (ply<=20), endgame
(material não-peão <= 26), middlegame (resto). `time_s`: tempo gasto. `controller`: humano | pc.

## pieces.csv / dataset/pieces_all.csv (uma linha por peça inicial, 32 por partida)
`label` = tipo+casa inicial (Ng1). `moves`, `dist_euclid`/`dist_manhattan`, `unique_squares`, `revisits`,
`captures_made`, `captured*`, `lifetime_plies`, `activity_ratio` (lances da peça / turnos do seu lado
enquanto viva), `path` e `path_plies` (casas e ply de cada passo, separados por "-").
Os filtros da interface valem só para o `pieces.csv` da pasta da partida; `pieces_all.csv` é completo.

## heatmaps.csv (formato longo: map, square, file, rank, value)
destinations, traffic (inclui casas atravessadas), captures, occupancy_white/black, control_white/black.

## dataset/seen_games.txt
Hash SHA-1 de cada partida do auto-jogo aleatório / `--random`; impede que uma partida se repita.

## summary.json
Tudo agregado por lado, fase e tipo de peça + pontos quentes, ambiente e filtros usados.
"""

DICT_EN = """# Data dictionary

UTF-8 files. Squares in algebraic notation (e4). `ply` = half-move (1 = White's first move).
Categorical values are always English (independent of the UI language): white/black,
opening/middlegame/endgame, humano/pc. `game_id` links `moves.csv`, `pieces.csv` and `games_log.csv`.

## dataset/games_log.csv (one row per finished game)
Metadata (mode, PC levels, seed, `epsilon` = PC random noise, `random_mode`, undo count), result,
termination and metrics: captures, material captured, checks, castling, promotions, en passant,
recaptures, first capture/check, endgame start, material balance, max advantage, lead changes,
average branching, average time per move, longest quiet streak, opening and final FEN.

## moves.csv / dataset/moves_all.csv (one row per move)
`legal_moves_before` = legal moves available (branching). `opp_mobility_after` = opponent's legal moves
after the move. `material_*` in pawns (P1 N3 B3 R5 Q9). `phase`: opening (ply<=20), endgame
(non-pawn material <= 26), middlegame (rest). `time_s`: time spent. `controller`: humano | pc.

## pieces.csv / dataset/pieces_all.csv (one row per starting piece, 32 per game)
`label` = type+start square (Ng1). `moves`, `dist_euclid`/`dist_manhattan`, `unique_squares`, `revisits`,
`captures_made`, `captured*`, `lifetime_plies`, `activity_ratio` (piece moves / own-side turns while
alive), `path` and `path_plies` (squares and ply of each step, joined by "-").
UI filters only apply to the game-folder `pieces.csv`; `pieces_all.csv` is always complete.

## heatmaps.csv (long format: map, square, file, rank, value)
destinations, traffic (includes crossed squares), captures, occupancy_white/black, control_white/black.

## dataset/seen_games.txt
SHA-1 hash of every random self-play / `--random` game; prevents any game from repeating.

## summary.json
Everything aggregated by side, phase and piece type + hotspots, environment and filters used.
"""


def _passes_filters(p, filters):
    c_ok = filters["brancas"] if p["_color_bool"] == chess.WHITE else filters["pretas"]
    return c_ok and filters[TYPE_FILTER[p["_type_int"]]]


def export_game(sess, out_root, filters=None, folder=True, aggregate=False, images=True):
    """Gera todos os arquivos da partida. Retorna dict com summary, análise e pasta."""
    filters = filters or {k: True for k in FILTER_KEYS}
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    for fname, text in (("DICIONARIO_DE_DADOS.md", DICT_PT), ("DATA_DICTIONARY.md", DICT_EN)):
        if not (out_root / fname).exists():
            _atomic_write_text(out_root / fname, text)

    moves = list(sess.board.move_stack)
    an = analyze_game(moves, sess.controllers, sess.times, sess.game_id)
    summary = build_summary(sess, an, filters)
    result = {"summary": summary, "analysis": an, "folder": None}

    if folder:
        d = out_root / "partidas" / f"{sess.game_id}_{len(moves)}plies"
        d.mkdir(parents=True, exist_ok=True)
        fpieces = [p for p in an["pieces"] if _passes_filters(p, filters)]
        write_json(d / "summary.json", summary)
        write_csv(d / "moves.csv", an["moves"], MOVE_FIELDS)
        write_csv(d / "pieces.csv", [_csv_piece_row(p) for p in fpieces], PIECE_FIELDS)
        write_json(d / "traces.json", [{k: v for k, v in p.items() if not k.startswith("_")} for p in fpieces])
        heat_rows = [{"map": k, "square": chess.square_name(s), "file": chess.square_file(s) + 1,
                      "rank": chess.square_rank(s) + 1, "value": an["heat"][k][s]}
                     for k in HEAT_KEYS for s in chess.SQUARES]
        write_csv(d / "heatmaps.csv", heat_rows, ["map", "square", "file", "rank", "value"])
        write_pgn(d / "partida.pgn", sess)
        if images:
            sub = f"{sess.game_id} | {summary['meta']['result']} | {len(moves)} plies"
            render_trace_png(fpieces, d / "trace.png", sub)
            for k in ("destinations", "traffic", "captures", "control_white", "control_black"):
                render_heatmap_png(an["heat"][k], tr("heat_title", tr("map_" + k)), d / f"heat_{k}.png")
            render_material_png(an["moves"], d / "material.png")
        result["folder"] = d

    if aggregate and sess.is_over():
        ds = out_root / "dataset"
        write_csv(ds / "games_log.csv", [summary_to_game_row(summary)], GAME_FIELDS, append=True)
        write_csv(ds / "moves_all.csv", an["moves"], MOVE_FIELDS, append=True)
        write_csv(ds / "pieces_all.csv", [_csv_piece_row(p) for p in an["pieces"]], PIECE_FIELDS, append=True)
        sess.aggregated = True
    return result


# ============================================================
# Modo batch (PC vs PC sem interface) e relatório
# ============================================================
def run_batch(args):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.font.init()
    out_root = Path(args.out)
    batch_id = f"{dt.datetime.now():%Y%m%d_%H%M%S}"
    base_seed = args.seed if args.seed is not None else random.randrange(1 << 30)
    summaries, heat_sum = [], {k: [0] * 64 for k in HEAT_KEYS}
    registry = GameRegistry(out_root / "dataset" / "seen_games.txt") if args.random else None
    if args.random:
        print(tr("batch_random", batch_id, args.batch))
        print(tr("unique_known", len(registry.seen)))
    else:
        print(tr("batch_start", batch_id, args.batch, args.white_level, args.black_level, base_seed))

    for g in range(args.batch):
        sess = GameSession("auto" if args.random else "cpu",
                           {chess.WHITE: args.white_level, chess.BLACK: args.black_level}, base_seed + g)
        if args.random:
            randomize_session(sess)
        sess.game_id = f"{batch_id}_{g + 1:05d}"
        while not sess.is_over():
            if len(sess.board.move_stack) >= args.max_plies:
                sess.forced_termination = "max_plies"
                break
            mv = pick_move(sess, registry, args.move_time)
            if mv is None:
                break
            sess.push(mv, "pc")
        try:
            res = export_game(sess, out_root, folder=args.full, aggregate=True, images=args.full)
        except Exception:
            traceback.print_exc()
            continue
        if registry:
            registry.add(sess.board)
        summaries.append(res["summary"])
        for k in HEAT_KEYS:
            for s in range(64):
                heat_sum[k][s] += res["analysis"]["heat"][k][s]
        m = res["summary"]["meta"]
        print(f"  [{g + 1}/{args.batch}] {m['result']:>7} {m['termination']:<22} {res['summary']['plies']:>3} plies"
              + (f"  L{m['white_level']}/L{m['black_level']} eps={m['epsilon']}" if args.random else ""))

    if not summaries:
        print(tr("no_games"))
        return
    stats = aggregate_stats(summaries)
    bdir = out_root / "batches"
    bdir.mkdir(parents=True, exist_ok=True)
    write_json(bdir / f"batch_{batch_id}.json", {
        "batch_id": batch_id, "config": {"games": args.batch, "white_level": args.white_level,
                                         "black_level": args.black_level, "base_seed": base_seed,
                                         "move_time": args.move_time, "max_plies": args.max_plies,
                                         "random_unique": bool(args.random)},
        "stats": stats, "heatmaps_sum": heat_sum})
    for k in ("destinations", "traffic", "captures", "control_white", "control_black"):
        render_heatmap_png(heat_sum[k], tr("batch_heat", len(summaries), tr("map_" + k)),
                           bdir / f"batch_{batch_id}_{k}.png")
    print_stats(stats)
    if registry:
        print(tr("unique_known", len(registry.seen)))
    print("\n" + tr("data_in", out_root.resolve()))


def aggregate_stats(summaries):
    n = len(summaries)
    metas = [s["meta"] for s in summaries]
    w = sum(1 for m in metas if m["winner"] == "white")
    b = sum(1 for m in metas if m["winner"] == "black")
    d = sum(1 for m in metas if m["winner"] == "draw")
    rows = [summary_to_game_row(s) for s in summaries]

    def ci(k):
        lo, hi = wilson_interval(k, n)
        return {"count": k, "rate": k / n, "ci95": [round(lo, 4), round(hi, 4)]}

    metrics = ["plies", "white_captures", "black_captures", "white_checks", "black_checks", "recaptures",
               "lead_changes", "avg_branching", "max_quiet_streak", "first_capture_ply", "first_check_ply",
               "final_material_balance", "duration_s"]
    return {"games": n, "white_wins": ci(w), "black_wins": ci(b), "draws": ci(d),
            "unfinished": n - w - b - d,
            "terminations": dict(Counter(m["termination"] for m in metas)),
            "metrics": {k: describe([r.get(k) for r in rows]) for k in metrics}}


def _print_table(items):
    print(f"\n{tr('metric'):<24}{'n':>5}{tr('mean'):>10}{tr('median'):>10}{tr('stdev'):>10}{tr('min'):>8}{tr('max'):>8}")
    for k, v in items:
        if v["n"]:
            print(f"{k:<24}{v['n']:>5}{v['mean']:>10.2f}{v['median']:>10.2f}{v['stdev']:>10.2f}"
                  f"{v['min']:>8.1f}{v['max']:>8.1f}")


def print_stats(stats):
    print("\n" + tr("stats_title", stats["games"]))
    for key, label in (("white_wins", "wins_white"), ("black_wins", "wins_black"), ("draws", "draws")):
        s = stats[key]
        print(f"{tr(label):<20}{s['count']:>5}  {s['rate'] * 100:5.1f}%  "
              f"CI95% [{s['ci95'][0] * 100:.1f}%, {s['ci95'][1] * 100:.1f}%]")
    print(tr("terminations"), stats["terminations"])
    _print_table(stats["metrics"].items())


def run_report(args):
    path = Path(args.out) / "dataset" / "games_log.csv"
    if not path.exists():
        print(tr("report_none", path))
        return
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    n = len(rows)
    count = Counter(r["winner"] for r in rows)
    print(tr("report_head", n, path))
    for key, label in (("white", "r_white"), ("black", "r_black"), ("draw", "r_draw")):
        lo, hi = wilson_interval(count[key], n)
        print(f"{tr(label):<10}{count[key]:>5} ({count[key] / n * 100:5.1f}%)  "
              f"CI95% [{lo * 100:.1f}%, {hi * 100:.1f}%]")
    print(tr("terminations"), dict(Counter(r["termination"] for r in rows)))
    keys = ("plies", "white_captures", "black_captures", "recaptures", "lead_changes", "avg_branching",
            "max_quiet_streak", "first_capture_ply", "final_material_balance", "duration_s")
    _print_table([(k, describe([r[k] for r in rows if r.get(k) not in (None, "")])) for k in keys])
    reg = Path(args.out) / "dataset" / "seen_games.txt"
    if reg.exists():
        print("\n" + tr("unique_known", len(GameRegistry(reg).seen)))


# ============================================================
# Interface gráfica — tema neon fantasmagórico
# ============================================================
def square_rect(square, flipped=False):
    col, row = chess.square_file(square), 7 - chess.square_rank(square)
    if flipped:
        col, row = 7 - col, 7 - row
    return pygame.Rect(col * SQ_SIZE, row * SQ_SIZE, SQ_SIZE, SQ_SIZE)


def square_under_pos(pos, flipped=False):
    x, y = pos
    if not (0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE):
        return None
    col, row = x // SQ_SIZE, y // SQ_SIZE
    if flipped:
        col, row = 7 - col, 7 - row
    return chess.square(col, 7 - row)


_OVERLAYS = {}


def overlay(color, alpha):
    key = (color, alpha)
    if key not in _OVERLAYS:
        s = pygame.Surface((SQ_SIZE, SQ_SIZE), pygame.SRCALPHA)
        s.fill((*color, alpha))
        _OVERLAYS[key] = s
    return _OVERLAYS[key]


class PieceRenderer:
    """Peças fantasmas: glifo translúcido com halo neon (ciano = brancas, magenta = pretas)."""
    CANDIDATES = ["segoeuisymbol", "dejavusans", "freeserif", "applesymbols", "notosanssymbols2",
                  "symbola", "arialunicodems", "menlo"]
    HALO = [(dx, dy) for dx in (-5, -3, 0, 3, 5) for dy in (-5, -3, 0, 3, 5) if dx or dy]
    EDGE = [(dx, dy) for dx in (-2, 0, 2) for dy in (-2, 0, 2) if dx or dy]
    PAD = 8

    def __init__(self, size):
        self.size, self.font, self.cache = size, None, {}
        for name in self.CANDIDATES:
            path = pygame.font.match_font(name)
            if not path:
                continue
            try:
                f = pygame.font.Font(path, size)
                if all(m is not None for m in f.metrics("♚♟")):
                    self.font = f
                    break
            except Exception:
                continue
        self.fallback = pygame.font.Font(None, int(size * 0.8))

    def surface(self, piece):
        key = (piece.color, piece.piece_type)
        if key in self.cache:
            return self.cache[key]
        white = piece.color == chess.WHITE
        fill = (215, 245, 255) if white else (30, 10, 50)
        neon = COLOR_HIGHLIGHT if white else COLOR_MAGENTA
        if self.font:
            glyph, fnt = FILLED_GLYPH[piece.piece_type], self.font
        else:
            glyph, fnt = FALLBACK_LETTER[piece.piece_type], self.fallback
        body = fnt.render(glyph, True, fill)
        edge = fnt.render(glyph, True, neon)
        halo = with_alpha(fnt.render(glyph, True, neon), 38)
        w, h = body.get_size()
        p = self.PAD
        surf = pygame.Surface((w + 2 * p, h + 2 * p), pygame.SRCALPHA)
        for dx, dy in self.HALO:
            surf.blit(halo, (p + dx, p + dy))
        for dx, dy in self.EDGE:
            surf.blit(edge, (p + dx, p + dy))
        surf.blit(body, (p, p))
        self.cache[key] = with_alpha(surf, 232)
        return self.cache[key]


def draw_board(screen, board, selected, legal_targets, last_move, flipped, coord_font):
    for sq in chess.SQUARES:
        rect = square_rect(sq, flipped)
        light = (chess.square_file(sq) + chess.square_rank(sq)) % 2 == 1
        pygame.draw.rect(screen, COLOR_LIGHT if light else COLOR_DARK, rect)
        pygame.draw.rect(screen, COLOR_GRID, rect, 1)
        if last_move and sq in (last_move.from_square, last_move.to_square):
            screen.blit(overlay(COLOR_LAST_MOVE, 85), rect.topleft)
        if selected == sq:
            screen.blit(overlay(COLOR_HIGHLIGHT, 70), rect.topleft)
        if rect.x == 0:
            screen.blit(coord_font.render(str(chess.square_rank(sq) + 1), True, COLOR_COORD), (rect.x + 3, rect.y + 2))
        if rect.y == BOARD_SIZE - SQ_SIZE:
            lab = coord_font.render("abcdefgh"[chess.square_file(sq)], True, COLOR_COORD)
            screen.blit(lab, (rect.right - lab.get_width() - 4, rect.bottom - lab.get_height() - 2))
    if selected is not None:
        glow_rect(screen, square_rect(selected, flipped), COLOR_HIGHLIGHT, 2, 6, 2)
    for sq in legal_targets:
        rect = square_rect(sq, flipped)
        if board.piece_at(sq):
            pygame.draw.circle(screen, COLOR_MAGENTA, rect.center, SQ_SIZE // 2 - 6, 3)
        else:
            glow_circle(screen, rect.center, 7, COLOR_LEGAL, 7)
    if board.is_check():
        ksq = board.king(board.turn)
        if ksq is not None:
            glow_rect(screen, square_rect(ksq, flipped), COLOR_CHECK, 3, 9, 2)


def draw_pieces(screen, board, renderer, flipped, dragged_square=None, mouse_pos=None):
    t = time.time()
    for sq, piece in board.piece_map().items():
        if sq == dragged_square:
            continue
        s = renderer.surface(piece)
        bob = int(2 * math.sin(t * 2.2 + sq * 0.9))      # flutuação fantasmagórica
        r = s.get_rect(center=square_rect(sq, flipped).center)
        screen.blit(s, (r.x, r.y + bob))
    if dragged_square is not None and mouse_pos is not None:
        piece = board.piece_at(dragged_square)
        if piece:
            s = renderer.surface(piece)
            screen.blit(s, s.get_rect(center=mouse_pos))


def promotion_rects():
    w = SQ_SIZE
    x0 = (BOARD_SIZE - 4 * w) // 2
    return {pt: pygame.Rect(x0 + i * w, BOARD_SIZE // 2 - w // 2, w, w)
            for i, pt in enumerate((chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT))}


def draw_promotion(screen, renderer, color):
    shade = pygame.Surface((BOARD_SIZE, BOARD_SIZE), pygame.SRCALPHA)
    shade.fill((4, 2, 14, 190))
    screen.blit(shade, (0, 0))
    mouse = pygame.mouse.get_pos()
    for pt, rect in promotion_rects().items():
        pygame.draw.rect(screen, COLOR_BTN_HOVER if rect.collidepoint(mouse) else COLOR_PANEL, rect, border_radius=8)
        glow_rect(screen, rect, COLOR_HIGHLIGHT if rect.collidepoint(mouse) else COLOR_BORDER, 2, 6, 8)
        s = renderer.surface(chess.Piece(pt, color))
        screen.blit(s, s.get_rect(center=rect.center))


def _fmt_captured(types):
    if not types:
        return "-"
    c = Counter(types)
    return " ".join(f"{c[pt]}{FALLBACK_LETTER[pt]}" for pt in
                    (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN) if c[pt])


def draw_menu(screen, fonts, sess, mode_idx, level_idx, hist_scroll, ui_msg, thinking, filters, auto_info):
    font_ui, font_hist = fonts
    pygame.draw.rect(screen, COLOR_MENU, (BOARD_SIZE, 0, MENU_WIDTH, HEIGHT))
    for i, c in enumerate(((22, 14, 54), (60, 34, 130), COLOR_BORDER)):      # divisória neon
        pygame.draw.line(screen, c, (BOARD_SIZE + 2 - i, 0), (BOARD_SIZE + 2 - i, HEIGHT))
    mouse = pygame.mouse.get_pos()
    is_auto = sess.mode_key == "auto"

    labels = {"mode": tr("mode_label", tr(f"mode_{mode_idx}")),
              "level": tr("level_shuffled") if is_auto else tr("level_label", tr(f"level_{level_idx}")),
              "undo": tr("undo"), "restart": tr("restart"), "flip": tr("flip"), "export": tr("export")}
    for key, rect in BUTTONS.items():
        hover = rect.collidepoint(mouse)
        pygame.draw.rect(screen, COLOR_BTN_HOVER if hover else COLOR_BTN, rect, border_radius=6)
        glow_rect(screen, rect, COLOR_HIGHLIGHT if hover else COLOR_BORDER, 2, 5 if hover else 3, 6)
        if key == "lang":
            for i, code in enumerate(("PT", "EN")):
                active = code.lower() == LANG
                t = font_ui.render(code, True, COLOR_HIGHLIGHT if active else COLOR_MUTED)
                screen.blit(t, t.get_rect(center=(rect.x + 22 + i * 36, rect.centery)))
            pygame.draw.line(screen, COLOR_BORDER, (rect.centerx, rect.y + 8), (rect.centerx, rect.bottom - 8))
            continue
        color = COLOR_MUTED if (key == "level" and is_auto) else COLOR_TEXT
        txt = font_ui.render(fit_text(font_ui, labels[key], rect.w - 16), True, color)
        if key in ("undo", "restart", "flip"):
            screen.blit(txt, txt.get_rect(center=rect.center))
        else:
            screen.blit(txt, (rect.x + 10, rect.centery - txt.get_height() // 2))

    # Painel de status
    board = sess.board
    panel = pygame.Rect(BOARD_SIZE + 20, 128, MENU_WIDTH - 40, 80)
    pygame.draw.rect(screen, COLOR_PANEL, panel, border_radius=6)
    pygame.draw.rect(screen, COLOR_BORDER, panel, 1, border_radius=6)
    if sess.is_over():
        _, term, winner = sess.result_info()
        who = tr({"white": "win_white", "black": "win_black", "draw": "win_draw", "": "win_none"}[winner])
        line1, c1 = f"{tr('term_' + term)} - {who}", COLOR_HIGHLIGHT
    else:
        line1 = tr("turn_white") if board.turn == chess.WHITE else tr("turn_black")
        if board.is_check():
            line1 += "  " + tr("check")
        if thinking:
            line1 += "  " + tr("thinking") + "." * (int(time.time() * 3) % 4)
        c1 = COLOR_CHECK if board.is_check() else COLOR_TEXT
    if auto_info and auto_info["paused"]:
        line1 += "  [" + tr("paused") + "]"
    bal = material(board, chess.WHITE) - material(board, chess.BLACK)
    if is_auto and auto_info:
        lines = [(line1, c1),
                 (tr("auto_status", auto_info["n"], auto_info["unique"], len(board.move_stack)), COLOR_HIGHLIGHT),
                 (tr("auto_params", sess.levels[chess.WHITE], sess.levels[chess.BLACK], sess.epsilon), COLOR_MUTED),
                 (tr("status_move", len(board.move_stack), bal), COLOR_MUTED)]
    else:
        cap_w = [v for c, v in sess.cap_log if c == chess.WHITE and v]
        cap_b = [v for c, v in sess.cap_log if c == chess.BLACK and v]
        lines = [(line1, c1), (tr("status_move", len(board.move_stack), bal), COLOR_TEXT),
                 (tr("cap_w", _fmt_captured(cap_w)), COLOR_MUTED), (tr("cap_b", _fmt_captured(cap_b)), COLOR_MUTED)]
    for i, (t, c) in enumerate(lines):
        f = font_ui if i == 0 else font_hist
        screen.blit(f.render(fit_text(f, t, panel.w - 16), True, c), (panel.x + 8, panel.y + 6 + i * 18))

    # Filtros de exportação
    screen.blit(font_ui.render(tr("filters"), True, COLOR_HIGHLIGHT), (BOARD_SIZE + 20, 214))
    for cb in CHECKBOXES:
        rect = pygame.Rect(cb["x"], cb["y"], 18, 18)
        pygame.draw.rect(screen, COLOR_BORDER, rect, 2, border_radius=3)
        if filters[cb["key"]]:
            glow_rect(screen, pygame.Rect(cb["x"] + 4, cb["y"] + 4, 10, 10), COLOR_HIGHLIGHT, 0, 4, 2)
            pygame.draw.rect(screen, COLOR_HIGHLIGHT, pygame.Rect(cb["x"] + 4, cb["y"] + 4, 10, 10))
        screen.blit(font_hist.render(tr("f_" + cb["key"]), True, COLOR_TEXT), (cb["x"] + 25, cb["y"]))

    if ui_msg[2] > 0:
        screen.blit(font_hist.render(fit_text(font_hist, ui_msg[0], MENU_WIDTH - 40), True, ui_msg[1]),
                    (BOARD_SIZE + 20, 382))

    # Histórico em pares, rolável com a roda do mouse
    screen.blit(font_ui.render(tr("history"), True, COLOR_HIGHLIGHT), (BOARD_SIZE + 20, 402))
    san = sess.san
    pairs = [(san[i], san[i + 1] if i + 1 < len(san) else "") for i in range(0, len(san), 2)]
    visible = 8
    start = max(0, len(pairs) - visible - hist_scroll)
    for r, (w_, b_) in enumerate(pairs[start:start + visible]):
        y = 426 + r * 25
        screen.blit(font_hist.render(f"{start + r + 1}.", True, COLOR_MUTED), (BOARD_SIZE + 20, y))
        screen.blit(font_hist.render(w_, True, COLOR_HIGHLIGHT), (BOARD_SIZE + 62, y))
        screen.blit(font_hist.render(b_, True, COLOR_MAGENTA), (BOARD_SIZE + 180, y))


def draw_game_over(screen, sess, font, font_small, next_in=None):
    result, term, winner = sess.result_info()
    who = tr({"white": "win_white", "black": "win_black", "draw": "win_draw", "": "win_none"}[winner])
    band = pygame.Surface((BOARD_SIZE, 92), pygame.SRCALPHA)
    band.fill((4, 2, 14, 205))
    y0 = BOARD_SIZE // 2 - 46
    screen.blit(band, (0, y0))
    pygame.draw.line(screen, COLOR_BORDER, (0, y0), (BOARD_SIZE, y0), 2)
    pygame.draw.line(screen, COLOR_BORDER, (0, y0 + 92), (BOARD_SIZE, y0 + 92), 2)
    t = font.render(f"{who}  ({result})", True, COLOR_TEXT)
    screen.blit(t, t.get_rect(center=(BOARD_SIZE // 2, y0 + 24)))
    t2 = font.render(tr("term_" + term), True, COLOR_HIGHLIGHT)
    screen.blit(t2, t2.get_rect(center=(BOARD_SIZE // 2, y0 + 54)))
    if next_in is not None:
        t3 = font_small.render(tr("auto_next", next_in), True, COLOR_MUTED)
        screen.blit(t3, t3.get_rect(center=(BOARD_SIZE // 2, y0 + 78)))


def run_gui(args):
    pygame.init()
    out_root = Path(args.out)
    set_lang(args.lang or load_settings(out_root).get("lang", "pt"))
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(tr("caption"))
    clock = pygame.time.Clock()

    renderer = PieceRenderer(int(SQ_SIZE * 0.78))
    font_ui = pygame.font.SysFont("arial", 17, bold=True)
    font_hist = pygame.font.SysFont("arial", 15)
    font_big = pygame.font.SysFont("arial", 26, bold=True)
    font_coord = pygame.font.SysFont("arial", 13, bold=True)

    filters = {k: True for k in FILTER_KEYS}
    registry = GameRegistry(out_root / "dataset" / "seen_games.txt")
    mode_idx, level_idx, flipped = 0, 2, False
    sess = GameSession(MODE_KEYS[mode_idx], {chess.WHITE: level_idx, chess.BLACK: level_idx}, args.seed)
    worker = EngineWorker()
    selected, dragging, legal_targets, promo_pending = None, False, [], None
    hist_scroll, mouse_pos, ui_msg = 0, (0, 0), ["", COLOR_TEXT, 0]
    pc_ready_at = time.monotonic() + PC_DELAY_S
    auto_count, auto_paused, next_game_at, registered_id = 0, False, 0.0, None

    def say(text, color=COLOR_HIGHLIGHT, frames=240):
        ui_msg[:] = [text, color, frames]

    def clear_selection():
        nonlocal selected, dragging, legal_targets, promo_pending
        selected, dragging, legal_targets, promo_pending = None, False, [], None

    def is_auto():
        return sess.mode_key == "auto"

    def human_turn():
        k = sess.mode_key
        return k == "both" or (k == "white" and sess.board.turn == chess.WHITE) or \
            (k == "black" and sess.board.turn == chess.BLACK)

    def apply_human_move(move):
        nonlocal pc_ready_at, hist_scroll
        if move in sess.board.legal_moves:
            sess.push(move, "humano")
            pc_ready_at = time.monotonic() + PC_DELAY_S
            hist_scroll = 0

    def try_move(frm, to):
        nonlocal promo_pending
        cands = [m for m in sess.board.legal_moves if m.from_square == frm and m.to_square == to]
        if not cands:
            return
        if len(cands) > 1:  # promoção: pede escolha da peça
            promo_pending = (frm, to)
            return
        apply_human_move(cands[0])

    def new_game():
        nonlocal pc_ready_at
        worker.cancel()
        sess.mode_key = MODE_KEYS[mode_idx]
        sess.reset()
        if is_auto():
            randomize_session(sess)           # semente, níveis e ruído novos a cada partida
        else:
            sess.levels = {chess.WHITE: level_idx, chess.BLACK: level_idx}
            sess.epsilon, sess.random_mode = 0.0, False
        clear_selection()
        pc_ready_at = time.monotonic() + PC_DELAY_S

    def undo():
        worker.cancel()
        clear_selection()
        if is_auto() or not sess.board.move_stack:
            return
        sess.undo_count += 1
        sess.pop()
        if sess.mode_key in ("white", "black"):
            hc = chess.WHITE if sess.mode_key == "white" else chess.BLACK
            while sess.board.move_stack and sess.board.turn != hc:
                sess.pop()

    def do_export():
        try:
            res = export_game(sess, out_root, filters, folder=True, aggregate=not sess.aggregated)
            say(tr("saved", res["folder"].name))
        except Exception as e:
            traceback.print_exc()
            say(tr("export_err", e), COLOR_ERROR, 360)

    def finalize_auto():
        """Fim de partida no auto-jogo: grava no dataset e registra o hash para nunca repetir."""
        nonlocal auto_count, next_game_at, registered_id
        try:
            if not sess.aggregated:
                export_game(sess, out_root, filters, folder=False, aggregate=True, images=False)
        except Exception as e:
            traceback.print_exc()
            say(tr("export_err", e), COLOR_ERROR, 360)
        registry.add(sess.board)
        registered_id = sess.game_id
        auto_count += 1
        next_game_at = time.monotonic() + AUTO_NEXT_DELAY_S

    def toggle_lang():
        set_lang("en" if LANG == "pt" else "pt")
        save_settings(out_root, {"lang": LANG})
        pygame.display.set_caption(tr("caption"))

    def change_mode():
        nonlocal mode_idx, pc_ready_at
        was_auto = is_auto()
        mode_idx = (mode_idx + 1) % len(MODE_KEYS)
        if was_auto or MODE_KEYS[mode_idx] == "auto":
            new_game()                        # entrar/sair do auto-jogo sempre começa partida nova
        else:
            worker.cancel()
            sess.mode_key = MODE_KEYS[mode_idx]
            clear_selection()
            pc_ready_at = time.monotonic() + PC_DELAY_S

    running = True
    while running:
        now = time.monotonic()
        thinking = worker.busy

        # ---- fluxo do PC / auto-jogo ----
        if is_auto() and not sess.is_over() and len(sess.board.move_stack) >= AUTO_MAX_PLIES:
            sess.forced_termination = "max_plies"
        if is_auto() and sess.is_over():
            if sess.game_id != registered_id:
                finalize_auto()
            elif not auto_paused and now >= next_game_at:
                new_game()
        elif not sess.is_over() and not human_turn() and not worker.busy and now >= pc_ready_at \
                and not (is_auto() and auto_paused):
            forb = registry.forbidden(sess.board) if is_auto() else set()
            worker.start(sess.board, sess.levels[sess.board.turn], sess.seed, forb, sess.epsilon)
        mv = worker.poll()
        if mv is not None and len(sess.board.move_stack) == worker.start_ply and mv in sess.board.legal_moves \
                and not sess.is_over() and not human_turn():
            sess.push(mv, "pc")
            pc_ready_at = time.monotonic() + PC_DELAY_S
            hist_scroll = 0

        # ---- eventos ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    clear_selection()
                elif event.key == pygame.K_u:
                    undo()
                elif event.key == pygame.K_r:
                    new_game()
                elif event.key == pygame.K_f:
                    flipped = not flipped
                elif event.key == pygame.K_e:
                    do_export()
                elif event.key == pygame.K_l:
                    toggle_lang()
                elif event.key == pygame.K_p:
                    auto_paused = not auto_paused
            elif event.type == pygame.MOUSEWHEEL:
                if mouse_pos[0] >= BOARD_SIZE:
                    hist_scroll = max(0, min(max(0, (len(sess.san) + 1) // 2 - 8), hist_scroll + event.y))
            elif event.type == pygame.MOUSEMOTION:
                mouse_pos = event.pos
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if promo_pending:
                    for pt, rect in promotion_rects().items():
                        if rect.collidepoint(pos):
                            frm, to = promo_pending
                            promo_pending = None
                            apply_human_move(chess.Move(frm, to, promotion=pt))
                            clear_selection()
                            break
                    else:
                        clear_selection()
                elif pos[0] >= BOARD_SIZE:
                    if BUTTONS["mode"].collidepoint(pos):
                        change_mode()
                    elif BUTTONS["level"].collidepoint(pos):
                        if not is_auto():
                            level_idx = (level_idx + 1) % N_LEVELS
                            worker.cancel()
                            sess.levels = {chess.WHITE: level_idx, chess.BLACK: level_idx}
                    elif BUTTONS["lang"].collidepoint(pos):
                        toggle_lang()
                    elif BUTTONS["undo"].collidepoint(pos):
                        undo()
                    elif BUTTONS["restart"].collidepoint(pos):
                        new_game()
                    elif BUTTONS["flip"].collidepoint(pos):
                        flipped = not flipped
                    elif BUTTONS["export"].collidepoint(pos):
                        do_export()
                    for cb in CHECKBOXES:
                        if pygame.Rect(cb["x"], cb["y"], 130, 22).collidepoint(pos):
                            filters[cb["key"]] = not filters[cb["key"]]
                elif human_turn() and not sess.is_over():
                    sq = square_under_pos(pos, flipped)
                    if sq is None:
                        clear_selection()
                    elif selected is not None and sq in legal_targets:
                        frm = selected
                        clear_selection()
                        try_move(frm, sq)
                    else:
                        piece = sess.board.piece_at(sq)
                        if piece and piece.color == sess.board.turn:
                            selected, dragging = sq, True
                            legal_targets = [m.to_square for m in sess.board.legal_moves if m.from_square == sq]
                        else:
                            clear_selection()
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and dragging:
                dragging = False
                drop = square_under_pos(event.pos, flipped)
                if selected is not None and drop is not None and drop != selected and drop in legal_targets:
                    frm = selected
                    legal_targets = []
                    selected = None
                    try_move(frm, drop)
                elif drop != selected:
                    clear_selection()   # soltou fora: cancela; soltar na origem mantém seleção (clique-clique)

        if ui_msg[2] > 0:
            ui_msg[2] -= 1

        # ---- desenho ----
        screen.fill(COLOR_VOID)
        draw_board(screen, sess.board, selected, legal_targets, sess.last_move, flipped, font_coord)
        draw_pieces(screen, sess.board, renderer, flipped, selected if dragging else None, mouse_pos)
        auto_info = None
        next_in = None
        if is_auto():
            auto_info = {"n": auto_count + (0 if sess.game_id == registered_id else 1),
                         "unique": len(registry.seen), "paused": auto_paused}
            if sess.is_over() and sess.game_id == registered_id and not auto_paused:
                next_in = max(0, math.ceil(next_game_at - now))
        if promo_pending:
            draw_promotion(screen, renderer, sess.board.turn)
        elif sess.is_over():
            draw_game_over(screen, sess, font_big, font_hist, next_in)
        draw_menu(screen, (font_ui, font_hist), sess, mode_idx, level_idx, hist_scroll, ui_msg, thinking,
                  filters, auto_info)
        pygame.display.flip()
        clock.tick(FPS)

    worker.cancel()
    pygame.quit()


# ============================================================
# Entrada
# ============================================================
def parse_args():
    ap = argparse.ArgumentParser(description="Simulador de Xadrez — Análise e Rastros / Chess Simulator")
    ap.add_argument("--out", default="exports", help="pasta de saída / output folder (padrão: ./exports)")
    ap.add_argument("--lang", choices=("pt", "en"), default=None, help="idioma / language (pt|en)")
    ap.add_argument("--seed", type=int, default=None, help="semente para reprodutibilidade / seed")
    ap.add_argument("--batch", type=int, default=0, help="roda N partidas PC vs PC sem interface / headless games")
    ap.add_argument("--random", action="store_true",
                    help="batch: auto-jogo aleatório com partidas únicas (nunca repete) / unique random self-play")
    ap.add_argument("--white-level", type=int, default=1, choices=range(4), help="nível das brancas 0-3 / white level")
    ap.add_argument("--black-level", type=int, default=1, choices=range(4), help="nível das pretas 0-3 / black level")
    ap.add_argument("--move-time", type=float, default=1.0, help="limite (s) por lance no batch / time per move")
    ap.add_argument("--max-plies", type=int, default=400, help="limite de lances por partida no batch")
    ap.add_argument("--full", action="store_true", help="batch: pasta completa (CSV/JSON/PNG) por partida")
    ap.add_argument("--report", action="store_true", help="resume dataset/games_log.csv / summarize the dataset")
    return ap.parse_args()


def main():
    args = parse_args()
    if args.lang:
        set_lang(args.lang)
    else:
        set_lang(load_settings(args.out).get("lang", "pt"))
    if args.report:
        run_report(args)
    elif args.batch > 0:
        run_batch(args)
    else:
        run_gui(args)


if __name__ == "__main__":
    main()
    sys.exit(0)
