<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Regex Translator - README</title>
    <style>
        :root {
            --bg-color: #282a36;
            --card-bg: #1e1f29;
            --text-color: #f8f8f2;
            --comment-color: #6272a4;
            --green: #50fa7b;
            --purple: #bd93f9;
            --cyan: #8be9fd;
            --pink: #ff79c6;
            --border-color: #44475a;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            margin: 0;
            padding: 40px 20px;
            display: flex;
            justify-content: center;
        }

        .container {
            max-width: 850px;
            width: 100%;
            background-color: var(--card-bg);
            padding: 40px;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }

        h1 {
            color: var(--green);
            font-size: 2.2em;
            margin-top: 0;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 10px;
            letter-spacing: 1px;
        }

        h2 {
            color: var(--purple);
            font-size: 1.5em;
            margin-top: 30px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 6px;
        }

        h3 {
            color: var(--cyan);
            font-size: 1.15em;
            margin-top: 20px;
        }

        p {
            margin-bottom: 16px;
        }

        ul, ol {
            padding-left: 24px;
            margin-bottom: 20px;
        }

        li {
            margin-bottom: 10px;
        }

        strong {
            color: var(--pink);
        }

        code {
            font-family: "Fira Code", "JetBrains Mono", Consolas, monospace;
            background-color: var(--bg-color);
            color: var(--cyan);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.9em;
        }

        pre {
            background-color: var(--bg-color);
            padding: 16px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            overflow-x: auto;
        }

        pre code {
            background-color: transparent;
            padding: 0;
            color: var(--green);
            font-size: 0.95em;
        }

        hr {
            border: 0;
            height: 1px;
            background: var(--border-color);
            margin: 30px 0;
        }
    </style>
</head>
<body>

<div class="container">
    <h1>Regex Translator</h1>
    <p>Um utilitário de tradução bidirecional entre expressões regulares (Regex) e linguagem natural (Português), desenvolvido em Python utilizando a biblioteca PySide6. A ferramenta opera 100% offline, conta com detecção automática de formato, realce de sintaxe em tempo real e processamento assíncrono em segundo plano para manter a interface responsiva.</p>

    <hr>

    <h2>🛠️ Tecnologias e Bibliotecas Utilizadas</h2>
    <ul>
        <li><strong>Python 3.8+:</strong> Linguagem principal para a lógica de tradução e manipulação de strings.</li>
        <li><strong>PySide6 (Qt para Python):</strong> Framework gráfico utilizado para a construção da interface de usuário, gerenciamento de eventos, estilização e manipulação do DOM de texto.</li>
        <li><strong>QThreadPool &amp; QRunnable:</strong> Utilizados para isolar o motor de tradução da thread principal da interface gráfica (<em>UI Thread</em>), evitando travamentos durante o processamento de blocos grandes de texto.</li>
    </ul>

    <hr>

    <h2>✨ Principais Funcionalidades</h2>
    <ul>
        <li><strong>Tradução Bidirecional:</strong> Conversão fluida de expressões regulares para descrições textuais em português e vice-versa.</li>
        <li><strong>Detecção Automática:</strong> Identifica de forma inteligente se o texto inserido corresponde a uma sintaxe de Regex ou a uma instrução em linguagem natural.</li>
        <li><strong>Realce de Sintaxe (<em>Syntax Highlighting</em>):</strong> Destaca visualmente âncoras, metacaracteres, classes, quantificadores e grupos utilizando uma paleta inspirada no tema Dracula.</li>
        <li><strong>Processamento Assíncrono com Debounce:</strong> As traduções são acionadas por um temporizador de atraso (<em>timer single-shot</em> de 400ms) executado em segundo plano, garantindo digitação fluida.</li>
        <li><strong>Interface Adaptada:</strong> Janela dividida (<em>splitter</em>) com suporte a atalhos de teclado (como <code>Ctrl + L</code> para limpeza rápida) e inversão dinâmica de direções de tradução.</li>
    </ul>

    <hr>

    <h2>📂 Estrutura do Código</h2>
    <p>O script está dividido em quatro módulos lógicos principais:</p>
    <ol>
        <li><strong>Configurações e Constantes:</strong> Definição do nome da aplicação, rótulos de idioma e dicionários de mapeamento heurístico (<code>REGEX_TO_NATURAL</code> e <code>NATURAL_TO_REGEX</code>).</li>
        <li><strong>Motor de Tradução (<code>RegexEngine</code>):</strong> Responsável por analisar o texto de entrada, aplicar as regras de substituição via expressões regulares nativas e calcular o tempo de execução em milissegundos.</li>
        <li><strong>Componentes de Interface:</strong> Fábrica de fontes monoespaçadas (suportando <em>Fira Code</em>, <em>JetBrains Mono</em> e <em>Consolas</em>), o marcador de sintaxe (<code>RegexSyntaxHighlighter</code>) e o editor de texto otimizado (<code>EditorArea</code>).</li>
        <li><strong>Execução em Background e Janela Principal:</strong> Implementação do padrão <code>QRunnable</code>/<code>QSignals</code> para processamento paralelo e estruturação da janela principal (<code>RegexTranslatorApp</code>) com gerenciamento de layout e tema visual customizado.</li>
    </ol>

    <hr>

    <h2>🚀 Como Executar</h2>

    <h3>Pré-requisitos</h3>
    <p>Certifique-se de ter o Python 3 instalado em seu ambiente. Instale a única dependência necessária executando o comando abaixo no terminal:</p>
    <pre><code>pip install PySide6</code></pre>

    <h3>Execução</h3>
    <p>Com a dependência instalada, execute o script diretamente pelo terminal:</p>
    <pre><code>python regex_translator.py</code></pre>
</div>

</body>
</html>
