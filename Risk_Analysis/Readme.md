# Operational Risk Assessment & Risk Heatmap

## Project Overview

I developed this project in Python to simulate an operational risk assessment process across multiple countries and business processes.

The main objective was to structure risk information, evaluate the effectiveness of existing controls, calculate residual risk exposure, and apply consistent criteria to support risk prioritization.

I used synthetic data to represent operational scenarios involving incidents, control weaknesses, recurring issues, overdue actions, and Key Risk Indicators (KRIs). This allowed me to build and test the assessment logic without using confidential or company-specific information.

The project reflects concepts commonly used in Operational Risk Management, Internal Controls, Quality Assurance, and Continuous Improvement.

## Project Objectives

I structured the project around the following objectives:

- Assess inherent and residual risk levels using a consistent scoring methodology.
- Compare risk exposure across countries and operational processes.
- Evaluate control design and operating effectiveness.
- Incorporate incidents, recurrence, overdue actions, and KRI breaches into the assessment.
- Establish criteria for risk classification and escalation.
- Translate assessment results into management recommendations based on predefined conditions.

My intention was to represent how operational data can be organized and assessed to support risk monitoring, prioritization, and management decisions.

## Data Structure and Simulation

I used Python to generate a synthetic dataset representing operational risk records across five countries: Brazil, Mexico, Colombia, Chile, and Argentina.

The simulation covers different operational processes and risk categories. Each record contains attributes used throughout the assessment, including:

- Country and operational process.
- Risk category and description.
- Likelihood and impact scores.
- Control design effectiveness.
- Control operating effectiveness.
- Incident frequency and recurrence.
- Overdue corrective actions.
- KRI status.

I used **Pandas** to structure and manipulate the records, while **NumPy** supported numerical calculations and the generation of controlled variations in the simulated data.

The use of synthetic data made it possible to define different operational scenarios and test how changes in risk factors affect the assessment.

## Risk Assessment Methodology

I applied a scoring model based on two main dimensions: likelihood and impact.

### Inherent Risk

Inherent risk represents the level of exposure before considering the effect of controls.

I calculated it by multiplying the likelihood score by the impact score:

`Inherent Risk = Likelihood × Impact`

Both dimensions use a scale from 1 to 5, allowing each risk to receive a numerical score between 1 and 25.

### Control Effectiveness

I separated control effectiveness into two dimensions:

- **Design Effectiveness:** evaluates whether the control is appropriately structured to address the identified risk.
- **Operating Effectiveness:** evaluates whether the control is being consistently applied in practice.

I assigned a weight of 40% to design effectiveness and 60% to operating effectiveness.

`Control Effectiveness = (Design × 0.40) + (Operation × 0.60)`

I used a higher weight for operating effectiveness because a well-designed control does not necessarily reduce exposure if it is not consistently performed.

### Residual Risk

Residual risk represents the remaining exposure after considering the estimated effect of controls.

I calculated it using the inherent risk score and the control effectiveness percentage:

`Residual Risk = Inherent Risk × (1 - Control Effectiveness / 100 × 0.80)`

The 0.80 factor represents an adjustment applied within the simulation to avoid assuming that controls eliminate the entire identified exposure.

This calculation allows me to compare the initial exposure with the estimated risk remaining after controls are considered.

### Risk Classification

I defined four classification levels based on the resulting risk score:

| Risk Level | Score |
|---|---:|
| Critical | 15–25 |
| High | 10–14 |
| Moderate | 5–9 |
| Low | Below 5 |

These thresholds are parameters established for this project. They are illustrative and should not be interpreted as official COSO or ISO 31000 classification thresholds.

## Incident and KRI Assessment

I incorporated incident information into the assessment to represent how operational events can influence risk prioritization.

The model considers incident frequency, recurring events, overdue corrective actions, and KRI threshold breaches.

I defined a KRI breach in the simulation when the incident count exceeds three. This threshold is configurable and serves as an example of how an organization can establish monitoring criteria for operational indicators.

I also included escalation conditions based on the combination of risk classification, KRI breaches, and overdue actions.

This approach allows the assessment to consider not only the calculated risk score, but also operational signals that may require additional attention.

## Automated Decision Criteria

I used conditional logic in Python to associate assessment results with predefined management recommendations.

The criteria consider:

- Critical and high residual risk classifications.
- Low operating effectiveness.
- KRI threshold breaches.
- Overdue corrective actions.
- Recurring incidents.

I chose this approach to connect numerical risk assessment with practical management criteria. Instead of treating each risk score as an isolated value, the model considers additional indicators that may influence the need for investigation, escalation, or corrective action.

## Technology and Libraries

| Technology | Purpose |
|---|---|
| Python | Main programming language and assessment logic |
| Pandas | Data structuring, transformation, grouping, and aggregation |
| NumPy | Numerical calculations and synthetic data generation |
| Matplotlib | Chart construction and visual customization |
| Seaborn | Risk matrix and heatmap visualization |
| OpenPyXL | Excel workbook generation |

I used Python as the central component because it allowed me to keep data generation, calculations, classification rules, and visualizations within the same workflow.

Pandas and NumPy were selected to handle the tabular data and numerical operations. Matplotlib and Seaborn were used to represent risk scores and relationships between operational dimensions in a visual format.

## Execution

To install the required libraries:

```bash
pip install pandas numpy matplotlib seaborn openpyxl
```

To run the project:

```bash
python risk_assessment_engine.py
```

## Methodological Considerations

The dataset is entirely synthetic, and the scoring thresholds, weights, and escalation conditions are assumptions defined for this simulation.

The model is intended to demonstrate the structure and application of an operational risk assessment methodology. Its calculations do not represent measured business performance or an official implementation of any regulatory framework.

I used this project to apply Python to concepts related to operational risk, internal controls, incident monitoring, KRI assessment, and risk-based decision-making.

## Output Files

When I run the script, it saves the following files:

| File | What it contains |
|---|---|
| `risk_register.csv` | The full list of 245 risk records with all scores, classifications, KRI status and escalation flag. |
| `country_summary.xlsx` | Totals and averages for each country. |
| `process_summary.xlsx` | Totals and averages for each process. |
| `control_diagnostics.xlsx` | Count of records by type of control weakness. |
| `executive_report.txt` | A short summary with the main numbers and management recommendations. |
| `01_inherent_risk_matrix.png` | Likelihood vs impact matrix. |
| `02_country_process_heatmap.png` | Average residual risk by country and process. |
| `03_control_effectiveness.png` | Average control effectiveness by country and process. |
| `04_risk_concentration.png` | Number of records per risk level in each country. |
| `05_country_risk_comparison.png` | Average residual risk by country, compared to a risk appetite line of 8. |

## Results

All numbers below come from the synthetic dataset, so they only show how the model behaves. They are not real business results.

### Overall

- I assessed 245 risk records: 49 per country, 35 per process.
- Average inherent risk was 9.40 and average residual risk was 4.16. The model estimates that controls reduce risk by 55.78%.
- No record was classified as Critical. 7 records were classified as High.
- 14 records breached the KRI threshold, and 2 required escalation.
- 348 incidents were recorded in the last 90 days.

### By country

| Country | Avg. inherent risk | Avg. residual risk | High risks | KRI breaches |
|---|---:|---:|---:|---:|
| Mexico | 12.73 | 5.73 | 4 | 5 |
| Argentina | 10.16 | 4.55 | 2 | 5 |
| Colombia | 10.20 | 4.52 | 1 | 4 |
| Brazil | 8.49 | 3.65 | 0 | 0 |
| Chile | 5.43 | 2.34 | 0 | 0 |

- Mexico has the highest residual risk and the most High records. Chile has the lowest.
- All five countries are below the risk appetite line of 8 used in the country chart.
- Brazil and Chile have no KRI breaches.

### By process

| Process | Avg. residual risk | Avg. control effectiveness | Overdue actions |
|---|---:|---:|---:|
| Third Party Management | 6.78 | 65.9% | 36 |
| Information Security | 4.74 | 69.6% | 34 |
| Compliance | 4.65 | 70.1% | 46 |
| Technology | 3.92 | 71.7% | 26 |
| Customer Operations | 3.55 | 72.7% | 31 |
| Financial Operations | 2.87 | 72.3% | 18 |
| Quality Assurance | 2.58 | 71.7% | 23 |

- Third Party Management has the highest residual risk and the lowest control effectiveness.
- The highest country and process scores in the heatmap are Mexico – Third Party Management (9.6) and Argentina – Third Party Management (8.1). Both are above 8.
- Compliance has the most overdue actions (46).

### Controls and follow-up

- 58 records have operating effectiveness below 60%. These are the records with an operating control weakness, and their average operating effectiveness is 52.9%.
- 25 records have a control design weakness, 15 have a gap between design and operation, and 147 show no major gap.
- 142 records (58%) have at least one overdue action.
- 53 records have recurring incidents.

### Inherent risk matrix

The most common combination is likelihood 2 and impact 3, with 52 records. The next most common are likelihood 3 with impact 4 (31 records) and likelihood 3 with impact 3 (29 records).

## How the Code Helped

- **Consistent scoring:** I wrote the formulas once, and the code applied them to all 245 records. This gave every record the same inherent score, control effectiveness, residual score and risk level.
- **Combining signals:** The code checked each record for incidents, recurrence, overdue actions and KRI breaches at the same time. This is how I found the 14 KRI breaches and the 2 escalations without reviewing records one by one.
- **Comparing countries and processes:** Grouping the data let me see quickly that Mexico and Third Party Management had the highest residual risk.
- **Finding control problems:** The code labeled each record by type of control weakness, which showed that most weaknesses were in how controls are performed (58 records) rather than in how they are designed (25 records).
- **Ready-to-use outputs:** The script produced the Excel files, the CSV register, the charts and the text report in one run, so the results are easy to read and share.
