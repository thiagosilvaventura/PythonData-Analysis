import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="Automotive Intelligence Platform",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded",
)

COORDS_MAP = {
    "SP": [-23.5505, -46.6333], "RJ": [-22.9068, -43.1729],
    "MG": [-18.5122, -44.5550], "BA": [-12.9714, -38.5014],
    "PR": [-25.2521, -52.0215], "RS": [-30.0346, -51.2177],
    "PE": [-8.0476, -34.8770], "CE": [-3.7172, -38.5433],
    "SC": [-27.5954, -48.5480], "CA": [36.7783, -119.4179],
    "NY": [40.7128, -74.0060], "TX": [31.9686, -99.9018],
    "FL": [27.9944, -81.7603], "IL": [40.0000, -89.0000],
}

PLOT_TEMPLATE = "plotly_dark"


def brl(value):
    if pd.isna(value):
        return "—"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def integer(value):
    return f"{int(round(value)):,}".replace(",", ".")


def pct(value):
    return f"{value:.1f}%".replace(".", ",")


def get_lat(state):
    return COORDS_MAP.get(state, [np.nan, np.nan])[0]


def get_lon(state):
    return COORDS_MAP.get(state, [np.nan, np.nan])[1]


# ============================================================
# DATA / QUALITY
# ============================================================
@st.cache_data(show_spinner=False)
def load_and_validate_data(uploaded_file):
    df = pd.read_excel(uploaded_file)

    cols = {
        "state": "Estado" if "Estado" in df.columns else "State",
        "income": "Renda Mensal (R$)" if "Renda Mensal (R$)" in df.columns else "Monthly Income (USD)",
        "age": "Idade" if "Idade" in df.columns else "Age",
        "gender": "Sexo" if "Sexo" in df.columns else "Gender",
        "vehicle": "Veículo" if "Veículo" in df.columns else "Vehicle",
        "part": "Componente do Veículo" if "Componente do Veículo" in df.columns else "Car Part",
        "education": "Escolaridade" if "Escolaridade" in df.columns else "Education",
        "marital": "Estado Civil" if "Estado Civil" in df.columns else "Marital Status",
    }

    if "Valor do Componente (R$)" in df.columns:
        cols["price"] = "Valor do Componente (R$)"
    elif "Valor (R$)" in df.columns:
        cols["price"] = "Valor (R$)"
    else:
        cols["price"] = "Part Price (USD)"

    # Date support: use an existing date column when available.
    # Never fabricate dates.
    date_candidates = ["Date", "Data", "Data da Venda", "Sale Date", "Purchase Date"]
    date_col = next((c for c in date_candidates if c in df.columns), None)
    cols["date"] = date_col
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    required = [
        cols["state"], cols["income"], cols["age"], cols["gender"],
        cols["vehicle"], cols["part"], cols["education"], cols["marital"],
        cols["price"],
    ]
    missing_required = [c for c in required if c not in df.columns]
    if missing_required:
        raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(missing_required)}")

    numeric_cols = [cols["income"], cols["age"], cols["price"]]
    if "Número de Filhos" in df.columns:
        cols["children"] = "Número de Filhos"
        numeric_cols.append(cols["children"])
    elif "Children" in df.columns:
        cols["children"] = "Children"
        numeric_cols.append(cols["children"])
    else:
        cols["children"] = None

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "ID" not in df.columns:
        df["ID"] = np.arange(1, len(df) + 1)

    dq = {
        "total_rows": len(df),
        "columns": len(df.columns),
        "missing_values": int(df.isna().sum().sum()),
        "duplicates": int(df.duplicated().sum()),
        "invalid_dates": int(df[cols["date"]].isna().sum()) if cols["date"] else None,
        "date_available": bool(cols["date"]),
    }

    return df, cols, dq


def init_state(df, cols):
    defaults = {
        "f_date": (
            df[cols["date"]].dropna().min().date(),
            df[cols["date"]].dropna().max().date(),
        ) if cols["date"] and df[cols["date"]].notna().any() else None,
        "f_age": (int(df[cols["age"]].min()), int(df[cols["age"]].max())),
        "f_income": (float(df[cols["income"]].min()), float(df[cols["income"]].max())),
        "f_gender": sorted(df[cols["gender"]].dropna().unique().tolist()),
        "f_marital": sorted(df[cols["marital"]].dropna().unique().tolist()),
        "f_education": sorted(df[cols["education"]].dropna().unique().tolist()),
        "f_state": sorted(df[cols["state"]].dropna().unique().tolist()),
        "f_vehicle": sorted(df[cols["vehicle"]].dropna().unique().tolist()),
        "f_part": sorted(df[cols["part"]].dropna().unique().tolist()),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_filters(df, cols):
    if cols["date"] and df[cols["date"]].notna().any():
        st.session_state["f_date"] = (
            df[cols["date"]].dropna().min().date(),
            df[cols["date"]].dropna().max().date(),
        )
    else:
        st.session_state["f_date"] = None

    st.session_state["f_age"] = (int(df[cols["age"]].min()), int(df[cols["age"]].max()))
    st.session_state["f_income"] = (float(df[cols["income"]].min()), float(df[cols["income"]].max()))
    st.session_state["f_gender"] = sorted(df[cols["gender"]].dropna().unique().tolist())
    st.session_state["f_marital"] = sorted(df[cols["marital"]].dropna().unique().tolist())
    st.session_state["f_education"] = sorted(df[cols["education"]].dropna().unique().tolist())
    st.session_state["f_state"] = sorted(df[cols["state"]].dropna().unique().tolist())
    st.session_state["f_vehicle"] = sorted(df[cols["vehicle"]].dropna().unique().tolist())
    st.session_state["f_part"] = sorted(df[cols["part"]].dropna().unique().tolist())


def apply_filters(df, cols):
    mask = (
        df[cols["age"]].between(*st.session_state["f_age"]) &
        df[cols["income"]].between(*st.session_state["f_income"]) &
        df[cols["gender"]].isin(st.session_state["f_gender"]) &
        df[cols["marital"]].isin(st.session_state["f_marital"]) &
        df[cols["education"]].isin(st.session_state["f_education"]) &
        df[cols["state"]].isin(st.session_state["f_state"]) &
        df[cols["vehicle"]].isin(st.session_state["f_vehicle"]) &
        df[cols["part"]].isin(st.session_state["f_part"])
    )

    if cols["date"] and st.session_state["f_date"]:
        d = df[cols["date"]].dt.date
        mask &= d.between(st.session_state["f_date"][0], st.session_state["f_date"][1])

    return df.loc[mask].copy()


# ============================================================
# ADVANCED ANALYTICS
# ============================================================
def correlation_frame(df, cols):
    numeric = {
        "Idade": cols["age"],
        "Renda": cols["income"],
        "Valor Componente": cols["price"],
    }

    if cols["children"]:
        numeric["Filhos"] = cols["children"]

    return df[list(numeric.values())].rename(
        columns={v: k for k, v in numeric.items()}
    ).corr()


def regression_model(df, cols):
    variables = [cols["age"], cols["price"]]
    labels = ["Idade", "Valor Componente"]

    if cols["children"]:
        variables.append(cols["children"])
        labels.append("Número de Filhos")

    work = df[[cols["income"], *variables]].dropna()

    if len(work) < 10:
        return None

    X = np.column_stack([
        np.ones(len(work)),
        work[variables].to_numpy(dtype=float)
    ])
    y = work[cols["income"]].to_numpy(dtype=float)

    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ beta
    residuals = y - pred

    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot else np.nan

    n, p = X.shape
    adj_r2 = (
        1 - (1 - r2) * (n - 1) / (n - p - 1)
        if n > p + 1 else np.nan
    )

    mse = ss_res / max(n - p, 1)
    cov = mse * np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.maximum(np.diag(cov), 0))
    tvals = beta / np.where(se == 0, np.nan, se)
    pvals = 2 * stats.t.sf(np.abs(tvals), df=max(n - p, 1))

    coef = pd.DataFrame({
        "Variável": ["Intercepto"] + labels,
        "Coeficiente": beta,
        "Erro padrão": se,
        "t": tvals,
        "p-value": pvals,
    })

    return {
        "coef": coef,
        "r2": r2,
        "adj_r2": adj_r2,
        "n": n,
    }


def statistical_summary(df, cols):
    numeric = [
        ("Idade", cols["age"]),
        ("Renda", cols["income"]),
        ("Valor Componente", cols["price"]),
    ]

    if cols["children"]:
        numeric.append(("Número de Filhos", cols["children"]))

    rows = []

    for label, col in numeric:
        s = pd.to_numeric(df[col], errors="coerce").dropna()

        if len(s) == 0:
            continue

        rows.append({
            "Variável": label,
            "N": len(s),
            "Média": s.mean(),
            "Mediana": s.median(),
            "Desvio Padrão": s.std(),
            "CV %": s.std() / s.mean() * 100 if s.mean() else np.nan,
            "Assimetria": s.skew(),
            "Curtose": s.kurtosis(),
            "P25": s.quantile(.25),
            "P75": s.quantile(.75),
            "Mínimo": s.min(),
            "Máximo": s.max(),
        })

    return pd.DataFrame(rows)


# ============================================================
# CHART HELPERS
# ============================================================
def polish(fig, height=400):
    fig.update_layout(
        template=PLOT_TEMPLATE,
        height=height,
        margin=dict(l=20, r=20, t=55, b=20),
        legend_title_text="",
    )
    return fig


def show(fig, height=400):
    st.plotly_chart(
        polish(fig, height),
        use_container_width=True,
        theme=None,
    )


# ============================================================
# KPI
# ============================================================
def render_kpis(df, cols):
    cards = st.columns(6)

    cards[0].metric("Clientes", integer(len(df)))
    cards[1].metric("Receita Total", brl(df[cols["price"]].sum()))
    cards[2].metric("Ticket Médio", brl(df[cols["price"]].mean()))
    cards[3].metric("Renda Média", brl(df[cols["income"]].mean()))
    cards[4].metric("Renda Mediana", brl(df[cols["income"]].median()))
    cards[5].metric("Idade Média", f"{df[cols['age']].mean():.1f} anos")


# ============================================================
# VIEWS
# ============================================================
def view_executive(df, cols):
    st.subheader("📊 Executive Overview")
    render_kpis(df, cols)
    st.divider()

    c1, c2 = st.columns([1.35, 1])

    with c1:
        st.markdown("#### 📍 Receita por Estado")

        state = df.groupby(cols["state"]).agg(
            Receita=(cols["price"], "sum"),
            Clientes=("ID", "count"),
            Ticket=(cols["price"], "mean"),
        ).reset_index().sort_values("Receita", ascending=False)

        fig = px.bar(
            state,
            x=cols["state"],
            y="Receita",
            text_auto=".2s",
            hover_data=["Clientes", "Ticket"],
            title="Receita acumulada por estado",
        )
        show(fig)

    with c2:
        st.markdown("#### 👥 Clientes por Estado")

        state2 = state.sort_values("Clientes", ascending=False)

        fig = px.bar(
            state2,
            x=cols["state"],
            y="Clientes",
            text_auto=True,
            title="Distribuição da base de clientes",
        )
        show(fig)

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 🔬 Renda × Idade")

        fig = px.scatter(
            df,
            x=cols["age"],
            y=cols["income"],
            color=cols["gender"],
            size=cols["price"],
            hover_data=[cols["vehicle"], cols["state"], cols["price"]],
                        title="Renda × idade — tamanho = valor do componente",
        )
        show(fig)

    with c2:
        st.markdown("#### 🚗 Top Veículos")

        vehicle = df.groupby(cols["vehicle"]).agg(
            Clientes=("ID", "count"),
            Receita=(cols["price"], "sum"),
        ).reset_index().sort_values("Clientes", ascending=False)

        fig = px.bar(
            vehicle.head(10).sort_values("Clientes"),
            x="Clientes",
            y=cols["vehicle"],
            orientation="h",
            text_auto=True,
            color="Receita",
            title="Top 10 veículos por quantidade",
        )
        show(fig)

    if cols["date"]:
        st.markdown("#### 📅 Evolução Temporal")

        temporal_base = df.dropna(subset=[cols["date"]]).copy()

        if not temporal_base.empty:
            temporal = (
                temporal_base
                .groupby(temporal_base[cols["date"]].dt.to_period("M"))
                .agg(
                    Receita=(cols["price"], "sum"),
                    Vendas=("ID", "count"),
                )
                .reset_index()
            )

            temporal["Data"] = temporal.iloc[:, 0].dt.to_timestamp()

            fig = px.line(
                temporal,
                x="Data",
                y=["Receita", "Vendas"],
                markers=True,
                title="Evolução mensal de receita e volume",
            )
            show(fig)
    else:
        st.info(
            "Análise temporal preparada, mas nenhuma coluna Date/Data "
            "foi detectada nesta base."
        )

    st.markdown("#### 💡 Estatística descritiva rápida")

    income = df[cols["income"]].dropna()

    q1, q2, q3, q4 = st.columns(4)

    q1.metric("Desvio padrão da renda", brl(income.std()))
    q2.metric("Coeficiente de variação", pct(income.std() / income.mean() * 100))
    q3.metric("Assimetria", f"{income.skew():.2f}")
    q4.metric("Curtose", f"{income.kurtosis():.2f}")


def view_customer(df, cols):
    st.subheader("👤 Customer Analytics")
    render_kpis(df, cols)
    st.divider()

    c1, c2, c3 = st.columns(3)

    with c1:
        fig = px.histogram(
            df,
            x=cols["age"],
            nbins=15,
            marginal="box",
            title="Distribuição de idade",
        )
        show(fig, 360)

    with c2:
        fig = px.histogram(
            df,
            x=cols["income"],
            nbins=20,
            marginal="box",
            title="Distribuição de renda",
        )
        show(fig, 360)

    with c3:
        fig = px.histogram(
            df,
            x=cols["price"],
            nbins=20,
            marginal="box",
            title="Distribuição do valor do componente",
        )
        show(fig, 360)

    c1, c2 = st.columns(2)

    with c1:
        fig = px.box(
            df,
            x=cols["education"],
            y=cols["income"],
            color=cols["education"],
            title="Renda por nível de escolaridade",
        )
        fig.update_xaxes(tickangle=-30)
        show(fig, 430)

    with c2:
        fig = px.violin(
            df,
            x=cols["gender"],
            y=cols["income"],
            box=True,
            points="outliers",
            color=cols["gender"],
            title="Distribuição de renda por sexo",
        )
        show(fig, 430)

    c1, c2 = st.columns(2)

    with c1:
        ct = pd.crosstab(df[cols["gender"]], df[cols["marital"]])

        fig = px.bar(
            ct,
            barmode="group",
            title="Estado civil por sexo",
        )
        show(fig)

    with c2:
        fig = px.scatter(
            df,
            x=cols["income"],
            y=cols["price"],
            color=cols["education"],
            size=cols["age"],
            hover_data=[cols["vehicle"], cols["state"]],
            title="Renda × valor do componente",
        )
        show(fig)

    st.markdown("#### 📐 Matriz de Correlação")

    corr = correlation_frame(df, cols)

    fig = px.imshow(
        corr,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        title="Pearson correlation matrix",
    )
    show(fig, 450)

    st.markdown("#### 🧪 Estatística Descritiva Avançada")

    summary = statistical_summary(df, cols)

    st.dataframe(
        summary.style.format({
            "Média": brl,
            "Mediana": brl,
            "Desvio Padrão": brl,
            "CV %": lambda x: f"{x:.2f}%",
            "Assimetria": "{:.3f}",
            "Curtose": "{:.3f}",
            "P25": brl,
            "P75": brl,
            "Mínimo": brl,
            "Máximo": brl,
        }),
        use_container_width=True,
    )


def view_vehicle(df, cols):
    st.subheader("🚗 Vehicle & Parts Analytics")
    render_kpis(df, cols)
    st.divider()

    max_n = min(10, df[cols["vehicle"]].nunique())

    top_n = st.slider(
        "Número de veículos no ranking/heatmap",
        5,
        max_n,
        max_n,
    )

    top_vehicles = (
        df[cols["vehicle"]]
        .value_counts()
        .head(top_n)
        .index
    )

    filtered_vehicle = df[df[cols["vehicle"]].isin(top_vehicles)]

    heat = pd.crosstab(
        filtered_vehicle[cols["state"]],
        filtered_vehicle[cols["vehicle"]],
    )

    c1, c2 = st.columns(2)

    with c1:
        fig = px.imshow(
            heat,
            text_auto=True,
            aspect="auto",
            color_continuous_scale="Blues",
            title="Penetração de veículos por estado",
        )
        show(fig, 430)

    with c2:
        ranking = (
            df.groupby(cols["vehicle"])
            .agg(
                Vendas=("ID", "count"),
                Receita=(cols["price"], "sum"),
                Ticket=(cols["price"], "mean"),
            )
            .reset_index()
            .sort_values("Receita", ascending=True)
            .tail(top_n)
        )

        fig = px.bar(
            ranking,
            x="Receita",
            y=cols["vehicle"],
            orientation="h",
            color="Ticket",
            text_auto=".2s",
            hover_data=["Vendas", "Ticket"],
            title="Ranking de veículos por receita",
        )
        show(fig, 430)

    c1, c2 = st.columns(2)

    with c1:
        parts = (
            df.groupby(cols["part"])
            .agg(
                Quantidade=("ID", "count"),
                Receita=(cols["price"], "sum"),
            )
            .reset_index()
            .sort_values("Quantidade", ascending=False)
        )

        fig = px.bar(
            parts,
            x=cols["part"],
            y="Quantidade",
            color="Receita",
            text_auto=True,
            title="Volume por componente",
        )
        fig.update_xaxes(tickangle=-35)
        show(fig, 430)

    with c2:
        fig = px.scatter(
            df,
            x=cols["age"],
            y=cols["price"],
            color=cols["vehicle"],
            size=cols["income"],
            hover_data=[cols["part"], cols["state"]],
            title="Idade × valor do componente × veículo",
        )
        show(fig, 430)

    st.markdown("#### 🧊 Análise 3D — Perfil Demográfico, Renda e Valor")

    fig3d = px.scatter_3d(
        df,
        x=cols["age"],
        y=cols["income"],
        z=cols["price"],
        color=cols["vehicle"],
        symbol=cols["gender"],
        hover_data=[cols["state"], cols["part"]],
        title="Idade × renda × valor do componente",
    )

    fig3d.update_layout(height=650)
    st.plotly_chart(fig3d, use_container_width=True)

    with st.expander("📈 Série temporal 3D — exploração avançada"):
        if cols["date"]:
            temporal_base = df.dropna(subset=[cols["date"]]).copy()

            if not temporal_base.empty:
                temporal = (
                    temporal_base
                    .groupby(temporal_base[cols["date"]].dt.date)
                    .agg(
                        Quantidade=("ID", "count"),
                        Valor_Total=(cols["price"], "sum"),
                    )
                    .reset_index()
                )

                temporal.rename(
                    columns={temporal.columns[0]: "Data"},
                    inplace=True,
                )

                fig = px.line_3d(
                    temporal,
                    x="Data",
                    y="Quantidade",
                    z="Valor_Total",
                    markers=True,
                    title="Volume × receita × tempo",
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )
        else:
            st.info("Nenhuma coluna de data foi encontrada na base carregada.")


def view_stats(df, cols):
    st.subheader("🧠 Advanced Statistics")
    st.caption(
        "Análises inferenciais, multivariadas e de segmentação "
        "calculadas exclusivamente sobre os dados filtrados."
    )

    render_kpis(df, cols)
    st.divider()

    numeric = {
        "Idade": cols["age"],
        "Renda": cols["income"],
        "Valor Componente": cols["price"],
    }

    if cols["children"]:
        numeric["Filhos"] = cols["children"]

    st.markdown("#### 🔗 Pearson × Spearman")

    rows = []
    items = list(numeric.items())

    for i, (a, ca) in enumerate(items):
        for b, cb in items[i + 1:]:
            pair = df[[ca, cb]].dropna()

            if len(pair) >= 3:
                pearson_r, pearson_p = stats.pearsonr(
                    pair[ca],
                    pair[cb],
                )

                spearman_r, spearman_p = stats.spearmanr(
                    pair[ca],
                    pair[cb],
                )

                rows.append({
                    "Variáveis": f"{a} × {b}",
                    "Pearson r": pearson_r,
                    "Pearson p-value": pearson_p,
                    "Spearman ρ": spearman_r,
                    "Spearman p-value": spearman_p,
                    "N": len(pair),
                })

    corr_tests = pd.DataFrame(rows)

    st.dataframe(
        corr_tests.style.format({
            "Pearson r": "{:.3f}",
            "Pearson p-value": "{:.4f}",
            "Spearman ρ": "{:.3f}",
            "Spearman p-value": "{:.4f}",
        }),
        use_container_width=True,
    )

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 📊 Renda por escolaridade — ANOVA")

        groups = [
            g[cols["income"]].dropna().values
            for _, g in df.groupby(cols["education"])
            if len(g[cols["income"]].dropna()) >= 2
        ]

        if len(groups) >= 2:
            f_stat, p_value = stats.f_oneway(*groups)

            st.metric("F-statistic", f"{f_stat:.3f}")
            st.metric("p-value", f"{p_value:.5f}")

            st.caption(
                "O teste avalia se pelo menos uma média de renda "
                "difere entre os grupos de escolaridade."
            )
        else:
            st.info("Dados insuficientes para ANOVA.")

    with c2:
        st.markdown("#### 🧮 Regressão linear multivariada")

        model = regression_model(df, cols)

        if model:
            m1, m2, m3 = st.columns(3)

            m1.metric("R²", f"{model['r2']:.3f}")
            m2.metric("R² ajustado", f"{model['adj_r2']:.3f}")
            m3.metric("Observações", integer(model["n"]))

            st.dataframe(
                model["coef"].style.format({
                    "Coeficiente": "{:.3f}",
                    "Erro padrão": "{:.3f}",
                    "t": "{:.3f}",
                    "p-value": "{:.5f}",
                }),
                use_container_width=True,
            )
        else:
            st.info("Dados insuficientes para regressão.")

    st.markdown("#### 🚨 Outliers estatísticos — IQR")

    outlier_rows = []

    for label, col in numeric.items():
        s = df[col].dropna()

        q1 = s.quantile(.25)
        q3 = s.quantile(.75)
        iqr = q3 - q1

        low = q1 - 1.5 * iqr
        high = q3 + 1.5 * iqr

        count = int(((s < low) | (s > high)).sum())

        outlier_rows.append({
            "Variável": label,
            "Q1": q1,
            "Q3": q3,
            "Limite inferior": low,
            "Limite superior": high,
            "Outliers": count,
            "% Outliers": count / len(s) * 100,
        })

    outliers = pd.DataFrame(outlier_rows)

    st.dataframe(
        outliers.style.format({
            "Q1": "{:.2f}",
            "Q3": "{:.2f}",
            "Limite inferior": "{:.2f}",
            "Limite superior": "{:.2f}",
            "% Outliers": "{:.2f}%",
        }),
        use_container_width=True,
    )

    st.markdown("#### 🧩 Segmentação estatística — K-Means")

    features = [
        cols["age"],
        cols["income"],
        cols["price"],
    ]

    if cols["children"]:
        features.append(cols["children"])

    work = df[features].dropna().copy()

    if len(work) >= 20:
        k = st.slider(
            "Número de clusters",
            2,
            min(6, len(work) // 10),
            3,
        )

        scaled = StandardScaler().fit_transform(work)

        km = KMeans(
            n_clusters=k,
            random_state=42,
            n_init=20,
        )

        work["Cluster"] = km.fit_predict(scaled).astype(str)

        profile = (
            work
            .groupby("Cluster")[features]
            .mean()
            .round(2)
        )

        st.dataframe(
            profile,
            use_container_width=True,
        )

        fig = px.scatter(
            work,
            x=cols["age"],
            y=cols["income"],
            color="Cluster",
            size=cols["price"],
            hover_data=[cols["price"]],
            title="Clusters de clientes — idade × renda × valor",
        )

        show(fig, 480)
    else:
        st.info("Dados insuficientes para clustering.")


def view_data(df, cols, dq):
    st.subheader("🗃️ Data Explorer & Data Quality")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Registros", integer(len(df)))
    c2.metric("Colunas", integer(len(df.columns)))
    c3.metric("Nulos", integer(int(df.isna().sum().sum())))
    c4.metric("Duplicados", integer(int(df.duplicated().sum())))

    if cols["date"] and df[cols["date"]].notna().any():
        c5, c6 = st.columns(2)

        c5.metric(
            "Data inicial",
            df[cols["date"]].min().strftime("%d/%m/%Y"),
        )

        c6.metric(
            "Data final",
            df[cols["date"]].max().strftime("%d/%m/%Y"),
        )
    else:
        st.warning(
            "A base carregada não possui uma coluna Date/Data reconhecida. "
            "Nenhuma data foi criada artificialmente."
        )

    st.divider()

    st.markdown("#### Dados filtrados")

    st.dataframe(
        df,
        use_container_width=True,
        height=500,
    )

    csv = df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "📥 Exportar dados filtrados (CSV)",
        csv,
        "dados_filtrados.csv",
        "text/csv",
    )


# ============================================================
# MAIN
# ============================================================
st.sidebar.title("📁 Fonte de Dados")

uploaded_file = st.sidebar.file_uploader(
    "Upload Excel (.xlsx)",
    type=["xlsx"],
    help="Carregue a base de dados para análise.",
)

if uploaded_file:
    try:
        df_raw, col_map, dq = load_and_validate_data(uploaded_file)
        init_state(df_raw, col_map)
    except Exception as exc:
        st.error(f"Não foi possível carregar a base: {exc}")
        st.stop()

    st.sidebar.divider()
    st.sidebar.subheader("🧭 Navegação")

    page = st.sidebar.radio(
        "Visão",
        [
            "Customer Analytics",
            "Vehicle Analytics",
            "Advanced Statistics",
            "Data Explorer",
        ],
        label_visibility="collapsed",
    )

    st.sidebar.divider()
    st.sidebar.subheader("🎛️ Filtros Globais")

    if st.sidebar.button(
        "🔄 Resetar filtros",
        use_container_width=True,
    ):
        reset_filters(df_raw, col_map)
        st.rerun()

    if col_map["date"] and df_raw[col_map["date"]].notna().any():
        date_val = st.sidebar.date_input(
            "🗓 Período",
            value=st.session_state["f_date"],
        )

        if isinstance(date_val, tuple) and len(date_val) == 2:
            st.session_state["f_date"] = date_val

    with st.sidebar.expander("👤 Demografia", expanded=True):
        st.session_state["f_age"] = st.slider(
            "Idade",
            int(df_raw[col_map["age"]].min()),
            int(df_raw[col_map["age"]].max()),
            st.session_state["f_age"],
        )

        st.session_state["f_gender"] = st.multiselect(
            "Sexo",
            sorted(df_raw[col_map["gender"]].dropna().unique()),
            st.session_state["f_gender"],
        )

        st.session_state["f_marital"] = st.multiselect(
            "Estado Civil",
            sorted(df_raw[col_map["marital"]].dropna().unique()),
            st.session_state["f_marital"],
        )

        st.session_state["f_education"] = st.multiselect(
            "Escolaridade",
            sorted(df_raw[col_map["education"]].dropna().unique()),
            st.session_state["f_education"],
        )

    with st.sidebar.expander("💰 Geografia & Finanças"):
        st.session_state["f_income"] = st.slider(
            "Renda mensal",
            float(df_raw[col_map["income"]].min()),
            float(df_raw[col_map["income"]].max()),
            st.session_state["f_income"],
        )

        st.session_state["f_state"] = st.multiselect(
            "Estado",
            sorted(df_raw[col_map["state"]].dropna().unique()),
            st.session_state["f_state"],
        )

    with st.sidebar.expander("🚗 Produto"):
        st.session_state["f_vehicle"] = st.multiselect(
            "Veículo",
            sorted(df_raw[col_map["vehicle"]].dropna().unique()),
            st.session_state["f_vehicle"],
        )

        st.session_state["f_part"] = st.multiselect(
            "Componente",
            sorted(df_raw[col_map["part"]].dropna().unique()),
            st.session_state["f_part"],
        )

    df_filtered = apply_filters(df_raw, col_map)

    st.markdown(
        f"""
        <div style="
            padding:14px 18px;
            border-radius:10px;
            border-left:5px solid #4DA3FF;
            background:rgba(255,255,255,.04);
            margin-bottom:18px;
        ">
            <div style="font-size:1.35rem;font-weight:700;">
                🚘 Automotive Intelligence Platform
            </div>
            <div style="opacity:.70;font-size:.85rem;">
                Fonte: {uploaded_file.name} · {len(df_filtered):,} registros filtrados
            </div>
        </div>
        """.replace(",", "."),
        unsafe_allow_html=True,
    )

    if df_filtered.empty:
        st.warning(
            "Nenhum registro corresponde aos filtros atuais. "
            "Utilize 'Resetar filtros'."
        )
    else:
        if page == "Customer Analytics":
            view_customer(df_filtered, col_map)

        elif page == "Vehicle Analytics":
            view_vehicle(df_filtered, col_map)

        elif page == "Advanced Statistics":
            view_stats(df_filtered, col_map)

        elif page == "Data Explorer":
            view_data(df_filtered, col_map, dq)

else:
    st.markdown(
        """
        <div style="text-align:center;margin-top:100px;">
            <h1>🚘 Automotive Intelligence Platform</h1>
            <p style="opacity:.65;">
                Carregue a base Excel na barra lateral para iniciar a análise.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
