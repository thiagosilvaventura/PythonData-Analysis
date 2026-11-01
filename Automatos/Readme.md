
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simulador de Vida - Evolução e Ecossistema</title>
</head>

<body>

<h1>🌱 Simulador de Vida — Evolução e Ecossistema</h1>

<p>
    Neste projeto, desenvolvo uma simulação computacional de um ecossistema
    artificial utilizando Python e Pygame. O ambiente contém seis espécies
    de agentes autônomos, cada uma com atributos físicos, necessidades
    energéticas e relações alimentares específicas.
</p>

<p>
    A simulação combina conceitos de programação orientada a objetos,
    sistemas multiagentes, algoritmos evolutivos e modelagem de
    comportamentos inspirados em processos ecológicos.
</p>

<hr>

<h2 id="objetivos">🎯 Objetivos</h2>

<p>
    O objetivo é observar como regras individuais relativamente simples
    podem produzir comportamentos coletivos e dinâmicas populacionais
    complexas ao longo do tempo.
</p>

<ul>
    <li>Simular organismos com características físicas distintas.</li>
    <li>Implementar relações entre predadores, presas e recursos vegetais.</li>
    <li>Desenvolver mecanismos de busca por alimento.</li>
    <li>Simular consumo energético e mortalidade.</li>
    <li>Implementar reprodução com herança de características.</li>
    <li>Introduzir mutações aleatórias nos atributos dos descendentes.</li>
    <li>Observar mudanças na distribuição das espécies.</li>
    <li>Visualizar os comportamentos em tempo real.</li>
</ul>

<hr>

<h2 id="tecnologias">🛠️ Tecnologias utilizadas</h2>

<table>
    <thead>
        <tr>
            <th>Tecnologia</th>
            <th>Aplicação</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>🐍 Python</td>
            <td>Linguagem principal e implementação da lógica.</td>
        </tr>
        <tr>
            <td>🎮 Pygame</td>
            <td>Renderização gráfica, eventos e controle da simulação.</td>
        </tr>
        <tr>
            <td>🎲 Random</td>
            <td>Geração de posições, probabilidades e mutações.</td>
        </tr>
        <tr>
            <td>📐 Math</td>
            <td>Cálculos de distância e movimentação vetorial.</td>
        </tr>
        <tr>
            <td>🧱 Programação Orientada a Objetos</td>
            <td>Organização dos agentes e recursos em classes.</td>
        </tr>
    </tbody>
</table>

<h3>Bibliotecas importadas</h3>

<pre><code>import pygame
import random
import math</code></pre>

<hr>

<h2 id="ecossistema">🧬 Estrutura do ecossistema</h2>

<p>
    Defino seis espécies com diferentes atributos e dietas.
    Cada espécie possui velocidade, tamanho corporal, alcance
    visual e relações alimentares próprias.
</p>

<h3>Classificação das espécies</h3>

<table>
    <thead>
        <tr>
            <th>ID</th>
            <th>Espécie</th>
            <th>Cor</th>
            <th>Dieta</th>
            <th>Velocidade</th>
            <th>Raio</th>
            <th>Visão</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>0</td>
            <td>Herbívoro Veloz</td>
            <td>🔵 Ciano</td>
            <td>Plantas</td>
            <td>3.5</td>
            <td>4</td>
            <td>100</td>
        </tr>
        <tr>
            <td>1</td>
            <td>Herbívoro Tanque</td>
            <td>🟡 Amarelo</td>
            <td>Plantas</td>
            <td>1.5</td>
            <td>8</td>
            <td>80</td>
        </tr>
        <tr>
            <td>2</td>
            <td>Herbívoro Comum</td>
            <td>🩷 Rosa</td>
            <td>Plantas</td>
            <td>2.2</td>
            <td>6</td>
            <td>120</td>
        </tr>
        <tr>
            <td>3</td>
            <td>Carnívoro Caçador</td>
            <td>🟠 Laranja</td>
            <td>Espécies 0, 1 e 2</td>
            <td>2.8</td>
            <td>7</td>
            <td>150</td>
        </tr>
        <tr>
            <td>4</td>
            <td>Predador Apex</td>
            <td>🔴 Vermelho</td>
            <td>Espécies 0, 1, 2, 3 e 5</td>
            <td>2.5</td>
            <td>10</td>
            <td>200</td>
        </tr>
        <tr>
            <td>5</td>
            <td>Onívoro Oportunista</td>
            <td>⚪ Branco</td>
            <td>Plantas e espécie 0</td>
            <td>2.0</td>
            <td>5</td>
            <td>110</td>
        </tr>
    </tbody>
</table>

<h3>Representação das relações alimentares</h3>

<p>
    A dieta de cada espécie é definida por uma lista de identificadores.
    Quando um agente encontra um indivíduo pertencente à sua dieta,
    ele pode consumi-lo e obter energia.
</p>

<pre><code>SPECIES_DEFS = {
    3: {
        "name": "Carnívoro Caçador",
        "color": (255, 165, 0),
        "diet": [0, 1, 2],
        "base_speed": 2.8,
        "base_radius": 7,
        "base_vision": 150
    }
}</code></pre>

<p>
    A espécie 3, por exemplo, pode consumir as três espécies herbívoras.
    Essa estrutura permite modificar as relações ecológicas sem
    reescrever o comportamento central dos agentes.
</p>

<hr>

<h2 id="conceitos">🧠 Conceitos e técnicas utilizados</h2>

<h3>1. Programação Orientada a Objetos (POO)</h3>

<p>
    Utilizo classes para representar os elementos fundamentais
    do ambiente: agentes e recursos alimentares.
    Cada objeto possui atributos e comportamentos próprios.
</p>

<h4>Classe Food</h4>

<pre><code>class Food:
    def __init__(self):
        self.x = random.randint(10, WIDTH - 10)
        self.y = random.randint(10, HEIGHT - 10)
        self.radius = 3</code></pre>

<p>
    Cada instância de <code>Food</code> representa uma unidade
    alimentar posicionada aleatoriamente no ambiente.
</p>

<h4>Classe Agent</h4>

<pre><code>class Agent:
    def __init__(self, x, y, species_id,
                 inherited_traits=None):

        self.x = x
        self.y = y
        self.species_id = species_id</code></pre>

<p>
    A classe <code>Agent</code> centraliza a lógica de movimento,
    alimentação, metabolismo, reprodução e herança genética.
    Essa organização facilita a manutenção e a expansão do modelo.
</p>

<h3>2. Sistemas Multiagentes (MAS)</h3>

<p>
    Cada agente atua de maneira relativamente independente,
    utilizando suas próprias características e informações locais
    para tomar decisões.
</p>

<p>
    Não estabeleço uma estratégia global para controlar a população.
    O comportamento coletivo emerge das interações entre agentes,
    recursos e ambiente.
</p>

<h3>3. Busca baseada em distância euclidiana</h3>

<p>
    Utilizo a distância euclidiana para identificar alimentos e
    possíveis presas dentro do campo de visão de cada indivíduo.
</p>

<pre><code>def distance_to(self, other):
    return math.hypot(
        self.x - other.x,
        self.y - other.y
    )</code></pre>

<p>
    Matematicamente, a distância entre dois pontos é:
</p>

<p>
    <strong>d = √((x₂ − x₁)² + (y₂ − y₁)²)</strong>
</p>

<p>
    A função <code>math.hypot()</code> calcula esse valor de maneira
    direta, evitando a implementação manual das operações.
</p>

<h3>4. Comportamento orientado a objetivos</h3>

<p>
    Quando um agente identifica um alvo dentro de seu alcance visual,
    ele calcula a direção necessária para se aproximar.
</p>

<pre><code>def move_towards(self, target_x, target_y):
    dx = target_x - self.x
    dy = target_y - self.y

    dist = math.hypot(dx, dy)

    if dist > 0:
        self.x += (dx / dist) * self.speed
        self.y += (dy / dist) * self.speed</code></pre>

<p>
    Divido os componentes do deslocamento pela distância total,
    obtendo um vetor normalizado. Multiplico esse vetor pela
    velocidade do agente para controlar a magnitude do movimento.
</p>

<h3>5. Movimento aleatório (Random Walk)</h3>

<p>
    Quando nenhum alvo é identificado, o agente realiza
    deslocamentos aleatórios em ambas as coordenadas.
</p>

<pre><code>def wander(self):
    self.x += random.uniform(
        -self.speed, self.speed
    )

    self.y += random.uniform(
        -self.speed, self.speed
    )</code></pre>

<p>
    Essa abordagem é conhecida como <em>Random Walk</em>.
    Ela permite que os indivíduos explorem o ambiente sem
    depender de um objetivo previamente definido.
</p>

<h3>6. Algoritmo evolutivo simplificado</h3>

<p>
    Implemento um mecanismo de reprodução no qual os agentes
    sobreviventes transmitem seus atributos físicos aos descendentes.
    A herança é acompanhada por pequenas alterações aleatórias.
</p>

<p>
    O processo apresenta elementos de algoritmos evolutivos:
    representação de indivíduos, herança, mutação e seleção
    condicionada à sobrevivência.
</p>

<p>
    Entretanto, não se trata de um algoritmo genético clássico
    completo, pois não utilizo uma função de aptidão explícita,
    seleção por torneio ou cruzamento entre dois genitores.
</p>

<hr>

<h2 id="funcionamento">⚙️ Funcionamento da simulação</h2>

<p>
    A execução ocorre em um ciclo contínuo de atualização.
    A cada quadro, verifico os eventos, atualizo os agentes,
    contabilizo a população e renderizo os elementos na tela.
</p>

<h3>Etapas do ciclo</h3>

<ol>
    <li>Inicializo os alimentos e os agentes.</li>
    <li>Gero novos recursos alimentares de maneira probabilística.</li>
    <li>Atualizo o metabolismo de cada agente.</li>
    <li>Identifico alimentos ou presas dentro do alcance visual.</li>
    <li>Movimento o agente em direção ao alvo ou aplico movimento aleatório.</li>
    <li>Verifico as condições de alimentação.</li>
    <li>Realizo a reprodução quando o nível energético é suficiente.</li>
    <li>Removo os agentes mortos e adiciono os descendentes.</li>
    <li>Verifico a presença de todas as espécies.</li>
    <li>Atualizo a interface gráfica.</li>
</ol>

<h3>Geração de alimentos</h3>

<pre><code>if random.random() &lt; 0.25:
    foods.append(Food())</code></pre>

<p>
    A cada quadro, existe uma probabilidade de 25% de geração
    de uma nova unidade alimentar.
    Como a simulação opera a 60 FPS, essa taxa corresponde
    a uma expectativa de aproximadamente 15 unidades por segundo,
    caso a execução mantenha a frequência configurada.
</p>

<h3>Seleção de alvos</h3>

<pre><code>target = None
min_dist = self.vision

for food in foods:
    dist = self.distance_to(food)

    if dist &lt; min_dist:
        min_dist = dist
        target = food</code></pre>

<p>
    Seleciono o alvo mais próximo dentro do campo de visão.
    O mesmo princípio é aplicado posteriormente aos agentes
    que pertencem à dieta do indivíduo.
</p>

<p>
    A busca utiliza uma comparação sequencial, sem estruturas
    espaciais auxiliares.
</p>

<hr>

<h2 id="genetica">🧪 Genética e mutação</h2>

<p>
    Os atributos de velocidade, tamanho e visão são transmitidos
    aos descendentes. Durante a reprodução, cada característica
    pode sofrer uma mutação de até 10% em relação ao valor herdado.
</p>

<h3>Herança com mutação</h3>

<pre><code>mutation_rate = 0.1

self.speed = max(
    0.5,
    inherited_traits['speed'] *
    random.uniform(1 - mutation_rate,
                   1 + mutation_rate)
)

self.radius = max(
    3.0,
    inherited_traits['radius'] *
    random.uniform(1 - mutation_rate,
                   1 + mutation_rate)
)

self.vision = max(
    50.0,
    inherited_traits['vision'] *
    random.uniform(1 - mutation_rate,
                   1 + mutation_rate)
)</code></pre>

<h3>Características mutáveis</h3>

<table>
    <thead>
        <tr>
            <th>Atributo</th>
            <th>Influência no comportamento</th>
            <th>Possível consequência evolutiva</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>🏃 Velocidade</td>
            <td>Determina a distância percorrida por quadro.</td>
            <td>Maior mobilidade, com custo energético superior.</td>
        </tr>
        <tr>
            <td>📏 Raio</td>
            <td>Define o tamanho corporal e a distância de contato.</td>
            <td>Maior alcance de colisão e metabolismo mais elevado.</td>
        </tr>
        <tr>
            <td>👁️ Visão</td>
            <td>Define a distância máxima para detectar alvos.</td>
            <td>Maior capacidade de localização, com custo energético.</td>
        </tr>
    </tbody>
</table>

<h3>Reprodução e transmissão genética</h3>

<pre><code>if agent.energy > agent.reproduce_threshold:

    agent.energy /= 2

    traits = {
        'speed': agent.speed,
        'radius': agent.radius,
        'vision': agent.vision
    }

    new_agents.append(
        Agent(
            agent.x + random.randint(-15, 15),
            agent.y + random.randint(-15, 15),
            agent.species_id,
            traits
        )
    )</code></pre>

<p>
    O agente divide sua energia com o custo de reprodução
    representado pela redução de 50% de sua reserva energética.
    O descendente recebe os atributos herdados e uma posição
    próxima à do progenitor.
</p>

<p>
    Como a reprodução depende da energia acumulada,
    os indivíduos que conseguem acessar recursos com maior
    frequência apresentam mais oportunidades de gerar descendentes.
</p>

<hr>

<h2 id="energia">⚡ Sistema energético</h2>

<p>
    Cada agente começa com 100 unidades de energia,
    possui capacidade máxima de 200 e perde energia
    continuamente durante a simulação.
</p>

<h3>Custo metabólico</h3>

<pre><code>self.energy_drain = (
    self.speed * self.radius * self.vision
) / 5000.0</code></pre>

<p>
    Defino o consumo energético como uma função multiplicativa
    dos atributos físicos. Assim, indivíduos maiores, mais rápidos
    e com maior campo visual apresentam maior custo metabólico.
</p>

<h3>Recuperação de energia</h3>

<table>
    <thead>
        <tr>
            <th>Evento</th>
            <th>Energia recuperada</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Consumo de alimento vegetal</td>
            <td>+30 unidades</td>
        </tr>
        <tr>
            <td>Consumo de outro agente</td>
            <td>+80 unidades</td>
        </tr>
        <tr>
            <td>Reprodução</td>
            <td>Redução de 50% da energia atual</td>
        </tr>
        <tr>
            <td>Metabolismo</td>
            <td>Consumo contínuo proporcional aos atributos</td>
        </tr>
    </tbody>
</table>

<h3>Mortalidade por energia</h3>

<pre><code>self.energy -= self.energy_drain

if self.energy &lt;= 0:
    self.dead = True
    return</code></pre>

<p>
    Quando a energia chega a zero ou a um valor negativo,
    o agente deixa de participar da simulação e é removido
    da população.
</p>

<hr>

<h2 id="interface">🖥️ Interface gráfica</h2>

<p>
    Utilizo o Pygame para representar os indivíduos como círculos
    coloridos e os recursos alimentares como pequenos pontos verdes.
    As cores permitem distinguir visualmente as espécies.
</p>

<h3>Indicadores populacionais</h3>

<p>
    No canto superior esquerdo da janela, apresento a quantidade
    de indivíduos vivos de cada espécie e o total de alimentos
    disponíveis.
</p>

<pre><code>text = font.render(
    f"{name}: {count}",
    True,
    color
)

screen.blit(text, (10, y_offset))</code></pre>

<h3>Controle de atualização</h3>

<pre><code>clock.tick(FPS)

pygame.display.flip()</code></pre>

<p>
    O controle de FPS limita a frequência de atualização
    e a função <code>pygame.display.flip()</code> apresenta
    o quadro renderizado na janela.
</p>

<hr>

<h2 id="instalacao">🚀 Instalação e execução</h2>

<h3>1. Pré-requisitos</h3>

<p>
    É necessário ter Python instalado e disponível no terminal.
</p>

<h3>2. Instalação do Pygame</h3>

<pre><code>pip install pygame</code></pre>

<h3>3. Execução</h3>

<p>
    Salve o código em um arquivo chamado
    <code>simulador_vida.py</code> e execute:
</p>

<pre><code>python simulador_vida.py</code></pre>

<h3>4. Encerramento</h3>

<p>
    Para fechar a simulação, utilize o botão de fechar
    da janela do Pygame.
</p>

<hr>

</p>

<h3>6. What if eu utilizasse um ambiente com recursos limitados?</h3>

<p>
    Atualmente, novos alimentos são gerados continuamente
    por meio de uma probabilidade fixa.
    Poderia substituir esse mecanismo por recursos que
    crescem, se regeneram ou se esgotam em regiões específicas.
</p>

<p><strong>Por que não utilizei inicialmente?</strong></p>

<p>
    A geração probabilística mantém uma fonte de alimento
    relativamente simples, permitindo observar inicialmente
    a interação entre metabolismo, reprodução e predação.
</p>

<p>
    A limitação de recursos poderia introduzir competição
    mais intensa, ciclos populacionais e alterações
    significativas no equilíbrio ecológico.
</p>

<h3>7. What if eu utilizasse seleção natural sem intervenção externa?</h3>

<p>
    No código atual, quando uma espécie desaparece,
    um novo indivíduo com características base é inserido
    automaticamente no ambiente.
</p>

<pre><code>if count == 0:
    agents.append(
        Agent(
            WIDTH // 2 + random.randint(-100, 100),
            HEIGHT // 2 + random.randint(-100, 100),
            species_id
        )
    )</code></pre>

<p><strong>Por que implementei essa regra?</strong></p>

<p>
    Utilizo esse mecanismo para garantir a presença contínua
    das seis espécies e facilitar a observação comparativa
    de seus comportamentos.
</p>

<p>
    Entretanto, essa regra representa uma intervenção externa
    no ecossistema e não corresponde à seleção natural
    em um ambiente fechado.
</p>

<p>
    Em uma versão alternativa, removeria essa reinicialização
    automática. A extinção passaria a ser permanente,
    permitindo observar quais espécies conseguem sobreviver
    sob as condições estabelecidas.
</p>

<hr>

<ul>
    <li>
        <strong>Metabolismo simplificado:</strong>
        o consumo energético é baseado em uma fórmula
        definida manualmente, sem calibração biológica.
    </li>
    <li>
        <strong>Reprodução assexuada:</strong>
        cada descendente herda os atributos de um único
        progenitor, sem recombinação genética.
    </li>
    <li>
        <strong>Mutação independente:</strong>
        as características são alteradas aleatoriamente,
        sem correlação genética entre os atributos.
    </li>
    <li>
        <strong>Percepção limitada:</strong>
        os agentes identificam alvos pela distância,
        sem obstáculos ou oclusão visual.
    </li>
    <li>
        <strong>Movimento simplificado:</strong>
        não há aceleração, inércia ou simulação
        física de colisões.
    </li>  


<h2>📄 Considerações finais</h2>

<p>
    Com este projeto, exploro a construção de um ambiente
    computacional no qual comportamentos individuais
    influenciam diretamente a dinâmica coletiva.
</p>

<p>
    A combinação de regras alimentares, metabolismo,
    movimentação e reprodução permite observar como
    pequenas diferenças nas características dos agentes
    podem produzir resultados distintos ao longo do tempo.
</p>

<p>
    O projeto também estabelece uma base para experimentos
    futuros envolvendo aprendizado de máquina, algoritmos
    evolutivos mais elaborados, análise estatística e
    modelagem de ecossistemas com maior complexidade.
</p>
<p align="center">
    🌿 <strong>Simulação, observação e experimentação computacional.</strong>
</p>

</body>
</html>
</WritingBlock>
