# Mamaearth Returns & Growth Intelligence Pipeline

This project uses SQL, Python, Pandas, Matplotlib, and Google's Gemini API to analyze Mamaearth's sales, revenue, product returns, and customer segments.

The pipeline consists of three parts:

1. SQL relational database and business reports.
2. Python data cleaning, exploratory data analysis, and visualization.
3. GenAI-powered business narrative using the Situation–Complication–Resolution (SCR) framework.

Follow the steps below in order to reproduce the results.

---

## 1. SQL Database and Business Reports

### Prerequisites

- Python installed.
- SQLite installed.
- The project dependencies installed.
- The three CSV files available in the `data/` directory.

The expected CSV files are:

- `data/customers.csv`
- `data/products.csv`
- `data/orders.csv`

### Running the SQL Pipeline

Open the VS Code terminal in the project root folder.

On this Windows setup, SQLite can be invoked using its full executable path:

```powershell
$sqlite = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages\SQLite.SQLite_Microsoft.Winget.Source_8wekyb3d8bbwe\sqlite3.exe"
```

If this path does not exist on another computer, locate the SQLite executable and update the path accordingly.

**Important:** The following commands are intended for a fresh database. They should not be run against an existing database containing the `loyalty_tier` column without first checking the schema.

Create the database tables:

```powershell
& $sqlite mamaearth.db ".read sql/schema.sql"
```

Load the seed data:

```powershell
& $sqlite mamaearth.db ".read sql/seed_data.sql"
```

Execute the business reports:

```powershell
& $sqlite mamaearth.db ".read sql/reports.sql"
```

The SQL layer contains three relational tables:

- `customers`
- `products`
- `orders`

The reporting layer covers order totals, missing ratings, zero-order customers, city-level return rates, customer spending rankings, category revenue, customer name pattern matching, acquisition sources, and loyalty tiers.

### Expected Record Counts

After loading the seed data, the expected record counts are:

| Table | Expected rows |
|---|---:|
| Customers | 45 |
| Products | 16 |
| Orders | 180 |

The SQL reports analyze the original, uncleaned data. The Python pipeline independently cleans the raw CSV files.

---

## 2. Data Cleaning, Analysis, and Visualization

Run the Python scripts from the project root folder.

### Step 1: Clean and Analyze the Data

```powershell
python analysis/clean_and_eda.py
```

This script loads the original CSV files directly using Pandas.

It performs the following operations:

- Loads and inspects the datasets.
- Standardizes payment method casing.
- Identifies and removes duplicate orders.
- Handles missing discount and rating values.
- Merges orders with customer and product information.
- Calculates order values and reconciles revenue.
- Detects quantity outliers using the interquartile range (IQR).
- Analyzes return rates by payment method.
- Identifies high-risk payment and city-tier combinations.
- Calculates correlations between ratings, returns, discounts, and quantities.
- Compares monthly revenue before and after excluding flagged outliers.
- Generates the structured findings used by the narrative generator.

### Revenue Reconciliation

The raw SQL analysis reports revenue of ₹99,860.20.

After removing five duplicate orders, the cleaned revenue is ₹97,358.30.

The difference of ₹2,501.90 is attributable to the removed duplicate orders. Missing-value imputation does not change the revenue total.

The quantity outliers are flagged for analysis rather than automatically removed from the cleaned dataset.

### Generated Findings

Part 2, Task 5 of the assignment requires the verified numerical findings to be written to:

```text
narrator/findings.json
```

This file contains the cleaned and raw revenue totals, the duplicate reconciliation difference, return rates by payment method, the highest-risk customer segment, and the corrected peak revenue month.

The findings file must be generated from the analysis results rather than manually maintained.

### Step 2: Generate Visualizations

After the analysis script finishes, run:

```powershell
python analysis/visualize.py
```

The script generates two PNG files in the `visualizations/` directory:

1. `return_rate_by_payment.png` — compares return rates across payment methods.
2. `monthly_revenue_trend.png` — displays outlier-corrected monthly revenue and identifies the genuine peak month.

Run the cleaning and analysis script before generating the visualizations so that the results are based on the current raw CSV files.

---

## 3. SCR Business Narrative

After completing the analysis and visualization steps, run:

```powershell
python narrator/generate_narrative.py
```

The script reads `narrator/findings.json` and generates a business narrative using the Situation–Complication–Resolution (SCR) framework.

The narrative explains:

- **Situation:** The cleaned revenue picture and overall business context.
- **Complication:** The return-rate problem, high-risk customer segment, and impact of duplicate orders.
- **Resolution:** Recommended operational actions based on the verified findings.

The script validates the required numerical findings and saves the narrative to:

```text
narrator/sample_output.txt
```

The pipeline supports both Gemini-powered generation and a deterministic offline fallback.

---

## 4. Running with Gemini

### Step 1: Obtain an API Key

Obtain a Gemini API key through Google AI Studio and use the available free usage tier.

The script uses the `google-genai` Python client library.

If the dependency is not installed, run:

```powershell
python -m pip install google-genai
```

### Step 2: Set the API Key in Windows PowerShell

In the same PowerShell terminal, run:

```powershell
$env:GEMINI_API_KEY="YOUR_API_KEY"
```

Replace `YOUR_API_KEY` with your actual key.

**Do not include the backslash before the colon.** The correct PowerShell syntax is `$env:GEMINI_API_KEY`.

This environment variable applies to the current PowerShell session. You do not need to write the key into the Python source code.

### Step 3: Run the Narrative Generator

```powershell
python narrator/generate_narrative.py
```

When a valid API key is configured, the script attempts to generate the narrative using Gemini.

The implementation uses deterministic generation settings, an explicit output-token limit, and request timeout handling.

If the API request fails or the generated narrative fails numerical validation, the script uses its offline fallback.

Keep your API key private. Never commit it to GitHub or include it in `findings.json`, `sample_output.txt`, or the README.

---

## 5. Running without Gemini (Offline Mode)

An API key is not required to run the offline narrative generator.

If `GEMINI_API_KEY` is not configured, run:

```powershell
python narrator/generate_narrative.py
```

The script uses its built-in offline narrative template, which reads the verified figures from `narrator/findings.json` and formats them into the SCR structure without making an API request.

The generated output is saved to:

```text
narrator/sample_output.txt
```

The offline fallback also runs when the Gemini request fails or the generated narrative does not pass numerical validation.

The narrative validation checks the required figures:

- Cleaned revenue: ₹97,358.30
- COD return rate: 44.4%
- COD + Tier-2 return rate: 54.5%
- Duplicate reconciliation difference: ₹2,501.90
- Corrected peak month: March, with revenue of ₹20,318.90

This allows the narrative pipeline to run without an API key, network access, or API expenditure.

---

## 6. Complete Execution Order

Follow these steps to reproduce the project results:

1. Create the database using `sql/schema.sql`.
2. Load the raw data using `sql/seed_data.sql`.
3. Run the business reports using `sql/reports.sql`.
4. Run `analysis/clean_and_eda.py` to clean and analyze the CSV data and generate `narrator/findings.json`.
5. Run `analysis/visualize.py` to generate the visualizations.
6. Run `narrator/generate_narrative.py` to generate and validate the SCR business narrative.
7. Review `narrator/sample_output.txt` to inspect the generated narrative.

The SQL and Python pipelines operate independently on the original datasets: the SQL reports analyze raw data, while the Python pipeline performs cleaning and reconciliation.

Following these steps reproduces the database reports, analysis results, visualizations, structured findings, and business narrative.

---

## Project Structure

```text
Mamaearth_Returns_Growth_Intelligence_Pipeline/
│
├── data/
│   ├── customers.csv
│   ├── products.csv
│   └── orders.csv
│
├── sql/
│   ├── schema.sql
│   ├── seed_data.sql
│   └── reports.sql
│
├── analysis/
│   ├── clean_and_eda.py
│   └── visualize.py
│
├── visualizations/
│   ├── return_rate_by_payment.png
│   └── monthly_revenue_trend.png
│
├── narrator/
│   ├── findings.json
│   ├── generate_narrative.py
│   └── sample_output.txt
│
├── README.md
└── mamaearth.db
```
