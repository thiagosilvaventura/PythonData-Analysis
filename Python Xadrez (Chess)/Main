import sys
import os
import json
import datetime
import pygame
import chess
import random

# ============================================================
# Simulador de Xadrez — Análise e Rastros
# Dependências: pip install pygame chess
# ============================================================

# Configurações da Janela (Aumentado para caber o novo menu)
BOARD_SIZE = 640
MENU_WIDTH = 340
WIDTH = BOARD_SIZE + MENU_WIDTH
HEIGHT = BOARD_SIZE
SQ_SIZE = BOARD_SIZE // 8
FPS = 60

# Cores
COLOR_LIGHT = (240, 217, 181)
COLOR_DARK = (181, 136, 99)
COLOR_HIGHLIGHT = (186, 202, 68)
COLOR_LAST_MOVE = (210, 190, 80)
COLOR_MENU = (45, 45, 45)
COLOR_BTN = (80, 80, 80)
COLOR_BTN_HOVER = (112, 112, 112)
COLOR_TEXT = (235, 235, 235)
COLOR_LEGAL = (70, 130, 80)
COLOR_CHECK = (190, 65, 65)

PIECE_TEXT = {
    'P': '♙', 'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔',
    'p': '♟', 'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚'
}

CONTROL_MODES = ["Brancas (vs PC)", "Pretas (vs PC)", "Ambos os lados"]
MODE_KEYS = {"Brancas (vs PC)": "white", "Pretas (vs PC)": "black", "Ambos os lados": "both"}

# Filtros de Exportação Iniciais
export_filters = {
    "brancas": True, "pretas": True,
    "peões": True, "cavalos": True, "bispos": True,
    "torres": True, "rainhas": True, "reis": True
}

CHECKBOXES = [
    {"key": "brancas", "label": "Brancas (Verde)", "x": BOARD_SIZE + 20, "y": 210},
    {"key": "pretas",  "label": "Pretas (Vermelho)", "x": BOARD_SIZE + 180, "y": 210},
    {"key": "peões",   "label": "Peões",           "x": BOARD_SIZE + 20, "y": 250},
    {"key": "cavalos", "label": "Cavalos",         "x": BOARD_SIZE + 180, "y": 250},
    {"key": "bispos",  "label": "Bispos",          "x": BOARD_SIZE + 20, "y": 290},
    {"key": "torres",  "label": "Torres",          "x": BOARD_SIZE + 180, "y": 290},
    {"key": "rainhas", "label": "Rainhas",         "x": BOARD_SIZE + 20, "y": 330},
    {"key": "reis",    "label": "Reis",            "x": BOARD_SIZE + 180, "y": 330},
]

# ============================================================
# Lógica de Rastreamento
# ============================================================
class PieceTracker:
    """Rastreia o movimento de cada peça individualmente recriando a partida."""
    def __init__(self):
        self.pieces = {}
        self.sq_to_id = {}
        temp_board = chess.Board()
        
        # Inicializa o rastreio baseando-se na casa de origem
        for sq in chess.SQUARES:
            p = temp_board.piece_at(sq)
            if p:
                self.pieces[sq] = {
                    'id': sq,
                    'color': p.color,
                    'type': p.piece_type,
                    'path': [sq],
                    'captured_at': None
                }
                self.sq_to_id[sq] = sq
                
    def track_move(self, board_before, move):
        from_sq = move.from_square
        to_sq = move.to_square
        
        # Identifica casa de captura (Lida com En-Passant)
        captured_sq = to_sq
        if board_before.is_en_passant(move):
            captured_sq = to_sq - 8 if board_before.turn == chess.WHITE else to_sq + 8
            
        # Registra captura
        if captured_sq in self.sq_to_id and self.sq_to_id[captured_sq] != self.sq_to_id.get(from_sq):
            cap_id = self.sq_to_id[captured_sq]
            self.pieces[cap_id]['captured_at'] = captured_sq # Registra onde a peça morreu
            del self.sq_to_id[captured_sq]
            
        # Tratamento especial para o movimento da Torre no Roque
        if board_before.is_castling(move):
            if to_sq == chess.G1: r_from, r_to = chess.H1, chess.F1
            elif to_sq == chess.C1: r_from, r_to = chess.A1, chess.D1
            elif to_sq == chess.G8: r_from, r_to = chess.H8, chess.F8
            elif to_sq == chess.C8: r_from, r_to = chess.A8, chess.D8
            else: r_from, r_to = None, None
            
            if r_from and r_from in self.sq_to_id:
                rid = self.sq_to_id.pop(r_from)
                self.pieces[rid]['path'].append(r_to)
                self.sq_to_id[r_to] = rid

        # Move a peça principal
        if from_sq in self.sq_to_id:
            pid = self.sq_to_id.pop(from_sq)
            self.pieces[pid]['path'].append(to_sq)
            self.sq_to_id[to_sq] = pid

def export_data(board):
    """Reconstrói a partida, filtra e exporta os dados selecionados."""
    # 1. Recria as trajetórias a partir da lista de movimentos atual
    tracker = PieceTracker()
    temp_board = chess.Board()
    for m in board.move_stack:
        tracker.track_move(temp_board, m)
        temp_board.push(m)
        
    # 2. Filtra os dados com base nos checkboxes
    filtered_pieces = []
    type_map = {
        chess.PAWN: 'peões', chess.KNIGHT: 'cavalos',
        chess.BISHOP: 'bispos', chess.ROOK: 'torres',
        chess.QUEEN: 'rainhas', chess.KING: 'reis'
    }
    
    for p in tracker.pieces.values():
        c_ok = (p['color'] == chess.WHITE and export_filters['brancas']) or \
               (p['color'] == chess.BLACK and export_filters['pretas'])
        t_ok = export_filters[type_map[p['type']]]
        
        if c_ok and t_ok:
            filtered_pieces.append(p)
            
    # 3. Exporta JSON
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"rastros_{timestamp}.json"
    img_filename = f"rastros_{timestamp}.png"
    
    json_data = []
    for p in filtered_pieces:
        json_data.append({
            "start_square": chess.square_name(p['id']),
            "color": "white" if p['color'] == chess.WHITE else "black",
            "type": chess.piece_name(p['type']),
            "path": [chess.square_name(sq) for sq in p['path']],
            "captured_at": chess.square_name(p['captured_at']) if p['captured_at'] is not None else None
        })
        
    with open(json_filename, "w") as f:
        json.dump(json_data, f, indent=4)
        
    # 4. Desenha Imagem PNG
    surf = pygame.Surface((BOARD_SIZE, BOARD_SIZE))
    for row in range(8):
        for col in range(8):
            color = COLOR_LIGHT if (row + col) % 2 == 0 else COLOR_DARK
            pygame.draw.rect(surf, color, pygame.Rect(col * SQ_SIZE, row * SQ_SIZE, SQ_SIZE, SQ_SIZE))
            
    for p in filtered_pieces:
        if len(p['path']) < 2: 
            continue # Ignora peças que nunca se moveram no desenho
            
        color = (40, 220, 40) if p['color'] == chess.WHITE else (220, 40, 40)
        pts = []
        for sq in p['path']:
            cx = chess.square_file(sq) * SQ_SIZE + SQ_SIZE // 2
            cy = (7 - chess.square_rank(sq)) * SQ_SIZE + SQ_SIZE // 2
            pts.append((cx, cy))
            
        pygame.draw.lines(surf, color, False, pts, 4)
        
        # Desenha o 'X' na casa de captura
        if p['captured_at'] is not None:
            cx = chess.square_file(p['captured_at']) * SQ_SIZE + SQ_SIZE // 2
            cy = (7 - chess.square_rank(p['captured_at'])) * SQ_SIZE + SQ_SIZE // 2
            offset = 12
            pygame.draw.line(surf, color, (cx - offset, cy - offset), (cx + offset, cy + offset), 6)
            pygame.draw.line(surf, color, (cx + offset, cy - offset), (cx - offset, cy + offset), 6)
            
    pygame.image.save(surf, img_filename)

# ============================================================
# Lógica de Interface e Jogo
# ============================================================
def square_rect(square):
    col = chess.square_file(square)
    row = 7 - chess.square_rank(square)
    return pygame.Rect(col * SQ_SIZE, row * SQ_SIZE, SQ_SIZE, SQ_SIZE)

def square_under_pos(pos):
    x, y = pos
    if not (0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE): return None
    return chess.square(x // SQ_SIZE, 7 - (y // SQ_SIZE))

def draw_board(screen, board, selected, legal_targets, last_move):
    for row in range(8):
        for col in range(8):
            sq = chess.square(col, 7 - row)
            color = COLOR_LIGHT if (row + col) % 2 == 0 else COLOR_DARK
            rect = pygame.Rect(col * SQ_SIZE, row * SQ_SIZE, SQ_SIZE, SQ_SIZE)
            pygame.draw.rect(screen, color, rect)
            
            if last_move and sq in (last_move.from_square, last_move.to_square):
                overlay = pygame.Surface((SQ_SIZE, SQ_SIZE), pygame.SRCALPHA)
                overlay.fill((*COLOR_LAST_MOVE, 95))
                screen.blit(overlay, rect.topleft)
            
            if selected == sq:
                pygame.draw.rect(screen, COLOR_HIGHLIGHT, rect)
            
            if sq in legal_targets:
                cx, cy = rect.center
                if board.piece_at(sq):
                    pygame.draw.circle(screen, COLOR_LEGAL, (cx, cy), SQ_SIZE // 2 - 5, 5)
                else:
                    pygame.draw.circle(screen, COLOR_LEGAL, (cx, cy), 9)

    if board.is_check():
        king_sq = board.king(board.turn)
        if king_sq is not None:
            pygame.draw.rect(screen, COLOR_CHECK, square_rect(king_sq), 5)

def draw_pieces(screen, board, font, dragged_square=None, mouse_pos=None):
    for square in chess.SQUARES:
        if square == dragged_square: continue
        piece = board.piece_at(square)
        if not piece: continue
        
        symbol = PIECE_TEXT[piece.symbol()]
        color = (255, 255, 255) if piece.color == chess.WHITE else (15, 15, 15)
        surface = font.render(symbol, True, color)
        screen.blit(surface, surface.get_rect(center=square_rect(square).center))

    if dragged_square is not None and mouse_pos is not None:
        piece = board.piece_at(dragged_square)
        if piece:
            symbol = PIECE_TEXT[piece.symbol()]
            color = (255, 255, 255) if piece.color == chess.WHITE else (15, 15, 15)
            surface = font.render(symbol, True, color)
            screen.blit(surface, surface.get_rect(center=mouse_pos))

def draw_menu(screen, font_ui, font_hist, mode_idx, move_history, export_msg_timer):
    pygame.draw.rect(screen, COLOR_MENU, (BOARD_SIZE, 0, MENU_WIDTH, HEIGHT))
    mouse_pos = pygame.mouse.get_pos()
    
    btn_mode = pygame.Rect(BOARD_SIZE + 20, 20, MENU_WIDTH - 40, 40)
    btn_undo = pygame.Rect(BOARD_SIZE + 20, 70, MENU_WIDTH - 40, 40)
    btn_restart = pygame.Rect(BOARD_SIZE + 20, 120, MENU_WIDTH - 40, 40)
    btn_export = pygame.Rect(BOARD_SIZE + 20, 370, MENU_WIDTH - 40, 40)
    
    buttons = {'mode': btn_mode, 'undo': btn_undo, 'restart': btn_restart, 'export': btn_export}
    
    for key, btn in buttons.items():
        color = COLOR_BTN_HOVER if btn.collidepoint(mouse_pos) else COLOR_BTN
        pygame.draw.rect(screen, color, btn, border_radius=5)
    
    screen.blit(font_ui.render(f"Modo: {CONTROL_MODES[mode_idx]}", True, COLOR_TEXT), (btn_mode.x + 10, btn_mode.y + 10))
    screen.blit(font_ui.render("Desfazer Jogada", True, COLOR_TEXT), (btn_undo.x + 10, btn_undo.y + 10))
    screen.blit(font_ui.render("Reiniciar Partida", True, COLOR_TEXT), (btn_restart.x + 10, btn_restart.y + 10))
    screen.blit(font_ui.render("Exportar Rastros (JSON/PNG)", True, COLOR_TEXT), (btn_export.x + 10, btn_export.y + 10))
    
    # Desenha Checkboxes de Filtro
    screen.blit(font_ui.render("Filtros de Exportação:", True, COLOR_TEXT), (BOARD_SIZE + 20, 180))
    for cb in CHECKBOXES:
        rect = pygame.Rect(cb['x'], cb['y'], 18, 18)
        pygame.draw.rect(screen, COLOR_TEXT, rect, 2)
        if export_filters[cb['key']]:
            pygame.draw.rect(screen, COLOR_HIGHLIGHT, pygame.Rect(cb['x']+4, cb['y']+4, 10, 10))
        screen.blit(font_hist.render(cb['label'], True, COLOR_TEXT), (cb['x'] + 25, cb['y']))

    # Desenha Mensagem de Sucesso
    if export_msg_timer > 0:
        msg = font_hist.render("Exportado com sucesso!", True, COLOR_HIGHLIGHT)
        screen.blit(msg, (BOARD_SIZE + 20, 420))

    # Histórico de jogadas
    screen.blit(font_ui.render("Histórico:", True, COLOR_TEXT), (BOARD_SIZE + 20, 450))
    y_offset = 480
    start_idx = max(0, len(move_history) - 6) # Mostra as últimas 6
    for i, move_str in enumerate(move_history[start_idx:]):
        screen.blit(font_hist.render(f"{start_idx + i + 1}. {move_str}", True, COLOR_TEXT), (BOARD_SIZE + 20, y_offset))
        y_offset += 25

    return buttons

def computer_move(board):
    legal_moves = list(board.legal_moves)
    return random.choice(legal_moves) if legal_moves else None

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Simulador de Xadrez Avançado")
    clock = pygame.time.Clock()
    
    try: font_pieces = pygame.font.SysFont("segoeuisymbol", 64)
    except: font_pieces = pygame.font.Font(None, 72)
    font_ui = pygame.font.SysFont("arial", 18, bold=True)
    font_hist = pygame.font.SysFont("arial", 16)

    board = chess.Board()
    mode_idx = 0
    dragged_square = None
    legal_targets = []
    last_move = None
    move_history_san = []
    mouse_pos = (0, 0)
    export_msg_timer = 0
    
    running = True
    while running:
        game_over = board.is_game_over()
        current_mode = MODE_KEYS[CONTROL_MODES[mode_idx]]
        
        is_human_turn = (current_mode == "both") or \
                        (current_mode == "white" and board.turn == chess.WHITE) or \
                        (current_mode == "black" and board.turn == chess.BLACK)

        if not is_human_turn and not game_over:
            pygame.time.wait(300)
            move = computer_move(board)
            if move:
                move_history_san.append(board.san(move))
                board.push(move)
                last_move = move

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEMOTION:
                mouse_pos = event.pos
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Cliques no Menu
                if event.pos[0] >= BOARD_SIZE:
                    buttons = draw_menu(screen, font_ui, font_hist, mode_idx, move_history_san, 0)
                    
                    if buttons['mode'].collidepoint(event.pos): mode_idx = (mode_idx + 1) % len(CONTROL_MODES)
                    elif buttons['restart'].collidepoint(event.pos):
                        board.reset()
                        move_history_san.clear()
                        last_move = dragged_square = None
                    elif buttons['export'].collidepoint(event.pos):
                        export_data(board)
                        export_msg_timer = 120 # Mostra mensagem por 2 segundos
                    elif buttons['undo'].collidepoint(event.pos):
                        if len(board.move_stack) > 0:
                            pop_count = 2 if current_mode != "both" and len(board.move_stack) >= 2 else 1
                            for _ in range(pop_count):
                                board.pop()
                                move_history_san.pop()
                                last_move = board.peek() if board.move_stack else None
                                
                    # Cliques nos Checkboxes
                    for cb in CHECKBOXES:
                        click_rect = pygame.Rect(cb['x'], cb['y'], 130, 25)
                        if click_rect.collidepoint(event.pos):
                            export_filters[cb['key']] = not export_filters[cb['key']]
                
                # Cliques no Tabuleiro (Arrastar peça)
                elif is_human_turn and not game_over:
                    sq = square_under_pos(event.pos)
                    if sq is not None:
                        piece = board.piece_at(sq)
                        if piece and piece.color == board.turn:
                            dragged_square = sq
                            legal_targets = [m.to_square for m in board.legal_moves if m.from_square == sq]

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if dragged_square is not None:
                    drop_sq = square_under_pos(event.pos)
                    if drop_sq is not None and drop_sq in legal_targets:
                        move = chess.Move(dragged_square, drop_sq)
                        if board.piece_at(dragged_square).piece_type == chess.PAWN and chess.square_rank(drop_sq) in [0, 7]:
                            move = chess.Move(dragged_square, drop_sq, promotion=chess.QUEEN)
                        
                        if move in board.legal_moves:
                            move_history_san.append(board.san(move))
                            board.push(move)
                            last_move = move
                    dragged_square = None
                    legal_targets = []

        if export_msg_timer > 0:
            export_msg_timer -= 1

        draw_board(screen, board, dragged_square, legal_targets, last_move)
        draw_pieces(screen, board, font_pieces, dragged_square, mouse_pos)
        draw_menu(screen, font_ui, font_hist, mode_idx, move_history_san, export_msg_timer)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
