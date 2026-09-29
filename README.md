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

### Controle de quantidade de veículos

Antes dos gráficos principais existe um controle deslizante para determinar quantos veículos serão considerados nas análises de ranking e distribuição geográfica.

```python
max_n = min(10, df[cols["vehicle"]].nunique())

top_n = st.slider(
    "Número de veículos no ranking/heatmap",
    5,
    max_n,
    max_n,
)



