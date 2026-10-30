# Simulador de Xadrez e Mapeamento de Trajetórias

Neste repositório, apresento o código referente a um simulador de xadrez que desenvolvi com foco primário no rastreamento e na exportação das trajetórias das peças. Eu construí esta aplicação com o intuito de viabilizar a análise espacial de partidas, permitindo que os dados de movimentação sejam extraídos e visualizados graficamente após o término de um jogo.

O software foi programado em Python e eu utilizei duas bibliotecas principais para a sua estruturação: o `pygame` para a renderização da interface gráfica e o `python-chess` (importado como `chess`) para o controle do estado do tabuleiro e a validação estrita das regras do jogo.

## Estrutura da Interface gráfica e Controles

Eu concebi a interface dividindo a tela em duas seções principais. À esquerda, renderizo o tabuleiro em formato tradicional. À direita, estruturei um menu de controle em uma paleta de cores escuras para concentrar os comandos de operação e análise.

No painel de controle, eu implementei os seguintes botões e funções:

* **Modo**: Permite alternar o controle dos lados da partida. Eu configurei três estados possíveis: controle exclusivo das peças brancas contra o computador, controle exclusivo das pretas contra o computador, e o modo onde ambos os lados são controlados pelo usuário no mesmo terminal. As respostas do computador são geradas por meio de escolhas pseudoaleatórias entre os movimentos legais disponíveis.
* **Desfazer Jogada**: Reverte o último movimento no tabuleiro. Se o usuário estiver jogando contra o computador, eu programei este botão para remover duas jogadas da pilha, garantindo que o turno retorne ao jogador humano.
* **Reiniciar Partida**: Restaura o tabuleiro à posição inicial padrão e limpa o histórico de movimentos.
* **Exportar Rastros (JSON/PNG)**: Aciona o algoritmo de varredura e reconstrução da partida, gerando os arquivos de saída com os dados mapeados.
* **Filtros de Exportação**: Um conjunto de caixas de seleção que eu incluí para refinar os dados exportados. É possível selecionar a cor das peças (Brancas ou Pretas) e o tipo de peça (Peões, Cavalos, Bispos, Torres, Rainhas e Reis).

## Metodologia de Rastreamento de Peças

A biblioteca `python-chess` não rastreia o ciclo de vida individual das peças; ela foca apenas no estado global do tabuleiro em um dado turno. Para resolver esse problema analítico, eu elaborei a classe `PieceTracker`. O objetivo desta classe é recriar a partida internamente, passo a passo, registrando a trajetória (caminho) de cada unidade específica.

Para alcançar isso, eu utilizo dois dicionários. O primeiro armazena as instâncias de cada peça acompanhadas de seus respectivos caminhos e locais de captura. O segundo atua como um ponteiro iterativo que mapeia a casa atual do tabuleiro para o identificador único da peça que a ocupa.

Abaixo destaco o fragmento central da lógica de rastreamento que implementei:

```python
class PieceTracker:
    def __init__(self):
        self.pieces = {}
        self.sq_to_id = {}
        temp_board = chess.Board()
        
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
        
        captured_sq = to_sq
        if board_before.is_en_passant(move):
            captured_sq = to_sq - 8 if board_before.turn == chess.WHITE else to_sq + 8
            
        if captured_sq in self.sq_to_id and self.sq_to_id[captured_sq] != self.sq_to_id.get(from_sq):
            cap_id = self.sq_to_id[captured_sq]
            self.pieces[cap_id]['captured_at'] = captured_sq 
            del self.sq_to_id[captured_sq]
            
        if from_sq in self.sq_to_id:
            pid = self.sq_to_id.pop(from_sq)
            self.pieces[pid]['path'].append(to_sq)
            self.sq_to_id[to_sq] = pid
