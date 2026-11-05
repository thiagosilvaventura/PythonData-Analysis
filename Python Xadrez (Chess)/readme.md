# Simulador de Xadrez com Mapeamento de Trajetórias de Peças

<img width="1458" height="1002" alt="image" src="https://github.com/user-attachments/assets/553e010d-400b-4533-8c78-b11bcaf3fbdd" />

Desenvolvi este simulador de xadrez em Python para registrar a trajetória de cada peça durante uma partida e exportar, ao final, tabelas e imagens que possam ser usadas em análises espaciais e estatísticas. Usei o `pygame` para a interface gráfica e o `python-chess` para o estado do tabuleiro e a validação das regras.

O `python-chess` guarda apenas a posição atual, sem identificar cada peça ao longo dos lances. Para resolver isso, escrevi a classe `PieceTracker`, que refaz a partida lance a lance e associa cada movimento, captura e promoção à peça que o realizou. Na primeira versão eu exportava somente o caminho de cada peça e a casa onde ela foi capturada. Na versão atual também exporto métricas por lance, por peça e por partida, mapas por casa, arquivos CSV, JSON e PGN, e incluí um modo sem interface para rodar várias partidas e um modo de autojogo aleatório que não repete partidas.

## 1. Requisitos e instalação

- Python 3 (usei o 3.13).
- `pygame` 2.x e `python-chess` 1.x. Preciso da versão 1.0 ou superior por causa do método `Board.outcome()`.

```bash
pip install pygame python-chess
```

Rodei o código no Windows 11, com `pygame` 2.6.1 e `python-chess` 1.11.2.

## 2. Execução

```bash
python Main.py                                   # interface gráfica
python Main.py --lang en                         # interface em inglês (também dá para trocar na janela)
python Main.py --batch 200 --white-level 1 --black-level 3 --seed 7
python Main.py --batch 100 --random              # autojogo aleatório, sem repetir partidas
python Main.py --batch 50 --full                 # grava a pasta completa (CSV/JSON/PNG) de cada partida
python Main.py --report                          # resume as partidas já salvas
```

| Opção | Descrição |
|---|---|
| `--out` | Pasta de saída. O padrão é a pasta `exports`, criada ao lado do `Main.py`. |
| `--lang pt\|en` | Idioma inicial. A escolha fica salva em `exports/settings.json`. |
| `--seed` | Semente para reproduzir uma execução. |
| `--batch N` | Roda N partidas computador contra computador, sem interface. |
| `--random` | No modo `--batch`, sorteia semente, níveis e ruído a cada partida e evita repetições. |
| `--white-level`, `--black-level` | Nível do motor (0 a 3) de cada lado. |
| `--move-time`, `--max-plies` | Tempo por lance e limite de lances por partida no modo `--batch`. |
| `--full` | No modo `--batch`, grava a pasta completa de cada partida. |
| `--report` | Resume `dataset/games_log.csv`: frequência dos resultados com intervalo de confiança de Wilson a 95% e estatísticas descritivas das métricas. |

## 3. Interface e controles

A janela tem duas áreas: o tabuleiro, à esquerda, e o painel de controle, à direita. Usei fundo escuro com realces em ciano para as peças brancas e em magenta para as pretas.

| Controle | Função |
|---|---|
| **Modo** | Define quem controla cada lado (ver Seção 4). O clique esquerdo avança e o direito volta. |
| **Nível do PC** | Escolhe o nível do motor: Aleatório, Fácil, Médio ou Difícil. |
| **PT \| EN** | Troca o idioma da interface. |
| **Desfazer** | Remove o último lance. Nos modos contra o computador, remove lances até a vez voltar ao jogador humano. |
| **Reiniciar** | Volta à posição inicial e limpa o histórico. |
| **Girar** | Inverte a orientação do tabuleiro. |
| **Filtros de exportação** | Limitam as peças incluídas em `pieces.csv`, `traces.json` e `trace.png`, por cor e por tipo. |
| **Exportar análise** | Gera os arquivos descritos na Seção 6. |
| **Abrir pasta** | Abre no explorador de arquivos a última pasta exportada, ou a pasta raiz de saída se ainda não houve exportação. |
| **Iniciar / Parar** | Inicia, retoma ou interrompe as jogadas do computador. Em uma partida terminada, **Iniciar** começa outra. |

Atalhos: `U` desfaz, `R` reinicia, `F` gira, `E` exporta, `O` abre a pasta, `P` inicia ou para, `L` troca o idioma e `Esc` cancela a seleção. As peças podem ser movidas arrastando ou clicando na origem e no destino. Em promoções, aparece um seletor de peça. A roda do mouse sobre o painel rola o histórico de lances.

## 4. Modos de jogo e motor do computador

| Modo | Brancas | Pretas |
|---|---|---|
| Brancas (vs PC) | Humano | Computador |
| Pretas (vs PC) | Computador | Humano |
| Humano nos 2 lados | Humano | Humano |
| PC vs PC | Computador | Computador |
| Autojogo aleatório | Computador | Computador, com partidas encadeadas e sem repetição |

O computador só joga depois de **Iniciar**. Nos modos contra o computador, o primeiro lance do jogador humano também ativa as respostas. No modo "Humano nos 2 lados" não há jogada automática.

**Motor.** No nível 0, o computador escolhe uniformemente entre os lances legais. Nos níveis 1 a 3, usei busca negamax com poda alfa-beta e aprofundamento iterativo (profundidade 1 a 3), com limite de tempo por lance. A avaliação soma o material (P=100, N=320, B=330, R=500, Q=900) a dois termos posicionais simples: centralização das peças e avanço dos peões. O parâmetro ε é a probabilidade de trocar o lance escolhido por um lance legal aleatório.

**Autojogo aleatório e partidas únicas.** A cada partida, sorteio com gerador criptográfico a semente, o nível de cada lado (0 a 3, com mais peso nos níveis baixos) e o ruído ε (entre 0,05 e 0,30). Quando a partida termina, gravo em `dataset/seen_games.txt` o hash SHA-1 da sequência completa de lances em notação UCI. Nas partidas seguintes, um lance que reproduziria por inteiro uma sequência já registrada é proibido, desde que exista outro lance legal. Como o registro fica em arquivo, a regra vale também entre execuções diferentes do programa, enquanto esse arquivo for mantido. Partidas interrompidas com **Parar** antes de terminar não entram no registro.

## 5. Metodologia de rastreamento

A classe `PieceTracker` usa duas estruturas:

1. `pieces`: dicionário indexado pela casa inicial de cada uma das 32 peças, que funciona como identificador. Cada entrada guarda cor, tipo, tipo final, caminho percorrido, lance de cada passo e, quando existem, casa e lance da captura, peça que capturou e lance da promoção.
2. `sq_to_id`: dicionário que associa a casa ocupada no momento ao identificador da peça que está nela.

A cada lance, o rastreador faz cinco coisas: identifica a casa da captura, tratando a captura *en passant* à parte; registra a captura e a atribui à peça que se moveu; desloca a torre no roque; atualiza o caminho da peça movida; e registra a promoção, mantendo o identificador original e alterando só o tipo final. O rastreamento é refeito a partir da posição inicial, usando a pilha de lances do tabuleiro, de modo que o botão Desfazer não deixa os dados inconsistentes.

```python
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
    # ... deslocamento da torre no roque, atualização do caminho e registro da promoção
```

Com as trajetórias reconstruídas, a função `analyze_game` percorre a partida e calcula as métricas por lance e os mapas por casa descritos na próxima seção. Defini as fases da partida por um critério simples: abertura até o 20.º meio-lance; final quando o material não-peão somado dos dois lados é de até 26 pontos; meio-jogo nos demais casos.

## 6. Dados exportados

Cada exportação manual cria a pasta `exports/partidas/<id>_<N>plies/`. As partidas finalizadas também são acrescentadas aos arquivos acumulados em `exports/dataset/`.

```
exports/
├── partidas/<id>_<N>plies/
│   ├── summary.json        # métricas por lado, fase e tipo de peça; metadados e ambiente
│   ├── moves.csv           # uma linha por meio-lance
│   ├── pieces.csv          # uma linha por peça inicial (sujeito aos filtros da interface)
│   ├── traces.json         # trajetórias por peça
│   ├── heatmaps.csv        # mapas por casa em formato longo (map, square, file, rank, value)
│   ├── partida.pgn         # partida em PGN, com o tempo de cada lance como comentário
│   ├── trace.png           # trajetórias sobre o tabuleiro
│   ├── heat_*.png          # mapas de calor
│   └── material.png        # balanço de material e lances legais por lance
├── dataset/
│   ├── games_log.csv       # uma linha por partida finalizada
│   ├── moves_all.csv       # lances de todas as partidas
│   ├── pieces_all.csv      # peças de todas as partidas (sem filtros)
│   └── seen_games.txt      # hashes das partidas do autojogo aleatório
├── batches/                # resumos e mapas agregados do modo --batch
├── DICIONARIO_DE_DADOS.md  # descrição das colunas (português)
└── DATA_DICTIONARY.md      # descrição das colunas (inglês)
```

**Variáveis por lance (`moves.csv`).** Número do lance e cor; notação SAN e UCI; peça, casa de origem e casa de destino; indicadores de captura, peça capturada, *en passant*, roque, promoção, xeque e xeque-mate; número de lances legais antes do lance; número de lances legais do adversário depois dele; material de cada lado e balanço, em unidades de peão (P=1, N=B=3, R=5, Q=9); material não-peão total; fase; contador de meios-lances sem captura ou avanço de peão; tempo gasto; e o FEN resultante.

**Variáveis por peça (`pieces.csv`).** Rótulo com tipo e casa inicial (por exemplo `Ng1`); tipo inicial e final; número de movimentos; distâncias euclidiana e de Manhattan percorridas, em casas; casas distintas visitadas e revisitas; capturas realizadas; casa, lance e autor da captura sofrida; tempo de vida em meios-lances; razão de atividade (movimentos da peça divididos pelos turnos do seu lado enquanto ela esteve em jogo); e o caminho completo com o lance de cada passo.

**Mapas por casa (`heatmaps.csv`).**

| Mapa | Definição |
|---|---|
| `destinations` | Número de chegadas à casa. |
| `traffic` | Chegadas somadas às casas atravessadas por bispo, torre e dama, e pelo avanço duplo do peão. |
| `captures` | Número de capturas ocorridas na casa. |
| `occupancy_white`, `occupancy_black` | Número de meios-lances em que a casa esteve ocupada por peça da cor. |
| `control_white`, `control_black` | Soma, ao longo dos lances, de quantas vezes a casa foi atacada por peças da cor. Inclui casas ocupadas por peças da própria cor (defesas). |

## 7. Exemplo de saída

Gerei uma partida para mostrar o formato dos arquivos e o tipo de informação que o código produz. Os valores abaixo servem só como ilustração dos campos. Não são estimativas gerais sobre o jogo, e as análises com várias partidas serão feitas em outro repositório.

**Configuração e desfecho.** Modo PC vs PC, níveis 0 e 0, semente 1069430941. A partida teve 253 meios-lances e terminou empatada por material insuficiente, com rei e bispo contra rei e bispo (`4K3/1B6/8/5b2/3k4/8/8/8 b - - 0 127`).

**Exemplo do `summary.json`, bloco `sides`.**

| Campo | Brancas | Pretas |
|---|---|---|
| Lances | 127 | 126 |
| Capturas | 14 | 14 |
| Material capturado (unidades de peão) | 36 | 44 |
| Xeques aplicados | 8 | 12 |
| Promoções | 1 | 0 |
| Peças perdidas | 14 | 14 |
| Ramificação média | 22,55 | 28,42 |
| Mobilidade média do adversário após o lance | 28,33 | 22,57 |

O material capturado pelas pretas inclui a dama obtida por promoção (9 pontos), que foi capturada no lance seguinte.

**Exemplo do bloco `timeline`.** Primeira captura no meio-lance 11, primeiro xeque no 27, início do final no 114 (pelo critério da Seção 5) e promoção `d8=Q+` no 127, feita pelo peão inicial de c2. A dama promovida foi capturada no meio-lance 128, pela torre inicial de a8. O campo `max_quiet_streak` registrou 80 meios-lances sem captura ou avanço de peão. Nessa partida não houve roque, captura *en passant* nem recaptura imediata na mesma casa.

**Exemplo do bloco `phases`.**

| Fase | Meios-lances | Capturas | Xeques | Ramificação média |
|---|---|---|---|---|
| Abertura | 20 | 1 | 0 | 29,0 |
| Meio-jogo | 94 | 16 | 8 | 33,0 |
| Final | 139 | 11 | 12 | 19,9 |

**Exemplo do bloco `piece_stats`.**

| Tipo | Mov. médios (B / P) | Capturas feitas (B / P) | Sobrevivência (B / P) |
|---|---|---|---|
| Peão | 2,38 / 1,38 | 2 / 1 | 0,00 / 0,00 |
| Cavalo | 9,5 / 6,0 | 5 / 1 | 0,00 / 0,00 |
| Bispo | 18,5 / 10,0 | 2 / 2 | 0,50 / 0,50 |
| Torre | 4,5 / 23,5 | 1 / 8 | 0,00 / 0,00 |
| Dama | 5,0 / 8,0 | 1 / 0 | 0,00 / 0,00 |
| Rei | 38,0 / 28,0 | 3 / 2 | 1,00 / 1,00 |

B = brancas, P = pretas. A sobrevivência é a fração das peças do tipo que não foi capturada até o fim da partida.


