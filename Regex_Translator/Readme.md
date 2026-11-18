# Regex Translator

**Tradutor bidirecional entre Linguagem Natural e Expressões Regulares (Regex)**

O Regex Translator é uma aplicação desktop desenvolvida em Python que permite converter descrições simples em linguagem natural para expressões regulares e interpretar padrões Regex em descrições textuais em português.

Desenvolvi o projeto utilizando **PySide6** para a interface gráfica e o módulo nativo `re` para o processamento das expressões. A aplicação funciona integralmente offline, sem depender de APIs ou serviços externos.

---

## 🖥️ Interface

A aplicação possui uma interface dividida em dois painéis: entrada e saída. Essa organização permite visualizar o texto original e sua tradução simultaneamente.

- **Painel de entrada:** recebe expressões regulares ou descrições em linguagem natural.
- **Painel de saída:** apresenta o resultado da conversão.
- **Detecção automática:** identifica heurísticamente se o conteúdo informado corresponde a Regex ou linguagem natural.
- **Inversão de tradução:** permite alternar os idiomas de origem e destino.
- **Realce de sintaxe:** aplica cores diferentes aos principais elementos das expressões regulares.

---

## ⚙️ Tecnologias utilizadas

| Tecnologia | Aplicação |
|---|---|
| Python | Linguagem principal |
| PySide6 | Interface gráfica desktop |
| `re` | Processamento e substituição de padrões |
| `QSyntaxHighlighter` | Realce de sintaxe |
| `QThreadPool` | Gerenciamento de tarefas em segundo plano |
| `QTimer` | Controle do intervalo de tradução automática |
| `time` | Medição do tempo de processamento |

**Dependências:** apenas PySide6. Os demais módulos utilizados fazem parte da biblioteca padrão do Python.

---

## 🔄 Funcionamento do tradutor

Implementei dois mecanismos principais de conversão, organizados em uma classe chamada `RegexEngine`.

### 1. Regex para Linguagem Natural

O mecanismo percorre um dicionário de correspondências entre elementos de Regex e suas respectivas descrições em português.

| Expressão | Interpretação |
|---|---|
| `^` | Início da linha |
| `$` | Fim da linha |
| `\d` | Um dígito numérico |
| `\w` | Um caractere alfanumérico |
| `\s` | Um espaço em branco |
| `.*` | Qualquer texto (opcional) |
| `.` | Qualquer caractere |
| `[a-z]` | Uma letra minúscula |
| `[A-Z]` | Uma letra maiúscula |
| `[0-9]` | Um número de 0 a 9 |
| `+` | Uma ou mais vezes |
| `*` | Zero ou mais vezes |
| `?` | Opcionalmente |

A conversão utiliza substituições sucessivas por meio de `re.sub()`.

### 2. Linguagem Natural para Regex

Implementei o processo inverso utilizando um segundo dicionário de expressões linguísticas e seus respectivos padrões Regex.

| Descrição | Expressão |
|---|---|
| Início da linha | `^` |
| Fim da linha | `$` |
| Um dígito / número | `\d` |
| Letra | `[a-zA-Z]` |
| Alfanumérico | `\w` |
| Espaço | `\s` |
| Qualquer caractere | `.` |
| Qualquer coisa / texto | `.*` |
| Uma ou mais vezes | `+` |
| Zero ou mais vezes | `*` |
| Opcional / opcionalmente | `?` |

O mecanismo converte as descrições reconhecidas, remove conectivos e espaços excedentes e organiza o resultado em uma expressão regular.

**Observação:** a tradução é baseada em correspondências heurísticas. Portanto, não representa um interpretador semântico completo de linguagem natural nem garante equivalência entre todos os padrões Regex e suas descrições.

---

## 🧠 Arquitetura do projeto

Organizei o código em componentes com responsabilidades distintas:

| Componente | Responsabilidade |
|---|---|
| `RegexEngine` | Detecta a linguagem e executa as conversões |
| `TranslationResult` | Armazena o resultado, a origem detectada e o tempo de processamento |
| `RegexSyntaxHighlighter` | Identifica e colore elementos da sintaxe Regex |
| `EditorArea` | Configura os campos de edição e exibição |
| `TaskSignals` | Gerencia os sinais de conclusão e erro |
| `TranslationTask` | Executa o processamento em uma tarefa independente |
| `RegexTranslatorApp` | Controla a interface gráfica e os eventos da aplicação |

### Processamento em segundo plano

Utilizei `QRunnable` e `QThreadPool` para executar as traduções em tarefas independentes, evitando concentrar o processamento diretamente no fluxo principal da interface.

Também implementei um `QTimer` com intervalo de 400 milissegundos. Ele aguarda uma breve pausa na digitação antes de iniciar a tradução automática, reduzindo chamadas desnecessárias ao motor de processamento.

### Detecção automática

A identificação da linguagem utiliza uma análise de caracteres específicos.

Quando o conteúdo apresenta símbolos como `^`, `$`, `\`, `{}`, `[]`, `|`, `+` ou `*`, o mecanismo classifica a entrada como Regex. Caso contrário, considera o conteúdo linguagem natural.

---

## 🎨 Realce de sintaxe

Implementei um sistema de destaque visual utilizando `QSyntaxHighlighter`, com identificação de diferentes elementos das expressões regulares.

| Elemento | Cor |
|---|---|
| Âncoras | Rosa |
| Metacaracteres | Ciano |
| Classes de caracteres | Amarelo |
| Quantificadores | Verde |
| Grupos | Roxo |

A interface utiliza uma paleta baseada no tema Dracula, com fundo escuro e elementos contrastantes.

---

## 🚀 Instalação e execução

### 1. Pré-requisitos

- Python 3.9 ou superior.
- pip.

### 2. Instalação da dependência

```bash
pip install PySide6
```

### 3. Execução

Salve o script como `regex_translator.py` e execute:

```bash
python regex_translator.py
```

A janela da aplicação será inicializada diretamente pelo Python.

---

## ⌨️ Atalhos e controles

| Controle | Função |
|---|---|
| `Ctrl + L` | Limpar os campos |
| ⇄ Inverter | Inverter os idiomas de origem e destino |
| Limpar | Apagar entrada e resultado |
| Auto-detectar | Identificar automaticamente o tipo de entrada |

---

## 📂 Estrutura do projeto

```text
Regex-Translator/
│
├── regex_translator.py
└── README.md
```

---

## 📌 Características técnicas

- Conversão bidirecional entre Regex e linguagem natural.
- Processamento local e funcionamento offline.
- Detecção heurística automática da linguagem.
- Tradução automática durante a digitação.
- Processamento em segundo plano com `QThreadPool`.
- Realce de sintaxe com `QSyntaxHighlighter`.
- Suporte a múltiplas linhas.
- Medição do tempo de execução em milissegundos.
- Interface gráfica desenvolvida com PySide6.

---

**Desenvolvido em Python | PySide6 | Regex**
