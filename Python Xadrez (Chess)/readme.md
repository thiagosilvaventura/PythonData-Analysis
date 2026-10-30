<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simulador de Xadrez e Mapeamento de Trajetórias</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 30px;
            background-color: #f4f7f6;
        }
        .container {
            background-color: #fff;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        h1, h2, h3 {
            color: #2c3e50;
        }
        h1 {
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-top: 0;
        }
        h2 {
            margin-top: 35px;
            border-bottom: 1px solid #ecf0f1;
            padding-bottom: 8px;
        }
        p {
            margin-bottom: 15px;
            text-align: justify;
        }
        ul, ol {
            margin-bottom: 20px;
            padding-left: 20px;
        }
        li {
            margin-bottom: 10px;
        }
        pre {
            background-color: #282c34;
            color: #abb2bf;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            font-family: 'Consolas', 'Courier New', Courier, monospace;
            font-size: 14px;
            line-height: 1.4;
        }
        code {
            background-color: #e8eaed;
            color: #d90429;
            padding: 2px 5px;
            border-radius: 4px;
            font-family: 'Consolas', 'Courier New', Courier, monospace;
            font-size: 0.95em;
        }
        pre code {
            background-color: transparent;
            color: inherit;
            padding: 0;
            border-radius: 0;
        }
    </style>
</head>
<body>

<div class="container">
    <h1>Simulador de Xadrez e Mapeamento de Trajetórias</h1>

    <p>Neste repositório, apresento o código referente a um simulador de xadrez que desenvolvi com foco primário no rastreamento e na exportação das trajetórias das peças. Eu construí esta aplicação com o intuito de viabilizar a análise espacial de partidas, permitindo que os dados de movimentação sejam extraídos e visualizados graficamente após o término de um jogo.</p>
    
    <p>O software foi programado em Python e eu utilizei duas bibliotecas principais para a sua estruturação: o <code>pygame</code> para a renderização da interface gráfica e o <code>python-chess</code> (importado como <code>chess</code>) para o controle do estado do tabuleiro e a validação estrita das regras do jogo.</p>

    <h2>Estrutura da Interface gráfica e Controles</h2>

    <p>Eu concebi a interface dividindo a tela em duas seções principais. À esquerda, renderizo o tabuleiro em formato tradicional. À direita, estruturei um menu de controle em uma paleta de cores escuras para concentrar os comandos de operação e análise.</p>
    
    <p>No painel de controle, eu implementei os seguintes botões e funções:</p>

    <ul>
        <li><strong>Modo</strong>: Permite alternar o controle dos lados da partida. Eu configurei três estados possíveis: controle exclusivo das peças brancas contra o computador, controle exclusivo das pretas contra o computador, e o modo onde ambos os lados são controlados pelo usuário no mesmo terminal. As respostas do computador são geradas por meio de escolhas pseudoaleatórias entre os movimentos legais disponíveis.</li>
        <li><strong>Desfazer Jogada</strong>: Reverte o último movimento no tabuleiro. Se o usuário estiver jogando contra o computador, eu programei este botão para remover duas jogadas da pilha, garantindo que o turno retorne ao jogador humano.</li>
        <li><strong>Reiniciar Partida</strong>: Restaura o tabuleiro à posição inicial padrão e limpa o histórico de movimentos.</li>
        <li><strong>Exportar Rastros (JSON/PNG)</strong>: Aciona o algoritmo de varredura e reconstrução da partida, gerando os arquivos de saída com os dados mapeados.</li>
        <li><strong>Filtros de Exportação</strong>: Um conjunto de caixas de seleção que eu incluí para refinar os dados exportados. É possível selecionar a cor das peças (Brancas ou Pretas) e o tipo de peça (Peões, Cavalos, Bispos, Torres, Rainhas e Reis).</li>
    </ul>

    <h2>Metodologia de Rastreamento de Peças</h2>

    <p>A biblioteca <code>python-chess</code> não rastreia o ciclo de vida individual das peças; ela foca apenas no estado global do tabuleiro em um dado turno. Para resolver esse problema analítico, eu elaborei a classe <code>PieceTracker</code>. O objetivo desta classe é recriar a partida internamente, passo a passo, registrando a trajetória (caminho) de cada unidade específica.</p>
    
    <p>Para alcançar isso, eu utilizo dois dicionários. O primeiro armazena as instâncias de cada peça acompanhadas de seus respectivos caminhos e locais de captura. O segundo atua como um ponteiro iterativo que mapeia a casa atual do tabuleiro para o identificador único da peça que a ocupa.</p>
    
    <p>Abaixo destaco o fragmento central da lógica de rastreamento que implementei:</p>

<pre><code>class PieceTracker:
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
            self.sq_to_id[to_sq] = pid</code></pre>

    <p>Eu adicionei tratamentos condicionais específicos dentro desta classe para abranger as regras de captura <em>en passant</em> e de roque. No caso do roque, eu garanto que tanto o movimento do rei quanto o da torre correspondente sejam atualizados no dicionário, transferindo os ponteiros simultaneamente.</p>

    <h2>Rotina de Exportação e Filtragem</h2>

    <p>A etapa de exportação é manipulada pela função <code>export_data(board)</code>. Eu estruturei essa função para não interferir no estado real do jogo. Ao acioná-la, eu instancio um tabuleiro temporário e reproduzo todos os movimentos armazenados na pilha (<code>board.move_stack</code>) por meio do <code>PieceTracker</code>.</p>
    
    <p>Em seguida, eu aplico uma camada de filtragem booleana, onde cruzo os atributos das peças rastreadas com o estado atual dos filtros selecionados na interface.</p>

<pre><code>    filtered_pieces = []
    type_map = {
        chess.PAWN: 'peões', chess.KNIGHT: 'cavalos',
        chess.BISHOP: 'bispos', chess.ROOK: 'torres',
        chess.QUEEN: 'rainhas', chess.KING: 'reis'
    }
    
    for p in tracker.pieces.values():
        c_ok = (p['color'] == chess.WHITE and export_filters['brancas']) or                (p['color'] == chess.BLACK and export_filters['pretas'])
        t_ok = export_filters[type_map[p['type']]]
        
        if c_ok and t_ok:
            filtered_pieces.append(p)</code></pre>

    <p>Por fim, eu programo o software para gerar dois arquivos baseados na coleção de peças filtradas:</p>
    <ol>
        <li>Um documento no formato <code>.json</code> que discrimina a casa inicial, tipo, cor, vetor cronológico das coordenadas do trajeto completo e o ponto de captura (caso tenha ocorrido).</li>
        <li>Uma representação estática em <code>.png</code> do tabuleiro. Eu utilizo os módulos de desenho do <code>pygame</code> para traçar segmentos de linha (vetores) evidenciando as casas pelas quais as peças transitaram, marcando com um sinal gráfico em forma de cruz a coordenada exata em que uma peça foi capturada.</li>
    </ol>

    <h2>Como executar</h2>

    <p>Para iniciar o simulador em sua máquina local, certifique-se de que o interpretador Python está instalado e proceda com a obtenção das bibliotecas necessárias utilizando o gerenciador de pacotes:</p>

<pre><code>pip install pygame chess</code></pre>
