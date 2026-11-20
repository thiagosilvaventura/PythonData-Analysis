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
