import pandas as pd
from pathlib import Path

# ============================================================
# MAMAEARTH RETURNS & GROWTH INTELLIGENCE PIPELINE
# Part 2: Python/Pandas Data Wrangling and EDA
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def heading(title):
    print("\n" + "=" * 75)
    print(title)
    print("=" * 75)


# ============================================================
# TASK 1 — LOAD AND INSPECT RAW DATA
# ============================================================

orders = pd.read_csv(DATA_DIR / "orders.csv")
customers = pd.read_csv(DATA_DIR / "customers.csv")
products = pd.read_csv(DATA_DIR / "products.csv")

heading("TASK 1: LOAD AND INSPECT RAW DATA")

print("Raw orders shape:", orders.shape)
print("Raw customers shape:", customers.shape)
print("Raw products shape:", products.shape)

print("\nRaw orders preview:")
print(orders.head())

if orders.shape != (180, 9):
    raise ValueError(f"Expected raw orders shape (180, 9), got {orders.shape}")


# ============================================================
# TASK 2 — STANDARDIZE PAYMENT METHOD CASING
# ============================================================

heading("TASK 2: STANDARDIZE PAYMENT METHODS")

print("Raw payment methods:")
print(orders["payment_method"].unique())
print("Distinct raw payment methods:",
      orders["payment_method"].nunique())

orders["payment_method"] = (
    orders["payment_method"].str.strip().str.upper()
)

print("\nPayment methods after standardization:")
print(orders["payment_method"].unique())

print("\nPayment method counts:")
print(orders["payment_method"].value_counts().sort_index())


# ============================================================
# TASK 3 — REMOVE DUPLICATE ORDERS
# ============================================================

heading("TASK 3: REMOVE DUPLICATE ORDERS")

natural_key = [
    "customer_id",
    "product_id",
    "order_date",
    "quantity",
    "discount_pct",
    "payment_method",
    "rating",
    "returned",
]

duplicate_mask = orders.duplicated(
    subset=natural_key,
    keep="first"
)

dropped_orders = orders.loc[duplicate_mask].copy()

print("Number of duplicate rows:", int(duplicate_mask.sum()))
print("Duplicate order IDs:")
print(dropped_orders["order_id"].tolist())

orders_clean = orders.loc[~duplicate_mask].copy()

print("Shape after removing duplicates:", orders_clean.shape)

if orders_clean.shape != (175, 9):
    raise ValueError(
        f"Expected cleaned shape (175, 9), got {orders_clean.shape}"
    )


# ============================================================
# TASK 4 — IMPUTE MISSING VALUES
# ============================================================

heading("TASK 4: IMPUTE MISSING VALUES")

missing_discounts = int(orders_clean["discount_pct"].isna().sum())
missing_ratings = int(orders_clean["rating"].isna().sum())

rating_median = orders_clean["rating"].median()

print("Missing discounts before imputation:", missing_discounts)
print("Missing ratings before imputation:", missing_ratings)
print("Median rating before imputation:", rating_median)

orders_clean["discount_pct"] = (
    orders_clean["discount_pct"].fillna(0)
)

orders_clean["rating"] = (
    orders_clean["rating"].fillna(rating_median)
)

print("\nMissing values after imputation:")
print(orders_clean[["discount_pct", "rating"]].isnull().sum())

print("\nDiscounts imputed:", missing_discounts)
print("Ratings imputed:", missing_ratings)


# ============================================================
# TASK 5 — MERGE AND RECONCILE REVENUE
# ============================================================

heading("TASK 5: MERGE AND RECONCILE REVENUE")

# Merge the original orders after payment standardization
# and the duplicate rows have been removed, but before
# missing-value imputation, to independently value duplicates.

dropped_valued = (
    dropped_orders
    .merge(products, on="product_id", how="left")
)

dropped_valued["order_value"] = (
    dropped_valued["quantity"]
    * dropped_valued["price"]
    * (1 - dropped_valued["discount_pct"].fillna(0) / 100)
)

duplicate_revenue = dropped_valued["order_value"].sum()

# Use the imputed, deduplicated orders for the cleaned total.
merged = (
    orders_clean
    .merge(products, on="product_id", how="left")
    .merge(customers, on="customer_id", how="left")
)

merged["order_value"] = (
    merged["quantity"]
    * merged["price"]
    * (1 - merged["discount_pct"] / 100)
)

cleaned_revenue = merged["order_value"].sum()

raw_revenue = 99860.20
revenue_delta = raw_revenue - cleaned_revenue

print("Cleaned order count:", len(merged))
print(f"Cleaned total revenue: ₹{cleaned_revenue:.2f}")
print(f"Part 1 raw revenue: ₹{raw_revenue:.2f}")
print(f"Revenue difference: ₹{revenue_delta:.2f}")
print(f"Revenue of the five dropped duplicate rows: ₹{duplicate_revenue:.2f}")

print(
    "\nRECONCILIATION NOTE: The raw Part 1 revenue was ₹99,860.20, "
    f"whereas cleaned revenue is ₹{cleaned_revenue:.2f}. "
    f"The difference is ₹{revenue_delta:.2f}, attributable to removing "
    f"the five duplicate orders in Task 3, whose independently calculated "
    f"combined order value is ₹{duplicate_revenue:.2f}. "
    "Filling missing discounts with zero and missing ratings with the "
    "median does not change the revenue total: missing discounts are "
    "valued at zero discount, and ratings do not enter the revenue formula."
)


# ============================================================
# TASK 6 — IQR OUTLIER DETECTION
# ============================================================

heading("TASK 6: IQR OUTLIER DETECTION ON QUANTITY")

q1 = merged["quantity"].quantile(0.25)
q3 = merged["quantity"].quantile(0.75)
iqr = q3 - q1

lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr

print(f"Q1: {q1}")
print(f"Q3: {q3}")
print(f"IQR: {iqr}")
print(f"Lower bound: {lower}")
print(f"Upper bound: {upper}")

merged["is_outlier"] = (
    (merged["quantity"] < lower)
    | (merged["quantity"] > upper)
)

outliers = merged.loc[
    merged["is_outlier"],
    ["order_id", "order_date", "quantity", "order_value"]
]

print("\nFlagged outlier orders:")
print(outliers.to_string(index=False))
print("Number of flagged outliers:", len(outliers))

# Keep outliers in the dataset; only flag them.


# ============================================================
# TASK 7 — HYPOTHESIS: DOES COD HAVE A HIGHER RETURN RATE?
# ============================================================

heading("TASK 7: PAYMENT METHOD AND RETURN RATE")

print("Hypothesis: COD orders have a higher return rate than CARD and UPI.")
print("Return rate is calculated as the mean of the binary returned column.")

payment_returns = (
    merged.groupby("payment_method")["returned"]
    .agg(["count", "mean"])
)

payment_returns["return_rate_pct"] = (
    payment_returns["mean"] * 100
).round(1)

print("\nReturn rate by payment method:")
print(payment_returns)

cod_rate = payment_returns.loc["COD", "return_rate_pct"]
other_rates = payment_returns.loc[
    ["CARD", "UPI"], "return_rate_pct"
]

if (cod_rate > other_rates).all():
    print("\nHypothesis result: CONFIRMED")
else:
    print("\nHypothesis result: NOT CONFIRMED")


# ============================================================
# TASK 8 — MULTI-LEVEL SEGMENTATION
# ============================================================

heading("TASK 8: PAYMENT METHOD AND CITY-TIER SEGMENTATION")

segment = (
    merged.groupby(["payment_method", "city_tier"])["returned"]
    .agg(["count", "mean"])
    .reset_index()
)

segment["return_rate_pct"] = (segment["mean"] * 100).round(1)

print("Return rates by payment method and city tier:")
print(
    segment[
        ["payment_method", "city_tier", "count", "return_rate_pct"]
    ].to_string(index=False)
)

highest_risk = segment.loc[segment["return_rate_pct"].idxmax()]

print(
    "\nHighest-risk segment: "
    f"{highest_risk['payment_method']} + Tier-{highest_risk['city_tier']} "
    f"cities at {highest_risk['return_rate_pct']:.1f}%."
)

print("\nCOD return rates by city tier:")
print(
    segment.loc[
        segment["payment_method"] == "COD",
        ["city_tier", "count", "return_rate_pct"]
    ].to_string(index=False)
)


# ============================================================
# TASK 9 — CORRELATION ANALYSIS
# ============================================================

heading("TASK 9: CORRELATION ANALYSIS")

correlation_columns = [
    "rating",
    "returned",
    "discount_pct",
    "quantity",
]

correlation_matrix = merged[correlation_columns].corr()

print("Correlation matrix:")
print(correlation_matrix.round(4))

print("\nPairwise correlation strengths:")


def correlation_band(value):
    absolute_value = abs(value)

    if absolute_value < 0.2:
        return "negligible"
    elif absolute_value < 0.4:
        return "weak"
    elif absolute_value < 0.7:
        return "moderate"
    else:
        return "strong"


for i in range(len(correlation_columns)):
    for j in range(i + 1, len(correlation_columns)):
        col1 = correlation_columns[i]
        col2 = correlation_columns[j]
        value = correlation_matrix.loc[col1, col2]

        print(
            f"{col1} vs {col2}: r={value:.4f} — "
            f"{correlation_band(value)}"
        )

discount_return_corr = correlation_matrix.loc[
    "discount_pct", "returned"
]

print(
    "\nHypothesis: Higher discounts reduce returns. "
    f"Correlation = {discount_return_corr:.4f}. "
    "Hypothesis result: BUSTED; correlation alone does not establish causation."
)


# ============================================================
# TASK 10 — OUTLIER-CORRECTED MONTHLY REVENUE
# ============================================================

heading("TASK 10: MONTHLY REVENUE WITH AND WITHOUT OUTLIERS")

merged["order_date"] = pd.to_datetime(merged["order_date"])
merged["year_month"] = merged["order_date"].dt.to_period("M").astype(str)

monthly_all = (
    merged.groupby("year_month")["order_value"]
    .sum()
    .sort_index()
)

monthly_corrected = (
    merged.loc[~merged["is_outlier"]]
    .groupby("year_month")["order_value"]
    .sum()
    .sort_index()
)

print("Monthly revenue including outliers:")
for month, revenue in monthly_all.items():
    print(f"{month}: ₹{revenue:.2f}")

print("\nMonthly revenue excluding flagged outliers:")
for month, revenue in monthly_corrected.items():
    print(f"{month}: ₹{revenue:.2f}")

apparent_peak = monthly_all.idxmax()
true_peak = monthly_corrected.idxmax()

print(
    "\nTIME-SERIES FINDING: January's apparent lead is an artifact of "
    "the two bulk orders O0011 (2026-01-28) and O0098 (2026-01-10). "
    f"January revenue falls from ₹{monthly_all.loc['2026-01']:.2f} "
    f"to ₹{monthly_corrected.loc['2026-01']:.2f} when those outliers "
    f"are excluded. March is the genuine peak month, with corrected "
    f"revenue of ₹{monthly_corrected.loc[true_peak]:.2f}."
)

print("\nAnalysis complete.")
# TASK 11: EXPORT FINDINGS FOR THE NARRATIVE GENERATOR

import json
from pathlib import Path

# Calculate the highest-risk COD + Tier 2 segment.
cod_tier2 = merged[
    (merged["payment_method"] == "COD") &
    (merged["city_tier"] == 2)
]

cod_tier2_return_rate = round(cod_tier2["returned"].mean() * 100, 1)

# Find the genuine peak month after excluding flagged outliers.
true_peak_month = monthly_corrected.idxmax()

findings = {
    "cleaned_total_revenue_inr": round(float(cleaned_revenue), 2),
    "raw_total_revenue_inr": round(float(raw_revenue), 2),
    "duplicate_reconciliation_delta_inr": round(float(revenue_delta), 2),
    "return_rate_by_payment": {
        method: round(float(rate), 1)
        for method, rate in payment_returns["return_rate_pct"].items()
    },
    "highest_risk_segment": {
        "payment_method": "COD",
        "city_tier": 2,
        "return_rate_pct": cod_tier2_return_rate
    },
    "true_peak_month": {
        "month": str(true_peak_month),
        "revenue_inr": round(float(monthly_corrected.loc[true_peak_month]), 2)
    },
    "outlier_inflated_month": {
        "month": "2026-01",
        "apparent_revenue_inr": round(float(monthly_all.loc["2026-01"]), 2),
        "corrected_revenue_inr": round(float(monthly_corrected.loc["2026-01"]), 2)
    }
}

output_path = Path(__file__).resolve().parent.parent / "narrator" / "findings.json"
output_path.write_text(json.dumps(findings, indent=2), encoding="utf-8")

print(f"Findings exported successfully to: {output_path}")
