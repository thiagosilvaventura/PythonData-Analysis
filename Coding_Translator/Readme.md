<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Coding Translator – README</title>
<style>
  :root { --bg:#ffffff; --fg:#1c2330; --muted:#5b667a; --line:#dde2ea; --code:#f2f5f9; --accent:#2864b5; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#11151d; --fg:#e5eaf2; --muted:#8e9bb0; --line:#2b3647; --code:#19212d; --accent:#7fa9e8; }
  }
  body { background:var(--bg); color:var(--fg); font:16px/1.6 system-ui, "Segoe UI", sans-serif; margin:0; }
  main { max-width:760px; margin:0 auto; padding:40px 20px 56px; }
  h1 { margin:0 0 4px; letter-spacing:1px; }
  h2 { margin:32px 0 8px; font-size:1.15rem; color:var(--accent); border-bottom:1px solid var(--line); padding-bottom:4px; }
  p, li { margin:6px 0; }
  .sub { color:var(--muted); margin:0; }
  code, pre { background:var(--code); border-radius:6px; font:14px/1.5 Consolas, Menlo, monospace; }
  code { padding:2px 6px; }
  pre { padding:12px 14px; overflow-x:auto; }
  table { border-collapse:collapse; width:100%; }
  td, th { border:1px solid var(--line); padding:6px 10px; text-align:left; }
  th { background:var(--code); }
  footer { margin-top:40px; color:var(--muted); font-size:12px; text-align:center; }
</style>
</head>
<body>
<main>
  <h1>Coding Translator</h1>
  <p class="sub">Tradutor de lógica computacional e transpilador de código. 100% offline, sem APIs.</p>

  <h2>Instalação</h2>
  <pre>pip install PySide6
python coding_translator.py</pre>
  <p>Requer Python 3.9 ou superior.</p>

  <h2>Aba 1 – Lógica Computacional</h2>
  <p>Traduz fórmulas entre <strong>Matemática Discreta</strong>, <strong>Portas Lógicas</strong>, <strong>Python</strong> e <strong>C/C++</strong>, uma fórmula por linha. A origem pode ser detectada automaticamente.</p>
  <ul>
    <li>Operadores: <code>AND OR NOT XOR NAND NOR XNOR IMPLIES IFF</code>, símbolos <code>∧ ∨ ¬ ⊕ → ↔</code>, <code>&amp;&amp; || !</code> e <code>-&gt; &lt;-&gt;</code>.</li>
    <li>Resultado, <strong>tabela-verdade</strong> (até 10 variáveis) e <strong>análise</strong>: classificação, formas canônicas, forma mínima, árvore sintática e equivalência entre linhas.</li>
  </ul>

  <h2>Aba 2 – Tradutor de Código</h2>
  <p>Converte entre <strong>Python, JavaScript, Java, C#, C/C++ e Rust</strong>, em qualquer direção.</p>
  <ul>
    <li>Suporta funções, variáveis, <code>if/while/for</code>, listas, strings, f-strings e <code>print</code>.</li>
    <li>Trechos não suportados viram um comentário <code>TODO</code> e aparecem no painel <strong>Avisos</strong>.</li>
    <li>O resultado é gerado para C++ no caso de "C/C++".</li>
  </ul>

  <h2>Atalhos</h2>
  <table>
    <tr><th>Ação</th><th>Atalho</th></tr>
    <tr><td>Traduzir</td><td><code>F5</code> ou <code>Ctrl+Enter</code></td></tr>
    <tr><td>Importar / Exportar</td><td><code>Ctrl+O</code> / <code>Ctrl+S</code></td></tr>
    <tr><td>Copiar resultado</td><td><code>Ctrl+Shift+C</code></td></tr>
    <tr><td>Limpar</td><td><code>Ctrl+L</code></td></tr>
    <tr><td>Trocar de aba</td><td><code>Ctrl+1</code> / <code>Ctrl+2</code></td></tr>
  </table>
  <p>Também é possível arrastar um arquivo para o editor de origem.</p>



  <footer>created by Thiago Ventura</footer>
</main>
</body>
</html>
