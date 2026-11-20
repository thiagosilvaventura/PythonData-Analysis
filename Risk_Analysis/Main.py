
# ============================================================
# OPERATIONAL RISK ASSESSMENT & HEATMAP INTELLIGENCE
# LATAM Risk Management Simulation
#
# Technologies:
# Python | Pandas | NumPy | Matplotlib | Seaborn
#
# Data: 100% synthetic
# Purpose: Portfolio / Risk Management demonstration
# ============================================================

import os
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from datetime import datetime

# ============================================================
# 1. CONFIGURATION
# ============================================================

np.random.seed(42)

OUTPUT_DIR = "risk_assessment_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

COUNTRIES = [
    "Brazil",
    "Mexico",
    "Colombia",
    "Chile",
    "Argentina"
]

PROCESSES = [
    "Customer Operations",
    "Third Party Management",
    "Compliance",
    "Information Security",
    "Financial Operations",
    "Quality Assurance",
    "Technology"
]

RISK_TYPES = [
    "Operational Failure",
    "Regulatory Compliance",
    "Data Protection",
    "Fraud",
    "Process Inefficiency",
    "Third Party Dependency",
    "Internal Control Failure"
]

# Risk thresholds: configurable model assumptions
RISK_THRESHOLDS = {
    "Critical": 15,
    "High": 10,
    "Moderate": 5,
    "Low": 0
}

RISK_APPETITE = 8

# ============================================================
# 2. SCENARIO CONFIGURATION
# ============================================================

# Deliberately introduced scenario pressures.
# These are simulation assumptions, NOT real country ratings.

COUNTRY_PRESSURE = {
    "Brazil": 1.00,
    "Mexico": 1.25,
    "Colombia": 1.05,
    "Chile": 0.80,
    "Argentina": 1.10
}

PROCESS_PRESSURE = {
    "Customer Operations": 1.00,
    "Third Party Management": 1.35,
    "Compliance": 1.15,
    "Information Security": 1.10,
    "Financial Operations": 0.90,
    "Quality Assurance": 0.85,
    "Technology": 1.05
}

# ============================================================
# 3. SYNTHETIC DATA GENERATION
# ============================================================

def generate_risk_data():

    records = []
    risk_id = 1

    for country in COUNTRIES:

        for process in PROCESSES:

            for risk_type in RISK_TYPES:

                country_factor = COUNTRY_PRESSURE[country]
                process_factor = PROCESS_PRESSURE[process]

                pressure = country_factor * process_factor

                # Base probability and impact
                likelihood = np.clip(
                    round(np.random.uniform(1.5, 3.5) * pressure),
                    1, 5
                )

                impact = np.clip(
                    round(np.random.uniform(2.0, 4.0) * pressure),
                    1, 5
                )

                # Control effectiveness
                design_effectiveness = np.clip(
                    np.random.normal(
                        82 - (pressure * 8), 10
                    ),
                    30, 100
                )

                operating_effectiveness = np.clip(
                    np.random.normal(
                        78 - (pressure * 10), 12
                    ),
                    20, 100
                )

                # Weighted control effectiveness
                control_effectiveness = (
                    design_effectiveness * 0.40
                    + operating_effectiveness * 0.60
                )

                # Risk scores
                inherent_risk = likelihood * impact

                residual_risk = (
                    inherent_risk
                    * (
                        1
                        - (control_effectiveness / 100) * 0.80
                    )
                )

                # Incident history: last 90 days
                incident_rate = (
                    pressure
                    * (1 + residual_risk / 15)
                )

                incidents = np.random.poisson(incident_rate)

                # Corrective action monitoring
                overdue_actions = np.random.poisson(
                    max(0.2, pressure * 0.8)
                )

                # Recurrent incidents
                recurrence = np.random.binomial(
                    incidents,
                    min(0.8, max(0.05, pressure * 0.18))
                )

                # KRI threshold
                kri_threshold = 3

                kri_status = (
                    "BREACH"
                    if incidents > kri_threshold
                    else "NORMAL"
                )

                # Risk classification
                if residual_risk >= 15:
                    risk_level = "Critical"
                elif residual_risk >= 10:
                    risk_level = "High"
                elif residual_risk >= 5:
                    risk_level = "Moderate"
                else:
                    risk_level = "Low"

                # Escalation logic
                escalation = (
                    "YES"
                    if (
                        risk_level == "Critical"
                        or (
                            risk_level == "High"
                            and (
                                kri_status == "BREACH"
                                or overdue_actions >= 2
                            )
                        )
                    )
                    else "NO"
                )

                records.append({

                    "Risk_ID": f"RISK-{risk_id:04d}",
                    "Country": country,
                    "Process": process,
                    "Risk_Type": risk_type,

                    "Likelihood": int(likelihood),
                    "Impact": int(impact),

                    "Inherent_Risk": round(
                        inherent_risk, 2
                    ),

                    "Design_Effectiveness": round(
                        design_effectiveness, 2
                    ),

                    "Operating_Effectiveness": round(
                        operating_effectiveness, 2
                    ),

                    "Control_Effectiveness": round(
                        control_effectiveness, 2
                    ),

                    "Residual_Risk": round(
                        residual_risk, 2
                    ),

                    "Risk_Level": risk_level,

                    "Incidents_90d": incidents,
                    "Recurring_Incidents": recurrence,

                    "Overdue_Actions": overdue_actions,

                    "KRI_Threshold": kri_threshold,
                    "KRI_Status": kri_status,

                    "Escalation_Required": escalation

                })

                risk_id += 1

    return pd.DataFrame(records)


df = generate_risk_data()

# ============================================================
# 4. RISK AGGREGATION
# ============================================================

country_summary = (
    df.groupby("Country")
    .agg(
        Total_Risks=("Risk_ID", "count"),
        Average_Inherent_Risk=("Inherent_Risk", "mean"),
        Average_Residual_Risk=("Residual_Risk", "mean"),
        Average_Control_Effectiveness=(
            "Control_Effectiveness", "mean"
        ),
        Total_Incidents=("Incidents_90d", "sum"),
        Recurring_Incidents=("Recurring_Incidents", "sum"),
        Overdue_Actions=("Overdue_Actions", "sum"),
        Critical_Risks=(
            "Risk_Level",
            lambda x: (x == "Critical").sum()
        ),
        High_Risks=(
            "Risk_Level",
            lambda x: (x == "High").sum()
        ),
        KRI_Breaches=(
            "KRI_Status",
            lambda x: (x == "BREACH").sum()
        )
    )
    .reset_index()
)

process_summary = (
    df.groupby("Process")
    .agg(
        Total_Risks=("Risk_ID", "count"),
        Residual_Risk=("Residual_Risk", "mean"),
        Control_Effectiveness=(
            "Control_Effectiveness", "mean"
        ),
        Incidents=("Incidents_90d", "sum"),
        Recurrences=("Recurring_Incidents", "sum"),
        Overdue_Actions=("Overdue_Actions", "sum")
    )
    .reset_index()
    .sort_values("Residual_Risk", ascending=False)
)

# Country x Process heatmap
exposure_matrix = df.pivot_table(
    index="Country",
    columns="Process",
    values="Residual_Risk",
    aggfunc="mean"
)

# ============================================================
# 5. VISUALIZATION SETTINGS
# ============================================================

sns.set_theme(
    style="whitegrid",
    context="notebook"
)

# ============================================================
# 6. HEATMAP 01 - INHERENT RISK MATRIX
# ============================================================

risk_matrix = pd.crosstab(
    df["Likelihood"],
    df["Impact"]
).reindex(
    index=range(1, 6),
    columns=range(1, 6),
    fill_value=0
)

plt.figure(figsize=(10, 7))

sns.heatmap(
    risk_matrix,
    annot=True,
    fmt="d",
    cmap="YlOrRd",
    linewidths=1,
    linecolor="white",
    cbar_kws={
        "label": "Number of identified risks"
    }
)

plt.title(
    "INHERENT RISK MATRIX\n"
    "Likelihood vs Impact",
    fontsize=15,
    fontweight="bold",
    pad=20
)

plt.xlabel("Impact (1-5)")
plt.ylabel("Likelihood (1-5)")

plt.tight_layout()

plt.savefig(
    f"{OUTPUT_DIR}/01_inherent_risk_matrix.png",
    dpi=300
)

plt.close()

# ============================================================
# 7. HEATMAP 02 - RESIDUAL RISK BY COUNTRY / PROCESS
# ============================================================

plt.figure(figsize=(17, 7))

sns.heatmap(
    exposure_matrix,
    annot=True,
    fmt=".1f",
    cmap="RdYlGn_r",
    linewidths=1,
    linecolor="white",
    vmin=0,
    vmax=25,
    cbar_kws={
        "label": "Average Residual Risk Score"
    }
)

plt.title(
    "LATAM OPERATIONAL RISK EXPOSURE\n"
    "Average Residual Risk by Country and Process",
    fontsize=15,
    fontweight="bold",
    pad=20
)

plt.xlabel("Operational Process")
plt.ylabel("Country")

plt.xticks(rotation=35, ha="right")

plt.tight_layout()

plt.savefig(
    f"{OUTPUT_DIR}/02_country_process_heatmap.png",
    dpi=300
)

plt.close()

# ============================================================
# 8. HEATMAP 03 - CONTROL EFFECTIVENESS
# ============================================================

control_matrix = df.pivot_table(
    index="Country",
    columns="Process",
    values="Control_Effectiveness",
    aggfunc="mean"
)

plt.figure(figsize=(17, 7))

sns.heatmap(
    control_matrix,
    annot=True,
    fmt=".1f",
    cmap="RdYlGn",
    linewidths=1,
    linecolor="white",
    vmin=0,
    vmax=100,
    cbar_kws={
        "label": "Control Effectiveness (%)"
    }
)

plt.title(
    "INTERNAL CONTROL EFFECTIVENESS\n"
    "Design and Operating Performance",
    fontsize=15,
    fontweight="bold",
    pad=20
)

plt.xlabel("Operational Process")
plt.ylabel("Country")

plt.xticks(rotation=35, ha="right")

plt.tight_layout()

plt.savefig(
    f"{OUTPUT_DIR}/03_control_effectiveness.png",
    dpi=300
)

plt.close()

# ============================================================
# 9. HEATMAP 04 - RISK CONCENTRATION
# ============================================================

risk_concentration = pd.crosstab(
    df["Country"],
    df["Risk_Level"]
).reindex(
    columns=["Low", "Moderate", "High", "Critical"],
    fill_value=0
)

plt.figure(figsize=(11, 6))

sns.heatmap(
    risk_concentration,
    annot=True,
    fmt="d",
    cmap="OrRd",
    linewidths=1,
    cbar_kws={
        "label": "Number of risk records"
    }
)

plt.title(
    "RISK CONCENTRATION BY COUNTRY",
    fontsize=15,
    fontweight="bold",
    pad=20
)

plt.xlabel("Risk Classification")
plt.ylabel("Country")

plt.tight_layout()

plt.savefig(
    f"{OUTPUT_DIR}/04_risk_concentration.png",
    dpi=300
)

plt.close()

# ============================================================
# 10. COUNTRY PERFORMANCE CHART
# ============================================================

country_plot = country_summary.sort_values(
    "Average_Residual_Risk",
    ascending=False
)

plt.figure(figsize=(11, 6))

sns.barplot(
    data=country_plot,
    x="Country",
    y="Average_Residual_Risk",
    hue="Country",
    palette="Reds_r",
    legend=False
)

plt.axhline(
    RISK_APPETITE,
    linestyle="--",
    color="black",
    label=f"Risk Appetite: {RISK_APPETITE}"
)

plt.title(
    "AVERAGE RESIDUAL RISK BY COUNTRY",
    fontsize=15,
    fontweight="bold"
)

plt.xlabel("Country")
plt.ylabel("Average Residual Risk")

plt.legend()
plt.tight_layout()

plt.savefig(
    f"{OUTPUT_DIR}/05_country_risk_comparison.png",
    dpi=300
)

plt.close()

# ============================================================
# 11. ROOT CAUSE / CONTROL DIAGNOSTICS
# ============================================================

df["Control_Gap"] = (
    df["Design_Effectiveness"]
    - df["Operating_Effectiveness"]
)

df["Control_Weakness"] = np.where(
    df["Operating_Effectiveness"] < 60,
    "Operating Control Weakness",
    np.where(
        df["Design_Effectiveness"] < 60,
        "Control Design Weakness",
        np.where(
            df["Control_Gap"] > 20,
            "Design vs Operating Gap",
            "No Major Control Gap Identified"
        )
    )
)

control_diagnostics = (
    df.groupby("Control_Weakness")
    .agg(
        Risk_Count=("Risk_ID", "count"),
        Average_Residual_Risk=("Residual_Risk", "mean"),
        Average_Operating_Effectiveness=(
            "Operating_Effectiveness", "mean"
        )
    )
    .reset_index()
    .sort_values("Average_Residual_Risk", ascending=False)
)

# ============================================================
# 12. MANAGEMENT DECISION ENGINE
# ============================================================

def generate_recommendations(data):

    recommendations = []

    critical = data[
        data["Risk_Level"] == "Critical"
    ]

    high = data[
        data["Risk_Level"] == "High"
    ]

    overdue = data[
        data["Overdue_Actions"] > 0
    ]

    weak_controls = data[
        data["Operating_Effectiveness"] < 60
    ]

    kri_breaches = data[
        data["KRI_Status"] == "BREACH"
    ]

    recurring = data[
        data["Recurring_Incidents"] > 0
    ]

    # Critical risk escalation
    if len(critical) > 0:

        recommendations.append(
            f"CRITICAL ESCALATION: {len(critical)} "
            "risk records exceed the critical threshold. "
            "Require immediate risk-owner review, "
            "documented mitigation plans and escalation "
            "according to the organization's risk appetite."
        )

    # High residual risk
    if len(high) > 0:

        recommendations.append(
            f"HIGH EXPOSURE: {len(high)} high-risk records "
            "require prioritized mitigation, assigned owners "
            "and time-bound corrective actions."
        )

    # Weak operating controls
    if len(weak_controls) > 0:

        recommendations.append(
            f"CONTROL EFFECTIVENESS: {len(weak_controls)} "
            "records show operating effectiveness below 60%. "
            "Perform control testing, investigate execution "
            "failures and assess whether redesign or automation "
            "is necessary."
        )

    # KRI breaches
    if len(kri_breaches) > 0:

        recommendations.append(
            f"KRI MONITORING: {len(kri_breaches)} records "
            "breach the defined incident threshold. "
            "Investigate trends, validate thresholds and "
            "determine whether escalation is required."
        )

    # Overdue actions
    if len(overdue) > 0:

        recommendations.append(
            f"ACTION GOVERNANCE: {len(overdue)} risk records "
            "have at least one overdue action. "
            "Review ownership, deadlines, dependencies "
            "and evidence of completion."
        )

    # Recurrence
    if len(recurring) > 0:

        recommendations.append(
            f"RECURRENCE ANALYSIS: {len(recurring)} records "
            "show recurring incidents. Prioritize root cause "
            "analysis and validate whether previous CAPAs "
            "were effective."
        )

    if not recommendations:

        recommendations.append(
            "No defined escalation triggers were identified. "
            "Continue periodic monitoring and control testing."
        )

    return recommendations


recommendations = generate_recommendations(df)

# ============================================================
# 13. EXECUTIVE DIAGNOSTIC
# ============================================================

total_risks = len(df)

critical_count = (
    df["Risk_Level"] == "Critical"
).sum()

high_count = (
    df["Risk_Level"] == "High"
).sum()

kri_count = (
    df["KRI_Status"] == "BREACH"
).sum()

escalation_count = (
    df["Escalation_Required"] == "YES"
).sum()

average_inherent = df["Inherent_Risk"].mean()
average_residual = df["Residual_Risk"].mean()

risk_reduction = (
    (average_inherent - average_residual)
    / average_inherent
) * 100

worst_country = country_summary.loc[
    country_summary["Average_Residual_Risk"].idxmax()
]

worst_process = process_summary.iloc[0]

worst_country_process = (
    df.groupby(["Country", "Process"])
    ["Residual_Risk"]
    .mean()
    .idxmax()
)

print("\n" + "=" * 65)
print("OPERATIONAL RISK MANAGEMENT - EXECUTIVE REPORT")
print("=" * 65)

print(f"\nAssessment date: {datetime.now():%Y-%m-%d}")

print(f"\nTotal risks assessed: {total_risks}")

print(f"Critical risks: {critical_count}")
print(f"High risks: {high_count}")
print(f"KRI breaches: {kri_count}")
print(f"Escalations required: {escalation_count}")

print("\n--- RISK EXPOSURE ---")

print(
    f"Average Inherent Risk: {average_inherent:.2f}/25"
)

print(
    f"Average Residual Risk: {average_residual:.2f}/25"
)

print(
    f"Modeled Risk Reduction: {risk_reduction:.2f}%"
)

print("\n--- PRIORITY EXPOSURES ---")

print(
    f"Country with highest average residual risk: "
    f"{worst_country['Country']}"
)

print(
    f"Process with highest average residual risk: "
    f"{worst_process['Process']}"
)

print(
    f"Highest exposure combination: "
    f"{worst_country_process[0]} / "
    f"{worst_country_process[1]}"
)

print("\n--- MANAGEMENT RECOMMENDATIONS ---")

for index, recommendation in enumerate(
    recommendations, start=1
):

    print(f"\n{index}. {recommendation}")

print("\n" + "=" * 65)

# ============================================================
# 14. EXPORT RESULTS
# ============================================================

df.to_csv(
    f"{OUTPUT_DIR}/risk_register.csv",
    index=False,
    encoding="utf-8-sig"
)

country_summary.to_excel(
    f"{OUTPUT_DIR}/country_summary.xlsx",
    index=False
)

process_summary.to_excel(
    f"{OUTPUT_DIR}/process_summary.xlsx",
    index=False
)

control_diagnostics.to_excel(
    f"{OUTPUT_DIR}/control_diagnostics.xlsx",
    index=False
)

with open(
    f"{OUTPUT_DIR}/executive_report.txt",
    "w",
    encoding="utf-8"
) as report:

    report.write(
        "OPERATIONAL RISK MANAGEMENT REPORT\n"
    )

    report.write("=" * 55 + "\n")

    report.write(
        f"Total risks: {total_risks}\n"
    )

    report.write(
        f"Critical risks: {critical_count}\n"
    )

    report.write(
        f"High risks: {high_count}\n"
    )

    report.write(
        f"KRI breaches: {kri_count}\n"
    )

    report.write(
        f"Escalations: {escalation_count}\n"
    )

    report.write(
        f"Average inherent risk: {average_inherent:.2f}\n"
    )

    report.write(
        f"Average residual risk: {average_residual:.2f}\n"
    )

    report.write(
        f"Modeled risk reduction: {risk_reduction:.2f}%\n"
    )

    report.write("\nMANAGEMENT RECOMMENDATIONS\n")

    for recommendation in recommendations:

        report.write(f"\n- {recommendation}\n")

print("\nFILES SUCCESSFULLY EXPORTED:")
print(f"Check the folder: {OUTPUT_DIR}")

print("\nRisk assessment completed.")

