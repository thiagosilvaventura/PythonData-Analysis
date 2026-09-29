# Python-Data-Analysis

# 🚗 Veículos Streamlit — Dashboard de Análise Automotiva

Aplicação desenvolvida em Python e Streamlit para exploração, tratamento e análise de uma base de dados fictícia relacionada a clientes, características demográficas, veículos e componentes automotivos.

O projeto combina recursos de exploração de dados, visualização, análise estatística e segmentação em uma única interface. A aplicação permite trabalhar com diferentes dimensões da base sem a necessidade de executar consultas ou alterar o código para cada análise.

---

## 1. Objetivo e problematização

Bases de dados que combinam informações cadastrais, características demográficas e informações relacionadas a produtos podem apresentar diferentes perspectivas de análise. Uma mesma variável pode assumir comportamentos distintos quando observada em conjunto com idade, renda, localização, escolaridade, estado civil, veículo ou componente.

Neste projeto, o problema é transformar uma base tabular com diferentes dimensões em um ambiente de exploração que permita:

- identificar padrões de distribuição dos dados;
- comparar grupos de clientes;
- analisar relações entre características demográficas e renda;
- observar a distribuição de veículos e componentes;
- identificar diferenças entre regiões;
- investigar relações entre variáveis numéricas;
- localizar possíveis valores discrepantes;
- testar relações estatísticas entre grupos;
- segmentar registros com características semelhantes;
- avaliar aspectos básicos da qualidade da base.

A aplicação foi estruturada para que essas análises possam ser realizadas sobre o **conjunto de dados atualmente selecionado pelo usuário**, em vez de trabalhar exclusivamente sobre a base completa.

Isso permite, por exemplo, analisar simultaneamente um determinado estado, faixa etária, sexo, nível de escolaridade, veículo ou faixa de renda e observar como as distribuições e métricas se comportam dentro desse recorte.

### Problema de usabilidade

Uma análise desse tipo pode exigir a combinação de diferentes ferramentas: planilhas para filtros, consultas para agregações, bibliotecas estatísticas para testes e ferramentas de visualização para gráficos. Quando essas etapas são executadas separadamente, torna-se necessário repetir filtros, exportar dados e reconstruir análises para cada novo recorte.

A aplicação concentra essas etapas em uma interface única.

O usuário pode:

1. carregar a base de dados;
2. aplicar filtros sobre diferentes dimensões;
3. visualizar os indicadores correspondentes ao subconjunto selecionado;
4. comparar distribuições por meio de diferentes tipos de gráficos;
5. executar análises estatísticas sobre os registros filtrados;
6. consultar os dados diretamente por meio do explorador;
7. exportar o subconjunto analisado quando necessário.


## 2. Arquitetura técnica e bibliotecas utilizadas

<img width="1029" height="884" alt="image" src="https://github.com/user-attachments/assets/35795741-2d66-42db-904f-40df49b297ce" />


Customer Analytics

A seção **Customer Analytics** concentra as análises relacionadas ao perfil dos registros selecionados. Os resultados são recalculados de acordo com os filtros aplicados, permitindo observar como diferentes recortes da base modificam as distribuições e relações entre as variáveis.

A página combina indicadores agregados, distribuições, comparação entre grupos, análise de relacionamento entre variáveis e estatística descritiva.

---


No início da página são apresentados seis indicadores calculados sobre o conjunto atualmente filtrado:

| Indicador | Cálculo | Finalidade |
|---|---|---|
| **Clientes** | Quantidade de registros | Mostra o tamanho do subconjunto analisado |
| **Receita Total** | Soma do valor dos componentes | Representa o valor acumulado dos registros selecionados |
| **Ticket Médio** | Média do valor dos componentes | Permite observar o valor médio por registro |
| **Renda Média** | Média da renda mensal | Representa o nível médio de renda do subconjunto |
| **Renda Mediana** | Mediana da renda mensal | Permite comparar a renda central sem depender tanto de valores extremos |
| **Idade Média** | Média da idade | Resume a faixa etária do conjunto selecionado |

Esses indicadores são apresentados utilizando **Streamlit**, enquanto os cálculos são realizados sobre o `DataFrame` filtrado utilizando **Pandas**.

<img width="1030" height="775" alt="image" src="https://github.com/user-attachments/assets/426fc980-d6c4-4c10-9cce-8e905d5c8676" />


##  Vehicle & Parts Analytics

A seção **Vehicle & Parts Analytics** desloca a análise do perfil dos clientes para as dimensões relacionadas aos veículos e componentes registrados na base.

A página combina distribuição geográfica, ranking de receita, volume de componentes, análise bivariada e visualização tridimensional. Os gráficos são construídos a partir do conjunto de dados atualmente filtrado.

---

###  Indicadores principais

A página inicia utilizando o mesmo conjunto de indicadores da análise de clientes:

- quantidade de registros;
- receita total;
- ticket médio;
- renda média;
- renda mediana;
- idade média.

Esses indicadores permitem manter uma referência quantitativa enquanto as análises específicas de veículos e componentes são realizadas.

Os valores são recalculados sobre o `DataFrame` filtrado e apresentados utilizando **Streamlit**, enquanto os cálculos são realizados com **Pandas**.

Isso permite, por exemplo, comparar os indicadores gerais antes e depois de selecionar determinados veículos, estados ou componentes nos filtros globais.

---

<img width="834" height="795" alt="image" src="https://github.com/user-attachments/assets/a7b91293-d9b9-49ff-bfe0-459593feba9b" />


## 3. Advanced Statistics

A seção **Advanced Statistics** concentra as análises estatísticas e de segmentação disponíveis na aplicação. Enquanto as views anteriores possuem foco principalmente descritivo e exploratório, esta etapa utiliza métodos estatísticos para medir associações entre variáveis, comparar grupos, estimar relações, identificar possíveis valores discrepantes e segmentar registros por similaridade.

Todas as análises são executadas sobre o conjunto de dados resultante dos filtros aplicados na interface.

---

### Indicadores principais

A página mantém os mesmos indicadores utilizados nas demais views:

| Indicador | Finalidade |
|---|---|
| **Clientes** | Quantidade de registros atualmente analisados |
| **Receita Total** | Soma dos valores dos componentes |
| **Ticket Médio** | Valor médio dos componentes |
| **Renda Média** | Média da renda mensal |
| **Renda Mediana** | Mediana da renda mensal |
| **Idade Média** | Média da idade dos registros |

Os cálculos são realizados sobre o `DataFrame` filtrado e apresentados pelo **Streamlit**.

Essa estrutura mantém os indicadores gerais disponíveis enquanto o usuário executa análises estatísticas sobre o mesmo subconjunto de dados.

---

## Pearson × Spearman

**Tipo:** Correlação estatística  
**Bibliotecas:** SciPy + Pandas + Streamlit

A primeira análise compara dois métodos de correlação aplicados às variáveis numéricas:

- **Pearson**
- **Spearman**

A tabela apresenta os coeficientes calculados para os pares de variáveis disponíveis.

### Pearson

A correlação de Pearson mede a associação **linear** entre duas variáveis numéricas.

O coeficiente varia entre `-1` e `+1`:

| Coeficiente | Interpretação |
|---:|---|
| Próximo de `+1` | Associação linear positiva |
| Próximo de `0` | Pouca ou nenhuma associação linear |
| Próximo de `-1` | Associação linear negativa |

### Spearman

A correlação de Spearman utiliza a posição relativa dos valores, trabalhando com seus rankings.

Ela pode ser utilizada para investigar relações monotônicas, inclusive quando a relação entre as variáveis não apresenta comportamento linear.

### Por que utilizar os dois métodos?

A comparação permite verificar se a associação entre duas variáveis permanece semelhante quando são utilizados métodos com características diferentes.

| Método | Mede principalmente |
|---|---|
| **Pearson** | Associação linear |
| **Spearman** | Associação monotônica baseada em rankings |

Os cálculos estatísticos são realizados pelo **SciPy**, enquanto o **Pandas** organiza as variáveis utilizadas na análise e o **Streamlit** apresenta os resultados.

---

##  Renda por escolaridade — ANOVA

**Tipo:** ANOVA de uma via  
**Biblioteca:** SciPy

A análise de **ANOVA — Analysis of Variance** é utilizada para comparar a distribuição de renda entre os diferentes grupos de escolaridade.

A estrutura da análise pode ser representada como:

```text
Escolaridade
     │
     ├── Grupo 1 → Renda
     ├── Grupo 2 → Renda
     ├── Grupo 3 → Renda
     └── ...
             ↓
           ANOVA
             ↓
      F-statistic
             +
         p-value
```

O teste avalia se existe evidência estatística de diferença entre as médias dos grupos analisados.

### F-statistic

A estatística F relaciona a variabilidade observada entre os grupos com a variabilidade existente dentro dos grupos.

### p-value

O `p-value` representa a evidência estatística contra a hipótese nula do teste.

O dashboard apresenta os valores calculados para o conjunto atualmente filtrado.

A ANOVA é utilizada como ferramenta de comparação estatística entre grupos. O resultado do teste, isoladamente, não estabelece causalidade entre escolaridade e renda.

---

## Regressão linear multivariada

**Tipo:** Regressão linear múltipla  
**Bibliotecas:** NumPy + SciPy + Pandas

A regressão linear multivariada estima uma variável dependente utilizando múltiplas variáveis explicativas.

Na implementação do dashboard, a **renda** é utilizada como variável dependente.

A estrutura pode ser representada por:

```text
Renda
  ↑
  │
  ├── Idade
  ├── Número de filhos
  └── Valor do componente
```

O modelo pode ser representado matematicamente como:

```text
y = β₀ + β₁X₁ + β₂X₂ + ... + βₙXₙ + ε
```

onde:

- `y` = variável dependente;
- `X` = variáveis explicativas;
- `β` = coeficientes estimados;
- `β₀` = intercepto;
- `ε` = erro do modelo.

### Estimação dos coeficientes

A implementação utiliza `numpy.linalg.lstsq()` para resolver o problema de mínimos quadrados:

```python
X = np.column_stack([
    np.ones(len(work)),
    work[variables].to_numpy(dtype=float)
])

y = work[cols["income"]].to_numpy(dtype=float)

beta, *_ = np.linalg.lstsq(
    X,
    y,
    rcond=None
)
```

O uso do `NumPy` permite trabalhar diretamente com a representação matricial necessária para a estimação dos coeficientes.

### Métricas do modelo

A interface apresenta informações relacionadas ao ajuste do modelo e aos coeficientes estimados.

Entre elas:

| Métrica | Finalidade |
|---|---|
| **R²** | Mede a proporção da variabilidade da variável dependente explicada pelo modelo |
| **R² ajustado** | Considera o número de variáveis utilizadas no modelo |
| **MSE** | Mede o erro quadrático médio das estimativas |
| **Coeficiente** | Valor estimado para cada variável |
| **Erro padrão** | Mede a incerteza associada ao coeficiente |
| **t** | Estatística utilizada na avaliação individual dos coeficientes |
| **p-value** | Evidência estatística associada ao coeficiente |

A análise permite observar o comportamento conjunto das variáveis utilizadas no modelo, em vez de avaliar somente pares isolados.

É importante diferenciar:

```text
Correlação
    ≠
Regressão
    ≠
Causalidade
```

A regressão utilizada no projeto é uma ferramenta de modelagem estatística aplicada à base disponível e não estabelece, isoladamente, uma relação causal entre as variáveis.

---

##  Outliers estatísticos — IQR

**Tipo:** Identificação de valores discrepantes  
**Método:** Intervalo Interquartil — IQR  
**Bibliotecas:** Pandas + NumPy

A análise de outliers utiliza o **Interquartile Range (IQR)** para identificar valores localizados fora dos limites estatísticos definidos pelos quartis.

O intervalo interquartil é calculado por:

```text
IQR = Q3 - Q1
```

Os limites utilizados são:

```text
Limite inferior = Q1 - 1.5 × IQR

Limite superior = Q3 + 1.5 × IQR
```

Valores abaixo do limite inferior ou acima do limite superior são classificados como possíveis outliers segundo esse critério.

### Informações apresentadas

A tabela apresenta informações como:

| Campo | Descrição |
|---|---|
| **Q1** | Primeiro quartil |
| **Q3** | Terceiro quartil |
| **IQR** | Intervalo interquartil |
| **Limite inferior** | Limite inferior utilizado pelo método |
| **Limite superior** | Limite superior utilizado pelo método |
| **Outliers** | Quantidade de registros fora dos limites |
| **% Outliers** | Percentual de registros classificados como outliers |

### Por que utilizar IQR?

O IQR permite analisar valores extremos utilizando os quartis da distribuição, sem depender diretamente da média e do desvio padrão.

Isso é útil para variáveis que podem apresentar distribuições assimétricas, como:

- renda;
- valor do componente;
- idade;
- número de filhos.

Um registro classificado como outlier pelo IQR não significa necessariamente que exista um erro nos dados. Significa apenas que o valor está fora dos limites definidos pelo critério estatístico utilizado.

---

##  Segmentação estatística — K-Means

**Tipo:** Clustering não supervisionado  
**Biblioteca:** Scikit-learn

A última análise da página utiliza o algoritmo **K-Means** para agrupar registros com características numéricas semelhantes.

Diferentemente da ANOVA e da regressão, o K-Means não parte de uma variável dependente ou de grupos previamente definidos.

O algoritmo procura formar grupos a partir da similaridade entre os registros.

O processo pode ser representado como:

```text
Dados numéricos
      ↓
Padronização
      ↓
Definição de K
      ↓
K-Means
      ↓
Clusters
      ↓
Perfil dos grupos
```

---

### Padronização das variáveis

Antes da aplicação do K-Means, as variáveis são padronizadas utilizando `StandardScaler`.

```python
scaler = StandardScaler()

X_scaled = scaler.fit_transform(
    work[cluster_vars]
)
```

A padronização coloca as variáveis em uma escala comparável.

Essa etapa é importante porque o K-Means utiliza distância para determinar a proximidade entre os registros. Sem padronização, uma variável com valores numericamente maiores poderia exercer influência desproporcional sobre o cálculo das distâncias.

---

### Definição do número de clusters

A interface disponibiliza um controle para selecionar a quantidade de clusters:

```text
Número de clusters
       ↓
       K
```

O usuário pode alterar o valor de `K` e observar como a segmentação dos registros muda.

O algoritmo é executado utilizando o `KMeans` do Scikit-learn:

```python
kmeans = KMeans(
    n_clusters=k,
    random_state=42,
    n_init=10
)

labels = kmeans.fit_predict(X_scaled)
```

O parâmetro `random_state=42` permite reproduzir a mesma inicialização aleatória entre execuções.

O parâmetro `n_init=10` determina o número de inicializações utilizadas pelo algoritmo antes de selecionar a solução final.

---

##  Perfil dos clusters

Depois da classificação, os registros são agrupados de acordo com o cluster atribuído.

O dashboard apresenta uma tabela com as características médias dos grupos.

A estrutura pode ser representada como:

```text
Cluster
   │
   ├── Idade média
   ├── Renda média
   └── Valor médio do componente
```

A tabela permite comparar os grupos gerados pelo algoritmo e identificar diferenças entre seus perfis numéricos.

Os clusters não correspondem a categorias previamente existentes na base. Eles são resultados do processo de agrupamento aplicado às variáveis selecionadas.

---

##  Visualização dos clusters

**Tipo:** Scatter plot  
**Bibliotecas:** Scikit-learn + Plotly Express

Após a execução do K-Means, os clusters são representados visualmente em um scatter plot.

Cada ponto representa um registro e sua cor indica o cluster atribuído.

Conceitualmente:

```text
Dados
  │
  └── K-Means
        │
        ├── Cluster 0
        ├── Cluster 1
        ├── Cluster 2
        └── ...
              ↓
        Visualização Plotly
```

A visualização permite investigar:

- concentração dos grupos;
- dispersão;
- sobreposição entre clusters;
- regiões com maior concentração de registros;
- possíveis diferenças entre os segmentos.

O **Scikit-learn** realiza o agrupamento e o **Plotly** representa graficamente o resultado.

A visualização não altera os clusters calculados pelo algoritmo; ela apenas apresenta graficamente a classificação resultante.

---

## Relação entre os métodos estatísticos

Os métodos disponíveis na página possuem finalidades diferentes:

| Método | Objetivo |
|---|---|
| **Pearson** | Medir associação linear |
| **Spearman** | Medir associação monotônica baseada em rankings |
| **ANOVA** | Comparar médias entre grupos |
| **Regressão linear** | Estimar uma variável a partir de múltiplas variáveis explicativas |
| **IQR** | Identificar possíveis valores discrepantes |
| **K-Means** | Agrupar registros por similaridade |

O fluxo analítico pode ser representado da seguinte maneira:

```text
                         Dados filtrados
                              │
              ┌───────────────┼────────────────┐
              │               │                │
              ▼               ▼                ▼
         Correlação         ANOVA         Regressão
              │               │                │
              ▼               ▼                ▼
         Associação       Grupos           Modelo
              
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
                   IQR                K-Means
                    │                   │
                    ▼                   ▼
                Outliers            Clusters
```

Cada método responde a uma questão diferente e, portanto, os resultados devem ser analisados de acordo com a finalidade específica de cada técnica.

---

##  Bibliotecas utilizadas nesta seção

| Biblioteca | Responsabilidade |
|---|---|
| **Streamlit** | Interface, indicadores, tabelas, controles e apresentação dos resultados |
| **Pandas** | Preparação, filtragem, agrupamento e organização dos dados |
| **NumPy** | Operações matriciais e cálculo da regressão por mínimos quadrados |
| **SciPy** | Correlação, ANOVA e cálculos estatísticos |
| **Scikit-learn** | Padronização das variáveis e algoritmo K-Means |
| **Plotly** | Visualização dos clusters e representação gráfica dos resultados |

A seção **Advanced Statistics** utiliza as bibliotecas de forma complementar: o **Pandas** organiza os dados, o **NumPy** executa operações numéricas, o **SciPy** fornece métodos estatísticos, o **Scikit-learn** realiza a segmentação e o **Streamlit** organiza os resultados em uma interface interativa.
