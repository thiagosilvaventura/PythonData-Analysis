# Simulador de Xadrez e Mapeamento de Trajetórias

Neste repositório, apresento o código referente a um simulador de xadrez que desenvolvi com foco primário no rastreamento e na exportação das trajetórias das peças. Eu construí esta aplicação com o intuito de viabilizar a análise espacial de partidas, permitindo que os dados de movimentação sejam extraídos e visualizados graficamente após o término de um jogo.

O software foi programado em Python e eu utilizei duas bibliotecas principais para a sua estruturação: o `pygame` para a renderização da interface gráfica e o `python-chess` (importado como `chess`) para o controlo do estado do tabuleiro e a validação estrita das regras do jogo.

## Estrutura da Interface Gráfica e Controles

<img width="1036" height="709" alt="image" src="https://github.com/user-attachments/assets/ed8988f7-a0b9-49e2-b9ba-950fcba5acaf" />
Interface inicial da aplicação


Eu concebi a interface dividindo o ecrã em duas secções principais. À esquerda, renderizo o tabuleiro em formato tradicional. À direita, estruturei um menu de controlo numa paleta de cores escuras para concentrar os comandos de operação e análise.

No painel de controle, eu implementei os seguintes botões e funções:

* **Modo**: Permite alternar o controlo dos lados da partida. Eu configurei três estados possíveis: controlo exclusivo das peças brancas contra o computador, controlo exclusivo das pretas contra o computador, e o modo onde ambos os lados são controlados pelo utilizador no mesmo terminal. As respostas do computador são geradas por meio de escolhas pseudoaleatórias entre os movimentos legais disponíveis.
* **Desfazer Jogada**: Reverte o último movimento no tabuleiro. Se o utilizador estiver a jogar contra o computador, eu programei este botão para remover duas jogadas da pilha, garantindo que o turno retorne ao jogador humano.
* **Reiniciar Partida**: Restaura o tabuleiro à posição inicial padrão e limpa o histórico de movimentos.
* **Exportar Rastros (JSON/PNG)**: Aciona o algoritmo de varredura e reconstrução da partida, gerando os ficheiros de saída com os dados mapeados.
* **Filtros de Exportação**: Um conjunto de caixas de seleção que eu incluí para refinar os dados exportados. É possível selecionar a cor das peças (Brancas ou Pretas) e o tipo de peça (Peões, Cavalos, Bispos, Torres, Rainhas e Reis).



<img width="1036" height="713" alt="image" src="https://github.com/user-attachments/assets/fd16bb83-6ff8-4f69-bcad-7f8c13cdde8d" />
As casas disponiveis para cada tipo de peça foram herdadas nas regras da biblioteca utilizada



## Metodologia de Rastreamento de Peças

A biblioteca `python-chess` não rastreia o ciclo de vida individual das peças; ela foca apenas no estado global do tabuleiro num dado turno. Para resolver esse problema analítico, eu elaborei a classe `PieceTracker`. O objetivo desta classe é recriar a partida internamente, passo a passo, registrando a trajetória (caminho) de cada unidade específica.

Para alcançar isso, eu utilizo dois dicionários. O primeiro armazena as instâncias de cada peça acompanhadas dos seus respetivos caminhos e locais de captura. O segundo atua como um ponteiro iterativo que mapeia a casa atual do tabuleiro para o identificador único da peça que a ocupa.

ExemploS do export dos movimentos das jogadas
<img width="640" height="640" alt="image" src="https://github.com/user-attachments/assets/84f0a870-a6be-4f0e-8a57-4ff41f212e99" />
Jogada 01
<img width="640" height="640" alt="image" src="https://github.com/user-attachments/assets/523e6b6d-6c15-46ea-aa9b-45e82653eae7" />
Jogada 02


Abaixo destaco o fragmento central da lógica de rastreamento que implementei:

```python
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
